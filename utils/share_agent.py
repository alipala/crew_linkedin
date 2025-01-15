# utils/share_agent.py

from typing import Dict, Any, Optional, Union
import requests
import time
import json
from datetime import datetime
from crewai.tools import BaseTool
from pydantic import Field, BaseModel
from config.settings import Config
from utils.logger import logger
import re

class ShareRequest(BaseModel):
    """Model for LinkedIn share request data"""
    content: str
    visibility: str = "connections"

class ShareResponse(BaseModel):
    """Model for LinkedIn share response data"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    post_data: Optional[Dict[str, Any]] = None

class ShareAgent(BaseTool):
    """
    Agent responsible for sharing content on LinkedIn.
    Extends BaseTool to integrate with CrewAI framework.
    """
    
    name: str = "LinkedIn Share Tool"
    description: str = "Shares content on LinkedIn using the LinkedIn API with proper formatting and error handling."
    
    # Define Pydantic fields with validation
    access_token: str = Field(
        default_factory=lambda: Config.LINKEDIN_ACCESS_TOKEN,
        description="LinkedIn API access token"
    )
    person_id: str = Field(
        default_factory=lambda: Config.LINKEDIN_PERSON_ID,
        description="LinkedIn person ID for posting"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts"
    )
    base_delay: int = Field(
        default=1,
        description="Base delay (in seconds) for retry backoff"
    )
    
    def _make_request(
        self, 
        headers: Dict[str, str], 
        data: Dict[str, Any], 
        retry: int = 0
    ) -> Dict[str, Any]:
        """
        Make authenticated request to LinkedIn API with retry logic
        
        Args:
            headers (Dict[str, str]): Request headers including auth
            data (Dict[str, Any]): Post data to be shared
            retry (int): Current retry attempt number
            
        Returns:
            Dict[str, Any]: Response data with success status and details
        """
        try:
            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return {
                "success": True,
                "response": response.json(),
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            if retry < self.max_retries:
                delay = self.base_delay * (2 ** retry)  # Exponential backoff
                logger.warning(f"Request failed, retrying in {delay} seconds... Error: {str(e)}")
                time.sleep(delay)
                return self._make_request(headers, data, retry + 1)
            else:
                logger.error(f"Max retries reached. Error: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
    
    @staticmethod
    def _to_bold(text: str) -> str:
        """Convert regular text to Unicode bold characters for LinkedIn"""
        normal = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        bold = '𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵'
        trans = str.maketrans(normal, bold)
        return text.translate(trans)

    def _run(self, args: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute LinkedIn post sharing (CrewAI tool interface)
        
        Args:
            args: Either a string content or dict with content and options
                If dict: {
                    "content": str,
                    "title": str,
                    "visibility": str ("connections" or "public")
                }
                
        Returns:
            Dict[str, Any]: Result of the sharing operation
        """
        try:
            # Parse input
            if isinstance(args, str):
                share_request = ShareRequest(content=args)
            elif isinstance(args, dict):
                # Clean and format content
                title = args.get('title', '').strip()
                content = args.get('content', '').strip()
                visibility = args.get('visibility', 'connections')
                
                # Remove emoji-like codes from both title and content
                cleaned_title = re.sub(r':[a-zA-Z_]+:', '', title)
                cleaned_content = re.sub(r':[a-zA-Z_]+:', '', content)
                
                # Format LinkedIn post with bold Unicode title and proper paragraph spacing
                formatted_content = f"{self._to_bold(cleaned_title)}\n\n{cleaned_content}"
                
                # Split content into paragraphs and rejoin with double newlines
                # This ensures proper spacing between paragraphs
                paragraphs = [p.strip() for p in formatted_content.split('\n') if p.strip()]
                formatted_content = '\n\n'.join(paragraphs)
                
                share_request = ShareRequest(
                    content=formatted_content,
                    visibility=visibility
                )
            else:
                raise ValueError("Invalid input format")
            
            # Validate credentials
            if not self.access_token or not self.person_id:
                raise ValueError("LinkedIn credentials not configured")
            
            # Validate content
            if not share_request.content.strip():
                raise ValueError("Empty content provided")
            
            # Prepare request
            visibility_setting = "PUBLIC" if share_request.visibility.lower() == "public" else "CONNECTIONS"
            
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
                            "text": share_request.content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility_setting
                }
            }
            
            # Execute request
            logger.info(f"Attempting to share post on LinkedIn with visibility: {visibility_setting}")
            result = self._make_request(headers, data)
            
            # Handle response
            if result["success"]:
                logger.info("Successfully shared post on LinkedIn")
                return ShareResponse(
                    success=True,
                    message="Post shared successfully",
                    post_data=result["response"]
                ).model_dump()
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Failed to share post: {error_msg}")
                return ShareResponse(
                    success=False,
                    error=error_msg
                ).model_dump()
                
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return ShareResponse(
                success=False,
                error=str(e)
            ).model_dump()
            
        except Exception as e:
            logger.error(f"Unexpected error sharing to LinkedIn: {str(e)}")
            return ShareResponse(
                success=False,
                error=str(e)
            ).model_dump()