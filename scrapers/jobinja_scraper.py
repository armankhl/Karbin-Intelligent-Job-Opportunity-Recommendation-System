# scrapers/jobinja_scraper.py
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException # <-- Add TimeoutException
from selenium.webdriver.support.ui import WebDriverWait # <-- Add this
from selenium.webdriver.support import expected_conditions as EC # <-- Add this
from . import database

class JobinjaScraper:
    def __init__(self, email, password, proxy=None, headless=True):
        self.base_url = "https://jobinja.ir"
        self.email = email
        self.password = password
        self.driver = self._setup_driver(proxy, headless)
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
        
        return webdriver.Chrome(options=options)

    # In class JobinjaScraper:
    def login(self):
        """Logs into jobinja.ir using explicit waits for robustness."""
        login_url = f"{self.base_url}/login/user"
        self.driver.get(login_url)
        try:
            print("Attempting to log in...")
            
            # --- START OF CHANGES ---
            # Wait up to 10 seconds for the email field to be visible before trying to interact with it
            wait = WebDriverWait(self.driver, 10)
            
            email_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#identifier")))
            email_field.send_keys(self.email)
            
            # The password field is usually available right after the email field
            password_field = self.driver.find_element(By.CSS_SELECTOR, "#password")
            password_field.send_keys(self.password)
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type=submit]")
            submit_button.click()
            # --- END OF CHANGES ---
            
            # Wait until the URL no longer contains '/login'
            # This is a better way to check for successful login
            print("Waiting for login redirect...")
            wait.until(EC.url_changes(login_url))

            if '/login' in self.driver.current_url:
                print("Login failed. The page reloaded but is still on the login page. Check credentials or CAPTCHA.")
                logging.warning("Login failed.")
                return False

            print("Login successful.")
            logging.info("Login successful.")
            return True

        except TimeoutException:
            # This will catch the error if the email field doesn't appear after 10 seconds
            print("Login failed: Timed out waiting for login page elements to load.")
            logging.error("Login page elements not found.")
            # Let's save a screenshot to see what the page looks like
            self.driver.save_screenshot('login_error_screenshot.png')
            print("Screenshot saved to 'login_error_screenshot.png' for debugging.")
            return False
            
        except Exception as e:
            # Catch any other unexpected errors
            print(f"An unexpected error occurred during login: {e}")
            logging.error(f"Unexpected login error: {e}")
            return False

    def scrape(self, start_page=1, end_page=5):
        """Main method to start the scraping process."""
        if not self.login():
            self.close()
            return
        
        print(f"Starting to scrape from page {start_page} to {end_page}...")
        for page_num in range(start_page, end_page + 1):
            list_url = f"{self.base_url}/jobs?page={page_num}"
            print(f"\n--- Scraping page {page_num}: {list_url} ---")
            self.driver.get(list_url)
            time.sleep(2) # Wait for page to load

            job_links = [a.get_attribute('href') for a in self.driver.find_elements(By.CSS_SELECTOR, 'a.c-jobListView__titleLink')]
            
            for link in job_links:
                try:
                    job_data = self.scrape_job_details(link)
                    if job_data:
                        database.save_job_posting(job_data)
                except Exception as e:
                    print(f"Error processing link {link}: {e}")
                    logging.error(f"Error on link {link}: {e}")
        
        self.close()
# In class JobinjaScraper:
    def scrape_job_details(self, link):
        """Scrapes all details from a single job page using explicit waits."""
        self.driver.get(link)
        
        try:
            # Use an explicit wait for the main job container to ensure the page is loaded
            wait = WebDriverWait(self.driver, 10)
            job_container_selector = (By.CSS_SELECTOR, "section.c-jobView")
            wait.until(EC.visibility_of_element_located(job_container_selector))
            
            data = {
                'link': link,
                'job_id': link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
            }

            # --- CORRECTED SELECTORS START HERE ---
            
            # Corrected Title selector
            title_selector = (By.CSS_SELECTOR, ".c-jobView__titleText h1")
            data['title'] = wait.until(EC.visibility_of_element_located(title_selector)).text.strip()

            # Corrected Company Name selector (assuming it's still correct, let's make it robust)
            # The company name is often in a separate header outside the main box.
            # We will use a more general selector. Let's assume it's still '.c-companyHeader__name' for now
            try:
                company_name_selector = (By.CSS_SELECTOR, ".c-companyHeader__name")
                data['company_name'] = self.driver.find_element(*company_name_selector).text.strip()
            except NoSuchElementException:
                # Fallback if the company name is somewhere else
                data['company_name'] = "N/A" # Or try another selector
                logging.warning(f"Company name not found for {link} using primary selector.")

            # --- SELECTORS FOR INFO BOXES ---
            # This logic is more robust as it iterates through boxes by their title.
            
            # The info boxes are now in two separate `<ul>` lists. We'll get all of them.
            info_items = self.driver.find_elements(By.CSS_SELECTOR, ".c-infoBox__item")
            for item in info_items:
                try:
                    title = item.find_element(By.CSS_SELECTOR, '.c-infoBox__itemTitle').text.strip()
                    value_element = item.find_element(By.CSS_SELECTOR, '.tags')
                    
                    if 'دسته‌بندی شغلی' in title:
                        data['category'] = value_element.text.strip()
                    elif 'حداقل سابقه کار' in title:
                        data['minimum_experience'] = value_element.text.strip()
                    elif 'مهارت‌های مورد نیاز' in title:
                        skills = [span.text.strip() for span in value_element.find_elements(By.TAG_NAME, 'span')]
                        data['skills'] = '|'.join(skills)
                    elif 'جنسیت' in title:
                        data['gender'] = value_element.text.strip()
                    elif 'وضعیت نظام وظیفه' in title:
                        data['military_service_status'] = value_element.text.strip() # Corrected key
                    elif 'حداقل مدرک تحصیلی' in title:
                        data['minimum_education'] = value_element.text.strip()
                    elif 'زبان‌های مورد نیاز' in title:
                        languages = [span.text.strip() for span in value_element.find_elements(By.TAG_NAME, 'span')]
                        data['languages'] = '|'.join(languages)
                    elif 'موقعیت مکانی' in title:
                        data['city'] = value_element.text.strip()
                    elif 'نوع همکاری' in title:
                        data['contract_type'] = value_element.text.strip()
                    elif 'حقوق' in title:
                        data['salary'] = value_element.text.strip()

                except NoSuchElementException:
                    continue # Ignore if a box doesn't have the expected structure

            # --- SELECTOR FOR JOB DESCRIPTION ---
            try:
                description_selector = (By.CSS_SELECTOR, ".s-jobDesc")
                data['job_description'] = self.driver.find_element(*description_selector).text.strip()
            except NoSuchElementException:
                data['job_description'] = "Description not found."
                logging.warning(f"Job description not found for {link}")

            return data

        except TimeoutException:
            logging.error(f"Timeout waiting for job details to load for {link}")
            self.driver.save_screenshot(f"error_detail_page_{data.get('job_id', 'unknown')}.png")
            return None
        except Exception as e:
            # This now prints the full error, which is much more helpful
            logging.error(f"Could not scrape details for {link}: {e}", exc_info=True)
            return None
            
    def close(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")