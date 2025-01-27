# utils/notification_slack_tool.py
from crewai.tools import BaseTool
from typing import Dict, Any
from utils.logger import logger
import requests
import os
import re

class NotificationSlackTool(BaseTool):
    name: str = "Slack Notification Tool"
    description: str = "Sends notifications to a Slack channel."

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
        """Send notifications to a Slack channel."""
        logger.info("NotificationAgent: Starting notification process")
        
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if not webhook_url:
                raise ValueError("Slack webhook URL not configured")

            # Get the post data from context
            post_data = {}
            if isinstance(context, dict):
                # Get context either directly or from nested 'context' key
                context_data = context.get('context', context)
                post_data = {
                    'title': self._clean_content(context_data.get('title', 'New LinkedIn Post')),
                    'content': self._clean_content(context_data.get('content', 'No content available'))
                }

            # Format message for Slack with clear spacing
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📝 {post_data['title']}"[:150]  # Slack header limit
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Content:\n{post_data['content']}"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "👍 Approve"
                                },
                                "style": "primary",
                                "value": "approve"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔄 Regenerate"
                                },
                                "style": "danger",
                                "value": "regenerate"
                            }
                        ]
                    }
                ]
            }

            # Handle long content by splitting into multiple blocks if needed
            max_block_size = 3000  # Slack's limit per block
            if len(post_data['content']) > max_block_size:
                # Remove the original content block
                message["blocks"].pop(1)
                
                # Split content into chunks
                content_chunks = [
                    post_data['content'][i:i + max_block_size] 
                    for i in range(0, len(post_data['content']), max_block_size)
                ]
                
                # Insert content blocks after header
                for i, chunk in enumerate(content_chunks):
                    content_block = {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Content (Part {i+1}/{len(content_chunks)}):\n{chunk}"
                        }
                    }
                    message["blocks"].insert(i + 1, content_block)

            # Send to Slack
            response = requests.post(webhook_url, json=message)
            response.raise_for_status()

            logger.info("Slack notification sent successfully")
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