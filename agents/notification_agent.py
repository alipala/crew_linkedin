from crewai import Agent
from utils.notification_utils import send_email_notification
from typing import Dict, Any, Optional
from utils.logger import logger
from config.settings import Config

class NotificationAgent(Agent):
    def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info("NotificationAgent: Starting notification process")
        
        try:
            if not context or 'raw' not in context:
                raise ValueError("No context provided")

            post_data = context.get('raw', {})
            logger.info(f"NotificationAgent received context: {post_data}")

            if not isinstance(post_data, dict):
                raise ValueError(f"Invalid post_data type: {type(post_data)}")

            # Get email configuration
            email_config = Config.get_email_config()
            if not email_config.get('email_address'):
                raise ValueError("Email configuration missing")

            # Format email content
            subject = f"Review Request: LinkedIn Post - {post_data.get('title', 'New Post')}"
            body = self._format_email_body(post_data)

            # Send email
            email_sent = send_email_notification(
                to_email=email_config['email_address'],
                subject=subject,
                body=body,
                smtp_server=email_config['smtp_server'],
                smtp_port=email_config['smtp_port'],
                username=email_config['email_address'],
                password=email_config['email_password']
            )

            logger.info(f"Email notification sent: {email_sent}")
            
            return {
                "email_sent": email_sent,
                "recipient": email_config['email_address'],
                "status": "success" if email_sent else "failed"
            }

        except Exception as e:
            logger.error(f"NotificationAgent failed: {str(e)}")
            return {
                "email_sent": False,
                "status": "error",
                "error": str(e)
            }

    def _format_email_body(self, post_data: Dict[str, Any]) -> str:
        body = (
            f"Dear LinkedIn Content Creator,\n\n"
            f"A new LinkedIn post draft has been created for your review:\n\n"
            f"Title: {post_data.get('title', 'N/A')}\n\n"
            f"Content:\n{post_data.get('content', 'N/A')}\n\n"
        )
        
        if post_data.get('image_url'):
            body += f"Image URL: {post_data['image_url']}\n\n"
            
        body += (
            f"Please reply with:\n"
            f"- 'APPROVE' to publish the post\n"
            f"- 'REGENERATE' with any specific feedback for modifications\n\n"
            f"Best regards,\n"
            f"Your AI Content Team"
        )
        
        return body