#!/usr/bin/env python3
"""
Tag Generator for Patreon Posts
Uses Gemini AI to automatically generate relevant tags from post content
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
import google.generativeai as genai
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tag_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TagGenerator:
    """Generates tags for posts using Gemini AI"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize tag generator

        Args:
            api_key: Gemini API key (optional, will try env var)
        """
        # Try to get API key
        if not api_key:
            api_key = os.environ.get('GEMINI_API_KEY')

        if not api_key:
            logger.warning("⚠️  No Gemini API key provided. Set GEMINI_API_KEY environment variable.")
            self.model = None
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("✅ Gemini AI initialized")

        # Tag categories for better organization
        self.tag_categories = {
            'topics': [],      # Main subject matter
            'formats': [],     # Type of content (tutorial, story, analysis)
            'themes': [],      # Underlying themes
            'historical': [],  # Historical periods/events (for history content)
            'astrological': [] # Astrological concepts (for astrology content)
        }

    def generate_tags_for_post(self, post: Dict) -> Dict[str, List[str]]:
        """
        Generate tags for a single post

        Args:
            post: Post dictionary with title and content

        Returns:
            Dictionary with 'patreon_tags' and 'ai_tags'
        """
        result = {
            'patreon_tags': [],
            'ai_tags': [],
            'all_tags': []
        }

        # Get Patreon native tags
        patreon_tags = post.get('patreon_tags', [])
        if patreon_tags:
            result['patreon_tags'] = patreon_tags
            logger.info(f"  ✓ Found {len(patreon_tags)} Patreon tags: {', '.join(patreon_tags[:3])}...")

        # Generate AI tags if model is available
        if not self.model:
            logger.warning("Gemini not initialized, skipping AI tags")
            result['all_tags'] = patreon_tags
            return result

        # Build prompt from post data
        title = post.get('title', '')
        content = post.get('full_content', post.get('preview_text', ''))
        creator = post.get('creator_id', '')

        # Truncate content if too long (Gemini has token limits)
        max_content_length = 3000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        prompt = self._build_prompt(title, content, creator, patreon_tags)

        try:
            logger.debug(f"Generating AI tags for: {title[:50]}...")

            response = self.model.generate_content(prompt)

            # Parse response
            ai_tags = self._parse_tags_from_response(response.text)
            result['ai_tags'] = ai_tags

            logger.info(f"  ✓ Generated {len(ai_tags)} AI tags: {', '.join(ai_tags[:3])}...")

            # Combine all tags (Patreon + AI, removing duplicates)
            all_tags = list(set(patreon_tags + ai_tags))
            result['all_tags'] = sorted(all_tags)

            return result

        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            result['all_tags'] = patreon_tags
            return result

    def _build_prompt(self, title: str, content: str, creator: str, patreon_tags: List[str] = None) -> str:
        """
        Build prompt for Gemini AI

        Args:
            title: Post title
            content: Post content
            creator: Creator ID
            patreon_tags: Existing tags from Patreon (optional)

        Returns:
            Formatted prompt string
        """
        # Customize prompt based on creator type
        domain_context = ""
        if 'history' in creator.lower():
            domain_context = "This is historical content. Focus on historical periods, events, figures, and themes."
        elif 'astro' in creator.lower():
            domain_context = "This is astrological content. Focus on astrological concepts, signs, planets, and practices."
        elif 'horoi' in creator.lower():
            domain_context = "This is horology/time-related content. Focus on clocks, watches, time concepts, and craftsmanship."

        patreon_tags_section = ""
        if patreon_tags:
            patreon_tags_section = f"""
EXISTING PATREON TAGS:
{', '.join(patreon_tags)}

NOTE: The creator already tagged this post with the above tags. You can include them if relevant, but focus on adding NEW complementary tags that provide additional context and organization value.
"""

        prompt = f"""You are a content tagging expert. Analyze the following post and generate relevant tags.

{domain_context}

POST TITLE:
{title}

POST CONTENT:
{content}
{patreon_tags_section}
INSTRUCTIONS:
1. Generate 5-10 relevant tags that describe this content
2. Tags should be:
   - Specific and descriptive
   - Useful for organizing and searching content
   - Single words or short phrases (2-3 words max)
   - Lowercase
   - No special characters (use hyphens for multi-word tags)
3. Include tags for:
   - Main topics/subjects
   - Content type (tutorial, analysis, story, guide, etc.)
   - Key concepts or themes
   - Time periods (if historical)
   - Specific elements mentioned (people, places, concepts)
4. Complement the existing Patreon tags (if any) with additional relevant tags

OUTPUT FORMAT:
Return ONLY a comma-separated list of tags, nothing else.
Example: history, world-war-2, military-strategy, analysis, europe, 1940s

TAGS:"""

        return prompt

    def _parse_tags_from_response(self, response_text: str) -> List[str]:
        """
        Parse tags from Gemini response

        Args:
            response_text: Raw response from Gemini

        Returns:
            List of cleaned tags
        """
        # Clean response
        response_text = response_text.strip()

        # Remove any markdown formatting
        response_text = response_text.replace('```', '').replace('*', '')

        # Split by comma
        tags = [tag.strip().lower() for tag in response_text.split(',')]

        # Clean each tag
        cleaned_tags = []
        for tag in tags:
            # Remove special characters except hyphens
            tag = ''.join(c for c in tag if c.isalnum() or c in ['-', ' '])
            # Replace spaces with hyphens
            tag = tag.replace(' ', '-')
            # Remove multiple hyphens
            while '--' in tag:
                tag = tag.replace('--', '-')
            # Remove leading/trailing hyphens
            tag = tag.strip('-')

            if tag and len(tag) > 2:  # Skip very short tags
                cleaned_tags.append(tag)

        return cleaned_tags

    def process_posts_json(self, json_path: str, output_path: Optional[str] = None) -> Dict:
        """
        Process all posts in a JSON file and add tags

        Args:
            json_path: Path to posts JSON file
            output_path: Path to save processed JSON (default: data/processed/)

        Returns:
            Dictionary with processing results
        """
        logger.info(f"{'='*60}")
        logger.info(f"Processing: {json_path}")
        logger.info(f"{'='*60}\n")

        # Load posts
        with open(json_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        logger.info(f"Found {len(posts)} posts to process")

        processed_posts = []
        all_tags = set()
        patreon_tags_count = 0
        ai_tags_count = 0

        for i, post in enumerate(posts, 1):
            logger.info(f"\n[{i}/{len(posts)}] {post.get('title', 'Unknown')[:60]}")

            # Generate tags
            tag_result = self.generate_tags_for_post(post)

            # Add tags to post
            post['patreon_tags'] = tag_result['patreon_tags']
            post['ai_tags'] = tag_result['ai_tags']
            post['all_tags'] = tag_result['all_tags']
            post['tags_generated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')

            processed_posts.append(post)
            all_tags.update(tag_result['all_tags'])

            if tag_result['patreon_tags']:
                patreon_tags_count += 1
            if tag_result['ai_tags']:
                ai_tags_count += 1

            # Small delay to avoid rate limiting
            time.sleep(1)

        # Determine output path
        if not output_path:
            input_path = Path(json_path)
            output_dir = Path("data/processed")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / input_path.name

        # Save processed posts
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_posts, f, indent=2, ensure_ascii=False)

        logger.info(f"\n💾 Processed posts saved: {output_path}")

        # Save tag summary
        tag_summary = {
            'total_posts': len(processed_posts),
            'posts_with_patreon_tags': patreon_tags_count,
            'posts_with_ai_tags': ai_tags_count,
            'total_unique_tags': len(all_tags),
            'all_tags': sorted(list(all_tags)),
            'tag_frequency': self._calculate_tag_frequency(processed_posts),
            'patreon_tag_frequency': self._calculate_tag_frequency(processed_posts, tag_type='patreon'),
            'ai_tag_frequency': self._calculate_tag_frequency(processed_posts, tag_type='ai')
        }

        summary_path = Path(output_path).parent / f"{Path(output_path).stem}_tag_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(tag_summary, f, indent=2, ensure_ascii=False)

        logger.info(f"📊 Tag summary saved: {summary_path}")

        return tag_summary

    def _calculate_tag_frequency(self, posts: List[Dict], tag_type: str = 'all') -> Dict[str, int]:
        """
        Calculate frequency of each tag across all posts

        Args:
            posts: List of posts with tags
            tag_type: Type of tags to count ('all', 'patreon', 'ai')

        Returns:
            Dictionary mapping tag to frequency
        """
        frequency = {}

        for post in posts:
            # Determine which tags to count
            if tag_type == 'patreon':
                tags = post.get('patreon_tags', [])
            elif tag_type == 'ai':
                tags = post.get('ai_tags', [])
            else:  # 'all'
                tags = post.get('all_tags', post.get('tags', []))

            for tag in tags:
                frequency[tag] = frequency.get(tag, 0) + 1

        # Sort by frequency
        return dict(sorted(frequency.items(), key=lambda x: x[1], reverse=True))

    def print_tag_stats(self, tag_summary: Dict):
        """
        Print tag statistics

        Args:
            tag_summary: Tag summary dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info("TAG GENERATION STATISTICS")
        logger.info(f"{'='*60}\n")

        logger.info(f"📊 Total posts processed: {tag_summary['total_posts']}")
        logger.info(f"📊 Posts with Patreon tags: {tag_summary['posts_with_patreon_tags']}")
        logger.info(f"📊 Posts with AI tags: {tag_summary['posts_with_ai_tags']}")
        logger.info(f"📊 Total unique tags (combined): {tag_summary['total_unique_tags']}")

        logger.info(f"\n🏆 Top 20 Most Common Tags (All):")
        for i, (tag, count) in enumerate(list(tag_summary['tag_frequency'].items())[:20], 1):
            logger.info(f"   {i:2d}. {tag:30s} ({count:3d} posts)")

        if tag_summary.get('patreon_tag_frequency'):
            logger.info(f"\n🔖 Top 10 Patreon Tags:")
            for i, (tag, count) in enumerate(list(tag_summary['patreon_tag_frequency'].items())[:10], 1):
                logger.info(f"   {i:2d}. {tag:30s} ({count:3d} posts)")

        if tag_summary.get('ai_tag_frequency'):
            logger.info(f"\n🤖 Top 10 AI-Generated Tags:")
            for i, (tag, count) in enumerate(list(tag_summary['ai_tag_frequency'].items())[:10], 1):
                logger.info(f"   {i:2d}. {tag:30s} ({count:3d} posts)")

        logger.info(f"\n{'='*60}\n")


