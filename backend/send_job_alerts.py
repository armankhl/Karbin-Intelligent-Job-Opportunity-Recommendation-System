import os
import argparse
import psycopg2
import numpy as np
import faiss
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from services.recommendation_service import get_recommendations_for_user
from services.email_service import send_recommendations_email


# --- IMPORTANT: These globals must be loaded for the service to work ---
load_dotenv()
FAISS_INDEX_PATH = os.path.join('data', 'job_index.faiss')
JOB_ID_MAP_PATH = os.path.join('data', 'job_id_map.npy')
faiss_index = faiss.read_index(FAISS_INDEX_PATH)
job_id_map = np.load(JOB_ID_MAP_PATH)
job_id_to_faiss_idx = {job_id: i for i, job_id in enumerate(job_id_map)}


# --- NEW: Define constants for clarity ---
CANDIDATES_FOR_RERANKING = 50  # Retrieve 50 candidates for the cross-encoder to re-rank
FINAL_RECOMMENDATIONS_COUNT = 7 # Send the top 7 most accurate results in the email


def main(user_id: int, count: int):
    """
    Generates and emails job recommendations for a specific user.
    """
    print(f"--- Starting Recommendation Email Sender for User ID: {user_id} ---")
    
    # 1. Fetch user's email and name from the database using a JOIN
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    user_email, user_name = None, "کاربر گرامی" # A more polite default name
    try:
        with conn.cursor() as cur:
            # --- THE FIX IS HERE ---
            # We use a LEFT JOIN to get the email from 'users' and the first_name
            # from 'user_profiles'. This handles users who haven't created a profile yet.
            cur.execute("""
                SELECT u.email, up.first_name
                FROM users u
                LEFT JOIN user_profiles up ON u.id = up.user_id
                WHERE u.id = %s
            """, (user_id,))
            
            user_record = cur.fetchone()
            if not user_record:
                print(f"Error: User with ID {user_id} not found.")
                return
            
            # Unpack the results and provide a fallback for the name
            user_email = user_record[0]
            fetched_name = user_record[1]
            if fetched_name:
                user_name = fetched_name

    except Exception as e:
        print(f"Database error fetching user info: {e}")
        return
    finally:
        if conn:
            conn.close()
 # 2. Get Recommendations with Re-ranking Enabled
    print("Generating high-accuracy recommendations...")
    recommendations = get_recommendations_for_user(
        user_id,
        top_k=count,
        retrieval_k=CANDIDATES_FOR_RERANKING,
        use_reranker=True  # <-- THE KEY CHANGE IS HERE
    )
    
    if not recommendations:
        print(f"No suitable recommendations found for user {user_id}. No email will be sent.")
        return    

    # 3. Send the email
    print(f"Found {len(recommendations)} recommendations. Preparing to send email...")
    success = send_recommendations_email(
        recipient_email=user_email,
        user_name=user_name,
        jobs=recommendations
    )

    if success:
        print("--- Process Completed Successfully! ---")
    else:
        print("--- Process Failed. Check Brevo API logs. ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send job recommendations to a user.")
    parser.add_argument("--user-id", type=int, required=True, help="The ID of the user to send recommendations to.")
    parser.add_argument("--count", type=int, default=4, help="The number of recommendations to send.")
    args = parser.parse_args()
    
    main(args.user_id, args.count)