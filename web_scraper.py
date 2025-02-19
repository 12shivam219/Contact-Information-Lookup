import trafilatura
import re
from typing import Optional, Dict, Tuple, List
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import quote
from api_services import RocketReachAPI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_phone_number(phone: str) -> str:
    """Clean and standardize phone number format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Handle international format
    if len(digits) > 10 and digits.startswith('1'):
        digits = digits[1:]

    # Format to standard format (XXX) XXX-XXXX
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) > 10:  # International format
        return f"+{digits}"
    return digits

def validate_phone_number(phone: str) -> Tuple[bool, str, float]:
    """
    Validate phone number format and length
    Returns: (is_valid, message, confidence_score)
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Initialize confidence score
    confidence = 0.0

    # Length validation
    if len(digits) < 10 or len(digits) > 15:
        return False, "Invalid length", 0.0

    # Perfect length for US numbers
    if len(digits) == 10:
        confidence += 0.4

    # Check for common patterns
    patterns = [
        (r'^\+?1?\d{10}$', 0.3),  # Basic US format
        (r'^\+?1?\d{3}[-.]?\d{3}[-.]?\d{4}$', 0.2),  # Common separators
        (r'^\+?1?\s?\(\d{3}\)\s?\d{3}[-.]?\d{4}$', 0.3),  # (XXX) format
        (r'^\+\d{1,3}\s?\d{10,14}$', 0.2)  # International format
    ]

    for pattern, score in patterns:
        if re.match(pattern, phone):
            confidence += score

    # Area code validation for US numbers
    if len(digits) == 10:
        area_code = digits[:3]
        if area_code in ['800', '844', '855', '866', '877', '888']:
            confidence += 0.2  # Toll-free numbers are likely business numbers

    # Check for obviously fake numbers
    if re.match(r'^(\d)\1{9,}$', digits):  # All same digits
        return False, "Invalid pattern - repeated digits", 0.0

    if digits in ['1234567890', '0123456789']:
        return False, "Invalid pattern - sequential digits", 0.0

    # Final validation
    if confidence > 0:
        confidence = min(confidence, 1.0)  # Cap at 1.0
        return True, "Valid phone number", confidence

    return False, "Invalid format", 0.0

