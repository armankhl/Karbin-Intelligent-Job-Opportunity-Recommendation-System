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
# from services.recommendation_service import get_user_vector, get_filtered_job_ids
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import random
from datetime import datetime, timedelta, timezone
import hmac
from services.email_service import send_verification_email
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.recommendation_service import get_recommendations_for_user



# --- 2. CONFIGURATION & INITIALIZATIONS ---

# Load environment variables from .env file FIRST
load_dotenv()

# Initialize Flask App and extensions
app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# --- Configure Flask-Limiter ---
# This uses a simple in-memory store, perfect for your current setup.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Configure JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "a-default-fallback-secret-key")
jwt = JWTManager(app)

# --- 3. LOAD MACHINE LEARNING ARTIFACTS AT STARTUP ---
# This is crucial for performance, preventing file I/O on every request.
FAISS_INDEX_PATH = os.path.join('data', 'job_index.faiss')
JOB_ID_MAP_PATH = os.path.join('data', 'job_id_map.npy')
faiss_index = None
job_id_map = None

TFIDF_VECTORIZER_PATH = os.path.join('data', 'tfidf_vectorizer.joblib')
TFIDF_MATRIX_PATH = os.path.join('data', 'tfidf_matrix.joblib')
TFIDF_JOB_ID_MAP_PATH = os.path.join('data', 'tfidf_job_id_map.joblib')
tfidf_vectorizer = None
tfidf_matrix = None


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
    print("Loading TF-IDF artifacts for relevance sort...")
    tfidf_vectorizer = joblib.load(TFIDF_VECTORIZER_PATH)
    tfidf_matrix = joblib.load(TFIDF_MATRIX_PATH)
    tfidf_job_ids = joblib.load(TFIDF_JOB_ID_MAP_PATH)
    print("TF-IDF artifacts loaded successfully.")

except FileNotFoundError:
    print("CRITICAL WARNING: FAISS index or job ID map or TF-IDF artifacts not found. Recommendation endpoint will be disabled.")
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
    LATEST_JOBS_LIMIT = 9
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

#####

@app.route('/api/auth/send-verification', methods=['POST'])
@jwt_required()
@limiter.limit("1 per minute")
def send_verification():
    """
    Generates and sends a new verification code for the logged-in user.
    """
    current_user_id = int(get_jwt_identity())
    
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            # 1. Fetch user's email and verification status
            cur.execute("SELECT email, is_verified FROM users WHERE id = %s", (current_user_id,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"error": "User not found"}), 404
            
            user_email, is_verified = user_record
            if is_verified:
                return jsonify({"message": "Email is already verified"}), 400

            # 2. Generate a 6-digit code
            code = f"{random.randint(0, 999999):06d}"
            
            # 3. Set expiration time (15 minutes from now)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            
            # 4. Save code to the database (UPSERT logic is robust)
            cur.execute("""
                INSERT INTO email_verifications (user_id, code, expires_at, attempts)
                VALUES (%s, %s, %s, 0)
                ON CONFLICT (user_id) DO UPDATE SET
                    code = EXCLUDED.code,
                    expires_at = EXCLUDED.expires_at,
                    attempts = 0;
            """, (current_user_id, code, expires_at))
            
            # 5. Send the email via our service
            email_sent = send_verification_email(user_email, code)
            
            if email_sent:
                conn.commit()
                return jsonify({"message": "Verification code sent successfully"}), 200
            else:
                conn.rollback()
                return jsonify({"error": "Failed to send verification email"}), 500

    except Exception as e:
        if conn: conn.rollback()
        print(f"Send verification error: {e}")
        return jsonify({"error": "An internal error occurred"}), 500
    finally:
        if conn: conn.close()
