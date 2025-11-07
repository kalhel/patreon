#!/usr/bin/env python3
"""
Patreon Post Scraper V2 - Improved version
Handles lazy loading with "Load more" button
Uses updated selectors for current Patreon structure
"""

import json
import time
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from patreon_auth_selenium import PatreonAuthSelenium
from content_parser import parse_post_page


def parse_relative_date(date_text: str) -> Optional[str]:
    """
    Convert relative date text (e.g., '3 days ago') to ISO format date

    Args:
        date_text: Relative date string like '3 days ago', '2 hours ago', etc.

    Returns:
        ISO format date string (YYYY-MM-DD) or None if cannot parse
    """
    if not date_text:
        return None

    date_text = date_text.lower().strip()
    now = datetime.now()

    # Pattern: "X units ago"
    match = re.match(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', date_text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        if unit == 'second':
            target_date = now - timedelta(seconds=amount)
        elif unit == 'minute':
            target_date = now - timedelta(minutes=amount)
        elif unit == 'hour':
            target_date = now - timedelta(hours=amount)
        elif unit == 'day':
            target_date = now - timedelta(days=amount)
        elif unit == 'week':
            target_date = now - timedelta(weeks=amount)
        elif unit == 'month':
            target_date = now - timedelta(days=amount*30)  # Approximate
        elif unit == 'year':
            target_date = now - timedelta(days=amount*365)  # Approximate
        else:
            return None

        return target_date.strftime('%Y-%m-%d')

    # Handle "yesterday"
    if 'yesterday' in date_text:
        target_date = now - timedelta(days=1)
        return target_date.strftime('%Y-%m-%d')

    # Handle "today"
    if 'today' in date_text:
        return now.strftime('%Y-%m-%d')

    return None

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


class PatreonScraperV2:
    """Improved scraper for Patreon posts with Load More button support"""

    PATREON_API_POST_URL = "https://www.patreon.com/api/posts/{post_id}?include=media,attachments,post_file"

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
            creator_id: Creator identifier
            limit: Maximum number of posts to scrape (None = all)

        Returns:
            List of post dictionaries
        """
        logger.info(f"🎯 Starting scrape for creator: {creator_id}")
        logger.info(f"URL: {creator_url}")

        # Navigate to creator's page
        self.driver.get(creator_url)

        # Wait for initial content to load
        logger.info("⏳ Waiting for posts to load...")
        time.sleep(3)

        # Accept cookies if banner appears (using exact selector from HTML)
        try:
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//div[@class='accept-or-reject-all-button-row']//button[.//span[text()='Accept all']]"))
            )
            cookie_btn.click()
            logger.info("✅ Accepted cookies")
            time.sleep(1)
        except Exception as e:
            logger.debug(f"No cookie banner found or already accepted: {e}")

        time.sleep(2)

        posts = []
        click_count = 0
        no_new_posts_count = 0  # Track consecutive times with no new posts

        # Accept cookies at the beginning
        self._accept_cookies_if_present()

        while True:
            # Extract posts from current view
            new_posts = self._extract_posts_from_page(creator_id)

            # Add only new posts (avoid duplicates)
            posts_before = len(posts)
            for post in new_posts:
                if post['post_id'] not in [p['post_id'] for p in posts]:
                    posts.append(post)
                    logger.info(f"  ✓ Post {len(posts)}: {post['title'][:60] if post['title'] else post['post_id']}")

                    if limit and len(posts) >= limit:
                        logger.info(f"✅ Reached limit of {limit} posts")
                        return posts

            # Check if we got new posts
            posts_after = len(posts)
            if posts_after == posts_before:
                no_new_posts_count += 1
                logger.info(f"⚠️  No new posts found in this batch ({no_new_posts_count}/3)")

                # If no new posts found 3 times in a row, stop
                if no_new_posts_count >= 3:
                    logger.info(f"✅ No new posts after 3 attempts - reached end")
                    break
            else:
                no_new_posts_count = 0  # Reset counter when we find new posts

            # Accept cookies if they popup again
            self._accept_cookies_if_present()

            # Try to click "Load more" button
            click_count += 1
            logger.info(f"🔄 Attempting to click 'Load more' button ({click_count})...")

            if self._click_load_more():
                logger.info(f"✅ Clicked 'Load more' button")
                time.sleep(3)  # Wait for new content to load
            else:
                logger.info(f"⚠️  'Load more' button not found - may have reached end")
                # If button not found, we're at the end
                break

        logger.info(f"🎉 Scraped {len(posts)} posts from {creator_id}")
        return posts

    def _accept_cookies_if_present(self):
        """Silently try to accept cookies without logging if not found"""
        try:
            # The exact selector for Patreon's cookie banner (based on HTML structure)
            cookie_btn = self.driver.find_element(
                By.XPATH,
                "//div[@class='accept-or-reject-all-button-row']//button[.//span[text()='Accept all']]"
            )
            if cookie_btn.is_displayed():
                cookie_btn.click()
                logger.debug("✅ Dismissed cookie banner")
                time.sleep(1)
                return True
        except:
            pass
        return False

    def _click_load_more(self) -> bool:
        """
        Find and click the "Load more" button

        Returns:
            True if button was found and clicked, False otherwise
        """
        # Scroll to bottom multiple times to make sure we reach the actual bottom
        # (sometimes the page height increases as we scroll)
        for _ in range(3):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

        # Wait a bit more to ensure lazy-loaded content appears
        time.sleep(1)

        # Try multiple selectors for Load More button
        # IMPORTANT: Exclude "comments" to avoid clicking "Load more comments"
        # Using specific selectors from actual Patreon HTML structure
        selectors = [
            # Specific selector based on actual Patreon HTML structure
            "//button[@aria-disabled='false'][@type='button']//div[contains(@class, 'cm-oHFIQB') and text()='Load more']",
            # Alternative: find button containing div with "Load more" text (not comments)
            "//button[@aria-disabled='false'][@type='button'][.//div[text()='Load more']]",
            # Generic but safe selectors
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more') and not(contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'comment'))]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more') and not(contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'comment'))]",
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more') and not(contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'comment'))]",
            "//button[text()='Load more' or text()='load more' or text()='LOAD MORE']",
            "//button[contains(@class, 'load-more') and not(contains(@class, 'comment'))]",
            "//div[contains(@data-tag, 'load-more') and not(contains(@data-tag, 'comment'))]//button",
        ]

        for i, selector in enumerate(selectors):
            try:
                # Try to find the button
                button = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )

                # Log which selector worked
                logger.debug(f"Found 'Load more' button with selector #{i+1}: {selector}")

                # Scroll to button to make it visible
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(0.5)

                # Try regular click first
                try:
                    button.click()
                    logger.debug(f"Clicked button with regular click")
                    return True
                except Exception as e:
                    logger.debug(f"Regular click failed: {e}, trying JavaScript click")
                    # If regular click fails, use JavaScript click
                    self.driver.execute_script("arguments[0].click();", button)
                    logger.debug(f"Clicked button with JavaScript click")
                    return True

            except (TimeoutException, NoSuchElementException) as e:
                logger.debug(f"Selector #{i+1} failed: {type(e).__name__}")
                continue

        logger.debug("No 'Load more' button found with any selector")
        return False

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
            # Try to find all post containers
            # Patreon uses div elements with specific attributes or classes
            selectors = [
                "[data-tag='post-card']",
                "div[data-tag='post-card']",
                "article",
                "div[class*='PostCard']",
                "a[href*='/posts/']",  # Links to posts
            ]

            post_elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > len(post_elements):
                        post_elements = elements
                        logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                except:
                    continue

            if not post_elements:
                logger.warning("⚠️  No post elements found with any selector")

                # Try to get page source for debugging
                page_html = self.driver.page_source
                if "posts" in page_html.lower():
                    logger.warning("Page contains 'posts' text but no post elements found")
                    logger.warning("This might be a structure issue")

                return posts

            logger.debug(f"Processing {len(post_elements)} potential post elements")

            for element in post_elements:
                try:
                    post_data = self._extract_post_data(element, creator_id)
                    if post_data and post_data.get('post_id'):
                        # Check if we already have this post
                        if not any(p['post_id'] == post_data['post_id'] for p in posts):
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

            # Extract post URL and ID
            try:
                # Try to get href from the element or find a link inside
                href = element.get_attribute('href')

                if not href:
                    # Look for links inside the element
                    links = element.find_elements(By.CSS_SELECTOR, "a[href*='/posts/']")
                    if links:
                        href = links[0].get_attribute('href')

                if href and '/posts/' in href:
                    post_data['post_url'] = href

                    # Extract post ID from URL
                    # URL format: https://www.patreon.com/posts/title-here-12345678
                    match = re.search(r'/posts/[^/]+-(\d+)', href)
                    if match:
                        post_data['post_id'] = match.group(1)
                    else:
                        # Try simpler pattern
                        match = re.search(r'/posts/(\d+)', href)
                        if match:
                            post_data['post_id'] = match.group(1)
            except Exception as e:
                logger.debug(f"Error extracting URL: {e}")

            # If no post_id found, skip this element
            if 'post_id' not in post_data:
                return None

            # Extract title
            try:
                # Try multiple selectors for title
                title_selectors = [
                    'h1', 'h2', 'h3',
                    '[data-tag="post-title"]',
                    'span[class*="title"]',
                    'div[class*="title"]'
                ]

                for selector in title_selectors:
                    title_elems = element.find_elements(By.CSS_SELECTOR, selector)
                    if title_elems:
                        title = title_elems[0].text.strip()
                        if title and len(title) > 3:
                            post_data['title'] = title
                            break
            except:
                pass

            if 'title' not in post_data:
                post_data['title'] = f"Post {post_data['post_id']}"

            # Extract preview text
            try:
                text_selectors = [
                    '[data-tag="post-content"]',
                    '[data-tag="post-card-teaser"]',
                    'div[class*="content"]',
                    'p'
                ]

                for selector in text_selectors:
                    text_elems = element.find_elements(By.CSS_SELECTOR, selector)
                    if text_elems:
                        text = text_elems[0].text.strip()
                        if text:
                            post_data['preview_text'] = text[:500]  # Limit length
                            break
            except:
                pass

            if 'preview_text' not in post_data:
                post_data['preview_text'] = ""

            # Extract publication date
            try:
                time_elem = element.find_elements(By.TAG_NAME, 'time')
                if time_elem:
                    date_str = time_elem[0].get_attribute('datetime')
                    if date_str:
                        post_data['published_at'] = date_str
                    else:
                        post_data['published_at'] = time_elem[0].text.strip()
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
                post_data['preview_images'] = list(set(image_urls))  # Remove duplicates
            except:
                post_data['preview_images'] = []

            # Extract Patreon native tags
            try:
                tag_elements = element.find_elements(By.CSS_SELECTOR, '[data-tag="post-tag"], a[href*="/posts/tag/"]')
                patreon_tags = []
                for tag_elem in tag_elements:
                    tag_text = tag_elem.text.strip()
                    if tag_text and len(tag_text) > 1 and len(tag_text) < 50:
                        patreon_tags.append(tag_text.lower())
                post_data['patreon_tags'] = list(set(patreon_tags))
            except:
                post_data['patreon_tags'] = []

            # Extract other metadata
            post_data['access_tier'] = ""
            post_data['likes'] = ""
            post_data['comments'] = ""

            return post_data

        except Exception as e:
            logger.debug(f"Error extracting post data: {e}")
            return None

    def scrape_post_detail(self, post_url: str, post_id: Optional[str] = None) -> Optional[Dict]:
        """
        Scrape full content of a single post

        Args:
            post_url: URL to the post

        Returns:
            Dictionary with full post data
        """
        logger.info(f"📄 Scraping post detail: {post_url}")

        self.driver.get(post_url)
        time.sleep(3)  # Wait for post to load

        post_detail = {
            'post_url': post_url,
            'scraped_at': datetime.now().isoformat()
        }

        if post_id:
            post_detail['post_id'] = str(post_id)

        if 'post_id' not in post_detail:
            match = re.search(r'(\d+)(?:$|[/?#])', post_url)
            if match:
                post_detail['post_id'] = match.group(1)

        try:
            # Extract full title
            title_selectors = ['h1', '[data-tag="post-title"]', 'h2']
            for selector in title_selectors:
                try:
                    title = self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if title:
                        post_detail['title'] = title
                        break
                except:
                    continue
        except:
            pass

        try:
            # Parse entire page including JSON-LD embeds, content, and comments
            parsed_data = parse_post_page(self.driver)
            post_detail['content_blocks'] = parsed_data.get('blocks', [])
            post_detail['post_metadata'] = parsed_data.get('metadata', {})

            # Also extract plain text for backward compatibility
            try:
                content_selectors = [
                    '[data-tag="post-content"]',
                    '[class*="post-content"]',
                    'div[class*="content"]',
                    'article',
                    'main'
                ]

                content_element = None
                for selector in content_selectors:
                    try:
                        content_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if content_element:
                            break
                    except:
                        continue

                if content_element:
                    post_detail['full_content'] = content_element.text.strip()
                else:
                    post_detail['full_content'] = ""
            except:
                post_detail['full_content'] = ""

        except Exception as e:
            logger.error(f"Error parsing content blocks: {e}")
            post_detail['content_blocks'] = []
            post_detail['full_content'] = ""

        try:
            # Extract ONLY content images (not avatars, covers, or thumbnails)
            # Strategy: Use specific selectors for content images and exclude avatar patterns
            image_urls = []

            # Method 1: Images with data-media-id (most reliable for content images)
            content_images = self.driver.find_elements(By.CSS_SELECTOR, 'img[data-media-id]')
            for img in content_images:
                src = img.get_attribute('src')
                if src and 'patreonusercontent.com' in src:
                    image_urls.append(src)

            # Method 2: Images inside <figure> tags (common for post content)
            figure_images = self.driver.find_elements(By.CSS_SELECTOR, 'figure img')
            for img in figure_images:
                src = img.get_attribute('src')
                if src and 'patreonusercontent.com' in src:
                    image_urls.append(src)

            # Method 3: Images in post content containers (but exclude avatars)
            # Exclude: comment avatars (data-tag="comment-send-avatar"), creator profile pics
            all_images = self.driver.find_elements(By.CSS_SELECTOR, 'img')
            for img in all_images:
                try:
                    src = img.get_attribute('src')
                    if not src or 'patreonusercontent.com' not in src:
                        continue

                    # Skip if already captured
                    if src in image_urls:
                        continue

                    # Exclude avatars by URL pattern
                    if '/p/campaign/' in src or '/p/user/' in src:
                        continue

                    # Exclude avatars by data-tag
                    data_tag = img.get_attribute('data-tag')
                    if data_tag and 'avatar' in data_tag.lower():
                        continue

                    # Exclude by alt text
                    alt = img.get_attribute('alt')
                    if alt and ('profile picture' in alt.lower() or 'avatar' in alt.lower()):
                        continue

                    # Exclude by parent class (comment avatars have specific parent classes)
                    try:
                        parent = img.find_element(By.XPATH, '..')
                        parent_class = parent.get_attribute('class') or ''
                        # cm-MCtAYf is used for comment avatars
                        if 'cm-MCtAYf' in parent_class:
                            continue
                    except:
                        pass

                    # If URL contains /p/post/ it's likely content
                    if '/p/post/' in src:
                        image_urls.append(src)

                except Exception as e:
                    continue

            post_detail['images'] = list(set(image_urls))
            logger.info(f"  📸 Extracted {len(post_detail['images'])} content images (avatars excluded)")

        except Exception as e:
            logger.warning(f"  ⚠️  Error extracting images: {e}")
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
            post_detail['videos'] = list(set(video_urls))
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
                sources = audio.find_elements(By.TAG_NAME, 'source')
                for source in sources:
                    src = source.get_attribute('src')
                    if src:
                        audio_urls.append(src)
            post_detail['audios'] = list(set(audio_urls))
        except:
            post_detail['audios'] = []

        try:
            # Extract Patreon native tags from detail page
            tag_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-tag="post-tag"], a[href*="/posts/tag/"]')
            patreon_tags = []
            for tag_elem in tag_elements:
                tag_text = tag_elem.text.strip()
                if tag_text and len(tag_text) > 1 and len(tag_text) < 50:
                    patreon_tags.append(tag_text.lower())
            post_detail['patreon_tags'] = list(set(patreon_tags))
        except:
            post_detail['patreon_tags'] = []

        try:
            # Extract like count
            like_selectors = [
                '[data-tag="post-card-like-count"]',
                '[aria-label*="like"]',
                'button[aria-label*="Like"] ~ span',
                'button:has(svg[data-tag="icon-like"]) span'
            ]
            for selector in like_selectors:
                try:
                    like_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    like_text = like_elem.text.strip()
                    if like_text and like_text.isdigit():
                        post_detail['like_count'] = int(like_text)
                        break
                except:
                    continue
            if 'like_count' not in post_detail:
                post_detail['like_count'] = 0
        except:
            post_detail['like_count'] = 0

        try:
            # Extract published date
            date_selectors = [
                '[data-tag="post-published-at"]',
                'time[datetime]',
                '[data-tag="post-date"]',
                'time',
                '[data-tag="post-card"] time',
                'div[data-tag*="date"]'
            ]
            for selector in date_selectors:
                try:
                    date_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    # Try to get datetime attribute first
                    datetime_attr = date_elem.get_attribute('datetime')
                    if datetime_attr:
                        # Extract just the date part (YYYY-MM-DD)
                        if 'T' in datetime_attr:
                            post_detail['published_at'] = datetime_attr.split('T')[0]
                        else:
                            post_detail['published_at'] = datetime_attr
                        break
                    # Otherwise get text content and try to parse
                    date_text = date_elem.text.strip()
                    if date_text:
                        # Try to parse relative date (e.g., "3 days ago")
                        parsed_date = parse_relative_date(date_text)
                        if parsed_date:
                            post_detail['published_at'] = parsed_date
                            break
                        # Otherwise store as is
                        post_detail['published_at'] = date_text
                        break
                except:
                    continue
            if 'published_at' not in post_detail:
                post_detail['published_at'] = None
        except:
            post_detail['published_at'] = None

        try:
            # Extract creator avatar - try multiple strategies
            avatar_selectors = [
                'img[data-tag="creator-avatar"]',
                'img[data-tag*="avatar"]',
                'a[data-tag="creator-page-link"] img',
                'a[href*="/user/"] img',
                '[data-tag*="creator"] img',
                'header img',
                'article img'
            ]
            for selector in avatar_selectors:
                try:
                    avatar_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    avatar_url = avatar_elem.get_attribute('src')
                    # Accept any patreon image URL (they host avatars on patreonusercontent.com)
                    if avatar_url and ('patreon' in avatar_url.lower() or 'http' in avatar_url):
                        post_detail['creator_avatar'] = avatar_url
                        logger.info(f"  ✓ Creator avatar: {avatar_url[:60]}...")
                        break
                except:
                    continue
            if 'creator_avatar' not in post_detail:
                post_detail['creator_avatar'] = None
        except:
            post_detail['creator_avatar'] = None

        try:
            # Extract attachments
            attachments = self.driver.find_elements(By.CSS_SELECTOR, 'a[download], [data-tag="attachment"]')
            post_detail['attachments'] = [a.get_attribute('href') for a in attachments if a.get_attribute('href')]
        except:
            post_detail['attachments'] = []

        logger.info(f"  ✓ Title: {post_detail.get('title', 'N/A')}")
        logger.info(f"  ✓ Published: {post_detail.get('published_at', 'N/A')}")
        logger.info(f"  ✓ Likes: {post_detail.get('like_count', 0)}")
        logger.info(f"  ✓ Content Blocks: {len(post_detail.get('content_blocks', []))}")
        logger.info(f"  ✓ Images: {len(post_detail.get('images', []))}")
        logger.info(f"  ✓ Videos: {len(post_detail.get('videos', []))}")
        logger.info(f"  ✓ Audios: {len(post_detail.get('audios', []))}")
        logger.info(f"  ✓ Patreon Tags: {len(post_detail.get('patreon_tags', []))}")

        try:
            self._enrich_video_sources(post_detail)
        except Exception as enrich_error:
            logger.debug(f"    ⚠️  Could not enrich video sources: {enrich_error}")

        # Append Mux playback URLs if present
        try:
            self._append_mux_streams(post_detail)
        except Exception as mux_error:
            logger.debug(f"    ⚠️  Could not append Mux streams: {mux_error}")

        return post_detail

    def _fetch_post_api(self, post_id: str) -> Optional[Dict]:
        """Call Patreon API for a post using cookies from the Selenium session"""

        try:
            session = requests.Session()
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])

            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.patreon.com/'
            })

            url = self.PATREON_API_POST_URL.format(post_id=post_id)
            response = session.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
            logger.debug(f"    ⚠️  Patreon API returned {response.status_code} for post {post_id}")
        except Exception as api_error:
            logger.debug(f"    ⚠️  Error calling Patreon API for post {post_id}: {api_error}")
        return None

    def _enrich_video_sources(self, post_detail: Dict):
        """Fetch additional downloadable/stream URLs for Patreon-hosted videos"""

        post_id = post_detail.get('post_id')
        if not post_id:
            return

        existing_videos = post_detail.get('videos', []) or []
        needs_lookup = not existing_videos or any(url.startswith('blob:') for url in existing_videos)

        if not needs_lookup:
            return

        api_data = self._fetch_post_api(post_id)
        if not api_data:
            return

        download_urls: set = set()
        stream_urls: set = set()

        def register(url):
            if not url or not isinstance(url, str):
                return
            if url.startswith('blob:'):
                return
            if '://' not in url:
                return
            lowered = url.lower()
            if 'm3u8' in lowered or lowered.endswith('.m3u8'):
                stream_urls.add(url)
            elif lowered.startswith('data:'):
                return
            else:
                download_urls.add(url)

        def collect(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        collect(value)
                    else:
                        register(value)
            elif isinstance(obj, list):
                for value in obj:
                    if isinstance(value, (dict, list)):
                        collect(value)
                    else:
                        register(value)
            else:
                register(obj)

        data_section = api_data.get('data') or {}
        if isinstance(data_section, dict):
            attrs = data_section.get('attributes') or {}
            collect(attrs.get('post_file'))
            collect(attrs.get('download_url'))
            collect(attrs.get('stream_url'))

        for item in api_data.get('included') or []:
            if not isinstance(item, dict):
                continue
            attrs = item.get('attributes') or {}
            collect(attrs.get('download_url'))
            collect(attrs.get('stream_url'))
            collect(attrs.get('url'))
            collect(attrs.get('source_url'))
            collect(attrs.get('file_url'))
            collect(attrs.get('variant_streams'))
            collect(attrs.get('variants'))

        def dedupe(sequence):
            seen = set()
            result = []
            for value in sequence:
                if value not in seen:
                    seen.add(value)
                    result.append(value)
            return result

        sanitized = [url for url in existing_videos if url and not url.startswith('blob:')]
        if download_urls:
            sanitized.extend(sorted(download_urls))
        post_detail['videos'] = dedupe(sanitized)

        if download_urls:
            post_detail['video_downloads'] = dedupe(sorted(download_urls))
        if stream_urls:
            post_detail['video_streams'] = dedupe(sorted(stream_urls))

    def _append_mux_streams(self, post_detail: Dict):
        """Detect Mux playback IDs in the page and add stream/download URLs."""

        logger.info("  🔍 [MUX] Buscando playback IDs de Mux en la página...")
        playback_map = {}

        # Find elements with data-mux-playback-id attribute
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-mux-playback-id]')
            logger.info(f"  🔍 [MUX] Encontrados {len(elements)} elementos con data-mux-playback-id")
            for elem in elements:
                playback_id = elem.get_attribute('data-mux-playback-id')
                token = elem.get_attribute('data-mux-token') or ''
                if playback_id:
                    logger.info(f"  ✓ [MUX] Playback ID desde data-attribute: {playback_id[:20]}... (token: {'SÍ' if token else 'NO'})")
                    playback_map.setdefault(playback_id, set())
                    if token:
                        playback_map[playback_id].add(token)
        except Exception as e:
            logger.warning(f"  ⚠️  [MUX] Error buscando data-mux-playback-id: {e}")

        # Find Mux thumbnail images and extract playback IDs
        try:
            thumbs = self.driver.find_elements(By.CSS_SELECTOR, 'img[src*="image.mux.com/"]')
            logger.info(f"  🔍 [MUX] Encontradas {len(thumbs)} imágenes de Mux thumbnail")
            for img in thumbs:
                src = img.get_attribute('src') or ''
                match = re.search(r'image\.mux\.com/([^/]+)/thumbnail', src)
                if match:
                    playback_id = match.group(1)
                    logger.info(f"  ✓ [MUX] Playback ID desde thumbnail: {playback_id[:20]}...")
                    token = ''
                    try:
                        qs = parse_qs(urlparse(src).query)
                        token = qs.get('token', [''])[0]
                        if token:
                            logger.info(f"  ✓ [MUX] Token extraído: {token[:30]}...")
                    except Exception:
                        pass
                    playback_map.setdefault(playback_id, set())
                    if token:
                        playback_map[playback_id].add(token)
        except Exception as e:
            logger.warning(f"  ⚠️  [MUX] Error buscando thumbnails: {e}")

        if not playback_map:
            logger.warning("  ❌ [MUX] NO se encontraron playback IDs de Mux")
            return

        logger.info(f"  ✓ [MUX] Total playback IDs encontrados: {len(playback_map)}")

        downloads = post_detail.get('video_downloads', []) or []
        streams = post_detail.get('video_streams', []) or []
        existing_videos = post_detail.get('videos', []) or []

        logger.info(f"  📋 [MUX] Estado ANTES - downloads:{len(downloads)}, streams:{len(streams)}, videos:{len(existing_videos)}")

        # Build Mux stream and download URLs
        urls_added = 0
        for playback_id, tokens in playback_map.items():
            if not playback_id:
                continue

            if tokens:
                for token in tokens:
                    stream_url = f"https://stream.mux.com/{playback_id}.m3u8?token={token[:30]}..."
                    download_url = f"https://stream.mux.com/{playback_id}/medium.mp4?token={token[:30]}..."
                    logger.info(f"  ➕ [MUX] Agregando HLS: {stream_url}")
                    logger.info(f"  ➕ [MUX] Agregando MP4: {download_url}")
                    streams.append(f"https://stream.mux.com/{playback_id}.m3u8?token={token}")
                    downloads.append(f"https://stream.mux.com/{playback_id}/medium.mp4?token={token}")
                    existing_videos.append(f"https://stream.mux.com/{playback_id}/medium.mp4?token={token}")
                    urls_added += 1
            else:
                stream_url = f"https://stream.mux.com/{playback_id}.m3u8"
                download_url = f"https://stream.mux.com/{playback_id}/medium.mp4"
                logger.info(f"  ➕ [MUX] Agregando HLS (sin token): {stream_url}")
                logger.info(f"  ➕ [MUX] Agregando MP4 (sin token): {download_url}")
                streams.append(stream_url)
                downloads.append(download_url)
                existing_videos.append(download_url)
                urls_added += 1

        logger.info(f"  ✓ [MUX] Total URLs agregadas: {urls_added}")

        # Deduplicate
        def dedupe(seq):
            seen = set()
            result = []
            for value in seq:
                if value not in seen:
                    seen.add(value)
                    result.append(value)
            return result

        post_detail['video_downloads'] = dedupe(downloads)
        post_detail['video_streams'] = dedupe(streams)
        post_detail['videos'] = dedupe(existing_videos)

        logger.info(f"  📋 [MUX] Estado DESPUÉS - downloads:{len(post_detail['video_downloads'])}, streams:{len(post_detail['video_streams'])}, videos:{len(post_detail['videos'])}")

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
