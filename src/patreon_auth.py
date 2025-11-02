#!/usr/bin/env python3
"""
Patreon Authentication Module
Handles login and session management
"""

import requests
import json
import logging
from pathlib import Path
from typing import Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatreonAuth:
    """Handles Patreon authentication and session management"""

    BASE_URL = "https://www.patreon.com"
    API_URL = "https://www.patreon.com/api"

    # Public API key (from reverse engineering)
    API_KEY = "1745177328c8a1d48100a9b14a1d38c1"

    def __init__(self, email: str, password: str):
        """
        Initialize authenticator

        Args:
            email: Patreon account email
            password: Patreon account password
        """
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session_cookie = None

        # Set default headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': self.BASE_URL,
            'Referer': f'{self.BASE_URL}/login'
        })

    def login(self) -> bool:
        """
        Authenticate with Patreon and obtain session cookie

        Returns:
            bool: True if login successful, False otherwise
        """
        logger.info(f"Attempting to login with email: {self.email}")

        # First, get CSRF token
        try:
            # Visit login page to get CSRF token
            login_page = self.session.get(f"{self.BASE_URL}/login")

            if login_page.status_code != 200:
                logger.error(f"Failed to load login page: {login_page.status_code}")
                return False

            # TODO: Extract CSRF token from page if needed
            # For now, attempt direct login

            # Prepare login payload
            login_data = {
                "data": {
                    "type": "user",
                    "attributes": {
                        "email": self.email,
                        "password": self.password
                    }
                }
            }

            # Attempt login
            response = self.session.post(
                f"{self.API_URL}/login",
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )

            logger.info(f"Login response status: {response.status_code}")

            if response.status_code == 200:
                # Check for session cookie
                if 'session_id' in self.session.cookies:
                    self.session_cookie = self.session.cookies['session_id']
                    logger.info("✅ Login successful! Session cookie obtained.")
                    return True
                else:
                    # Try to get session cookie from response
                    cookies = response.cookies
                    if 'session_id' in cookies:
                        self.session_cookie = cookies['session_id']
                        logger.info("✅ Login successful! Session cookie obtained from response.")
                        return True

                    logger.warning("Login returned 200 but no session cookie found")
                    logger.debug(f"Response: {response.text[:500]}")
                    return False
            else:
                logger.error(f"Login failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exception during login: {e}")
            return False

    def get_current_user(self) -> Optional[Dict]:
        """
        Get current logged-in user information

        Returns:
            dict: User data if authenticated, None otherwise
        """
        if not self.session_cookie:
            logger.error("No session cookie. Please login first.")
            return None

        try:
            response = self.session.get(
                f"{self.API_URL}/current_user",
                params={'api_key': self.API_KEY}
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Current user: {data.get('data', {}).get('attributes', {}).get('full_name', 'Unknown')}")
                return data
            else:
                logger.error(f"Failed to get current user: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Exception getting current user: {e}")
            return None

    def is_authenticated(self) -> bool:
        """
        Check if session is authenticated

        Returns:
            bool: True if authenticated and session is valid
        """
        user = self.get_current_user()
        return user is not None

    def save_session(self, filepath: str = "config/session.json"):
        """
        Save session cookie to file for reuse

        Args:
            filepath: Path to save session data
        """
        if not self.session_cookie:
            logger.warning("No session cookie to save")
            return

        session_data = {
            'session_id': self.session_cookie,
            'email': self.email,
            'cookies': dict(self.session.cookies)
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)

        logger.info(f"💾 Session saved to {filepath}")

    def load_session(self, filepath: str = "config/session.json") -> bool:
        """
        Load session cookie from file

        Args:
            filepath: Path to session data file

        Returns:
            bool: True if session loaded and valid
        """
        try:
            with open(filepath, 'r') as f:
                session_data = json.load(f)

            self.session_cookie = session_data.get('session_id')

            # Restore cookies
            for name, value in session_data.get('cookies', {}).items():
                self.session.cookies.set(name, value)

            logger.info(f"📂 Session loaded from {filepath}")

            # Verify session is still valid
            if self.is_authenticated():
                logger.info("✅ Session is valid!")
                return True
            else:
                logger.warning("⚠️  Loaded session is no longer valid")
                return False

        except FileNotFoundError:
            logger.info(f"No saved session found at {filepath}")
            return False
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return False


def main():
    """Test authentication"""
    # Load credentials
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"

    with open(config_path) as f:
        config = json.load(f)

    email = config['patreon']['email']
    password = config['patreon']['password']

    # Test authentication
    auth = PatreonAuth(email, password)

    # Try to load existing session first
    if auth.load_session():
        print("✅ Using existing session")
    else:
        print("🔐 No valid session found, logging in...")
        if auth.login():
            print("✅ Login successful!")
            auth.save_session()
        else:
            print("❌ Login failed!")
            return

    # Test getting current user
    user = auth.get_current_user()
    if user:
        print(f"\n👤 Logged in as: {user['data']['attributes']['full_name']}")
        print(f"📧 Email: {user['data']['attributes']['email']}")


if __name__ == "__main__":
    main()
