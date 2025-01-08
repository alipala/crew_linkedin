import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from config.settings import Config
from utils.logger import logger

def format_post_data(post_data: Dict) -> Dict:
    """Format post data for storage."""
    return {
        'post_id': post_data.get('post_id'),
        'text': post_data.get('text'),
        'date': post_data.get('date'),
        'metrics': {
            'reactions': post_data.get('metrics', {}).get('reactions', 0),
            'comments': post_data.get('metrics', {}).get('comments', 0),
            'shares': post_data.get('metrics', {}).get('shares', 0)
        },
        'url': post_data.get('url'),
        'scraped_at': datetime.now().isoformat()
    }

def save_posts_to_json(posts: List[Dict], filename: Optional[str] = None) -> str:
    """Save scraped posts to JSON file, removing duplicates."""
    try:
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_posts_{timestamp}.json"

        # Ensure the output directory exists
        filepath = os.path.join(Config.OUTPUT_DIR, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Remove duplicates by using post text as unique identifier
        unique_posts = {}
        for post in posts:
            # Use post_id if available, otherwise use hash of text
            post_key = post.get('post_id') or hash(post.get('text', ''))
            unique_posts[post_key] = post

        # Convert unique posts back to list
        unique_posts_list = list(unique_posts.values())

        # Save posts with proper formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(unique_posts_list, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully saved {len(unique_posts_list)} posts to {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Error saving posts to JSON: {str(e)}")
        raise

def load_posts_from_json(filepath: str) -> List[Dict]:
    """Load posts from a JSON file."""
    try:
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return []

        with open(filepath, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        logger.info(f"Successfully loaded {len(posts)} posts from {filepath}")
        return posts

    except Exception as e:
        logger.error(f"Error loading posts from JSON: {str(e)}")
        return []