@app.route('/api/auth/verify-code', methods=['POST'])
@jwt_required()
def verify_code():
    """
    Verifies the submitted code for the logged-in user.
    """
    current_user_id = int(get_jwt_identity())
    submitted_code = request.json.get('code')
    
    if not submitted_code:
        return jsonify({"error": "Verification code is required"}), 400

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT code, expires_at, attempts FROM email_verifications WHERE user_id = %s", (current_user_id,))
            verification_record = cur.fetchone()
            
            if not verification_record:
                return jsonify({"error": "No verification process started. Please request a new code."}), 404
            
            stored_code, expires_at, attempts = verification_record
            
            if attempts >= 5:
                return jsonify({"error": "Too many attempts. Please request a new code."}), 429

            if datetime.now(timezone.utc) > expires_at:
                return jsonify({"error": "Verification code has expired. Please request a new one."}), 410

            # --- THE FIX IS HERE ---
            # Use hmac.compare_digest and encode both strings to bytes
            if not hmac.compare_digest(stored_code.encode('utf-8'), submitted_code.encode('utf-8')):
                cur.execute("UPDATE email_verifications SET attempts = attempts + 1 WHERE user_id = %s", (current_user_id,))
                conn.commit()
                return jsonify({"error": "Invalid verification code"}), 400

            # --- Success Case ---
            cur.execute("UPDATE users SET is_verified = TRUE WHERE id = %s", (current_user_id,))
            cur.execute("DELETE FROM email_verifications WHERE user_id = %s", (current_user_id,))
            conn.commit()
            return jsonify({"message": "Email verified successfully"}), 200

    except Exception as e:
        if conn: conn.rollback()
        print(f"Verify code error: {e}")
        return jsonify({"error": "An internal error occurred"}), 500
    finally:
        if conn: conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
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
            # --- THE FIX (Step 1): Fetch the is_verified status ---
            cur.execute("SELECT id, password_hash, is_verified FROM users WHERE email = %s", (email,))
            user_record = cur.fetchone()
            
            if user_record and bcrypt.check_password_hash(user_record[1], password):
                user_id = user_record[0]
                is_verified = user_record[2]
                
                access_token = create_access_token(identity=str(user_id))
                
                # --- THE FIX (Step 2): Return a different status based on verification ---
                if is_verified:
                    # User is fully authenticated and verified
                    return jsonify({
                        "access_token": access_token,
                        "status": "verified"
                    })
                else:
                    # User is authenticated but NOT verified
                    return jsonify({
                        "access_token": access_token,
                        "status": "unverified"
                    })
            else:
                return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "An internal error occurred"}), 500
    finally:
        if conn: conn.close()

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


@app.route('/api/recommendations', methods=['GET'])
@jwt_required()
def get_recommendations():
    """
    A thin wrapper that calls the reusable recommendation service.
    """
    if faiss_index is None:
        return jsonify({"error": "Recommendation service is unavailable"}), 503
    
    current_user_id = int(get_jwt_identity())
    top_k = request.args.get('top_k', default=10, type=int)
    
    recommendations = get_recommendations_for_user(current_user_id, top_k=top_k)
    
    return jsonify(recommendations)

