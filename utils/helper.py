import json
import os
from datetime import datetime
from config.settings import Config

def save_posts_to_json(posts, filename=None):
    """Save scraped posts to JSON file, removing duplicates."""
    unique_posts = {post.get('post_id') or hash(post['text']): post for post in posts}.values()
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_posts_{timestamp}.json"

    filepath = os.path.join(Config.OUTPUT_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(list(unique_posts), f, indent=2, ensure_ascii=False)
    return filepath


def format_post_data(post_data):
    """Format post data for storage"""
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