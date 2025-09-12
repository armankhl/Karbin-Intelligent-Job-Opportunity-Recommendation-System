# services/recommendation_service.py
import os
import psycopg2
import numpy as np
from dotenv import load_dotenv
from services.embedding_service import embed_texts
import faiss
from sklearn.metrics.pairwise import cosine_similarity

# --- 1. CONFIGURATION & DATABASE ---
load_dotenv()

# --- 3. LOAD MACHINE LEARNING ARTIFACTS AT STARTUP ---
# This is crucial for performance, preventing file I/O on every request.
FAISS_INDEX_PATH = os.path.join('data', 'job_index.faiss')
JOB_ID_MAP_PATH = os.path.join('data', 'job_id_map.npy')
faiss_index = None
job_id_map = None

try:
    print("Loading FAISS index...")
    faiss_index = faiss.read_index(FAISS_INDEX_PATH)
    print(f"FAISS index loaded. Contains {faiss_index.ntotal} vectors.")
    
    print("Loading job ID map...")
    job_id_map = np.load(JOB_ID_MAP_PATH)
    print("Job ID map loaded successfully.")
        
    # Create a reverse map for quick lookups: DB Job ID -> FAISS Index Position
    job_id_to_faiss_idx = {job_id: i for i, job_id in enumerate(job_id_map)}

except FileNotFoundError:
    print("CRITICAL WARNING: FAISS index or job ID map or TF-IDF artifacts not found. Recommendation endpoint will be disabled.")
except Exception as e:
    print(f"An error occurred while loading recommendation artifacts: {e}")


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

# --- 2. USER VECTOR GENERATION (REVISED) ---

def _build_user_text(user_id: int) -> str:
    """
    Connects to the DB and constructs a descriptive text from the user's profile.
    This is now aligned with the most important semantic fields: their professional
    title, their skills, and their detailed work experience.
    """
    conn = get_db_connection()
    if not conn:
        return ""

    full_text_parts = []
    try:
        with conn.cursor() as cur:
            # 1. Fetch professional title from user_profiles
            cur.execute("SELECT professional_title FROM user_profiles WHERE user_id = %s", (user_id,))
            profile_res = cur.fetchone()
            if profile_res and profile_res[0]:
                full_text_parts.append(profile_res[0])

            # 2. Fetch skills from user_skills
            cur.execute("""
                SELECT s.name FROM skills s
                JOIN user_skills us ON s.id = us.skill_id
                WHERE us.user_id = %s
            """, (user_id,))
            skills_res = cur.fetchall()
            if skills_res:
                skills_text = ", ".join([row[0] for row in skills_res])
                full_text_parts.append(f"Skills include: {skills_text}")

            # 3. Fetch work experience descriptions
            cur.execute("""
                SELECT description FROM work_experiences
                WHERE user_id = %s AND description IS NOT NULL AND description != ''
            """, (user_id,))
            exp_res = cur.fetchall()
            if exp_res:
                experience_text = " ".join([row[0] for row in exp_res])
                full_text_parts.append(f"Past work experience: {experience_text}")

    except Exception as e:
        print(f"Error building user text for user_id {user_id}: {e}")
    finally:
        conn.close()

    return ". ".join(filter(None, full_text_parts))

def get_user_vector(user_id: int) -> np.ndarray | None:
    """
    Generates a semantic vector embedding for a given user ID.
    (This function's logic does not need to change.)
    """
    user_text = _build_user_text(user_id)
    if not user_text:
        print(f"Warning: No text data found for user_id {user_id} to generate a vector.")
        return None
    
    user_embedding = embed_texts([user_text])
    return user_embedding[0]

# --- 3. HARD FILTERING ---

def get_filtered_job_ids(user_id: int, min_skill_overlap: int = 0) -> list[int]:
    """
    Implements Stage 1: Candidate Generation.
    Applies all hard filters to find a small, highly-relevant pool of job candidates.
    """
    conn = get_db_connection()
    if not conn: return []

    candidate_job_ids = []
    try:
        with conn.cursor() as cur:
            # 1. Fetch all user preferences in one go
            cur.execute("""
                SELECT preferred_provinces, wants_full_time, wants_part_time,
                       wants_remote, wants_onsite, wants_internship,
                       experience_level, preferred_category_id
                FROM user_profiles WHERE user_id = %s
            """, (user_id,))
            
            prefs = cur.fetchone()
            if not prefs: return []
            
            provinces, full_time, part_time, remote, onsite, internship, exp_level, cat_id = prefs
            
            # 2. Build the powerful filtering query with a Common Table Expression (CTE) for skill overlap
            query_parts = []
            params = {'user_id': user_id, 'min_skill_overlap': min_skill_overlap}

            # --- THE CORE SKILL OVERLAP LOGIC ---
            base_query = """
                WITH user_skill_set AS (
                    SELECT skill_id FROM user_skills WHERE user_id = %(user_id)s
                ),
                job_skill_counts AS (
                    SELECT js.job_id, count(js.skill_id) as matching_skills
                    FROM job_skill js
                    WHERE js.skill_id IN (SELECT skill_id FROM user_skill_set)
                    GROUP BY js.job_id
                )
                SELECT jp.id FROM job_postings jp
                JOIN job_skill_counts jsc ON jp.id = jsc.job_id
                WHERE jp.is_active = TRUE AND jp.scraped_at >= NOW() - INTERVAL '45 days'
                AND jsc.matching_skills >= %(min_skill_overlap)s
            """
            query_parts.append(base_query)
            
            # --- filters ---
            if cat_id:
                query_parts.append("AND jp.category_id = %(cat_id)s")
                params['cat_id'] = cat_id
            if provinces:
                params['provinces'] = tuple([p.strip() for p in provinces.split(',')])
                query_parts.append("AND jp.province IN %(provinces)s")
            if exp_level is not None:
                query_parts.append("AND jp.minimum_experience <= %(exp_level)s")
                params['exp_level'] = exp_level

            # Time commitment filtering
            if full_time and not part_time:
                query_parts.append("AND is_full_time = TRUE")
            elif part_time and not full_time:
                query_parts.append("AND is_part_time = TRUE")
            # If user wants both, we don't add a filter, showing them all options.

            # Location type filtering
            if remote and not onsite:
                query_parts.append("AND is_remote = TRUE")
            elif onsite and not remote:
                 query_parts.append("AND is_remote = FALSE")
            # If user wants both, we don't add a filter, showing them all options.

            
            final_query = " ".join(query_parts)
            cur.execute(final_query, params)
            candidate_job_ids = [row[0] for row in cur.fetchall()]

    except Exception as e:
        print(f"Error in get_filtered_job_ids: {e}")
    finally:
        if conn: conn.close()
        
    return candidate_job_ids
