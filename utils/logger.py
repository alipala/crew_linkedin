# logger.py
from loguru import logger
import sys
from pathlib import Path
from config.settings import Config

def setup_logger():
    """Setup logger with dual logging: console and file."""
    logger.remove()  # Remove default handlers
    
    # Ensure log directory exists
    log_dir = Path(Config.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Add console logging
    logger.add(
        sys.stderr,
        level=Config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True
    )

    # Add file logging
    logger.add(
        str(log_dir / "app.log"),
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        level=Config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    return logger

logger = setup_logger()
