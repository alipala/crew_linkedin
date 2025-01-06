from loguru import logger
import sys
from config.settings import Config

# Configure logger
logger.remove()  # Remove default handler

# Add console handler
logger.add(
    sys.stderr,
    level=Config.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Add file handler
logger.add(
    Config.LOG_FILE,
    rotation="500 MB",
    retention="10 days",
    level=Config.LOG_LEVEL
)