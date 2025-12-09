from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from uuid import UUID
import logging

from backend.database import get_db
from backend.models.user import User

logger = logging.getLogger(__name__)

# Static UUID for the Guest User
GUEST_USER_ID = UUID('00000000-0000-0000-0000-000000000000')

async def get_guest_user(session: AsyncSession = Depends(get_db)) -> User:
    """
    Return the singleton Guest User.
    Create it if it doesn't exist.
    """
    try:
        # Check if guest exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == GUEST_USER_ID))
        guest = result.scalars().first()

        if not guest:
            logger.info("Creating Guest User")
            guest = User(
                id=GUEST_USER_ID,
                email="guest@resumebuilder.local",
                hashed_password="N/A",  # No password needed
                is_active=True,
                full_name="Guest User"
            )
            session.add(guest)
            await session.commit()
            await session.refresh(guest)
        
        return guest
    except Exception as e:
        logger.error(f"Failed to get/create Guest User: {e}")
        # Build a dummy fallback in memory if DB fails (shouldn't happen)
        return User(id=GUEST_USER_ID, email="guest@fallback.local", is_active=True)
