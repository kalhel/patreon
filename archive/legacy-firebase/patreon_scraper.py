#!/usr/bin/env python3
"""
Patreon Post Scraper
Extracts all posts from Patreon creators using Selenium
"""

import json
import time
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from patreon_auth_selenium import PatreonAuthSelenium

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PatreonScraper:
    """Scrapes posts from Patreon creators"""

    def __init__(self, auth: PatreonAuthSelenium):
        """
        Initialize scraper

        Args:
            auth: Authenticated PatreonAuthSelenium instance
        """
        self.auth = auth
        self.driver = auth.driver
        self.posts_data = []

    def scrape_creator(self, creator_url: str, creator_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Scrape all posts from a creator

        Args:
            creator_url: URL to creator's posts page
            creator_id: Creator identifier (e.g., 'headonhistory')
            limit: Maximum number of posts to scrape (None = all)

        Returns:
            List of post dictionaries
        """
        logger.info(f"🎯 Starting scrape for creator: {creator_id}")
        logger.info(f"URL: {creator_url}")

        # Navigate to creator's page
        self.driver.get(creator_url)
        time.sleep(3)

        posts = []
        scroll_pause = 2
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        posts_found = 0

        while True:
            # Extract posts from current view
            new_posts = self._extract_posts_from_page(creator_id)

            # Add only new posts (avoid duplicates)
            for post in new_posts:
                if post['post_id'] not in [p['post_id'] for p in posts]:
                    posts.append(post)
                    posts_found += 1
                    logger.info(f"  ✓ Post {posts_found}: {post['title'][:50]}...")

                    if limit and posts_found >= limit:
                        logger.info(f"✅ Reached limit of {limit} posts")
                        return posts

            # Scroll down to load more posts
            logger.info(f"📜 Scrolling to load more posts... (found {posts_found} so far)")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)

            # Calculate new scroll height and compare
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                # Try one more time to be sure
                logger.info("⏸️  No new content, trying once more...")
                time.sleep(scroll_pause)
                newer_height = self.driver.execute_script("return document.body.scrollHeight")

                if newer_height == new_height:
                    logger.info("✅ Reached end of posts")
                    break

            last_height = new_height

        logger.info(f"🎉 Scraped {len(posts)} posts from {creator_id}")
        return posts

    def _extract_posts_from_page(self, creator_id: str) -> List[Dict]:
        """
        Extract post data from currently loaded page

        Args:
            creator_id: Creator identifier

        Returns:
            List of post dictionaries
        """
        posts = []

        try:
            # Find all post cards/containers
            # Patreon uses various selectors, we'll try multiple approaches
            post_elements = []

            # Try different selectors
            selectors = [
                "[data-tag='post-card']",
                "[data-tag='post-wrapper']",
                "div[class*='PostCard']",
                "div[class*='post-card']",
                "article",
                "div[class*='sc-']"  # Patreon uses styled-components with sc- prefix
            ]

            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                    post_elements = elements
                    break

            if not post_elements:
                logger.warning("No post elements found with any selector")
                return posts

            for element in post_elements:
                try:
                    post_data = self._extract_post_data(element, creator_id)
                    if post_data and post_data.get('post_id'):
                        posts.append(post_data)
                except Exception as e:
                    logger.debug(f"Error extracting post: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error finding post elements: {e}")

        return posts

    def _extract_post_data(self, element, creator_id: str) -> Optional[Dict]:
        """
        Extract data from a single post element

        Args:
            element: Selenium WebElement
            creator_id: Creator identifier

        Returns:
            Dictionary with post data
        """
        try:
            post_data = {
                'creator_id': creator_id,
                'scraped_at': datetime.now().isoformat()
            }

            # Extract post ID from URL
            try:
                links = element.find_elements(By.TAG_NAME, 'a')
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/posts/' in href:
                        # Extract post ID from URL like: https://www.patreon.com/posts/12345678
                        match = re.search(r'/posts/(\d+)', href)
                        if match:
                            post_data['post_id'] = match.group(1)
                            post_data['post_url'] = href
                            break
            except:
                pass

            # If no post_id found, skip this element
            if 'post_id' not in post_data:
                return None

            # Extract title
            try:
                title_selectors = ['h1', 'h2', 'h3', '[data-tag="post-title"]', 'a[href*="/posts/"]']
                for selector in title_selectors:
                    title_elem = element.find_elements(By.CSS_SELECTOR, selector)
                    if title_elem:
                        title = title_elem[0].text.strip()
                        if title and len(title) > 3:  # Avoid empty or too short titles
                            post_data['title'] = title
                            break
            except:
                pass

            if 'title' not in post_data:
                post_data['title'] = f"Post {post_data['post_id']}"

            # Extract preview text/content
            try:
                text_elem = element.find_element(By.CSS_SELECTOR, '[data-tag="post-content"], [data-tag="post-card-teaser"], div[class*="content"]')
                post_data['preview_text'] = text_elem.text.strip()
            except:
                post_data['preview_text'] = ""

            # Extract publication date
            try:
                time_elem = element.find_element(By.TAG_NAME, 'time')
                date_str = time_elem.get_attribute('datetime')
                if date_str:
                    post_data['published_at'] = date_str
                else:
                    post_data['published_at'] = time_elem.text.strip()
            except:
                post_data['published_at'] = ""

            # Extract images (thumbnail/preview)
            try:
                images = element.find_elements(By.TAG_NAME, 'img')
                image_urls = []
                for img in images:
                    src = img.get_attribute('src')
                    if src and 'patreon' in src and not src.endswith('.svg'):
                        image_urls.append(src)
                post_data['preview_images'] = image_urls
            except:
                post_data['preview_images'] = []

            # Extract tier/access level
            try:
                tier_elem = element.find_element(By.CSS_SELECTOR, '[data-tag="post-access-badge"], [class*="tier"]')
                post_data['access_tier'] = tier_elem.text.strip()
            except:
                post_data['access_tier'] = ""

            # Extract engagement (likes, comments)
            try:
                likes_elem = element.find_element(By.CSS_SELECTOR, '[data-tag="like-count"], [class*="like"]')
                post_data['likes'] = likes_elem.text.strip()
            except:
                post_data['likes'] = ""

            try:
                comments_elem = element.find_element(By.CSS_SELECTOR, '[data-tag="comment-count"], [class*="comment"]')
                post_data['comments'] = comments_elem.text.strip()
            except:
                post_data['comments'] = ""

            # Extract Patreon native tags
            try:
                tag_elements = element.find_elements(By.CSS_SELECTOR, '[data-tag="post-tag"], [class*="tag"], a[href*="/posts/tag/"]')
                patreon_tags = []
                for tag_elem in tag_elements:
                    tag_text = tag_elem.text.strip()
                    if tag_text and len(tag_text) > 1 and len(tag_text) < 50:
                        patreon_tags.append(tag_text.lower())
                post_data['patreon_tags'] = list(set(patreon_tags))  # Remove duplicates
            except:
                post_data['patreon_tags'] = []

            return post_data

        except Exception as e:
            logger.debug(f"Error extracting post data: {e}")
            return None

    def scrape_post_detail(self, post_url: str) -> Optional[Dict]:
        """
        Scrape full content of a single post

        Args:
            post_url: URL to the post

        Returns:
            Dictionary with full post data
        """
        logger.info(f"📄 Scraping post detail: {post_url}")

        self.driver.get(post_url)
        time.sleep(2)

        post_detail = {
            'post_url': post_url,
            'scraped_at': datetime.now().isoformat()
        }

        try:
            # Extract full title
            title = self.driver.find_element(By.CSS_SELECTOR, 'h1, [data-tag="post-title"]').text.strip()
            post_detail['title'] = title
        except:
            pass

        try:
            # Extract full content
            content = self.driver.find_element(By.CSS_SELECTOR, '[data-tag="post-content"], [class*="content"]').text.strip()
            post_detail['full_content'] = content
        except:
            post_detail['full_content'] = ""

        try:
            # Extract all images
            images = self.driver.find_elements(By.CSS_SELECTOR, '[data-tag="post-content"] img, [class*="content"] img')
            post_detail['images'] = [img.get_attribute('src') for img in images if img.get_attribute('src')]
        except:
            post_detail['images'] = []

        try:
            # Extract videos
            videos = self.driver.find_elements(By.CSS_SELECTOR, 'video, [data-tag="video"]')
            video_urls = []
            for video in videos:
                src = video.get_attribute('src')
                if src:
                    video_urls.append(src)
                # Check for source tags
                sources = video.find_elements(By.TAG_NAME, 'source')
                for source in sources:
                    src = source.get_attribute('src')
                    if src:
                        video_urls.append(src)
            post_detail['videos'] = video_urls
        except:
            post_detail['videos'] = []

        try:
            # Extract audio
            audios = self.driver.find_elements(By.CSS_SELECTOR, 'audio, [data-tag="audio"]')
            audio_urls = []
            for audio in audios:
                src = audio.get_attribute('src')
                if src:
                    audio_urls.append(src)
                # Check for source tags
                sources = audio.find_elements(By.TAG_NAME, 'source')
                for source in sources:
                    src = source.get_attribute('src')
                    if src:
                        audio_urls.append(src)
            post_detail['audios'] = audio_urls
        except:
            post_detail['audios'] = []

        try:
            # Extract attachments/downloads
            attachments = self.driver.find_elements(By.CSS_SELECTOR, 'a[download], [data-tag="attachment"]')
            post_detail['attachments'] = [a.get_attribute('href') for a in attachments if a.get_attribute('href')]
        except:
            post_detail['attachments'] = []

        try:
            # Extract Patreon native tags from post detail page
            tag_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-tag="post-tag"], [class*="tag"], a[href*="/posts/tag/"]')
            patreon_tags = []
            for tag_elem in tag_elements:
                tag_text = tag_elem.text.strip()
                if tag_text and len(tag_text) > 1 and len(tag_text) < 50:
                    patreon_tags.append(tag_text.lower())
            post_detail['patreon_tags'] = list(set(patreon_tags))
        except:
            post_detail['patreon_tags'] = []

        logger.info(f"  ✓ Title: {post_detail.get('title', 'N/A')}")
        logger.info(f"  ✓ Images: {len(post_detail.get('images', []))}")
        logger.info(f"  ✓ Videos: {len(post_detail.get('videos', []))}")
        logger.info(f"  ✓ Audios: {len(post_detail.get('audios', []))}")
        logger.info(f"  ✓ Patreon Tags: {len(post_detail.get('patreon_tags', []))}")

        return post_detail

    def save_posts(self, posts: List[Dict], creator_id: str, output_dir: str = "data/raw"):
        """
        Save posts to JSON file

        Args:
            posts: List of post dictionaries
            creator_id: Creator identifier
            output_dir: Directory to save JSON file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = output_path / f"{creator_id}_posts.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Saved {len(posts)} posts to {filename}")


