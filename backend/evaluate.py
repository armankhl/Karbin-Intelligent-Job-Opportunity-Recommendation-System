import os
import psycopg2
import numpy as np
import math
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd 

# --- 1. IMPORTS FROM OUR PROJECT ---
from services.recommendation_service import (
    get_recommendations_for_user,
    faiss_index,
    job_id_to_faiss_idx
)

# --- 2. CONFIGURATION ---
load_dotenv()
PERSONA_USER_IDS = [1, 5, 10]
CANDIDATES_FOR_RERANKING = 50
RECOMMENDATIONS_TO_EVALUATE = 10
RECOMMENDATIONS_TO_DISPLAY = 5


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


# --- NEW: Serendipity Metric ---
def calculate_serendipity(recommendations: list[dict], user_id: int) -> float:
    """
    Calculates the average serendipity of a list of recommended items.
    Serendipity = A measure of how "unexpectedly useful" an item is.
    We'll define it as items that are highly relevant but not obvious from the user's direct skills.
    """
    conn = get_db_connection()
    if not conn or not recommendations: return 0.0

    total_serendipity = 0
    try:
        with conn.cursor() as cur:
            # 1. Get the user's explicitly listed skills
            cur.execute("SELECT skill_id FROM user_skills WHERE user_id = %s", (user_id,))
            user_skill_ids = {row[0] for row in cur.fetchall()}
            
            # 2. Get the skills for all recommended jobs
            recommended_ids = [rec['id'] for rec in recommendations]
            cur.execute("SELECT job_id, skill_id FROM job_skill WHERE job_id = ANY(%s)", (recommended_ids,))
            
            job_skills_map = {job_id: set() for job_id in recommended_ids}
            for job_id, skill_id in cur.fetchall():
                job_skills_map[job_id].add(skill_id)

            # 3. Calculate serendipity for each item
            for rec in recommendations:
                job_id = rec['id']
                relevance_score = rec['score'] # The score from our recommender
                job_skills = job_skills_map.get(job_id, set())
                
                # An item is "obvious" if any of its required skills are in the user's skill set
                is_obvious = len(user_skill_ids.intersection(job_skills)) > 0
                
                # Serendipity is high if the item is relevant but not obvious
                if not is_obvious and relevance_score > 0.5: # Using 0.5 as a relevance threshold
                    total_serendipity += relevance_score
                
    except Exception as e:
        print(f"Error calculating serendipity: {e}")
    finally:
        if conn: conn.close()
        
    return total_serendipity / len(recommendations) if recommendations else 0.0

# --- 4. MAIN EVALUATION SCRIPT (REVISED FOR A/B TESTING) ---
def evaluate_persona(user_id: int, job_popularity_map: dict, use_reranker: bool):
    """
    A helper function to run the full evaluation pipeline for a single mode.
    Returns a dictionary with the results and calculated metrics.
    """
    print(f"\n-> Running pipeline with Cross-Encoder Re-ranking: {'ENABLED' if use_reranker else 'DISABLED'}")
    
    # 1. Run the recommendation pipeline
    recommendations = get_recommendations_for_user(
        user_id,
        top_k=RECOMMENDATIONS_TO_EVALUATE,
        retrieval_k=CANDIDATES_FOR_RERANKING,
        use_reranker=use_reranker
    )
    
    results = {
        "recommendations": recommendations,
        "diversity": "N/A",
        "novelty": "N/A",
        "serendipity": "N/A"
    }

    if not recommendations:
        print("   - No recommendations generated in this mode.")
        return results

    # 2. Prepare data for metric calculations
    recommended_job_ids = [rec['id'] for rec in recommendations]
    rec_faiss_indices = [job_id_to_faiss_idx[job_id] for job_id in recommended_job_ids if job_id in job_id_to_faiss_idx]
    
    if rec_faiss_indices:
        recommended_vectors = faiss_index.reconstruct_batch(np.array(rec_faiss_indices, dtype=np.int64))
        
        # 3. Calculate advanced metrics
        results["diversity"] = calculate_diversity(recommended_vectors)
        results["novelty"] = calculate_novelty(recommended_job_ids, job_popularity_map)
        results["serendipity"] = calculate_serendipity(recommendations, user_id)
        
    return results



def main():
    print("--- Starting A/B Evaluation Script: Bi-Encoder vs. Cross-Encoder ---")

    if faiss_index is None:
        print("FATAL: FAISS index not loaded. Cannot run evaluation. Exiting.")
        return
        
    print("Pre-calculating job popularity map...")
    job_popularity_map = get_job_popularity_map()
    
    conn = get_db_connection()
    if not conn: return
    
    for user_id in PERSONA_USER_IDS:
        print("\n" + "="*70)
        print(f" EVALUATING PERSONA: USER ID {user_id} ")
        print("="*70)

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT first_name, last_name, professional_title FROM user_profiles WHERE user_id = %s", (user_id,))
                user_info = cur.fetchone()
                if not user_info:
                    print(f"SKIPPING: No profile found for user_id {user_id}.")
                    continue
                print(f"Persona Profile: {user_info[0] or ''} {user_info[1] or ''} - {user_info[2] or 'N/A'}")

            # --- Run both evaluation modes ---
            bi_encoder_results = evaluate_persona(user_id, job_popularity_map, use_reranker=False)
            cross_encoder_results = evaluate_persona(user_id, job_popularity_map, use_reranker=True)

            # --- Print the comparative report ---
            print("\n--- Comparative Report ---")
            
            # Create a DataFrame for clean, aligned printing
            report_data = {
                "Metric": ["Diversity", "Novelty", "Serendipity"],
                "Bi-Encoder Only": [
                    f"{bi_encoder_results['diversity']:.4f}" if isinstance(bi_encoder_results['diversity'], float) else "N/A",
                    f"{bi_encoder_results['novelty']:.4f}" if isinstance(bi_encoder_results['novelty'], float) else "N/A",
                    f"{bi_encoder_results['serendipity']:.4f}" if isinstance(bi_encoder_results['serendipity'], float) else "N/A"
                ],
                "Bi + Cross-Encoder": [
                    f"{cross_encoder_results['diversity']:.4f}" if isinstance(cross_encoder_results['diversity'], float) else "N/A",
                    f"{cross_encoder_results['novelty']:.4f}" if isinstance(cross_encoder_results['novelty'], float) else "N/A",
                    f"{cross_encoder_results['serendipity']:.4f}" if isinstance(cross_encoder_results['serendipity'], float) else "N/A"
                ]
            }
            df = pd.DataFrame(report_data)
            print(df.to_string(index=False))

            print("\n--- Top 5 Recommendations (Bi-Encoder Only) ---")
            if bi_encoder_results["recommendations"]:
                for i, rec in enumerate(bi_encoder_results["recommendations"][:RECOMMENDATIONS_TO_DISPLAY]):
                    print(f"  {i+1}. {rec['title']} (Score: {rec['score']:.2f})")
            else:
                print("  No recommendations.")

            print("\n--- Top 5 Recommendations (Bi + Cross-Encoder) ---")
            if cross_encoder_results["recommendations"]:
                for i, rec in enumerate(cross_encoder_results["recommendations"][:RECOMMENDATIONS_TO_DISPLAY]):
                    print(f"  {i+1}. {rec['title']} (Score: {rec['score']:.2f})")
            else:
                print("  No recommendations.")

        except Exception as e:
            print(f"An error occurred while evaluating user {user_id}: {e}")
            
    if conn: conn.close()
    print("\n--- Evaluation Complete ---")

if __name__ == "__main__":
    main()