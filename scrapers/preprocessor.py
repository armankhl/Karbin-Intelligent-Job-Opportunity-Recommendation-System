# scrapers/preprocessor.py
import re

# تابع کمکی برای تبدیل اعداد فارسی به انگلیسی
def convert_persian_to_english_numbers(text):
    persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return text.translate(persian_to_english)

class DataCleaner:
    
    def _get_number_from_string(self, s):
        """Helper function to convert a string (digit or word) to an integer."""
        s = s.strip()
        num_map = {
            'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5, 
            'شش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9, 'ده': 10
        }
        if s in num_map:
            return num_map[s]
        try:
            return int(s)
        except ValueError:
            return None # Return None if conversion fails

    def clean_text(self, text):
        """A general-purpose text cleaning function."""
        if not text:
            return None
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def clean_salary(self, salary_text):
        """
        Cleans and standardizes salary information into a structured format.
        Outputs: ' توافقی', 'قانون کار', or a numeric value in millions of Toman.
        """
        if not salary_text:
            return "توافقی"
        
        salary_text = self.clean_text(salary_text)
        salary_text_en_num = convert_persian_to_english_numbers(salary_text)

        # Case 1: Negotiable salary
        if "توافقی" in salary_text:
            return "توافقی"
        
        # Case 2: Base salary (Ministry of Labor)
        if "قانون کار" in salary_text or "وزارت کار" in salary_text:
            return "قانون کار"
        
        # Case 3: Numeric salary (e.g., "از ۲۲,۰۰۰,۰۰۰ تومان")
        # Find all numbers in the string
        numbers = re.findall(r'\d[\d,]*', salary_text_en_num)
        
        if numbers:
            try:
                # Get the first number, remove commas, and convert to integer
                # We assume the number is in Toman and convert it to millions
                salary_value = int(numbers[0].replace(',', ''))
                # You can store the raw number or standardize it (e.g., in millions)
                # Storing the raw number is more flexible.
                return str(salary_value)
            except (ValueError, IndexError):
                # If conversion fails, fall back to a default
                return "توافقی"
        
        # Fallback for any other case
        return "توافقی"



    def clean_experience(self, exp_text):
        """
        Cleans and standardizes minimum experience into a numeric range format (e.g., '3-6').
        This version correctly handles both numeric digits and Persian number words.
        """
        if not exp_text:
            return "0"
            
        exp_text_norm = self.clean_text(exp_text)
        exp_text_en_num = convert_persian_to_english_numbers(exp_text_norm)
        
        # Case 1: Not important
        if "مهم نیست" in exp_text_norm or "اهمیت" in exp_text_norm:
            return "0"
            
        # Case 2: Range (e.g., "سه تا شش سال" or "3 تا 5 سال")
        # We match words (\w+) or digits (\d+)
        match = re.search(r'([\w\d]+)\s*تا\s*([\w\d]+)\s*سال', exp_text_norm)
        if match:
            num1_str = convert_persian_to_english_numbers(match.group(1))
            num2_str = convert_persian_to_english_numbers(match.group(2))
            
            num1 = self._get_number_from_string(num1_str)
            num2 = self._get_number_from_string(num2_str)

            if num1 is not None and num2 is not None:
                return f"{num1}-{num2}"

        # Case 3: More than X years (e.g., "بیش از شش سال")
        match = re.search(r'بیش از\s*([\w\d]+)\s*سال', exp_text_norm)
        if match:
            num_str = convert_persian_to_english_numbers(match.group(1))
            num = self._get_number_from_string(num_str)
            if num is not None:
                return str(num) # Represents "num+" years, we just store the lower bound.
        
        # Case 4: Less than X years (e.g., "کمتر از سه سال")
        match = re.search(r'کمتر از\s*([\w\d]+)\s*سال', exp_text_norm)
        if match:
            num_str = convert_persian_to_english_numbers(match.group(1))
            num = self._get_number_from_string(num_str)
            if num is not None:
                return f"0-{num}"

        # Case 5: Exactly X years (e.g., "حداقل ۲ سال")
        match = re.search(r'حداقل\s*([\w\d]+)\s*سال', exp_text_en_num)
        if match:
            num_str = match.group(1)
            num = self._get_number_from_string(num_str)
            if num is not None:
                return str(num)

        # Fallback: if no pattern matches, return the normalized original text
        return exp_text_norm
        
    def clean_gender(self, gender_text):
        """
        Converts gender text to a numeric code.
        - Male: 1
        - Female: 0
        - Not important / Both: 2
        """
        if not gender_text:
            return 2  # Default to 'Not important'

        gender_text = self.clean_text(gender_text)

        if "مرد" in gender_text:
            return 1
        if "زن" in gender_text:
            return 0
        
        # "مهم نیست", "خانم و آقا", "آقا و خانم" all fall here
        return 2

    def preprocess_job_data(self, job_data):
        """
        Applies cleaning functions to the entire job data dictionary
        before it gets saved to the database.
        """
        cleaned_data = job_data.copy()
        
        # Clean all text fields
        for key in ['title', 'company_name', 'city', 'category', 
                    'job_description', 'minimum_education', 'gender', 
                    'military_service_status', 'contract_type']: # Renamed military_service
            if key in cleaned_data and cleaned_data[key]:
                cleaned_data[key] = self.clean_text(cleaned_data[key])
        
        # Clean specialized fields with new logic
        if 'salary' in cleaned_data:
            cleaned_data['salary'] = self.clean_salary(cleaned_data.get('salary'))
            
        if 'minimum_experience' in cleaned_data:
            cleaned_data['minimum_experience'] = self.clean_experience(cleaned_data.get('minimum_experience'))
            
        if 'gender' in cleaned_data:
            cleaned_data['gender'] = self.clean_gender(cleaned_data.get('gender'))
            
        # Clean skills and languages
        if 'skills' in cleaned_data and cleaned_data['skills']:
            cleaned_data['skills'] = '|'.join([self.clean_text(s) for s in cleaned_data['skills'].split('|') if s.strip()])
        
        if 'languages' in cleaned_data and cleaned_data['languages']:
            cleaned_data['languages'] = '|'.join([self.clean_text(l) for l in cleaned_data['languages'].split('|') if l.strip()])

        return cleaned_data