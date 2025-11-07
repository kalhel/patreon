#!/usr/bin/env python3
"""
Content Parser - Extracts structured content blocks from Patreon posts
Maintains order, formatting, and structure for processing
"""

import json
import logging
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from io import BytesIO
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


def is_image_mostly_black(image_url: str, threshold: float = 0.15) -> bool:
    """
    Check if an image is mostly black/dark

    Args:
        image_url: URL of the image to check
        threshold: Brightness threshold (0-1). Below this is considered dark.

    Returns:
        True if image is mostly black, False otherwise
    """
    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code != 200:
            return True  # Consider it black if we can't load it

        img = Image.open(BytesIO(response.content))
        img = img.convert('RGB')

        # Resize to speed up processing
        img.thumbnail((100, 100))

        # Convert to numpy array and calculate average brightness
        img_array = np.array(img)
        avg_brightness = np.mean(img_array) / 255.0

        return avg_brightness < threshold

    except Exception as e:
        logger.debug(f"Error checking image brightness for {image_url}: {e}")
        return True  # Consider it black if we can't process it


def find_best_youtube_thumbnail(video_id: str) -> str:
    """
    Find the best YouTube thumbnail that isn't mostly black

    Tries in order:
    1. hqdefault.jpg (high quality default)
    2. mqdefault.jpg (medium quality)
    3. 1.jpg, 2.jpg, 3.jpg (frame captures)
    4. maxresdefault.jpg (fallback)

    Args:
        video_id: YouTube video ID

    Returns:
        URL of the best thumbnail
    """
    base_url = f'https://img.youtube.com/vi/{video_id}'

    # Try thumbnails in order of preference
    thumbnails_to_try = [
        f'{base_url}/hqdefault.jpg',
        f'{base_url}/mqdefault.jpg',
        f'{base_url}/1.jpg',
        f'{base_url}/2.jpg',
        f'{base_url}/3.jpg',
        f'{base_url}/maxresdefault.jpg',
    ]

    for thumbnail_url in thumbnails_to_try:
        try:
            # Check if thumbnail exists
            response = requests.head(thumbnail_url, timeout=3)
            if response.status_code == 200:
                # Check if it's not mostly black
                if not is_image_mostly_black(thumbnail_url):
                    logger.info(f"Found good thumbnail for {video_id}: {thumbnail_url}")
                    return thumbnail_url
                else:
                    logger.debug(f"Thumbnail too dark, trying next: {thumbnail_url}")
        except Exception as e:
            logger.debug(f"Error checking thumbnail {thumbnail_url}: {e}")
            continue

    # Fallback to hqdefault if all failed
    logger.warning(f"All thumbnails failed for {video_id}, using hqdefault as fallback")
    return f'{base_url}/hqdefault.jpg'


