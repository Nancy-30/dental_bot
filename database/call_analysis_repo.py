"""Repository helper for the call_analysis table."""

from __future__ import annotations

import logging
from typing import Optional

from database.connection import AsyncSessionLocal
from database.models import CallAnalysis

logger = logging.getLogger(__name__)

_COLUMNS = {
    "call_date", "call_start_time", "call_end_time", "duration", "phone_number",
    "call_intent", "appointment_requested", "appointment_confirmed",
    "patient_name_captured", "dob_captured", "reason_for_call",
    "preferred_time_captured", "insurance_name_captured",
    "questions_asked", "num_questions_asked", "num_questions_answered",
    "did_bot_fail_to_answer", "unanswered_question",
    "bot_response_accuracy", "conversation_status",
    "escalation_triggered", "customer_satisfaction_signal",
    "conversational_issue_detected",
}


async def save_call_analysis(
    call_id: str,
    data: dict,
) -> Optional[CallAnalysis]:
    """Insert one call_analysis row from the dict produced by the LLM analyser. Never raises."""
    if not call_id:
        return None

    async with AsyncSessionLocal() as db:
        try:
            row = CallAnalysis(
                call_id=call_id,
                **{k: data.get(k) for k in _COLUMNS},
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            logger.info("call_analysis: saved id=%s call_id=%s", row.id, call_id)
            return row
        except Exception as exc:
            await db.rollback()
            logger.warning("call_analysis: failed to save call_id=%s: %s", call_id, exc)
            return None
