"""Main agent entrypoint — one call per session."""

import asyncio
import logging
import time

from livekit import rtc
from livekit.agents import (
    AgentSession,
    ConversationItemAddedEvent,
    JobContext,
    MetricsCollectedEvent,
    UserInputTranscribedEvent,
    room_io,
)
from livekit.plugins import noise_cancellation

from agents.dental_agent import DentalAgent
from agents.metrics import MetricsTracker
from agents.session import build_session, load_greeting_audio, play_greeting
from database.call_analysis_service import analyze_call
from database.call_metadata_repo import update_call_duration, upsert_call_metadata
from database.conversation_repo import save_conversation_turn
from database.patient_repo import upsert_patient_data
from database.evaluation_stats_repo import save_evaluation_statistics

logger = logging.getLogger(__name__)


async def my_agent(ctx: JobContext) -> None:
    call_id = ctx.room.name or "unknown"
    # Room name convention:
    #   client-server → 'dental-{uuid8}' (set by the frontend /token route)
    is_telephonic = not call_id.startswith("dental-")
    conv_mode = "telephonic" if is_telephonic else "client-server"

    tracker = MetricsTracker()
    tracker.start_turn()
    print(f"[OK] Job accepted for room: {call_id} mode={conv_mode}")

    phone_number = ""

    # Always create the parent call_metadata row (conversations FK-reference it)
    await upsert_call_metadata(call_id=call_id, phone_number=None)
    asyncio.create_task(upsert_patient_data(
        conversation_id=call_id,
        mode=conv_mode,
    ))

    _seq = [0]

    # ── Connect to Cloud room ────────────────────────────────────────────────────
    logger.info("[%s] Connecting to Cloud room...", call_id)
    await ctx.connect()
    call_start_time = time.monotonic()
    logger.info("[%s] Connected", call_id)

    disconnect_event = asyncio.Event()

    @ctx.room.on("reconnecting")
    def on_reconnecting():
        logger.warning("[%s] Room reconnecting...", call_id)

    @ctx.room.on("reconnected")
    def on_reconnected():
        logger.info("[%s] Room reconnected", call_id)

    @ctx.room.on("disconnected")
    def on_room_disconnect(reason=None):
        logger.info("[%s] Room disconnected (reason=%s)", call_id, reason)
        disconnect_event.set()

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        logger.info("[%s] Participant disconnected: %s", call_id,
                     getattr(participant, "identity", "?"))
        disconnect_event.set()

    # ── Load greeting audio (MP3 file, cached after first load) ─────────────────
    cache_key = "dental_greeting_mp3_frames"
    if cache_key in ctx.proc.userdata:
        greeting_frames = ctx.proc.userdata[cache_key]
        logger.info("[%s] Greeting MP3 from cache (%d frames)", call_id, len(greeting_frames))
    else:
        greeting_frames = await load_greeting_audio()
        if greeting_frames:
            ctx.proc.userdata[cache_key] = greeting_frames

    # ── Build session ────────────────────────────────────────────────────────────
    session = build_session(ctx)

    # ── Session event handlers ───────────────────────────────────────────────────

    @session.on("user_state_changed")
    def on_user_state_changed(ev):
        if ev.new_state == "speaking":
            tracker.on_speech_start()

    @session.on("user_input_transcribed")
    def on_user_speech(ev: UserInputTranscribedEvent):
        tracker.on_first_transcript()
        if ev.is_final:
            logger.info("[%s] User: %s", call_id, ev.transcript)

    @session.on("conversation_item_added")
    def on_conversation_item(ev: ConversationItemAddedEvent):
        item = ev.item
        text = (item.text_content or "").strip()
        if not text:
            return
        role = getattr(item, "role", None)
        role_str = (getattr(role, "value", None) or getattr(role, "name", None) or str(role)).lower()
        logger.info("[%s] [%s] %s", call_id, role_str.upper(), text[:120])

        seq = _seq[0]
        _seq[0] += 1
        asyncio.create_task(save_conversation_turn(
            conversation_id=call_id,
            role=role_str,
            content=text,
            sequence=seq,
            mode=conv_mode,
            phone_number=phone_number or None,
        ))

    @session.on("metrics_collected")
    def on_metrics(ev: MetricsCollectedEvent):
        tracker.on_metrics(ev)

    @session.on("error")
    def on_session_error(err):
        logger.error("[%s] Session error: %s", call_id, err)

    def on_session_close(_ev=None):
        disconnect_event.set()

    session.once("close", on_session_close)

    # ── Start session, play greeting, wait for disconnect ────────────────────────
    try:
        await session.start(
            agent=DentalAgent(
                phone_number=phone_number,
                conversation_id=call_id,
                mode=conv_mode,
            ),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )
        logger.info("[%s] AgentSession started", call_id)
        logger.info("[%s] Playing greeting...", call_id)
        await play_greeting(session, greeting_frames, call_id)

        logger.info("[%s] Waiting for room disconnect...", call_id)
        await disconnect_event.wait()
    finally:
        call_duration_s = time.monotonic() - call_start_time
        logger.info("[%s] Call duration: %.3fs", call_id, call_duration_s)
        asyncio.create_task(update_call_duration(call_id=call_id, duration_seconds=call_duration_s))
        tracker.print_session_summary(call_id=call_id)
        asyncio.create_task(save_evaluation_statistics(
            conversation_id=call_id,
            stats=tracker.get_stats(),
        ))
        asyncio.create_task(analyze_call(call_id=call_id))
        try:
            await asyncio.wait_for(session.aclose(), timeout=5.0)
            logger.info("[%s] Session closed", call_id)
        except Exception as exc:
            logger.warning("[%s] session.aclose() error: %s", call_id, exc)
