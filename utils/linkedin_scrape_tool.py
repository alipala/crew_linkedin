from crewai.tools import BaseTool
from typing import Optional, Dict, Any
from agents.linkedin_scraper import LinkedInFeedScraper
from utils.logger import logger
import os
from datetime import datetime
import json
from contextlib import contextmanager

class LinkedInScrapeTool(BaseTool):
    name: str = "LinkedIn Scrape Tool"
    description: str = "Scrapes LinkedIn posts and analyzes engagement metrics for AI-related content"
    
    def __init__(self):
        super().__init__()
        self._scraper = None
    
    @contextmanager
    def _get_scraper(self):
        """Context manager for handling scraper lifecycle."""
        scraper = None
        try:
            scraper = LinkedInFeedScraper(
                email=os.getenv("LINKEDIN_EMAIL"),
                password=os.getenv("LINKEDIN_PASSWORD")
            )
            yield scraper
        finally:
            if scraper:
                try:
                    scraper.close()
                    logger.info("Scraper closed successfully.")
                except Exception as close_error:
                    logger.warning(f"Error while closing scraper: {close_error}")
    
    def _save_posts_to_json(self, posts: list) -> str:
        """Save posts to JSON file with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_posts_{timestamp}.json"
        filepath = os.path.join("data", "output", filename)
        
        os.makedirs(os.path.join("data", "output"), exist_ok=True)
        
        # Ensure file is closed after writing
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
            logger.info(f"Posts saved to {filepath}")
            f.close
            
        return filepath
    
    def _calculate_metrics(self, posts: list) -> dict:
        """Calculate engagement metrics and statistics."""
        if not posts:
            return {
                "total_posts": 0,
                "unique_topics": 0,
                "avg_reactions": 0
            }
            
        # Get unique topics
        all_topics = []
        for post in posts:
            all_topics.extend(post.get('matched_ai_topics', []))
        unique_topics = list(set(all_topics))
        
        # Calculate average reactions
        total_reactions = sum(post['metrics']['reactions'] for post in posts)
        avg_reactions = total_reactions / len(posts) if posts else 0
        
        return {
            "total_posts": len(posts),
            "unique_topics": len(unique_topics),
            "avg_reactions": avg_reactions
        }
    
    def _run(self, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute LinkedIn scraping with provided configuration."""
        try:
            with self._get_scraper() as scraper:
                max_posts = args.get('max_posts', 10) if args else 10
                posts = scraper.run(max_posts=max_posts)
                
                if not posts:
                    return {
                        "status": "error",
                        "error": "No posts were scraped"
                    }
                
                # Save posts to JSON
                filepath = self._save_posts_to_json(posts)
                
                # Get unique topics
                all_topics = []
                for post in posts:
                    all_topics.extend(post.get('matched_ai_topics', []))
                unique_topics = list(set(all_topics))
                
                return {
                    "status": "success",
                    "filepath": filepath,
                    "posts": posts,
                    "post_count": len(posts),
                    "topics": unique_topics,
                    "summary": self._calculate_metrics(posts)
                }
                
        except Exception as e:
            logger.error(f"LinkedIn scraping failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
