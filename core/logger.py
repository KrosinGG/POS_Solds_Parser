import sys
from loguru import logger

# Remove default logger handler
logger.remove()

# Add console handler with clear formatting
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# Add file handler for error tracking
logger.add(
    "parser.log",
    rotation="10 MB",
    retention="14 days",
    level="DEBUG",
    encoding="utf-8"
)

__all__ = ["logger"]
