#!/usr/bin/env python3
"""
DevBlogger - Blog Generation Tests
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.blog.generator import BlogGenerator, BlogGenerationError
from src.blog.storage import BlogStorageManager, BlogEntry, BlogStorageError
from src.blog.manager import BlogManager
from src.ai.manager import DevBloggerAIProviderManager
from src.ai.base import AIResponse
from src.github.models import GitHubCommit, GitHubUser
from src.config.settings import Settings
from src.config.database import DatabaseManager


class TestBlogGenerator:
    """Test Blog Generator functionality."""

    def test_blog_generator_initialization(self):
        """Test blog generator initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            generator = BlogGenerator(ai_manager, settings, db)

            assert generator.ai_manager == ai_manager
            assert generator.settings == settings
            assert generator.database == db

    def test_commit_data_preparation(self):
        """Test commit data preparation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            generator = BlogGenerator(ai_manager, settings, db)

            # Create test commits
            commits = [
                GitHubCommit(
                    sha="abc123",
                    message="Add new feature",
                    author=GitHubUser(name="Test Author", email="test@example.com"),
                    committer=GitHubUser(name="Test Author", email="test@example.com"),
                    date=datetime.now(),
                    files=[{"filename": "test.py", "status": "modified", "additions": 10, "deletions": 2}]
                )
            ]

            commit_data = generator._prepare_commit_data(commits, "test/repo")

            assert "Repository: test/repo" in commit_data
            assert "abc123" in commit_data
            assert "Add new feature" in commit_data

    def test_blog_entry_formatting(self):
        """Test blog entry formatting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            generator = BlogGenerator(ai_manager, settings, db)

            # Create test data
            ai_content = "# Test Blog Entry\n\nThis is a test blog entry content."
            commits = [GitHubCommit(sha="abc123", message="Test", author=GitHubUser(name="Test"), committer=GitHubUser(name="Test"), date=datetime.now())]

            formatted = generator._format_blog_entry(ai_content, commits, "test/repo", "chatgpt", "gpt-4")

            assert "---" in formatted  # Frontmatter
            assert "title:" in formatted
            assert "repository: test/repo" in formatted
            assert "Test Blog Entry" in formatted

    def test_content_cleaning(self):
        """Test AI content cleaning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            generator = BlogGenerator(ai_manager, settings, db)

            # Test content with excessive newlines
            messy_content = "Line 1\n\n\n\n\nLine 2"
            cleaned = generator._clean_ai_content(messy_content)

            assert cleaned == "Line 1\n\nLine 2"

    def test_commit_validation(self):
        """Test commit validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            generator = BlogGenerator(ai_manager, settings, db)

            # Test with no commits
            issues = generator.validate_commits_for_generation([])
            assert "No commits selected" in issues

            # Test with valid commits
            commits = [
                GitHubCommit(
                    sha="abc123",
                    message="Add feature",
                    author=GitHubUser(name="Test"),
                    committer=GitHubUser(name="Test"),
                    date=datetime.now()
                )
            ]

            issues = generator.validate_commits_for_generation(commits)
            assert len(issues) == 0  # No issues with valid commits

    def test_generation_stats(self):
        """Test generation statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            generator = BlogGenerator(ai_manager, settings, db)

            commits = [
                GitHubCommit(
                    sha="abc123",
                    message="Add feature",
                    author=GitHubUser(name="Author 1"),
                    committer=GitHubUser(name="Author 1"),
                    date=datetime.now(),
                    files=[{"filename": "file1.py", "additions": 10, "deletions": 2}]
                ),
                GitHubCommit(
                    sha="def456",
                    message="Fix bug",
                    author=GitHubUser(name="Author 2"),
                    committer=GitHubUser(name="Author 2"),
                    date=datetime.now(),
                    files=[{"filename": "file2.py", "additions": 5, "deletions": 1}]
                )
            ]

            stats = generator.get_generation_stats(commits)

            assert stats["total_commits"] == 2
            assert len(stats["authors"]) == 2
            assert stats["additions"] == 15
            assert stats["deletions"] == 3


class TestBlogStorageManager:
    """Test Blog Storage Manager functionality."""

    def test_storage_manager_initialization(self):
        """Test storage manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            storage = BlogStorageManager(settings)

            assert storage.entries_dir == settings.get_generated_entries_dir()
            assert storage.index_file.exists()

    def test_blog_entry_creation(self):
        """Test blog entry creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            storage = BlogStorageManager(settings)

            # Create test entry
            entry = BlogEntry(
                filepath=Path(temp_dir) / "test.md",
                repository="test/repo",
                commit_count=5,
                provider="chatgpt",
                model="gpt-4",
                generated_at=datetime.now()
            )

            entry_id = storage.add_entry(entry)

            assert entry_id in storage.entries
            assert storage.get_entry(entry_id) == entry

    def test_entry_search(self):
        """Test entry search functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            storage = BlogStorageManager(settings)

            # Add test entries
            entry1 = BlogEntry(
                filepath=Path(temp_dir) / "test1.md",
                repository="repo1",
                commit_count=1,
                provider="chatgpt",
                model="gpt-4",
                generated_at=datetime.now(),
                title="Test Entry 1",
                tags=["feature", "ui"]
            )

            entry2 = BlogEntry(
                filepath=Path(temp_dir) / "test2.md",
                repository="repo2",
                commit_count=2,
                provider="gemini",
                model="gemini-pro",
                generated_at=datetime.now(),
                title="Test Entry 2",
                tags=["bugfix", "backend"]
            )

            storage.add_entry(entry1)
            storage.add_entry(entry2)

            # Test search
            results = storage.search_entries("feature")
            assert len(results) == 1
            assert results[0].title == "Test Entry 1"

            results = storage.search_entries("repo2")
            assert len(results) == 1
            assert results[0].repository == "repo2"

    def test_entry_filtering(self):
        """Test entry filtering by repository and provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            storage = BlogStorageManager(settings)

            # Add test entries
            entry1 = BlogEntry(
                filepath=Path(temp_dir) / "test1.md",
                repository="repo1",
                commit_count=1,
                provider="chatgpt",
                model="gpt-4",
                generated_at=datetime.now()
            )

            entry2 = BlogEntry(
                filepath=Path(temp_dir) / "test2.md",
                repository="repo1",
                commit_count=2,
                provider="gemini",
                model="gemini-pro",
                generated_at=datetime.now()
            )

            storage.add_entry(entry1)
            storage.add_entry(entry2)

            # Filter by repository
            repo_entries = storage.get_entries_by_repository("repo1")
            assert len(repo_entries) == 2

            # Filter by provider
            chatgpt_entries = storage.get_entries_by_provider("chatgpt")
            assert len(chatgpt_entries) == 1
            assert chatgpt_entries[0].provider == "chatgpt"

    def test_storage_stats(self):
        """Test storage statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            storage = BlogStorageManager(settings)

            # Add test entries
            entry1 = BlogEntry(
                filepath=Path(temp_dir) / "test1.md",
                repository="repo1",
                commit_count=1,
                provider="chatgpt",
                model="gpt-4",
                generated_at=datetime.now()
            )

            entry2 = BlogEntry(
                filepath=Path(temp_dir) / "test2.md",
                repository="repo2",
                commit_count=2,
                provider="chatgpt",
                model="gpt-4",
                generated_at=datetime.now()
            )

            storage.add_entry(entry1)
            storage.add_entry(entry2)

            stats = storage.get_storage_stats()

            assert stats["total_entries"] == 2
            assert stats["repositories"]["repo1"] == 1
            assert stats["repositories"]["repo2"] == 1
            assert stats["providers"]["chatgpt"] == 2


