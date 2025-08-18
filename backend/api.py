from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for all routes, allowing requests from any origin
CORS(app)

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn

@app.route('/api/jobs/latest', methods=['GET'])
def get_latest_jobs():
    """API endpoint to fetch the 5 most recent job postings."""
    jobs = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Query to get the latest 5 jobs, joining with the companies table
            cur.execute("""
                SELECT 
                    jp.id, 
                    jp.title, 
                    c.name AS company_name, 
                    jp.city, 
                    jp.source_link
                FROM 
                    job_postings jp
                JOIN 
                    companies c ON jp.company_id = c.id
                ORDER BY 
                    jp.scraped_at DESC
                LIMIT 5;
            """)
            rows = cur.fetchall()
            # Get column names from the cursor description
            columns = [desc[0] for desc in cur.description]
            for row in rows:
                # Create a dictionary for each job posting
                jobs.append(dict(zip(columns, row)))
                
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Could not retrieve jobs from database"}), 500
    finally:
        conn.close()
        
    return jsonify(jobs)

if __name__ == '__main__':
    # Runs the API on http://127.0.0.1:5000
    app.run(debug=True, port=5000)