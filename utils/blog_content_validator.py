from typing import Tuple, Union, Dict, Any
import re
from utils.logger import logger

class BlogContentValidator:
    MIN_WORDS = 800
    MAX_WORDS = 1500
    
    @staticmethod
    def count_words(text: str) -> int:
        """Count words in markdown text, excluding code blocks and metadata."""
        try:
            # Remove code blocks
            text = re.sub(r'```[\s\S]*?```', '', text)
            # Remove inline code
            text = re.sub(r'`[^`]*`', '', text)
            # Remove markdown links
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
            # Remove markdown images
            text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            # Remove hashtags and other markdown syntax
            text = re.sub(r'[#*_~]', '', text)
            
            # Split and count remaining words
            words = text.split()
            word_count = len(words)
            logger.info(f"Word count: {word_count}")
            return word_count
            
        except Exception as e:
            logger.error(f"Error counting words: {str(e)}")
            raise

    @staticmethod
    def validate_content(result: str) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """Validate blog content meets length requirements."""
        try:
            word_count = BlogContentValidator.count_words(result)
            
            if word_count < BlogContentValidator.MIN_WORDS:
                return (False, {
                    "error": f"Content is too short. Current: {word_count} words. Minimum required: {BlogContentValidator.MIN_WORDS} words.",
                    "code": "CONTENT_TOO_SHORT",
                    "context": {"word_count": word_count, "min_words": BlogContentValidator.MIN_WORDS}
                })
                
            if word_count > BlogContentValidator.MAX_WORDS:
                return (False, {
                    "error": f"Content is too long. Current: {word_count} words. Maximum allowed: {BlogContentValidator.MAX_WORDS} words.",
                    "code": "CONTENT_TOO_LONG",
                    "context": {"word_count": word_count, "max_words": BlogContentValidator.MAX_WORDS}
                })
                
            return (True, result)
            
        except Exception as e:
            logger.error(f"Error validating content: {str(e)}")
            return (False, {
                "error": f"Error validating content: {str(e)}",
                "code": "VALIDATION_ERROR"
            })