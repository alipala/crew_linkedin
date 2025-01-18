# notification_slack_tool.py
from crewai.tools import BaseTool
from typing import Dict, Any
from utils.logger import logger
import requests
import os

class NotificationSlackTool(BaseTool):
    name: str = "Slack Notification Tool"
    description: str = "Sends notifications to a Slack channel."

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
                    'title': context_data.get('title', 'New LinkedIn Post'),
                    'content': context_data.get('content', 'No content available')
                }

            # Format content with proper spacing
            content_paragraphs = post_data['content'].split('\n')
            formatted_content = '\n\n'.join(p for p in content_paragraphs if p.strip())

            # Format message for Slack with clear spacing and ensure content isn't truncated
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
                            "text": f"*Content:*\n{formatted_content}"
                        }
                    },
                    # Add a divider for better visual separation
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

            # If content is too long for a single message block, split it into multiple blocks
            max_block_size = 3000  # Slack's limit per block
            if len(formatted_content) > max_block_size:
                # Remove the original content block
                message["blocks"].pop(1)
                
                # Split content into chunks
                content_chunks = [formatted_content[i:i + max_block_size] 
                                for i in range(0, len(formatted_content), max_block_size)]
                
                # Insert content blocks after header
                for i, chunk in enumerate(content_chunks):
                    content_block = {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Content (Part {i+1}/{len(content_chunks)}):*\n{chunk}"
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