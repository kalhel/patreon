#!/usr/bin/env python3
"""Test to explore comment structure in Patreon"""

import sys
sys.path.insert(0, 'src')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# Setup Chrome
chrome_options = Options()
# chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')

driver = webdriver.Chrome(options=chrome_options)

# Load a post with comments
url = "https://www.patreon.com/posts/jinn-history-and-142355366"
print(f"Loading {url}...")
driver.get(url)
time.sleep(5)

# Scroll to load comments
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(3)

# Find all comment containers
comments = driver.find_elements(By.CSS_SELECTOR, '[data-tag="comment-body"]')
print(f"\nFound {len(comments)} comments")

# Explore first few comments structure
for i, comment in enumerate(comments[:3], 1):
    print(f"\n{'='*60}")
    print(f"Comment {i}:")
    print(f"{'='*60}")
    
    # Get parent elements to see structure
    parent = comment
    levels = []
    for level in range(10):
        try:
            parent = parent.find_element(By.XPATH, '..')
            tag_name = parent.tag_name
            classes = parent.get_attribute('class') or ''
            data_tag = parent.get_attribute('data-tag') or ''
            
            if data_tag or 'comment' in classes.lower() or 'reply' in classes.lower():
                levels.append(f"  Level {level}: <{tag_name}> data-tag='{data_tag}' class='{classes[:50]}'")
        except:
            break
    
    print("Parent hierarchy:")
    for l in levels:
        print(l)
    
    # Check for reply indicators
    try:
        # Look for nested comment containers
        parent_container = comment.find_element(By.XPATH, '../..')
        nested = parent_container.find_elements(By.CSS_SELECTOR, '[data-tag="comment-body"]')
        if len(nested) > 1:
            print(f"  → Found {len(nested)} nested comments in parent container")
    except:
        pass

driver.quit()
print("\nDone!")
