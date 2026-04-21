"""Post-call LLM analysis service — uses OpenAI for structured extraction."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy import select

from database.call_analysis_repo import save_call_analysis
from database.connection import AsyncSessionLocal
from database.conversation_repo import get_conversation_transcript
from database.models import CallMetadata, PatientData

logger = logging.getLogger(__name__)

_ANALYSIS_MODEL = "gpt-4o-mini"

_ANALYSIS_PROMPT = """\
You are a call quality analyst for a dental clinic. You will be given a full transcript \
of a voice conversation between a patient and an AI dental receptionist. \
Analyse the conversation and return a single valid JSON object with EXACTLY the \
keys listed below. Do not add markdown fences or any text outside the JSON object.

TRANSCRIPT:
{transcript}

METADATA:
- Phone Number: {phone_number}
- Patient Name (from DB): {patient_name}
- Call Start Time: {call_start_time}
- Call End Time: {call_end_time}
- Call Duration (seconds): {duration}

Return a JSON object with these exact keys:

{{
  "call_intent": "booking | faq | reschedule | emergency | other",
  "appointment_requested": true or false,
  "appointment_confirmed": true or false,
  "patient_name_captured": "<patient name as spoken or null>",
  "dob_captured": "<date of birth as mentioned or null>",
  "reason_for_call": "<reason for visit as stated by patient or null>",
  "preferred_time_captured": "<preferred appointment time or null>",
  "insurance_name_captured": "<insurance provider or null>",
  "questions_asked": ["<question 1>", "<question 2>"],
  "num_questions_asked": 0,
  "num_questions_answered": 0,
  "did_bot_fail_to_answer": "Yes | No",
  "unanswered_question": "<unanswered question text or null>",
  "bot_response_accuracy": "Accurate | Partially Accurate | Incorrect",
  "conversation_status": "Completed | Disconnected | Technical Issue",
  "escalation_triggered": true or false,
  "customer_satisfaction_signal": "Satisfied | Dissatisfied | Neutral | Not detectable",
  "conversational_issue_detected": "<describe issue or null>"
}}

Rules:
- Use null (not the string "null") for absent fields.
- For boolean fields use true or false (JSON booleans, not strings).
- For Yes/No fields use exactly "Yes" or "No".
- questions_asked must be a JSON array.
- Do not hallucinate information not in the transcript.
"""


def _build_transcript(turns: list[dict]) -> str:
    lines = []
    for turn in turns:
        role = turn.get("role", "unknown").upper()
        content = (turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(empty transcript)"


def _compute_end_time(start_ist_str: str, duration_s: Optional[float]) -> str:
    if not start_ist_str or not duration_s:
        return ""
    try:
        dt = datetime.strptime(start_ist_str, "%Y-%m-%d %H:%M:%S IST")
        dt_end = dt + timedelta(seconds=duration_s)
        return dt_end.strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return ""


async def _fetch_call_metadata(call_id: str) -> Optional[CallMetadata]:
    async with AsyncSessionLocal() as db:
        return await db.get(CallMetadata, call_id)


async def _fetch_patient_data(call_id: str) -> Optional[PatientData]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PatientData).where(PatientData.conversation_id == call_id)
        )
        return result.scalars().first()


async def _call_openai(prompt: str) -> Optional[dict]:
    """Call OpenAI and parse the JSON response."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("call_analysis: OPENAI_API_KEY not set — skipping post-call analysis")
        return None

    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=_ANALYSIS_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    return json.loads(raw)


async def analyze_call(call_id: str) -> None:
    """Fetch transcript, analyse with OpenAI, save to call_analysis. Never raises."""
    if not call_id:
        return
    try:
        turns = await get_conversation_transcript(call_id)
        meta = await _fetch_call_metadata(call_id)
        patient = await _fetch_patient_data(call_id)

        if not turns:
            logger.warning("call_analysis: no transcript for call_id=%s — skipping", call_id)
            return

        call_start_time = meta.created_at_ist if meta else ""
        duration = meta.call_duration if meta else None
        call_end_time = _compute_end_time(call_start_time, duration)
        call_date = call_start_time[:10] if call_start_time else ""
        phone_number = (meta.phone_number if meta else "") or ""
        patient_name = (patient.name if patient else "") or ""

        transcript_str = _build_transcript(turns)
        prompt = _ANALYSIS_PROMPT.format(
            transcript=transcript_str,
            phone_number=phone_number or "Unknown",
            patient_name=patient_name or "Not provided",
            call_start_time=call_start_time or "Unknown",
            call_end_time=call_end_time or "Unknown",
            duration=round(duration, 1) if duration else "Unknown",
        )

        logger.info("call_analysis: calling OpenAI for call_id=%s (%d turns)", call_id, len(turns))
        llm_data = await _call_openai(prompt)

        if not llm_data:
            logger.warning("call_analysis: no data returned for call_id=%s", call_id)
            return

        llm_data.update({
            "call_date": call_date,
            "call_start_time": call_start_time,
            "call_end_time": call_end_time,
            "duration": round(duration, 3) if duration else None,
            "phone_number": phone_number or None,
        })

        if isinstance(llm_data.get("questions_asked"), list):
            llm_data["questions_asked"] = json.dumps(llm_data["questions_asked"], ensure_ascii=False)

        await save_call_analysis(call_id=call_id, data=llm_data)
        logger.info("call_analysis: completed for call_id=%s", call_id)

    except Exception as exc:
        logger.warning("call_analysis: failed for call_id=%s: %s", call_id, exc)
