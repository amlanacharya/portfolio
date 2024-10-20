from pydantic import BaseModel, Field

from realtime_phone_agents.config import settings


class FasterWhisperSTTOptions(BaseModel):
    """Faster Whisper STT options with defaults from Pydantic settings."""

    api_url: str = Field(
        default_factory=lambda: settings.faster_whisper.api_url,
        description="Orpheus TTS API URL",
    )
    model: str = Field(
        default_factory=lambda: settings.faster_whisper.model,
        description="Faster Whisper Model",
    )
