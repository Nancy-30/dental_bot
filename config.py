"""Central configuration for ABC Dental Clinic Bot."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LiveKit Cloud ──────────────────────────────────────────────────────────
    CLOUD_URL: str = "wss://your-project.livekit.cloud"
    CLOUD_API_KEY: str = "devkey"
    CLOUD_API_SECRET: str = "secret"

    # ── AI Providers ───────────────────────────────────────────────────────────
    DEEPGRAM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""          # LLM + post-call analysis
    CARTESIA_API_KEY: str = ""        # TTS

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dental_bot"

    # ── App Meta ───────────────────────────────────────────────────────────────
    APP_NAME: str = "ABC Dental Clinic AI Receptionist"
    AGENT_NAME: str = "dental-bot"

    # ── Clinic static info ─────────────────────────────────────────────────────
    CLINIC_NAME: str = "ABC Dental Clinic"
    CLINIC_PHONE: str = "+1-555-000-1234"
    CLINIC_ADDRESS: str = "123 Main Street, Suite 200, New York, NY 10001"
    CLINIC_HOURS: str = "Monday to Friday, 9 AM to 6 PM"
    CLINIC_INSURANCE: str = "Delta Dental, Cigna, Aetna, MetLife, Guardian, and most PPO plans"


settings = Settings()
