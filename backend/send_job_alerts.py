import os
import argparse
import psycopg2
import numpy as np
import faiss
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# --- IMPORTANT: These globals must be loaded for the service to work ---
load_dotenv()
FAISS_INDEX_PATH = os.path.join('data', 'job_index.faiss')
JOB_ID_MAP_PATH = os.path.join('data', 'job_id_map.npy')
faiss_index = faiss.read_index(FAISS_INDEX_PATH)
job_id_map = np.load(JOB_ID_MAP_PATH)
job_id_to_faiss_idx = {job_id: i for i, job_id in enumerate(job_id_map)}

# Now, import our services
from services.recommendation_service import get_recommendations_for_user
from services.email_service import send_recommendations_email

def main(user_id: int, count: int):
    """
    Generates and emails job recommendations for a specific user.
    """
    print(f"--- Starting Recommendation Email Sender for User ID: {user_id} ---")
    
    # 1. Fetch user's name and email from the database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    user_email, user_name = None, "User"
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email, name FROM users WHERE id = %s", (user_id,))
            user_record = cur.fetchone()
            if not user_record:
                print(f"Error: User with ID {user_id} not found.")
                return
            user_email, user_name = user_record
    except Exception as e:
        print(f"Database error fetching user info: {e}")
        return
    finally:
        conn.close()

    # 2. Get recommendations using the refactored service function
    print(f"Generating top {count} recommendations for {user_email}...")
    recommendations = get_recommendations_for_user(user_id, top_k=count)

    if not recommendations:
        print("No suitable recommendations found for this user. No email will be sent.")
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