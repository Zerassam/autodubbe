import os
import json
import logging
import sys
from pathlib import Path

def ensure_dir(p):
    """Ensure the directory exists."""
    Path(p).mkdir(parents=True, exist_ok=True)

def load_config(path='config.json'):
    """Load configuration with environment variable support."""
    if not os.path.exists(path):
        # Try config directory
        config_dir_path = os.path.join('config', os.path.basename(path))
        if os.path.exists(config_dir_path):
            path = config_dir_path
        else:
            raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Override with environment variables
    if 'YOUTUBE_API_KEY' in os.environ:
        config.setdefault('YOUTUBE', {})['API_KEY'] = os.environ['YOUTUBE_API_KEY']
    
    if 'YOUTUBE_COOKIES_FILE' in os.environ:
        config.setdefault('YOUTUBE', {})['COOKIES_FILE'] = os.environ['YOUTUBE_COOKIES_FILE']
    
    if 'TMP_DIR' in os.environ:
        config['TMP_DIR'] = os.environ['TMP_DIR']
        
    return config

def setup_logging(logpath=None, level=None):
    """Enhanced logging setup with console + file output."""
    if level is None:
        level = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Default log file
    log_file = log_dir / 'autodubber.log'
    handlers.append(logging.FileHandler(log_file))
    
    # Optional additional log path
    if logpath:
        handlers.append(logging.FileHandler(logpath))
    
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=handlers
    )
