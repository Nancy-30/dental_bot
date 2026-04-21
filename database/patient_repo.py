"""Repository helpers for the patient_data table."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from database.connection import AsyncSessionLocal
from database.models import IST, PatientData, _IST_FMT

logger = logging.getLogger(__name__)


async def upsert_patient_data(
    conversation_id: Optional[str] = None,
    phone_number: Optional[str] = None,
    name: Optional[str] = None,
    dob: Optional[str] = None,
    reason_for_visit: Optional[str] = None,
    preferred_time: Optional[str] = None,
    insurance_name: Optional[str] = None,
    mode: str = "client-server",
) -> Optional[PatientData]:
    """Create or update a patient_data row.

    Upsert key: conversation_id for client-server, phone_number for telephonic.
    Only non-empty fields overwrite existing values.
    """
    clean_conv = (conversation_id or "").strip()
    clean_phone = (phone_number or "").strip()

    if not clean_conv and not clean_phone:
        logger.warning("upsert_patient_data: requires conversation_id or phone_number — skipping")
        return None

    async with AsyncSessionLocal() as db:
        try:
            row: Optional[PatientData] = None
            if clean_conv:
                result = await db.execute(
                    select(PatientData).where(PatientData.conversation_id == clean_conv)
                )
                row = result.scalar_one_or_none()
            elif clean_phone:
                result = await db.execute(
                    select(PatientData).where(PatientData.phone_number == clean_phone)
                )
                row = result.scalar_one_or_none()

            now_ist = datetime.now(timezone.utc).astimezone(IST).strftime(_IST_FMT)
            if row is None:
                row = PatientData(
                    conversation_id=clean_conv or None,
                    phone_number=clean_phone or None,
                    mode=mode,
                    name=name or None,
                    dob=dob or None,
                    reason_for_visit=reason_for_visit or None,
                    preferred_time=preferred_time or None,
                    insurance_name=insurance_name or None,
                    created_at_ist=now_ist,
                    updated_at_ist=now_ist,
                )
                db.add(row)
                logger.info("patient_data: new row conv=%s", clean_conv or "-")
            else:
                if name:
                    row.name = name
                if dob:
                    row.dob = dob
                if reason_for_visit:
                    row.reason_for_visit = reason_for_visit
                if preferred_time:
                    row.preferred_time = preferred_time
                if insurance_name:
                    row.insurance_name = insurance_name
                if clean_conv:
                    row.conversation_id = clean_conv
                row.updated_at_ist = now_ist
                logger.info("patient_data: updated row conv=%s", clean_conv or "-")

            await db.commit()
            await db.refresh(row)
            return row
        except Exception as exc:
            await db.rollback()
            logger.warning("patient_data upsert failed (conv=%s): %s", clean_conv or "-", exc)
            return None
