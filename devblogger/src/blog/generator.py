#!/usr/bin/env python3
"""
DevBlogger - Blog Generation Engine
"""

import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import re

from ..ai.manager import DevBloggerAIProviderManager
from ..github.models import GitHubCommit
from ..config.settings import Settings
from ..config.database import DatabaseManager


class BlogGenerationError(Exception):
    """Exception raised during blog generation."""
    pass


class BlogGenerator:
    """Main blog generation engine."""

    def __init__(self, ai_manager: DevBloggerAIProviderManager, settings: Settings, database: DatabaseManager):
        """Initialize blog generator."""
        self.ai_manager = ai_manager
        self.settings = settings
        self.database = database
        self.logger = logging.getLogger(__name__)

    def generate_blog_entry(
        self,
        commits: List[GitHubCommit],
        repository: str,
        prompt: Optional[str] = None,
        provider: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate a blog entry from commits."""
        if not commits:
            raise BlogGenerationError("No commits provided for blog generation")

        if not repository:
            raise BlogGenerationError("Repository name is required")

        # Use default prompt if not provided
        if not prompt:
            prompt = self.settings.get_default_prompt()
            if not prompt:
                prompt = self._get_default_prompt()

        # Use active provider if not specified
        if not provider:
            active_provider = self.ai_manager.get_active_provider()
            if not active_provider:
                raise BlogGenerationError("No AI provider available")
            provider = active_provider.name

        # Validate provider
        ai_provider = self.ai_manager.get_provider(provider)
        if not ai_provider or not ai_provider.is_configured():
            raise BlogGenerationError(f"AI provider '{provider}' is not configured")

        try:
            # Prepare commit data
            commit_data = self._prepare_commit_data(commits, repository)

            # Generate blog content
            full_prompt = f"{prompt}\n\n{commit_data}"

            # Use async generation if available
            if hasattr(ai_provider, 'generate_text'):
                # Check if it's a coroutine function
                import inspect
                if inspect.iscoroutinefunction(ai_provider.generate_text):
                    # Run async generation
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in an async context, need to handle differently
                        raise BlogGenerationError("Async generation not supported in current context")
                    else:
                        response = loop.run_until_complete(
                            ai_provider.generate_text(
                                prompt=full_prompt,
                                max_tokens=max_tokens,
                                temperature=temperature
                            )
                        )
                else:
                    # Synchronous generation
                    response = ai_provider.generate_text(
                        prompt=full_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
            else:
                raise BlogGenerationError(f"Provider {provider} does not support text generation")

            # Create blog entry
            blog_content = self._format_blog_entry(
                response.text,
                commits,
                repository,
                provider,
                response.model
            )

            # Mark commits as processed
            self._mark_commits_processed(commits, repository, provider)

            return {
                "success": True,
                "content": blog_content,
                "metadata": {
                    "repository": repository,
                    "commit_count": len(commits),
                    "provider": provider,
                    "model": response.model,
                    "tokens_used": getattr(response, 'tokens_used', None),
                    "generated_at": datetime.now().isoformat()
                }
            }

        except Exception as e:
            self.logger.error(f"Error generating blog entry: {e}")
            raise BlogGenerationError(f"Failed to generate blog entry: {str(e)}")

    def _prepare_commit_data(self, commits: List[GitHubCommit], repository: str) -> str:
        """Prepare commit data for AI processing."""
        sections = []

        # Repository header
        sections.append(f"Repository: {repository}")
        sections.append(f"Total Commits: {len(commits)}")
        sections.append("")

        # Individual commits
        for i, commit in enumerate(commits, 1):
            sections.append(f"--- Commit {i} ---")
            sections.append(f"SHA: {commit.sha}")
            sections.append(f"Author: {commit.author.name or commit.author.login or 'Unknown'}")
            sections.append(f"Date: {commit.date.strftime('%Y-%m-%d %H:%M:%S') if commit.date else 'Unknown'}")
            sections.append(f"Message: {commit.message}")

            # File changes
            if commit.files:
                sections.append("Files Changed:")
                for file_info in commit.files[:10]:  # Limit to first 10 files
                    filename = file_info.get('filename', 'Unknown')
                    status = file_info.get('status', 'Unknown')
                    additions = file_info.get('additions', 0)
                    deletions = file_info.get('deletions', 0)

                    change_info = f"  {status} {filename}"
                    if additions:
                        change_info += f" (+{additions})"
                    if deletions:
                        change_info += f" (-{deletions})"
                    sections.append(change_info)

                if len(commit.files) > 10:
                    sections.append(f"  ... and {len(commit.files) - 10} more files")

            sections.append("")

        return "\n".join(sections)

    def _format_blog_entry(
        self,
        ai_content: str,
        commits: List[GitHubCommit],
        repository: str,
        provider: str,
        model: str
    ) -> str:
        """Format the AI-generated content into a proper blog entry."""
        # Generate metadata
        timestamp = datetime.now()
        repo_name = repository.split('/')[-1]

        # Create frontmatter
        frontmatter = f"""---
title: Development Update - {repo_name}
date: {timestamp.strftime('%Y-%m-%d')}
repository: {repository}
commit_count: {len(commits)}
generated_by: {provider} ({model})
generated_at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
---

"""

        # Clean up AI content
        cleaned_content = self._clean_ai_content(ai_content)

        # Add commit references at the end
        commit_references = self._generate_commit_references(commits, repository)

        return frontmatter + cleaned_content + commit_references

    def _clean_ai_content(self, content: str) -> str:
        """Clean up AI-generated content."""
        if not content:
            return ""

        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Ensure proper spacing after headers
        content = re.sub(r'^(#{1,6} .+)$', r'\1\n', content, flags=re.MULTILINE)

        # Fix list formatting
        content = re.sub(r'^(\d+\.)\s*', r'\1 ', content, flags=re.MULTILINE)
        content = re.sub(r'^(\*)\s*', r'\1 ', content, flags=re.MULTILINE)
        content = re.sub(r'^(-)\s*', r'\1 ', content, flags=re.MULTILINE)

        # Ensure content ends with newline
        if not content.endswith('\n'):
            content += '\n'

        return content.strip()

    def _generate_commit_references(self, commits: List[GitHubCommit], repository: str) -> str:
        """Generate commit references section."""
        if not commits:
            return ""

        references = [
            "",
            "## Commit Details",
            "",
            "The following commits were included in this update:",
            ""
        ]

        for commit in commits:
            short_sha = commit.sha[:8]
            author = commit.author.name or commit.author.login or "Unknown"
            date = commit.date.strftime('%Y-%m-%d %H:%M') if commit.date else "Unknown"
            message = commit.message.split('\n')[0]  # First line only

            references.append(f"- **{short_sha}** by {author} on {date}: {message}")

        references.append("")
        return "\n".join(references)

    def _mark_commits_processed(self, commits: List[GitHubCommit], repository: str, provider: str):
        """Mark commits as processed in the database."""
        for commit in commits:
            try:
                self.database.mark_commit_processed(
                    repo_name=repository,
                    commit_sha=commit.sha,
                    ai_provider=provider
                )
                self.logger.debug(f"Marked commit {commit.sha} as processed")
            except Exception as e:
                self.logger.warning(f"Failed to mark commit {commit.sha} as processed: {e}")

    def save_blog_entry(self, content: str, repository: str, custom_filename: Optional[str] = None) -> Path:
        """Save blog entry to file."""
        try:
            # Generate filename
            if custom_filename:
                filename = custom_filename
                if not filename.endswith('.md'):
                    filename += '.md'
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                repo_name = repository.replace("/", "_")
                filename = f"{repo_name}_{timestamp}.md"

            # Get output directory
            output_dir = self.settings.get_generated_entries_dir()
            output_dir.mkdir(parents=True, exist_ok=True)

            # Full path
            filepath = output_dir / filename

            # Write content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Blog entry saved to: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Error saving blog entry: {e}")
            raise BlogGenerationError(f"Failed to save blog entry: {str(e)}")

    def regenerate_blog_entry(
        self,
        commits: List[GitHubCommit],
        repository: str,
        original_content: str,
        new_provider: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Regenerate blog entry with a different AI provider."""
        # Extract original metadata
        metadata = self._extract_metadata_from_content(original_content)

        # Use new provider
        return self.generate_blog_entry(
            commits=commits,
            repository=repository,
            prompt=prompt,
            provider=new_provider,
            max_tokens=metadata.get('max_tokens'),
            temperature=metadata.get('temperature')
        )

    def _extract_metadata_from_content(self, content: str) -> Dict[str, Any]:
        """Extract metadata from existing blog content."""
        metadata = {}

        # Simple regex to extract frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

        return metadata

    def get_generation_stats(self, commits: List[GitHubCommit]) -> Dict[str, Any]:
        """Get statistics about the commits for generation."""
        if not commits:
            return {}

        stats = {
            "total_commits": len(commits),
            "authors": set(),
            "files_changed": set(),
            "additions": 0,
            "deletions": 0,
            "date_range": None
        }

        earliest_date = None
        latest_date = None

        for commit in commits:
            # Authors
            author_name = commit.author.name or commit.author.login or "Unknown"
            stats["authors"].add(author_name)

            # Files changed
            if commit.files:
                for file_info in commit.files:
                    filename = file_info.get('filename', '')
                    if filename:
                        stats["files_changed"].add(filename)

                    # Line changes
                    stats["additions"] += file_info.get('additions', 0)
                    stats["deletions"] += file_info.get('deletions', 0)

            # Date range
            if commit.date:
                if earliest_date is None or commit.date < earliest_date:
                    earliest_date = commit.date
                if latest_date is None or commit.date > latest_date:
                    latest_date = commit.date

        stats["authors"] = list(stats["authors"])
        stats["files_changed"] = list(stats["files_changed"])
        stats["unique_files"] = len(stats["files_changed"])

        if earliest_date and latest_date:
            stats["date_range"] = {
                "earliest": earliest_date.isoformat(),
                "latest": latest_date.isoformat(),
                "span_days": (latest_date - earliest_date).days
            }

        return stats

    def validate_commits_for_generation(self, commits: List[GitHubCommit]) -> List[str]:
        """Validate commits for blog generation and return any issues."""
        issues = []

        if not commits:
            issues.append("No commits selected")
            return issues

        if len(commits) > 50:
            issues.append("Large number of commits selected - generation may be slow")

        # Check for empty or very short messages
        short_messages = 0
        for commit in commits:
            if len(commit.message.strip()) < 10:
                short_messages += 1

        if short_messages > len(commits) * 0.5:  # More than 50% have short messages
            issues.append("Many commits have very short messages - blog quality may be affected")

        # Check for processed commits
        processed_count = 0
        repository = getattr(commits[0], 'repository', '') if commits else ''

        for commit in commits:
            if self.database.is_commit_processed(repository, commit.sha):
                processed_count += 1

        if processed_count > 0:
            issues.append(f"{processed_count} commits have already been processed")

        return issues

    def _get_default_prompt(self) -> str:
        """Get default prompt for blog generation."""
        return (
            "Write a concise, informative, and interesting development blog entry "
            "based on the provided commit information. Focus on the most significant "
            "changes and improvements. Write in first person as if you are the "
            "developer describing your work. Keep the tone professional but engaging. "
            "Highlight technical achievements, challenges overcome, and the impact "
            "of the changes. Structure the post with a clear introduction, main content "
            "describing the key changes, and a conclusion if appropriate."
        )

    def get_supported_providers(self) -> List[str]:
        """Get list of AI providers that support blog generation."""
        providers = []
        for name, provider in self.ai_manager.get_all_providers().items():
            if provider.is_configured():
                providers.append(name)
        return providers

    def estimate_generation_time(self, commits: List[GitHubCommit], provider: str) -> Dict[str, Any]:
        """Estimate generation time based on commit count and provider."""
        base_time = 10  # Base time in seconds
        per_commit_time = 2  # Additional time per commit
        provider_multiplier = {
            "chatgpt": 1.0,
            "gemini": 1.2,
            "ollama": 2.0  # Local models are slower
        }

        commit_count = len(commits)
        estimated_seconds = base_time + (commit_count * per_commit_time)
        estimated_seconds *= provider_multiplier.get(provider, 1.5)

        return {
            "estimated_seconds": estimated_seconds,
            "estimated_minutes": estimated_seconds / 60,
            "commit_count": commit_count,
            "provider": provider
        }
