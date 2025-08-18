
# run_scraper.py
import os
from dotenv import load_dotenv, find_dotenv
from .jobinja_scraper import JobinjaScraper

# Load environment variables from .env file
load_dotenv(find_dotenv())

if __name__ == "__main__":
    # Get configuration from environment variables
    email = os.getenv("JOBINJA_EMAIL")
    password = os.getenv("JOBINJA_PASSWORD")
    proxy = os.getenv("PROXY_SERVER")
    headless = os.getenv("HEADLESS_MODE", 'True').lower() == 'true'
    USE_HEADLESS_MODE = False 

if not email or not password:
    print("Error: JOBINJA_EMAIL and JOBINJA_PASSWORD must be set in the .env file.")
else:
    print(f"--- Starting Scraper ---")
    print(f"Headless Mode: {USE_HEADLESS_MODE}")
    print(f"Proxy Server: {proxy if proxy else 'Disabled'}")

    scraper = JobinjaScraper(
        email=email, 
        password=password, 
        proxy=proxy, 
        headless=USE_HEADLESS_MODE
    )
    
    # Scrape only 1 page and 5 jobs for a quick test
    scraper.scrape(start_page=2, end_page=2)