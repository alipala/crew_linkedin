from typing import Dict, Any
import requests
import time
from config.settings import Config
from utils.logger import logger

class ShareAgent:
    """Agent responsible for sharing content on LinkedIn"""
    
    def __init__(self):
        self.access_token = Config.LINKEDIN_ACCESS_TOKEN
        self.person_id = Config.LINKEDIN_PERSON_ID
        self.max_retries = 3
        self.base_delay = 1  # Base delay in seconds
        
    def _make_request(self, headers: Dict[str, str], data: Dict[str, Any], retry: int = 0) -> Dict[str, Any]:
        """Make request to LinkedIn API with retry logic"""
        try:
            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "response": response.json()}
            
        except requests.exceptions.RequestException as e:
            if retry < self.max_retries:
                delay = self.base_delay * (2 ** retry)  # Exponential backoff
                logger.warning(f"Request failed, retrying in {delay} seconds... Error: {str(e)}")
                time.sleep(delay)
                return self._make_request(headers, data, retry + 1)
            else:
                logger.error(f"Max retries reached. Error: {str(e)}")
                return {"success": False, "error": str(e)}
    
    def share_post(self, content: str) -> Dict[str, Any]:
        """Share content on LinkedIn"""
        try:
            if not self.access_token or not self.person_id:
                raise ValueError("LinkedIn credentials not configured")
                
            if not content or not content.strip():
                raise ValueError("Empty content provided")
                
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            data = {
                "author": f"urn:li:person:{self.person_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "CONNECTIONS"
                }
            }
            
            logger.info("Attempting to share post on LinkedIn")
            result = self._make_request(headers, data)
            
            if result["success"]:
                logger.info("Successfully shared post on LinkedIn")
                return result
            else:
                logger.error(f"Failed to share post: {result.get('error')}")
                return result
                
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return {"success": False, "error": str(e)}
            
        except Exception as e:
            logger.error(f"Unexpected error sharing to LinkedIn: {str(e)}")
            return {"success": False, "error": str(e)}