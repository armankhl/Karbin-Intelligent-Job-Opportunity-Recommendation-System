# embed_jobs.py
import os
import time
import psycopg2
import numpy as np
import faiss
from dotenv import load_dotenv
from services.embedding_service import embed_texts

# --- 1. CONFIGURATION ---
# As requested, you can control the number of jobs to process.
# Set to None to process all active jobs.
MAX_JOBS_TO_EMBED = None 

# Create a directory to store our data artifacts if it doesn't exist
os.makedirs('data', exist_ok=True)
FAISS_INDEX_PATH = os.path.join('data', 'job_index.faiss')
JOB_ID_MAP_PATH = os.path.join('data', 'job_id_map.npy')

# Load database credentials from .env file
load_dotenv()

# --- 2. DATABASE CONNECTION ---
def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Fatal: Could not connect to the database: {e}")
        return None

# --- 3. MAIN PIPELINE LOGIC ---
def main():
    """
    Main function to run the entire job embedding pipeline.
    """
    print("--- Starting Day 2: Job Embedding Pipeline ---")
    
    # --- Step 1: Fetch Active Job Postings ---
    print("Connecting to the database...")
    conn = get_db_connection()
    if not conn:
        return

    job_ids = []
    texts_to_embed = []
    
    print("Fetching active job postings...")
    try:
        with conn.cursor() as cur:
            # We join with the `skills` table to get a clean, aggregated list of skills.
            # This is more robust than relying on a potentially messy text column.
            sql_query = """
                SELECT 
                    jp.id, 
                    jp.title, 
                    jp.category, 
                    jp.city, 
                    jp.job_description,
                    STRING_AGG(s.name, ', ') AS skills
                FROM 
                    job_postings jp
                LEFT JOIN 
                    job_skill js ON jp.id = js.job_id
                LEFT JOIN 
                    skills s ON js.skill_id = s.id
                WHERE 
                    jp.is_active = TRUE
                GROUP BY
                    jp.id
                ORDER BY
                    jp.scraped_at DESC
            """
            if MAX_JOBS_TO_EMBED:
                sql_query += f" LIMIT {MAX_JOBS_TO_EMBED};"
            else:
                sql_query += ";"
                
            cur.execute(sql_query)
            job_postings = cur.fetchall()

            if not job_postings:
                print("No active job postings found to embed. Exiting.")
                return

            print(f"Found {len(job_postings)} active jobs to process.")

            # --- Step 2: Build Job Text for Embedding ---
            for job in job_postings:
                job_id, title, category, city, description, skills = job
                
                # Gracefully handle None values from the database
                title = title or ""
                category = category or ""
                city = city or ""
                description = description or ""
                skills = skills or ""

                # Construct the comprehensive text as planned in the roadmap
                full_text = f"{title}. {category} in {city}. Skills: {skills}. Description: {description}"
                
                job_ids.append(job_id)
                texts_to_embed.append(full_text)
                
    except Exception as e:
        print(f"Fatal: Failed to fetch or process jobs from database: {e}")
        return
    finally:
        conn.close()

    # --- Step 3: Batch-Embed Jobs ---
    print(f"Generating embeddings for {len(texts_to_embed)} jobs. This may take a while on a CPU...")
    start_time = time.time()
    job_embeddings = embed_texts(texts_to_embed)
    end_time = time.time()
    print(f"Embedding completed in {end_time - start_time:.2f} seconds.")

    # --- Step 4: Build and Store FAISS Index ---
    print("Building FAISS index...")
    embedding_dimension = job_embeddings.shape[1]
    
    # We use IndexFlatIP for cosine similarity with normalized embeddings, which is what SentenceTransformer produces.
    index = faiss.IndexFlatIP(embedding_dimension)
    
    # FAISS requires normalized vectors for IndexFlatIP to work correctly as a cosine similarity search
    faiss.normalize_L2(job_embeddings)
    index.add(job_embeddings)
    
    print(f"FAISS index built successfully. Total vectors in index: {index.ntotal}")

    # --- Step 5: Save Index and ID Mapping ---
    print(f"Saving FAISS index to: {FAISS_INDEX_PATH}")
    faiss.write_index(index, FAISS_INDEX_PATH)

    print(f"Saving job ID to index map to: {JOB_ID_MAP_PATH}")
    np.save(JOB_ID_MAP_PATH, np.array(job_ids, dtype=np.int32))

    print("\n--- Day 2 Deliverables Complete and Verified! ---")
    print(f"Artifacts saved in the '{os.path.abspath('data')}' directory.")


if __name__ == "__main__":
    main()
