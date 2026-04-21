"""Environment variable setup."""

import os


def set_openai_key() -> None:
    """Expose OPENAI_API_KEY to the environment for livekit-plugins-openai."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        os.environ["OPENAI_API_KEY"] = key
