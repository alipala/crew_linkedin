from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logger import logger
import os
from dotenv import load_dotenv
from config.settings import Config

def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    logger.info(f"Preparing email notification to {to_email}")
    
    if not Config.validate_email_config():
        logger.error("Invalid email configuration")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False