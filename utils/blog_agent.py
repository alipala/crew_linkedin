from crewai.tools import BaseTool
from typing import Dict, Any, Optional
import requests
from config.settings import Config
from utils.logger import logger
from utils.blog_content_validator import BlogContentValidator
import re
from datetime import datetime

class HashNodePublisher(BaseTool):
    name: str = "HashNode Blog Publisher"
    description: str = "Creates and publishes technical blog posts on HashNode with length between 800-1000 words"

    def __init__(self):
        super().__init__()
        if not Config.HASHNODE_API_KEY or not Config.HASHNODE_PUBLICATION_ID:
            raise ValueError("HASHNODE_API_KEY and HASHNODE_PUBLICATION_ID must be configured")

    def _sanitize_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title"""
        clean_title = re.sub(r'[^a-z0-9\s-]', '', title.lower())
        slug = re.sub(r'\s+', '-', clean_title.strip())
        date_suffix = datetime.now().strftime('%Y%m%d')
        return f"{slug}-{date_suffix}"

    def _extract_content(self, args: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """Extract title and content from various input formats"""
        # Direct format
        title = args.get('title')
        content = args.get('content')

        # Through args.description
        if not title or not content:
            if 'args' in args and isinstance(args['args'], dict):
                desc = args['args'].get('description', {})
                if isinstance(desc, dict):
                    title = desc.get('title')
                    content = desc.get('content')

        # Through description directly
        if not title or not content:
            if 'description' in args and isinstance(args['description'], dict):
                desc = args['description']
                title = desc.get('title')
                content = desc.get('content')

        return title, content

    def _run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute blog post publishing with content validation"""
        try:
            # Extract title and content
            title, content = self._extract_content(args)
            
            if not title or not content:
                logger.error(f"Missing title or content. Args received: {args}")
                raise ValueError("Title and content are required")

            # Validate content length
            is_valid, validation_result = BlogContentValidator.validate_content(content)
            if not is_valid:
                error_msg = validation_result.get("error", "Content validation failed")
                logger.error(f"Content validation failed: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "validation_details": validation_result
                }

            # Prepare GraphQL mutation
            mutation = """
            mutation PublishPost($input: PublishPostInput!) { 
                publishPost(input: $input) { 
                    post { 
                        id 
                        url 
                        title 
                    } 
                } 
            }
            """

            # Prepare variables for GraphQL mutation
            variables = {
                "input": {
                    "title": title,
                    "contentMarkdown": content,
                    "publicationId": Config.HASHNODE_PUBLICATION_ID,
                    "slug": self._sanitize_slug(title)
                }
            }

            # Make request
            headers = {
                "Authorization": Config.HASHNODE_API_KEY,
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://gql.hashnode.com",
                headers=headers,
                json={
                    "query": mutation,
                    "variables": variables
                },
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if "errors" in result:
                error_msg = result["errors"][0].get("message", "Unknown error")
                logger.error(f"GraphQL Error: {error_msg}")
                raise Exception(f"GraphQL Error: {error_msg}")

            post_data = result.get("data", {}).get("publishPost", {}).get("post")
            if not post_data:
                raise Exception("No post data returned")

            # Log success with word count
            word_count = BlogContentValidator.count_words(content)
            logger.info(f"Successfully published post: {post_data['url']} with {word_count} words")
            
            return {
                "status": "success",
                "url": post_data["url"],
                "id": post_data["id"],
                "title": post_data["title"],
                "word_count": word_count
            }

        except Exception as e:
            logger.error(f"Failed to publish post: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }