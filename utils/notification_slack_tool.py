from crewai.tools import BaseTool
from typing import Dict, Any, Optional
from utils.logger import logger
import requests
import os

class NotificationSlackTool(BaseTool):
    name: str = "Slack Notification Tool"
    description: str = "Sends notifications to a Slack channel."

    def _run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Required method for BaseTool, calls run() internally."""
        return self.run(context)

    def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info("NotificationAgent: Starting notification process")
        
        try:
            if not context or 'raw' not in context:
                raise ValueError("No context provided")

            post_data = context.get('raw', {})
            logger.info(f"NotificationAgent received context: {post_data}")

            # Get Slack webhook URL from environment variable
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if not webhook_url:
                raise ValueError("Slack webhook URL not configured")

            # Format message for Slack
            message = self._format_slack_message(post_data)
            
            # Send to Slack
            response = requests.post(webhook_url, json=message)
            response.raise_for_status()  # Raises error for bad status codes

            logger.info("Slack notification sent successfully")
            return {
                "sent": True,
                "platform": "slack",
                "status": "success",
                "recipient": "slack-channel"
            }

        except Exception as e:
            logger.error(f"NotificationAgent failed: {str(e)}")
            return {
                "sent": False,
                "status": "error",
                "error": str(e)
            }

    def _format_slack_message(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        final_answer = post_data.get('content', 'N/A')  # Adjust key based on actual task output structure
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 New LinkedIn Post Final Answer"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Final Answer:*\n{final_answer}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "If this is correct, please approve or request regeneration."
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
