#!/usr/bin/env python3
"""
DevBlogger - Database management for tracking processed commits
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class DatabaseManager:
    """SQLite database manager for DevBlogger."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager."""
        if db_path is None:
            # Use default database path from settings
            from .settings import Settings
            settings = Settings()
            self.db_path = settings.get_database_path()
        else:
            self.db_path = Path(db_path)

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create processed_commits table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_commits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        repo_name TEXT NOT NULL,
                        commit_sha TEXT NOT NULL,
                        process_type TEXT DEFAULT 'both',
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        blog_entry_path TEXT,
                        ai_provider TEXT,
                        prompt_used TEXT,
                        UNIQUE(repo_name, commit_sha, process_type)
                    )
                ''')

                # Add process_type column if it doesn't exist (for existing databases)
                try:
                    cursor.execute("ALTER TABLE processed_commits ADD COLUMN process_type TEXT DEFAULT 'both'")
                except sqlite3.Error:
                    # Column already exists
                    pass

                # Create commit_metadata table for additional commit info
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS commit_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        repo_name TEXT NOT NULL,
                        commit_sha TEXT NOT NULL,
                        author_name TEXT,
                        author_email TEXT,
                        commit_date TIMESTAMP,
                        message TEXT,
                        file_changes TEXT,  -- JSON string of changed files
                        raw_data TEXT,      -- Full commit data as JSON
                        UNIQUE(repo_name, commit_sha)
                    )
                ''')

                # Create settings table for application state
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processed_commits_repo
                    ON processed_commits(repo_name)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processed_commits_time
                    ON processed_commits(processed_at)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_commit_metadata_repo
                    ON commit_metadata(repo_name)
                ''')

                conn.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise

    def is_commit_processed(self, repo_name: str, commit_sha: str, process_type: str = "any") -> bool:
        """Check if a commit has already been processed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if process_type == "any":
                    cursor.execute(
                        "SELECT id FROM processed_commits WHERE repo_name = ? AND commit_sha = ?",
                        (repo_name, commit_sha)
                    )
                else:
                    cursor.execute(
                        "SELECT id FROM processed_commits WHERE repo_name = ? AND commit_sha = ? AND process_type = ?",
                        (repo_name, commit_sha, process_type)
                    )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"Error checking processed commit: {e}")
            return False

    def mark_commit_processed(
        self,
        repo_name: str,
        commit_sha: str,
        process_type: str = "both",
        blog_entry_path: Optional[str] = None,
        ai_provider: Optional[str] = None,
        prompt_used: Optional[str] = None
    ) -> bool:
        """Mark a commit as processed for specific type."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_commits
                    (repo_name, commit_sha, process_type, blog_entry_path, ai_provider, prompt_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (repo_name, commit_sha, process_type, blog_entry_path, ai_provider, prompt_used))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error marking commit as processed: {e}")
            return False

    def mark_commit_unprocessed(self, repo_name: str, commit_sha: str, process_type: str = "both") -> bool:
        """Mark a commit as unprocessed for specific type."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if process_type == "both":
                    # Remove all processing records for this commit
                    cursor.execute(
                        "DELETE FROM processed_commits WHERE repo_name = ? AND commit_sha = ?",
                        (repo_name, commit_sha)
                    )
                else:
                    # Remove specific processing type
                    cursor.execute(
                        "DELETE FROM processed_commits WHERE repo_name = ? AND commit_sha = ? AND process_type = ?",
                        (repo_name, commit_sha, process_type)
                    )

                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error marking commit as unprocessed: {e}")
            return False

    def store_commit_metadata(
        self,
        repo_name: str,
        commit_sha: str,
        author_name: str,
        author_email: str,
        commit_date: datetime,
        message: str,
        file_changes: List[Dict[str, Any]],
        raw_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store commit metadata for future reference."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO commit_metadata
                    (repo_name, commit_sha, author_name, author_email, commit_date,
                     message, file_changes, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    repo_name,
                    commit_sha,
                    author_name,
                    author_email,
                    commit_date.isoformat() if commit_date else None,
                    message,
                    json.dumps(file_changes),
                    json.dumps(raw_data) if raw_data else None
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error storing commit metadata: {e}")
            return False

    def get_commit_metadata(self, repo_name: str, commit_sha: str) -> Optional[Dict[str, Any]]:
        """Retrieve commit metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM commit_metadata WHERE repo_name = ? AND commit_sha = ?",
                    (repo_name, commit_sha)
                )
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving commit metadata: {e}")
            return None

    def get_processed_commits(
        self,
        repo_name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get list of processed commits with optional filtering."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM processed_commits"
                params = []

                if repo_name:
                    query += " WHERE repo_name = ?"
                    params.append(repo_name)

                query += " ORDER BY processed_at DESC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                if offset:
                    query += " OFFSET ?"
                    params.append(offset)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving processed commits: {e}")
            return []

    def get_unprocessed_commits_count(self, repo_name: str) -> int:
        """Get count of unprocessed commits for a repository."""
        # This would require comparing with actual GitHub data
        # For now, return 0 as a placeholder
        return 0

    def set_setting(self, key: str, value: str):
        """Store a setting in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO app_settings (key, value)
                    VALUES (?, ?)
                ''', (key, value))
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error setting database value: {e}")

    def get_setting(self, key: str, default: str = "") -> str:
        """Retrieve a setting from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else default
        except sqlite3.Error as e:
            self.logger.error(f"Error getting database value: {e}")
            return default

    def cleanup_old_records(self, days_old: int = 30):
        """Clean up old processed commit records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM processed_commits
                    WHERE processed_at < datetime('now', '-' || ? || ' days')
                ''', (days_old,))
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error cleaning up old records: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                stats = {}

                # Get table counts
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats[f"{table_name}_count"] = count

                # Get database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                size = cursor.fetchone()[0]
                stats["database_size_bytes"] = size

                return stats

        except sqlite3.Error as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}

    def vacuum_database(self):
        """Optimize database by running VACUUM."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
        except sqlite3.Error as e:
            self.logger.error(f"Error vacuuming database: {e}")

    def close(self):
        """Close database connection (no-op for this implementation)."""
        pass

    def __del__(self):
        """Destructor - ensure database is properly closed."""
        self.close()
