from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
import json
from crewai.tools import BaseTool
import requests
import time
from utils.logger import logger
from pydantic import Field
import os


class LinkedInGoogleSearchTool(BaseTool):
    name: str = "LinkedIn Google Search Tool"
    description: str = "Searches for LinkedIn posts via Google Custom Search API and extracts topic information"

    # API Configuration
    api_key: str = Field(
        default_factory=lambda: os.getenv('GOOGLE_SEARCH_API_KEY')
    )
    cx: str = Field(
        default_factory=lambda: os.getenv('GOOGLE_SEARCH_CX')
    )

    # Define ai_topics as a class attribute with Field
    ai_topics: List[str] = Field(
        default_factory=lambda: [
            'llm', 'genai', 'rag', 'agent', 'openai', 'anthropic', 'llama',
            'gpt', 'claude', 'gemini', 'vector db', 'embedding', 'semantic search',
            'autogpt', 'babyagi', 'mlops', 'ai safety', 'ai ethics', 'machine learning',
            'transformer', 'langchain'
        ]
    )

    def _search_linkedin_posts(self, topic: str, days: int = 7) -> List[Dict]:
        """Search for LinkedIn posts using Google Custom Search API"""
        try:
            base_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': f'site:linkedin.com/posts {topic}',
                'dateRestrict': f'd{days}',
                'num': 10  # Max results per request
            }

            response = requests.get(base_url, params=params)
            response.raise_for_status()
            results = response.json()

            posts = []
            for item in results.get('items', []):
                # Extract post data
                post = {
                    'url': item.get('link'),
                    'title': item.get('title', ''),
                    'text': item.get('snippet', ''),
                    'matched_ai_topics': [topic],
                    'scraped_at': datetime.now().isoformat(),
                    'metrics': {
                        'reactions': 0,  # Default metrics
                        'comments': 0,
                        'shares': 0
                    }
                }
                posts.append(post)

            return posts

        except Exception as e:
            logger.error(f"Search API error for topic {topic}: {str(e)}")
            return []

    def _save_posts_to_json(self, posts: List[Dict]) -> str:
        """Save scraped posts to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_posts_{timestamp}.json"
        
        try:
            # Ensure directory exists
            os.makedirs("data/output", exist_ok=True)
            
            with open(f"data/output/{filename}", 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            return filename
        except Exception as e:
            logger.error(f"Error saving posts to JSON: {str(e)}")
            return None

    def _run(self, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute LinkedIn post search and data collection"""
        try:
            days = args.get('days', 7) if args else 7
            max_topics = args.get('max_topics', 5) if args else 5
            
            if not self.api_key or not self.cx:
                raise ValueError("Google Custom Search API credentials not configured")

            all_posts = []
            processed_topics = 0
            
            for topic in self.ai_topics:
                if processed_topics >= max_topics:
                    break
                    
                logger.info(f"Searching for topic: {topic}")
                posts = self._search_linkedin_posts(topic, days)
                
                if posts:
                    all_posts.extend(posts)
                    processed_topics += 1
                
                # Respect API rate limits
                time.sleep(2)
            
            # Remove duplicates based on URL
            unique_posts = {post['url']: post for post in all_posts}.values()
            posts_list = list(unique_posts)
            
            # Sort by number of matched topics (if a post matches multiple search terms)
            posts_list.sort(key=lambda x: len(x.get('matched_ai_topics', [])), reverse=True)
            
            # Save to JSON
            output_file = self._save_posts_to_json(posts_list)
            
            return {
                'status': 'success',
                'topics_searched': processed_topics,
                'posts_found': len(posts_list),
                'output_file': output_file,
                'posts': posts_list
            }
            
        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }