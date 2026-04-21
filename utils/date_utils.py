"""Date normalization utilities for patient data."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_SETTINGS = {
    "PREFER_DAY_OF_MONTH": "first",
    "RETURN_AS_TIMEZONE_AWARE": False,
}


def _parse(raw: str) -> Optional[datetime]:
    try:
        import dateparser
        return dateparser.parse(raw, settings=_SETTINGS)
    except Exception as exc:
        logger.debug("dateparser failed for %r: %s", raw, exc)
        return None


def normalize_dob(raw: str) -> str:
    """Convert any DOB string to DD-MM-YYYY. Returns raw string if parsing fails."""
    if not raw:
        return raw
    dt = _parse(raw)
    if dt:
        return dt.strftime("%d-%m-%Y")
    logger.warning("Could not parse DOB %r — storing as-is", raw)
    return raw


def normalize_preferred_time(raw: str) -> str:
    """Convert any preferred time string to DD-MM-YYYY HH:MM:SS. Returns raw if parsing fails."""
    if not raw:
        return raw
    dt = _parse(raw)
    if dt:
        return dt.strftime("%d-%m-%Y %H:%M:%S")
    logger.warning("Could not parse preferred_time %r — storing as-is", raw)
    return raw
