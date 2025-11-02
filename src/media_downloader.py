#!/usr/bin/env python3
"""
Media Downloader for Patreon Posts
Downloads images, videos, and audio files from scraped posts
"""

import json
import requests
import logging
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse, unquote
import time
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/media_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MediaDownloader:
    """Downloads media files from Patreon posts"""

    def __init__(self, output_dir: str = "data/media"):
        """
        Initialize downloader

        Args:
            output_dir: Base directory for media downloads
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        self.images_dir = self.output_dir / "images"
        self.videos_dir = self.output_dir / "videos"
        self.audio_dir = self.output_dir / "audio"

        self.images_dir.mkdir(exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)

        # Session for downloads
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Download statistics
        self.stats = {
            'images': {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0},
            'videos': {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0},
            'audios': {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0}
        }

    def download_file(self, url: str, output_path: Path, media_type: str = 'image') -> bool:
        """
        Download a single file

        Args:
            url: URL to download
            output_path: Path to save file
            media_type: Type of media (for stats)

        Returns:
            bool: True if downloaded successfully
        """
        try:
            # Check if already exists
            if output_path.exists():
                logger.debug(f"Skipped (exists): {output_path.name}")
                self.stats[f'{media_type}s']['skipped'] += 1
                return True

            # Download
            logger.debug(f"Downloading: {url}")
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Get total size for progress bar
            total_size = int(response.headers.get('content-length', 0))

            # Create parent directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            with open(output_path, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

            self.stats[f'{media_type}s']['downloaded'] += 1
            logger.info(f"✓ Downloaded: {output_path.name} ({self._format_size(output_path.stat().st_size)})")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to download {url}: {e}")
            self.stats[f'{media_type}s']['failed'] += 1
            return False
        except Exception as e:
            logger.error(f"✗ Error downloading {url}: {e}")
            self.stats[f'{media_type}s']['failed'] += 1
            return False

    def _get_filename_from_url(self, url: str, default_ext: str = '.jpg') -> str:
        """
        Extract filename from URL

        Args:
            url: URL to extract filename from
            default_ext: Default extension if not found

        Returns:
            str: Filename
        """
        try:
            parsed = urlparse(url)
            filename = Path(unquote(parsed.path)).name

            if not filename or '.' not in filename:
                # Generate filename from URL hash
                filename = f"{abs(hash(url))}{default_ext}"

            return filename
        except:
            return f"{abs(hash(url))}{default_ext}"

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    def download_images_from_post(self, post: Dict, creator_id: str) -> List[str]:
        """
        Download all images from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier

        Returns:
            List of downloaded file paths
        """
        downloaded = []

        # Get image URLs
        image_urls = []

        if 'images' in post and post['images']:
            image_urls.extend(post['images'])

        if 'preview_images' in post and post['preview_images']:
            image_urls.extend(post['preview_images'])

        if not image_urls:
            return downloaded

        # Create creator subdirectory
        creator_dir = self.images_dir / creator_id
        creator_dir.mkdir(exist_ok=True)

        # Download each image
        post_id = post.get('post_id', 'unknown')

        for i, url in enumerate(image_urls):
            self.stats['images']['total'] += 1

            # Generate filename
            filename = self._get_filename_from_url(url, '.jpg')

            # Add post_id prefix to avoid conflicts
            filename = f"{post_id}_{i:02d}_{filename}"

            output_path = creator_dir / filename

            if self.download_file(url, output_path, 'image'):
                downloaded.append(str(output_path))

            # Small delay between downloads
            time.sleep(0.5)

        return downloaded

    def download_videos_from_post(self, post: Dict, creator_id: str) -> List[str]:
        """
        Download all videos from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier

        Returns:
            List of downloaded file paths
        """
        downloaded = []

        video_urls = post.get('videos', [])

        if not video_urls:
            return downloaded

        # Create creator subdirectory
        creator_dir = self.videos_dir / creator_id
        creator_dir.mkdir(exist_ok=True)

        post_id = post.get('post_id', 'unknown')

        for i, url in enumerate(video_urls):
            self.stats['videos']['total'] += 1

            filename = self._get_filename_from_url(url, '.mp4')
            filename = f"{post_id}_{i:02d}_{filename}"

            output_path = creator_dir / filename

            if self.download_file(url, output_path, 'video'):
                downloaded.append(str(output_path))

            time.sleep(1)  # Longer delay for videos

        return downloaded

    def download_audios_from_post(self, post: Dict, creator_id: str) -> List[str]:
        """
        Download all audio files from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier

        Returns:
            List of downloaded file paths
        """
        downloaded = []

        audio_urls = post.get('audios', [])

        if not audio_urls:
            return downloaded

        # Create creator subdirectory
        creator_dir = self.audio_dir / creator_id
        creator_dir.mkdir(exist_ok=True)

        post_id = post.get('post_id', 'unknown')

        for i, url in enumerate(audio_urls):
            self.stats['audios']['total'] += 1

            filename = self._get_filename_from_url(url, '.mp3')
            filename = f"{post_id}_{i:02d}_{filename}"

            output_path = creator_dir / filename

            if self.download_file(url, output_path, 'audio'):
                downloaded.append(str(output_path))

            time.sleep(0.5)

        return downloaded

    def download_all_from_post(self, post: Dict, creator_id: str) -> Dict:
        """
        Download all media from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier

        Returns:
            Dictionary with downloaded file paths
        """
        logger.info(f"\n📥 Downloading media for post: {post.get('title', 'Unknown')[:50]}...")

        result = {
            'post_id': post.get('post_id'),
            'images': [],
            'videos': [],
            'audios': []
        }

        # Download images
        result['images'] = self.download_images_from_post(post, creator_id)

        # Download videos
        result['videos'] = self.download_videos_from_post(post, creator_id)

        # Download audios
        result['audios'] = self.download_audios_from_post(post, creator_id)

        total_downloaded = len(result['images']) + len(result['videos']) + len(result['audios'])
        logger.info(f"  ✓ Downloaded {total_downloaded} files")

        return result

    def download_from_json(self, json_path: str, creator_id: str) -> Dict:
        """
        Download all media from a posts JSON file

        Args:
            json_path: Path to posts JSON file
            creator_id: Creator identifier

        Returns:
            Dictionary with download results
        """
        logger.info(f"{'='*60}")
        logger.info(f"Processing: {json_path}")
        logger.info(f"Creator: {creator_id}")
        logger.info(f"{'='*60}\n")

        # Load posts
        with open(json_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        logger.info(f"Found {len(posts)} posts to process")

        results = []

        # Process each post
        for i, post in enumerate(posts, 1):
            logger.info(f"\n[{i}/{len(posts)}] {post.get('title', 'Unknown')[:60]}")

            result = self.download_all_from_post(post, creator_id)
            results.append(result)

        # Save download manifest
        manifest_path = self.output_dir / f"{creator_id}_download_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        logger.info(f"\n💾 Download manifest saved: {manifest_path}")

        return results

    def print_stats(self):
        """Print download statistics"""
        logger.info(f"\n{'='*60}")
        logger.info("DOWNLOAD STATISTICS")
        logger.info(f"{'='*60}\n")

        for media_type, stats in self.stats.items():
            logger.info(f"📊 {media_type.upper()}:")
            logger.info(f"   Total: {stats['total']}")
            logger.info(f"   Downloaded: {stats['downloaded']}")
            logger.info(f"   Skipped (existing): {stats['skipped']}")
            logger.info(f"   Failed: {stats['failed']}")
            logger.info("")

        total = sum(s['total'] for s in self.stats.values())
        downloaded = sum(s['downloaded'] for s in self.stats.values())
        skipped = sum(s['skipped'] for s in self.stats.values())
        failed = sum(s['failed'] for s in self.stats.values())

        logger.info(f"📈 TOTAL:")
        logger.info(f"   Files processed: {total}")
        logger.info(f"   New downloads: {downloaded}")
        logger.info(f"   Skipped: {skipped}")
        logger.info(f"   Failed: {failed}")

        if total > 0:
            success_rate = ((downloaded + skipped) / total) * 100
            logger.info(f"   Success rate: {success_rate:.1f}%")

        logger.info(f"\n{'='*60}\n")


def main():
    """Test media downloader"""
    import argparse

    parser = argparse.ArgumentParser(description='Download media from Patreon posts')
    parser.add_argument('--json', type=str, help='Path to posts JSON file')
    parser.add_argument('--creator', type=str, help='Creator ID')
    parser.add_argument('--all', action='store_true', help='Download from all JSONs in data/raw/')

    args = parser.parse_args()

    downloader = MediaDownloader()

    if args.all:
        # Find all JSON files in data/raw/
        raw_dir = Path("data/raw")
        json_files = list(raw_dir.glob("*_posts.json"))

        if not json_files:
            logger.error("No post JSON files found in data/raw/")
            return

        logger.info(f"Found {len(json_files)} post files to process\n")

        for json_file in json_files:
            # Extract creator ID from filename
            creator_id = json_file.stem.replace('_posts', '')

            downloader.download_from_json(str(json_file), creator_id)

    elif args.json and args.creator:
        downloader.download_from_json(args.json, args.creator)

    else:
        logger.error("Please specify --json and --creator, or use --all")
        return

    # Print statistics
    downloader.print_stats()


if __name__ == "__main__":
    main()
