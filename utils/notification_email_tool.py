# utils/notification_slack_tool.py
import os
import re
from typing import Dict, Any

from crewai.tools import BaseTool

from utils.logger import logger
from utils.notification_utils import send_email_notification


class NotificationEmailTool(BaseTool):
    name: str = "Email Notification Tool"
    description: str = "Sends notifications to a email"

    def _clean_content(self, text: str) -> str:
        """
        Clean content by:
        1. Removing Markdown-style bold markers
        2. Preserving the text inside them
        3. Removing any excessive whitespace
        """
        # Remove ** markers while keeping the text inside
        cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Split into paragraphs and clean each one
        paragraphs = [p.strip() for p in cleaned_text.split('\n') if p.strip()]
        
        # Rejoin with proper spacing
        return '\n\n'.join(paragraphs)

    def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send notifications to email"""
        logger.info("NotificationAgent: Starting notification process")
        
        try:

            # Get the post data from context
            post_data = {}

            if isinstance(context, dict):
                context_data = context.get('context', context)
                if isinstance(context_data, dict):
                    context_data = context_data.get('description', context)
                    if isinstance(context_data, dict):
                        context_data = context_data.get('post', context)


            to_email = os.getenv('EMAIL_TO_ADDRESS')
            send_email_notification(
                to_email,
                self._clean_content(context_data.get('title', 'New LinkedIn Post')),
                self._clean_content(context_data.get('content', 'No content available'))
            )

            logger.info("Email notification sent successfully to " + to_email)
            return {
                "sent": True,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"NotificationAgent failed: {str(e)}")
            return {
                "sent": False,
                "status": "error",
                "error": str(e)
            }