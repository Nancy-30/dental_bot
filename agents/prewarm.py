"""Prewarm — load heavy models once per worker process."""

from livekit.agents import JobProcess
from livekit.plugins import deepgram, openai, silero


def prewarm(proc: JobProcess) -> None:
    """Load VAD, STT, and LLM into proc.userdata before any session starts."""
    print("PREWARMING MODELS...")

    proc.userdata["vad"] = silero.VAD.load()

    proc.userdata["stt"] = deepgram.STT(
        model="nova-2",
        language="en-US",
    )

    proc.userdata["llm"] = openai.LLM(
        model="gpt-4o-mini",
        temperature=0.1,
    )

    print("Prewarm complete: VAD + STT (Deepgram Nova-2) + LLM (GPT-4o-mini) ready")
