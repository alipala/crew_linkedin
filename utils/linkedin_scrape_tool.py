from crewai.tools import BaseTool
from typing import Optional, Dict, Any
from utils.linkedin_scraper import LinkedInFeedScraper
from utils.logger import logger
import os
import json
from datetime import datetime

class LinkedInScrapeTool(BaseTool):
    name: str = "LinkedIn Scrape Tool"
    description: str = "Scrapes LinkedIn posts and analyzes engagement metrics for AI-related content"
    
    def _run(self, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute LinkedIn scraping with provided configuration"""
        scraper = None
        try:
            scraper = LinkedInFeedScraper(
                email=os.getenv("LINKEDIN_EMAIL"),
                password=os.getenv("LINKEDIN_PASSWORD")
            )
            
            max_posts = args.get('max_posts', 10) if args else 10
            posts = scraper.run(max_posts=max_posts)
            
            # Save posts to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_posts_{timestamp}.json"
            filepath = os.path.join("data", "output", filename)
            os.makedirs(os.path.join("data", "output"), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
                logger.info(f"Posts saved to {filepath}")
            
            # Calculate unique topics
            all_topics = []
            for post in posts:
                matched_topics = post.get('matched_ai_topics', [])
                all_topics.extend(matched_topics)
            unique_topics = list(set(all_topics))
            
            # Calculate average reactions
            total_reactions = 0
            if posts:
                for post in posts:
                    total_reactions += post['metrics']['reactions']
                avg_reactions = total_reactions / len(posts)
            else:
                avg_reactions = 0
            
            return {
                "status": "success",
                "filepath": filepath,
                "posts": posts,
                "post_count": len(posts),
                "topics": unique_topics,
                "summary": {
                    "total_posts": len(posts),
                    "unique_topics": len(unique_topics),
                    "avg_reactions": avg_reactions
                }
            }
            
        except Exception as e:
            logger.error(f"LinkedIn scraping failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            if scraper:
                scraper.close()