"""POST /token — generate LiveKit access tokens."""

import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from livekit.api import AccessToken, VideoGrants, RoomAgentDispatch, RoomConfiguration

from config import settings

logger = logging.getLogger("backend")
router = APIRouter()


class TokenRequest(BaseModel):
    room_name: str = ""
    participant_name: str = ""


class TokenResponse(BaseModel):
    token: str
    room_name: str
    participant_name: str
    livekit_url: str


@router.post("/token", response_model=TokenResponse)
async def create_token(request: TokenRequest) -> TokenResponse:
    """Generate a LiveKit access token for a participant to join a room."""
    room_name = request.room_name.strip() or f"dental-{uuid.uuid4().hex[:8]}"
    participant_name = request.participant_name.strip() or f"patient-{uuid.uuid4().hex[:6]}"

    try:
        token = (
            AccessToken(
                api_key=settings.CLOUD_API_KEY,
                api_secret=settings.CLOUD_API_SECRET,
            )
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .with_identity(participant_name)
            .with_name(participant_name)
            .with_room_config(
                RoomConfiguration(
                    agents=[RoomAgentDispatch(agent_name=settings.AGENT_NAME)],
                )
            )
            .to_jwt()
        )
    except Exception as exc:
        logger.error("Token generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate LiveKit token")

    return TokenResponse(
        token=token,
        room_name=room_name,
        participant_name=participant_name,
        livekit_url=settings.CLOUD_URL,
    )
