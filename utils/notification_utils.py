from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logger import logger
import os
from dotenv import load_dotenv

def send_email_notification(
    to_email: str,
    subject: str,
    body: str
) -> bool:
    """
    Send email notification with improved error handling and logging.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    logger.info(f"Attempting to send email to {to_email}")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get email configuration
        email_address = os.getenv("EMAIL_ADDRESS")
        email_password = os.getenv("EMAIL_PASSWORD")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        if not all([email_address, email_password]):
            raise ValueError("Missing email configuration")
            
        logger.debug(f"Email setup - From: {email_address}, To: {to_email}")
        logger.debug(f"Using SMTP server: {smtp_server}:{smtp_port}")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Establish connection and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logger.debug("Starting SMTP connection")
            server.starttls()
            
            logger.debug("Attempting SMTP login")
            server.login(email_address, email_password)
            
            logger.debug("Sending message")
            server.send_message(msg)
            
        logger.info(f"Email successfully sent to {to_email}")
        return True
        
    except ValueError as ve:
        logger.error(f"Configuration error: {str(ve)}")
        return False
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed - check credentials")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        return False