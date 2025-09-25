#!/usr/bin/env python3
"""
DevBlogger - Application settings and configuration
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Settings:
    """Application settings manager."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize settings with optional config file path."""
        if config_file is None:
            # Default config file in user's home directory
            self.config_dir = Path.home() / ".devblogger"
            self.config_file = self.config_dir / "config.json"
        else:
            self.config_file = Path(config_file)

        self.config_dir = self.config_file.parent
        self._settings: Dict[str, Any] = {}
        self._default_settings = self._get_default_settings()

        self._load_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings."""
        return {
            "app": {
                "name": "DevBlogger",
                "version": "0.1.0",
                "debug": False,
            },
            "paths": {
                "generated_entries": "Generated_entries",
                "logs": "logs",
                "database": "devblogger.db",
            },
            "github": {
                "client_id": "",
                "client_secret": "",
                "redirect_uri": "http://localhost:8080/callback",
                "scope": "read:user repo",
                "api_base_url": "https://api.github.com",
            },
            "ai": {
                "default_provider": "chatgpt",
                "providers": {
                    "chatgpt": {
                        "api_key": "",
                        "model": "gpt-4",
                        "max_tokens": 2000,
                        "temperature": 0.7,
                    },
                    "gemini": {
                        "api_key": "",
                        "model": "gemini-pro",
                        "max_tokens": 2000,
                        "temperature": 0.7,
                    },
                    "ollama": {
                        "base_url": "http://localhost:11434",
                        "model": "llama2",
                        "max_tokens": 2000,
                        "temperature": 0.7,
                    },
                },
            },
            "ui": {
                "theme": "system",  # system, dark, light
                "window_width": 1200,
                "window_height": 800,
                "default_prompt": (
                    "Write a concise informative but interesting development blog entry "
                    "for each commit message (if you think it warrants a blog entry) if you think "
                    "it is interesting enough to post about. Keep the wording professional, "
                    "in the first person. Sign with the committer's name."
                ),
            },
            "blog": {
                "file_extension": ".md",
                "include_commit_hashes": True,
                "include_timestamps": True,
                "auto_save": True,
            },
        }

    def _load_settings(self):
        """Load settings from config file or create with defaults."""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Load existing settings or create with defaults
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self._settings = self._merge_settings(self._default_settings, loaded_settings)
            else:
                self._settings = self._default_settings.copy()
                self._save_settings()

        except Exception as e:
            print(f"Warning: Could not load settings: {e}")
            self._settings = self._default_settings.copy()

    def _merge_settings(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge settings dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        return result

    def _save_settings(self):
        """Save current settings to config file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value using dot notation (e.g., 'app.name')."""
        keys = key.split('.')
        value = self._settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """Set a setting value using dot notation (e.g., 'app.name')."""
        keys = key.split('.')
        settings = self._settings
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]
        settings[keys[-1]] = value
        self._save_settings()

    def get_generated_entries_dir(self) -> Path:
        """Get the directory for generated blog entries."""
        return Path(self.get("paths.generated_entries", "Generated_entries"))

    def get_logs_dir(self) -> Path:
        """Get the logs directory."""
        return Path(self.get("paths.logs", "logs"))

    def get_database_path(self) -> Path:
        """Get the database file path."""
        return Path(self.get("paths.database", "devblogger.db"))

    def get_github_config(self) -> Dict[str, Any]:
        """Get GitHub configuration."""
        return self.get("github", {})

    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration."""
        return self.get("ai", {})

    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration."""
        return self.get("ui", {})

    def get_blog_config(self) -> Dict[str, Any]:
        """Get blog configuration."""
        return self.get("blog", {})

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get("app.debug", False)

    def get_default_prompt(self) -> str:
        """Get the default AI prompt."""
        return self.get("ui.default_prompt", "")

    def set_default_prompt(self, prompt: str):
        """Set the default AI prompt."""
        self.set("ui.default_prompt", prompt)

    def get_window_size(self) -> tuple[int, int]:
        """Get the default window size."""
        width = self.get("ui.window_width", 1200)
        height = self.get("ui.window_height", 800)
        return (width, height)

    def set_window_size(self, width: int, height: int):
        """Set the default window size."""
        self.set("ui.window_width", width)
        self.set("ui.window_height", height)

    def get_ai_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific AI provider."""
        providers = self.get("ai.providers", {})
        return providers.get(provider, {})

    def set_ai_provider_config(self, provider: str, config: Dict[str, Any]):
        """Set configuration for a specific AI provider."""
        providers = self.get("ai.providers", {})
        providers[provider] = config
        self.set("ai.providers", providers)

    def get_active_ai_provider(self) -> str:
        """Get the currently active AI provider."""
        return self.get("ai.default_provider", "chatgpt")

    def set_active_ai_provider(self, provider: str):
        """Set the active AI provider."""
        self.set("ai.default_provider", provider)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._settings = self._default_settings.copy()
        self._save_settings()

    def export_settings(self, filepath: str):
        """Export settings to a JSON file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Failed to export settings: {e}")

    def import_settings(self, filepath: str):
        """Import settings from a JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
                self._settings = self._merge_settings(self._default_settings, imported_settings)
                self._save_settings()
        except Exception as e:
            raise Exception(f"Failed to import settings: {e}")

    def save(self):
        """Save current settings to config file."""
        self._save_settings()
