from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, JWTManager
import os
from dotenv import load_dotenv
import psycopg2
import faiss
import numpy as np
from services.recommendation_service import get_user_vector, get_filtered_job_ids

# --- Load Recommendation Artifacts at Startup ---
FAISS_INDEX_PATH = os.path.join('data', 'job_index.faiss')
JOB_ID_MAP_PATH = os.path.join('data', 'job_id_map.npy')
faiss_index = None
job_id_map = None
job_id_to_faiss_idx = {}

try:
    print("Loading FAISS index...")
    faiss_index = faiss.read_index(FAISS_INDEX_PATH)
    print(f"FAISS index loaded. Contains {faiss_index.ntotal} vectors.")
    
    print("Loading job ID map...")
    job_id_map = np.load(JOB_ID_MAP_PATH)
    
    # Create a reverse map for quick lookups: DB Job ID -> FAISS Index Position
    job_id_to_faiss_idx = {job_id: i for i, job_id in enumerate(job_id_map)}
    print("Job ID map loaded and reverse map created.")
    
except FileNotFoundError:
    print("Warning: FAISS index or job ID map not found. Recommendation endpoint will be disabled.")
except Exception as e:
    print(f"An error occurred while loading recommendation artifacts: {e}")
    

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

# --- Setup JWT ---
app.config["JWT_SECRET_KEY"] = "your-super-secret-key-change-this" # Change this!
jwt = JWTManager(app)
# --- End JWT Setup ---

# ... get_db_connection function ...
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn

# ... /api/jobs/latest route (no changes needed) ...
@app.route('/api/jobs/latest', methods=['GET'])
def get_latest_jobs():
    jobs = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT jp.id, jp.title, c.name AS company_name, jp.city, jp.source_link
                FROM job_postings jp JOIN companies c ON jp.company_id = c.id
                ORDER BY jp.scraped_at DESC LIMIT 6;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            for row in rows:
                jobs.append(dict(zip(columns, row)))
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Could not retrieve jobs from database"}), 500
    finally:
        conn.close()
    return jsonify(jobs)


# --- AUTHENTICATION ROUTES (No changes needed inside these functions) ---

@app.route('/api/auth/check-email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    if not email:
        return jsonify({"error": "Email is required"}), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            return jsonify({"exists": user is not None})
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"error": "Missing name, email, or password"}), 400
    
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (name, email, password_hash)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            
            access_token = create_access_token(identity=user_id) # Also create token on register
            return jsonify(access_token=access_token), 201
            
    except psycopg2.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
            user_record = cur.fetchone()
            
            if user_record and bcrypt.check_password_hash(user_record[1], password):
                user_id = user_record[0]
                access_token = create_access_token(identity=user_id) # Create token
                return jsonify(access_token=access_token) # Return token
            else:
                return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

@app.route('/api/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    """Fetches a complete user profile."""
    conn = get_db_connection()
    profile_data = {}
    try:
        with conn.cursor() as cur:
            # Fetch basic profile
            cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
            profile = cur.fetchone()
            if profile:
                columns = [desc[0] for desc in cur.description]
                profile_data = dict(zip(columns, profile))

            # Fetch work experiences
            cur.execute("SELECT * FROM work_experiences WHERE user_id = %s ORDER BY start_date DESC", (user_id,))
            experiences = []
            columns = [desc[0] for desc in cur.description]
            for row in cur.fetchall():
                experiences.append(dict(zip(columns, row)))
            profile_data['work_experiences'] = experiences

            # Fetch educations
            cur.execute("SELECT * FROM educations WHERE user_id = %s", (user_id,))
            educations = []
            columns = [desc[0] for desc in cur.description]
            for row in cur.fetchall():
                educations.append(dict(zip(columns, row)))
            profile_data['educations'] = educations

            # Fetch skills
            cur.execute("""
                SELECT s.name FROM skills s
                JOIN user_skills us ON s.id = us.skill_id
                WHERE us.user_id = %s
            """, (user_id,))
            profile_data['skills'] = [row[0] for row in cur.fetchall()]

    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

    return jsonify(profile_data)


@app.route('/api/profile/<int:user_id>', methods=['POST'])
def update_profile(user_id):
    """Creates or updates a complete user profile."""
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # --- 1. Update user_profiles (using ON CONFLICT for UPSERT) ---
            profile = data['profile']
            sql = """
                INSERT INTO user_profiles (user_id, first_name, last_name, phone_number, professional_title,
                                         seniority_level, employment_types, preferred_cities, expected_salary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name,
                    phone_number = EXCLUDED.phone_number, professional_title = EXCLUDED.professional_title,
                    seniority_level = EXCLUDED.seniority_level, employment_types = EXCLUDED.employment_types,
                    preferred_cities = EXCLUDED.preferred_cities, expected_salary = EXCLUDED.expected_salary;
            """
            cur.execute(sql, (user_id, profile.get('first_name'), profile.get('last_name'), profile.get('phone_number'),
                              profile.get('professional_title'), profile.get('seniority_level'),
                              ",".join(profile.get('employment_types', [])), ",".join(profile.get('preferred_cities', [])),
                              profile.get('expected_salary')))

            # --- 2. Update work_experiences (delete old, insert new) ---
            cur.execute("DELETE FROM work_experiences WHERE user_id = %s", (user_id,))
            for exp in data.get('work_experiences', []):
                cur.execute("INSERT INTO work_experiences (user_id, job_title, company_name, description) VALUES (%s, %s, %s, %s)",
                            (user_id, exp['job_title'], exp['company_name'], exp.get('description')))

            # --- 3. Update educations (delete old, insert new) ---
            cur.execute("DELETE FROM educations WHERE user_id = %s", (user_id,))
            for edu in data.get('educations', []):
                cur.execute("INSERT INTO educations (user_id, degree, field_of_study, university_name) VALUES (%s, %s, %s, %s)",
                            (user_id, edu['degree'], edu['field_of_study'], edu['university_name']))

            # --- 4. Update skills (delete old, insert new) ---
            cur.execute("DELETE FROM user_skills WHERE user_id = %s", (user_id,))
            for skill_name in data.get('skills', []):
                # Get or create skill in the main `skills` table
                cur.execute("INSERT INTO skills (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (skill_name,))
                cur.execute("SELECT id FROM skills WHERE name = %s", (skill_name,))
                skill_id = cur.fetchone()[0]
                # Link skill to user
                cur.execute("INSERT INTO user_skills (user_id, skill_id) VALUES (%s, %s)", (user_id, skill_id))

            conn.commit() # Commit the transaction
            return jsonify({"message": "Profile updated successfully"}), 200

    except Exception as e:
        conn.rollback() # Rollback transaction on error
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)