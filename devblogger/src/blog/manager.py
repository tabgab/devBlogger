#!/usr/bin/env python3
"""
DevBlogger - Blog Management Interface
"""

import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple
from pathlib import Path

from .generator import BlogGenerator, BlogGenerationError
from .storage import BlogStorageManager, BlogEntry, BlogStorageError
from ..ai.manager import DevBloggerAIProviderManager
from ..github.models import GitHubCommit
from ..config.settings import Settings
from ..config.database import DatabaseManager


class BlogManager:
    """Main blog management interface."""

    def __init__(
        self,
        ai_manager: DevBloggerAIProviderManager,
        settings: Settings,
        database: DatabaseManager
    ):
        """Initialize blog manager."""
        self.ai_manager = ai_manager
        self.settings = settings
        self.database = database
        self.logger = logging.getLogger(__name__)

        # Core components
        self.generator = BlogGenerator(ai_manager, settings, database)
        self.storage = BlogStorageManager(settings)

        # Event callbacks
        self.on_generation_start: Optional[Callable] = None
        self.on_generation_complete: Optional[Callable] = None
        self.on_generation_error: Optional[Callable] = None
        self.on_save_complete: Optional[Callable] = None

    def generate_blog_from_commits(
        self,
        commits: List[GitHubCommit],
        repository: str,
        prompt: Optional[str] = None,
        provider: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        custom_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a blog entry from commits."""
        try:
            # Validate inputs
            issues = self.generator.validate_commits_for_generation(commits)
            if issues:
                self.logger.warning(f"Validation issues: {issues}")

            # Notify start
            if self.on_generation_start:
                self.on_generation_start(repository, len(commits))

            # Generate blog entry
            result = self.generator.generate_blog_entry(
                commits=commits,
                repository=repository,
                prompt=prompt,
                provider=provider,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Save to storage
            if result["success"]:
                filepath = self.generator.save_blog_entry(
                    result["content"],
                    repository,
                    custom_filename
                )

                # Create blog entry object
                entry = BlogEntry(
                    filepath=filepath,
                    repository=repository,
                    commit_count=len(commits),
                    provider=result["metadata"]["provider"],
                    model=result["metadata"]["model"],
                    generated_at=datetime.fromisoformat(result["metadata"]["generated_at"])
                )

                # Add to storage
                entry_id = self.storage.add_entry(entry)

                result["entry_id"] = entry_id
                result["filepath"] = str(filepath)

            # Notify completion
            if self.on_generation_complete and result["success"]:
                self.on_generation_complete(result)

            return result

        except BlogGenerationError as e:
            error_result = {
                "success": False,
                "error": str(e),
                "repository": repository,
                "commit_count": len(commits)
            }

            if self.on_generation_error:
                self.on_generation_error(error_result)

            return error_result

    def regenerate_blog_entry(
        self,
        entry_id: str,
        commits: List[GitHubCommit],
        repository: str,
        new_provider: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Regenerate an existing blog entry with a different provider."""
        try:
            # Get existing entry
            existing_entry = self.storage.get_entry(entry_id)
            if not existing_entry:
                raise BlogGenerationError(f"Blog entry {entry_id} not found")

            # Read existing content
            if not existing_entry.filepath.exists():
                raise BlogGenerationError(f"Blog entry file not found: {existing_entry.filepath}")

            with open(existing_entry.filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Generate new content
            result = self.generator.regenerate_blog_entry(
                commits=commits,
                repository=repository,
                original_content=original_content,
                new_provider=new_provider,
                prompt=prompt
            )

            if result["success"]:
                # Save updated content
                filepath = self.generator.save_blog_entry(
                    result["content"],
                    repository,
                    existing_entry.filepath.stem
                )

                # Update entry
                existing_entry.filepath = filepath
                existing_entry.provider = new_provider
                existing_entry.generated_at = datetime.now()

                self.storage.update_entry(entry_id, {
                    "filepath": str(filepath),
                    "provider": new_provider,
                    "generated_at": datetime.now()
                })

                result["entry_id"] = entry_id
                result["filepath"] = str(filepath)

            return result

        except Exception as e:
            self.logger.error(f"Error regenerating blog entry: {e}")
            return {
                "success": False,
                "error": str(e),
                "entry_id": entry_id
            }

    def get_blog_entries(
        self,
        repository: Optional[str] = None,
        provider: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[BlogEntry]:
        """Get blog entries with optional filtering."""
        try:
            entries = self.storage.get_all_entries()

            # Apply filters
            if repository:
                entries = [e for e in entries if e.repository == repository]

            if provider:
                entries = [e for e in entries if e.provider == provider]

            # Sort by date (newest first)
            entries.sort(key=lambda x: x.generated_at, reverse=True)

            # Apply pagination
            if offset:
                entries = entries[offset:]

            if limit:
                entries = entries[:limit]

            return entries

        except Exception as e:
            self.logger.error(f"Error getting blog entries: {e}")
            return []

    def get_blog_entry(self, entry_id: str) -> Optional[BlogEntry]:
        """Get a specific blog entry."""
        return self.storage.get_entry(entry_id)

    def update_blog_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a blog entry."""
        try:
            return self.storage.update_entry(entry_id, updates)
        except Exception as e:
            self.logger.error(f"Error updating blog entry {entry_id}: {e}")
            return False

    def delete_blog_entry(self, entry_id: str) -> bool:
        """Delete a blog entry."""
        try:
            return self.storage.delete_entry(entry_id)
        except Exception as e:
            self.logger.error(f"Error deleting blog entry {entry_id}: {e}")
            return False

    def get_generation_stats(self, commits: List[GitHubCommit]) -> Dict[str, Any]:
        """Get statistics about commits for generation."""
        return self.generator.get_generation_stats(commits)

    def validate_commits(self, commits: List[GitHubCommit]) -> List[str]:
        """Validate commits for blog generation."""
        return self.generator.validate_commits_for_generation(commits)

    def estimate_generation_time(self, commits: List[GitHubCommit], provider: str) -> Dict[str, Any]:
        """Estimate generation time."""
        return self.generator.estimate_generation_time(commits, provider)

    def get_supported_providers(self) -> List[str]:
        """Get list of supported AI providers."""
        return self.generator.get_supported_providers()

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self.storage.get_storage_stats()

    def export_entries(self, export_path: Path, format: str = "json") -> Path:
        """Export all blog entries."""
        return self.storage.export_entries(export_path, format)

    def cleanup_old_entries(self, days_old: int = 90) -> int:
        """Clean up old blog entries."""
        return self.storage.cleanup_old_entries(days_old)

    def validate_storage(self) -> Dict[str, Any]:
        """Validate storage integrity."""
        return self.storage.validate_storage()

    def repair_storage(self) -> Dict[str, Any]:
        """Repair storage issues."""
        return self.storage.repair_storage()

    def search_entries(self, query: str) -> List[BlogEntry]:
        """Search blog entries."""
        return self.storage.search_entries(query)

    def get_entries_by_repository(self, repository: str) -> List[BlogEntry]:
        """Get entries for a specific repository."""
        return self.storage.get_entries_by_repository(repository)

    def get_entries_by_provider(self, provider: str) -> List[BlogEntry]:
        """Get entries by AI provider."""
        return self.storage.get_entries_by_provider(provider)

    def get_entries_by_date_range(self, start_date: datetime, end_date: datetime) -> List[BlogEntry]:
        """Get entries within a date range."""
        return self.storage.get_entries_by_date_range(start_date, end_date)

    def bulk_generate_blogs(
        self,
        repository_commits_map: Dict[str, List[GitHubCommit]],
        prompt: Optional[str] = None,
        provider: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate blog entries for multiple repositories."""
        results = {
            "total_repositories": len(repository_commits_map),
            "successful": 0,
            "failed": 0,
            "results": {}
        }

        for repository, commits in repository_commits_map.items():
            try:
                result = self.generate_blog_from_commits(
                    commits=commits,
                    repository=repository,
                    prompt=prompt,
                    provider=provider,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                results["results"][repository] = result

                if result["success"]:
                    results["successful"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                results["results"][repository] = {
                    "success": False,
                    "error": str(e)
                }
                results["failed"] += 1

        return results

    def get_recent_entries(self, limit: int = 10) -> List[BlogEntry]:
        """Get most recent blog entries."""
        entries = self.get_blog_entries(limit=limit)
        return entries[:limit]

    def get_popular_repositories(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most popular repositories by entry count."""
        stats = self.get_storage_stats()
        repositories = stats.get("repositories", {})

        # Sort by count
        sorted_repos = sorted(repositories.items(), key=lambda x: x[1], reverse=True)
        return sorted_repos[:limit]

    def get_provider_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics by AI provider."""
        stats = self.get_storage_stats()
        return stats.get("providers", {})

    def get_default_prompt(self) -> str:
        """Get the default prompt for blog generation."""
        return self.generator._get_default_prompt()

    def set_default_prompt(self, prompt: str):
        """Set the default prompt for blog generation."""
        self.settings.set_default_prompt(prompt)

    def get_generation_history(self, repository: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get generation history."""
        entries = self.get_blog_entries(repository=repository)

        history = []
        for entry in entries:
            history.append({
                "entry_id": f"{entry.generated_at.strftime('%Y%m%d_%H%M%S')}_{entry.repository.replace('/', '_')}",
                "repository": entry.repository,
                "title": entry.title,
                "provider": entry.provider,
                "model": entry.model,
                "commit_count": entry.commit_count,
                "generated_at": entry.generated_at.isoformat(),
                "filepath": str(entry.filepath)
            })

        return history

    def backup_entries(self, backup_path: Path) -> Path:
        """Create a backup of all blog entries."""
        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            # Export as JSON
            json_file = self.export_entries(backup_path, "json")

            # Export as Markdown
            md_file = self.export_entries(backup_path, "markdown")

            # Create backup info
            backup_info = {
                "backup_created": datetime.now().isoformat(),
                "total_entries": len(self.storage.get_all_entries()),
                "json_export": str(json_file),
                "markdown_export": str(md_file)
            }

            info_file = backup_path / "backup_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(backup_info, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Backup created at: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            raise BlogStorageError(f"Failed to create backup: {str(e)}")
