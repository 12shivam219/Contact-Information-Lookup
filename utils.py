import re
import time
import requests
from typing import Dict, Optional, Tuple
from web_scraper import search_contact_info

class RateLimiter:
    def __init__(self, calls_per_minute: int = 30):
        self.calls_per_minute = calls_per_minute
        self.calls = []

    def can_make_request(self) -> bool:
        current_time = time.time()
        self.calls = [call_time for call_time in self.calls 
                     if current_time - call_time < 60]
        return len(self.calls) < self.calls_per_minute

    def add_call(self):
        self.calls.append(time.time())

def validate_person_name(name: str) -> Tuple[bool, str]:
    """Validate person name"""
    if not name:
        return False, "Person name cannot be empty"
    if len(name.strip()) < 2:
        return False, "Name too short"
    if not re.match(r'^[A-Za-z\s\'-]+$', name.strip()):
        return False, "Invalid name format"
    return True, ""

def validate_company_name(name: str) -> Tuple[bool, str]:
    """Validate company name"""
    if not name:
        return False, "Company name cannot be empty"
    if len(name.strip()) < 2:
        return False, "Company name too short"
    return True, ""

def search_person(person_name: str, company_name: str) -> Optional[Dict]:
    """Search person information using various APIs and web scraping"""
    try:
        # Get contact information through web scraping
        contact_info = search_contact_info(person_name, company_name)

        if not contact_info:
            contact_info = {}

        # Combine all information
        person_info = {
            'name': person_name,
            'company': company_name,
            'position': 'Professional',  # This would be found through scraping
            'email': contact_info.get('email'),
            'phone': contact_info.get('phone'),
            'social_profiles': contact_info.get('social_profiles', {}),
            'confidence_score': contact_info.get('confidence_score', 'low')
        }

        return person_info
    except Exception as e:
        print(f"Error in search_person: {str(e)}")
        return None

def search_company_info(company_name: str) -> Optional[Dict]:
    """Search company information"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(
            f'https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}',
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                return data[0]
        return None
    except Exception:
        return None