class TestBlogManager:
    """Test Blog Manager functionality."""

    def test_blog_manager_initialization(self):
        """Test blog manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            manager = BlogManager(ai_manager, settings, db)

            assert manager.ai_manager == ai_manager
            assert manager.settings == settings
            assert manager.database == db
            assert manager.generator is not None
            assert manager.storage is not None

    @patch('src.blog.generator.BlogGenerator.generate_blog_entry')
    def test_blog_generation_workflow(self, mock_generate):
        """Test complete blog generation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            manager = BlogManager(ai_manager, settings, db)

            # Mock the generator response
            mock_response = AIResponse(
                text="Generated blog content",
                model="gpt-4",
                provider="chatgpt",
                tokens_used=150
            )
            mock_generate.return_value = {
                "success": True,
                "content": "Generated content",
                "metadata": {
                    "provider": "chatgpt",
                    "model": "gpt-4",
                    "generated_at": datetime.now().isoformat()
                }
            }

            # Create test commits
            commits = [
                GitHubCommit(
                    sha="abc123",
                    message="Add feature",
                    author=GitHubUser(name="Test Author"),
                    committer=GitHubUser(name="Test Author"),
                    date=datetime.now()
                )
            ]

            # Generate blog
            result = manager.generate_blog_from_commits(
                commits=commits,
                repository="test/repo"
            )

            assert result["success"] == True
            assert "entry_id" in result
            assert "filepath" in result

    def test_generation_stats(self):
        """Test generation statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            manager = BlogManager(ai_manager, settings, db)

            commits = [
                GitHubCommit(
                    sha="abc123",
                    message="Add feature",
                    author=GitHubUser(name="Author 1"),
                    committer=GitHubUser(name="Author 1"),
                    date=datetime.now(),
                    files=[{"filename": "file1.py", "additions": 10, "deletions": 2}]
                )
            ]

            stats = manager.get_generation_stats(commits)

            assert stats["total_commits"] == 1
            assert stats["additions"] == 10
            assert stats["deletions"] == 2

    def test_commit_validation(self):
        """Test commit validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            manager = BlogManager(ai_manager, settings, db)

            # Test with no commits
            issues = manager.validate_commits([])
            assert "No commits selected" in issues

            # Test with valid commits
            commits = [
                GitHubCommit(
                    sha="abc123",
                    message="Add feature",
                    author=GitHubUser(name="Test"),
                    committer=GitHubUser(name="Test"),
                    date=datetime.now()
                )
            ]

            issues = manager.validate_commits(commits)
            assert len(issues) == 0

    def test_supported_providers(self):
        """Test supported providers listing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            manager = BlogManager(ai_manager, settings, db)

            providers = manager.get_supported_providers()
            assert isinstance(providers, list)
            assert len(providers) <= 3  # At most 3 providers

    def test_storage_operations(self):
        """Test storage operations through manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(config_dir=temp_dir)
            db = DatabaseManager(db_path=str(Path(temp_dir) / "test.db"))
            ai_manager = DevBloggerAIProviderManager(settings)

            manager = BlogManager(ai_manager, settings, db)

            # Test getting all entries (should be empty initially)
            entries = manager.get_blog_entries()
            assert len(entries) == 0

            # Test storage stats
            stats = manager.get_storage_stats()
            assert stats["total_entries"] == 0


