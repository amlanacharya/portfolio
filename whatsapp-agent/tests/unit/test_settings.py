"""Unit tests for the Settings configuration."""

import os
from unittest.mock import patch

import pytest


def test_settings_loads_from_env():
    """Settings should load all required fields from environment variables."""
    env_vars = {
        "GROQ_API_KEY": "test-groq-key",
        "ELEVENLABS_API_KEY": "test-eleven-key",
        "ELEVENLABS_VOICE_ID": "test-voice-id",
        "TOGETHER_API_KEY": "test-together-key",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "test-qdrant-key",
        "WHATSAPP_PHONE_NUMBER_ID": "123",
        "WHATSAPP_TOKEN": "test-token",
        "WHATSAPP_VERIFY_TOKEN": "test-verify",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        from ai_companion.settings import Settings

        s = Settings()
        assert s.GROQ_API_KEY == "test-groq-key"
        assert s.ELEVENLABS_API_KEY == "test-eleven-key"
        assert s.QDRANT_URL == "http://localhost:6333"


def test_settings_defaults():
    """Settings should have sensible defaults for optional fields."""
    env_vars = {
        "GROQ_API_KEY": "x",
        "ELEVENLABS_API_KEY": "x",
        "ELEVENLABS_VOICE_ID": "x",
        "TOGETHER_API_KEY": "x",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "x",
        "WHATSAPP_PHONE_NUMBER_ID": "x",
        "WHATSAPP_TOKEN": "x",
        "WHATSAPP_VERIFY_TOKEN": "x",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        from ai_companion.settings import Settings

        s = Settings()
        assert s.MEMORY_TOP_K == 3
        assert s.ROUTER_MESSAGES_TO_ANALYZE == 3
        assert s.TOTAL_MESSAGES_SUMMARY_TRIGGER == 20
        assert s.TOTAL_MESSAGES_AFTER_SUMMARY == 5
        assert "llama" in s.TEXT_MODEL_NAME
        assert "whisper" in s.STT_MODEL_NAME
