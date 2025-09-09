# scrapers/preprocessor.py
import re
import logging

# Configure logging to see warnings about unhandled cases.
# You can add this to your main run_scraper.py file as well.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_persian_to_english_numbers(text):
    if not isinstance(text, str):
        return text
    persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return text.translate(persian_to_english)

class DataCleaner:
    """
    A robust class for cleaning and standardizing scraped job data.
    - Uses data-driven logic for maintainability.
    - Logs warnings for unhandled data formats.
    - Uses pre-compiled regex for efficiency.
    """
    # --- Configuration Constants (Easy to see and modify) ---
    _NUM_MAP = {'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5, 'شش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9, 'ده': 10}
    
    # Gender codes
    GENDER_MALE = 1
    GENDER_FEMALE = 0
    GENDER_ANY = 2

    # Salary constants
    SALARY_NEGOTIABLE = "توافقی"
    SALARY_BASE_LAW = "قانون کار"

    _PATTERNS = {
        'numeric_range': re.compile(r'^(\d+)\s*-\s*(\d+)$'),
        'numeric_single': re.compile(r'^(\d+)$'),
        'range': re.compile(r'\b([\w\d]+)\b\s*تا\s*\b([\w\d]+)\b\s*سال'),
        'more_than': re.compile(r'بیش از\s*\b([\w\d]+)\b\s*سال'),
        'less_than': re.compile(r'کمتر از\s*\b([\w\d]+)\b\s*سال'),
        'at_least': re.compile(r'حداقل\s*\b([\w\d]+)\b\s*سال'),
        'numeric_salary': re.compile(r'\d[\d,.]*')
    }
    def __init__(self):
        self.experience_rules = [
            (self._PATTERNS['numeric_range'], self._handle_exp_numeric_range),
            (self._PATTERNS['numeric_single'], self._handle_exp_numeric_single),
            (self._PATTERNS['range'], self._handle_exp_range),
            (self._PATTERNS['more_than'], self._handle_exp_more_than),
            (self._PATTERNS['less_than'], self._handle_exp_less_than),
            (self._PATTERNS['at_least'], self._handle_exp_at_least),
        ]
    # --- Private Helper Methods ---
    def _get_number_from_string(self, s):
        s = s.strip()
        if s in self._NUM_MAP: return self._NUM_MAP[s]
        try: return int(s)
        except (ValueError, TypeError): return None

    def _clean_text(self, text):
        if not text: return None
        return re.sub(r'\s+', ' ', str(text)).strip()

    def _handle_exp_range(self, match):
        num1 = self._get_number_from_string(convert_persian_to_english_numbers(match.group(1)))
        num2 = self._get_number_from_string(convert_persian_to_english_numbers(match.group(2)))
        # Return the smaller of the two numbers in the range
        return min(num1, num2) if num1 is not None and num2 is not None else None

    def _handle_exp_more_than(self, match):
        # "More than 3 years" means the minimum is 3
        return self._get_number_from_string(convert_persian_to_english_numbers(match.group(1)))

    def _handle_exp_less_than(self, match):
        # "Less than 3 years" implies a minimum of 0
        return 0
    
    def _handle_exp_at_least(self, match):
        # "At least 3 years" means the minimum is 3
        return self._get_number_from_string(convert_persian_to_english_numbers(match.group(1)))

    # --- Public Cleaning Methods ---
    def clean_salary(self, salary_text):
        cleaned_text = self._clean_text(salary_text)
        if not cleaned_text: return self.SALARY_NEGOTIABLE

        if "توافقی" in cleaned_text: return self.SALARY_NEGOTIABLE
        if "قانون کار" in cleaned_text or "وزارت کار" in cleaned_text: return self.SALARY_BASE_LAW

        en_num_text = convert_persian_to_english_numbers(cleaned_text)
        numbers = self._PATTERNS['numeric_salary'].findall(en_num_text)
        if numbers:
            try: return str(int(float(numbers[0].replace(',', ''))))
            except (ValueError, IndexError): pass
        
        logging.warning(f"Could not parse salary: '{salary_text}'. Falling back to '{self.SALARY_NEGOTIABLE}'.")
        return self.SALARY_NEGOTIABLE

    def clean_experience(self, exp_text: str) -> int:
        cleaned_text = self._clean_text(exp_text)
        if not cleaned_text or "مهم نیست" in cleaned_text or "اهمیت" in cleaned_text:
            return 0
        for pattern, handler in self.experience_rules:
            match = pattern.search(cleaned_text)
            if match:
                result = handler(match)
                if result is not None:
                    return int(result)
        logging.warning(f"Could not parse experience: '{exp_text}'. Defaulting to 0.")
        return 0
        
    def clean_gender(self, gender_text):
        cleaned_text = self._clean_text(gender_text)
        if not cleaned_text: return self.GENDER_ANY
        if "مرد" in cleaned_text: return self.GENDER_MALE
        if "زن" in cleaned_text: return self.GENDER_FEMALE
        return self.GENDER_ANY

    def preprocess_job_data(self, job_data):
        cleaned_data = job_data.copy()
        
        text_fields = ['title', 'company_name', 'city', 'category', 'job_description', 
                       'minimum_education', 'military_service_status', 'contract_type']
        for key in text_fields:
            if key in cleaned_data:
                cleaned_data[key] = self._clean_text(cleaned_data.get(key))
        
        if 'salary' in cleaned_data:
            cleaned_data['salary'] = self.clean_salary(cleaned_data.get('salary'))
        if 'minimum_experience' in cleaned_data:
            cleaned_data['minimum_experience'] = self.clean_experience(cleaned_data.get('minimum_experience'))
        if 'gender' in cleaned_data:
            cleaned_data['gender'] = self.clean_gender(cleaned_data.get('gender'))
            
        for key in ['skills', 'languages']:
            if key in cleaned_data and cleaned_data.get(key):
                items = [self._clean_text(s) for s in cleaned_data[key].split('|') if s and s.strip()]
                cleaned_data[key] = '|'.join(items)

        return cleaned_data