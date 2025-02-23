import trafilatura
import re
from typing import Optional, Dict, Tuple, List
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import quote
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_phone_number(phone: str) -> str:
    """Clean and standardize phone number format"""
    digits = re.sub(r'\D', '', phone)
    if len(digits) > 10 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) > 10:
        return f"+{digits}"
    return digits

def validate_phone_number(phone: str) -> Tuple[bool, str, float]:
    """Validate phone number format and length"""
    digits = re.sub(r'\D', '', phone)
    confidence = 0.0
    if len(digits) < 10 or len(digits) > 15:
        return False, "Invalid length", 0.0
    if len(digits) == 10:
        confidence += 0.4
    patterns = [
        (r'^\+?1?\d{10}$', 0.3),
        (r'^\+?1?\d{3}[-.]?\d{3}[-.]?\d{4}$', 0.2),
        (r'^\+?1?\s?\(\d{3}\)\s?\d{3}[-.]?\d{4}$', 0.3),
        (r'^\+\d{1,3}\s?\d{10,14}$', 0.2)
    ]
    for pattern, score in patterns:
        if re.match(pattern, phone):
            confidence += score
    if len(digits) == 10:
        area_code = digits[:3]
        if area_code in ['800', '844', '855', '866', '877', '888']:
            confidence += 0.2
    if re.match(r'^(\d)\1{9,}$', digits):
        return False, "Invalid pattern - repeated digits", 0.0
    if digits in ['1234567890', '0123456789']:
        return False, "Invalid pattern - sequential digits", 0.0
    if confidence > 0:
        confidence = min(confidence, 1.0)
        return True, "Valid phone number", confidence
    return False, "Invalid format", 0.0

def process_potential_phone(phone_match: str, source: str, base_confidence: float, best_phone_data: Dict[str, Tuple[str, float, str]]) -> None:
    """Helper function to process and validate potential phone numbers"""
    cleaned_phone = clean_phone_number(phone_match)
    is_valid, _, confidence = validate_phone_number(cleaned_phone)
    total_confidence = confidence * base_confidence
    if is_valid and total_confidence > best_phone_data.get('confidence', 0):
        best_phone_data.update({
            'phone': cleaned_phone,
            'confidence': total_confidence,
            'source': source
        })

def search_contact_info(person_name: str, company_name: str) -> Optional[Dict]:
    """Search for contact information using web scraping"""
    try:
        logger.info(f"Starting contact search for {person_name} at {company_name}")
        search_query = f"{person_name} {company_name} contact phone"
        encoded_query = quote(search_query)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        phone_patterns = [
            r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
            r'\d{3}[-.]?\d{3}[-.]?\d{4}',
            r'\+\d{1,3}\s\d{3,14}'
        ]
        best_phone_data = {}
        search_services = [
            ('Google Business', f"https://customsearch.googleapis.com/customsearch/v1?q={encoded_query}+phone"),
            ('DuckDuckGo', f"https://api.duckduckgo.com/?q={encoded_query}&format=json"),
        ]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(requests.get, url, headers=headers, timeout=5) for _, url in search_services]
            for future, (service_name, _) in zip(concurrent.futures.as_completed(futures), search_services):
                try:
                    response = future.result()
                    if response.status_code == 200:
                        data = response.json()
                        text_to_search = json.dumps(data)
                        for pattern in phone_patterns:
                            matches = re.findall(pattern, text_to_search)
                            for match in matches:
                                process_potential_phone(match, service_name, 0.9, best_phone_data)
                except Exception as e:
                    logger.error(f"Error in {service_name} search: {str(e)}")
        return {
            'phone': best_phone_data.get('phone'),
            'confidence_score': 'high' if best_phone_data.get('confidence', 0) > 0.8 else 'medium' if best_phone_data.get('confidence', 0) > 0.5 else 'low',
            'source': best_phone_data.get('source'),
            'social_profiles': {
                'linkedin': f"https://linkedin.com/in/{person_name.lower().replace(' ', '-')}",
                'linkedin_company': f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
                'twitter': f"https://twitter.com/{person_name.lower().replace(' ', '')}",
                'company': f"https://www.{company_name.lower().replace(' ', '')}.com",
                'facebook': f"https://facebook.com/{company_name.lower().replace(' ', '-')}"
            }
        }
    except Exception as e:
        logger.error(f"Error in search_contact_info: {str(e)}")
        return None