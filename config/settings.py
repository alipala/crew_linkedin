# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Central configuration class for the application.
    Handles all configuration settings including paths, credentials, and parameters.
    """
    
    # Base directories
    BASE_DIR = Path(__file__).parent.parent
    
    # Logging configuration
    LOG_DIR = Path(BASE_DIR / 'logs')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG') if os.getenv('ENVIRONMENT') == 'development' else 'INFO'
    LOG_FILE = Path(LOG_DIR / 'app.log')

    # Ensure log directory exists
    if not LOG_DIR.exists():    
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Output and data directories
    OUTPUT_DIR = Path(BASE_DIR / 'data' / 'output')
    DATA_DIR = Path(BASE_DIR / 'data')
    
    # Ensure directories exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # LinkedIn credentials
    LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL')
    LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')
    LINKEDIN_ACCESS_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN')

    # LinkedIn API Configuration
    LINKEDIN_ACCESS_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN')
    LINKEDIN_PERSON_ID = os.getenv('LINKEDIN_PERSON_ID')
    SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')
    
    # Email configuration
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    TOGETHERAI_API_KEY = os.getenv('TOGETHERAI_API_KEY')
    SERPER_API_KEY = os.getenv('SERPER_API_KEY')
    
    # Scraping settings
    MAX_POSTS = int(os.getenv('MAX_POSTS', '100'))
    SCROLL_PAUSE_TIME = float(os.getenv('SCROLL_PAUSE_TIME', '2.0'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    # LLM Settings
    DEFAULT_LLM_MODEL = os.getenv('DEFAULT_LLM_MODEL', 'gpt-4')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '500'))
    
    # MongoDB Configuration (if needed)
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB = os.getenv('MONGODB_DB', 'linkedin_content')
    
    # Application settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

    API_KEY = os.getenv("API_KEY")
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that all required configuration variables are set.
        Returns True if all required configs are present, False otherwise.
        """
        required_configs = [
            ('LINKEDIN_EMAIL', cls.LINKEDIN_EMAIL),
            ('LINKEDIN_PASSWORD', cls.LINKEDIN_PASSWORD),
            ('EMAIL_ADDRESS', cls.EMAIL_ADDRESS),
            ('EMAIL_PASSWORD', cls.EMAIL_PASSWORD),
            ('OPENAI_API_KEY', cls.OPENAI_API_KEY),
            ('SERPER_API_KEY', cls.SERPER_API_KEY),
        ]
        
        missing_configs = [config[0] for config in required_configs if not config[1]]
        
        if missing_configs:
            print(f"Missing required configurations: {', '.join(missing_configs)}")
            return False
        return True
    
    @classmethod
    def get_email_config(cls) -> dict:
        """
        Return email configuration as a dictionary.
        """
        return {
            'email_address': cls.EMAIL_ADDRESS,
            'email_password': cls.EMAIL_PASSWORD,
            'smtp_server': cls.SMTP_SERVER,
            'smtp_port': cls.SMTP_PORT,
        }
    
    @classmethod
    def get_linkedin_config(cls) -> dict:
        """
        Return LinkedIn configuration as a dictionary.
        """
        return {
            'email': cls.LINKEDIN_EMAIL,
            'password': cls.LINKEDIN_PASSWORD,
            'max_posts': cls.MAX_POSTS,
            'scroll_pause_time': cls.SCROLL_PAUSE_TIME,
            'max_retries': cls.MAX_RETRIES,
            'access_token': cls.LINKEDIN_ACCESS_TOKEN,
        }
    
    @classmethod
    def get_llm_config(cls) -> dict:
        """
        Return LLM configuration as a dictionary.
        """
        return {
            'model': cls.DEFAULT_LLM_MODEL,
            'temperature': cls.LLM_TEMPERATURE,
            'max_tokens': cls.MAX_TOKENS,
        }
    
    @classmethod
    def validate_email_config(cls) -> bool:
        required = ['EMAIL_ADDRESS', 'EMAIL_PASSWORD', 'SMTP_SERVER', 'SMTP_PORT']
        return all(getattr(cls, attr) for attr in required)
    
    @classmethod
    def validate_slack_config(cls) -> bool:
        if not cls.SLACK_WEBHOOK_URL:
            print("Slack webhook URL not configured")
            return False
        return True