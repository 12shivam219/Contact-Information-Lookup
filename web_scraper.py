import trafilatura
import re
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup

def search_contact_info(person_name: str, company_name: str) -> Optional[Dict]:
    """
    Search for contact information using web scraping
    """
    try:
        # Create search queries
        search_query = f"{person_name} {company_name} contact email phone"

        # Use a search engine API (this is a mock URL, you would need to use a real search API)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Extract email using pattern matching
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_patterns = [
            r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International format
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',  # (123) 456-7890
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'    # 123-456-7890
        ]

        # Generate email based on common patterns
        email = f"{person_name.lower().replace(' ', '.')}@{company_name.lower().replace(' ', '')}.com"

        # Try to find phone number from various sources
        phone = None
        confidence_score = 'low'

        # 1. Try company website
        company_domain = f"www.{company_name.lower().replace(' ', '')}.com"
        try:
            response = requests.get(f"https://{company_domain}/contact", headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for phone numbers in contact page
                text_content = soup.get_text()
                for pattern in phone_patterns:
                    matches = re.findall(pattern, text_content)
                    if matches:
                        phone = matches[0]
                        confidence_score = 'medium'
                        break
        except Exception:
            pass

        # 2. Try LinkedIn-style URL (public profile)
        linkedin_name = person_name.lower().replace(' ', '-')
        social_profiles = {
            'linkedin': f"https://linkedin.com/in/{linkedin_name}",
            'twitter': f"https://twitter.com/{person_name.lower().replace(' ', '')}"
        }

        # 3. If no phone found, try company directory style URL
        if not phone:
            try:
                directory_url = f"https://{company_domain}/directory"
                response = requests.get(directory_url, headers=headers, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Look for phone numbers in directory
                    text_content = soup.get_text()
                    for pattern in phone_patterns:
                        matches = re.findall(pattern, text_content)
                        if matches:
                            phone = matches[0]
                            confidence_score = 'medium'
                            break
            except Exception:
                pass

        # 4. As a last resort, try business directories
        if not phone:
            try:
                directories = [
                    f"https://www.yellowpages.com/search?q={company_name}",
                    f"https://www.yelp.com/search?find_desc={company_name}"
                ]
                for url in directories:
                    response = requests.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        text_content = soup.get_text()
                        for pattern in phone_patterns:
                            matches = re.findall(pattern, text_content)
                            if matches:
                                phone = matches[0]
                                confidence_score = 'low'  # Lower confidence for directory listings
                                break
                    if phone:
                        break
            except Exception:
                pass

        contact_info = {
            'email': email,
            'phone': phone,
            'social_profiles': social_profiles,
            'confidence_score': confidence_score
        }

        return contact_info
    except Exception as e:
        print(f"Error in search_contact_info: {str(e)}")
        return None