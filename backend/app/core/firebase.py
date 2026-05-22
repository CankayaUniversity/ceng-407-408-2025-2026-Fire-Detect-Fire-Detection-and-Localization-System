import base64
import json
import os
import logging
import firebase_admin
from firebase_admin import credentials
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def init_firebase():
    if firebase_admin._apps:
        logger.info("Firebase Admin SDK already initialized.")
        return True

    encoded_credentials = settings.firebase_credentials_json_base64
    if encoded_credentials:
        try:
            decoded = base64.b64decode(encoded_credentials).decode("utf-8")
            cred_data = json.loads(decoded)
            cred = credentials.Certificate(cred_data)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized from environment.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK from environment: {e}")
            return False

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
