from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt  # <-- FIX #1: This line was likely missing.
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)           # <-- FIX #2: This line initializes the bcrypt object.
CORS(app)

# ... get_db_connection function (no changes needed) ...
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
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash)
            )
            conn.commit()
            return jsonify({"message": "User registered successfully"}), 201
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
            cur.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
            user_record = cur.fetchone()
            
            if user_record and bcrypt.check_password_hash(user_record[0], password):
                return jsonify({"message": "Login successful"})
            else:
                return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)