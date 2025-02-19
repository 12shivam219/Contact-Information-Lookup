import os
import requests
from typing import Optional, Dict
import time

class RocketReachAPI:
    """RocketReach API integration for contact information lookup"""
    
    def __init__(self):
        self.api_key = os.getenv('ROCKETREACH_API_KEY')
        self.base_url = "https://api.rocketreach.co/v2"
        self.rate_limit_remaining = 10
        self.rate_limit_reset = 0

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        if time.time() < self.rate_limit_reset:
            return self.rate_limit_remaining > 0
        return True

    def lookup_person(self, name: str, company: str) -> Optional[Dict]:
        """
        Look up a person's contact information using RocketReach API
        Returns None if API is not available or rate limited
        """
        if not self.api_key or not self._check_rate_limit():
            return None

        try:
            # Search for the person
            search_url = f"{self.base_url}/lookup"
            headers = {
                "Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            params = {
                "name": name,
                "current_employer": company,
            }

            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            # Update rate limits from headers
            self.rate_limit_remaining = int(response.headers.get('X-Rate-Limit-Remaining', 0))
            self.rate_limit_reset = int(response.headers.get('X-Rate-Limit-Reset', 0))

            if response.status_code == 200:
                data = response.json()
                if not data:
                    return None

                # Extract relevant information
                contact_info = {
                    'name': data.get('name', name),
                    'position': data.get('title'),
                    'company': data.get('current_employer', company),
                    'email': data.get('email'),
                    'phone': data.get('phone_numbers', [None])[0],
                    'social_profiles': {
                        'linkedin': data.get('linkedin_url'),
                        'twitter': data.get('twitter_url'),
                    },
                    'confidence_score': 'high',
                    'source': 'RocketReach API'
                }
                return contact_info

            return None

        except Exception as e:
            print(f"RocketReach API error: {str(e)}")
            return None
