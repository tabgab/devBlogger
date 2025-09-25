#!/usr/bin/env python3
"""
DevBlogger - Blog File Management
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import shutil

from ..config.settings import Settings


class BlogStorageError(Exception):
    """Exception raised during blog storage operations."""
    pass


class BlogEntry:
    """Represents a blog entry with metadata."""

    def __init__(
        self,
        filepath: Path,
        repository: str,
        commit_count: int,
        provider: str,
        model: str,
        generated_at: datetime,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Initialize blog entry."""
        self.filepath = filepath
        self.repository = repository
        self.commit_count = commit_count
        self.provider = provider
        self.model = model
        self.generated_at = generated_at
        self.title = title or f"Development Update - {repository.split('/')[-1]}"
        self.tags = tags or []

    @classmethod
    def from_file(cls, filepath: Path) -> 'BlogEntry':
        """Create BlogEntry from existing file."""
        try:
            # Read frontmatter
            content = filepath.read_text(encoding='utf-8')
            metadata = cls._extract_frontmatter(content)

            return cls(
                filepath=filepath,
                repository=metadata.get('repository', 'Unknown'),
                commit_count=int(metadata.get('commit_count', 0)),
                provider=metadata.get('generated_by', 'Unknown').split('(')[0].strip(),
                model=metadata.get('generated_by', 'Unknown').split('(')[-1].rstrip(')'),
                generated_at=datetime.fromisoformat(metadata.get('generated_at', datetime.now().isoformat())),
                title=metadata.get('title', None),
                tags=metadata.get('tags', [])
            )
        except Exception as e:
            raise BlogStorageError(f"Failed to load blog entry from {filepath}: {e}")

    @staticmethod
    def _extract_frontmatter(content: str) -> Dict[str, Any]:
        """Extract frontmatter from markdown content."""
        import re

        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if not frontmatter_match:
            return {}

        frontmatter = frontmatter_match.group(1)
        metadata = {}

        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Handle different value types
                if value.lower() in ['true', 'false']:
                    metadata[key] = value.lower() == 'true'
                elif value.isdigit():
                    metadata[key] = int(value)
                elif value.startswith('[') and value.endswith(']'):
                    # Simple list parsing
                    list_items = [item.strip().strip('"\'') for item in value[1:-1].split(',')]
                    metadata[key] = [item for item in list_items if item]
                else:
                    metadata[key] = value

        return metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "filepath": str(self.filepath),
            "repository": self.repository,
            "commit_count": self.commit_count,
            "provider": self.provider,
            "model": self.model,
            "generated_at": self.generated_at.isoformat(),
            "title": self.title,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlogEntry':
        """Create from dictionary representation."""
        return cls(
            filepath=Path(data["filepath"]),
            repository=data["repository"],
            commit_count=data["commit_count"],
            provider=data["provider"],
            model=data["model"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            title=data.get("title"),
            tags=data.get("tags", [])
        )


class BlogStorageManager:
    """Manages blog entry storage and organization."""

    def __init__(self, settings: Settings):
        """Initialize storage manager."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # Storage configuration
        self.entries_dir = self.settings.get_generated_entries_dir()
        self.index_file = self.entries_dir / ".blog_index.json"
        self.entries: Dict[str, BlogEntry] = {}

        # Ensure directories exist
        self.entries_dir.mkdir(parents=True, exist_ok=True)

        # Load existing entries
        self._load_index()

    def _load_index(self):
        """Load blog entry index from file."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)

                for entry_id, entry_data in index_data.items():
                    try:
                        self.entries[entry_id] = BlogEntry.from_dict(entry_data)
                    except Exception as e:
                        self.logger.warning(f"Failed to load entry {entry_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error loading blog index: {e}")

    def _save_index(self):
        """Save blog entry index to file."""
        try:
            index_data = {
                entry_id: entry.to_dict()
                for entry_id, entry in self.entries.items()
            }

            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Error saving blog index: {e}")

    def add_entry(self, entry: BlogEntry) -> str:
        """Add a blog entry to storage."""
        try:
            # Generate unique ID
            entry_id = entry.generated_at.strftime("%Y%m%d_%H%M%S") + "_" + entry.repository.replace("/", "_")

            # Check if entry already exists
            if entry_id in self.entries:
                # Update existing entry
                existing_entry = self.entries[entry_id]
                existing_entry.filepath = entry.filepath
                existing_entry.title = entry.title
                existing_entry.tags = entry.tags
            else:
                # Add new entry
                self.entries[entry_id] = entry

            # Save index
            self._save_index()

            self.logger.info(f"Added blog entry: {entry_id}")
            return entry_id

        except Exception as e:
            self.logger.error(f"Error adding blog entry: {e}")
            raise BlogStorageError(f"Failed to add blog entry: {str(e)}")

    def get_entry(self, entry_id: str) -> Optional[BlogEntry]:
        """Get a blog entry by ID."""
        return self.entries.get(entry_id)

    def get_all_entries(self) -> List[BlogEntry]:
        """Get all blog entries."""
        return list(self.entries.values())

    def get_entries_by_repository(self, repository: str) -> List[BlogEntry]:
        """Get all entries for a specific repository."""
        return [entry for entry in self.entries.values() if entry.repository == repository]

    def get_entries_by_provider(self, provider: str) -> List[BlogEntry]:
        """Get all entries generated by a specific provider."""
        return [entry for entry in self.entries.values() if entry.provider == provider]

    def get_entries_by_date_range(self, start_date: datetime, end_date: datetime) -> List[BlogEntry]:
        """Get entries within a date range."""
        return [
            entry for entry in self.entries.values()
            if start_date <= entry.generated_at <= end_date
        ]

    def search_entries(self, query: str) -> List[BlogEntry]:
        """Search entries by title, repository, or tags."""
        query_lower = query.lower()
        results = []

        for entry in self.entries.values():
            if (query_lower in entry.title.lower() or
                query_lower in entry.repository.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)

        return results

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a blog entry."""
        try:
            if entry_id not in self.entries:
                return False

            entry = self.entries[entry_id]

            # Apply updates
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)

            # Save index
            self._save_index()

            self.logger.info(f"Updated blog entry: {entry_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating blog entry {entry_id}: {e}")
            return False

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a blog entry."""
        try:
            if entry_id not in self.entries:
                return False

            entry = self.entries[entry_id]

            # Delete file if it exists
            if entry.filepath.exists():
                entry.filepath.unlink()

            # Remove from index
            del self.entries[entry_id]
            self._save_index()

            self.logger.info(f"Deleted blog entry: {entry_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting blog entry {entry_id}: {e}")
            return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            total_entries = len(self.entries)
            total_size = 0
            repository_counts = {}
            provider_counts = {}

            for entry in self.entries.values():
                # Calculate file size
                if entry.filepath.exists():
                    total_size += entry.filepath.stat().st_size

                # Count by repository
                repo = entry.repository
                repository_counts[repo] = repository_counts.get(repo, 0) + 1

                # Count by provider
                provider = entry.provider
                provider_counts[provider] = provider_counts.get(provider, 0) + 1

            return {
                "total_entries": total_entries,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "repositories": repository_counts,
                "providers": provider_counts,
                "storage_path": str(self.entries_dir)
            }

        except Exception as e:
            self.logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}

    def export_entries(self, export_path: Path, format: str = "json") -> Path:
        """Export all entries to a file."""
        try:
            if format.lower() == "json":
                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "total_entries": len(self.entries),
                    "entries": {
                        entry_id: entry.to_dict()
                        for entry_id, entry in self.entries.items()
                    }
                }

                export_file = export_path / "blog_entries_export.json"
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

            elif format.lower() == "markdown":
                # Export as a combined markdown file
                export_file = export_path / "blog_entries_export.md"

                with open(export_file, 'w', encoding='utf-8') as f:
                    f.write(f"# DevBlogger Export\n\n")
                    f.write(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total entries: {len(self.entries)}\n\n")
                    f.write("---\n\n")

                    for entry in sorted(self.entries.values(), key=lambda x: x.generated_at, reverse=True):
                        f.write(f"# {entry.title}\n\n")
                        f.write(f"**Repository:** {entry.repository}\n")
                        f.write(f"**Generated:** {entry.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"**Provider:** {entry.provider} ({entry.model})\n")
                        f.write(f"**Commits:** {entry.commit_count}\n")

                        if entry.tags:
                            f.write(f"**Tags:** {', '.join(entry.tags)}\n")

                        f.write("\n")

                        # Read and include content
                        if entry.filepath.exists():
                            content = entry.filepath.read_text(encoding='utf-8')
                            # Remove frontmatter for export
                            content = content.split('---\n\n', 1)[-1] if '---\n\n' in content else content
                            f.write(content)
                        else:
                            f.write("*Content file not found*\n")

                        f.write("\n\n---\n\n")

            else:
                raise BlogStorageError(f"Unsupported export format: {format}")

            self.logger.info(f"Exported {len(self.entries)} entries to {export_file}")
            return export_file

        except Exception as e:
            self.logger.error(f"Error exporting entries: {e}")
            raise BlogStorageError(f"Failed to export entries: {str(e)}")

    def cleanup_old_entries(self, days_old: int = 90) -> int:
        """Clean up entries older than specified days."""
        try:
            cutoff_date = datetime.now() - datetime.timedelta(days=days_old)
            deleted_count = 0

            entries_to_delete = [
                entry_id for entry_id, entry in self.entries.items()
                if entry.generated_at < cutoff_date
            ]

            for entry_id in entries_to_delete:
                if self.delete_entry(entry_id):
                    deleted_count += 1

            self.logger.info(f"Cleaned up {deleted_count} old entries")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return 0

    def validate_storage(self) -> Dict[str, Any]:
        """Validate storage integrity and return issues."""
        issues = {
            "missing_files": [],
            "orphaned_files": [],
            "total_issues": 0
        }

        try:
            # Check for missing files
            for entry_id, entry in self.entries.items():
                if not entry.filepath.exists():
                    issues["missing_files"].append({
                        "entry_id": entry_id,
                        "filepath": str(entry.filepath)
                    })

            # Check for orphaned files (files not in index)
            if self.entries_dir.exists():
                for file_path in self.entries_dir.glob("*.md"):
                    if file_path.name != ".blog_index.json":
                        # Check if file is in index
                        found = False
                        for entry in self.entries.values():
                            if entry.filepath == file_path:
                                found = True
                                break

                        if not found:
                            issues["orphaned_files"].append(str(file_path))

            issues["total_issues"] = len(issues["missing_files"]) + len(issues["orphaned_files"])

        except Exception as e:
            issues["error"] = str(e)

        return issues

    def repair_storage(self) -> Dict[str, Any]:
        """Attempt to repair storage issues."""
        repair_results = {
            "repaired_missing_files": 0,
            "removed_orphaned_files": 0,
            "errors": []
        }

        try:
            # Remove orphaned files
            validation = self.validate_storage()
            for orphaned_file in validation["orphaned_files"]:
                try:
                    Path(orphaned_file).unlink()
                    repair_results["removed_orphaned_files"] += 1
                except Exception as e:
                    repair_results["errors"].append(f"Failed to remove {orphaned_file}: {e}")

            # Note: Missing files can't be automatically repaired
            repair_results["repaired_missing_files"] = 0

        except Exception as e:
            repair_results["errors"].append(f"Repair failed: {e}")

        return repair_results
