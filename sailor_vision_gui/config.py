import os
import json
from pathlib import Path
import logging
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("sailorvision.log")
    ]
)

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "database": {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", ""),
        "database": os.getenv("PGDATABASE", "sailorvision"),
        "url": os.getenv("DATABASE_URL", "postgresql://postgres:@localhost:5432/sailorvision")
    },
    "app": {
        "name": "SailorVision",
        "version": "1.0.0",
        "description": "Maritime Surveillance System",
        "host": "0.0.0.0",
        "port": 5000
    },
    "storage": {
        "default": "local",  # "local" or "cloud"
        "local_path": str(Path.home() / "SailorVision" / "recordings"),
        "cloud_settings": {
            "provider": "s3",
            "bucket": "sailorvision-recordings",
            "region": "us-east-1"
        }
    },
    "detection": {
        "confidence_threshold": 0.6,
        "model_path": "models/yolov4-tiny.weights",
        "config_path": "models/yolov4-tiny.cfg",
        "classes_path": "models/coco.names"
    }
}

CONFIG_PATH = Path.home() / ".sailorvision" / "config.json"

def load_config():
    """Load configuration from file or create default if not exists"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                logger.info("Loaded configuration from %s", CONFIG_PATH)
                return config
        else:
            save_config(DEFAULT_CONFIG)
            logger.info("Created default configuration at %s", CONFIG_PATH)
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error("Error loading configuration: %s", e)
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file"""
    try:
        # Create directory if not exists
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        logger.info("Saved configuration to %s", CONFIG_PATH)
        return True
    except Exception as e:
        logger.error("Error saving configuration: %s", e)
        return False

def get_db_url():
    return os.getenv("DB_URL")
