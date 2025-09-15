import os
import psycopg2
import numpy as np
import math
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# --- 1. IMPORTS FROM OUR PROJECT ---
# We import the core recommendation logic and the loaded ML artifacts
from services.recommendation_service import (
    get_recommendations_for_user,
    faiss_index,
    job_id_to_faiss_idx
)

# --- 2. CONFIGURATION ---
load_dotenv()

# Define the user personas we want to evaluate
PERSONA_USER_IDS = [1, 5, 10]
RECOMMENDATIONS_TO_EVALUATE = 10 # Generate 10 to get a good diversity score
RECOMMENDATIONS_TO_DISPLAY = 5  # But only display the top 5 in the report

# --- 3. DATABASE HELPER ---
def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    except psycopg2.OperationalError as e:
        print(f"FATAL: Could not connect to the database: {e}")
        return None

# --- 4. METRIC IMPLEMENTATION ---

def get_job_popularity_map() -> dict:
    """
    Calculates a popularity score for each job.
    Proxy for popularity: The number of users who have at least one skill required by the job.
    A lower number means the job is more niche/less popular.
    """
    conn = get_db_connection()
    if not conn: return {}
    
    popularity_counts = {}
    try:
        with conn.cursor() as cur:
            # This query counts, for each job, how many distinct users share at least one skill.
            cur.execute("""
                SELECT js.job_id, COUNT(DISTINCT us.user_id)
                FROM job_skill js
                JOIN user_skills us ON js.skill_id = us.skill_id
                GROUP BY js.job_id;
            """)
            
            for job_id, count in cur.fetchall():
                popularity_counts[job_id] = count
            
            # Normalize the counts to be probabilities
            total_users = list(popularity_counts.values())
            max_popularity = max(total_users) if total_users else 1
            
            return {job_id: count / max_popularity for job_id, count in popularity_counts.items()}

    except Exception as e:
        print(f"Error calculating job popularity: {e}")
        return {}
    finally:
        if conn: conn.close()


def calculate_diversity(recommended_job_vectors: np.ndarray) -> float:
    """
    Calculates the diversity of a list of recommended items.
    Diversity = 1 - Intra-List Similarity (ILS).
    Score Range: 0 (all items are identical) to 1 (all items are completely different).
    """
    if recommended_job_vectors.shape[0] < 2:
        return 1.0 # Perfect diversity for a single item

    # Calculate cosine similarity between all pairs of item vectors in the list
    similarity_matrix = cosine_similarity(recommended_job_vectors)
    
    # Get the upper triangle of the matrix, excluding the diagonal (which is always 1)
    upper_triangle_indices = np.triu_indices_from(similarity_matrix, k=1)
    intra_list_similarity = np.mean(similarity_matrix[upper_triangle_indices])
    
    diversity = 1 - intra_list_similarity
    return float(diversity)

def calculate_novelty(recommended_job_ids: list[int], popularity_map: dict) -> float:
    """
    Calculates the average novelty of a list of recommended items.
    Novelty(i) = -log2(popularity(i)). A lower popularity means higher novelty.
    """

    if not recommended_job_ids:
        return 0.0

    total_novelty = 0
    for job_id in recommended_job_ids:
        popularity = popularity_map.get(job_id, 0.99)
        if popularity == 0: popularity = 0.00001
        total_novelty += -math.log2(popularity)
        
    return total_novelty / len(recommended_job_ids)

# --- 5. MAIN EVALUATION SCRIPT (REVISED) ---
def main():
    print("--- Starting Research Evaluation Script ---")

    if faiss_index is None:
        print("FATAL: FAISS index not loaded. Exiting.")
        return
        
    print("Pre-calculating job popularity map...")
    job_popularity_map = get_job_popularity_map()
    
    conn = get_db_connection()
    if not conn: return
    
    for user_id in PERSONA_USER_IDS:
        print("\n" + "="*50)
        print(f" EVALUATING PERSONA: USER ID {user_id} ")
        print("="*50)

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT first_name, last_name, professional_title FROM user_profiles WHERE user_id = %s", (user_id,))
                user_info = cur.fetchone()
                if not user_info:
                    print(f"SKIPPING: No profile found for user_id {user_id}.")
                    continue
                
                print(f"Persona Profile: {user_info[0] or ''} {user_info[1] or ''} - {user_info[2] or ''}")

            # Run the recommendation pipeline
            recommendations = get_recommendations_for_user(user_id, top_k=RECOMMENDATIONS_TO_EVALUATE)
            
            # --- FIX IS HERE: Gracefully handle the "no recommendations" case ---
            if not recommendations:
                print("\n--- Top 5 Recommendations ---")
                print("  No recommendations were generated for this user based on the current filters.")
                print("\n--- Evaluation Metrics ---")
                print("  Metrics cannot be calculated for an empty list.")
                continue # Move to the next persona

            # --- FIX IS HERE: Use the correct key 'id' instead of 'job_id' ---
            recommended_job_ids = [rec['id'] for rec in recommendations]
            
            # Reconstruct vectors for metric calculations
            rec_faiss_indices = [job_id_to_faiss_idx[job_id] for job_id in recommended_job_ids if job_id in job_id_to_faiss_idx]
            
            # Another check to ensure we have vectors before calculating diversity
            if not rec_faiss_indices:
                print("Warning: Could not find vectors for recommended jobs. Skipping metrics.")
                continue

            recommended_vectors = faiss_index.reconstruct_batch(np.array(rec_faiss_indices, dtype=np.int64))
            
            # Calculate metrics
            diversity_score = calculate_diversity(recommended_vectors)
            novelty_score = calculate_novelty(recommended_job_ids, job_popularity_map)
            
            # Print the report
            print("\n--- Top 5 Recommendations ---")
            for i, rec in enumerate(recommendations[:RECOMMENDATIONS_TO_DISPLAY]):
                # Use the correct key 'id' here as well for consistency, although 'job_id' wasn't used here before
                matched_skills = rec.get('reason', {}).get('matched_skills', [])
                reason_str = f"Matches skills: {', '.join(matched_skills)}" if matched_skills else "Strong profile match"
                print(f"  {i+1}. {rec['title']} @ {rec['company_name']} (Score: {rec['score']:.2f})")
                print(f"     Reason: {reason_str}")

            print("\n--- Evaluation Metrics ---")
            print(f"  Diversity Score: {diversity_score:.4f} (0=similar, 1=diverse)")
            print(f"  Novelty Score:   {novelty_score:.4f} (higher is better)")
            
        except Exception as e:
            print(f"An unexpected error occurred while evaluating user {user_id}: {e}")
            import traceback
            traceback.print_exc() # This will give a more detailed error message if something else is wrong
            
    conn.close()
    print("\n--- Evaluation Complete ---")

if __name__ == "__main__":
    main()