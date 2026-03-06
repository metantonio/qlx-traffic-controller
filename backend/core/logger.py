import logging
import os
from logging.handlers import RotatingFileHandler

# Ensure log directory exists inside backend
# We want this to be consistently in the backend/logs directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Main physical log file
LOG_FILE = os.path.join(LOG_DIR, "kernel.log")

def get_kernel_logger(name: str) -> logging.Logger:
    """Returns a pre-configured logger that writes both to stdout and a rolling file."""
    
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 1. Console Handler (for dev terminal)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # 2. File Handler (Persistent AI syslogs)
        # Keeps up to 5 files of 5MB each
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # File gets more verbose details
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        # Prevent propagation to the root logger to avoid duplicate prints
        logger.propagate = False
        
    return logger
