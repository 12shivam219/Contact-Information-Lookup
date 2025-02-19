import re
import time
import requests
from typing import Dict, Optional, Tuple

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
    """Search person information using various APIs"""
    try:
        # Example using a people search API (placeholder for demonstration)
        params = {
            'name': person_name,
            'company': company_name
        }
        headers = {'User-Agent': 'Mozilla/5.0'}

        # For demonstration, using a mock response
        # In reality, you would integrate with actual people search APIs
        mock_data = {
            'name': person_name,
            'company': company_name,
            'position': 'Position information would appear here',
            'professional_details': 'Professional details would appear here',
            'public_info': 'Public information would appear here'
        }

        return mock_data
    except Exception:
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