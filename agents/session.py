"""Session building, greeting audio loading, and greeting playback."""

import asyncio
import logging
import os
from pathlib import Path

from livekit import rtc
from livekit.agents import AgentSession, JobContext
from livekit.agents.utils.audio import audio_frames_from_file
from livekit.plugins import cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agents.prompts import GREETING_TEXT

logger = logging.getLogger(__name__)

_GREETING_AUDIO_PATH = Path(__file__).parent.parent / "greeting_audio.mp3"

# Cartesia voice: "Helpful Woman" — clear, warm, professional for a dental clinic
_CARTESIA_VOICE_ID = "f786b574-daa5-4673-aa0c-cbe3e8534c02"


def build_session(ctx: JobContext) -> AgentSession:
    """Create an AgentSession wired to prewarmed models from the worker process."""
    tts = cartesia.TTS(
        model="sonic-english",
        voice=_CARTESIA_VOICE_ID,
        api_key=os.environ.get("CARTESIA_API_KEY"),
    )

    # Pre-establish WebSocket to Cartesia to avoid cold-start latency on first TTS.
    # Swallow prewarm failures — the session can still start and TTS will connect
    # on first use. The error will surface in the agent logs.
    try:
        tts.prewarm()
    except Exception as exc:
        logger.warning("TTS prewarm failed (check CARTESIA_API_KEY): %s", exc)

    return AgentSession(
        stt=ctx.proc.userdata["stt"],
        llm=ctx.proc.userdata["llm"],
        tts=tts,
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
        min_endpointing_delay=0.05,
        max_endpointing_delay=0.3,
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=0.5,
        allow_interruptions=True,
    )


async def load_greeting_audio() -> list[rtc.AudioFrame]:
    """Load the pre-recorded greeting MP3 into AudioFrame objects."""
    frames: list[rtc.AudioFrame] = []
    try:
        async for frame in audio_frames_from_file(str(_GREETING_AUDIO_PATH)):
            frames.append(frame)
        logger.info("Greeting audio loaded from MP3 (%d frames)", len(frames))
    except Exception as exc:
        logger.warning("Failed to load greeting MP3: %s — will use live TTS", exc)
    return frames


async def play_greeting(
    session: AgentSession,
    greeting_frames: list[rtc.AudioFrame],
    call_id: str,
) -> None:
    """Play the pre-recorded greeting, falling back to live TTS if needed."""
    try:
        if greeting_frames:
            async def _frame_iter():
                for frame in greeting_frames:
                    yield frame

            await asyncio.wait_for(
                session.say(GREETING_TEXT, audio=_frame_iter(), allow_interruptions=False),
                timeout=30.0,
            )
        else:
            await asyncio.wait_for(
                session.say(GREETING_TEXT, allow_interruptions=False),
                timeout=30.0,
            )
    except asyncio.TimeoutError:
        logger.warning("[%s] Greeting timed out", call_id)
    except Exception as exc:
        logger.warning("[%s] Greeting say() error: %s", call_id, exc)