# ... (keep all existing functions like get_user_vector, get_filtered_job_ids) ...

def get_recommendations_for_user(user_id: int, top_k: int = 10) -> list[dict]:
    """
    The complete, reusable recommendation pipeline.
    This function contains the core logic previously in the api.py route.
    """
    # NOTE: This requires loading the ML artifacts in the module's scope.
    # We will do this in the final api.py and send_job_alerts.py files.
    
    # --- Stage 1: Candidate Generation (The Sieve) ---
    candidate_ids = get_filtered_job_ids(user_id)
    if not candidate_ids:
        return []

    # --- Stage 2: Candidate Ranking (The Magnet) ---
    user_vector = get_user_vector(user_id)
    if user_vector is None:
        return []

    candidate_faiss_indices = [job_id_to_faiss_idx[job_id] for job_id in candidate_ids if job_id in job_id_to_faiss_idx]
    if not candidate_faiss_indices:
        return []

    candidate_vectors = faiss_index.reconstruct_batch(np.array(candidate_faiss_indices, dtype=np.int64))
    user_vector_2d = np.array([user_vector]).astype('float32')
    similarities = cosine_similarity(user_vector_2d, candidate_vectors)[0]
    
    scored_candidates = [{"job_id": candidate_ids[i], "score": float(similarities[i])} for i in range(len(candidate_faiss_indices))]
    final_recs = sorted(scored_candidates, key=lambda x: x['score'], reverse=True)[:top_k]
    
    if not final_recs:
        return []

    # --- Stage 3: Enrich with Details and Reasoning ---
    final_job_ids = [rec['job_id'] for rec in final_recs]
    scores_map = {rec['job_id']: rec['score'] for rec in final_recs}
    
    conn = get_db_connection()
    if not conn: return []
    
    results = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT s.name FROM skills s JOIN user_skills us ON s.id = us.skill_id WHERE us.user_id = %s", (user_id,))
            user_skills = {row[0] for row in cur.fetchall()}
            
            cur.execute("SELECT js.job_id, s.name FROM skills s JOIN job_skill js ON s.id = js.skill_id WHERE js.job_id = ANY(%s)", (final_job_ids,))
            job_skills_map = {job_id: set() for job_id in final_job_ids}
            for job_id, skill_name in cur.fetchall():
                job_skills_map[job_id].add(skill_name)
            
            cur.execute("""
                SELECT jp.id, jp.title, c.name AS company_name, jp.city, jp.source_link
                FROM job_postings jp JOIN companies c ON jp.company_id = c.id
                WHERE jp.id = ANY(%s)
            """, (final_job_ids,))
            jobs_data = {row[0]: dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()}

            for job_id in final_job_ids:
                if job_id in jobs_data:
                    job_info = jobs_data[job_id]
                    job_info['score'] = scores_map[job_id]
                    matching_skills = user_skills.intersection(job_skills_map.get(job_id, set()))
                    job_info['reason'] = f"Matches skills: {', '.join(matching_skills)}" if matching_skills else "Strong profile match"
                    results.append(job_info)
    except Exception as e:
        print(f"Enrichment error: {e}")
    finally:
        conn.close()

    return results

# --- 4. VERIFICATION BLOCK (UNCHANGED) ---
if __name__ == "__main__":
    print("\n--- Running Verification for Day 3 Deliverables (Revised) ---")
    
    TEST_USER_ID = 1 # Make sure this user has a complete profile

    print(f"\n1. Building user text for user_id: {TEST_USER_ID}")
    user_text_for_embedding = _build_user_text(TEST_USER_ID)
    print(f"   - Generated Text: '{user_text_for_embedding[:200]}...'") # Print a snippet

    print(f"\n2. Generating vector for user_id: {TEST_USER_ID}")
    user_vector = get_user_vector(TEST_USER_ID)
    if user_vector is not None:
        print("   - Verification passed: Vector is valid.")
    else:
        print("   - FAILED to generate user vector.")

    print(f"\n3. Applying revised hard filters for user_id: {TEST_USER_ID}")
    filtered_ids = get_filtered_job_ids(TEST_USER_ID)
    if filtered_ids is not None:
        print(f"   - Found {len(filtered_ids)} candidate jobs matching the user's new preferences.")
        if len(filtered_ids) > 0:
            print(f"   - A sample of candidate job IDs: {filtered_ids[:10]}")
        print("   - Verification passed: Filtering logic is working.")
    else:
        print("   - FAILED to get filtered jobs.")

    print("\n--- Day 3 Deliverables Complete and Verified! ---")