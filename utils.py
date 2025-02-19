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

def validate_domain(domain: str) -> Tuple[bool, str]:
    """Validate domain format"""
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    if not domain:
        return False, "Domain cannot be empty"
    if not re.match(domain_pattern, domain):
        return False, "Invalid domain format"
    return True, ""

def validate_company_name(name: str) -> Tuple[bool, str]:
    """Validate company name"""
    if not name:
        return False, "Company name cannot be empty"
    if len(name) < 2:
        return False, "Company name too short"
    return True, ""

def search_clearbit(domain: str) -> Optional[Dict]:
    """Search company information using Clearbit's free API"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(
            f'https://autocomplete.clearbit.com/v1/companies/suggest?query={domain}',
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                return data[0]
        return None
    except Exception:
        return None

def search_domain_info(domain: str) -> Optional[Dict]:
    """Search domain information using WHOIS API"""
    try:
        response = requests.get(f'https://api.whoapi.com/?domain={domain}&r=whois')
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None
