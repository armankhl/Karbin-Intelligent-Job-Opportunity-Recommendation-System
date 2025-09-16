import os
import psycopg2
import numpy as np
import math
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# --- 1. IMPORTS & CONFIGURATION ---
from services.recommendation_service import get_recommendations_for_user, faiss_index, job_id_to_faiss_idx

load_dotenv()
PERSONA_USER_IDS = [1, 10, 11]
CANDIDATES_FOR_RERANKING = 50
RECOMMENDATIONS_TO_EVALUATE = 10
RECOMMENDATIONS_TO_DISPLAY = 5
GROUND_TRUTH_SKILL_OVERLAP_THRESHOLD = 1

# --- 2. DATABASE & METRIC FUNCTIONS ---

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

# --- NEW: Ground Truth and Information Retrieval Metrics ---
def get_ground_truth(user_id: int, relevance_threshold: int) -> set:
    """
    Creates a "ground truth" set of job IDs that are considered highly relevant
    to the user based on a skill overlap threshold.
    """
    conn = get_db_connection()
    if not conn: return set()
    
    ground_truth_ids = set()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                WITH user_skill_set AS (
                    SELECT skill_id FROM user_skills WHERE user_id = %s
                ),
                job_skill_counts AS (
                    SELECT js.job_id, count(js.skill_id) as matching_skills
                    FROM job_skill js
                    WHERE js.skill_id IN (SELECT skill_id FROM user_skill_set)
                    GROUP BY js.job_id
                )
                SELECT job_id FROM job_skill_counts WHERE matching_skills >= %s;
            """, (user_id, relevance_threshold))
            ground_truth_ids = {row[0] for row in cur.fetchall()}
    except Exception as e:
        print(f"Error getting ground truth for user {user_id}: {e}")
    finally:
        if conn: conn.close()
    return ground_truth_ids

def calculate_precision_at_k(recommended_ids: list[int], ground_truth_ids: set) -> float:
    """Calculates Precision@K."""
    if not recommended_ids: return 0.0
    k = len(recommended_ids)
    relevant_in_recommendations = len(set(recommended_ids).intersection(ground_truth_ids))
    return relevant_in_recommendations / k

def calculate_recall_at_k(recommended_ids: list[int], ground_truth_ids: set) -> float:
    """Calculates Recall@K."""
    if not ground_truth_ids: return 0.0 # Cannot calculate recall if there are no relevant items
    relevant_in_recommendations = len(set(recommended_ids).intersection(ground_truth_ids))
    return relevant_in_recommendations / len(ground_truth_ids)

# --- 3. REVISED EVALUATION PIPELINE ---
def evaluate_persona(user_id: int, job_popularity_map: dict, ground_truth_ids: set, use_reranker: bool):
    """
    A helper function to run the full evaluation pipeline for a single mode.
    """
    print(f"\n-> Running pipeline with Cross-Encoder Re-ranking: {'ENABLED' if use_reranker else 'DISABLED'}")
    
    recommendations = get_recommendations_for_user(
        user_id,
        top_k=RECOMMENDATIONS_TO_EVALUATE,
        retrieval_k=CANDIDATES_FOR_RERANKING,
        use_reranker=use_reranker
    )
    
    results = {
        "recommendations": recommendations, "precision": "N/A", "recall": "N/A",
        "diversity": "N/A", "novelty": "N/A", "serendipity": "N/A"
    }

    if not recommendations:
        print("   - No recommendations generated in this mode.")
        return results

    recommended_ids = [rec['id'] for rec in recommendations]
    
    # Calculate Precision and Recall
    results["precision"] = calculate_precision_at_k(recommended_ids, ground_truth_ids)
    results["recall"] = calculate_recall_at_k(recommended_ids, ground_truth_ids)
    
    rec_faiss_indices = [job_id_to_faiss_idx[job_id] for job_id in recommended_ids if job_id in job_id_to_faiss_idx]
    
    if rec_faiss_indices:
        recommended_vectors = faiss_index.reconstruct_batch(np.array(rec_faiss_indices, dtype=np.int64))
        results["diversity"] = calculate_diversity(recommended_vectors)
        results["novelty"] = calculate_novelty(recommended_ids, job_popularity_map)
        
    return results

# --- 4. REVISED MAIN SCRIPT ---
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

            # --- NEW: Get ground truth for this persona ONCE ---
            print(f"Generating ground truth for user {user_id} (threshold: {GROUND_TRUTH_SKILL_OVERLAP_THRESHOLD} skills)...")
            ground_truth_ids = get_ground_truth(user_id, GROUND_TRUTH_SKILL_OVERLAP_THRESHOLD)
            print(f"   - Found {len(ground_truth_ids)} highly relevant jobs for this user.")

            # --- Run both evaluation modes ---
            bi_encoder_results = evaluate_persona(user_id, job_popularity_map, ground_truth_ids, use_reranker=False)
            cross_encoder_results = evaluate_persona(user_id, job_popularity_map, ground_truth_ids, use_reranker=True)

            # --- REVISED: Print the comparative report with new metrics ---
            print("\n--- Comparative Report ---")
            report_data = {
                "Metric": ["Precision@10", "Recall@10", "Diversity", "Novelty"],
                "Bi-Encoder Only": [
                    f"{bi_encoder_results['precision']:.2%}" if isinstance(bi_encoder_results['precision'], float) else "N/A",
                    f"{bi_encoder_results['recall']:.2%}" if isinstance(bi_encoder_results['recall'], float) else "N/A",
                    f"{bi_encoder_results['diversity']:.4f}" if isinstance(bi_encoder_results['diversity'], float) else "N/A",
                    f"{bi_encoder_results['novelty']:.4f}" if isinstance(bi_encoder_results['novelty'], float) else "N/A",
                ],
                "Bi + Cross-Encoder": [
                    f"{cross_encoder_results['precision']:.2%}" if isinstance(cross_encoder_results['precision'], float) else "N/A",
                    f"{cross_encoder_results['recall']:.2%}" if isinstance(cross_encoder_results['recall'], float) else "N/A",
                    f"{cross_encoder_results['diversity']:.4f}" if isinstance(cross_encoder_results['diversity'], float) else "N/A",
                    f"{cross_encoder_results['novelty']:.4f}" if isinstance(cross_encoder_results['novelty'], float) else "N/A",
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
    
    print("\n--- Evaluation Complete ---")

if __name__ == "__main__":
    main()
