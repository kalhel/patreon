#!/usr/bin/env python3
"""
Test script to debug Patreon login
"""

import json
from pathlib import Path
from src.patreon_auth_selenium import PatreonAuthSelenium
import time

# Load credentials
config_path = Path("config/credentials.json")
with open(config_path) as f:
    config = json.load(f)

email = config['patreon']['email']
password = config['patreon']['password']

print("🧪 Testing Patreon Login...")
print(f"Email: {email}")
print(f"Password: {'*' * len(password)}")
print()

# Initialize auth (not headless for debugging)
auth = PatreonAuthSelenium(email, password, headless=False)

try:
    # Try login
    print("🔐 Attempting login...")
    success = auth.login(manual_mode=False)

    if success:
        print("✅ Login successful!")

        # Take screenshot
        auth.driver.save_screenshot("logs/login_success.png")
        print("📸 Screenshot saved: logs/login_success.png")

        # Save cookies
        auth.save_cookies()
        print("🍪 Cookies saved")

        # Check authentication
        if auth.is_authenticated():
            print("✅ Authentication verified!")
        else:
            print("⚠️  Login succeeded but authentication check failed")
    else:
        print("❌ Login failed")

        # Take screenshot of failure
        auth.driver.save_screenshot("logs/login_failed.png")
        print("📸 Screenshot saved: logs/login_failed.png")
        print(f"📍 Current URL: {auth.driver.current_url}")

    print()
    print("Press ENTER to close browser...")
    input()

finally:
    auth.close()
    print("🎉 Test complete")
