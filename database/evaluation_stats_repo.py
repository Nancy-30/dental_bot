"""Repository helper for the evaluation_statistics table."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from database.connection import AsyncSessionLocal
from database.models import IST, EvaluationStatistics, _IST_FMT

logger = logging.getLogger(__name__)


async def save_evaluation_statistics(
    conversation_id: str,
    stats: dict,
) -> Optional[EvaluationStatistics]:
    """Persist one evaluation_statistics row for a completed session. Never raises."""
    if not conversation_id:
        return None

    async with AsyncSessionLocal() as db:
        try:
            now_ist = datetime.now(timezone.utc).astimezone(IST).strftime(_IST_FMT)
            row = EvaluationStatistics(
                conversation_id=conversation_id,
                turns_completed=stats.get("turns_completed"),
                llm_avg_latency=stats.get("llm_avg_latency"),
                tts_avg_latency=stats.get("tts_avg_latency"),
                stt_avg_latency=stats.get("stt_avg_latency"),
                llm_prompt_tokens=stats.get("llm_prompt_tokens"),
                llm_completion_tokens=stats.get("llm_completion_tokens"),
                total_llm_tokens=stats.get("total_llm_tokens"),
                stt_audio_duration_s=stats.get("stt_audio_duration_s"),
                tts_characters=stats.get("tts_characters"),
                tts_audio_duration_s=stats.get("tts_audio_duration_s"),
                llm_cost_inr=stats.get("llm_cost_inr"),
                stt_cost_inr=stats.get("stt_cost_inr"),
                tts_cost_inr=stats.get("tts_cost_inr"),
                total_cost_inr=stats.get("total_cost_inr"),
                created_at_ist=now_ist,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            logger.info(
                "evaluation_statistics: saved id=%s conv=%s turns=%s",
                row.id, conversation_id, stats.get("turns_completed"),
            )
            return row
        except Exception as exc:
            await db.rollback()
            logger.warning(
                "evaluation_statistics: failed to save conv=%s: %s", conversation_id, exc,
            )
            return None
