"""Silence noisy third-party loggers."""

import logging

_NOISY_LOGGERS = (
    "livekit", "livekit.rtc", "livekit.agents",
    "livekit.plugins.cartesia", "livekit.plugins.deepgram",
    "livekit.plugins.openai", "livekit.plugins.silero",
    "livekit.plugins.turn_detector",
    "httpx", "httpcore", "openai", "grpc",
)


def silence_noisy_loggers() -> None:
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
