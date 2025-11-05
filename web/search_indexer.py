#!/usr/bin/env python3
"""
Advanced Search Indexer for Patreon Content
Creates a full-text search index using SQLite FTS5
Indexes: titles, content, tags, comments, video subtitles
"""

import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Try to import webvtt for subtitle parsing
try:
    import webvtt
    WEBVTT_AVAILABLE = True
except ImportError:
    WEBVTT_AVAILABLE = False
    print("Warning: webvtt-py not installed. Subtitle indexing will be limited.")


class SearchIndexer:
    """Advanced search indexer with FTS5"""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent / "search_index.db"
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None

        # Data directories
        self.processed_dir = Path(__file__).parent.parent / "data" / "processed"
        self.media_root = Path(__file__).parent.parent / "data" / "media"

    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def create_index(self):
        """Create FTS5 full-text search index"""
        self.connect()

        # Drop existing index if it exists
        self.cursor.execute("DROP TABLE IF EXISTS posts_fts")

        # Create FTS5 virtual table with tokenizer for better fuzzy search
        self.cursor.execute("""
            CREATE VIRTUAL TABLE posts_fts USING fts5(
                post_id UNINDEXED,
                creator_id UNINDEXED,
                title,
                content,
                tags,
                comments,
                subtitles,
                published_date UNINDEXED,
                tokenize='porter unicode61'
            )
        """)

        # Create metadata table for additional info
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts_meta (
                post_id TEXT PRIMARY KEY,
                creator_id TEXT,
                creator_name TEXT,
                post_url TEXT,
                published_date TEXT,
                has_images INTEGER,
                has_videos INTEGER,
                has_audio INTEGER,
                image_count INTEGER,
                video_count INTEGER,
                audio_count INTEGER,
                comment_count INTEGER,
                like_count INTEGER,
                collections TEXT
            )
        """)

        self.conn.commit()
        print("✓ Search index created")

    def parse_vtt_subtitles(self, vtt_path):
        """Parse VTT subtitle file and extract text"""
        if not WEBVTT_AVAILABLE:
            # Fallback: simple text extraction
            try:
                with open(vtt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Remove timestamps and VTT metadata
                    lines = []
                    for line in content.split('\n'):
                        # Skip lines that look like timestamps
                        if '-->' in line or line.startswith('WEBVTT') or line.strip().isdigit():
                            continue
                        line = line.strip()
                        if line and not line.startswith('NOTE'):
                            lines.append(line)
                    return ' '.join(lines)
            except Exception as e:
                print(f"Warning: Could not parse VTT file {vtt_path}: {e}")
                return ""

        try:
            # Use webvtt library for proper parsing
            captions = webvtt.read(str(vtt_path))
            text_parts = []
            for caption in captions:
                # Clean caption text
                text = caption.text.replace('\n', ' ').strip()
                if text:
                    text_parts.append(text)
            return ' '.join(text_parts)
        except Exception as e:
            print(f"Warning: Could not parse VTT file {vtt_path}: {e}")
            return ""

    def extract_post_content(self, post):
        """Extract all searchable text from a post"""
        # Title
        title = post.get('title', '')

        # Full content from content_blocks
        content_parts = []
        content_blocks = post.get('content_blocks', [])

        for block in content_blocks:
            block_type = block.get('type', '')

            if block_type in ['paragraph', 'heading']:
                text = block.get('text', '')
                if text:
                    content_parts.append(text)

            elif block_type == 'list_item':
                text = block.get('text', '')
                if text:
                    content_parts.append(text)

        # Fallback to full_content if no blocks
        if not content_parts and post.get('full_content'):
            content_parts.append(post['full_content'])

        content = ' '.join(content_parts)

        # Tags
        tags = post.get('patreon_tags', [])
        if isinstance(tags, list):
            tags_text = ' '.join(tags)
        else:
            tags_text = str(tags)

        # Comments
        comment_parts = []
        for block in content_blocks:
            if block.get('type') == 'comment':
                comment_text = block.get('text', '')
                if comment_text:
                    comment_parts.append(comment_text)

                # Also get replies
                replies = block.get('replies', [])
                for reply in replies:
                    reply_text = reply.get('text', '')
                    if reply_text:
                        comment_parts.append(reply_text)

        comments = ' '.join(comment_parts)

        # Video subtitles
        subtitle_parts = []
        video_subtitles = post.get('video_subtitles_relative', [])

        if video_subtitles:
            for subtitle_path in video_subtitles:
                # Full path to subtitle file
                full_path = self.media_root / subtitle_path
                if full_path.exists():
                    subtitle_text = self.parse_vtt_subtitles(full_path)
                    if subtitle_text:
                        subtitle_parts.append(subtitle_text)

        subtitles = ' '.join(subtitle_parts)

        return {
            'title': title,
            'content': content,
            'tags': tags_text,
            'comments': comments,
            'subtitles': subtitles
        }

    def extract_post_metadata(self, post):
        """Extract metadata for filtering and display"""
        metadata = post.get('post_metadata', {})

        # Count media
        content_blocks = post.get('content_blocks', [])
        image_count = sum(1 for b in content_blocks if b.get('type') == 'image')
        video_count = sum(1 for b in content_blocks if b.get('type') in ['video', 'youtube_embed'])
        audio_count = sum(1 for b in content_blocks if b.get('type') == 'audio')
        comment_count = sum(1 for b in content_blocks if b.get('type') == 'comment')

        # Also check local paths
        if not video_count and post.get('video_local_paths'):
            video_count = len(post.get('video_local_paths', []))
        if not audio_count and post.get('audio_local_paths'):
            audio_count = len(post.get('audio_local_paths', []))

        # Collections
        collections = post.get('collections', [])
        collections_json = json.dumps(collections) if collections else ''

        return {
            'creator_name': metadata.get('creator_name', ''),
            'post_url': post.get('post_url', ''),
            'published_date': metadata.get('published_date', ''),
            'has_images': 1 if image_count > 0 else 0,
            'has_videos': 1 if video_count > 0 else 0,
            'has_audio': 1 if audio_count > 0 else 0,
            'image_count': image_count,
            'video_count': video_count,
            'audio_count': audio_count,
            'comment_count': comment_count,
            'like_count': post.get('like_count', 0),
            'collections': collections_json
        }

    def index_posts(self):
        """Index all posts from JSON files"""
        if not self.processed_dir.exists():
            print(f"Warning: {self.processed_dir} does not exist")
            return 0

        post_files = list(self.processed_dir.glob("*_posts_detailed.json"))

        if not post_files:
            print(f"Warning: No post files found in {self.processed_dir}")
            return 0

        total_indexed = 0

        for json_file in post_files:
            print(f"\nProcessing {json_file.name}...")

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)

                for post in posts:
                    post_id = post.get('post_id')
                    creator_id = post.get('creator_id')

                    if not post_id:
                        continue

                    # Extract searchable content
                    content_data = self.extract_post_content(post)

                    # Extract metadata
                    meta_data = self.extract_post_metadata(post)

                    # Insert into FTS5 table
                    self.cursor.execute("""
                        INSERT INTO posts_fts (post_id, creator_id, title, content, tags, comments, subtitles, published_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        post_id,
                        creator_id,
                        content_data['title'],
                        content_data['content'],
                        content_data['tags'],
                        content_data['comments'],
                        content_data['subtitles'],
                        meta_data['published_date']
                    ))

                    # Insert into metadata table
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO posts_meta
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        post_id,
                        creator_id,
                        meta_data['creator_name'],
                        meta_data['post_url'],
                        meta_data['published_date'],
                        meta_data['has_images'],
                        meta_data['has_videos'],
                        meta_data['has_audio'],
                        meta_data['image_count'],
                        meta_data['video_count'],
                        meta_data['audio_count'],
                        meta_data['comment_count'],
                        meta_data['like_count'],
                        meta_data['collections']
                    ))

                    total_indexed += 1

                    # Show progress for subtitles
                    if content_data['subtitles']:
                        print(f"  ✓ {post_id}: Indexed with subtitles ({len(content_data['subtitles'])} chars)")

                self.conn.commit()
                print(f"✓ Indexed {len(posts)} posts from {json_file.name}")

            except Exception as e:
                print(f"Error processing {json_file}: {e}")

        return total_indexed

    def search(self, query, limit=50, creator_filter=None):
        """
        Search posts with ranking

        Args:
            query: Search query string
            limit: Maximum number of results
            creator_filter: Optional creator_id to filter by

        Returns:
            List of search results with scores
        """
        if not self.conn:
            self.connect()

        # Build search query for FTS5
        # FTS5 syntax: use quotes for exact phrases, OR/AND for boolean
        # Add prefix matching with * for better fuzzy results
        search_terms = query.strip().split()
        fts_query = ' OR '.join([f'{term}*' for term in search_terms if term])

        # Base query with BM25 ranking
        sql = """
            SELECT
                f.post_id,
                f.creator_id,
                f.title,
                snippet(posts_fts, 2, '<mark>', '</mark>', '...', 30) as title_snippet,
                snippet(posts_fts, 3, '<mark>', '</mark>', '...', 30) as content_snippet,
                snippet(posts_fts, 4, '<mark>', '</mark>', '...', 30) as tags_snippet,
                snippet(posts_fts, 5, '<mark>', '</mark>', '...', 30) as comments_snippet,
                snippet(posts_fts, 6, '<mark>', '</mark>', '...', 30) as subtitles_snippet,
                bm25(posts_fts) as rank,
                m.creator_name,
                m.published_date,
                m.has_images,
                m.has_videos,
                m.has_audio,
                m.image_count,
                m.video_count,
                m.audio_count,
                m.comment_count,
                m.like_count
            FROM posts_fts f
            LEFT JOIN posts_meta m ON f.post_id = m.post_id
            WHERE posts_fts MATCH ?
        """

        params = [fts_query]

        # Add creator filter
        if creator_filter:
            sql += " AND f.creator_id = ?"
            params.append(creator_filter)

        # Order by rank (BM25 score)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        try:
            self.cursor.execute(sql, params)
            results = []

            for row in self.cursor.fetchall():
                # Determine which fields matched
                matched_in = []

                # Check if there are highlights in each field (with snippet)
                # Order matters: title, content, tags, comments, subtitles
                if '<mark>' in (row['title_snippet'] or ''):
                    matched_in.append('title')
                if '<mark>' in (row['content_snippet'] or ''):
                    matched_in.append('content')
                if '<mark>' in (row['tags_snippet'] or ''):
                    matched_in.append('tags')
                if '<mark>' in (row['comments_snippet'] or ''):
                    matched_in.append('comments')
                if '<mark>' in (row['subtitles_snippet'] or ''):
                    matched_in.append('subtitles')

                # Fallback: if no matches detected but post was returned, check manually
                if not matched_in:
                    title_lower = (row['title'] or '').lower()
                    content_snippet_lower = (row['content_snippet'] or '').lower()
                    tags_snippet_lower = (row['tags_snippet'] or '').lower()

                    for term in search_terms:
                        term_lower = term.lower().rstrip('*')  # Remove trailing *
                        if term_lower in title_lower and 'title' not in matched_in:
                            matched_in.append('title')
                        if term_lower in content_snippet_lower and 'content' not in matched_in:
                            matched_in.append('content')
                        if term_lower in tags_snippet_lower and 'tags' not in matched_in:
                            matched_in.append('tags')

                result = {
                    'post_id': row['post_id'],
                    'creator_id': row['creator_id'],
                    'creator_name': row['creator_name'],
                    'title': row['title'],
                    'rank': row['rank'],
                    'matched_in': matched_in,
                    'snippets': {
                        'title': row['title_snippet'],
                        'content': row['content_snippet'],
                        'tags': row['tags_snippet'],
                        'comments': row['comments_snippet'],
                        'subtitles': row['subtitles_snippet']
                    },
                    'published_date': row['published_date'],
                    'has_images': bool(row['has_images']),
                    'has_videos': bool(row['has_videos']),
                    'has_audio': bool(row['has_audio']),
                    'counts': {
                        'images': row['image_count'],
                        'videos': row['video_count'],
                        'audio': row['audio_count'],
                        'comments': row['comment_count'],
                        'likes': row['like_count']
                    }
                }

                results.append(result)

            return results

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def get_stats(self):
        """Get index statistics"""
        if not self.conn:
            self.connect()

        self.cursor.execute("SELECT COUNT(*) FROM posts_fts")
        total_posts = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM posts_fts WHERE subtitles != ''")
        posts_with_subtitles = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM posts_fts WHERE comments != ''")
        posts_with_comments = self.cursor.fetchone()[0]

        return {
            'total_posts': total_posts,
            'posts_with_subtitles': posts_with_subtitles,
            'posts_with_comments': posts_with_comments
        }


def main():
    """Build search index"""
    print("=" * 60)
    print("🔍 Advanced Search Indexer")
    print("=" * 60)

    indexer = SearchIndexer()

    # Create index
    print("\n1. Creating search index...")
    indexer.create_index()

    # Index all posts
    print("\n2. Indexing posts...")
    total = indexer.index_posts()

    # Show stats
    print("\n3. Index statistics:")
    stats = indexer.get_stats()
    print(f"  Total posts indexed: {stats['total_posts']}")
    print(f"  Posts with subtitles: {stats['posts_with_subtitles']}")
    print(f"  Posts with comments: {stats['posts_with_comments']}")

    # Test search
    print("\n4. Testing search...")
    results = indexer.search("astrology", limit=5)
    print(f"  Found {len(results)} results for 'astrology'")

    if results:
        print("\n  Top 3 results:")
        for i, result in enumerate(results[:3], 1):
            print(f"    {i}. {result['title'][:50]}...")
            print(f"       Matched in: {', '.join(result['matched_in'])}")
            print(f"       Score: {result['rank']:.2f}")

    indexer.close()

    print("\n" + "=" * 60)
    print("✓ Indexing complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
