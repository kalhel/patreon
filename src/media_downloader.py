#!/usr/bin/env python3
"""
Media Downloader for Patreon Posts
Downloads images, videos, and audio files from scraped posts
"""

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, unquote
import tempfile

import requests
from requests.cookies import RequestsCookieJar

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

    def __init__(self, output_dir: str = "data/media", cookies_path: Optional[str] = "config/patreon_cookies.json"):
        """
        Initialize downloader

        Args:
            output_dir: Base directory for media downloads
            cookies_path: Optional path to Patreon cookies captured by Selenium
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.patreon.com'
        })

        self.cookies_path = Path(cookies_path) if cookies_path else None
        if self.cookies_path:
            self._load_cookies_from_file(self.cookies_path)

        # Download statistics
        self.stats = {
            'images': {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0},
            'videos': {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0},
            'audios': {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0}
        }
        self.min_video_size_bytes = 15 * 1024 * 1024  # 15 MB threshold to detect previews

    def _load_cookies_from_file(self, path: Path):
        """Load Patreon cookies exported by Selenium"""
        if not path.exists():
            logger.debug(f"No cookie file found at {path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as fh:
                cookies = json.load(fh)
        except Exception as exc:
            logger.warning(f"⚠️  Could not read cookies from {path}: {exc}")
            return

        loaded = 0
        for cookie in cookies or []:
            name = cookie.get('name')
            value = cookie.get('value')
            if not name or value is None:
                continue
            params = {
                'domain': cookie.get('domain'),
                'path': cookie.get('path', '/')
            }
            self.session.cookies.set(name, value, **{k: v for k, v in params.items() if v})
            loaded += 1

        logger.info(f"🍪 Loaded {loaded} cookies from {path}")

    def sync_cookies_from_driver(self, driver, clear_existing: bool = False):
        """
        Copy cookies from an authenticated Selenium WebDriver into the requests session.

        Args:
            driver: Selenium WebDriver instance
            clear_existing: Whether to clear existing cookies before syncing
        """
        if driver is None:
            return

        try:
            selenium_cookies = driver.get_cookies()
        except Exception as exc:
            logger.debug(f"⚠️  Unable to read cookies from driver: {exc}")
            return

        if clear_existing:
            self.session.cookies.clear()

        jar = RequestsCookieJar()
        synced = 0
        for cookie in selenium_cookies:
            name = cookie.get('name')
            value = cookie.get('value')
            if not name or value is None:
                continue
            jar.set(
                name,
                value,
                domain=cookie.get('domain'),
                path=cookie.get('path', '/')
            )
            synced += 1

        self.session.cookies.update(jar)
        logger.debug(f"🍪 Synced {synced} cookies from Selenium session")

    def _flatten_urls(self, sources) -> List[str]:
        """Flatten nested collections of URLs into a unique ordered list"""

        urls: List[str] = []

        def collect(value):
            if not value:
                return
            if isinstance(value, str):
                value = value.strip()
                if value and value not in urls:
                    urls.append(value)
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item)

        collect(sources)
        return urls

    def _expand_mux_variants(self, url: str) -> List[str]:
        """
        Generate additional download candidates for Mux playback URLs.

        Args:
            url: Original URL detected in the post

        Returns:
            Ordered list of URLs to try (original first)
        """
        candidates: List[str] = []
        if not url or 'stream.mux.com' not in url:
            return [url]

        try:
            parsed = urlparse(url)
            path = parsed.path or ''
            _, _, filename = path.rpartition('/')
            query = f"?{parsed.query}" if parsed.query else ""
            prefix = url[: url.rfind('/') + 1] if '/' in url else url

            def add_candidate(suffix: str):
                candidate = f"{prefix}{suffix}{query}"
                if candidate not in candidates:
                    candidates.append(candidate)

            candidates.append(url)

            if filename.lower().endswith('.mp4'):
                name = filename.lower()
                variant_order: List[str] = []
                if name == 'medium.mp4':
                    variant_order = [
                        'download.mp4',
                        'source.mp4',
                        'high.mp4',
                        '720p.mp4',
                        '1080p.mp4'
                    ]
                elif name == 'high.mp4':
                    variant_order = ['download.mp4', 'source.mp4']
                elif name == 'source.mp4':
                    variant_order = ['download.mp4']

                for variant in variant_order:
                    add_candidate(variant)

                if query:
                    download_flag = f"{url}&download=1"
                else:
                    download_flag = f"{url}?download=1"
                if download_flag not in candidates:
                    candidates.append(download_flag)
        except Exception:
            return [url]

        return candidates or [url]

    def _create_temp_cookie_file(self) -> Optional[str]:
        """Create a temporary Netscape cookie file from the current session cookies."""
        if not self.session.cookies:
            return None

        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".cookies.txt")
            with open(tmp.name, 'w', encoding='utf-8') as fh:
                fh.write("# Netscape HTTP Cookie File\n")
                fh.write("# This file was generated automatically. Edit at your own risk.\n")
                for cookie in self.session.cookies:
                    domain = cookie.domain or ""
                    if not domain:
                        continue
                    include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
                    path = cookie.path or '/'
                    secure = 'TRUE' if cookie.secure else 'FALSE'
                    expiry = str(cookie.expires) if cookie.expires else '0'
                    name = cookie.name or ''
                    value = cookie.value or ''
                    fh.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
            return tmp.name
        except Exception as cookie_error:
            logger.debug(f"Could not generate temp cookie file: {cookie_error}")
            return None

    def _download_with_ytdlp(self, candidate_urls: List[str], output_path: Path, referer: Optional[str], count_success: bool = True) -> bool:
        """Fallback to yt-dlp for stubborn Mux streams."""
        yt_dlp_executable = shutil.which("yt-dlp")
        if not yt_dlp_executable:
            python_exe = shutil.which("python3") or shutil.which("python")
            if python_exe:
                yt_dlp_executable = None
                base_command = [python_exe, "-m", "yt_dlp"]
            else:
                logger.warning("yt-dlp not found. Install it to enable video fallback downloads.")
                return False
        else:
            base_command = [yt_dlp_executable]

        cookie_file = self._create_temp_cookie_file()
        headers = []
        if referer:
            headers.extend(["--referer", referer])
            headers.extend(["--add-header", "Origin: https://www.patreon.com"])

        output_path.parent.mkdir(parents=True, exist_ok=True)

        success = False

        for candidate in candidate_urls:
            command = base_command + [
                "--no-mtime",
                "--quiet",
                "--no-warnings",
                "--restrict-filenames",
                "--force-overwrites",
                "-o", str(output_path)
            ]

            if cookie_file:
                command.extend(["--cookies", cookie_file])
            command.extend(headers)
            command.append(candidate)

            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    text=True
                )
                if result.returncode == 0 and output_path.exists():
                    file_size = output_path.stat().st_size
                    logger.info(f"✓ yt-dlp downloaded: {output_path.name} ({self._format_size(file_size)})")
                    if count_success:
                        self.stats['videos']['downloaded'] += 1
                    success = True
                    break
                else:
                    logger.debug(f"yt-dlp failed for {candidate}: {result.stderr.strip()}")
            except FileNotFoundError:
                logger.warning("yt-dlp executable not found when attempting fallback.")
                break
            except Exception as fallback_error:
                logger.debug(f"yt-dlp error for {candidate}: {fallback_error}")

        if cookie_file:
            try:
                os.remove(cookie_file)
            except OSError:
                pass

        return success

    def download_file(self, url: str, output_path: Path, media_type: str = 'image', referer: Optional[str] = None) -> bool:
        """
        Download a single file

        Args:
            url: URL to download
            output_path: Path to save file
            media_type: Type of media (for stats)
            referer: Optional HTTP referer header to include

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
            headers = {}
            if referer:
                headers['Referer'] = referer
            response = self.session.get(url, stream=True, timeout=30, headers=headers)
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

    def download_images_from_post(self, post: Dict, creator_id: str, referer: Optional[str]) -> Dict[str, List[str]]:
        """
        Download all images from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier
            referer: HTTP referer for authenticated asset requests

        Returns:
            List of downloaded file paths
        """
        downloaded = []
        relatives = []

        # Get image URLs
        image_urls = self._flatten_urls([
            post.get('images'),
            post.get('preview_images'),
            post.get('image_urls')
        ])

        if not image_urls:
            return {'absolute': [], 'relative': []}

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

            if self.download_file(url, output_path, 'image', referer=referer):
                abs_path = str(output_path)
                if abs_path not in downloaded:
                    downloaded.append(abs_path)
                    try:
                        relatives.append(output_path.relative_to(self.output_dir).as_posix())
                    except ValueError:
                        relatives.append(abs_path)

            # Small delay between downloads
            time.sleep(0.5)

        return {'absolute': downloaded, 'relative': relatives}

    def download_videos_from_post(
        self,
        post: Dict,
        creator_id: str,
        referer: Optional[str],
        expected_count: Optional[int] = None
    ) -> Dict[str, List[str]]:
        """
        Download all videos from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier
            referer: HTTP referer for authenticated asset requests

        Returns:
            List of downloaded file paths
        """
        downloaded = []
        relatives = []

        preferred_downloads = self._flatten_urls(post.get('video_downloads'))
        fallback_videos = self._flatten_urls(post.get('videos'))
        stream_only_urls = self._flatten_urls(post.get('video_streams'))

        video_urls = preferred_downloads if preferred_downloads else fallback_videos

        if not video_urls:
            if stream_only_urls:
                logger.info("Video available as stream-only (HLS). Saved reference for manual download.")
            return {'absolute': [], 'relative': []}

        # Create creator subdirectory
        creator_dir = self.videos_dir / creator_id
        creator_dir.mkdir(exist_ok=True)

        post_id = post.get('post_id', 'unknown')

        video_extensions = {'.mp4', '.m4v', '.mov', '.webm', '.mkv'}

        successful_downloads = 0

        for i, url in enumerate(video_urls):
            if url.startswith('blob:'):
                logger.info(f"Skipped blob URL (stream-only): {url[:60]}...")
                self.stats['videos']['skipped'] += 1
                continue

            self.stats['videos']['total'] += 1

            filename = self._get_filename_from_url(url, '.mp4')
            filename = f"{post_id}_{i:02d}_{filename}"

            output_path = creator_dir / filename
            suffix = Path(filename).suffix.lower()

            candidate_urls = self._expand_mux_variants(url) if suffix in video_extensions else [url]

            if output_path.exists() and len(candidate_urls) > 1 and suffix in video_extensions:
                try:
                    existing_size = output_path.stat().st_size
                    if existing_size < self.min_video_size_bytes:
                        output_path.unlink()
                        logger.debug(f"Removed {output_path.name} (size {existing_size}B) before trying alternate variants")
                except Exception as unlink_error:
                    logger.debug(f"Could not remove existing file before retry: {unlink_error}")

            download_success = False
            for idx, candidate in enumerate(candidate_urls):
                if idx > 0 and output_path.exists() and suffix in video_extensions:
                    try:
                        existing_size = output_path.stat().st_size
                        if existing_size < self.min_video_size_bytes:
                            output_path.unlink()
                            logger.debug(f"Removed {output_path.name} (size {existing_size}B) to retry alternate variant")
                    except Exception as unlink_error:
                        logger.debug(f"Could not remove existing file before retry: {unlink_error}")

                if self.download_file(candidate, output_path, 'video', referer=referer):
                    download_success = True
                    break

            # Fallback to yt-dlp if direct download failed
            if not download_success and suffix in video_extensions:
                yt_candidates = candidate_urls.copy()
                for stream_url in stream_only_urls:
                    if stream_url not in yt_candidates:
                        yt_candidates.append(stream_url)

                if self._download_with_ytdlp(yt_candidates, output_path, referer):
                    download_success = True
                    logger.info(f"✓ Fallback succeeded for {output_path.name}")

            # Replace preview-sized files with yt-dlp result
            elif output_path.exists() and suffix in video_extensions:
                try:
                    file_size = output_path.stat().st_size
                except OSError:
                    file_size = 0
                if file_size and file_size < self.min_video_size_bytes:
                    logger.info(f"Preview-sized video detected ({self._format_size(file_size)}). Retrying with yt-dlp...")
                    if self._download_with_ytdlp(candidate_urls, output_path, referer, count_success=False):
                        download_success = True
                        logger.info(f"✓ Replaced preview file with full download for {output_path.name}")

            if download_success:
                abs_path = str(output_path)
                if abs_path not in downloaded:
                    downloaded.append(abs_path)
                    try:
                        relatives.append(output_path.relative_to(self.output_dir).as_posix())
                    except ValueError:
                        relatives.append(abs_path)
                successful_downloads += 1

            if expected_count and successful_downloads >= expected_count:
                break

            time.sleep(1)  # Longer delay for videos

        if not downloaded and stream_only_urls:
            logger.info("No downloadable video URLs, but stream sources are available (HLS).")

        return {'absolute': downloaded, 'relative': relatives}

    def download_audios_from_post(self, post: Dict, creator_id: str, referer: Optional[str]) -> Dict[str, List[str]]:
        """
        Download all audio files from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier
            referer: HTTP referer for authenticated asset requests

        Returns:
            List of downloaded file paths
        """
        downloaded = []
        relatives = []

        audio_urls = self._flatten_urls([
            post.get('audios'),
            post.get('audio_urls')
        ])

        if not audio_urls:
            return {'absolute': [], 'relative': []}

        # Create creator subdirectory
        creator_dir = self.audio_dir / creator_id
        creator_dir.mkdir(exist_ok=True)

        post_id = post.get('post_id', 'unknown')

        for i, url in enumerate(audio_urls):
            self.stats['audios']['total'] += 1

            filename = self._get_filename_from_url(url, '.mp3')
            filename = f"{post_id}_{i:02d}_{filename}"

            output_path = creator_dir / filename

            if self.download_file(url, output_path, 'audio', referer=referer):
                abs_path = str(output_path)
                if abs_path not in downloaded:
                    downloaded.append(abs_path)
                    try:
                        relatives.append(output_path.relative_to(self.output_dir).as_posix())
                    except ValueError:
                        relatives.append(abs_path)

            time.sleep(0.5)

        return {'absolute': downloaded, 'relative': relatives}

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

        referer = post.get('post_url') or post.get('url') or 'https://www.patreon.com/'

        result = {
            'post_id': post.get('post_id'),
            'images': [],
            'images_relative': [],
            'videos': [],
            'videos_relative': [],
            'video_streams': post.get('video_streams', []),
            'audios': [],
            'audios_relative': []
        }

        # Download images
        images = self.download_images_from_post(post, creator_id, referer)
        result['images'] = images['absolute']
        result['images_relative'] = images['relative']

        # Download videos
        video_block_count = sum(
            1
            for block in post.get('content_blocks') or []
            if isinstance(block, dict) and block.get('type') == 'video'
        )
        expected_videos = video_block_count if video_block_count > 0 else None

        videos = self.download_videos_from_post(post, creator_id, referer, expected_videos)
        result['videos'] = videos['absolute']
        result['videos_relative'] = videos['relative']

        # Download audios
        audios = self.download_audios_from_post(post, creator_id, referer)
        result['audios'] = audios['absolute']
        result['audios_relative'] = audios['relative']

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
    parser.add_argument('--cookies', type=str, help='Path to Patreon cookies JSON (defaults to config/patreon_cookies.json)')

    args = parser.parse_args()

    downloader = MediaDownloader(cookies_path=args.cookies or "config/patreon_cookies.json")

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
