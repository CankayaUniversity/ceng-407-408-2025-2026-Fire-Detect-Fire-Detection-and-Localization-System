import os
import logging
import firebase_admin
from firebase_admin import credentials
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def init_firebase():
    cred_path = settings.firebase_credentials_path
    if not cred_path or not os.path.exists(cred_path):
        logger.warning(f"Firebase credentials not found at {cred_path}. Push notifications will be disabled.")
        return False
        
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
        return True
    except ValueError as e:
        # Happens if already initialized
        logger.warning(f"Firebase initialization issue: {e}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return False