@app.route('/api/jobs', methods=['GET'])
@jwt_required(optional=True)
def get_jobs():
    """
    Fetches, filters, sorts, and paginates job postings for the main job hub.
    """
    # --- 1. Get Parameters & Define Page Size ---
    JOBS_PER_PAGE = 12  # <--- THIS IS THE CHANGE
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    province = request.args.get('province', '', type=str)
    category_id = request.args.get('category_id', None, type=int)
    sort_by = request.args.get('sortBy', 'newest', type=str)
    
    current_user_id = get_jwt_identity()
    
    # --- 2. Build Dynamic SQL Query ---
    # ... (This part of the code is unchanged) ...
    base_query = """
        SELECT jp.id, jp.title, c.name as company_name, jp.province, cat.name as category_name,
               jp.scraped_at, jp.salary, jp.source_link
        FROM job_postings jp
        JOIN companies c ON jp.company_id = c.id
        LEFT JOIN categories cat ON jp.category_id = cat.id
    """
    count_query = "SELECT COUNT(jp.id) FROM job_postings jp"
    
    where_clauses = ["jp.is_active = TRUE"]
    params = {}
    
    if search_query:
        where_clauses.append("jp.title ILIKE %(search)s")
        params['search'] = f"%{search_query}%"
    if province:
        where_clauses.append("jp.province = %(province)s")
        params['province'] = province
    if category_id:
        where_clauses.append("jp.category_id = %(category_id)s")
        params['category_id'] = category_id
    
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)
        base_query += where_sql
        count_query += where_sql

    # --- 3. Handle Sorting ---
    if sort_by == 'relevance' and current_user_id and tfidf_vectorizer:
        # ... (Relevance sort logic is unchanged) ...
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                from services.recommendation_service import _build_user_text
                user_text = _build_user_text(current_user_id)
                if user_text:
                    cur.execute(base_query.replace("SELECT jp.id, ...", "SELECT jp.id"), params)
                    filtered_job_ids = {row[0] for row in cur.fetchall()}
                    matrix_indices = [i for i, job_id in enumerate(tfidf_job_ids) if job_id in filtered_job_ids]
                    if matrix_indices:
                        user_vector = tfidf_vectorizer.transform([user_text])
                        similarities = cosine_similarity(user_vector, tfidf_matrix[matrix_indices])[0]
                        ranked_job_ids = [tfidf_job_ids[matrix_indices[i]] for i in np.argsort(similarities)[::-1]]
                        
                        # Apply pagination with the new page size
                        offset = (page - 1) * JOBS_PER_PAGE
                        paginated_ids = ranked_job_ids[offset : offset + JOBS_PER_PAGE]
                        
                        base_query = base_query.replace(" WHERE " + " AND ".join(where_clauses), "")
                        base_query += " WHERE jp.id = ANY(%(paginated_ids)s) ORDER BY array_position(%(paginated_ids)s, jp.id)"
                        params = {'paginated_ids': paginated_ids}
                        count_query = "SELECT COUNT(id) FROM job_postings WHERE id = ANY(%(ranked_job_ids)s)"
                        count_params = {'ranked_job_ids': ranked_job_ids}
        except Exception as e:
            print(f"Relevance sort failed: {e}")
            sort_by = 'newest'
        finally:
            if conn: conn.close()
    
    if sort_by != 'relevance':
        order_by_sql = {
            'newest': " ORDER BY jp.scraped_at DESC",
            'pay': " ORDER BY jp.salary::bigint DESC NULLS LAST"
        }.get(sort_by, " ORDER BY jp.scraped_at DESC")
        base_query += order_by_sql
        
        # Use the new page size variable here
        base_query += " LIMIT %(limit)s OFFSET %(offset)s"
        params['limit'] = JOBS_PER_PAGE
        params['offset'] = (page - 1) * JOBS_PER_PAGE
        count_params = params

    # --- 4. Execute Queries and Return Response ---
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(count_query, count_params)
            total_count = cur.fetchone()[0]
            
            cur.execute(base_query, params)
            columns = [desc[0] for desc in cur.description]
            jobs = [dict(zip(columns, row)) for row in cur.fetchall()]
            
            return jsonify({
                "jobs": jobs,
                "total_count": total_count,
                "current_page": page,
                # Update total_pages calculation with the new page size
                "total_pages": (total_count + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE
            })
    except Exception as e:
        print(f"Get jobs error: {e}")
        return jsonify({"error": "Failed to retrieve jobs"}), 500
    finally:
        if conn: conn.close()

# --- 6. MAIN EXECUTION BLOCK ---
if __name__ == '__main__':
    # The debug=True setting enables auto-reloading when you save the file.
    # Set host='0.0.0.0' to make the server accessible from other devices on your network.
    app.run(host='0.0.0.0', port=5000, debug=True)
