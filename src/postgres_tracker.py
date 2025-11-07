#!/usr/bin/env python3
"""
PostgreSQL Database Integration
Tracks post processing state in PostgreSQL (replaces FirebaseTracker)
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)


class PostgresTracker:
    """Track post processing state in PostgreSQL"""

    def __init__(self, db_url: str = None):
        """
        Initialize Postgres tracker

        Args:
            db_url: PostgreSQL connection URL (or read from env)
        """
        if db_url is None:
            db_url = self._build_db_url_from_env()

        try:
            self.engine = create_engine(db_url, pool_pre_ping=True)
            self.Session = sessionmaker(bind=self.engine)
            logger.info(f"🐘 PostgreSQL Tracker initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgresTracker: {e}")
            raise

    def _build_db_url_from_env(self) -> str:
        """Build database URL from environment variables"""
        db_user = os.getenv('DB_USER', 'patreon_user')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST', '127.0.0.1')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'alejandria')

        if not db_password:
            raise ValueError("DB_PASSWORD not found in environment")

        # URL encode password
        encoded_password = quote_plus(db_password)
        return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

    def _resolve_source_id(self, creator_identifier: str, platform: str = 'patreon') -> Optional[int]:
        """
        Resolve creator identifier to source_id

        Args:
            creator_identifier: Could be creator name OR platform_id
            platform: Platform name (default: 'patreon')

        Returns:
            source_id from creator_sources table, or None if not found
        """
        session = self.Session()
        try:
            # Try to find by platform_id first (exact match)
            result = session.execute(text("""
                SELECT cs.id
                FROM creator_sources cs
                WHERE cs.platform = :platform
                  AND cs.platform_id = :identifier
            """), {"platform": platform, "identifier": creator_identifier})

            row = result.fetchone()
            if row:
                return row[0]

            # Try to find by creator name (fallback)
            result = session.execute(text("""
                SELECT cs.id
                FROM creator_sources cs
                JOIN creators c ON c.id = cs.creator_id
                WHERE c.name = :name
                  AND cs.platform = :platform
            """), {"name": creator_identifier, "platform": platform})

            row = result.fetchone()
            return row[0] if row else None

        except Exception as e:
            logger.error(f"Error resolving source_id for {creator_identifier}: {e}")
            return None
        finally:
            session.close()

    # ========== POST TRACKING ==========

    def create_post_record(self, post_id: str, creator_id: str, post_url: str) -> bool:
        """
        Create initial post record in PostgreSQL

        Args:
            post_id: Platform post ID (e.g., Patreon post ID)
            creator_id: Creator identifier (will be resolved to source_id)
            post_url: URL to the post

        Returns:
            True if successful
        """
        # Resolve creator_id to source_id
        source_id = self._resolve_source_id(creator_id)
        if not source_id:
            logger.error(f"Could not resolve creator '{creator_id}' to a source_id")
            return False

        session = self.Session()
        try:
            # Check if record already exists
            result = session.execute(text("""
                SELECT id FROM scraping_status
                WHERE source_id = :source_id AND post_id = :post_id
            """), {"source_id": source_id, "post_id": post_id})

            if result.fetchone():
                logger.debug(f"  Post {post_id} already exists in database")
                return True

            # Insert new record
            session.execute(text("""
                INSERT INTO scraping_status (
                    post_id, source_id, post_url,
                    phase1_status, phase1_completed_at,
                    phase2_status,
                    created_at, updated_at
                ) VALUES (
                    :post_id, :source_id, :post_url,
                    'completed', NOW(),
                    'pending',
                    NOW(), NOW()
                )
            """), {
                "post_id": post_id,
                "source_id": source_id,
                "post_url": post_url
            })

            session.commit()
            logger.info(f"  ✓ Created PostgreSQL record for post {post_id}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating post record: {e}")
            return False
        finally:
            session.close()

    def mark_url_collected(self, post_id: str) -> bool:
        """
        Mark post URL as collected (phase1 completed)

        Args:
            post_id: Platform post ID

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            result = session.execute(text("""
                UPDATE scraping_status
                SET phase1_status = 'completed',
                    phase1_completed_at = NOW(),
                    updated_at = NOW()
                WHERE post_id = :post_id
            """), {"post_id": post_id})

            session.commit()
            return result.rowcount > 0

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error marking URL collected: {e}")
            return False
        finally:
            session.close()

    def mark_details_extracted(self, post_id: str, success: bool = True, error: str = None) -> bool:
        """
        Mark post details as extracted (phase2 completed/failed)

        Args:
            post_id: Platform post ID
            success: Whether extraction was successful
            error: Error message if failed

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            status = 'completed' if success else 'failed'

            session.execute(text("""
                UPDATE scraping_status
                SET phase2_status = :status,
                    phase2_completed_at = :completed_at,
                    phase2_last_error = :error,
                    updated_at = NOW()
                WHERE post_id = :post_id
            """), {
                "post_id": post_id,
                "status": status,
                "completed_at": datetime.now() if success else None,
                "error": error
            })

            session.commit()

            if success:
                logger.info(f"  ✓ Marked post {post_id} details as extracted")
            else:
                logger.warning(f"  ⚠ Marked post {post_id} details as failed: {error}")

            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error marking details extracted: {e}")
            return False
        finally:
            session.close()

    def mark_uploaded_to_notion(self, post_id: str, notion_page_id: str = None) -> bool:
        """
        Mark post as uploaded to Notion (phase3 completed)

        Args:
            post_id: Platform post ID
            notion_page_id: Notion page ID (optional, stored in metadata)

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            session.execute(text("""
                UPDATE scraping_status
                SET phase3_status = 'completed',
                    phase3_completed_at = NOW(),
                    updated_at = NOW()
                WHERE post_id = :post_id
            """), {"post_id": post_id})

            session.commit()
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error marking uploaded to Notion: {e}")
            return False
        finally:
            session.close()

    def increment_attempt(self, post_id: str, phase: int = 2) -> bool:
        """
        Increment attempt count for a post

        Args:
            post_id: Platform post ID
            phase: Which phase to increment (1, 2, or 3)

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            phase_field = f"phase{phase}_attempts"

            session.execute(text(f"""
                UPDATE scraping_status
                SET {phase_field} = {phase_field} + 1,
                    updated_at = NOW()
                WHERE post_id = :post_id
            """), {"post_id": post_id})

            session.commit()
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error incrementing attempt: {e}")
            return False
        finally:
            session.close()

    def get_post(self, post_id: str) -> Optional[Dict]:
        """
        Get post record from PostgreSQL

        Args:
            post_id: Platform post ID

        Returns:
            Dict with post data, or None if not found
        """
        session = self.Session()
        try:
            result = session.execute(text("""
                SELECT
                    ss.post_id,
                    ss.post_url,
                    c.name as creator_name,
                    cs.platform,
                    cs.platform_id,
                    ss.phase1_status,
                    ss.phase1_completed_at,
                    ss.phase2_status,
                    ss.phase2_completed_at,
                    ss.phase3_status,
                    ss.phase3_completed_at,
                    ss.phase2_attempts,
                    ss.phase2_last_error,
                    ss.created_at,
                    ss.updated_at
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                JOIN creators c ON c.id = cs.creator_id
                WHERE ss.post_id = :post_id
            """), {"post_id": post_id})

            row = result.fetchone()
            if not row:
                return None

            # Map to Firebase-compatible format for backwards compatibility
            return {
                "post_id": row[0],
                "post_url": row[1],
                "creator_id": row[4],  # platform_id for compatibility
                "creator_name": row[2],
                "platform": row[3],
                "status": {
                    "url_collected": row[5] == 'completed',
                    "url_collected_at": row[6].isoformat() if row[6] else None,
                    "details_extracted": row[7] == 'completed',
                    "details_extracted_at": row[8].isoformat() if row[8] else None,
                    "uploaded_to_notion": row[9] == 'completed',
                    "uploaded_to_notion_at": row[10].isoformat() if row[10] else None,
                    "attempt_count": row[11] or 0,
                    "last_attempt": row[14].isoformat() if row[14] else None,
                    "errors": [row[12]] if row[12] else []
                },
                "created_at": row[13].isoformat() if row[13] else None,
                "updated_at": row[14].isoformat() if row[14] else None
            }

        except Exception as e:
            logger.error(f"Error getting post: {e}")
            return None
        finally:
            session.close()

    def post_exists(self, post_id: str) -> bool:
        """
        Check if post exists in PostgreSQL

        Args:
            post_id: Platform post ID

        Returns:
            True if post exists
        """
        return self.get_post(post_id) is not None

    def get_all_posts(self) -> Dict[str, Dict]:
        """
        Get all posts from PostgreSQL

        Returns:
            Dict of posts keyed by post_id
        """
        session = self.Session()
        try:
            result = session.execute(text("""
                SELECT
                    ss.post_id,
                    ss.post_url,
                    cs.platform_id as creator_id,
                    c.name as creator_name,
                    cs.platform,
                    ss.phase1_status,
                    ss.phase2_status,
                    ss.phase3_status
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                JOIN creators c ON c.id = cs.creator_id
                ORDER BY ss.created_at DESC
            """))

            posts = {}
            for row in result.fetchall():
                posts[row[0]] = {
                    "post_id": row[0],
                    "post_url": row[1],
                    "creator_id": row[2],
                    "creator_name": row[3],
                    "platform": row[4],
                    "status": {
                        "url_collected": row[5] == 'completed',
                        "details_extracted": row[6] == 'completed',
                        "uploaded_to_notion": row[7] == 'completed'
                    }
                }

            return posts

        except Exception as e:
            logger.error(f"Error getting all posts: {e}")
            return {}
        finally:
            session.close()

    def get_posts_by_creator(self, creator_id: str) -> List[Dict]:
        """
        Get all posts for a specific creator

        Args:
            creator_id: Creator identifier (platform_id or name)

        Returns:
            List of post dicts
        """
        all_posts = self.get_all_posts()
        return [
            post for post in all_posts.values()
            if post.get('creator_id') == creator_id or post.get('creator_name') == creator_id
        ]

    def get_posts_needing_details(self, creator_id: str = None) -> List[Dict]:
        """
        Get posts that need details extraction (phase2 pending)

        Args:
            creator_id: Optional filter by creator

        Returns:
            List of posts with URL collected but details not extracted
        """
        session = self.Session()
        try:
            query = """
                SELECT
                    ss.post_id,
                    ss.post_url,
                    cs.platform_id as creator_id,
                    c.name as creator_name,
                    cs.platform,
                    ss.phase2_attempts
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                JOIN creators c ON c.id = cs.creator_id
                WHERE ss.phase1_status = 'completed'
                  AND ss.phase2_status = 'pending'
            """

            params = {}
            if creator_id:
                query += " AND (cs.platform_id = :creator_id OR c.name = :creator_id)"
                params["creator_id"] = creator_id

            query += " ORDER BY ss.created_at ASC"

            result = session.execute(text(query), params)

            posts = []
            for row in result.fetchall():
                posts.append({
                    "post_id": row[0],
                    "post_url": row[1],
                    "creator_id": row[2],
                    "creator_name": row[3],
                    "platform": row[4],
                    "status": {
                        "url_collected": True,
                        "details_extracted": False,
                        "attempt_count": row[5] or 0
                    }
                })

            return posts

        except Exception as e:
            logger.error(f"Error getting posts needing details: {e}")
            return []
        finally:
            session.close()

    def get_posts_needing_notion_upload(self, creator_id: str = None) -> List[Dict]:
        """
        Get posts that need to be uploaded to Notion (phase3 pending)

        Args:
            creator_id: Optional filter by creator

        Returns:
            List of posts with details extracted but not uploaded
        """
        session = self.Session()
        try:
            query = """
                SELECT
                    ss.post_id,
                    ss.post_url,
                    cs.platform_id as creator_id,
                    c.name as creator_name,
                    cs.platform
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                JOIN creators c ON c.id = cs.creator_id
                WHERE ss.phase2_status = 'completed'
                  AND ss.phase3_status = 'pending'
            """

            params = {}
            if creator_id:
                query += " AND (cs.platform_id = :creator_id OR c.name = :creator_id)"
                params["creator_id"] = creator_id

            query += " ORDER BY ss.created_at ASC"

            result = session.execute(text(query), params)

            posts = []
            for row in result.fetchall():
                posts.append({
                    "post_id": row[0],
                    "post_url": row[1],
                    "creator_id": row[2],
                    "creator_name": row[3],
                    "platform": row[4],
                    "status": {
                        "details_extracted": True,
                        "uploaded_to_notion": False
                    }
                })

            return posts

        except Exception as e:
            logger.error(f"Error getting posts needing Notion upload: {e}")
            return []
        finally:
            session.close()

    # ========== CREATOR STATS ==========

    def update_creator_stats(self, creator_id: str) -> bool:
        """
        Update statistics for a creator
        Note: In PostgreSQL, stats are computed on-the-fly from scraping_status

        Args:
            creator_id: Creator identifier

        Returns:
            True if successful (always, since no update needed)
        """
        # Stats are computed dynamically in get_creator_stats()
        # No need to maintain a separate stats table
        logger.debug(f"Stats for {creator_id} are computed dynamically")
        return True

    def get_creator_stats(self, creator_id: str) -> Optional[Dict]:
        """
        Get statistics for a creator

        Args:
            creator_id: Creator identifier

        Returns:
            Dict with creator stats
        """
        session = self.Session()
        try:
            result = session.execute(text("""
                SELECT
                    c.name as creator_name,
                    cs.platform,
                    COUNT(*) as total_posts,
                    SUM(CASE WHEN ss.phase2_status = 'completed' THEN 1 ELSE 0 END) as processed_posts,
                    SUM(CASE WHEN ss.phase2_status = 'pending' THEN 1 ELSE 0 END) as pending_posts,
                    MAX(ss.updated_at) as last_scrape
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                JOIN creators c ON c.id = cs.creator_id
                WHERE cs.platform_id = :creator_id OR c.name = :creator_id
                GROUP BY c.name, cs.platform
            """), {"creator_id": creator_id})

            row = result.fetchone()
            if not row:
                return None

            return {
                "creator_id": creator_id,
                "creator_name": row[0],
                "platform": row[1],
                "total_posts": row[2],
                "processed_posts": row[3],
                "pending_posts": row[4],
                "last_scrape": row[5].isoformat() if row[5] else None,
                "updated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting creator stats: {e}")
            return None
        finally:
            session.close()

    def get_all_creator_stats(self) -> Dict[str, Dict]:
        """
        Get statistics for all creators

        Returns:
            Dict of stats keyed by creator_id
        """
        session = self.Session()
        try:
            result = session.execute(text("""
                SELECT
                    cs.platform_id as creator_id,
                    c.name as creator_name,
                    cs.platform,
                    COUNT(*) as total_posts,
                    SUM(CASE WHEN ss.phase2_status = 'completed' THEN 1 ELSE 0 END) as processed_posts,
                    SUM(CASE WHEN ss.phase2_status = 'pending' THEN 1 ELSE 0 END) as pending_posts,
                    MAX(ss.updated_at) as last_scrape
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                JOIN creators c ON c.id = cs.creator_id
                GROUP BY cs.platform_id, c.name, cs.platform
                ORDER BY c.name
            """))

            stats = {}
            for row in result.fetchall():
                stats[row[0]] = {
                    "creator_id": row[0],
                    "creator_name": row[1],
                    "platform": row[2],
                    "total_posts": row[3],
                    "processed_posts": row[4],
                    "pending_posts": row[5],
                    "last_scrape": row[6].isoformat() if row[6] else None
                }

            return stats

        except Exception as e:
            logger.error(f"Error getting all creator stats: {e}")
            return {}
        finally:
            session.close()

    # ========== UTILITIES ==========

    def get_summary(self) -> Dict:
        """
        Get overall summary of scraping progress

        Returns:
            Dict with summary statistics
        """
        session = self.Session()
        try:
            result = session.execute(text("""
                SELECT
                    COUNT(*) as total_posts,
                    SUM(CASE WHEN phase1_status = 'completed' THEN 1 ELSE 0 END) as url_collected,
                    SUM(CASE WHEN phase2_status = 'completed' THEN 1 ELSE 0 END) as details_extracted,
                    SUM(CASE WHEN phase3_status = 'completed' THEN 1 ELSE 0 END) as uploaded_to_notion
                FROM scraping_status
            """))

            row = result.fetchone()

            total_posts = row[0] or 0
            url_collected = row[1] or 0
            details_extracted = row[2] or 0
            uploaded_to_notion = row[3] or 0

            return {
                "total_posts": total_posts,
                "url_collected": url_collected,
                "details_extracted": details_extracted,
                "uploaded_to_notion": uploaded_to_notion,
                "pending_details": url_collected - details_extracted,
                "pending_upload": details_extracted - uploaded_to_notion,
                "creators": self.get_all_creator_stats()
            }

        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return {
                "total_posts": 0,
                "url_collected": 0,
                "details_extracted": 0,
                "uploaded_to_notion": 0,
                "pending_details": 0,
                "pending_upload": 0,
                "creators": {}
            }
        finally:
            session.close()

    def print_summary(self):
        """Print a formatted summary"""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("🐘 POSTGRESQL TRACKING SUMMARY")
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
            print(f"\n{stats['creator_name']} ({stats['platform']}):")
            print(f"  Total:     {stats.get('total_posts', 0)}")
            print(f"  Processed: {stats.get('processed_posts', 0)}")
            print(f"  Pending:   {stats.get('pending_posts', 0)}")

        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    # Test PostgreSQL connection
    logging.basicConfig(level=logging.INFO)

    print("🧪 Testing PostgreSQL Connection...\n")

    tracker = PostgresTracker()

    # Test: Get summary
    tracker.print_summary()

    print("✅ PostgreSQL connection test complete!")
