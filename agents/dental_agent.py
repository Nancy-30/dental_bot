"""DentalAgent — LiveKit Agent with tool methods for the dental clinic AI receptionist."""

import asyncio
import json
import logging
import random
from typing import AsyncIterable, Optional

from livekit import rtc
from livekit.agents import Agent, ModelSettings, RunContext, function_tool

from agents.patient_memory import PatientMemory
from agents.prompts import SYSTEM_PROMPT
from config import settings
from database.patient_repo import upsert_patient_data
from database.appointment_repo import create_appointment
from utils.date_utils import normalize_dob, normalize_preferred_time

logger = logging.getLogger(__name__)

class _FillerRotator:
    """Cycles through fillers without consecutive repeats."""

    def __init__(self, phrases: list[str]) -> None:
        self._phrases = phrases[:]
        self._last: str = ""

    def next(self) -> str:
        candidates = [p for p in self._phrases if p != self._last]
        if not candidates:
            candidates = self._phrases
        chosen = random.choice(candidates)
        self._last = chosen
        return chosen


_filler_lookup = _FillerRotator([
    "Sure, let me check that for you.",
    "Of course, one moment.",
    "Alright, let me look that up.",
    "Give me just a second.",
])
_filler_booking = _FillerRotator([
    "Alright, let me get that booked for you.",
    "Sure, processing that right now.",
    "One moment while I confirm your appointment.",
    "Let me lock that in for you.",
])


