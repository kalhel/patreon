#!/usr/bin/env python3
"""Debug script to check DATABASE_URL configuration"""

import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

print("=" * 60)
print("  Database Configuration Debug")
print("=" * 60)
print()

# Check individual vars
print("Individual variables:")
print(f"  DB_NAME: {os.getenv('DB_NAME', 'NOT SET')}")
print(f"  DB_USER: {os.getenv('DB_USER', 'NOT SET')}")
print(f"  DB_PASSWORD: {os.getenv('DB_PASSWORD', 'NOT SET')}")
print(f"  DB_HOST: {os.getenv('DB_HOST', 'NOT SET')}")
print(f"  DB_PORT: {os.getenv('DB_PORT', 'NOT SET')}")
print()

# Check DATABASE_URL
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("❌ DATABASE_URL: NOT SET")
    print()
    print("Solution:")
    print("  Add this to your .env file:")
    print()
    db_name = os.getenv('DB_NAME', 'alejandria')
    db_user = os.getenv('DB_USER', 'patreon_user')
    db_pass = os.getenv('DB_PASSWORD', 'YOUR_PASSWORD')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')

    # URL encode password if it contains @
    if '@' in db_pass and db_pass != 'YOUR_PASSWORD':
        db_pass_encoded = db_pass.replace('@', '%40')
        print(f"  DATABASE_URL=postgresql://{db_user}:{db_pass_encoded}@{db_host}:{db_port}/{db_name}")
    else:
        print(f"  DATABASE_URL=postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")
else:
    print(f"✅ DATABASE_URL: {db_url}")
    print()

    # Parse it
    parsed = urlparse(db_url)
    print("Parsed components:")
    print(f"  Scheme: {parsed.scheme}")
    print(f"  Hostname: {parsed.hostname}")
    print(f"  Port: {parsed.port}")
    print(f"  Username: {parsed.username}")
    print(f"  Password: {'*' * len(parsed.password) if parsed.password else 'NOT SET'}")
    print(f"  Database: {parsed.path.lstrip('/')}")
    print()

    if not parsed.password:
        print("❌ WARNING: Password not found in DATABASE_URL!")
        print("   Make sure your DATABASE_URL includes the password.")
        print("   If password contains @, use %40 instead.")

print("=" * 60)
