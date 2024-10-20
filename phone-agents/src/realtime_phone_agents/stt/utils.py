from realtime_phone_agents.stt.base import STTModel
from realtime_phone_agents.stt.groq.whisper import WhisperGroqSTT
from realtime_phone_agents.stt.local.moonshine import MoonshineSTT
from realtime_phone_agents.stt.runpod import FasterWhisperSTT


def get_stt_model(model: str) -> STTModel:
    """Get the STT model based on the model name."""
    if model == "whisper-groq":
        return WhisperGroqSTT()
    elif model == "faster-whisper":
        return FasterWhisperSTT()
    elif model == "moonshine":
        return MoonshineSTT()
    else:
        raise ValueError(f"Invalid model: {model}")
