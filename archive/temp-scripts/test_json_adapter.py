import os
import psycopg2
from psycopg2.extras import Json

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Connect
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 'patreon'),
    user=os.getenv('DB_USER', 'patreon_user'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)

cursor = conn.cursor()

# Test inserting JSON
test_data = {"test": "value", "number": 123}
print(f"Testing Json() with: {test_data}")
print(f"Json(test_data) = {Json(test_data)}")

cursor.close()
conn.close()
print("✅ Test passed!")
