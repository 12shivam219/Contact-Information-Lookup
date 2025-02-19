import trafilatura
import re
from typing import Optional, Dict, Tuple
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import quote
from api_services import RocketReachAPI

def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """Validate phone number format and length"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Check length (most phone numbers are 10-15 digits)
    if len(digits) < 10 or len(digits) > 15:
        return False, "Invalid length"

    # Basic format validation
    if not re.match(r'^\+?1?\d{10,14}$', digits):
        return False, "Invalid format"

    return True, "Valid phone number"

def search_contact_info(person_name: str, company_name: str) -> Optional[Dict]:
    """
    Search for contact information using RocketReach API first,
    then fall back to web scraping if API fails or is unavailable
    """
    try:
        # First try RocketReach API
        rocket_reach = RocketReachAPI()
        api_result = rocket_reach.lookup_person(person_name, company_name)

        if api_result and api_result.get('phone'):
            return api_result

        # If API fails or no phone number found, fall back to web scraping
        print("Falling back to web scraping...")

        # Rest of the original web scraping code remains the same
        search_query = f"{person_name} {company_name} contact phone"
        encoded_query = quote(search_query)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Phone number patterns
        phone_patterns = [
            r'\+?1?[-.\s]?\d{10,14}',  # Basic International Format
            r'\+?\d{1,4}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # Complex International Format
            r'\+?1?\s?\(?\d{3}\)?\s*\d{3}[-.\s]?\d{4}',  # US Format with Parentheses
            r'\+?1?\s?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'     # Simple Format
        ]

        # Generate email based on common patterns
        email = f"{person_name.lower().replace(' ', '.')}@{company_name.lower().replace(' ', '')}.com"

        # Try to find phone number from various sources
        phone = None
        confidence_score = 'low'
        source = None

        # 1. Try Google Business API (free tier)
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
                            if matches:
                                candidate_phone = matches[0]
                                is_valid, _ = validate_phone_number(candidate_phone)
                                if is_valid:
                                    phone = candidate_phone
                                    confidence_score = 'high'
                                    source = 'Google Business'
                                    break
        except Exception:
            pass

        # 2. Try company website and its subpages
        company_domain = f"www.{company_name.lower().replace(' ', '')}.com"
        subpages = [
            '/contact', '/about', '/team', '/directory', '/staff',
            '/people', '/management', '/leadership', '/executives',
            '/our-team', '/contact-us', '/about-us'
        ]

        for subpage in subpages:
            if phone:
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
                            if matches:
                                candidate_phone = matches[0]
                                is_valid, _ = validate_phone_number(candidate_phone)
                                if is_valid:
                                    phone = candidate_phone
                                    confidence_score = 'high'
                                    source = f'Company Website ({subpage})'
                                    break
            except Exception:
                continue

        # 3. Try business directories and public records
        if not phone:
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
                    if phone:
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
                                if matches:
                                    candidate_phone = matches[0]
                                    is_valid, _ = validate_phone_number(candidate_phone)
                                    if is_valid:
                                        phone = candidate_phone
                                        confidence_score = 'medium'
                                        source = directory_name
                                        break
                    except Exception:
                        continue
            except Exception:
                pass

        # 4. Try DuckDuckGo API (free)
        if not phone:
            try:
                duckduckgo_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json"
                response = requests.get(duckduckgo_url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    text_to_search = json.dumps(data)  # Search through all data
                    for pattern in phone_patterns:
                        matches = re.findall(pattern, text_to_search)
                        if matches:
                            candidate_phone = matches[0]
                            is_valid, _ = validate_phone_number(candidate_phone)
                            if is_valid:
                                phone = candidate_phone
                                confidence_score = 'medium'
                                source = 'DuckDuckGo'
                                break
            except Exception:
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

        contact_info = {
            'email': email,
            'phone': phone,
            'social_profiles': social_profiles,
            'confidence_score': confidence_score,
            'source': source
        }

        return contact_info
    except Exception as e:
        print(f"Error in search_contact_info: {str(e)}")
        return None