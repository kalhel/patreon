#!/usr/bin/env python3
"""
Notion Integrator for Patreon Content
Uploads posts, media, tags, and creators to Notion databases
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from notion_client import Client
from notion_client.errors import APIResponseError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/notion_integrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NotionIntegrator:
    """Integrates Patreon content with Notion databases"""

    def __init__(self, api_key: str, database_ids: Dict[str, str]):
        """
        Initialize Notion integrator

        Args:
            api_key: Notion API key
            database_ids: Dictionary mapping database names to IDs
        """
        self.client = Client(auth=api_key)
        self.database_ids = database_ids

        # Validate database IDs
        required_dbs = ['posts', 'creators', 'tags', 'images', 'videos', 'audio']
        for db_name in required_dbs:
            if db_name not in database_ids or not database_ids[db_name]:
                logger.warning(f"⚠️  Database ID for '{db_name}' not configured")

        # Caches for existing items (to avoid duplicates)
        self.existing_creators = {}
        self.existing_tags = {}
        self.existing_posts = {}

        logger.info("✅ Notion client initialized")

    # ========================================
    # CREATORS
    # ========================================

    def create_or_get_creator(self, creator_data: Dict) -> Optional[str]:
        """
        Create or get existing creator in Notion

        Args:
            creator_data: Creator information

        Returns:
            Page ID of creator or None
        """
        creator_id = creator_data.get('creator_id')

        # Check cache
        if creator_id in self.existing_creators:
            return self.existing_creators[creator_id]

        try:
            # Search for existing creator
            results = self.client.databases.query(
                database_id=self.database_ids['creators'],
                filter={
                    "property": "Creator ID",
                    "rich_text": {
                        "equals": creator_id
                    }
                }
            )

            if results['results']:
                # Creator exists
                page_id = results['results'][0]['id']
                self.existing_creators[creator_id] = page_id
                logger.info(f"  ✓ Found existing creator: {creator_data.get('name')}")
                return page_id

            # Create new creator
            properties = {
                "Nombre": {
                    "title": [{"text": {"content": creator_data.get('name', 'Unknown')}}]
                },
                "Creator ID": {
                    "rich_text": [{"text": {"content": creator_id}}]
                },
                "URL Patreon": {
                    "url": creator_data.get('url', '')
                }
            }

            # Add optional fields
            if creator_data.get('category'):
                properties["Categoría"] = {
                    "select": {"name": creator_data['category']}
                }

            response = self.client.pages.create(
                parent={"database_id": self.database_ids['creators']},
                properties=properties
            )

            page_id = response['id']
            self.existing_creators[creator_id] = page_id
            logger.info(f"  ✓ Created creator: {creator_data.get('name')}")

            return page_id

        except APIResponseError as e:
            logger.error(f"  ✗ Error creating creator: {e}")
            return None

    # ========================================
    # TAGS
    # ========================================

    def create_or_get_tag(self, tag_name: str, tag_type: str = "AI") -> Optional[str]:
        """
        Create or get existing tag in Notion

        Args:
            tag_name: Name of the tag
            tag_type: Type (Patreon, AI, Manual)

        Returns:
            Page ID of tag or None
        """
        # Check cache
        if tag_name in self.existing_tags:
            return self.existing_tags[tag_name]

        try:
            # Search for existing tag
            results = self.client.databases.query(
                database_id=self.database_ids['tags'],
                filter={
                    "property": "Tag",
                    "title": {
                        "equals": tag_name
                    }
                }
            )

            if results['results']:
                # Tag exists
                page_id = results['results'][0]['id']
                self.existing_tags[tag_name] = page_id
                return page_id

            # Create new tag
            properties = {
                "Tag": {
                    "title": [{"text": {"content": tag_name}}]
                },
                "Tipo": {
                    "select": {"name": tag_type}
                }
            }

            response = self.client.pages.create(
                parent={"database_id": self.database_ids['tags']},
                properties=properties
            )

            page_id = response['id']
            self.existing_tags[tag_name] = page_id
            logger.debug(f"  ✓ Created tag: {tag_name}")

            return page_id

        except APIResponseError as e:
            logger.error(f"  ✗ Error creating tag: {e}")
            return None

    def create_all_tags(self, tags: List[str], tag_type: str = "AI") -> List[str]:
        """
        Create or get multiple tags

        Args:
            tags: List of tag names
            tag_type: Type of tags

        Returns:
            List of page IDs
        """
        tag_ids = []
        for tag in tags:
            tag_id = self.create_or_get_tag(tag, tag_type)
            if tag_id:
                tag_ids.append(tag_id)
        return tag_ids

    # ========================================
    # POSTS
    # ========================================

    def upload_post(self, post_data: Dict, creator_page_id: str) -> Optional[str]:
        """
        Upload a single post to Notion

        Args:
            post_data: Post information
            creator_page_id: Notion page ID of creator

        Returns:
            Page ID of created post or None
        """
        post_id = post_data.get('post_id')

        # Check if post already exists
        if post_id in self.existing_posts:
            logger.info(f"  ⊙ Post already exists: {post_data.get('title', 'Unknown')[:50]}")
            return self.existing_posts[post_id]

        try:
            # Prepare properties
            properties = {
                "Título": {
                    "title": [{"text": {"content": post_data.get('title', 'Untitled')[:2000]}}]
                },
                "Post ID": {
                    "rich_text": [{"text": {"content": str(post_id)}}]
                },
                "URL Original": {
                    "url": post_data.get('post_url', '')
                }
            }

            # Add creator relation
            if creator_page_id:
                properties["Creator"] = {
                    "relation": [{"id": creator_page_id}]
                }

            # Add date
            if post_data.get('published_at'):
                try:
                    # Extract just the date part
                    date_str = post_data['published_at'].split('T')[0]
                    properties["Fecha Publicación"] = {
                        "date": {"start": date_str}
                    }
                except:
                    pass

            # Add preview text
            if post_data.get('preview_text'):
                preview = post_data['preview_text'][:2000]  # Notion limit
                properties["Preview Text"] = {
                    "rich_text": [{"text": {"content": preview}}]
                }

            # Add access tier
            if post_data.get('access_tier'):
                properties["Access Tier"] = {
                    "select": {"name": post_data['access_tier'][:100]}
                }

            # Add likes and comments
            if post_data.get('likes'):
                try:
                    likes = int(''.join(filter(str.isdigit, str(post_data['likes']))))
                    properties["Likes"] = {"number": likes}
                except:
                    pass

            if post_data.get('comments'):
                try:
                    comments = int(''.join(filter(str.isdigit, str(post_data['comments']))))
                    properties["Comments"] = {"number": comments}
                except:
                    pass

            # Create tags
            all_tag_ids = []

            # Patreon tags
            if post_data.get('patreon_tags'):
                patreon_tag_ids = self.create_all_tags(post_data['patreon_tags'], "Patreon")
                all_tag_ids.extend(patreon_tag_ids)

            # AI tags
            if post_data.get('ai_tags'):
                ai_tag_ids = self.create_all_tags(post_data['ai_tags'], "AI")
                all_tag_ids.extend(ai_tag_ids)

            # Add tag relations
            if all_tag_ids:
                properties["Tags"] = {
                    "relation": [{"id": tag_id} for tag_id in all_tag_ids]
                }

            # Create the page
            response = self.client.pages.create(
                parent={"database_id": self.database_ids['posts']},
                properties=properties
            )

            page_id = response['id']
            self.existing_posts[post_id] = page_id

            # Now add the content to the page
            if post_data.get('full_content'):
                self._add_content_to_page(page_id, post_data)

            logger.info(f"  ✓ Created post: {post_data.get('title', 'Unknown')[:50]}")

            return page_id

        except APIResponseError as e:
            logger.error(f"  ✗ Error creating post: {e}")
            return None

    def _add_content_to_page(self, page_id: str, post_data: Dict):
        """
        Add content blocks to a Notion page

        Args:
            page_id: Notion page ID
            post_data: Post data with content
        """
        try:
            content = post_data.get('full_content', '')

            if not content:
                return

            # Split content into paragraphs
            paragraphs = content.split('\n\n')

            blocks = []

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # Limit paragraph length (Notion has limits)
                if len(para) > 2000:
                    para = para[:1997] + "..."

                # Create paragraph block
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": para}}]
                    }
                })

                # Notion API limit: 100 blocks per request
                if len(blocks) >= 90:
                    break

            # Add blocks to page
            if blocks:
                self.client.blocks.children.append(
                    block_id=page_id,
                    children=blocks
                )
                logger.debug(f"    ✓ Added {len(blocks)} content blocks")

        except APIResponseError as e:
            logger.warning(f"    ⚠️  Could not add content blocks: {e}")

    # ========================================
    # IMAGES
    # ========================================

    def upload_image(self, image_data: Dict, post_page_id: str, creator_page_id: str, tag_ids: List[str]) -> Optional[str]:
        """
        Upload image metadata to Notion

        Args:
            image_data: Image information
            post_page_id: Related post page ID
            creator_page_id: Related creator page ID
            tag_ids: Related tag page IDs

        Returns:
            Page ID of created image or None
        """
        try:
            file_name = image_data.get('file_name', 'Unknown')

            properties = {
                "Título": {
                    "title": [{"text": {"content": file_name[:2000]}}]
                },
                "File Name": {
                    "rich_text": [{"text": {"content": file_name}}]
                },
                "File Path": {
                    "rich_text": [{"text": {"content": image_data.get('file_path', '')[:2000]}}]
                }
            }

            # Add URL
            if image_data.get('url'):
                properties["URL Original"] = {"url": image_data['url']}

            # Add file size
            if image_data.get('file_size'):
                properties["File Size"] = {
                    "rich_text": [{"text": {"content": image_data['file_size']}}]
                }

            # Add relations
            if post_page_id:
                properties["Post"] = {"relation": [{"id": post_page_id}]}

            if creator_page_id:
                properties["Creator"] = {"relation": [{"id": creator_page_id}]}

            if tag_ids:
                properties["Tags"] = {"relation": [{"id": tag_id} for tag_id in tag_ids]}

            # Create page
            response = self.client.pages.create(
                parent={"database_id": self.database_ids['images']},
                properties=properties
            )

            logger.debug(f"    ✓ Created image entry: {file_name[:30]}")
            return response['id']

        except APIResponseError as e:
            logger.error(f"    ✗ Error creating image: {e}")
            return None

    # ========================================
    # VIDEOS
    # ========================================

    def upload_video(self, video_data: Dict, post_page_id: str, creator_page_id: str, tag_ids: List[str]) -> Optional[str]:
        """
        Upload video metadata to Notion

        Args:
            video_data: Video information
            post_page_id: Related post page ID
            creator_page_id: Related creator page ID
            tag_ids: Related tag page IDs

        Returns:
            Page ID of created video or None
        """
        try:
            file_name = video_data.get('file_name', 'Unknown')

            properties = {
                "Título": {
                    "title": [{"text": {"content": file_name[:2000]}}]
                },
                "File Name": {
                    "rich_text": [{"text": {"content": file_name}}]
                },
                "File Path": {
                    "rich_text": [{"text": {"content": video_data.get('file_path', '')[:2000]}}]
                }
            }

            # Add URL
            if video_data.get('url'):
                properties["URL Original"] = {"url": video_data['url']}

            # Add file size
            if video_data.get('file_size'):
                properties["File Size"] = {
                    "rich_text": [{"text": {"content": video_data['file_size']}}]
                }

            # Add relations
            if post_page_id:
                properties["Post"] = {"relation": [{"id": post_page_id}]}

            if creator_page_id:
                properties["Creator"] = {"relation": [{"id": creator_page_id}]}

            if tag_ids:
                properties["Tags"] = {"relation": [{"id": tag_id} for tag_id in tag_ids]}

            # Create page
            response = self.client.pages.create(
                parent={"database_id": self.database_ids['videos']},
                properties=properties
            )

            logger.debug(f"    ✓ Created video entry: {file_name[:30]}")
            return response['id']

        except APIResponseError as e:
            logger.error(f"    ✗ Error creating video: {e}")
            return None

    # ========================================
    # AUDIO
    # ========================================

    def upload_audio(self, audio_data: Dict, post_page_id: str, creator_page_id: str, tag_ids: List[str]) -> Optional[str]:
        """
        Upload audio metadata to Notion

        Args:
            audio_data: Audio information
            post_page_id: Related post page ID
            creator_page_id: Related creator page ID
            tag_ids: Related tag page IDs

        Returns:
            Page ID of created audio or None
        """
        try:
            file_name = audio_data.get('file_name', 'Unknown')

            properties = {
                "Título": {
                    "title": [{"text": {"content": file_name[:2000]}}]
                },
                "File Name": {
                    "rich_text": [{"text": {"content": file_name}}]
                },
                "File Path": {
                    "rich_text": [{"text": {"content": audio_data.get('file_path', '')[:2000]}}]
                }
            }

            # Add URL
            if audio_data.get('url'):
                properties["URL Original"] = {"url": audio_data['url']}

            # Add file size
            if audio_data.get('file_size'):
                properties["File Size"] = {
                    "rich_text": [{"text": {"content": audio_data['file_size']}}]
                }

            # Add relations
            if post_page_id:
                properties["Post"] = {"relation": [{"id": post_page_id}]}

            if creator_page_id:
                properties["Creator"] = {"relation": [{"id": creator_page_id}]}

            if tag_ids:
                properties["Tags"] = {"relation": [{"id": tag_id} for tag_id in tag_ids]}

            # Create page
            response = self.client.pages.create(
                parent={"database_id": self.database_ids['audio']},
                properties=properties
            )

            logger.debug(f"    ✓ Created audio entry: {file_name[:30]}")
            return response['id']

        except APIResponseError as e:
            logger.error(f"    ✗ Error creating audio: {e}")
            return None

    # ========================================
    # UPLOAD COMPLETE POST WITH MEDIA
    # ========================================

    def upload_complete_post(self, post_data: Dict, creator_info: Dict, media_dir: Path) -> Dict:
        """
        Upload a complete post with all media

        Args:
            post_data: Post information
            creator_info: Creator information
            media_dir: Path to media directory

        Returns:
            Dictionary with upload results
        """
        result = {
            'post_id': post_data.get('post_id'),
            'success': False,
            'notion_post_id': None,
            'images_uploaded': 0,
            'videos_uploaded': 0,
            'audio_uploaded': 0
        }

        try:
            # 1. Create or get creator
            creator_page_id = self.create_or_get_creator(creator_info)
            if not creator_page_id:
                logger.error("  ✗ Failed to create creator")
                return result

            # 2. Upload post
            post_page_id = self.upload_post(post_data, creator_page_id)
            if not post_page_id:
                logger.error("  ✗ Failed to create post")
                return result

            result['notion_post_id'] = post_page_id

            # 3. Get tag IDs for media
            tag_ids = []
            for tag in post_data.get('all_tags', []):
                tag_id = self.create_or_get_tag(tag, "AI")
                if tag_id:
                    tag_ids.append(tag_id)

            # 4. Upload images
            images = post_data.get('images', [])
            if images:
                logger.info(f"    📸 Uploading {len(images)} images...")
                for i, image_url in enumerate(images):
                    image_data = {
                        'file_name': f"{post_data['post_id']}_{i:02d}_image.jpg",
                        'file_path': str(media_dir / 'images' / creator_info['creator_id'] / f"{post_data['post_id']}_{i:02d}_image.jpg"),
                        'url': image_url
                    }
                    if self.upload_image(image_data, post_page_id, creator_page_id, tag_ids):
                        result['images_uploaded'] += 1

            # 5. Upload videos
            videos = post_data.get('videos', [])
            if videos:
                logger.info(f"    🎬 Uploading {len(videos)} videos...")
                for i, video_url in enumerate(videos):
                    video_data = {
                        'file_name': f"{post_data['post_id']}_{i:02d}_video.mp4",
                        'file_path': str(media_dir / 'videos' / creator_info['creator_id'] / f"{post_data['post_id']}_{i:02d}_video.mp4"),
                        'url': video_url
                    }
                    if self.upload_video(video_data, post_page_id, creator_page_id, tag_ids):
                        result['videos_uploaded'] += 1

            # 6. Upload audio
            audios = post_data.get('audios', [])
            if audios:
                logger.info(f"    🎵 Uploading {len(audios)} audio files...")
                for i, audio_url in enumerate(audios):
                    audio_data = {
                        'file_name': f"{post_data['post_id']}_{i:02d}_audio.mp3",
                        'file_path': str(media_dir / 'audio' / creator_info['creator_id'] / f"{post_data['post_id']}_{i:02d}_audio.mp3"),
                        'url': audio_url
                    }
                    if self.upload_audio(audio_data, post_page_id, creator_page_id, tag_ids):
                        result['audio_uploaded'] += 1

            result['success'] = True
            logger.info(f"  ✅ Post upload complete: {result['images_uploaded']} images, {result['videos_uploaded']} videos, {result['audio_uploaded']} audio")

        except Exception as e:
            logger.error(f"  ✗ Error uploading complete post: {e}")

        return result

    # ========================================
    # BATCH UPLOAD
    # ========================================

    def upload_from_json(self, json_path: str, creator_info: Dict) -> Dict:
        """
        Upload all posts from a JSON file

        Args:
            json_path: Path to posts JSON file
            creator_info: Creator information

        Returns:
            Upload statistics
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Uploading to Notion: {json_path}")
        logger.info(f"Creator: {creator_info['name']}")
        logger.info(f"{'='*60}\n")

        # Load posts
        with open(json_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        logger.info(f"Found {len(posts)} posts to upload")

        stats = {
            'total_posts': len(posts),
            'posts_uploaded': 0,
            'posts_failed': 0,
            'total_images': 0,
            'total_videos': 0,
            'total_audio': 0
        }

        media_dir = Path("data/media")

        for i, post in enumerate(posts, 1):
            logger.info(f"\n[{i}/{len(posts)}] {post.get('title', 'Unknown')[:60]}")

            result = self.upload_complete_post(post, creator_info, media_dir)

            if result['success']:
                stats['posts_uploaded'] += 1
                stats['total_images'] += result['images_uploaded']
                stats['total_videos'] += result['videos_uploaded']
                stats['total_audio'] += result['audio_uploaded']
            else:
                stats['posts_failed'] += 1

            # Rate limiting
            time.sleep(0.5)

        return stats

    def print_stats(self, stats: Dict):
        """Print upload statistics"""
        logger.info(f"\n{'='*60}")
        logger.info("UPLOAD STATISTICS")
        logger.info(f"{'='*60}\n")

        logger.info(f"📊 Total posts: {stats['total_posts']}")
        logger.info(f"✅ Uploaded: {stats['posts_uploaded']}")
        logger.info(f"❌ Failed: {stats['posts_failed']}")
        logger.info(f"📸 Images: {stats['total_images']}")
        logger.info(f"🎬 Videos: {stats['total_videos']}")
        logger.info(f"🎵 Audio: {stats['total_audio']}")

        logger.info(f"\n{'='*60}\n")


def main():
    """Test Notion integrator"""
    import argparse

    parser = argparse.ArgumentParser(description='Upload Patreon content to Notion')
    parser.add_argument('--json', type=str, help='Path to posts JSON file')
    parser.add_argument('--all', action='store_true', help='Upload all JSONs in data/processed/')
    parser.add_argument('--api-key', type=str, help='Notion API key')

    args = parser.parse_args()

    # Load config
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"
    with open(config_path) as f:
        config = json.load(f)

    # Get API key
    api_key = args.api_key or config['notion'].get('api_key') or os.environ.get('NOTION_API_KEY')

    if not api_key:
        logger.error("❌ No Notion API key provided!")
        logger.info("Set NOTION_API_KEY environment variable, use --api-key, or add to config/credentials.json")
        logger.info("\nGet API key from: https://www.notion.so/my-integrations")
        return

    # Get database IDs
    database_ids = config['notion'].get('database_ids', {})

    if not all(database_ids.get(db) for db in ['posts', 'creators', 'tags']):
        logger.error("❌ Database IDs not configured!")
        logger.info("Add database IDs to config/credentials.json")
        return

    integrator = NotionIntegrator(api_key, database_ids)

    if args.all:
        # Upload all processed JSONs
        processed_dir = Path("data/processed")
        json_files = list(processed_dir.glob("*_posts.json"))

        if not json_files:
            logger.error("No processed JSON files found in data/processed/")
            return

        logger.info(f"Found {len(json_files)} files to upload\n")

        for json_file in json_files:
            # Extract creator ID
            creator_id = json_file.stem.replace('_posts', '')

            # Find creator info
            creator_info = None
            for creator in config['patreon']['creators']:
                if creator['creator_id'] == creator_id:
                    creator_info = creator
                    break

            if not creator_info:
                logger.warning(f"Creator info not found for: {creator_id}")
                continue

            stats = integrator.upload_from_json(str(json_file), creator_info)
            integrator.print_stats(stats)

    elif args.json:
        # Upload single file
        creator_id = Path(args.json).stem.replace('_posts', '')

        creator_info = None
        for creator in config['patreon']['creators']:
            if creator['creator_id'] == creator_id:
                creator_info = creator
                break

        if not creator_info:
            logger.error(f"Creator info not found for: {creator_id}")
            return

        stats = integrator.upload_from_json(args.json, creator_info)
        integrator.print_stats(stats)

    else:
        logger.error("Please specify --json FILE or use --all")

    logger.info("✅ Upload complete!")


if __name__ == "__main__":
    main()
