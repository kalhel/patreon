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
from pathlib import PurePosixPath
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

# Audio processing for waveform generation
try:
    from pydub import AudioSegment
    import numpy as np
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    logger.warning("⚠️  pydub/numpy not available - waveform generation disabled")


class MediaDownloader:
    """Downloads media files from Patreon posts"""

    def __init__(self, output_dir: str = "data/media", cookies_path: Optional[str] = "config/patreon_cookies.json"):
        """
        Initialize downloader

        Args:
            output_dir: Base directory for media downloads (data/media)
            cookies_path: Optional path to Patreon cookies captured by Selenium

        Directory structure:
            data/media/images/{creator_id}/{post_id}_00_image.jpg
            data/media/videos/{creator_id}/{post_id}_00_video.mp4
            data/media/videos/{creator_id}/{post_id}_00_subtitle.vtt
            data/media/audio/{creator_id}/{post_id}_00_audio.mp3
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Media type directories
        self.images_dir = self.output_dir / "images"
        self.videos_dir = self.output_dir / "videos"
        self.audio_dir = self.output_dir / "audio"

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

    def _validate_vtt_subtitle(self, content: bytes) -> bool:
        """
        Validate that a VTT file contains actual subtitles, not storyboard URLs.

        Args:
            content: Raw bytes content of the VTT file

        Returns:
            bool: True if it's a valid subtitle file, False if it's a storyboard
        """
        try:
            text = content.decode('utf-8', errors='ignore')
            lines = text.split('\n')

            # Check first 50 lines for URL patterns that indicate storyboard
            check_lines = lines[:50]
            for line in check_lines:
                line = line.strip()
                # If we find image URLs (especially from Mux storyboard), it's not a subtitle file
                if 'image.mux.com' in line.lower() or '/storyboard.jpg' in line.lower():
                    logger.info("  ⚠️  Detected storyboard VTT (contains image URLs), rejecting")
                    return False
                # Also check for generic image URLs in subtitle timing lines
                if line.startswith('http') and any(ext in line.lower() for ext in ['.jpg', '.png', '.jpeg', '.webp']):
                    logger.info("  ⚠️  Detected storyboard VTT (contains image URLs), rejecting")
                    return False

            return True
        except Exception as e:
            logger.debug(f"Error validating VTT content: {e}")
            return True  # Accept on error to avoid breaking downloads

    def _validate_image_size(self, file_path: Path, min_width: int = 400, min_height: int = 400) -> bool:
        """
        Validate that an image meets minimum size requirements.
        Used to filter out small avatars and icons.

        Args:
            file_path: Path to the image file
            min_width: Minimum width in pixels
            min_height: Minimum height in pixels

        Returns:
            bool: True if image meets size requirements
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                width, height = img.size
                if width < min_width or height < min_height:
                    logger.info(f"  ⚠️  Rejected small image ({width}x{height}): {file_path.name}")
                    return False
                return True
        except ImportError:
            # If PIL is not available, accept all images
            logger.debug("PIL not available, skipping image size validation")
            return True
        except Exception as e:
            logger.debug(f"Could not validate image size: {e}")
            return True  # Accept on error to avoid breaking downloads

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
            Dict with 'absolute' and 'relative' lists of downloaded file paths
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
        creator_dir.mkdir(parents=True, exist_ok=True)

        post_id = post.get('post_id', 'unknown')

        # Download each image
        for i, url in enumerate(image_urls):
            self.stats['images']['total'] += 1

            filename = self._get_filename_from_url(url, '.jpg')
            filename = f"{post_id}_{i:02d}_{filename}"

            output_path = creator_dir / filename

            if self.download_file(url, output_path, 'image', referer=referer):
                # Validate image size to filter out small avatars/icons
                if not self._validate_image_size(output_path, min_width=400, min_height=400):
                    # Remove the small image
                    try:
                        output_path.unlink()
                        self.stats['images']['downloaded'] -= 1
                        self.stats['images']['skipped'] += 1
                    except Exception:
                        pass
                    time.sleep(0.5)
                    continue

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

        # Define variables at the beginning
        creator_dir = self.videos_dir / creator_id
        creator_dir.mkdir(parents=True, exist_ok=True)
        post_id = post.get('post_id', 'unknown')
        video_extensions = {'.mp4', '.m4v', '.mov', '.webm', '.mkv'}
        successful_downloads = 0

        preferred_downloads = self._flatten_urls(post.get('video_downloads'))
        fallback_videos = self._flatten_urls(post.get('videos'))
        stream_only_urls = self._flatten_urls(post.get('video_streams'))

        def dedupe_mux(urls: List[str]) -> List[str]:
            unique: List[str] = []
            seen = set()

            for url in urls:
                if not url:
                    continue
                key = url
                if 'stream.mux.com' in url:
                    try:
                        parsed = urlparse(url)
                        parts = [p for p in PurePosixPath(parsed.path or '').parts if p]
                        playback_id = parts[0] if parts else url
                        key = ('mux', playback_id)
                    except Exception:
                        key = url

                if key in seen:
                    continue
                seen.add(key)
                unique.append(url)

            return unique


        def filter_video_candidates(urls: List[str]) -> List[str]:
            filtered = []
            for url in urls or []:
                if not url:
                    continue
                lower = url.lower()

                # Rechazar archivos que NO son videos
                if any(reject in lower for reject in ['.vtt', '.json', '/text/', '/thumbnail', '/storyboard', 'thumbnail.jpg', 'thumbnail.png']):
                    logger.info(f"  ⚠️  [VIDEO DL] RECHAZADO (no es video): {url[:80]}...")
                    continue

                # Aceptar solo videos reales o streams HLS
                if any(lower.endswith(ext) for ext in video_extensions) or '.m3u8' in lower:
                    filtered.append(url)
                    logger.info(f"  ✓ [VIDEO DL] ACEPTADO: {url[:80]}...")
            return filtered

        video_urls = preferred_downloads if preferred_downloads else fallback_videos
        video_urls = dedupe_mux(video_urls)
        video_urls = filter_video_candidates(video_urls)
        stream_only_urls = dedupe_mux(stream_only_urls)
        stream_only_urls = filter_video_candidates(stream_only_urls)

        logger.info(f"  📊 [VIDEO DL] URLs después de dedupe/filter:")
        logger.info(f"  📊 [VIDEO DL] - video_urls (directas): {len(video_urls)}")
        for i, url in enumerate(video_urls[:3]):
            logger.info(f"  📊 [VIDEO DL]   {i+1}. {url[:80]}...")
        logger.info(f"  📊 [VIDEO DL] - stream_only_urls (HLS): {len(stream_only_urls)}")
        for i, url in enumerate(stream_only_urls[:3]):
            logger.info(f"  📊 [VIDEO DL]   {i+1}. {url[:80]}...")
        logger.info(f"  📊 [VIDEO DL] - expected_count: {expected_count}")

        if not video_urls:
            if stream_only_urls:
                logger.info("  🎬 [VIDEO DL] Video disponible como stream-only (HLS). Intentando yt-dlp fallback.")

                for idx, stream_url in enumerate(stream_only_urls):
                    logger.info(f"  🎬 [VIDEO DL] Procesando stream HLS #{idx+1}: {stream_url[:80]}...")
                    filename = f"{post_id}_{idx:02d}.mp4"
                    output_path = creator_dir / filename
                    logger.info(f"  💾 [VIDEO DL] Descargando a: {output_path}")

                    if self._download_with_ytdlp([stream_url], output_path, referer):
                        abs_path = str(output_path)
                        if abs_path not in downloaded:
                            downloaded.append(abs_path)
                            try:
                                relatives.append(output_path.relative_to(self.output_dir).as_posix())
                            except ValueError:
                                relatives.append(abs_path)

                        self.stats['videos']['total'] += 1
                        successful_downloads += 1

                        if expected_count and successful_downloads >= expected_count:
                            logger.info("✓ Downloaded stream-only video via yt-dlp")
                            return {'absolute': downloaded, 'relative': relatives}

                        # If no expected count, we only need the first success
                        logger.info("✓ Downloaded stream-only video via yt-dlp")
                        return {'absolute': downloaded, 'relative': relatives}

            return {'absolute': [], 'relative': []}

        encountered_blob_only = True

        for i, url in enumerate(video_urls):
            if url.startswith('blob:'):
                logger.info(f"Skipped blob URL (stream-only): {url[:60]}...")
                self.stats['videos']['skipped'] += 1
                continue

            encountered_blob_only = False

            self.stats['videos']['total'] += 1

            # Use clean filename: {post_id}_00.mp4
            ext = Path(urlparse(url).path).suffix or '.mp4'
            filename = f"{post_id}_{i:02d}{ext}"

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

        if not downloaded and (stream_only_urls or encountered_blob_only):
            candidates = stream_only_urls or []
            if encountered_blob_only and not candidates:
                candidates = preferred_downloads or fallback_videos

            if candidates:
                logger.info("No direct video download succeeded. Attempting yt-dlp fallback for stream sources.")

                for idx, stream_url in enumerate(candidates):
                    filename = f"{post_id}_{idx:02d}.mp4"
                    output_path = creator_dir / filename

                    if self._download_with_ytdlp([stream_url], output_path, referer):
                        abs_path = str(output_path)
                        if abs_path not in downloaded:
                            downloaded.append(abs_path)
                            try:
                                relatives.append(output_path.relative_to(self.output_dir).as_posix())
                            except ValueError:
                                relatives.append(abs_path)
                            successful_downloads += 1

                        self.stats['videos']['total'] += 1

                        # Stop if we've reached expected count
                        if expected_count and successful_downloads >= expected_count:
                            break

                if downloaded:
                    logger.info("✓ Stream-only video captured via yt-dlp")
                    return {'absolute': downloaded, 'relative': relatives}

        if not downloaded and stream_only_urls:
            logger.info("No downloadable video URLs, but stream sources are available (HLS).")

        return {'absolute': downloaded, 'relative': relatives}

    def download_subtitles_from_post(self, post: Dict, creator_id: str, referer: Optional[str]) -> Dict[str, List[str]]:
        """
        Download subtitle files (.vtt) from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier
            referer: HTTP referer for authenticated asset requests

        Returns:
            Dict with 'absolute' and 'relative' lists of downloaded subtitle paths
        """
        downloaded = []
        relatives = []

        # Get video_downloads which may contain .vtt files
        video_downloads = self._flatten_urls(post.get('video_downloads'))

        # Filter only .vtt files
        vtt_urls = [url for url in video_downloads if url and '.vtt' in url.lower()]

        if not vtt_urls:
            logger.info("  📝 [SUBTITLES] No hay archivos .vtt para descargar")
            return {'absolute': [], 'relative': []}

        logger.info(f"  📝 [SUBTITLES] Encontrados {len(vtt_urls)} archivos de subtítulos")

        creator_dir = self.videos_dir / creator_id
        creator_dir.mkdir(parents=True, exist_ok=True)
        post_id = post.get('post_id', 'unknown')

        # Use a counter that only increments for valid saved files
        saved_count = 0

        for i, url in enumerate(vtt_urls):
            try:
                response = self.session.get(url, headers={'Referer': referer}, timeout=30)
                response.raise_for_status()

                # Validate that this is a real subtitle file, not a storyboard
                if not self._validate_vtt_subtitle(response.content):
                    logger.info(f"  ⚠️  [SUBTITLES] Skipped storyboard file (would be #{i})")
                    continue

                # Use saved_count for filename, not the loop index
                filename = f"{post_id}_{saved_count:02d}.vtt"
                output_path = creator_dir / filename

                output_path.write_bytes(response.content)
                abs_path = str(output_path)
                downloaded.append(abs_path)

                try:
                    relatives.append(output_path.relative_to(self.output_dir).as_posix())
                except ValueError:
                    relatives.append(abs_path)

                logger.info(f"  ✓ [SUBTITLES] Descargado: {filename}")
                saved_count += 1

            except Exception as e:
                logger.warning(f"  ⚠️  [SUBTITLES] Error descargando {url[:50]}: {e}")

        return {'absolute': downloaded, 'relative': relatives}

    def generate_waveform(self, audio_path: Path, samples: int = 500) -> Optional[Path]:
        """
        Generate waveform data from audio file and save as JSON

        Args:
            audio_path: Path to audio file (.mp3, .wav, etc)
            samples: Number of waveform samples to generate (default 500)

        Returns:
            Path to generated JSON file, or None if generation failed
        """
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.warning(f"⚠️  Cannot generate waveform - pydub/numpy not installed")
            return None

        try:
            # Load audio file
            audio = AudioSegment.from_file(str(audio_path))

            # Convert to mono and get raw data
            audio_mono = audio.set_channels(1)
            samples_data = np.array(audio_mono.get_array_of_samples())

            # Normalize to -1 to 1 range
            max_val = np.abs(samples_data).max()
            if max_val > 0:
                samples_data = samples_data.astype(float) / max_val

            # Downsample to desired number of samples
            chunk_size = len(samples_data) // samples
            if chunk_size < 1:
                chunk_size = 1

            waveform = []
            for i in range(samples):
                start = i * chunk_size
                end = start + chunk_size
                if end > len(samples_data):
                    end = len(samples_data)
                chunk = samples_data[start:end]
                if len(chunk) > 0:
                    # Use RMS (root mean square) for better waveform representation
                    rms = np.sqrt(np.mean(chunk**2))
                    waveform.append(float(rms))

            # Save as JSON next to the audio file
            json_path = audio_path.with_suffix('.json')
            waveform_data = {
                'version': 1,
                'channels': 1,
                'sample_rate': audio.frame_rate,
                'samples_per_pixel': chunk_size,
                'bits': 8,
                'length': len(samples_data),
                'data': waveform
            }

            with open(json_path, 'w') as f:
                json.dump(waveform_data, f)

            logger.info(f"  ✓ [WAVEFORM] Generated: {json_path.name}")
            return json_path

        except Exception as e:
            logger.error(f"  ✗ [WAVEFORM] Failed to generate for {audio_path.name}: {e}")
            return None

    def download_audios_from_post(self, post: Dict, creator_id: str, referer: Optional[str]) -> Dict[str, List[str]]:
        """
        Download all audio files from a post

        Args:
            post: Post dictionary
            creator_id: Creator identifier
            referer: HTTP referer for authenticated asset requests

        Returns:
            Dict with 'absolute' and 'relative' lists of downloaded audio paths
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
        creator_dir.mkdir(parents=True, exist_ok=True)

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

                    # Generate waveform JSON for this audio file
                    self.generate_waveform(output_path)

            time.sleep(0.5)

        return {'absolute': downloaded, 'relative': relatives}

    def _clean_vtt_alignment(self, vtt_path: Path) -> bool:
        """
        Clean alignment parameters from VTT subtitle files.

        YouTube subtitles often include 'align:start position:0%' which forces
        left alignment and breaks our centered subtitle CSS.

        Args:
            vtt_path: Path to VTT file to clean

        Returns:
            bool: True if cleaned successfully
        """
        try:
            # Read the file
            with open(vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Remove alignment parameters from timestamp lines
            # Pattern: "00:00:00.000 --> 00:00:00.000 align:start position:0%"
            # We want: "00:00:00.000 --> 00:00:00.000"
            import re

            # Remove align:start, align:end, align:middle, etc.
            content = re.sub(r'\s+align:\w+', '', content)

            # Remove position:N%
            content = re.sub(r'\s+position:\d+%', '', content)

            # Remove line:N%
            content = re.sub(r'\s+line:\d+%', '', content)

            # Remove size:N%
            content = re.sub(r'\s+size:\d+%', '', content)

            # Only write if content changed
            if content != original_content:
                with open(vtt_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"  🧹 [VTT CLEAN] Removed alignment parameters from: {vtt_path.name}")
                return True

            return False

        except Exception as e:
            logger.warning(f"  ⚠️  [VTT CLEAN] Error cleaning {vtt_path.name}: {e}")
            return False

    def download_youtube_videos_from_post(self, post: Dict, creator_id: str) -> Dict[str, List[str]]:
        """
        Download YouTube videos from youtube_embed blocks

        Args:
            post: Post dictionary with content_blocks
            creator_id: Creator identifier

        Returns:
            Dict with 'absolute' and 'relative' lists of downloaded video/subtitle paths
        """
        downloaded_videos = []
        downloaded_subtitles = []
        relatives_videos = []
        relatives_subtitles = []

        # Find youtube_embed blocks
        youtube_blocks = []
        content_blocks = post.get('content_blocks', [])

        for block in content_blocks:
            if isinstance(block, dict) and block.get('type') == 'youtube_embed':
                url = block.get('url', '')
                if url:
                    youtube_blocks.append(block)

        if not youtube_blocks:
            return {
                'absolute': [],
                'relative': [],
                'subtitles_absolute': [],
                'subtitles_relative': []
            }

        logger.info(f"  🎬 [YOUTUBE] Found {len(youtube_blocks)} YouTube video(s) to download")

        # Create creator subdirectory
        creator_dir = self.videos_dir / creator_id
        creator_dir.mkdir(parents=True, exist_ok=True)

        post_id = post.get('post_id', 'unknown')

        # Find yt-dlp executable
        yt_dlp_executable = shutil.which("yt-dlp")
        if not yt_dlp_executable:
            python_exe = shutil.which("python3") or shutil.which("python")
            if python_exe:
                base_command = [python_exe, "-m", "yt_dlp"]
            else:
                logger.warning("  ⚠️  [YOUTUBE] yt-dlp not found - skipping YouTube downloads")
                return {
                    'absolute': [],
                    'relative': [],
                    'subtitles_absolute': [],
                    'subtitles_relative': []
                }
        else:
            base_command = [yt_dlp_executable]

        for idx, block in enumerate(youtube_blocks):
            url = block.get('url', '')

            # Extract video ID from URL
            video_id = None
            if 'youtube.com' in url:
                if 'v=' in url:
                    video_id = url.split('v=')[1].split('&')[0]
                elif 'embed/' in url:
                    video_id = url.split('embed/')[1].split('?')[0]
            elif 'youtu.be' in url:
                video_id = url.split('youtu.be/')[1].split('?')[0]

            if not video_id:
                logger.warning(f"  ⚠️  [YOUTUBE] Could not extract video ID from: {url}")
                continue

            logger.info(f"  📥 [YOUTUBE] Downloading video {idx+1}/{len(youtube_blocks)}: {video_id}")

            # Output filename pattern
            filename_base = f"{post_id}_yt{idx:02d}"

            # First, download video without subtitles (to avoid subtitle errors blocking video)
            video_command = base_command + [
                '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
                '--no-mtime',
                '--no-warnings',
                '-o', str(creator_dir / f'{filename_base}.%(ext)s'),
                url
            ]

            try:
                logger.info(f"  🔄 [YOUTUBE] Downloading video {video_id}...")
                result = subprocess.run(
                    video_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    text=True,
                    timeout=600  # 10 minute timeout per video
                )

                # Check for downloaded video file
                video_path = creator_dir / f'{filename_base}.mp4'
                if video_path.exists():
                    file_size = video_path.stat().st_size
                    logger.info(f"  ✓ [YOUTUBE] Downloaded video: {video_path.name} ({self._format_size(file_size)})")

                    abs_path = str(video_path)
                    downloaded_videos.append(abs_path)
                    try:
                        relatives_videos.append(video_path.relative_to(self.output_dir).as_posix())
                    except ValueError:
                        relatives_videos.append(abs_path)

                    self.stats['videos']['downloaded'] += 1
                    self.stats['videos']['total'] += 1

                    # Update the content block to be a video block instead of youtube_embed
                    block['type'] = 'video'
                    block['youtube_downloaded'] = True
                    block['youtube_video_id'] = video_id

                    # Now try to download subtitles separately (each language independently)
                    # This way if one fails (rate limit), the other can still succeed
                    logger.info(f"  📝 [YOUTUBE] Attempting to download subtitles...")

                    for lang in ['es', 'en']:
                        subtitle_command = base_command + [
                            '--skip-download',        # Don't re-download the video
                            '--write-subs',           # Manual subtitles
                            '--write-auto-subs',      # Auto-generated subtitles
                            '--sub-langs', lang,      # One language at a time
                            '--sub-format', 'vtt',
                            '--convert-subs', 'vtt',
                            '--ignore-errors',        # Continue if this language fails
                            '--no-warnings',
                            '-o', str(creator_dir / f'{filename_base}.%(ext)s'),
                            url
                        ]

                        try:
                            sub_result = subprocess.run(
                                subtitle_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                check=False,
                                text=True,
                                timeout=60  # 1 minute timeout for subtitles
                            )

                            if sub_result.returncode != 0:
                                if '429' in sub_result.stderr or 'Too Many Requests' in sub_result.stderr:
                                    logger.warning(f"  ⚠️  [YOUTUBE] Rate limited for {lang} subtitles")
                                else:
                                    logger.debug(f"  ℹ️  [YOUTUBE] {lang} subtitles not available or failed")
                        except Exception as e:
                            logger.debug(f"  ℹ️  [YOUTUBE] Error downloading {lang} subtitles: {e}")

                    # Check for subtitle files with various naming patterns from yt-dlp
                    # Patterns: .es.vtt, .en.vtt, .es-es.vtt, .en-US.vtt, .es-orig.vtt, etc.
                    subtitle_patterns = [
                        f'{filename_base}.es*.vtt',
                        f'{filename_base}.en*.vtt',
                        f'{filename_base}.*es*.vtt',
                        f'{filename_base}.*en*.vtt'
                    ]

                    found_subs = set()
                    for pattern in subtitle_patterns:
                        import glob
                        matches = glob.glob(str(creator_dir / pattern))
                        for match_path in matches:
                            subtitle_path = Path(match_path)

                            # Skip if already processed
                            if str(subtitle_path) in found_subs:
                                continue
                            found_subs.add(str(subtitle_path))

                            # Detect language from filename
                            name_lower = subtitle_path.stem.lower()
                            lang_code = None
                            if '.es' in name_lower or 'spanish' in name_lower:
                                lang_code = 'es'
                            elif '.en' in name_lower or 'english' in name_lower:
                                lang_code = 'en'
                            else:
                                # Default to 'unknown' if can't detect
                                lang_code = 'xx'

                            # Rename to consistent format: {post_id}_yt00_es.vtt
                            new_name = f'{filename_base}_{lang_code}.vtt'
                            new_path = creator_dir / new_name

                            # Rename if different
                            if subtitle_path != new_path:
                                subtitle_path.rename(new_path)
                                logger.info(f"  📝 [YOUTUBE] Renamed subtitle: {subtitle_path.name} → {new_name}")
                                subtitle_path = new_path

                            # Clean alignment parameters from VTT file
                            self._clean_vtt_alignment(subtitle_path)

                            logger.info(f"  ✓ [YOUTUBE] Found subtitle ({lang_code}): {subtitle_path.name}")
                            abs_sub_path = str(subtitle_path)
                            downloaded_subtitles.append(abs_sub_path)
                            try:
                                relatives_subtitles.append(subtitle_path.relative_to(self.output_dir).as_posix())
                            except ValueError:
                                relatives_subtitles.append(abs_sub_path)

                    # Log summary of what was found
                    if found_subs:
                        logger.info(f"  ✓ [YOUTUBE] Found {len(found_subs)} subtitle file(s)")
                    else:
                        logger.info(f"  ℹ️  [YOUTUBE] No subtitles found (may be rate limited or unavailable)")
                else:
                    logger.warning(f"  ⚠️  [YOUTUBE] Video download failed for {video_id}")
                    logger.warning(f"  Return code: {result.returncode}")
                    if result.stderr:
                        logger.warning(f"  Error output: {result.stderr[:500]}")

            except subprocess.TimeoutExpired:
                logger.error(f"  ❌ [YOUTUBE] Download timeout for {video_id}")
            except Exception as e:
                logger.error(f"  ❌ [YOUTUBE] Error downloading {video_id}: {e}")

            # Small delay between downloads
            time.sleep(1)

        logger.info(f"  ✓ [YOUTUBE] Downloaded {len(downloaded_videos)} video(s), {len(downloaded_subtitles)} subtitle(s)")

        return {
            'absolute': downloaded_videos,
            'relative': relatives_videos,
            'subtitles_absolute': downloaded_subtitles,
            'subtitles_relative': relatives_subtitles
        }

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
            'video_subtitles': [],
            'video_subtitles_relative': [],
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

        # Download subtitles (.vtt files)
        subtitles = self.download_subtitles_from_post(post, creator_id, referer)
        result['video_subtitles'] = subtitles['absolute']
        result['video_subtitles_relative'] = subtitles['relative']

        # Download audios
        audios = self.download_audios_from_post(post, creator_id, referer)
        result['audios'] = audios['absolute']
        result['audios_relative'] = audios['relative']

        # Download YouTube videos (if any youtube_embed blocks exist)
        youtube_result = self.download_youtube_videos_from_post(post, creator_id)
        if youtube_result['absolute']:
            # Add YouTube videos to the main video lists
            result['videos'].extend(youtube_result['absolute'])
            result['videos_relative'].extend(youtube_result['relative'])
            # Add YouTube subtitles to the subtitles lists
            result['video_subtitles'].extend(youtube_result['subtitles_absolute'])
            result['video_subtitles_relative'].extend(youtube_result['subtitles_relative'])

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
