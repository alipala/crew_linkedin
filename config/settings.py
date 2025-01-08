import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # LinkedIn credentials
    LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL', 'default_email@example.com')
    LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD', 'default_password')
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Scraping settings
    MAX_POSTS = 100
    SCROLL_PAUSE_TIME = 2
    MAX_RETRIES = 3
    
    # File paths
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'output')
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    
    # Ensure directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(LOG_DIR, 'scraper.log')