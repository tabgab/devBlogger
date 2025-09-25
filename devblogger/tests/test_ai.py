#!/usr/bin/env python3
"""
DevBlogger - AI Integration Tests
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.ai.manager import DevBloggerAIProviderManager
from src.ai.base import AIResponse
from src.config.settings import Settings
from src.config.database import DatabaseManager


class TestAIProviderManager:
    """Test AI Provider Manager functionality."""

    def test_provider_manager_initialization(self):
        """Test AI provider manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))

            manager = DevBloggerAIProviderManager(settings)

            assert len(manager.providers) == 3  # ChatGPT, Gemini, Ollama
            assert manager.active_provider is not None

    def test_provider_registration(self):
        """Test provider registration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            # Check that all expected providers are registered
            provider_names = list(manager.providers.keys())
            assert "chatgpt" in provider_names
            assert "gemini" in provider_names
            assert "ollama" in provider_names

    def test_active_provider_management(self):
        """Test active provider management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            # Set active provider
            manager.set_active_provider("gemini")
            assert manager.active_provider == "gemini"

            # Get active provider instance
            active = manager.get_active_provider()
            assert active is not None
            assert active.name == "gemini"

    def test_provider_status(self):
        """Test provider status reporting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            status = manager.get_provider_status_summary()
            assert "total_providers" in status
            assert "configured_providers" in status
            assert "working_providers" in status
            assert status["total_providers"] == 3

    def test_provider_capabilities(self):
        """Test provider capabilities reporting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            capabilities = manager.get_provider_capabilities("chatgpt")
            assert "name" in capabilities
            assert "configured" in capabilities
            assert "available" in capabilities

    def test_recommended_provider(self):
        """Test recommended provider selection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            # Should return a provider name
            recommended = manager.get_recommended_provider()
            assert recommended is not None
            assert recommended in manager.providers


class TestAIResponse:
    """Test AI Response class."""

    def test_ai_response_creation(self):
        """Test AI response creation."""
        response = AIResponse(
            text="Test response",
            model="gpt-4",
            provider="chatgpt",
            tokens_used=100,
            finish_reason="stop"
        )

        assert response.text == "Test response"
        assert response.model == "gpt-4"
        assert response.provider == "chatgpt"
        assert response.tokens_used == 100
        assert response.finish_reason == "stop"
        assert response.metadata == {}

    def test_ai_response_metadata(self):
        """Test AI response with metadata."""
        metadata = {"test": "value", "number": 42}
        response = AIResponse(
            text="Test",
            model="gpt-4",
            provider="chatgpt",
            metadata=metadata
        )

        assert response.metadata == metadata


class TestAIProviderIntegration:
    """Test AI provider integration with mocking."""

    @patch('src.ai.openai_client.OPENAI_AVAILABLE', True)
    @patch('src.ai.gemini_client.GENAI_AVAILABLE', True)
    def test_provider_initialization_with_mocked_dependencies(self):
        """Test provider initialization with mocked dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            # All providers should be registered
            assert len(manager.providers) == 3

            # Test each provider exists
            chatgpt = manager.get_provider("chatgpt")
            gemini = manager.get_provider("gemini")
            ollama = manager.get_provider("ollama")

            assert chatgpt is not None
            assert gemini is not None
            assert ollama is not None

    def test_provider_validation(self):
        """Test provider validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            # Test validation of all providers
            validation = manager.validate_all_providers()
            assert isinstance(validation, dict)
            assert len(validation) == 3

    def test_provider_switching(self):
        """Test switching between providers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            # Switch to different provider
            manager.set_active_provider("ollama")
            assert manager.active_provider == "ollama"

            # Switch back
            manager.set_active_provider("chatgpt")
            assert manager.active_provider == "chatgpt"

    def test_error_handling_invalid_provider(self):
        """Test error handling for invalid provider operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            # Test invalid provider name
            with pytest.raises(ValueError):
                manager.set_active_provider("invalid_provider")

            # Test getting non-existent provider
            provider = manager.get_provider("nonexistent")
            assert provider is None

    def test_provider_diagnostics(self):
        """Test provider diagnostics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            manager = DevBloggerAIProviderManager(settings)

            diagnostics = manager.get_provider_diagnostics()
            assert "summary" in diagnostics
            assert "configurations" in diagnostics
            assert "capabilities" in diagnostics
            assert "issues" in diagnostics


def test_ai_response_equality():
    """Test AI response equality."""
    response1 = AIResponse("test", "gpt-4", "chatgpt")
    response2 = AIResponse("test", "gpt-4", "chatgpt")
    response3 = AIResponse("different", "gpt-4", "chatgpt")

    # Same content should be equal
    assert response1.text == response2.text
    assert response1.model == response2.model
    assert response1.provider == response2.provider

    # Different content should not be equal
    assert response1.text != response3.text


def test_ai_provider_manager_singleton_behavior():
    """Test that AI provider manager behaves consistently."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = Settings(config_dir=temp_dir)

        manager1 = DevBloggerAIProviderManager(settings)
        manager2 = DevBloggerAIProviderManager(settings)

        # Both should have same providers
        assert len(manager1.providers) == len(manager2.providers)
        assert set(manager1.providers.keys()) == set(manager2.providers.keys())
