"""Repository helpers for the conversations table."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select

from database.connection import AsyncSessionLocal
from database.models import IST, Conversation, _IST_FMT

logger = logging.getLogger(__name__)


async def save_conversation_turn(
    conversation_id: str,
    role: str,
    content: str,
    sequence: int,
    mode: str = "client-server",
    phone_number: Optional[str] = None,
) -> None:
    """Persist one user/assistant turn. Never raises."""
    if not conversation_id or not role or not content:
        return

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            db.add(Conversation(
                conversation_id=conversation_id,
                phone_number=phone_number or None,
                mode=mode,
                role=role,
                content=content,
                sequence=sequence,
                created_at_ist=now.astimezone(IST).strftime(_IST_FMT),
            ))
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.warning(
                "conversations: failed to save turn conv=%s seq=%s: %s",
                conversation_id, sequence, exc,
            )


async def get_conversation_transcript(conversation_id: str) -> List[dict]:
    """Return all turns for a conversation ordered by sequence."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.conversation_id == conversation_id)
            .order_by(Conversation.sequence)
        )
        return [row.to_dict() for row in result.scalars().all()]
