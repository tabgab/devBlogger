#!/usr/bin/env python3
"""
DevBlogger - Configuration Tests
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.config.settings import Settings
from src.config.database import DatabaseManager


class TestSettings:
    """Test Settings class functionality."""

    def test_settings_initialization(self):
        """Test settings initialization with defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)

            assert settings.config_dir == Path(temp_dir)
            assert settings.get_window_size() == (1200, 800)
            assert settings.get_default_prompt() is not None

    def test_settings_persistence(self):
        """Test settings persistence to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)

            # Set some values
            settings.set_window_size(1400, 900)
            settings.set_default_prompt("Test prompt")

            # Create new instance
            settings2 = Settings(config_dir=temp_dir)

            assert settings2.get_window_size() == (1400, 900)
            assert settings2.get_default_prompt() == "Test prompt"

    def test_ai_provider_config(self):
        """Test AI provider configuration management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)

            # Test ChatGPT config
            chatgpt_config = {
                "api_key": "test-key",
                "model": "gpt-4",
                "max_tokens": 2000,
                "temperature": 0.7
            }
            settings.set_ai_provider_config("chatgpt", chatgpt_config)

            retrieved = settings.get_ai_provider_config("chatgpt")
            assert retrieved == chatgpt_config

    def test_active_ai_provider(self):
        """Test active AI provider management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)

            # Set active provider
            settings.set_active_ai_provider("gemini")
            assert settings.get_active_ai_provider() == "gemini"

            # Test default
            settings2 = Settings(config_dir=temp_dir)
            assert settings2.get_active_ai_provider() == "gemini"


class TestDatabaseManager:
    """Test DatabaseManager class functionality."""

    def test_database_initialization(self):
        """Test database initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = DatabaseManager(db_path=str(db_path))

            assert db.db_path == str(db_path)
            assert db.is_initialized()

    def test_commit_processing_tracking(self):
        """Test commit processing tracking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = DatabaseManager(db_path=str(db_path))

            # Mark commit as processed
            db.mark_commit_processed("test/repo", "abc123", "chatgpt")

            # Check if processed
            assert db.is_commit_processed("test/repo", "abc123") == True
            assert db.is_commit_processed("test/repo", "def456") == False

    def test_processed_commits_query(self):
        """Test querying processed commits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = DatabaseManager(db_path=str(db_path))

            # Add some processed commits
            db.mark_commit_processed("repo1", "abc123", "chatgpt")
            db.mark_commit_processed("repo1", "def456", "gemini")
            db.mark_commit_processed("repo2", "ghi789", "chatgpt")

            # Query processed commits
            processed = db.get_processed_commits("repo1")
            assert len(processed) == 2
            assert "abc123" in processed
            assert "def456" in processed

    def test_database_stats(self):
        """Test database statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = DatabaseManager(db_path=str(db_path))

            # Add test data
            db.mark_commit_processed("repo1", "abc123", "chatgpt")
            db.mark_commit_processed("repo2", "def456", "gemini")

            stats = db.get_database_stats()
            assert stats["total_processed_commits"] == 2
            assert stats["unique_repositories"] == 2
            assert stats["unique_providers"] == 2


def test_settings_singleton_behavior():
    """Test that Settings behaves as a singleton within the same process."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings1 = Settings(config_dir=temp_dir)
        settings2 = Settings(config_dir=temp_dir)

        # Both should reference the same configuration
        settings1.set_window_size(1000, 600)
        assert settings2.get_window_size() == (1000, 600)


def test_database_connection_cleanup():
    """Test database connection cleanup."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DatabaseManager(db_path=str(db_path))

        # Ensure connection is properly closed
        db.close()
        assert not db.is_initialized()
