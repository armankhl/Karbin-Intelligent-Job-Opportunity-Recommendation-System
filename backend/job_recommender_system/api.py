from flask_jwt_extended import jwt_required, get_jwt_identity

@app.route('/api/recommendations', methods=['GET'])
@jwt_required()
def get_recommendations():
    """
    Generates personalized job recommendations for the logged-in user.
    """
    # --- Step 0: Check if the recommendation engine is ready ---
    if faiss_index is None or job_id_map is None:
        return jsonify({"error": "Recommendation service is not available"}), 503

    # --- Step 1: Get User Info and Parameters ---
    user_id = get_jwt_identity() # Get user_id securely from JWT token
    top_k = request.args.get('top_k', default=10, type=int)

    # --- Step 2: Generate User Vector ---
    user_vector = get_user_vector(user_id)
    if user_vector is None:
        return jsonify({"message": "Your profile is not complete enough for recommendations."}), 200

    # FAISS requires a 2D array for searching
    user_vector = np.array([user_vector]).astype('float32')
    faiss.normalize_L2(user_vector) # Normalize the user vector just like we did for jobs

    # --- Step 3: Perform Two-Stage Retrieval ---
    # Stage 1: Fast, semantic search with FAISS for a large candidate pool (e.g., top 200)
    CANDIDATE_POOL_SIZE = 200
    distances, faiss_indices = faiss_index.search(user_vector, CANDIDATE_POOL_SIZE)
    
    # Get the database job IDs and their similarity scores from the FAISS results
    semantic_matches = {}
    for i, idx in enumerate(faiss_indices[0]):
        if idx != -1: # FAISS returns -1 for empty results
            db_job_id = job_id_map[idx]
            similarity_score = float(distances[0][i])
            semantic_matches[db_job_id] = similarity_score

    # Stage 2: Apply hard filters to the semantically similar candidates
    candidate_job_ids_set = set(get_filtered_job_ids(user_id))
    
    final_recommendations = []
    for job_id, score in semantic_matches.items():
        if job_id in candidate_job_ids_set:
            final_recommendations.append({"job_id": int(job_id), "score": score})

    # Sort by score and take the top_k results
    final_recommendations = sorted(final_recommendations, key=lambda x: x['score'], reverse=True)[:top_k]
    
    if not final_recommendations:
        return jsonify([]), 200

    # --- Step 4: Fetch Full Job Details from Database ---
    recommended_job_ids = [rec['job_id'] for rec in final_recommendations]
    scores_map = {rec['job_id']: rec['score'] for rec in final_recommendations}
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            sql_query = """
                SELECT jp.id, jp.title, c.name AS company_name, jp.city
                FROM job_postings jp
                JOIN companies c ON jp.company_id = c.id
                WHERE jp.id = ANY(%s)
            """
            cur.execute(sql_query, (recommended_job_ids,))
            jobs_data = cur.fetchall()
            
            # Create a dictionary for easy lookup
            jobs_dict = {job[0]: {"id": job[0], "title": job[1], "company_name": job[2], "city": job[3]} for job in jobs_data}

            # Add score to the final result, preserving the order
            results = []
            for job_id in recommended_job_ids:
                if job_id in jobs_dict:
                    job_info = jobs_dict[job_id]
                    job_info['score'] = scores_map[job_id]
                    # We will add the "reason" in Day 6, for now it's a placeholder
                    job_info['reason'] = "Strong semantic match" 
                    results.append(job_info)

    except Exception as e:
        print(f"Database error fetching final recommendations: {e}")
        return jsonify({"error": "Could not retrieve job details"}), 500
    finally:
        conn.close()

    return jsonify(results)