class DentalAgent(Agent):
    def __init__(
        self,
        phone_number: str = "",
        conversation_id: str = "",
        mode: str = "client-server",
    ) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.patient_memory = PatientMemory(
            phone_number=phone_number,
            conversation_id=conversation_id,
            mode=mode,
        )

    # ── TTS node — pass through without heavy normalization (English) ──────────
    async def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> Optional[AsyncIterable[rtc.AudioFrame]]:
        """Stream text to TTS, flushing on sentence boundaries for low latency."""
        import re

        _FLUSH_CHARS = 80

        async def _sentence_iter() -> AsyncIterable[str]:
            buffer = ""
            async for chunk in text:
                buffer += chunk
                while True:
                    m = re.search(r"[.!?\n]", buffer)
                    if not m:
                        m = re.search(r"[,;:](?:\s)", buffer)
                    if m:
                        pos = m.end()
                        yield buffer[:pos]
                        buffer = buffer[pos:]
                    elif len(buffer) >= _FLUSH_CHARS:
                        space_idx = buffer.rfind(" ", 0, _FLUSH_CHARS)
                        if space_idx > 0:
                            yield buffer[:space_idx + 1]
                            buffer = buffer[space_idx + 1:]
                        else:
                            yield buffer
                            buffer = ""
                    else:
                        break
            if buffer.strip():
                yield buffer

        async for frame in Agent.default.tts_node(self, _sentence_iter(), model_settings):
            yield frame

    # ── Transcription node — raw text to frontend ─────────────────────────────
    async def transcription_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[str]:
        async for chunk in text:
            yield chunk

    # ── Tools ──────────────────────────────────────────────────────────────────

    @function_tool()
    async def capture_patient_info(
        self,
        context: RunContext,
        name: str = "",
        dob: str = "",
        reason_for_visit: str = "",
        preferred_time: str = "",
        insurance_name: str = "",
    ) -> str:
        """Save any patient detail the moment it is shared. Pass only known fields; leave others empty."""
        if not any((name, dob, reason_for_visit, preferred_time, insurance_name)):
            return "Nothing to save — no patient information provided."

        self.patient_memory.update(
            name=name,
            dob=normalize_dob(dob) if dob else dob,
            reason_for_visit=reason_for_visit,
            preferred_time=normalize_preferred_time(preferred_time) if preferred_time else preferred_time,
            insurance_name=insurance_name,
        )

        logger.info(
            "Tool: capture_patient_info conv=%s fields=%s",
            self.patient_memory.conversation_id,
            self.patient_memory.collected_fields(),
        )

        # Persist to DB in background
        asyncio.create_task(
            upsert_patient_data(
                conversation_id=self.patient_memory.conversation_id or None,
                phone_number=self.patient_memory.phone_number or None,
                mode=self.patient_memory.mode,
                name=self.patient_memory.name or None,
                dob=self.patient_memory.dob or None,
                reason_for_visit=self.patient_memory.reason_for_visit or None,
                preferred_time=self.patient_memory.preferred_time or None,
                insurance_name=self.patient_memory.insurance_name or None,
            )
        )

        # Append permanent session state to instructions so LLM never re-asks
        fields = self.patient_memory.collected_fields()
        if fields:
            state_block = (
                f"\n\n[SESSION STATE — PERMANENT: Patient info collected this call: "
                f"{', '.join(fields)}. "
                f"NEVER ask for these fields again. Proceed with the conversation.]"
            )
            self.update_instructions(SYSTEM_PROMPT + state_block)

        return (
            "[Saved. Do not repeat this back to the patient. "
            "Continue naturally and collect any remaining missing fields.]"
        )

    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        name: str = "",
        dob: str = "",
        reason_for_visit: str = "",
        preferred_time: str = "",
        insurance_name: str = "",
    ) -> str:
        """Confirm the appointment. Call only when name, dob, reason_for_visit, and preferred_time are all known. Insurance optional."""
        # Merge with memory in case some fields were captured earlier
        mem = self.patient_memory
        final_name = name or mem.name
        final_dob = normalize_dob(dob or mem.dob)
        final_reason = reason_for_visit or mem.reason_for_visit
        final_time = normalize_preferred_time(preferred_time or mem.preferred_time)
        final_insurance = insurance_name or mem.insurance_name

        await context.session.say(
            _filler_booking.next(),
            allow_interruptions=True,
            add_to_chat_ctx=False,
        )

        if not (final_name and final_dob and final_reason and final_time):
            missing = [
                f for f, v in [
                    ("name", final_name), ("date of birth", final_dob),
                    ("reason for visit", final_reason), ("preferred time", final_time),
                ] if not v
            ]
            return f"Cannot book yet — still missing: {', '.join(missing)}. Please collect these first."

        logger.info(
            "Tool: book_appointment name=%s dob=%s reason=%s time=%s insurance=%s",
            final_name, final_dob, final_reason, final_time, final_insurance,
        )

        # Update memory
        self.patient_memory.update(
            name=final_name, dob=final_dob,
            reason_for_visit=final_reason, preferred_time=final_time,
            insurance_name=final_insurance,
        )
        self.patient_memory.appointment_booked = True

        # Persist appointment to DB in background
        asyncio.create_task(
            create_appointment(
                conversation_id=self.patient_memory.conversation_id or None,
                name=final_name,
                dob=final_dob,
                reason_for_visit=final_reason,
                preferred_time=final_time,
                insurance_name=final_insurance or None,
            )
        )

        return (
            f"[Appointment confirmed and saved. "
            f"Patient: {final_name}, DOB: {final_dob}, "
            f"Reason: {final_reason}, Time: {final_time}, "
            f"Insurance: {final_insurance or 'N/A'}. "
            f"Tell the patient their appointment is confirmed and they will receive a confirmation shortly.]"
        )

    @function_tool()
    async def get_clinic_info(
        self,
        context: RunContext,
        topic: str = "general",
    ) -> str:
        """Clinic FAQ. topic: hours, address, insurance, services, emergency, general."""
        await context.session.say(
            _filler_lookup.next(),
            allow_interruptions=True,
            add_to_chat_ctx=False,
        )

        topic = topic.lower().strip()
        logger.info("Tool: get_clinic_info topic=%s", topic)

        if topic == "hours":
            return (
                f"{settings.CLINIC_NAME} is open {settings.CLINIC_HOURS}. "
                f"We are closed on weekends and major holidays."
            )
        elif topic == "address":
            return (
                f"{settings.CLINIC_NAME} is located at {settings.CLINIC_ADDRESS}. "
                f"Parking is available on site."
            )
        elif topic == "insurance":
            return (
                f"We accept {settings.CLINIC_INSURANCE}. "
                f"We also offer flexible payment plans for patients without insurance. "
                f"Please bring your insurance card to your appointment."
            )
        elif topic == "services":
            return (
                f"{settings.CLINIC_NAME} offers general dentistry, teeth cleaning, "
                f"fillings, extractions, root canals, crowns, veneers, Invisalign, "
                f"teeth whitening, and emergency dental care."
            )
        elif topic == "emergency":
            return (
                f"For dental emergencies during office hours, call us at {settings.CLINIC_PHONE}. "
                f"After hours, please go to your nearest emergency room or urgent care facility. "
                f"For severe pain or swelling, seek immediate medical attention."
            )
        else:
            return (
                f"{settings.CLINIC_NAME} — Phone: {settings.CLINIC_PHONE}. "
                f"Address: {settings.CLINIC_ADDRESS}. "
                f"Hours: {settings.CLINIC_HOURS}."
            )

    @function_tool()
    async def escalate_call(self, context: RunContext) -> str:
        """Transfer to human staff. Say the handoff line first, then call this."""
        logger.info(
            "Tool: escalate_call — conv=%s", self.patient_memory.conversation_id
        )
        # Signal the frontend/bridge that escalation is requested
        room = context.session.room_io.room
        if room and room.local_participant:
            await room.local_participant.publish_data(
                json.dumps({"action": "escalate"}).encode("utf-8"),
                reliable=True,
            )
        return "[Escalation signal sent. The call is being transferred to a staff member.]"

    @function_tool()
    async def end_call(self, context: RunContext) -> str:
        """Hang up. Call AFTER speaking a goodbye line."""
        logger.info(
            "Tool: end_call — conv=%s", self.patient_memory.conversation_id
        )
        room = context.session.room_io.room
        if room and room.local_participant:
            await room.local_participant.publish_data(
                json.dumps({"action": "hangup"}).encode("utf-8"),
                reliable=True,
            )
        return "Call ending."
