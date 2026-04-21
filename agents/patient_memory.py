"""Per-call in-memory store for captured patient profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PatientMemory:
    """Mutable per-call memory of the caller's patient profile."""

    phone_number: str = ""
    conversation_id: str = ""
    mode: str = "client-server"

    # Captured during the call
    name: str = ""
    dob: str = ""
    reason_for_visit: str = ""
    preferred_time: str = ""
    insurance_name: str = ""

    # Booking state
    appointment_booked: bool = False

    def update(
        self,
        name: Optional[str] = None,
        dob: Optional[str] = None,
        reason_for_visit: Optional[str] = None,
        preferred_time: Optional[str] = None,
        insurance_name: Optional[str] = None,
    ) -> None:
        """Store any non-empty values; keep existing on blanks."""
        if name:
            self.name = name.strip()
        if dob:
            self.dob = dob.strip()
        if reason_for_visit:
            self.reason_for_visit = reason_for_visit.strip()
        if preferred_time:
            self.preferred_time = preferred_time.strip()
        if insurance_name:
            self.insurance_name = insurance_name.strip()

    @property
    def has_booking_info(self) -> bool:
        """True when minimum fields for booking are available."""
        return bool(self.name and self.dob and self.reason_for_visit and self.preferred_time)

    @property
    def has_name(self) -> bool:
        return bool(self.name)

    def collected_fields(self) -> list[str]:
        """Return list of field labels that have been captured."""
        fields = []
        if self.name:
            fields.append(f"name={self.name}")
        if self.dob:
            fields.append(f"dob={self.dob}")
        if self.reason_for_visit:
            fields.append(f"reason={self.reason_for_visit}")
        if self.preferred_time:
            fields.append(f"preferred_time={self.preferred_time}")
        if self.insurance_name:
            fields.append(f"insurance={self.insurance_name}")
        return fields

    def as_dict(self) -> dict:
        return {
            "patient_name": self.name,
            "dob": self.dob,
            "reason_for_call": self.reason_for_visit,
            "appointment_requested": self.appointment_booked,
            "preferred_time": self.preferred_time,
            "insurance_name": self.insurance_name,
        }
