# scrapers/jobinja_scraper.py
import os
import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from .database import save_job_posting 
from .preprocessor import DataCleaner

# Use an absolute path for the driver for maximum portability
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_PATH = os.path.join(SCRIPT_DIR, "chromedriver.exe")

class JobinjaScraper:
    def __init__(self, email, password, proxy=None, headless=True):
        self.login_url = "https://jobinja.ir/login/user"
        self.jobs_path = "/jobs/latest-job-post-استخدامی-جدید"
        self.email = email
        self.password = password
        self.driver = self._setup_driver(proxy, headless)
        self.cleaner = DataCleaner() 
        logging.basicConfig(filename="scraper.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _setup_driver(self, proxy, headless):
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument('--disable-dev-shm-usage')
        if headless:
            options.add_argument("--headless=new")
        if proxy and proxy.lower() != 'none':
            options.add_argument(f'--proxy-server={proxy}')
        service = Service(executable_path=DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(45) # Increased timeout for slow pages
        return driver

    def login(self):
        """Logs into jobinja.ir using explicit waits for robustness."""
        print("Attempting to log in...")
        try:
            self.driver.get(self.login_url)
            wait = WebDriverWait(self.driver, 15)
            email_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#identifier")))
            email_field.send_keys(self.email)
            self.driver.find_element(By.CSS_SELECTOR, "#password").send_keys(self.password)
            self.driver.find_element(By.CSS_SELECTOR, "input[type=submit]").click()
            wait.until_not(EC.url_contains('/login'))
            print("Login successful.")
            logging.info("Login successful.")
            return True
        except TimeoutException:
            print("Login failed: Timed out waiting for login page or redirection.")
            self.driver.save_screenshot('login_error_screenshot.png')
            return False
        except Exception as e:
            print(f"An unexpected error occurred during login: {e}")
            return False
            
    def _sanitize_filename(self, filename):
        return re.sub(r'[^\w\-.]', '_', filename)
        
    def scrape(self, start_page=1, end_page=5):
        """
        Main scraping loop. It gets job links, scrapes raw details for each,
        cleans the data, and then saves it.
        """
        if not self.login():
            self.close()
            return
        
        print(f"Starting to scrape from page {start_page} to {end_page}...")
        for page_num in range(start_page, end_page + 1):
            list_url = f"https://jobinja.ir{self.jobs_path}?page={page_num}"
            print(f"\n--- Scraping page {page_num}: {list_url} ---")
            
            try:
                self.driver.get(list_url)
                wait = WebDriverWait(self.driver, 15)
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.c-jobListView__titleLink')))
                job_links = [a.get_attribute('href') for a in self.driver.find_elements(By.CSS_SELECTOR, 'a.c-jobListView__titleLink')]
            except TimeoutException:
                logging.warning(f"Could not find job links on page {page_num}. This might be the last page or a page with no results.")
                continue

            for link in job_links:
                try:
                    # Step 1: Scrape raw data from the page
                    raw_job_data = self.scrape_job_details(link)
                    
                    if raw_job_data:
                        # Step 2: Clean and standardize the raw data
                        cleaned_job_data = self.cleaner.preprocess_job_data(raw_job_data)
                        
                        # Step 3: Save the clean data to the database
                        save_job_posting(cleaned_job_data)
                except Exception as e:
                    logging.error(f"A critical error occurred while processing the link {link}: {e}", exc_info=True)
        
        self.close()

    def scrape_job_details(self, link: str) -> dict | None:
        """
        Scrapes raw text data from a single job page.
        This function's only responsibility is to extract information, not to clean it.
        """
        raw_data = {'link': link}
        
        try:
            # Use a more reliable regex for job ID extraction
            match = re.search(r'/jobs/([a-zA-Z0-9]+)/', link)
            raw_data['job_id'] = match.group(1) if match else self._sanitize_filename(link.split('/')[-1])

            self.driver.get(link)
            wait = WebDriverWait(self.driver, 15)
            
            # A simpler, more robust selector for the main title
            title_selector = (By.CSS_SELECTOR, "h1.c-jobView__title")
            wait.until(EC.presence_of_element_located(title_selector))
            
            raw_data['title'] = self.driver.find_element(*title_selector).text.strip()

            try:
                raw_data['company_name'] = self.driver.find_element(By.CSS_SELECTOR, ".c-companyHeader__name").text.strip()
            except NoSuchElementException:
                raw_data['company_name'] = "N/A"

            info_items = self.driver.find_elements(By.CSS_SELECTOR, ".c-infoBox__item")
            for item in info_items:
                try:
                    title = item.find_element(By.CSS_SELECTOR, '.c-infoBox__itemTitle').text.strip()
                    value_element = item.find_element(By.CSS_SELECTOR, '.tags')
                    
                    if 'دسته‌بندی شغلی' in title: raw_data['category'] = value_element.text.strip()
                    elif 'حداقل سابقه کار' in title: raw_data['minimum_experience'] = value_element.text.strip()
                    elif 'مهارت‌های مورد نیاز' in title: raw_data['skills'] = '|'.join([s.text.strip() for s in value_element.find_elements(By.TAG_NAME, 'span')])
                    elif 'جنسیت' in title: raw_data['gender'] = value_element.text.strip()
                    elif 'وضعیت نظام وظیفه' in title: raw_data['military_service_status'] = value_element.text.strip()
                    elif 'حداقل مدرک تحصیلی' in title: raw_data['minimum_education'] = value_element.text.strip()
                    elif 'موقعیت مکانی' in title: raw_data['city'] = value_element.text.strip()
                    elif 'نوع همکاری' in title: raw_data['contract_type'] = value_element.text.strip()
                    elif 'حقوق' in title: raw_data['salary'] = value_element.text.strip()
                except NoSuchElementException:
                    continue

            try:
                raw_data['job_description'] = self.driver.find_element(By.CSS_SELECTOR, ".s-jobDesc").text.strip()
            except NoSuchElementException:
                raw_data['job_description'] = ""

            return raw_data

        except TimeoutException:
            logging.error(f"Timeout waiting for job details on {link}. Page might be slow or selectors changed.")
            # Your excellent debug-saving logic is preserved here
            debug_dir = "scraper_debug"
            os.makedirs(debug_dir, exist_ok=True)
            safe_job_id = self._sanitize_filename(raw_data.get('job_id', 'unknown_job'))
            screenshot_path = os.path.join(debug_dir, f"error_timeout_{safe_job_id}.png")
            html_path = os.path.join(debug_dir, f"error_timeout_{safe_job_id}.html")
            self.driver.save_screenshot(screenshot_path)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logging.info(f"Saved debug files for timeout error to '{debug_dir}'.")
            return None
            
        except Exception as e:
            logging.error(f"An unexpected error occurred scraping details for {link}: {e}", exc_info=True)
            return None
            
    def close(self):
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")