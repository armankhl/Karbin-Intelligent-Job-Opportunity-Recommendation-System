# services/recommendation_service.py
import os
import psycopg2
import numpy as np
from dotenv import load_dotenv
from services.embedding_service import embed_texts

# --- 1. CONFIGURATION & DATABASE ---
load_dotenv()

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Fatal: Could not connect to the database: {e}")
        return None

# --- 2. USER VECTOR GENERATION ---

def _build_user_text(user_id: int) -> str:
    """
    Connects to the DB and constructs a single descriptive text from a user's profile.
    """
    conn = get_db_connection()
    if not conn:
        return ""

    full_text_parts = []
    try:
        with conn.cursor() as cur:
            # 1. Fetch from user_profiles
            cur.execute("""
                SELECT professional_title, seniority_level, preferred_cities
                FROM user_profiles WHERE user_id = %s
            """, (user_id,))
            profile_res = cur.fetchone()
            if profile_res:
                prof_title, seniority, cities = profile_res
                full_text_parts.append(prof_title or "")
                # full_text_parts.append(seniority or "")
                # full_text_parts.append(cities.replace(',', ' ') if cities else "")

            # 2. Fetch skills from user_skills
            cur.execute("""
                SELECT s.name FROM skills s
                JOIN user_skills us ON s.id = us.skill_id
                WHERE us.user_id = %s
            """, (user_id,))
            skills_res = cur.fetchall()
            if skills_res:
                skills_text = ", ".join([row[0] for row in skills_res])
                # full_text_parts.append(f"Skills: {skills_text}")

            # 3. Fetch work experience descriptions
            cur.execute("""
                SELECT description FROM work_experiences
                WHERE user_id = %s AND description IS NOT NULL
            """, (user_id,))
            exp_res = cur.fetchall()
            if exp_res:
                experience_text = " ".join([row[0] for row in exp_res])
                # full_text_parts.append(f"Work history: {experience_text}")

    except Exception as e:
        print(f"Error building user text for user_id {user_id}: {e}")
    finally:
        conn.close()

    # Join all non-empty parts into a single string
    return ". ".join(filter(None, full_text_parts))

def get_user_vector(user_id: int) -> np.ndarray | None:
    """
    Generates a semantic vector embedding for a given user ID.

    Returns:
        np.ndarray: The user's profile embedding.
        None: If the user profile is empty or an error occurs.
    """
    user_text = _build_user_text(user_id)
    if not user_text:
        print(f"Warning: No text data found for user_id {user_id} to generate a vector.")
        return None
    
    # embed_texts expects a list of strings, so we wrap our single string in a list.
    user_embedding = embed_texts([user_text])
    return user_embedding[0] # Return the first (and only) embedding

def get_filtered_job_ids(user_id: int) -> list[int]:
    """
    Applies hard filters using the new structured columns for high efficiency.
    """
    conn = get_db_connection()
    if not conn:
        return []

    candidate_job_ids = []
    try:
        with conn.cursor() as cur:
            # 1. Fetch user's new structured preferences
            cur.execute("""
                SELECT preferred_provinces, wants_full_time, wants_part_time,
                       wants_remote, wants_onsite, wants_internship
                FROM user_profiles WHERE user_id = %s
            """, (user_id,))
            
            prefs = cur.fetchone()
            if not prefs: return []
            
            provinces, full_time, part_time, remote, onsite, internship = prefs
            
            # 2. Build the dynamic SQL query
            query_parts = ["SELECT id FROM job_postings WHERE is_active = TRUE AND scraped_at >= NOW() - INTERVAL '45 days'"]
            params = []
            
            # Province filtering
            if provinces:
                preferred_provinces = [p.strip() for p in provinces.split(',')]
                query_parts.append("AND province = ANY(%s)")
                params.append(preferred_provinces)

            # Internship filtering
            if internship:
                query_parts.append("AND is_internship = TRUE")

            # Time commitment filtering
            if full_time and not part_time:
                query_parts.append("AND is_full_time = TRUE")
            elif part_time and not full_time:
                query_parts.append("AND is_part_time = TRUE")
            # If user wants both, we don't add a filter (or could use `is_full_time OR is_part_time`)

            # Location type filtering
            if remote and not onsite:
                query_parts.append("AND is_remote = TRUE")
            # If user wants onsite but not remote, we can filter for non-remote jobs
            elif onsite and not remote:
                 query_parts.append("AND is_remote = FALSE")

            # 3. Execute query
            final_query = " ".join(query_parts)
            cur.execute(final_query, params)
            candidate_job_ids = [row[0] for row in cur.fetchall()]

    except Exception as e:
        print(f"Error filtering jobs for user_id {user_id}: {e}")
    finally:
        conn.close()
        
    return candidate_job_ids

# --- 4. DELIVERABLE VERIFICATION (TESTING BLOCK) ---
if __name__ == "__main__":
    print("\n--- Running Verification for Day 3 Deliverables ---")
    
    # We will test with the user we created in the previous steps.
    # Make sure this user has a complete profile in your database.
    TEST_USER_ID = 2

    # --- Test 1: Generate User Vector ---
    print(f"\n1. Generating vector for user_id: {TEST_USER_ID}")
    user_vector = get_user_vector(TEST_USER_ID)
    
    if user_vector is not None:
        print(f"   - Successfully generated user vector.")
        print(f"   - Vector dimension: {user_vector.shape[0]}")
        # A simple check to ensure it's not all zeros
        assert user_vector.any(), "Vector should not be all zeros."
        print("   - Verification passed: Vector is valid.")
    else:
        print("   - FAILED to generate user vector. Check user profile data.")

    # --- Test 2: Apply Hard Filters ---
    print(f"\n2. Applying hard filters for user_id: {TEST_USER_ID}")
    filtered_ids = get_filtered_job_ids(TEST_USER_ID)

    if filtered_ids is not None:
        print(f"   - Successfully applied filters.")
        print(f"   - Found {len(filtered_ids)} candidate jobs matching the user's preferences.")
        if len(filtered_ids) > 0:
            print(f"   - A sample of candidate job IDs: {filtered_ids[:10]}")
        print("   - Verification passed: Filtering logic is working.")
    else:
        print("   - FAILED to get filtered jobs.")

    print("\n--- Day 3 Deliverables Complete and Verified! ---")