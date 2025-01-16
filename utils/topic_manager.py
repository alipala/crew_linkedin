from typing import List, Optional, Tuple
from datetime import datetime
import json
import os
from utils.logger import logger

class TopicManager:
    def __init__(self, storage_path: str = "data/topics"):
        self.storage_path = storage_path
        self.topics_file = os.path.join(storage_path, "current_topics.json")
        self.default_topics = [
            "LLM (Large Language Models)",
            "Generative AI applications in healthcare",
            "Retrieval-Augmented Generation (RAG) techniques"
        ]
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Ensure storage directory and files exist"""
        try:
            # Create storage directory if it doesn't exist
            os.makedirs(self.storage_path, exist_ok=True)
            
            # Create topics file with default data if it doesn't exist
            if not os.path.exists(self.topics_file):
                self.save_topics(self.default_topics, cleared=False)
                
            logger.info(f"Storage initialized at {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Error ensuring storage exists: {e}")
            raise

    def load_topics(self) -> List[str]:
        """Load current topics from storage"""
        try:
            with open(self.topics_file, 'r') as f:
                data = json.load(f)
                # Check if topics were explicitly cleared
                if data.get('cleared', False):
                    return []
                return data.get('topics', self.default_topics)
        except Exception as e:
            logger.error(f"Error loading topics: {e}")
            return self.default_topics

    def save_topics(self, topics: List[str], cleared: bool = False) -> bool:
        """Save topics to storage with cleared state"""
        try:
            data = {
                'topics': topics,
                'cleared': cleared,  # Add cleared state
                'last_updated': datetime.now().isoformat(),
                'total_topics': len(topics)
            }
            with open(self.topics_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully saved {len(topics)} topics")
            return True
        except Exception as e:
            logger.error(f"Error saving topics: {e}")
            return False

    def clear_topics(self) -> bool:
        """Reset topics to empty list"""
        try:
            # Save empty list with cleared flag
            success = self.save_topics([], cleared=True)
            if success:
                logger.info("Topics cleared successfully")
            return success
        except Exception as e:
            logger.error(f"Error clearing topics: {e}")
            return False

    def get_current_topics(self) -> List[str]:
        """Get current topics list"""
        topics = self.load_topics()
        if isinstance(topics, dict) and 'topics' in topics:
            # If we got the full JSON structure, return just the topics list
            return topics['topics']
        return topics  # Otherwise return what we got

    def _is_cleared(self) -> bool:
        """Check if topics were explicitly cleared"""
        try:
            with open(self.topics_file, 'r') as f:
                data = json.load(f)
                return data.get('cleared', False)
        except Exception:
            return False

    def add_topics(self, new_topics: str) -> Tuple[bool, List[str]]:
        """Add new topics and remove cleared state"""
        try:
            # Split and clean new topics
            topics_to_add = [
                topic.strip() 
                for topic in new_topics.split(',')
                if topic.strip()
            ]
            
            # Get current topics (excluding defaults if cleared)
            current_topics = self.load_topics()
            
            # Create new list with unique topics
            updated_topics = list(dict.fromkeys(topics_to_add + current_topics))
            
            # Save with cleared=False since we're adding new topics
            if self.save_topics(updated_topics, cleared=False):
                logger.info(f"Successfully added {len(topics_to_add)} new topics")
                return True, updated_topics
            return False, current_topics
            
        except Exception as e:
            logger.error(f"Error adding topics: {e}")
            return False, self.load_topics()