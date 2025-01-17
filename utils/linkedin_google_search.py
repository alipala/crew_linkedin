from typing import List, Dict, Any, Optional, Union, ClassVar
from datetime import datetime, timedelta
import re
import json
from crewai.tools import BaseTool
import requests
import time
from utils.logger import logger
from pydantic import Field, BaseModel
import os

class SearchConfig(BaseModel):
    """Configuration model for search parameters"""
    days: int = Field(default=7, description="Number of days to look back")
    max_topics: int = Field(default=5, description="Maximum number of topics to search")
    results_per_topic: int = Field(default=10, description="Number of results per topic")

class SearchInput(BaseModel):
    """Model for search input validation"""
    topics: Union[List[str], str]
    days: int = 3
    max_topics: int = 10
    results_per_topic: int = 10

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

    def _normalize_topics(self, topics_input: Union[str, List[str], Dict[str, Any]]) -> List[str]:
        """Normalize topics input into a list of strings"""
        if isinstance(topics_input, str):
            # If it's a string, split by comma or treat as single topic
            return [t.strip() for t in topics_input.split(',')] if ',' in topics_input else [topics_input.strip()]
        elif isinstance(topics_input, list):
            # If it's already a list, ensure all elements are strings
            return [str(t).strip() for t in topics_input if t]
        elif isinstance(topics_input, dict):
            # Try to extract topics from dictionary structure
            if 'topics' in topics_input:
                return self._normalize_topics(topics_input['topics'])
            elif 'task_kwargs' in topics_input and 'topics' in topics_input['task_kwargs']:
                return self._normalize_topics(topics_input['task_kwargs']['topics'])
        return []

    def _extract_topics_from_args(self, args: Any) -> List[str]:
        """Extract topics from various input formats"""
        try:
            if args is None:
                return []

            # If args is a string, try to parse it as JSON first
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    return [args.strip()]

            # Handle dictionary input
            if isinstance(args, dict):
                # Check all possible paths where topics might be stored
                possible_paths = [
                    args.get('topics'),
                    args.get('task_kwargs', {}).get('topics'),
                    args.get('task_data', {}).get('search_linkedin_posts', {}).get('topics'),
                ]
                
                for path in possible_paths:
                    if path:
                        return self._normalize_topics(path)

            # Handle list input
            if isinstance(args, list):
                return self._normalize_topics(args)

            logger.warning(f"Couldn't extract topics from args: {args}")
            return []

        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}")
            return []

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
                    'matched_topics': [topic],
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
        
        # Add regex patterns to extract metrics
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

    def _run(self, args: Any = None) -> Dict[str, Any]:
        """
        Execute LinkedIn Google search with provided arguments
        
        Args:
            args: Various formats of input containing topics and search parameters
            
        Returns:
            Dict[str, Any]: Search results and metadata
        """
        try:
            # Extract and normalize topics
            topics = self._extract_topics_from_args(args)
            
            if not topics:
                logger.warning("No topics found in input, using defaults")
                topics = self.default_topics

            logger.info(f"Searching with normalized topics: {topics}")

            # Validate credentials
            self._validate_credentials()

            # Validate input using Pydantic model
            search_input = SearchInput(
                topics=topics,
                days=args.get('days', 3) if isinstance(args, dict) else 3,
                max_topics=args.get('max_topics', 10) if isinstance(args, dict) else 10,
                results_per_topic=args.get('results_per_topic', 10) if isinstance(args, dict) else 10
            )

            # Process each topic
            all_posts = []
            successful_topics = []

            for topic in search_input.topics:
                logger.info(f"Processing topic: {topic}")
                try:
                    posts = self._search_linkedin_posts(
                        topic,
                        search_input.days,
                        search_input.results_per_topic
                    )
                    if posts:
                        all_posts.extend(posts)
                        successful_topics.append(topic)
                except Exception as e:
                    logger.error(f"Error processing topic '{topic}': {str(e)}")

            # Process results
            unique_posts = {post['url']: post for post in all_posts}.values()
            posts_list = sorted(
                list(unique_posts),
                key=lambda x: sum(x['metrics'].values()),
                reverse=True
            )

            # Save to JSON
            output_file = self._save_posts_to_json(posts_list, successful_topics)

            result = {
                'status': 'success',
                'topics_searched': len(successful_topics),
                'successful_topics': successful_topics,
                'posts_found': len(posts_list),
                'output_file': output_file,
                'posts': posts_list,
                'original_topics': topics
            }

            logger.info(f"Search completed successfully with topics: {successful_topics}")
            return result

        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'topics_attempted': topics if 'topics' in locals() else []
            }