def test_blog_entry_from_file():
    """Test creating blog entry from file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test markdown file
        content = """---
title: Test Blog Entry
date: 2024-01-01
repository: test/repo
commit_count: 5
generated_by: chatgpt (gpt-4)
generated_at: 2024-01-01T12:00:00
tags: [feature, ui]
---

# Test Content

This is test blog content.
"""
        filepath = Path(temp_dir) / "test.md"
        filepath.write_text(content)

        # Create entry from file
        entry = BlogEntry.from_file(filepath)

        assert entry.title == "Test Blog Entry"
        assert entry.repository == "test/repo"
        assert entry.commit_count == 5
        assert entry.provider == "chatgpt"
        assert entry.model == "gpt-4"
        assert entry.tags == ["feature", "ui"]


def test_blog_entry_serialization():
    """Test blog entry serialization."""
    entry = BlogEntry(
        filepath=Path("/test/path.md"),
        repository="test/repo",
        commit_count=3,
        provider="gemini",
        model="gemini-pro",
        generated_at=datetime.now(),
        title="Test Entry",
        tags=["test", "blog"]
    )

    # Test to_dict
    data = entry.to_dict()
    assert data["repository"] == "test/repo"
    assert data["commit_count"] == 3
    assert data["provider"] == "gemini"
    assert data["title"] == "Test Entry"
    assert data["tags"] == ["test", "blog"]

    # Test from_dict
    entry2 = BlogEntry.from_dict(data)
    assert entry2.repository == entry.repository
    assert entry2.commit_count == entry.commit_count
    assert entry2.provider == entry.provider
    assert entry2.title == entry.title
    assert entry2.tags == entry.tags
