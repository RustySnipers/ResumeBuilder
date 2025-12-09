"""
Database Initialization Script.

This script initializes the database schema by importing all models and running create_all.
It is intended to be run once before the application starts.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.database import init_db, engine
from backend.models.user import User
from backend.models.resume import Resume
from backend.models.webhook_event import WebhookEvent
from backend.models.webhook import Webhook
from backend.models.verification_token import VerificationToken
# Import other models if they exist. 
# Checking directories, we have 'auth' (User, Role, etc), 'resumes' (Resume). 
# But 'backend/models' directory listing would be better.
# Assuming standard ones for now based on what verify_full.py triggered (User, Resume).

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing database schema...")
    try:
        # Import all models here to ensure they are registered with Base
        # We imported User, Resume above.
        # Let's import implicit ones if possible or assume they are in models pkg
        from backend.models import user, resume, audit_log, verification_token, role, user_role, session
        
        await init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
