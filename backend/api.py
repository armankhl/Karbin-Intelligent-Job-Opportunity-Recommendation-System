"""
Main Flask API for the KarBin Job Recommendation System.

This application provides endpoints for:
- User authentication (registration, login).
- Managing user profiles (CVs).
- Serving job postings.
- Generating personalized job recommendations.
"""

# --- 1. IMPORTS ---
import os
import faiss
import numpy as np
import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
from services.recommendation_service import get_user_vector, get_filtered_job_ids
from sklearn.metrics.pairwise import cosine_similarity

# --- 2. CONFIGURATION & INITIALIZATIONS ---

# Load environment variables from .env file FIRST
load_dotenv()

# Initialize Flask App and extensions
app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# Configure JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "a-default-fallback-secret-key")
jwt = JWTManager(app)

# Define constants
LATEST_JOBS_LIMIT = 6

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
    print("Job ID map loaded and reverse map created.")
    
except FileNotFoundError:
    print("CRITICAL WARNING: FAISS index or job ID map not found. Recommendation endpoint will be disabled.")
except Exception as e:
    print(f"An error occurred while loading recommendation artifacts: {e}")

# --- 4. HELPER FUNCTIONS ---

def get_db_connection():
    """Establishes a reusable connection to the PostgreSQL database."""
    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    except psycopg2.OperationalError as e:
        print(f"Database connection error: {e}")
        return None

# --- 5. API ROUTES ---

# === PUBLIC ROUTES ===
@app.route('/api/jobs/latest', methods=['GET'])
def get_latest_jobs():
    """Fetches the N most recent job postings for the homepage."""
    jobs = []
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT jp.id, jp.title, c.name AS company_name, jp.city, jp.source_link
                FROM job_postings jp JOIN companies c ON jp.company_id = c.id
                WHERE jp.is_active = TRUE
                ORDER BY jp.scraped_at DESC LIMIT %s;
            """, (LATEST_JOBS_LIMIT,))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            jobs = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Database error in get_latest_jobs: {e}")
        return jsonify({"error": "Could not retrieve jobs"}), 500
    finally:
        conn.close()
    return jsonify(jobs)

# === AUTHENTICATION ROUTES ===
@app.route('/api/auth/check-email', methods=['POST'])
def check_email():
    # ... (This logic is sound and remains unchanged)
    email = request.json.get('email', '').strip()
    if not email: return jsonify({"error": "Email is required"}), 400
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            return jsonify({"exists": cur.fetchone() is not None})
    finally: conn.close()

@app.route('/api/auth/register', methods=['POST'])
def register():
    data, conn = request.json, get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        with conn.cursor() as cur:
            password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
            cur.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (data['name'], data['email'], password_hash)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            access_token = create_access_token(identity=str(user_id))
            return jsonify(access_token=access_token), 201
    except psycopg2.IntegrityError: return jsonify({"error": "Email already exists"}), 409
    except Exception as e: print(f"Register error: {e}"); return jsonify({"error": "Registration failed"}), 500
    finally: conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    # Gracefully handle cases where request body might not be JSON
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
        
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
            user_record = cur.fetchone()
            if user_record and bcrypt.check_password_hash(user_record[1], password):
                access_token = create_access_token(identity=str(user_record[0]))
                return jsonify(access_token=access_token)
            else:
                return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "An internal error occurred"}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Fetches the complete profile for the currently logged-in user.
    This version is robust and handles new users gracefully.
    """
    current_user_id = get_jwt_identity()
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500

    # --- THE CORE FIX ---
    # Define a complete, default structure that the frontend expects.
    profile_data = {
        "user_id": current_user_id,
        "experience_level": 0,
        "first_name": None, "last_name": None, "phone_number": None,
        "professional_title": None, "expected_salary": None,
        "wants_full_time": False, "wants_part_time": False,
        "wants_remote": False, "wants_onsite": False, "wants_internship": False,
        "preferred_provinces": None,
        "work_experiences": [],
        "educations": [],
        "skills": []
    }

    try:
        with conn.cursor() as cur:
            # Fetch base profile data from user_profiles
            cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (current_user_id,))
            profile_row = cur.fetchone()
            if profile_row:
                columns = [desc[0] for desc in cur.description]
                profile_from_db = dict(zip(columns, profile_row))
                
                # --- POLISH IS HERE ---
                # Explicitly handle boolean fields to ensure they are never null in the response
                for key in ['wants_full_time', 'wants_part_time', 'wants_remote', 'wants_onsite', 'wants_internship']:
                    if profile_from_db.get(key) is None:
                        profile_from_db[key] = False
                
                profile_data.update(profile_from_db)
            # Fetch related data (these will correctly return empty lists if nothing is found)
            cur.execute("SELECT * FROM work_experiences WHERE user_id = %s ORDER BY start_date DESC", (current_user_id,))
            columns = [desc[0] for desc in cur.description]
            profile_data['work_experiences'] = [dict(zip(columns, row)) for row in cur.fetchall()]
            
            cur.execute("SELECT * FROM educations WHERE user_id = %s", (current_user_id,))
            columns = [desc[0] for desc in cur.description]
            profile_data['educations'] = [dict(zip(columns, row)) for row in cur.fetchall()]
            
            cur.execute("SELECT s.name FROM skills s JOIN user_skills us ON s.id = us.skill_id WHERE us.user_id = %s", (current_user_id,))
            profile_data['skills'] = [row[0] for row in cur.fetchall()]

    except Exception as e:
        print(f"Get profile error: {e}")
        return jsonify({"error": "Could not retrieve profile"}), 500
    finally:
        conn.close()
        
    return jsonify(profile_data)            

