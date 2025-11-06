#!/usr/bin/env python3
"""Lightweight tests for media downloader helpers."""

import sys
import tempfile
import unittest

sys.path.insert(0, 'src')

from media_downloader import MediaDownloader  # noqa: E402


class DummyDriver:
    """Simple stand-in for Selenium driver returning static cookies."""

    def __init__(self, cookies):
        self._cookies = cookies

    def get_cookies(self):
        return list(self._cookies)


class MediaDownloaderTests(unittest.TestCase):
    """Validate helper utilities that do not hit the network."""

    def test_flatten_urls_handles_nested_structures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = MediaDownloader(output_dir=tmpdir, cookies_path=None)

            urls = downloader._flatten_urls([
                "https://example.com/video-a.mp4",
                [
                    "https://example.com/video-b.mp4",
                    {"fallback": "https://example.com/video-c.mp4"}
                ],
                {"other": ["https://example.com/video-a.mp4", "", None]},
                None
            ])

            self.assertEqual(
                urls,
                [
                    "https://example.com/video-a.mp4",
                    "https://example.com/video-b.mp4",
                    "https://example.com/video-c.mp4"
                ]
            )

    def test_sync_cookies_from_driver_populates_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = MediaDownloader(output_dir=tmpdir, cookies_path=None)
            driver = DummyDriver([{
                'name': 'session_id',
                'value': 'abc123',
                'domain': '.patreon.com',
                'path': '/'
            }])

            downloader.sync_cookies_from_driver(driver)

            self.assertEqual(downloader.session.cookies.get('session_id'), 'abc123')

    def test_expand_mux_variants_includes_download(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = MediaDownloader(output_dir=tmpdir, cookies_path=None)
            original = "https://stream.mux.com/PLAYBACK/medium.mp4?token=abc"
            expanded = downloader._expand_mux_variants(original)
            self.assertIn(original, expanded)
            self.assertIn("https://stream.mux.com/PLAYBACK/download.mp4?token=abc", expanded)


if __name__ == "__main__":
    unittest.main()
