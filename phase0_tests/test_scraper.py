import requests
from bs4 import BeautifulSoup

def scrape_job_titles(url):
    """
    A simple web scraper to fetch job titles from a given URL.
    This function simulates fetching job data.
    """
    print(f"--- Scraping Job Titles from: {url} ---")
    try:
        # Send a request to the URL
        response = requests.get(url, timeout=10)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all job titles. We assume they are in <h2> tags with class 'job-title'
        # This is a hypothetical structure. You'll need to inspect real websites.
        job_titles = soup.find_all('h2', class_='job-title')

        if not job_titles:
            print("No job titles found with the specified selector.")
            return

        print("Successfully found job titles:")
        for i, title in enumerate(job_titles):
            # .strip() removes any leading/trailing whitespace
            print(f"{i+1}. {title.get_text().strip()}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # We will use a public test site that is designed for scraping practice.
    # It contains a list of fake job postings.
    test_url = "https://realpython.github.io/fake-jobs/"
    scrape_job_titles(test_url)