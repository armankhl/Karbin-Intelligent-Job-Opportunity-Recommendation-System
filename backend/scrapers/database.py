# scrapers/database.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# --- NEW: In-memory cache for category names to IDs ---
_category_map = None

def get_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Could not connect to the database: {e}")
        return None

def _load_category_map(cursor):
    """
    Loads all categories from the DB into a dictionary for fast lookups.
    This is called once per script run.
    """
    global _category_map
    print("Loading category map from database...")
    cursor.execute("SELECT name, id FROM categories")
    # Creates a dictionary like: {'وب، برنامه‌نویسی و نرم‌افزار': 2, ...}
    _category_map = {name: cat_id for name, cat_id in cursor.fetchall()}
    print(f"Category map loaded with {len(_category_map)} entries.")

def get_or_create(cursor, table, column, value):
    """Gets the ID of a record or creates it if it doesn't exist."""
    cursor.execute(f"SELECT id FROM {table} WHERE {column} = %s", (value,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute(f"INSERT INTO {table} ({column}) VALUES (%s) RETURNING id", (value,))
        return cursor.fetchone()[0]

def save_job_posting(job_data):
    """Saves a complete job posting to the database, including category_id mapping."""
    conn = get_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # --- THE CORE CHANGE IS HERE ---
            # 1. Load the category map if it hasn't been loaded yet.
            global _category_map
            if _category_map is None:
                _load_category_map(cursor)

            # 2. Look up the category_id from the scraped category name.
            category_name = job_data.get('category', '').strip()
            category_id = _category_map.get(category_name)
            
            if category_name and not category_id:
                print(f"Warning: Scraped category '{category_name}' not found in the database. It will be saved as NULL.")

            # 3. Get or create company
            company_id = get_or_create(cursor, 'companies', 'name', job_data['company_name'])

            # 4. Insert the job posting with the new category_id field.
            # The old 'category' text field has been removed from this query.
            sql = """
                INSERT INTO job_postings (
                    source_site, source_id, source_link, title, company_id, city, province,
                    job_description, contract_type, salary, minimum_experience,
                    minimum_education, gender, military_service_status,
                    is_full_time, is_part_time, is_remote, is_internship, category_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_link) DO NOTHING;
            """
            cursor.execute(sql, (
                'jobinja.ir', job_data['job_id'], job_data['link'], job_data['title'], company_id, job_data.get('city'),
                job_data.get('province'), job_data.get('job_description'), job_data.get('contract_type'),
                job_data.get('salary'), job_data.get('minimum_experience'), job_data.get('minimum_education'),
                job_data.get('gender'), job_data.get('military_service_status'),
                job_data.get('is_full_time', False), job_data.get('is_part_time', False),
                job_data.get('is_remote', False), job_data.get('is_internship', False),
                category_id # Use the looked-up integer ID
            ))

            # 3. Handle skills
            if job_data.get('skills'):
                for skill_name in job_data['skills'].split('|'):
                    skill_id = get_or_create(cursor, 'skills', 'name', skill_name.strip())
                    cursor.execute("INSERT INTO job_skill (job_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (job_id, skill_id))

            # 4. Handle languages
            if job_data.get('languages'):
                 for lang_name in job_data['languages'].split('|'):
                    lang_id = get_or_create(cursor, 'languages', 'name', lang_name.strip())
                    cursor.execute("INSERT INTO job_language (job_id, language_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (job_id, lang_id))

            conn.commit()
            print(f"Successfully processed job: {job_data['title']}")

    except Exception as e:
        print(f"Failed to save job {job_data.get('link')}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()