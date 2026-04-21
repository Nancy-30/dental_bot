"""ORM models for the Dental Bot database."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, Integer, String, Text, text

from database.connection import Base

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
_IST_FMT = "%Y-%m-%d %H:%M:%S IST"


def _now_ist_str() -> str:
    return datetime.now(IST).strftime(_IST_FMT)


class CallMetadata(Base):
    """Tracks every agent session lifecycle.

    `call_id` is the LiveKit room name — unique per session.
    Acts as the parent row that conversations and patient_data FK-reference.
    """

    __tablename__ = "call_metadata"

    call_id = Column(String(100), primary_key=True)
    phone_number = Column(String(20), nullable=True, index=True)
    call_duration = Column(Float, nullable=True)
    created_at_ist = Column(String(32), nullable=False, default=_now_ist_str)

    def __repr__(self):
        return f"<CallMetadata(call_id='{self.call_id}', phone='{self.phone_number}')>"


class PatientData(Base):
    """Stores patient profile captured during inbound sessions.

    `mode` distinguishes how the patient reached the bot:
      - 'telephonic'    → phone call; phone_number may be set
      - 'client-server' → web session; phone_number is NULL
    """

    __tablename__ = "patient_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    dob = Column(String(50), nullable=True)
    phone_number = Column(String(20), nullable=True, index=True)
    mode = Column(String(20), nullable=False, default="client-server", server_default="client-server")
    conversation_id = Column(
        String(100),
        ForeignKey("call_metadata.call_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason_for_visit = Column(String(500), nullable=True)
    preferred_time = Column(String(255), nullable=True)
    insurance_name = Column(String(255), nullable=True)
    created_at_ist = Column(String(32), nullable=False, default=_now_ist_str)
    updated_at_ist = Column(String(32), nullable=False, default=_now_ist_str, onupdate=_now_ist_str)

    __table_args__ = (
        Index(
            "uq_patient_data_phone_notnull",
            "phone_number",
            unique=True,
            postgresql_where=text("phone_number IS NOT NULL"),
        ),
    )

    def __repr__(self):
        return f"<PatientData(id={self.id}, name='{self.name}', phone='{self.phone_number}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "dob": self.dob,
            "phone_number": self.phone_number,
            "mode": self.mode,
            "reason_for_visit": self.reason_for_visit,
            "preferred_time": self.preferred_time,
            "insurance_name": self.insurance_name,
            "created_at_ist": self.created_at_ist,
            "updated_at_ist": self.updated_at_ist,
        }


class Appointment(Base):
    """Confirmed appointment booking records.

    Created by book_appointment() tool call. Represents a patient's
    scheduled or requested appointment at the dental clinic.
    """

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String(100),
        ForeignKey("call_metadata.call_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    patient_name = Column(String(255), nullable=False)
    dob = Column(String(50), nullable=True)
    reason_for_visit = Column(String(500), nullable=False)
    preferred_time = Column(String(255), nullable=False)
    insurance_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="scheduled", server_default="scheduled")
    created_at_ist = Column(String(32), nullable=False, default=_now_ist_str)

    def __repr__(self):
        return (
            f"<Appointment(id={self.id}, patient='{self.patient_name}', "
            f"time='{self.preferred_time}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "patient_name": self.patient_name,
            "dob": self.dob,
            "reason_for_visit": self.reason_for_visit,
            "preferred_time": self.preferred_time,
            "insurance_name": self.insurance_name,
            "status": self.status,
            "created_at_ist": self.created_at_ist,
        }


class Conversation(Base):
    """One row per user/assistant turn, grouped by conversation_id."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String(100),
        ForeignKey("call_metadata.call_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone_number = Column(String(20), nullable=True, index=True)
    mode = Column(String(20), nullable=False, default="client-server")
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sequence = Column(Integer, nullable=False)
    created_at_ist = Column(String(32), nullable=False, default=_now_ist_str)

    def __repr__(self):
        return (
            f"<Conversation(id={self.id}, conv='{self.conversation_id}', "
            f"seq={self.sequence}, role='{self.role}')>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "phone_number": self.phone_number,
            "mode": self.mode,
            "role": self.role,
            "content": self.content,
            "sequence": self.sequence,
            "created_at_ist": self.created_at_ist,
        }


class EvaluationStatistics(Base):
    """One row per session with usage and cost stats logged at conversation end."""

    __tablename__ = "evaluation_statistics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String(100),
        ForeignKey("call_metadata.call_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turns_completed = Column(Integer, nullable=True)
    llm_avg_latency = Column(Float, nullable=True)
    tts_avg_latency = Column(Float, nullable=True)
    stt_avg_latency = Column(Float, nullable=True)
    llm_prompt_tokens = Column(Integer, nullable=True)
    llm_completion_tokens = Column(Integer, nullable=True)
    total_llm_tokens = Column(Integer, nullable=True)
    stt_audio_duration_s = Column(Float, nullable=True)
    tts_characters = Column(Integer, nullable=True)
    tts_audio_duration_s = Column(Float, nullable=True)
    llm_cost_inr = Column(Float, nullable=True)
    stt_cost_inr = Column(Float, nullable=True)
    tts_cost_inr = Column(Float, nullable=True)
    total_cost_inr = Column(Float, nullable=True)
    created_at_ist = Column(String(32), nullable=False, default=_now_ist_str)

    def __repr__(self):
        return (
            f"<EvaluationStatistics(id={self.id}, conv='{self.conversation_id}', "
            f"turns={self.turns_completed})>"
        )


class CallAnalysis(Base):
    """LLM-generated post-call analysis with dental-specific structured fields."""

    __tablename__ = "call_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(
        String(100),
        ForeignKey("call_metadata.call_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Call timing
    call_date = Column(String(20), nullable=True)
    call_start_time = Column(String(32), nullable=True)
    call_end_time = Column(String(32), nullable=True)
    duration = Column(Float, nullable=True)

    # Caller identity
    phone_number = Column(String(20), nullable=True)

    # Intent & outcome
    call_intent = Column(String(100), nullable=True)        # "booking", "faq", "reschedule", "emergency", "other"
    appointment_requested = Column(Boolean, nullable=True)
    appointment_confirmed = Column(Boolean, nullable=True)

    # Captured patient fields
    patient_name_captured = Column(String(255), nullable=True)
    dob_captured = Column(String(50), nullable=True)
    reason_for_call = Column(String(500), nullable=True)
    preferred_time_captured = Column(String(255), nullable=True)
    insurance_name_captured = Column(String(255), nullable=True)

    # Q&A quality
    questions_asked = Column(Text, nullable=True)           # JSON array
    num_questions_asked = Column(Integer, nullable=True)
    num_questions_answered = Column(Integer, nullable=True)
    did_bot_fail_to_answer = Column(String(5), nullable=True)
    unanswered_question = Column(Text, nullable=True)

    # Quality signals
    bot_response_accuracy = Column(String(30), nullable=True)
    conversation_status = Column(String(30), nullable=True)
    escalation_triggered = Column(Boolean, nullable=True)
    customer_satisfaction_signal = Column(String(100), nullable=True)
    conversational_issue_detected = Column(Text, nullable=True)

    created_at_ist = Column(String(32), nullable=False, default=_now_ist_str)

    def __repr__(self):
        return (
            f"<CallAnalysis(id={self.id}, call_id='{self.call_id}', "
            f"status='{self.conversation_status}')>"
        )
