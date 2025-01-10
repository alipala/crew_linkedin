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
        logger.info("NotificationAgent: Starting notification process")
        
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if not webhook_url:
                raise ValueError("Slack webhook URL not configured")

            # Get the post data from context
            post_data = {}
            if isinstance(context, dict):
                # Extract title and content from the LinkedInPostContent format
                post_data = {
                    'title': context.get('title', 'New LinkedIn Post'),
                    'content': context.get('content', 'No content available')
                }

            # Format message for Slack
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🚨 {post_data['title']}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Content:*\n{post_data['content']}"
                        }
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