"""Repository helper for the appointments table."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from database.connection import AsyncSessionLocal
from database.models import IST, Appointment, _IST_FMT

logger = logging.getLogger(__name__)


async def create_appointment(
    conversation_id: Optional[str],
    name: str,
    dob: str,
    reason_for_visit: str,
    preferred_time: str,
    insurance_name: Optional[str] = None,
) -> Optional[Appointment]:
    """Insert a new appointment record. Never raises."""
    async with AsyncSessionLocal() as db:
        try:
            now_ist = datetime.now(timezone.utc).astimezone(IST).strftime(_IST_FMT)
            row = Appointment(
                conversation_id=conversation_id or None,
                patient_name=name,
                dob=dob,
                reason_for_visit=reason_for_visit,
                preferred_time=preferred_time,
                insurance_name=insurance_name or None,
                status="scheduled",
                created_at_ist=now_ist,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            logger.info(
                "appointments: created id=%s patient=%s time=%s",
                row.id, name, preferred_time,
            )
            return row
        except Exception as exc:
            await db.rollback()
            logger.warning("appointments: create failed for patient=%s: %s", name, exc)
            return None