@app.route('/api/profile', methods=['POST'])
@jwt_required()
def update_profile():
    """Creates or updates the profile for the currently logged-in user."""
    current_user_id = get_jwt_identity()
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            # ... (The user_profiles update logic is unchanged and correct) ...
            profile = data['profile']
            salary_str = profile.get('expected_salary')
            expected_salary = int(salary_str) if salary_str and str(salary_str).strip() else None

            # 1. UPSERT user_profiles
            sql = """
                INSERT INTO user_profiles (
                    user_id, first_name, last_name, phone_number, professional_title,
                    expected_salary, wants_full_time, wants_part_time, wants_remote,
                    wants_onsite, wants_internship, preferred_provinces, experience_level, preferred_category_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name,
                    phone_number = EXCLUDED.phone_number, professional_title = EXCLUDED.professional_title,
                    expected_salary = EXCLUDED.expected_salary, wants_full_time = EXCLUDED.wants_full_time,
                    wants_part_time = EXCLUDED.wants_part_time, wants_remote = EXCLUDED.wants_remote,
                    wants_onsite = EXCLUDED.wants_onsite, wants_internship = EXCLUDED.wants_internship,
                    preferred_provinces = EXCLUDED.preferred_provinces, experience_level = EXCLUDED.experience_level,
                    preferred_category_id = EXCLUDED.preferred_category_id;
            """
            cur.execute(sql, (
                current_user_id, profile.get('first_name'), profile.get('last_name'),
                profile.get('phone_number'), profile.get('professional_title'), expected_salary,
                profile.get('wants_full_time', False), profile.get('wants_part_time', False),
                profile.get('wants_remote', False), profile.get('wants_onsite', False),
                profile.get('wants_internship', False), profile.get('preferred_provinces'),
                int(profile.get('experience_level', 0)),
                profile.get('preferred_category_id') or None
            ))

            # Experiences
            cur.execute("DELETE FROM work_experiences WHERE user_id = %s", (current_user_id,))
            for exp in data.get('work_experiences', []):
                cur.execute("INSERT INTO work_experiences (user_id, job_title, company_name, description) VALUES (%s, %s, %s, %s)",
                            (current_user_id, exp['job_title'], exp['company_name'], exp.get('description')))
            # Educations
            cur.execute("DELETE FROM educations WHERE user_id = %s", (current_user_id,))
            for edu in data.get('educations', []):
                cur.execute("INSERT INTO educations (user_id, degree, field_of_study, university_name) VALUES (%s, %s, %s, %s)",
                            (current_user_id, edu['degree'], edu['field_of_study'], edu['university_name']))

            # 4. Synchronize Skills
            cur.execute("DELETE FROM user_skills WHERE user_id = %s", (current_user_id,))
            for skill_name in data.get('skills', []):
                # Step A: Ensure the skill exists in the main `skills` table.
                cur.execute(
                    "INSERT INTO skills (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                    (skill_name,)
                )
                # Step B: Now that it's guaranteed to exist, fetch its ID.
                cur.execute("SELECT id FROM skills WHERE name = %s", (skill_name,))
                skill_id_result = cur.fetchone()
                
                if skill_id_result:
                    skill_id = skill_id_result[0]
                    # Step C: Link the skill to the user.
                    cur.execute("INSERT INTO user_skills (user_id, skill_id) VALUES (%s, %s)", (current_user_id, skill_id))
                else:
                    # This is a safety log, it should not happen in normal operation.
                    print(f"Warning: Could not find or create ID for skill '{skill_name}'")
            
            conn.commit()
            return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        print(f"Update profile error: {e}")
        return jsonify({"error": "Failed to update profile"}), 500
    finally:
        conn.close()


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Fetches the list of job categories for UI dropdowns."""
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM categories ORDER BY name")
            categories = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
            return jsonify(categories)
    except Exception as e:
        print(f"Get categories error: {e}")
        return jsonify({"error": "Could not retrieve categories"}), 500
    finally:
        conn.close()

# === PROTECTED RECOMMENDATION ROUTE ===
@app.route('/api/recommendations', methods=['GET'])
@jwt_required()
def get_recommendations():
    """
    Generates personalized job recommendations using a multi-stage,
    filter-then-rank strategy.
    """
    # --- Step 0: Pre-computation Checks ---
    if faiss_index is None:
        return jsonify({"error": "Recommendation service is unavailable"}), 503
    
    current_user_id = get_jwt_identity()
    top_k = request.args.get('top_k', default=10, type=int)

    # --- Stage 1: Candidate Generation (The Sieve) ---
    # Get a small, highly-relevant pool of jobs using hard filters.
    candidate_ids = get_filtered_job_ids(current_user_id)
    if not candidate_ids:
        return jsonify([]), 200 # Return empty list if no jobs match basic criteria

    # --- Stage 2: Candidate Ranking (The Magnet) ---
    user_vector = get_user_vector(current_user_id)
    if user_vector is None:
        return jsonify({"message": "Please complete your profile for recommendations."}), 200

    # Get the FAISS indices ONLY for our candidate jobs
    candidate_faiss_indices = [job_id_to_faiss_idx[job_id] for job_id in candidate_ids if job_id in job_id_to_faiss_idx]
    if not candidate_faiss_indices:
        return jsonify([]), 200

    # Reconstruct the vectors for only the candidates from the FAISS index
    candidate_vectors = faiss_index.reconstruct_batch(np.array(candidate_faiss_indices, dtype=np.int64))
    
    # Prepare user vector for comparison
    user_vector_2d = np.array([user_vector]).astype('float32')
    
    # Calculate cosine similarity against the small candidate pool
    similarities = cosine_similarity(user_vector_2d, candidate_vectors)[0]
    
    # Combine candidate IDs with their semantic scores
    scored_candidates = [{"job_id": candidate_ids[i], "score": float(similarities[i])} for i in range(len(candidate_faiss_indices))]
    
    # Sort by score and take the top N results
    final_recs = sorted(scored_candidates, key=lambda x: x['score'], reverse=True)[:top_k]
    
    if not final_recs:
        return jsonify([]), 200

    # --- Stage 3: Enrich with Details and Reasoning ---
    final_job_ids = [rec['job_id'] for rec in final_recs]
    scores_map = {rec['job_id']: rec['score'] for rec in final_recs}
    
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    results = []
    try:
        with conn.cursor() as cur:
            # A) Get the user's skills for comparison
            cur.execute("SELECT s.name FROM skills s JOIN user_skills us ON s.id = us.skill_id WHERE us.user_id = %s", (current_user_id,))
            user_skills = {row[0] for row in cur.fetchall()}
            
            # B) Get the skills for the recommended jobs
            cur.execute("""
                SELECT js.job_id, s.name FROM skills s
                JOIN job_skill js ON s.id = js.skill_id
                WHERE js.job_id = ANY(%s)
            """, (final_job_ids,))
            
            job_skills_map = {}
            for job_id, skill_name in cur.fetchall():
                if job_id not in job_skills_map:
                    job_skills_map[job_id] = set()
                job_skills_map[job_id].add(skill_name)
            
            # C) Get the main job details
            cur.execute("""
                SELECT jp.id, jp.title, c.name AS company_name, jp.city, jp.source_link
                FROM job_postings jp JOIN companies c ON jp.company_id = c.id
                WHERE jp.id = ANY(%s)
            """, (final_job_ids,))
            
            jobs_data = {row[0]: dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()}

            # D) Assemble the final response
            for job_id in final_job_ids:
                if job_id in jobs_data:
                    job_info = jobs_data[job_id]
                    job_info['score'] = scores_map[job_id]
                    
                    # Calculate matching skills for the "reason"
                    matching_skills = user_skills.intersection(job_skills_map.get(job_id, set()))
                    if matching_skills:
                        job_info['reason'] = f"Matches your skills in: {', '.join(matching_skills)}"
                    else:
                        job_info['reason'] = "Strong semantic match to your profile"
                        
                    results.append(job_info)

    except Exception as e:
        print(f"Get recommendations details error: {e}")
        return jsonify({"error": "Could not retrieve job details"}), 500
    finally:
        conn.close()

    return jsonify(results)

# --- 6. MAIN EXECUTION BLOCK ---
if __name__ == '__main__':
    # The debug=True setting enables auto-reloading when you save the file.
    # Set host='0.0.0.0' to make the server accessible from other devices on your network.
    app.run(host='0.0.0.0', port=5000, debug=True)
