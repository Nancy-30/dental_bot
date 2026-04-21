"""Repository helpers for the call_metadata table."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from database.connection import AsyncSessionLocal
from database.models import IST, CallMetadata, _IST_FMT

logger = logging.getLogger(__name__)


async def upsert_call_metadata(
    call_id: str,
    phone_number: Optional[str] = None,
) -> Optional[CallMetadata]:
    """Ensure a call_metadata row exists for call_id. Never raises."""
    if not call_id:
        return None
    clean_phone = (phone_number or "").strip()

    async with AsyncSessionLocal() as db:
        try:
            row = await db.get(CallMetadata, call_id)
            if row:
                if clean_phone and not row.phone_number:
                    row.phone_number = clean_phone
            else:
                now_ist = datetime.now(timezone.utc).astimezone(IST).strftime(_IST_FMT)
                row = CallMetadata(
                    call_id=call_id,
                    phone_number=clean_phone or None,
                    created_at_ist=now_ist,
                )
                db.add(row)
            await db.commit()
            logger.info("call_metadata: ensured call_id=%s", call_id)
            return row
        except Exception as exc:
            await db.rollback()
            logger.warning("call_metadata upsert failed (call_id=%s): %s", call_id, exc)
            return None


async def update_call_duration(call_id: str, duration_seconds: float) -> None:
    """Set call_duration on an existing call_metadata row. Never raises."""
    if not call_id:
        return
    async with AsyncSessionLocal() as db:
        try:
            row = await db.get(CallMetadata, call_id)
            if row:
                row.call_duration = round(duration_seconds, 3)
                await db.commit()
                logger.info("call_metadata: call_id=%s duration=%.3fs", call_id, duration_seconds)
        except Exception as exc:
            await db.rollback()
            logger.warning("call_metadata update_duration failed (call_id=%s): %s", call_id, exc)


async def get_call_phone(call_id: str, retries: int = 3, delay: float = 0.2) -> str:
    """Fetch the phone_number stored for a call_id."""
    if not call_id:
        return ""
    for attempt in range(retries):
        async with AsyncSessionLocal() as db:
            row = await db.get(CallMetadata, call_id)
            if row and row.phone_number:
                return row.phone_number
        if attempt < retries - 1:
            await asyncio.sleep(delay)
    return ""
