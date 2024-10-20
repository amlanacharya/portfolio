from fastrtc import audio_to_bytes
from openai import OpenAI

from realtime_phone_agents.stt.base import STTModel
from realtime_phone_agents.stt.runpod.faster_whisper.options import (
    FasterWhisperSTTOptions,
)


class FasterWhisperSTT(STTModel):
    """Speech-to-Text model using Faster Whisper."""

    def __init__(self, options: FasterWhisperSTTOptions | None = None):
        self.options = options or FasterWhisperSTTOptions()
        self.client = OpenAI(
            api_key="",
            base_url=f"{self.options.api_url}/v1",
        )

    def set_model(self, model: str) -> None:
        self.options.model = model

    def set_api_url(self, api_url: str) -> None:
        self.options.api_url = api_url

    def stt(self, audio_data: bytes) -> str:
        """Convert speech audio to text."""
        response = self.client.audio.transcriptions.create(
            file=("audio.wav", audio_to_bytes(audio_data)),
            model=self.options.model,
            response_format="verbose_json",
        )
        return response.text
