from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
import json
from crewai.tools import BaseTool
import requests
import time
from utils.logger import logger
from pydantic import Field, BaseModel
import os
from typing import ClassVar


class SearchConfig(BaseModel):
    """Configuration model for search parameters"""
    days: int = Field(default=7, description="Number of days to look back")
    max_topics: int = Field(default=5, description="Maximum number of topics to search")
    results_per_topic: int = Field(default=10, description="Number of results per topic")


class LinkedInGoogleSearchTool(BaseTool):
    """Tool for searching LinkedIn posts using Google Custom Search API"""
    
    name: str = "LinkedIn Google Search Tool"
    description: str = "Searches for LinkedIn posts via Google Custom Search API and extracts topic information"

    # API Configuration
    api_key: str = Field(
        default_factory=lambda: os.getenv('GOOGLE_SEARCH_API_KEY'),
        description="Google Custom Search API key"
    )
    cx: str = Field(
        default_factory=lambda: os.getenv('GOOGLE_SEARCH_CX'),
        description="Google Custom Search Engine ID"
    )

    # Default topics as fallback
    default_topics: ClassVar[List[str]] = [
        'llm', 'genai', 'rag', 'agent', 'openai', 'anthropic', 'llama',
        'gpt', 'claude', 'gemini', 'vector db', 'embedding', 'semantic search',
        'autogpt', 'babyagi', 'mlops', 'ai safety', 'ai ethics', 'machine learning',
        'transformer', 'langchain'
    ]

    def _validate_credentials(self) -> None:
        """Validate API credentials are present"""
        if not self.api_key:
            raise ValueError("Google Search API key not configured")
        if not self.cx:
            raise ValueError("Google Custom Search Engine ID not configured")

    def _search_linkedin_posts(self, topic: str, days: int, max_results: int = 10) -> List[Dict]:
        """
        Search for LinkedIn posts using Google Custom Search API
        
        Args:
            topic (str): Topic to search for
            days (int): Number of days to look back
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of posts found
        """
        try:
            base_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': f'site:linkedin.com/posts/ {topic}',
                'dateRestrict': f'd{days}',
                'num': min(max_results, 10)  # API limit is 10
            }

            response = requests.get(base_url, params=params, timeout=10)
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
                    'metrics': self._extract_metrics(item.get('snippet', '')),
                    'date': self._extract_date(item.get('snippet', ''))
                }
                posts.append(post)

            return posts

        except requests.RequestException as e:
            logger.error(f"Search API error for topic {topic}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search for topic {topic}: {str(e)}")
            return []

    def _extract_metrics(self, text: str) -> Dict[str, int]:
        """
        Extract engagement metrics from post text if available
        
        Args:
            text (str): Post text/snippet
            
        Returns:
            Dict[str, int]: Dictionary containing engagement metrics
        """
        metrics = {
            'reactions': 0,
            'comments': 0,
            'shares': 0
        }
        
        # Add regex patterns to extract metrics if they appear in the text
        patterns = {
            'reactions': r'(\d+)\s*(?:reaction|reactions|like|likes)',
            'comments': r'(\d+)\s*(?:comment|comments)',
            'shares': r'(\d+)\s*(?:share|shares|repost|reposts)'
        }
        
        for metric, pattern in patterns.items():
            if match := re.search(pattern, text, re.IGNORECASE):
                metrics[metric] = int(match.group(1))
                
        return metrics

    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extract post date from text if available
        
        Args:
            text (str): Post text/snippet
            
        Returns:
            Optional[str]: ISO format date string if found, None otherwise
        """
        try:
            # Add patterns for different date formats
            date_patterns = [
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
            
            for pattern in date_patterns:
                if match := re.search(pattern, text, re.IGNORECASE):
                    date_str = match.group(1)
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    return date.isoformat()
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting date: {str(e)}")
            return None

    def _save_posts_to_json(self, posts: List[Dict], topics: List[str]) -> Optional[str]:
        """
        Save scraped posts to JSON file
        
        Args:
            posts (List[Dict]): List of posts to save
            topics (List[str]): List of topics searched
            
        Returns:
            Optional[str]: Filename where posts were saved, or None if error
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_posts_{timestamp}.json"
            
            # Create output structure with metadata
            output_data = {
                'metadata': {
                    'timestamp': timestamp,
                    'topics_searched': topics,
                    'total_posts': len(posts)
                },
                'posts': posts
            }
            
            # Ensure directory exists
            os.makedirs("data/output", exist_ok=True)
            
            with open(f"data/output/{filename}", 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
                
            return filename
            
        except Exception as e:
            logger.error(f"Error saving posts to JSON: {str(e)}")
            return None

    def _run(self, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute LinkedIn Google search with provided arguments
        
        Args:
            args: Optional dictionary containing arguments including topics
            
        Returns:
            Dict[str, Any]: Search results and metadata
        """
        try:
            # Debug logging
            logger.debug(f"Received args: {args}")
            logger.debug(f"Args type: {type(args)}")
            
            # Validate credentials first
            self._validate_credentials()
            
            # Initialize search configuration
            config = SearchConfig(
                days=args.get('days', 3),
                max_topics=args.get('max_topics', 10),
                results_per_topic=args.get('results_per_topic', 10)
            )
            
            # Extract topics with better error handling
            topics = []
            if isinstance(args, dict):
                # Try different ways to get topics
                if 'topics' in args:
                    topics = args['topics']
                elif 'task_kwargs' in args and isinstance(args['task_kwargs'], dict):
                    topics = args['task_kwargs'].get('topics', [])
                elif 'task_data' in args and isinstance(args['task_data'], dict):
                    topics = args['task_data'].get('search_linkedin_posts', {}).get('topics', [])
                
                # Convert string to list if necessary
                if isinstance(topics, str):
                    topics = [t.strip() for t in topics.split(',')]
                elif not isinstance(topics, list):
                    topics = []
            
            # Ensure topics is a list and clean
            topics = [t for t in topics if isinstance(t, str) and t.strip()]
            
            if not topics:
                logger.warning("No valid topics found in arguments, using default topics")
                topics = self.default_topics
            else:
                logger.info(f"Using provided topics: {topics}")
                
            all_posts = []
            processed_topics = 0
            successful_topics = []
            
            # Execute search for each topic
            for topic in topics:
                if processed_topics >= config.max_topics:
                    break
                    
                logger.info(f"Searching for topic: {topic}")
                posts = self._search_linkedin_posts(
                    topic,
                    config.days,
                    config.results_per_topic
                )
                
                if posts:
                    all_posts.extend(posts)
                    successful_topics.append(topic)
                    processed_topics += 1
                else:
                    logger.warning(f"No posts found for topic: {topic}")
                
                # Respect API rate limits
                time.sleep(2)
            
            # Remove duplicates based on URL
            unique_posts = {post['url']: post for post in all_posts}.values()
            posts_list = list(unique_posts)
            
            # Sort by engagement (total of reactions, comments, and shares)
            posts_list.sort(
                key=lambda x: sum(x['metrics'].values()),
                reverse=True
            )
            
            # Save to JSON
            output_file = self._save_posts_to_json(posts_list, successful_topics)
            
            result = {
                'status': 'success',
                'topics_searched': processed_topics,
                'successful_topics': successful_topics,
                'posts_found': len(posts_list),
                'output_file': output_file,
                'posts': posts_list,
                'config': config.dict(),
                'topics_used': topics
            }
            
            logger.info(f"Search completed successfully with topics: {topics}")
            return result
            
        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'topics_attempted': topics if 'topics' in locals() else []
            }