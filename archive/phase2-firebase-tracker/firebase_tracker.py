#!/usr/bin/env python3
"""
Firebase Realtime Database Integration
Tracks post processing state in real-time
"""

import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FirebaseTracker:
    """Track post processing state in Firebase Realtime Database"""

    def __init__(self, database_url: str, database_secret: str):
        """
        Initialize Firebase tracker

        Args:
            database_url: Firebase Realtime Database URL
            database_secret: Database secret for authentication
        """
        self.database_url = database_url.rstrip('/')
        self.database_secret = database_secret
        logger.info(f"🔥 Firebase Tracker initialized: {database_url}")

    def _build_url(self, path: str) -> str:
        """Build Firebase URL with authentication"""
        return f"{self.database_url}/{path}.json?auth={self.database_secret}"

    def _get(self, path: str) -> Optional[Dict]:
        """GET request to Firebase"""
        try:
            response = requests.get(self._build_url(path), timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Firebase GET error at {path}: {e}")
            return None

    def _put(self, path: str, data: Dict) -> bool:
        """PUT request to Firebase"""
        try:
            response = requests.put(
                self._build_url(path),
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Firebase PUT error at {path}: {e}")
            return False

    def _patch(self, path: str, data: Dict) -> bool:
        """PATCH request to Firebase (update only specified fields)"""
        try:
            response = requests.patch(
                self._build_url(path),
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Firebase PATCH error at {path}: {e}")
            return False

    # ========== POST TRACKING ==========

    def create_post_record(self, post_id: str, creator_id: str, post_url: str) -> bool:
        """
        Create initial post record in Firebase

        Args:
            post_id: Patreon post ID
            creator_id: Creator identifier
            post_url: URL to the post

        Returns:
            True if successful
        """
        data = {
            "post_id": post_id,
            "creator_id": creator_id,
            "post_url": post_url,
            "status": {
                "url_collected": True,
                "url_collected_at": datetime.now().isoformat(),
                "details_extracted": False,
                "details_extracted_at": None,
                "uploaded_to_notion": False,
                "uploaded_to_notion_at": None,
                "last_attempt": datetime.now().isoformat(),
                "attempt_count": 1,
                "errors": []
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        success = self._put(f"posts/{post_id}", data)
        if success:
            logger.info(f"  ✓ Created Firebase record for post {post_id}")
        return success

    def mark_url_collected(self, post_id: str) -> bool:
        """Mark post URL as collected"""
        data = {
            "status/url_collected": True,
            "status/url_collected_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return self._patch(f"posts/{post_id}", data)

    def mark_details_extracted(self, post_id: str, success: bool = True, error: str = None) -> bool:
        """
        Mark post details as extracted

        Args:
            post_id: Post ID
            success: Whether extraction was successful
            error: Error message if failed
        """
        data = {
            "status/details_extracted": success,
            "status/details_extracted_at": datetime.now().isoformat() if success else None,
            "updated_at": datetime.now().isoformat()
        }

        if error:
            # Append error to errors array
            existing = self.get_post(post_id)
            if existing:
                errors = existing.get('status', {}).get('errors', [])
                errors.append({
                    "timestamp": datetime.now().isoformat(),
                    "phase": "details_extraction",
                    "error": error
                })
                data["status/errors"] = errors

        success_result = self._patch(f"posts/{post_id}", data)
        if success_result:
            logger.info(f"  ✓ Marked post {post_id} details as {'extracted' if success else 'failed'}")
        return success_result

    def mark_uploaded_to_notion(self, post_id: str, notion_page_id: str = None) -> bool:
        """Mark post as uploaded to Notion"""
        data = {
            "status/uploaded_to_notion": True,
            "status/uploaded_to_notion_at": datetime.now().isoformat(),
            "notion_page_id": notion_page_id,
            "updated_at": datetime.now().isoformat()
        }
        return self._patch(f"posts/{post_id}", data)

    def increment_attempt(self, post_id: str) -> bool:
        """Increment attempt count for a post"""
        existing = self.get_post(post_id)
        if not existing:
            return False

        attempt_count = existing.get('status', {}).get('attempt_count', 0) + 1
        data = {
            "status/attempt_count": attempt_count,
            "status/last_attempt": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return self._patch(f"posts/{post_id}", data)

    def get_post(self, post_id: str) -> Optional[Dict]:
        """Get post record from Firebase"""
        return self._get(f"posts/{post_id}")

    def post_exists(self, post_id: str) -> bool:
        """Check if post exists in Firebase"""
        return self.get_post(post_id) is not None

    def get_all_posts(self) -> Dict[str, Dict]:
        """Get all posts from Firebase"""
        posts = self._get("posts")
        return posts if posts else {}

    def get_posts_by_creator(self, creator_id: str) -> List[Dict]:
        """Get all posts for a specific creator"""
        all_posts = self.get_all_posts()
        return [
            post for post in all_posts.values()
            if post.get('creator_id') == creator_id
        ]

    def get_posts_needing_details(self, creator_id: str = None) -> List[Dict]:
        """
        Get posts that need details extraction

        Args:
            creator_id: Optional filter by creator

        Returns:
            List of posts with URL collected but details not extracted
        """
        all_posts = self.get_all_posts()
        posts_needing_details = []

        for post in all_posts.values():
            status = post.get('status', {})

            # Filter criteria
            url_collected = status.get('url_collected', False)
            details_extracted = status.get('details_extracted', False)
            creator_match = creator_id is None or post.get('creator_id') == creator_id

            if url_collected and not details_extracted and creator_match:
                posts_needing_details.append(post)

        return posts_needing_details

    def get_posts_needing_notion_upload(self, creator_id: str = None) -> List[Dict]:
        """Get posts that need to be uploaded to Notion"""
        all_posts = self.get_all_posts()
        posts_needing_upload = []

        for post in all_posts.values():
            status = post.get('status', {})

            details_extracted = status.get('details_extracted', False)
            uploaded = status.get('uploaded_to_notion', False)
            creator_match = creator_id is None or post.get('creator_id') == creator_id

            if details_extracted and not uploaded and creator_match:
                posts_needing_upload.append(post)

        return posts_needing_upload

    # ========== CREATOR STATS ==========

    def update_creator_stats(self, creator_id: str) -> bool:
        """Update statistics for a creator"""
        posts = self.get_posts_by_creator(creator_id)

        total = len(posts)
        processed = sum(1 for p in posts if p.get('status', {}).get('details_extracted', False))
        pending = total - processed

        data = {
            "creator_id": creator_id,
            "last_scrape": datetime.now().isoformat(),
            "total_posts": total,
            "processed_posts": processed,
            "pending_posts": pending,
            "updated_at": datetime.now().isoformat()
        }

        success = self._put(f"creators/{creator_id}", data)
        if success:
            logger.info(f"  ✓ Updated stats for {creator_id}: {processed}/{total} processed")
        return success

    def get_creator_stats(self, creator_id: str) -> Optional[Dict]:
        """Get statistics for a creator"""
        return self._get(f"creators/{creator_id}")

    def get_all_creator_stats(self) -> Dict[str, Dict]:
        """Get statistics for all creators"""
        stats = self._get("creators")
        return stats if stats else {}

    # ========== UTILITIES ==========

    def get_summary(self) -> Dict:
        """Get overall summary of scraping progress"""
        all_posts = self.get_all_posts()
        all_stats = self.get_all_creator_stats()

        total_posts = len(all_posts)
        url_collected = sum(1 for p in all_posts.values() if p.get('status', {}).get('url_collected', False))
        details_extracted = sum(1 for p in all_posts.values() if p.get('status', {}).get('details_extracted', False))
        uploaded_to_notion = sum(1 for p in all_posts.values() if p.get('status', {}).get('uploaded_to_notion', False))

        return {
            "total_posts": total_posts,
            "url_collected": url_collected,
            "details_extracted": details_extracted,
            "uploaded_to_notion": uploaded_to_notion,
            "pending_details": url_collected - details_extracted,
            "pending_upload": details_extracted - uploaded_to_notion,
            "creators": all_stats
        }

    def print_summary(self):
        """Print a formatted summary"""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("🔥 FIREBASE TRACKING SUMMARY")
        print("="*60)
        print(f"Total Posts:        {summary['total_posts']}")
        print(f"URLs Collected:     {summary['url_collected']}")
        print(f"Details Extracted:  {summary['details_extracted']}")
        print(f"Uploaded to Notion: {summary['uploaded_to_notion']}")
        print(f"\nPending Details:    {summary['pending_details']}")
        print(f"Pending Upload:     {summary['pending_upload']}")
        print("\n" + "="*60)
        print("CREATORS:")
        print("="*60)

        for creator_id, stats in summary['creators'].items():
            print(f"\n{creator_id}:")
            print(f"  Total:     {stats.get('total_posts', 0)}")
            print(f"  Processed: {stats.get('processed_posts', 0)}")
            print(f"  Pending:   {stats.get('pending_posts', 0)}")

        print("\n" + "="*60 + "\n")


def load_firebase_config() -> tuple:
    """Load Firebase configuration from credentials.json"""
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"
    with open(config_path) as f:
        config = json.load(f)

    firebase = config['firebase']
    return firebase['database_url'], firebase['database_secret']


if __name__ == "__main__":
    # Test Firebase connection
    logging.basicConfig(level=logging.INFO)

    print("🧪 Testing Firebase Connection...\n")

    database_url, database_secret = load_firebase_config()
    tracker = FirebaseTracker(database_url, database_secret)

    # Test: Get summary
    tracker.print_summary()

    print("✅ Firebase connection test complete!")
