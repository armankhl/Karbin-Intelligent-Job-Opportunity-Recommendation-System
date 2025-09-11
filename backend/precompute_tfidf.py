import os
import joblib
import psycopg2
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer

# Load environment variables
load_dotenv()

# --- Configuration ---
os.makedirs('data', exist_ok=True)
TFIDF_VECTORIZER_PATH = os.path.join('data', 'tfidf_vectorizer.joblib')
TFIDF_MATRIX_PATH = os.path.join('data', 'tfidf_matrix.joblib')
# We also need to save the order of job_ids for mapping
TFIDF_JOB_ID_MAP_PATH = os.path.join('data', 'tfidf_job_id_map.joblib')

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def main():
    print("--- Starting TF-IDF Pre-computation ---")
    conn = get_db_connection()
    if not conn: return

    try:
        with conn.cursor() as cur:
            # Fetch all active jobs' text data
            cur.execute("""
                SELECT jp.id, COALESCE(jp.title, '') || ' ' || COALESCE(jp.job_description, '') || ' ' || COALESCE(STRING_AGG(s.name, ' '), '') as job_text
                FROM job_postings jp
                LEFT JOIN job_skill js ON jp.id = js.job_id
                LEFT JOIN skills s ON js.skill_id = s.id
                WHERE jp.is_active = TRUE
                GROUP BY jp.id
            """)
            job_data = cur.fetchall()
            if not job_data:
                print("No active jobs to process.")
                return

            job_ids, job_texts = zip(*job_data)
            print(f"Loaded text for {len(job_texts)} jobs.")

            # Create and fit the TF-IDF vectorizer
            print("Fitting TF-IDF vectorizer...")
            vectorizer = TfidfVectorizer(max_features=5000, stop_words=None) # Using None for Persian
            tfidf_matrix = vectorizer.fit_transform(job_texts)
            
            # Save the artifacts
            print(f"Saving vectorizer to {TFIDF_VECTORIZER_PATH}")
            joblib.dump(vectorizer, TFIDF_VECTORIZER_PATH)
            
            print(f"Saving TF-IDF matrix to {TFIDF_MATRIX_PATH}")
            joblib.dump(tfidf_matrix, TFIDF_MATRIX_PATH)
            
            print(f"Saving job ID map to {TFIDF_JOB_ID_MAP_PATH}")
            joblib.dump(job_ids, TFIDF_JOB_ID_MAP_PATH)
            
            print("\n--- TF-IDF Pre-computation Complete! ---")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()