def main():
    """Test tag generator"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate tags for Patreon posts using AI')
    parser.add_argument('--json', type=str, help='Path to posts JSON file')
    parser.add_argument('--all', action='store_true', help='Process all JSONs in data/raw/')
    parser.add_argument('--api-key', type=str, help='Gemini API key (or set GEMINI_API_KEY env var)')

    args = parser.parse_args()

    # Check for API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logger.error("❌ No Gemini API key provided!")
        logger.info("Set GEMINI_API_KEY environment variable or use --api-key")
        logger.info("\nGet API key from: https://makersuite.google.com/app/apikey")
        return

    generator = TagGenerator(api_key=api_key)

    if args.all:
        # Process all JSON files in data/raw/
        raw_dir = Path("data/raw")
        json_files = list(raw_dir.glob("*_posts.json"))

        if not json_files:
            logger.error("No post JSON files found in data/raw/")
            return

        logger.info(f"Found {len(json_files)} post files to process\n")

        all_summaries = []
        for json_file in json_files:
            summary = generator.process_posts_json(str(json_file))
            all_summaries.append(summary)
            generator.print_tag_stats(summary)

    elif args.json:
        summary = generator.process_posts_json(args.json)
        generator.print_tag_stats(summary)

    else:
        logger.error("Please specify --json FILE or use --all")
        return

    logger.info("✅ Tag generation complete!")


if __name__ == "__main__":
    main()
