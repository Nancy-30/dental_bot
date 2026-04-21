"""ABC Dental Clinic AI Receptionist — LiveKit Agent entrypoint.

Usage:
    python agent.py download-files   # pre-download VAD + turn-detector models
    python agent.py dev              # dev mode (connects to LiveKit Cloud)
    python agent.py start            # production mode
"""

import sys
from pathlib import Path

_project_root = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

load_dotenv()

from livekit.agents import WorkerOptions, cli

from config import settings
from utils.logging_setup import silence_noisy_loggers
from agents.prewarm import prewarm
from agents.entrypoint import my_agent

silence_noisy_loggers()

server = WorkerOptions(
    agent_name=settings.AGENT_NAME,
    entrypoint_fnc=my_agent,
    prewarm_fnc=prewarm,
    num_idle_processes=2,
    ws_url=settings.CLOUD_URL,
    api_key=settings.CLOUD_API_KEY,
    api_secret=settings.CLOUD_API_SECRET,
)

if __name__ == "__main__":
    cli.run_app(server)
