# utils/topic_manager.py

from typing import List, Optional, Tuple
from datetime import datetime
import json
import os
from utils.logger import logger

class TopicManager:
    """Manages AI topics for the LinkedIn post search"""
    
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
        os.makedirs(self.storage_path, exist_ok=True)
        if not os.path.exists(self.topics_file):
            self.save_topics(self.default_topics)
            
    def load_topics(self) -> List[str]:
        """Load current topics from storage"""
        try:
            with open(self.topics_file, 'r') as f:
                data = json.load(f)
                return data.get('topics', self.default_topics)
        except Exception as e:
            logger.error(f"Error loading topics: {e}")
            return self.default_topics
            
    def save_topics(self, topics: List[str]) -> bool:
        """Save topics to storage with timestamp"""
        try:
            data = {
                'topics': topics,
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
            
    def add_topics(self, new_topics: str) -> Tuple[bool, List[str]]:
        """
        Add new topics from a comma-separated string
        Returns: (success, current_topics)
        """
        try:
            # Split and clean new topics
            topics_to_add = [
                topic.strip() 
                for topic in new_topics.split(',')
                if topic.strip()
            ]
            
            # Load current topics
            current_topics = self.load_topics()
            
            # Add new topics (avoid duplicates)
            updated_topics = list(set(current_topics + topics_to_add))
            
            # Save updated topics
            if self.save_topics(updated_topics):
                logger.info(f"Successfully added {len(topics_to_add)} new topics")
                return True, updated_topics
            return False, current_topics
            
        except Exception as e:
            logger.error(f"Error adding topics: {e}")
            return False, self.load_topics()
            
    def clear_topics(self) -> bool:
        """Reset topics to defaults"""
        logger.info("Resetting topics to defaults")
        return self.save_topics(self.default_topics)
        
    def get_current_topics(self) -> List[str]:
        """Get current topics list"""
        return self.load_topics()

    def get_topic_history(self) -> dict:
        """Get topic update history if file exists"""
        try:
            with open(self.topics_file, 'r') as f:
                data = json.load(f)
                return {
                    'last_updated': data.get('last_updated'),
                    'total_topics': data.get('total_topics'),
                    'topics': data.get('topics', [])
                }
        except Exception as e:
            logger.error(f"Error getting topic history: {e}")
            return {
                'last_updated': None,
                'total_topics': len(self.default_topics),
                'topics': self.default_topics
            }