def search_contact_info(person_name: str, company_name: str) -> Optional[Dict]:
    """
    Search for contact information using RocketReach API first,
    then fall back to web scraping if API fails or is unavailable
    """
    try:
        logger.info(f"Starting contact search for {person_name} at {company_name}")

        # First try RocketReach API
        rocket_reach = RocketReachAPI()
        api_result = rocket_reach.lookup_person(person_name, company_name)

        if api_result and api_result.get('phone'):
            logger.info("Found contact info via RocketReach API")
            return api_result

        # If API fails or no phone number found, fall back to web scraping
        logger.info("Falling back to web scraping...")

        search_query = f"{person_name} {company_name} contact phone"
        encoded_query = quote(search_query)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        phone_patterns = [
            r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',  # (XXX) XXX-XXXX
            r'\d{3}[-.]?\d{3}[-.]?\d{4}',  # XXX-XXX-XXXX
            r'\+\d{1,3}\s\d{3,14}'  # International with space
        ]

        # Initialize result tracking
        best_phone = None
        best_confidence = 0
        best_source = None

        def process_potential_phone(phone_match: str, source: str, base_confidence: float) -> None:
            """Helper function to process and validate potential phone numbers"""
            nonlocal best_phone, best_confidence, best_source

            cleaned_phone = clean_phone_number(phone_match)
            is_valid, _, confidence = validate_phone_number(cleaned_phone)

            total_confidence = confidence * base_confidence

            if is_valid and total_confidence > best_confidence:
                best_phone = cleaned_phone
                best_confidence = total_confidence
                best_source = source

        # 1. Try Google Business Search
        try:
            google_search_url = f"https://customsearch.googleapis.com/customsearch/v1?q={encoded_query}+phone"
            response = requests.get(google_search_url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'items' in data:
                    for item in data['items']:
                        snippet = item.get('snippet', '')
                        for pattern in phone_patterns:
                            matches = re.findall(pattern, snippet)
                            for match in matches:
                                process_potential_phone(match, 'Google Business', 0.9)
        except Exception as e:
            logger.error(f"Error in Google Business search: {str(e)}")

        # 2. Try company website and its subpages
        company_domain = f"www.{company_name.lower().replace(' ', '')}.com"
        subpages = [
            '/contact', '/about', '/team', '/directory', '/staff',
            '/people', '/management', '/leadership', '/executives',
            '/our-team', '/contact-us', '/about-us'
        ]

        for subpage in subpages:
            if best_phone:
                break
            try:
                url = f"https://{company_domain}{subpage}"
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    # Use trafilatura for better text extraction
                    downloaded = trafilatura.fetch_url(url)
                    text_content = trafilatura.extract(downloaded)

                    if text_content:
                        for pattern in phone_patterns:
                            matches = re.findall(pattern, text_content)
                            for match in matches:
                                process_potential_phone(match, f'Company Website ({subpage})', 0.8)
            except Exception as e:
                logger.error(f"Error processing company website subpage {subpage}: {str(e)}")
                continue

        # 3. Try business directories and public records
        if not best_phone:
            try:
                directories = [
                    ('Yellow Pages', f"https://www.yellowpages.com/search?q={encoded_query}"),
                    ('Yelp', f"https://www.yelp.com/search?find_desc={encoded_query}"),
                    ('Better Business Bureau', f"https://www.bbb.org/search?find_text={encoded_query}"),
                    ('Manta', f"https://www.manta.com/search?search_source=nav&search={encoded_query}"),
                    ('Chamber of Commerce', f"https://www.chamberofcommerce.com/united-states/{encoded_query}"),
                    ('Local Business Directory', f"https://local.com/business/search/{encoded_query}"),
                    ('White Pages', f"https://www.whitepages.com/business/{encoded_query}"),
                    ('CrunchBase', f"https://www.crunchbase.com/textsearch?q={encoded_query}"),
                    ('ZoomInfo', f"https://www.zoominfo.com/s/#!search/company/{encoded_query}")
                ]

                for directory_name, url in directories:
                    if best_phone:
                        break
                    try:
                        response = requests.get(url, headers=headers, timeout=5)
                        if response.status_code == 200:
                            # Use both BeautifulSoup and trafilatura
                            soup = BeautifulSoup(response.text, 'html.parser')
                            text_content = soup.get_text()

                            # Also try trafilatura
                            downloaded = trafilatura.fetch_url(url)
                            if downloaded:
                                text_content += trafilatura.extract(downloaded) or ''

                            for pattern in phone_patterns:
                                matches = re.findall(pattern, text_content)
                                for match in matches:
                                    process_potential_phone(match, directory_name, 0.7)
                    except Exception as e:
                        logger.error(f"Error processing directory {directory_name}: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Error in business directory search: {str(e)}")
                pass

        # 4. Try DuckDuckGo API (free)
        if not best_phone:
            try:
                duckduckgo_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json"
                response = requests.get(duckduckgo_url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    text_to_search = json.dumps(data)  # Search through all data
                    for pattern in phone_patterns:
                        matches = re.findall(pattern, text_to_search)
                        for match in matches:
                            process_potential_phone(match, 'DuckDuckGo', 0.6)
            except Exception as e:
                logger.error(f"Error in DuckDuckGo search: {str(e)}")
                pass

        # 5. Try LinkedIn public profile (respectful of ToS)
        linkedin_name = person_name.lower().replace(' ', '-')
        company_slug = company_name.lower().replace(' ', '-')
        social_profiles = {
            'linkedin': f"https://linkedin.com/in/{linkedin_name}",
            'linkedin_company': f"https://linkedin.com/company/{company_slug}",
            'twitter': f"https://twitter.com/{person_name.lower().replace(' ', '')}",
            'company': f"https://{company_domain}",
            'facebook': f"https://facebook.com/{company_slug}"
        }

        confidence_level = 'high' if best_confidence > 0.8 else 'medium' if best_confidence > 0.5 else 'low'

        contact_info = {
            'phone': best_phone,
            'confidence_score': confidence_level,
            'source': best_source,
            'social_profiles': social_profiles,
            'validation_score': round(best_confidence, 2)
        }

        logger.info(f"Search completed. Confidence: {confidence_level}, Source: {best_source}")
        return contact_info

    except Exception as e:
        logger.error(f"Error in search_contact_info: {str(e)}")
        return None