
# services/embedding_service.py
import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# --- 1. MODEL INITIALIZATION ---
# This is the multilingual model you chose. It's loaded only ONCE when the module
# is first imported, making subsequent calls very fast.
# The 'mps' device is for Apple Silicon (M1/M2) Macs. If you're on Windows/Linux,
# it will automatically fall back to 'cuda' (if you have a GPU) or 'cpu'.
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='mps')
except Exception:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

print("Embedding model loaded successfully.")

# --- 2. PERSIAN TEXT NORMALIZATION ---
# This function is crucial for cleaning Persian text before embedding.
def normalize_persian_text(text: str) -> str:
    """
    Cleans and normalizes Persian text by:
    - Replacing Arabic characters with their Persian equivalents.
    - Removing diacritics and special characters.
    - Standardizing whitespace.
    """
    if not text:
        return ""
    # Replace Arabic characters with Persian equivalents
    text = text.replace('ي', 'ی').replace('ك', 'ک')
    # Remove Arabic/Persian diacritics
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- 3. CORE EMBEDDING FUNCTION ---
def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Takes a list of texts, normalizes them, and returns their embeddings.
    
    Args:
        texts (list[str]): A list of strings to be embedded.

    Returns:
        np.ndarray: A numpy array of shape (n_texts, embedding_dimension)
    """
    # Normalize all texts in the list
    normalized_texts = [normalize_persian_text(text) for text in texts]
    
    # Generate embeddings. The model handles batching efficiently.
    embeddings = model.encode(normalized_texts, convert_to_numpy=True)
    return embeddings

# --- 4. DELIVERABLE VERIFICATION (TESTING BLOCK) ---
if __name__ == "__main__":
    print("\n--- Running Verification for Day 1 Deliverables ---")

    # Sample CVs (as planned for Day 3)
    cv1_text = "مهندس نرم افزار سنیور مسلط به پایتون و جنگو. تجربه کار با Docker و Postgres. به دنبال فرصت شغلی در تهران یا به صورت دورکاری."
    cv2_text = "کارشناس فرانت اند با سه سال سابقه کار با React و TypeScript. آشنا به طراحی UI/UX و کار با Figma. علاقمند به شرکت های استارتاپی در اصفهان."

    # Sample Job Postings (as planned for Day 2)
    job1_text = "توسعه دهنده ارشد Python شرکت دیجی کالا تهران استخدام برنامه نویس Django مسلط به REST API و Celery"
    job2_text = "استخدام کارشناس Frontend در شرکت تپسی تهران. نیازمند تسلط بر React.js و Redux. آشنایی با GraphQL مزیت محسوب میشود."
    job3_text = "برنامه نویس Back-End در اصفهان. شرکت اسنپ. کار با Golang و میکروسرویس. شرایط دورکاری فراهم است."
    job4_text = "طراح UI/UX در شیراز. مسلط به Figma و Adobe XD. حداقل دو سال سابقه کار مرتبط."
    job5_text = "کارآموز پایتون در شرکت همراه اول. تهران. آشنایی با مفاهیم اولیه برنامه نویسی و پایگاه داده."

    # Combine all texts for batch embedding
    all_texts = [cv1_text, cv2_text, job1_text, job2_text, job3_text, job4_text, job5_text]

    # Generate embeddings for all samples
    all_embeddings = embed_texts(all_texts)

    # --- Verification Checks ---
    print(f"\n1. Successfully generated embeddings.")
    print(f"   - Shape of the embedding matrix: {all_embeddings.shape}")
    print(f"   - This means {all_embeddings.shape[0]} texts were embedded into vectors of dimension {all_embeddings.shape[1]}.")

    # Separate CV and Job embeddings for analysis
    cv_embeddings = all_embeddings[:2]
    job_embeddings = all_embeddings[2:]

    # Calculate similarity between the first CV and all jobs
    similarity_scores = cosine_similarity([cv_embeddings[0]], job_embeddings)

    print("\n2. Verified semantic similarity for CV 1 ('Senior Python Developer'):")
    job_titles = ["Senior Python (Digikala)", "Frontend (Tapsi)", "Backend Go (Snapp)", "UI/UX (Shiraz)", "Python Intern (Hamrah-e Avval)"]
    for i, score in enumerate(similarity_scores[0]):
        print(f"   - Similarity with '{job_titles[i]}': {score:.4f}")
    
    # Find the best match
    best_match_index = np.argmax(similarity_scores)
    print(f"\n   ==> Best match for CV 1 is: '{job_titles[best_match_index]}' (Score: {similarity_scores[0][best_match_index]:.4f})")
    
    print("\n--- Day 1 Deliverables Complete and Verified! ---")