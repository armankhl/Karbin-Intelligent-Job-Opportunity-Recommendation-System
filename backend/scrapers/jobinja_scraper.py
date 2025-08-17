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
from .database import save_job_posting 
from .preprocessor import DataCleaner

# Import the Service class
from selenium.webdriver.chrome.service import Service

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
        
        service = Service(executable_path="chromedriver.exe")
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.set_page_load_timeout(30)
        return driver

    def login(self):
        """Logs into jobinja.ir using explicit waits for robustness."""
        print("Attempting to log in...")
        try:
            self.driver.get(self.login_url)
            wait = WebDriverWait(self.driver, 10)
            email_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#identifier")))
            email_field.send_keys(self.email)
            self.driver.find_element(By.CSS_SELECTOR, "#password").send_keys(self.password)
            self.driver.find_element(By.CSS_SELECTOR, "input[type=submit]").click()
            wait.until_not(EC.url_contains('/login'))
            print("Login successful.")
            logging.info("Login successful.")
            return True
        except TimeoutException:
            print("Login failed: Timed out waiting for login page.")
            self.driver.save_screenshot('login_error_screenshot.png')
            return False
        except Exception as e:
            print(f"An unexpected error occurred during login: {e}")
            return False
            
    def _sanitize_filename(self, filename):
        return re.sub(r'[^\w\-.]', '_', filename)
        
    def scrape(self, start_page=1, end_page=5):
        if not self.login():
            self.close()
            return
        
        print(f"Starting to scrape from page {start_page} to {end_page}...")
        for page_num in range(start_page, end_page + 1):
            list_url = f"https://jobinja.ir{self.jobs_path}?page={page_num}"
            print(f"\n--- Scraping page {page_num}: {list_url} ---")
            
            try:
                self.driver.get(list_url)
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.c-jobListView__titleLink')))
                job_links = [a.get_attribute('href') for a in self.driver.find_elements(By.CSS_SELECTOR, 'a.c-jobListView__titleLink')]
            except TimeoutException:
                logging.warning(f"Could not find job links on page {page_num}. It might be the last page.")
                continue

            for link in job_links:
                try:
                    raw_job_data = self.scrape_job_details(link)
                    if raw_job_data:
                        cleaned_job_data = self.cleaner.preprocess_job_data(raw_job_data)
                        save_job_posting(cleaned_job_data)
                except Exception as e:
                    print(f"An unexpected error occurred processing link {link}.")
                    logging.error(f"Error on link {link}: {e}", exc_info=True)
        
        self.close()

    def scrape_job_details(self, link):
        """
        Scrapes all details from a single job page with robust error handling
        and the corrected CSS selector for the job title.
        """
        try:
            job_id = link.split('/jobs/')[1].split('/')[0]
        except IndexError:
            job_id = self._sanitize_filename(link.split('/')[-1])
        
        data = {'link': link, 'job_id': job_id}

        try:
            self.driver.get(link)
            wait = WebDriverWait(self.driver, 15)
            title_selector = (By.CSS_SELECTOR, "div.c-jobView__titleText > h1")
            
            wait.until(EC.visibility_of_element_located(title_selector))
            
            data['title'] = self.driver.find_element(*title_selector).text.strip()

            try:
                company_name_selector = (By.CSS_SELECTOR, ".c-companyHeader__name")
                data['company_name'] = self.driver.find_element(*company_name_selector).text.strip()
            except NoSuchElementException:
                data['company_name'] = "N/A"
                logging.warning(f"Company name not found for {link}.")

            # --- Extract from Info Boxes (This logic is fine) ---
            info_items = self.driver.find_elements(By.CSS_SELECTOR, ".c-infoBox__item")
            for item in info_items:
                try:
                    title = item.find_element(By.CSS_SELECTOR, '.c-infoBox__itemTitle').text.strip()
                    value_element = item.find_element(By.CSS_SELECTOR, '.tags')
                    
                    if 'دسته‌بندی شغلی' in title: data['category'] = value_element.text.strip()
                    elif 'حداقل سابقه کار' in title: data['minimum_experience'] = value_element.text.strip()
                    elif 'مهارت‌های مورد نیاز' in title: data['skills'] = '|'.join([s.text.strip() for s in value_element.find_elements(By.TAG_NAME, 'span')])
                    elif 'جنسیت' in title: data['gender'] = value_element.text.strip()
                    elif 'وضعیت نظام وظیفه' in title: data['military_service_status'] = value_element.text.strip()
                    elif 'حداقل مدرک تحصیلی' in title: data['minimum_education'] = value_element.text.strip()
                    elif 'زبان‌های مورد نیاز' in title: data['languages'] = '|'.join([s.text.strip() for s in value_element.find_elements(By.TAG_NAME, 'span')])
                    elif 'موقعیت مکانی' in title: data['city'] = value_element.text.strip()
                    elif 'نوع همکاری' in title: data['contract_type'] = value_element.text.strip()
                    elif 'حقوق' in title: data['salary'] = value_element.text.strip()
                except NoSuchElementException:
                    continue

            # --- Extract Job Description ---
            try:
                description_selector = (By.CSS_SELECTOR, ".s-jobDesc")
                data['job_description'] = self.driver.find_element(*description_selector).text.strip()
            except NoSuchElementException:
                data['job_description'] = "Description not found."

            return data

        except TimeoutException:
            logging.error(f"Timeout waiting for job details to load for {link}. The website structure might have changed.")
            
            debug_dir = "scraper_debug"
            os.makedirs(debug_dir, exist_ok=True)
            safe_job_id = self._sanitize_filename(data['job_id'])
            screenshot_path = os.path.join(debug_dir, f"error_page_{safe_job_id}.png")
            html_path = os.path.join(debug_dir, f"error_page_{safe_job_id}.html")
            
            self.driver.save_screenshot(screenshot_path)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            
            logging.info(f"Saved debug files to '{debug_dir}'. Please inspect the HTML to find the correct CSS selectors.")
            return None
            
        except Exception as e:
            logging.error(f"An unexpected error occurred scraping details for {link}: {e}", exc_info=True)
            return None
            
    def close(self):
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")