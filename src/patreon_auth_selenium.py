#!/usr/bin/env python3
"""
Patreon Authentication with Selenium
Uses browser automation to bypass anti-bot protections
"""

import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatreonAuthSelenium:
    """Handles Patreon authentication using Selenium"""

    BASE_URL = "https://www.patreon.com"

    def __init__(self, email: str, password: str, headless: bool = False):
        """
        Initialize authenticator

        Args:
            email: Patreon account email
            password: Patreon account password
            headless: Run browser in headless mode
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None
        self.cookies = None

    def _init_driver(self):
        """Initialize Chrome WebDriver"""
        options = Options()

        if self.headless:
            options.add_argument('--headless')

        # Anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        logger.info("🚀 Chrome WebDriver initialized")

    def login(self, manual_mode: bool = False) -> bool:
        """
        Authenticate with Patreon

        Args:
            manual_mode: If True, allows manual login in browser window

        Returns:
            bool: True if login successful
        """
        try:
            self._init_driver()

            logger.info(f"🔐 Navigating to Patreon login...")
            self.driver.get(f"{self.BASE_URL}/login")

            time.sleep(3)  # Wait for page load

            # Try to accept cookies first (might appear on login page)
            self._accept_cookies()

            if manual_mode:
                logger.info("=" * 60)
                logger.info("MANUAL LOGIN MODE")
                logger.info("=" * 60)
                logger.info("Please login manually in the browser window")
                logger.info("Press ENTER when you're logged in and on your feed...")
                logger.info("=" * 60)
                input()
            else:
                # Automatic login
                logger.info(f"🔑 Attempting automatic login for {self.email}")

                try:
                    # Wait for email field and make sure it's visible
                    email_field = WebDriverWait(self.driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input#email"))
                    )
                    email_field.clear()
                    time.sleep(0.5)
                    email_field.send_keys(self.email)
                    logger.info("✓ Email entered")

                    time.sleep(2)

                    # Wait for password field to be visible and interactable
                    password_field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input#password"))
                    )
                    password_field.clear()
                    time.sleep(0.5)
                    password_field.send_keys(self.password)
                    logger.info("✓ Password entered")

                    time.sleep(2)

                    # Find and click login button - try multiple selectors
                    login_selectors = [
                        "button[type='submit']",
                        "button[data-tag='submit-button']",
                        "button:contains('Log in')",
                        "[data-tag='login-button']"
                    ]

                    login_button = None
                    for selector in login_selectors:
                        try:
                            login_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            break
                        except:
                            continue

                    if not login_button:
                        # Try finding by text
                        login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Sign in')]")

                    login_button.click()
                    logger.info("✓ Login button clicked")

                    # Wait for redirect to feed/home
                    time.sleep(8)

                except Exception as e:
                    logger.error(f"Error during automatic login: {e}")
                    logger.info("⚠️  Automatic login failed, but will continue...")
                    # Don't switch to manual mode, just continue
                    time.sleep(5)

            # Check if logged in by looking for common elements
            current_url = self.driver.current_url
            logger.info(f"Current URL: {current_url}")

            if "login" in current_url.lower():
                logger.error("❌ Still on login page. Login failed.")
                return False

            # Get all cookies
            self.cookies = self.driver.get_cookies()
            logger.info(f"✅ Login successful! Obtained {len(self.cookies)} cookies")

            # Log cookie names
            cookie_names = [c['name'] for c in self.cookies]
            logger.info(f"Cookies: {', '.join(cookie_names)}")

            return True

        except Exception as e:
            logger.error(f"Exception during login: {e}")
            return False

    def get_session_cookie(self) -> Optional[str]:
        """
        Get session_id cookie value

        Returns:
            str: Session ID if found, None otherwise
        """
        if not self.cookies:
            logger.error("No cookies available. Please login first.")
            return None

        for cookie in self.cookies:
            if cookie['name'] == 'session_id':
                return cookie['value']

        logger.warning("session_id cookie not found")
        return None

    def save_cookies(self, filepath: str = "config/patreon_cookies.json"):
        """
        Save cookies to file

        Args:
            filepath: Path to save cookies
        """
        if not self.cookies:
            logger.warning("No cookies to save")
            return

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.cookies, f, indent=2)

        logger.info(f"💾 Cookies saved to {filepath}")

    def load_cookies(self, filepath: str = "config/patreon_cookies.json") -> bool:
        """
        Load cookies from file and inject into browser

        Args:
            filepath: Path to cookies file

        Returns:
            bool: True if cookies loaded successfully
        """
        try:
            with open(filepath, 'r') as f:
                self.cookies = json.load(f)

            if not self.driver:
                self._init_driver()

            # Go to Patreon first
            self.driver.get(self.BASE_URL)
            time.sleep(2)

            # Inject cookies
            for cookie in self.cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Could not add cookie {cookie['name']}: {e}")

            logger.info(f"📂 Cookies loaded from {filepath}")

            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(2)

            return True

        except FileNotFoundError:
            logger.info(f"No saved cookies found at {filepath}")
            return False
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False

    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated

        Returns:
            bool: True if authenticated
        """
        if not self.driver:
            return False

        try:
            self.driver.get(f"{self.BASE_URL}/home")
            time.sleep(2)

            current_url = self.driver.current_url

            # If redirected to login, not authenticated
            if "login" in current_url.lower():
                return False

            # Check for user menu or other authenticated elements
            try:
                # Look for user avatar/menu (common indicator of being logged in)
                self.driver.find_element(By.CSS_SELECTOR, "[data-tag='user-avatar'], [data-tag='nav-profile-button']")
                logger.info("✅ Authenticated")
                return True
            except:
                # Try alternative check
                if "/home" in current_url or "/posts" in current_url:
                    logger.info("✅ Authenticated (URL check)")
                    return True

                logger.warning("⚠️  Could not verify authentication")
                return False

        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False

    def _accept_cookies(self):
        """Try to accept cookies if banner appears"""
        try:
            # Wait for cookie banner to appear
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@class='accept-or-reject-all-button-row']//button[.//span[text()='Accept all']]"))
            )
            cookie_btn.click()
            logger.info("✅ Accepted cookies")
            time.sleep(1)
            return True
        except Exception as e:
            logger.debug(f"No cookie banner found: {e}")
            return False

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Browser closed")


def main():
    """Test authentication"""
    # Load credentials
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"

    with open(config_path) as f:
        config = json.load(f)

    email = config['patreon']['email']
    password = config['patreon']['password']

    # Test authentication
    auth = PatreonAuthSelenium(email, password, headless=False)

    try:
        # Try to load existing cookies first
        if auth.load_cookies():
            print("📂 Loaded existing cookies, checking if still valid...")
            if auth.is_authenticated():
                print("✅ Cookies are valid! Already logged in")
            else:
                print("⚠️  Cookies expired, need to login again")
                if auth.login(manual_mode=True):  # Use manual mode to be safe
                    print("✅ Login successful!")
                    auth.save_cookies()
        else:
            print("🔐 No saved cookies found, logging in...")
            if auth.login(manual_mode=True):  # Use manual mode to be safe
                print("✅ Login successful!")
                auth.save_cookies()
            else:
                print("❌ Login failed!")
                return

        # Show session cookie
        session_id = auth.get_session_cookie()
        if session_id:
            print(f"\n🔑 Session ID: {session_id[:20]}...")

        print("\nPress ENTER to close browser...")
        input()

    finally:
        auth.close()


if __name__ == "__main__":
    main()