def main():
    """Test scraper"""
    # Load config
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"

    with open(config_path) as f:
        config = json.load(f)

    email = config['patreon']['email']
    password = config['patreon']['password']
    creators = config['patreon']['creators']

    # Initialize authentication
    auth = PatreonAuthSelenium(email, password, headless=False)

    try:
        # Try to load existing cookies
        if auth.load_cookies():
            logger.info("📂 Loaded existing cookies")
            if not auth.is_authenticated():
                logger.warning("Cookies expired, need to login")
                if not auth.login(manual_mode=True):
                    logger.error("Login failed")
                    return
                auth.save_cookies()
        else:
            logger.info("🔐 Logging in...")
            if not auth.login(manual_mode=True):
                logger.error("Login failed")
                return
            auth.save_cookies()

        # Initialize scraper
        scraper = PatreonScraper(auth)

        # Scrape first creator as test
        creator = creators[0]
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing with: {creator['name']}")
        logger.info(f"{'='*60}\n")

        # Scrape posts (limit to 5 for testing)
        posts = scraper.scrape_creator(
            creator_url=creator['url'],
            creator_id=creator['creator_id'],
            limit=5  # Change to None to scrape all posts
        )

        # Save posts
        scraper.save_posts(posts, creator['creator_id'])

        # Scrape full details of first post
        if posts:
            logger.info(f"\n{'='*60}")
            logger.info("Scraping full details of first post")
            logger.info(f"{'='*60}\n")

            post_detail = scraper.scrape_post_detail(posts[0]['post_url'])

            # Save detailed post
            detail_path = Path("data/raw") / f"{creator['creator_id']}_post_{posts[0]['post_id']}_detail.json"
            with open(detail_path, 'w', encoding='utf-8') as f:
                json.dump(post_detail, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Saved detailed post to {detail_path}")

        logger.info("\n✅ Test complete!")
        logger.info("Press ENTER to close browser...")
        input()

    finally:
        auth.close()


if __name__ == "__main__":
    main()
