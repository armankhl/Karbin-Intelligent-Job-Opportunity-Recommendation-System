from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def calculate_similarity():
    """
    Calculates the cosine similarity between a user profile and several job descriptions.
    This demonstrates the core logic of a content-based recommender.
    """
    print("--- Calculating Text Similarity ---")
    # --- Sample Data ---
    # The user's profile, summarized as a string of keywords
    user_profile = "python developer data science machine learning django"

    # A list of job descriptions
    job_descriptions = [
        "Senior Python Developer with experience in Django and REST APIs.", # High similarity
        "Data Scientist role, requires strong knowledge of machine learning and python.", # High similarity
        "Frontend Developer needed, expertise in React and JavaScript is a must.", # Low similarity
        "Project Manager for a software development team. Agile methodology." # Very low similarity
    ]

    # Combine the user profile and job descriptions into one list for vectorization
    documents = [user_profile] + job_descriptions

    # --- Vectorization (Text to Numbers) ---
    # Create a TF-IDF Vectorizer. This model converts text into numerical vectors.
    # TF-IDF stands for Term Frequency-Inverse Document Frequency.
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)

    # The first vector in the matrix is our user profile
    user_profile_vector = tfidf_matrix[0]

    # The rest are the job description vectors
    job_vectors = tfidf_matrix[1:]

    # --- Similarity Calculation ---
    # Calculate the cosine similarity between the user's profile vector and all job vectors
    similarity_scores = cosine_similarity(user_profile_vector, job_vectors)

    # --- Display Results ---
    print(f"User Profile: '{user_profile}'\n")
    for i, job in enumerate(job_descriptions):
        score = similarity_scores[0][i]
        print(f"Job: '{job}'")
        print(f"Similarity Score: {score:.4f}") # Format to 4 decimal places
        print("-" * 20)

if __name__ == "__main__":
    calculate_similarity()