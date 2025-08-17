# scrapers/database.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
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
        print(f"Could not connect to the database: {e}")
        return None

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
    """Saves a complete job posting to the database."""
    conn = get_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # 1. Get or create company
            company_id = get_or_create(cursor, 'companies', 'name', job_data['company_name'])

            # 2. Insert the job posting
            sql = """
                INSERT INTO job_postings (source_site, source_id, source_link, title, company_id, city,
                                          job_description, category, contract_type, salary, minimum_experience,
                                          minimum_education, gender, military_service_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_link) DO NOTHING
                RETURNING id;
            """
            cursor.execute(sql, (
                'jobinja.ir', job_data['job_id'], job_data['link'], job_data['title'], company_id, job_data['city'],
                job_data.get('job_description'), job_data.get('category'), job_data.get('contract_type'),
                job_data.get('salary'), job_data.get('minimum_experience'), job_data.get('minimum_education'),
                job_data.get('gender'), job_data.get('military_service')
            ))

            job_id = cursor.fetchone()
            if not job_id:
                print(f"Job at {job_data['link']} already exists. Skipping.")
                return

            job_id = job_id[0]

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
            print(f"Successfully saved job: {job_data['title']}")

    except Exception as e:
        print(f"Failed to save job {job_data.get('link')}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()