class ContentBlockParser:
    """Parse HTML content into structured blocks"""

    def __init__(self):
        self.blocks = []
        self.order = 0

    def parse_page(self, driver: WebDriver) -> Dict:
        """
        Parse entire page including JSON-LD schema, content, and comments

        Args:
            driver: Selenium WebDriver with loaded page

        Returns:
            Dict with 'blocks' (list of content blocks) and 'metadata' (post header info)
        """
        self.blocks = []
        self.order = 0
        self.youtube_urls = set()  # Track YouTube URLs to avoid duplicates

        try:
            # Extract post metadata (header info)
            metadata = self._extract_post_metadata(driver)

            # Extract YouTube embeds from JSON-LD schema
            self._extract_json_ld_embeds(driver)

            # Then parse main content
            content_element = self._find_content_element(driver)
            if content_element:
                html = content_element.get_attribute('innerHTML')
                soup = BeautifulSoup(html, 'html.parser')
                self._parse_children(soup)

            # Finally, extract comments
            self._extract_comments(driver)

            # Clean up extracted blocks (pass avatar URL to filter it out)
            avatar_url = metadata.get('creator_avatar', '')
            self.blocks = self._clean_blocks(self.blocks, avatar_url=avatar_url)

        except Exception as e:
            logger.error(f"Error parsing page: {e}")
            metadata = {}

        return {
            'blocks': self.blocks,
            'metadata': metadata
        }

    def _extract_post_metadata(self, driver: WebDriver) -> Dict:
        """
        Extract post header metadata (avatar, creator name, date, likes, comments)

        Returns:
            Dict with metadata fields
        """
        metadata = {
            'creator_avatar': '',
            'creator_name': '',
            'published_date': '',
            'likes_count': 0,
            'comments_count': 0
        }

        try:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Extract creator avatar
            avatar_img = soup.find('img', {'class': lambda x: x and 'cm-baquNM' in x})
            if not avatar_img:
                # Try alternative: img with alt="Creator profile picture"
                avatar_img = soup.find('img', {'alt': 'Creator profile picture'})
            if avatar_img:
                metadata['creator_avatar'] = avatar_img.get('src', '')

            # Extract creator name
            creator_heading = soup.find('h3', {'class': lambda x: x and 'cm-cyndlL' in x})
            if creator_heading:
                metadata['creator_name'] = creator_heading.get_text(strip=True)

            # Extract published date (inside span with id="track-click")
            track_span = soup.find('span', {'id': 'track-click'})
            if track_span:
                date_elem = track_span.find('p')
                if date_elem:
                    metadata['published_date'] = date_elem.get_text(strip=True)

            # Extract likes count
            like_count_elem = soup.find(attrs={'data-tag': 'like-count'})
            if like_count_elem:
                try:
                    metadata['likes_count'] = int(like_count_elem.get_text(strip=True))
                except:
                    pass

            # Extract comments count from button
            comment_button = soup.find('button', {'data-tag': 'comment-post-icon'})
            if comment_button:
                # Look for the count text inside
                count_div = comment_button.find('div', {'class': lambda x: x and 'cm-oHFIQB' in x})
                if count_div:
                    try:
                        metadata['comments_count'] = int(count_div.get_text(strip=True))
                    except:
                        pass

            logger.info(f"Extracted metadata: {metadata}")

        except Exception as e:
            logger.error(f"Error extracting post metadata: {e}")

        return metadata

    def _clean_blocks(self, blocks: List[Dict], avatar_url: str = '') -> List[Dict]:
        """
        Clean extracted blocks by removing UI elements, duplicates, and noise

        Args:
            blocks: List of extracted content blocks
            avatar_url: URL of creator avatar to filter out

        Returns:
            Cleaned list of blocks
        """
        # Phrases that indicate UI elements (not content)
        ui_phrases = [
            'patreon feed',
            'join to unlock',
            'change progress',
            'unlock the full',
            'load more',
            'related posts',
            'popular posts',
            'youtube',
            'privacy-enhanced mode'
        ]

        # UI labels that appear as standalone paragraphs
        ui_labels = ['author', 'tags', 'home', 'posts', 'share', 'like', 'comment']

        cleaned = []
        seen_content = set()
        previous_heading = None
        seen_audio_urls = set()
        seen_image_urls = set()

        # Find where comments_header starts to filter out duplicate comments before it
        comments_header_index = None
        comment_texts = set()
        for i, block in enumerate(blocks):
            if block.get('type') == 'comments_header':
                comments_header_index = i
            elif block.get('type') == 'comment':
                # Collect all real comment texts
                comment_texts.add(block.get('text', '').strip()[:100])

        for idx, block in enumerate(blocks):
            # Skip UI elements by text content
            text = block.get('text', '').lower().strip()

            # Filter out UI button text
            if any(phrase in text for phrase in ui_phrases):
                continue

            # Filter out standalone UI labels (AUTHOR, TAGS, HOME, etc.)
            if block['type'] in ['text', 'paragraph'] and text in ui_labels:
                continue

            # Filter out very short text blocks (likely timestamps or noise)
            if block['type'] in ['text', 'paragraph'] and len(text) < 5 and text not in ['']:
                continue

            # Filter out duplicate headings
            if block['type'].startswith('heading'):
                if text == previous_heading:
                    continue
                previous_heading = text
                # Filter out "X comments" headings (they're UI elements)
                if 'comment' in text and any(char.isdigit() for char in text):
                    continue

            # Filter out comments that appear as paragraphs/text before the real comments_header
            if comments_header_index is not None and idx < comments_header_index:
                if block['type'] in ['paragraph', 'text']:
                    # Check if this paragraph/text matches a real comment
                    block_text = block.get('text', '').strip()[:100]
                    if block_text in comment_texts:
                        continue  # Skip this duplicate comment

            # Filter duplicate audio blocks
            if block['type'] == 'audio':
                url = block.get('url', '')
                if url in seen_audio_urls:
                    continue
                seen_audio_urls.add(url)

            # Filter duplicate YouTube embeds and iframes
            if block['type'] == 'youtube_embed':
                url = block.get('url', '')
                # Extract video ID for deduplication
                video_id = None
                if 'youtube.com' in url or 'youtu.be' in url:
                    if 'v=' in url:
                        video_id = url.split('v=')[1].split('&')[0]
                    elif 'embed/' in url:
                        video_id = url.split('embed/')[1].split('?')[0]

                if video_id and video_id in self.youtube_urls:
                    continue  # Already seen this video
                if video_id:
                    self.youtube_urls.add(video_id)

            # Filter duplicate YouTube iframes (use video ID for deduplication)
            if block['type'] == 'iframe':
                url = block.get('url', '')
                if 'youtube' in url:
                    # Extract video ID
                    video_id = None
                    if 'v=' in url:
                        video_id = url.split('v=')[1].split('&')[0]
                    elif 'embed/' in url:
                        video_id = url.split('embed/')[1].split('?')[0]

                    if video_id:
                        if video_id in self.youtube_urls:
                            continue  # Skip duplicate YouTube iframe
                        self.youtube_urls.add(video_id)

            # Filter out small profile images (avatars) - usually < 200px
            if block['type'] == 'image':
                url = block.get('url', '')
                # Skip duplicate images
                if url in seen_image_urls:
                    continue
                # Skip the creator avatar image (exact match)
                if avatar_url and url == avatar_url:
                    continue
                # Skip avatar images (specific patterns for 100x100, 120x120, 360x360 sized images)
                # These have specific base64 patterns: eyJoIjoxMDAsInciOjEwMH0= (h:100,w:100)
                if 'eyJoIjoxMDAsInciOjEwMH0' in url or 'eyJ3IjoxMDAsImgiOjEwMH0' in url:
                    continue
                if 'eyJoIjoxMjAsInciOjEyMH0' in url or 'eyJ3IjoxMjAsImgiOjEyMH0' in url:
                    continue
                if 'eyJoIjozNjAsInciOjM2MH0' in url or 'eyJ3IjozNjAsImgiOjM2MH0' in url:
                    continue
                # Skip campaign avatar images (any size)
                if '/p/campaign/' in url:
                    continue
                seen_image_urls.add(url)

            # Create a content hash for duplicate detection
            if block['type'] in ['paragraph', 'heading_1', 'heading_2', 'heading_3']:
                content_hash = f"{block['type']}:{text[:100]}"
                if content_hash in seen_content:
                    continue
                seen_content.add(content_hash)

            # Filter out link blocks that are just navigation
            if block['type'] == 'link':
                link_text = text.lower()
                link_url = block.get('url', '')
                # Skip creator profile links
                if 'patreon.com/headonhistory' in link_url and not any(char.isdigit() for char in link_url):
                    continue
                if 'patreon.com/astrobymax' in link_url and not any(char.isdigit() for char in link_url):
                    continue
                if 'patreon.com/horoiproject' in link_url and not any(char.isdigit() for char in link_url):
                    continue
                # Skip "Related post" links
                if 'related post' in link_text:
                    continue
                # Skip tag links unless they're actually useful tags
                if 'filters%5Btag%5D=' in link_url and not text:
                    continue
                # Filter out very long link text (> 200 chars) - these are "Related posts"
                if len(text) > 200:
                    continue

            cleaned.append(block)

        # Post-processing: associate images with audio blocks and merge durations
        import re
        final_cleaned = []
        i = 0

        while i < len(cleaned):
            block = cleaned[i]

            # Check for IMAGE + DURATION + AUDIO pattern (most specific, check first)
            if block['type'] == 'image' and i + 2 < len(cleaned):
                potential_duration = cleaned[i + 1]
                potential_audio = cleaned[i + 2]

                if potential_duration['type'] == 'paragraph' and potential_audio['type'] == 'audio':
                    duration_text = potential_duration.get('text', '').strip()
                    # Match duration format: 36:40, 1:23:45, etc.
                    if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', duration_text):
                        # This is the pattern! Merge all three
                        potential_audio['thumbnail'] = block.get('url')
                        potential_audio['duration'] = duration_text
                        final_cleaned.append(potential_audio)
                        i += 3
                        continue

            # Check for IMAGE + AUDIO pattern (no duration paragraph between them)
            if block['type'] == 'image' and i + 1 < len(cleaned):
                next_block = cleaned[i + 1]
                if next_block['type'] == 'audio':
                    # Associate image as thumbnail
                    next_block['thumbnail'] = block.get('url')
                    # Skip image, add audio
                    i += 2
                    final_cleaned.append(next_block)
                    continue

            # Check for DURATION + AUDIO pattern (might have IMAGE before in final_cleaned)
            if block['type'] == 'paragraph' and i + 1 < len(cleaned):
                text = block.get('text', '').strip()
                next_block = cleaned[i + 1]
                # Match duration format: 36:40, 1:23:45, etc.
                if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', text) and next_block['type'] == 'audio':
                    # Check if the previous block in final_cleaned is an image
                    # If so, pop it and associate it with this audio
                    if final_cleaned and final_cleaned[-1]['type'] == 'image':
                        last_image = final_cleaned.pop()  # Remove the image we just added
                        next_block['thumbnail'] = last_image.get('url')
                        next_block['duration'] = text
                        final_cleaned.append(next_block)
                        i += 2
                        continue
                    else:
                        # No image before, just merge duration with audio
                        next_block['duration'] = text
                        final_cleaned.append(next_block)
                        i += 2
                        continue

            # Default: add block as-is
            final_cleaned.append(block)
            i += 1

        # Re-order blocks
        for i, block in enumerate(final_cleaned, 1):
            block['order'] = i

        return final_cleaned

    def parse_element(self, element: WebElement) -> List[Dict]:
        """
        Parse a Selenium WebElement into structured blocks
        (Kept for backward compatibility)

        Args:
            element: Selenium WebElement containing post content

        Returns:
            List of content blocks with order preserved
        """
        self.blocks = []
        self.order = 0

        try:
            # Get HTML from element
            html = element.get_attribute('innerHTML')
            soup = BeautifulSoup(html, 'html.parser')

            # Parse all children in order
            self._parse_children(soup)

        except Exception as e:
            logger.error(f"Error parsing content: {e}")

        return self.blocks

    def _find_content_element(self, driver: WebDriver) -> Optional[WebElement]:
        """Find the main content container on the page"""
        selectors = [
            '[data-tag="post-content"]',
            '.cm-bjFDAN',  # Patreon's main content container
            '.sc-4aa4e11b-0',  # Patreon's post detail container
            'div.cm-LIiDtl',  # Patreon's text content wrapper
            '[class*="post-content"]',
            'div[class*="content"]',
            'article',
            'main'
        ]

        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.text.strip():
                    logger.info(f"Found content with selector: {selector}")
                    return element
            except:
                continue

        logger.warning("Could not find content element with any selector")
        return None

    def _extract_json_ld_embeds(self, driver: WebDriver):
        """Extract YouTube embeds from JSON-LD schema in page head"""
        try:
            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Find all JSON-LD scripts
            json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})

            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)

                    # Check if it's a VideoObject with embedUrl
                    if isinstance(data, dict) and data.get('@type') == 'VideoObject':
                        embed_url = data.get('embedUrl')
                        if embed_url and 'youtube.com' in embed_url:
                            # Check if this YouTube URL was already added
                            if embed_url not in self.youtube_urls:
                                self.youtube_urls.add(embed_url)

                                # Extract video ID and find best thumbnail
                                video_id = None
                                if 'embed/' in embed_url:
                                    video_id = embed_url.split('embed/')[1].split('?')[0]
                                elif 'v=' in embed_url:
                                    video_id = embed_url.split('v=')[1].split('&')[0]

                                best_thumbnail = None
                                if video_id:
                                    best_thumbnail = find_best_youtube_thumbnail(video_id)

                                self.order += 1
                                block_data = {
                                    'type': 'youtube_embed',
                                    'order': self.order,
                                    'url': embed_url,
                                    'thumbnail': data.get('thumbnailUrl', ''),
                                    'description': data.get('description', '')
                                }
                                if best_thumbnail:
                                    block_data['best_thumbnail'] = best_thumbnail

                                self.blocks.append(block_data)
                                logger.info(f"Found YouTube embed: {embed_url} (thumbnail: {best_thumbnail})")

                except json.JSONDecodeError as e:
                    logger.debug(f"Error parsing JSON-LD: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting JSON-LD embeds: {e}")

    def _extract_comments(self, driver: WebDriver):
        """Extract comments from the page using data-tag attributes"""
        try:
            # Find all comment elements using data-tag
            comment_bodies = driver.find_elements(By.CSS_SELECTOR, '[data-tag="comment-body"]')

            if comment_bodies:
                logger.info(f"Found {len(comment_bodies)} comments")

                # First, collect valid comments (with text and nesting level)
                valid_comments = []
                for comment_elem in comment_bodies:
                    try:
                        # Get comment text
                        comment_text = comment_elem.text.strip()

                        if not comment_text:
                            continue

                        # Try to find commenter name
                        # Look for button with data-tag="commenter-name" near this comment
                        commenter_name = "Unknown"
                        nesting_level = 0

                        try:
                            # Navigate up to find the comment container and detect nesting
                            parent = comment_elem
                            for level in range(10):  # Search up to 10 levels
                                parent = parent.find_element(By.XPATH, '..')

                                # Get commenter name if found
                                if commenter_name == "Unknown":
                                    name_buttons = parent.find_elements(By.CSS_SELECTOR, 'button[data-tag="commenter-name"]')
                                    if name_buttons:
                                        commenter_name = name_buttons[0].text.strip()

                                # Check for reply container indicators
                                # Replies are in divs with classes like "sc-8b7d455-2 hWLkRA"
                                classes = parent.get_attribute('class') or ''
                                if 'hWLkRA' in classes or 'sc-8b7d455-2' in classes:
                                    nesting_level = 1
                                    break
                        except:
                            pass

                        valid_comments.append({
                            'author': commenter_name,
                            'text': comment_text,
                            'level': nesting_level
                        })

                    except Exception as e:
                        logger.debug(f"Error extracting individual comment: {e}")
                        continue

                # Now add the comments header with the correct count
                if valid_comments:
                    self.order += 1
                    self.blocks.append({
                        'type': 'comments_header',
                        'order': self.order,
                        'text': f'Comments ({len(valid_comments)})',
                        'count': len(valid_comments)
                    })

                    # Add all valid comments with nesting level
                    for comment in valid_comments:
                        self.order += 1
                        self.blocks.append({
                            'type': 'comment',
                            'order': self.order,
                            'author': comment['author'],
                            'text': comment['text'],
                            'level': comment.get('level', 0)
                        })

        except Exception as e:
            logger.error(f"Error extracting comments: {e}")

    def _parse_children(self, parent):
        """Recursively parse children elements"""
        for child in parent.children:
            if isinstance(child, str):
                # Skip pure whitespace
                if child.strip():
                    self._add_text_block(child.strip())
                continue

            tag = child.name.lower() if child.name else None

            if tag == 'h1':
                self._add_heading_block(1, child)
            elif tag == 'h2':
                self._add_heading_block(2, child)
            elif tag == 'h3':
                self._add_heading_block(3, child)
            elif tag == 'p':
                self._add_paragraph_block(child)
            elif tag == 'img':
                # Skip comment-send avatar (user's avatar for writing comments)
                if child.get('data-tag') == 'comment-send-avatar':
                    continue

                # Skip images that are inside a data-image-container or comment-send-avatar-root
                # (they're already processed by the container handler)
                # Check all ancestors, not just immediate parent
                ancestor = child.parent
                skip = False
                for _ in range(5):  # Check up to 5 levels up
                    if ancestor:
                        if ancestor.get('data-image-container') == 'true':
                            skip = True
                            break
                        if ancestor.get('data-tag') == 'comment-send-avatar-root':
                            skip = True
                            break
                    ancestor = ancestor.parent if ancestor else None
                if skip:
                    continue
                self._add_image_block(child)
            elif tag == 'video':
                self._add_video_block(child)
            elif tag == 'audio':
                self._add_audio_block(child)
            elif tag == 'iframe':
                self._add_iframe_block(child)
            elif tag == 'ul':
                self._add_list_block(child, ordered=False)
            elif tag == 'ol':
                self._add_list_block(child, ordered=True)
            elif tag == 'blockquote':
                self._add_quote_block(child)
            elif tag == 'a':
                self._add_link_block(child)
            elif tag == 'div':
                # Check if this is an image container
                if child.get('data-image-container') == 'true':
                    # Find the img inside this container
                    img = child.find('img')
                    if img:
                        self._add_image_block(img)
                    # Don't recurse into this div - we already processed it
                else:
                    # Regular div - dive into it
                    self._parse_children(child)
            elif tag == 'span':
                # Dive into spans
                self._parse_children(child)
            elif tag == 'figure':
                # Figures wrap images - recurse into them
                self._parse_children(child)
            elif tag == 'section':
                # Sections contain content - recurse into them
                self._parse_children(child)
            elif tag in ['strong', 'b', 'em', 'i', 'u', 'mark']:
                # Inline formatting tags - recurse into them
                self._parse_children(child)
            # Add more tag handlers as needed
            else:
                # Unknown tag - try to recurse if it might contain content
                if child.children:
                    self._parse_children(child)

    def _add_heading_block(self, level: int, element):
        """Add heading block (h1, h2, h3)"""
        text = self._extract_formatted_text(element)
        if text:
            self.order += 1
            self.blocks.append({
                'type': f'heading_{level}',
                'order': self.order,
                'text': text
            })

    def _add_paragraph_block(self, element):
        """Add paragraph block with inline formatting"""
        text = self._extract_formatted_text(element)
        if text:
            self.order += 1
            self.blocks.append({
                'type': 'paragraph',
                'order': self.order,
                'text': text,
                'html': str(element)  # Keep HTML for styling
            })

    def _add_text_block(self, text: str):
        """Add plain text block"""
        if text:
            self.order += 1
            self.blocks.append({
                'type': 'text',
                'order': self.order,
                'text': text
            })

    def _add_image_block(self, element):
        """Add image block - content images from patreonusercontent.com"""
        src = element.get('src', '')
        alt = element.get('alt', '')
        media_id = element.get('data-media-id', '')

        # Only add if it's a Patreon content image
        if not src or 'patreonusercontent.com' not in src:
            return

        # Extract media_id from URL if not in attribute
        # URL format: https://c10.patreonusercontent.com/4/patreon-media/p/post/123456789/...
        if not media_id and '/p/post/' in src:
            try:
                # Extract post_id from URL as media identifier
                url_parts = src.split('/p/post/')
                if len(url_parts) > 1:
                    post_part = url_parts[1].split('/')[0]
                    media_id = f"post_{post_part}_{src.split('/')[-1].split('?')[0]}"
            except:
                pass

        # If still no media_id, generate one from URL
        if not media_id:
            # Use last part of URL (filename) as identifier
            try:
                media_id = src.split('/')[-1].split('?')[0]
            except:
                media_id = ''

        self.order += 1
        self.blocks.append({
            'type': 'image',
            'order': self.order,
            'url': src,
            'caption': alt,
            'media_id': media_id or 'unknown'
        })
        logger.info(f"  ✓ Content image (media_id={media_id or 'extracted'}): {src[:80]}...")

    def _add_video_block(self, element):
        """Add video block"""
        src = element.get('src', '')

        # Check for source tags
        if not src:
            source = element.find('source')
            if source:
                src = source.get('src', '')

        if src:
            self.order += 1
            self.blocks.append({
                'type': 'video',
                'order': self.order,
                'url': src,
                'poster': element.get('poster', '')
            })

    def _add_audio_block(self, element):
        """Add audio block with thumbnail if available"""
        src = element.get('src', '')

        # Check for source tags
        if not src:
            source = element.find('source')
            if source:
                src = source.get('src', '')

        if src:
            # Look for associated thumbnail image
            thumbnail = None

            # Try to find thumbnail in parent container
            parent = element.parent
            if parent:
                # Look for img with data-tag="thumbnail" or nearby img
                thumbnail_container = parent.find(attrs={'data-tag': 'thumbnail'})
                if thumbnail_container:
                    img = thumbnail_container.find('img')
                    if img:
                        thumbnail = img.get('src', '')

                # If not found, look for any img in parent before the audio
                if not thumbnail:
                    img = parent.find('img')
                    if img:
                        img_src = img.get('src', '')
                        # Only use if it's a content image, not an avatar
                        if 'patreonusercontent.com' in img_src:
                            thumbnail = img_src

            self.order += 1
            block_data = {
                'type': 'audio',
                'order': self.order,
                'url': src
            }

            if thumbnail:
                block_data['thumbnail'] = thumbnail

            self.blocks.append(block_data)

    def _add_iframe_block(self, element):
        """Add iframe/embed block (YouTube, Vimeo, etc.)"""
        src = element.get('src', '')

        if src:
            # Determine embed type
            embed_type = 'iframe'
            if 'youtube.com' in src or 'youtu.be' in src:
                embed_type = 'youtube_embed'
            elif 'vimeo.com' in src:
                embed_type = 'vimeo_embed'
            elif 'soundcloud.com' in src:
                embed_type = 'soundcloud_embed'

            self.order += 1
            block_data = {
                'type': embed_type,
                'order': self.order,
                'url': src,
                'title': element.get('title', '')
            }

            # For YouTube embeds, find the best thumbnail
            if embed_type == 'youtube_embed':
                video_id = None
                if 'embed/' in src:
                    video_id = src.split('embed/')[1].split('?')[0]
                elif 'v=' in src:
                    video_id = src.split('v=')[1].split('&')[0]
                elif 'youtu.be/' in src:
                    video_id = src.split('youtu.be/')[1].split('?')[0]

                if video_id:
                    best_thumbnail = find_best_youtube_thumbnail(video_id)
                    if best_thumbnail:
                        block_data['best_thumbnail'] = best_thumbnail
                        logger.info(f"Found best thumbnail for YouTube {video_id}: {best_thumbnail}")

            self.blocks.append(block_data)

    def _add_list_block(self, element, ordered: bool):
        """Add bulleted or numbered list"""
        items = []
        for li in element.find_all('li', recursive=False):
            text = self._extract_formatted_text(li)
            if text:
                items.append(text)

        if items:
            self.order += 1
            self.blocks.append({
                'type': 'numbered_list' if ordered else 'bulleted_list',
                'order': self.order,
                'items': items
            })

    def _add_quote_block(self, element):
        """Add quote block - preserve paragraph breaks"""
        # Get all paragraphs in blockquote
        paragraphs = element.find_all('p', recursive=False)

        if paragraphs:
            # Join paragraphs with double line breaks
            texts = []
            for p in paragraphs:
                p_text = self._extract_formatted_text(p)
                if p_text:
                    texts.append(p_text)
            text = '\n\n'.join(texts)
        else:
            # No <p> tags, extract as-is
            text = self._extract_formatted_text(element)

        if text:
            self.order += 1
            self.blocks.append({
                'type': 'quote',
                'order': self.order,
                'text': text
            })

    def _add_link_block(self, element):
        """Add link (embedded in text usually)"""
        text = element.get_text(strip=True)
        href = element.get('href', '')

        if text and href:
            self.order += 1
            self.blocks.append({
                'type': 'link',
                'order': self.order,
                'text': text,
                'url': href
            })

    def _extract_formatted_text(self, element) -> str:
        """
        Extract text with inline formatting preserved as markdown

        Converts:
        - <strong>, <b> -> **text**
        - <em>, <i> -> *text*
        - <u> -> <u>text</u> (HTML, no hay underline en markdown)
        - <a> -> [text](url)

        Returns formatted text with markdown/HTML mix
        """
        if not element:
            return ""

        def process_node(node):
            """Recursively process nodes preserving structure"""
            if isinstance(node, str):
                # Text node - preserve as is (don't strip)
                return node

            if not hasattr(node, 'name'):
                return ''

            tag = node.name.lower() if node.name else None

            # Process children recursively
            children_text = ''.join(process_node(child) for child in node.children)

            # Apply formatting based on tag
            if tag in ['strong', 'b']:
                return f"**{children_text}**"
            elif tag in ['em', 'i']:
                return f"*{children_text}*"
            elif tag == 'u':
                return f"<u>{children_text}</u>"  # HTML underline
            elif tag == 'a':
                href = node.get('href', '')
                if href:
                    return f"[{children_text}]({href})"
                return children_text
            elif tag == 'br':
                return '\n'
            elif tag in ['span', 'div', 'p']:
                # Preserve structure tags
                return children_text
            else:
                return children_text

        result = process_node(element)

        # Clean up excessive whitespace but preserve intentional spacing
        import re
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)  # Max 2 newlines
        result = re.sub(r' +', ' ', result)  # Single spaces only

        return result.strip()


def parse_post_content(content_element: WebElement) -> List[Dict]:
    """
    Convenience function to parse post content
    (Kept for backward compatibility - use parse_post_page for better results)

    Args:
        content_element: Selenium WebElement containing post content

    Returns:
        List of structured content blocks
    """
    parser = ContentBlockParser()
    return parser.parse_element(content_element)


def parse_post_page(driver: WebDriver) -> Dict:
    """
    Convenience function to parse entire post page including embeds and comments

    Args:
        driver: Selenium WebDriver with loaded post page

    Returns:
        Dict with 'blocks' (list of content blocks) and 'metadata' (post header info)
    """
    parser = ContentBlockParser()
    return parser.parse_page(driver)
