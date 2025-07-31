
# run_scraper.py
import os
from dotenv import load_dotenv
from scrapers.jobinja_scraper import JobinjaScraper

# Load environment variables from .env file
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment variables
    email = os.getenv("JOBINJA_EMAIL")
    password = os.getenv("JOBINJA_PASSWORD")
    proxy = os.getenv("PROXY_SERVER")
    headless = os.getenv("HEADLESS_MODE", 'True').lower() == 'true'

    if not email or not password:
        print("Error: JOBINJA_EMAIL and JOBINJA_PASSWORD must be set in the .env file.")
    else:
        scraper = JobinjaScraper(email=email, password=password, proxy=proxy, headless=headless)


        scraper.scrape(start_page=1, end_page=50)