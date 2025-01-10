from crewai import Agent
from utils.notification_utils import send_email_notification
from typing import Dict, Any, Optional
import os
from utils.logger import logger
from config.settings import Config
class NotificationAgent(Agent):
    """
    Agent responsible for notifying users about draft LinkedIn posts and handling feedback.
    """

    def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info("NotificationAgent: Starting notification process")
        try:
            # Validate context from previous task
            if not context or not isinstance(context, dict):
                error_msg = "Invalid context structure received"
                logger.error(f"NotificationAgent: {error_msg}")
                return {"status": "failure", "reason": error_msg}
                
            # Extract post content - CrewAI passes previous task output in 'raw'
            post_content = context.get('raw', {})
            if not post_content:
                error_msg = "No post content found in context"
                logger.error(f"NotificationAgent: {error_msg}")
                return {"status": "failure", "reason": error_msg}

            # Get content and status from PostCreateAgent output
            content = post_content.get('content')
            image_url = post_content.get('image')
            post_status = post_content.get('status')

            if post_status != "success" or not content:
                error_msg = f"Invalid post content received. Status: {post_status}"
                logger.error(f"NotificationAgent: {error_msg}")
                return {"status": "failure", "reason": error_msg}

            # Prepare email content
            user_email = os.getenv("EMAIL_ADDRESS")
            if not user_email:
                error_msg = "Email address not configured"
                logger.error(f"NotificationAgent: {error_msg}")
                return {"status": "failure", "reason": error_msg}

            subject = "Review Required: New LinkedIn Post Draft"
            body = self._format_email_body(content, image_url)

            logger.info(f"NotificationAgent: Sending email to {user_email}")
            logger.debug(f"NotificationAgent: Email subject: {subject}")
            logger.debug(f"NotificationAgent: Email body preview: {body[:100]}...")

            # Send email notification
            notification_sent = send_email_notification(
                to_email=user_email,
                subject=subject,
                body=body
            )

            if not notification_sent:
                error_msg = "Failed to send email notification"
                logger.error(f"NotificationAgent: {error_msg}")
                return {"status": "failure", "reason": error_msg}

            logger.info("NotificationAgent: Email notification sent successfully")
            return {
                "status": "success",
                "message": "Notification sent successfully",
                "recipient": user_email,
                "post_content": content,
                "notification_type": "email",
                "requires_approval": True
            }

        except Exception as e:
            error_msg = f"NotificationAgent failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "failure", 
                "reason": error_msg,
                "error_details": str(e)
            }

    def _format_email_body(self, content: str, image_url: Optional[str] = None) -> str:
        """Format the email body with the draft post content."""
        logger.debug("NotificationAgent: Formatting email body")
        
        formatted_body = (
            f"Dear LinkedIn Content Creator,\n\n"
            f"A new LinkedIn post draft has been created for your review:\n\n"
            f"---\n"
            f"{content}\n"
            f"---\n"
        )
        
        if image_url:
            formatted_body += f"\nGenerated Image URL: {image_url}\n"
            
        formatted_body += (
            f"\nPlease reply with:\n"
            f"- 'APPROVE' to publish the post\n"
            f"- 'REGENERATE' with any specific feedback for modifications\n\n"
            f"Best regards,\nYour AI Content Team"
        )

        logger.debug(f"NotificationAgent: Formatted email body preview: {formatted_body[:100]}...")
        return formatted_body