from utils.logger import logger
from crewai import Agent
from utils.notification_utils import send_email_notification
from typing import Dict, Any, Optional

class NotificationAgent(Agent):
    """
    Agent responsible for notifying users about draft LinkedIn posts and handling feedback.
    """

    def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute notification process with comprehensive logging.
        
        Args:
            context (Dict[str, Any], optional): Input context containing post content.
            
        Returns:
            Dict[str, Any]: Status of notification delivery.
        """
        logger.info("NotificationAgent: Starting notification process")
        try:
            # Validate context
            if not context or 'content' not in context:
                error_msg = "Invalid or missing 'content' in context"
                logger.error(f"NotificationAgent: {error_msg}")
                return {"status": "failure", "reason": error_msg}

            draft_post = context['content']
            if not draft_post:
                error_msg = "Draft post content is empty"
                logger.error(f"NotificationAgent: {error_msg}")
                return {"status": "failure", "reason": error_msg}

            # Send email
            user_email = "starfish84itu@gmail.com"  # Consider moving to config
            subject = "Approval Required: Draft LinkedIn Post"
            body = self._format_email_body(draft_post)

            logger.info(f"NotificationAgent: Preparing to send email to {user_email}")
            logger.debug(f"NotificationAgent: Email subject: {subject}")
            logger.debug(f"NotificationAgent: Email body preview: {body[:100]}...")

            # Attempt to send email
            send_email_notification(user_email, subject, body)
            logger.info("NotificationAgent: Email sent successfully")

            return {
                "status": "success",
                "message": "Notification sent",
                "recipient": user_email
            }

        except Exception as e:
            error_msg = f"NotificationAgent failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "failure",
                "reason": error_msg,
                "error_details": str(e)
            }

    def _format_email_body(self, draft_post: str) -> str:
        """Format the email body with the draft post content."""
        logger.debug("NotificationAgent: Formatting email body")
        formatted_body = (
            f"Dear Ali,\n\n"
            f"Here is the draft LinkedIn post created by the system:\n\n"
            f"---\n"
            f"{draft_post}\n"
            f"---\n\n"
            f"Please reply with one of the following:\n"
            f"- 'approve' to finalize the post for sharing.\n"
            f"- 'regenerate' to request adjustments (optional: add suggestions).\n\n"
            f"Best regards,\nYour AI Content Team"
        )
        logger.debug(f"NotificationAgent: Formatted email body preview: {formatted_body[:100]}...")
        return formatted_body