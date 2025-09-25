#!/usr/bin/env python3
"""
DevBlogger - AI Provider Manager
"""

import logging
from typing import Dict, Any, Optional, List

from .base import AIProviderManager, AIProvider
from .openai_client import OpenAIProviderSync
from .gemini_client import GeminiProviderSync
from .ollama_client import OllamaProviderSync
from ..config.settings import Settings


class DevBloggerAIProviderManager(AIProviderManager):
    """AI Provider Manager for DevBlogger application."""

    def __init__(self, settings: Settings):
        """Initialize AI provider manager."""
        super().__init__()
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # Register all available providers
        self._register_providers()

    def _register_providers(self):
        """Register all available AI providers."""
        try:
            # Register OpenAI ChatGPT provider
            chatgpt_provider = OpenAIProviderSync(self.settings)
            self.register_provider(chatgpt_provider)

            # Register Google Gemini provider
            gemini_provider = GeminiProviderSync(self.settings)
            self.register_provider(gemini_provider)

            # Register Ollama provider
            ollama_provider = OllamaProviderSync(self.settings)
            self.register_provider(ollama_provider)

            # Set default active provider
            self._set_default_active_provider()

        except Exception as e:
            self.logger.error(f"Error registering providers: {e}")

    def _set_default_active_provider(self):
        """Set the default active provider based on configuration."""
        try:
            default_provider = self.settings.get_active_ai_provider()

            if default_provider in self.providers:
                self.active_provider = default_provider
                self.logger.info(f"Set default active provider: {default_provider}")
            else:
                # Find first configured provider
                configured_providers = self.get_configured_providers()
                if configured_providers:
                    self.active_provider = configured_providers[0]
                    self.logger.info(f"Set first configured provider as active: {self.active_provider}")
                else:
                    self.logger.warning("No configured AI providers found")

        except Exception as e:
            self.logger.error(f"Error setting default provider: {e}")

    def get_provider_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all provider statuses."""
        all_statuses = self.get_all_statuses()

        summary = {
            "total_providers": len(self.providers),
            "configured_providers": len(self.get_configured_providers()),
            "working_providers": len(self.get_working_providers()),
            "active_provider": self.active_provider,
            "providers": all_statuses
        }

        return summary

    def validate_all_configurations(self) -> Dict[str, List[str]]:
        """Validate all provider configurations and return issues."""
        issues = {}

        for name, provider in self.providers.items():
            provider_issues = provider.validate_config()
            if provider_issues:
                issues[name] = provider_issues

        return issues

    def get_recommended_provider(self) -> Optional[str]:
        """Get the recommended provider based on configuration and availability."""
        working_providers = self.get_working_providers()

        if working_providers:
            # Prefer the currently active provider if it's working
            if self.active_provider and self.active_provider in working_providers:
                return self.active_provider

            # Otherwise return the first working provider
            return working_providers[0]

        # If no providers are working, return the first configured one
        configured_providers = self.get_configured_providers()
        if configured_providers:
            return configured_providers[0]

        return None

    def switch_to_best_provider(self) -> bool:
        """Switch to the best available provider."""
        recommended = self.get_recommended_provider()

        if recommended and recommended != self.active_provider:
            try:
                self.set_active_provider(recommended)
                self.logger.info(f"Switched to best provider: {recommended}")
                return True
            except Exception as e:
                self.logger.error(f"Error switching to best provider: {e}")
                return False

        return False

    def get_provider_capabilities(self, provider_name: str) -> Dict[str, Any]:
        """Get detailed capabilities of a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return {"error": "Provider not found"}

        try:
            return {
                "name": provider.name,
                "model": provider.model,
                "configured": provider.is_configured(),
                "available": provider.test_connection(),
                "available_models": provider.get_available_models(),
                "model_info": provider.get_model_info(provider.model),
                "usage_info": self._get_provider_usage_info(provider),
                "status": provider.get_status()
            }
        except Exception as e:
            return {
                "name": provider_name,
                "error": f"Error getting capabilities: {str(e)}"
            }

    def _get_provider_usage_info(self, provider: AIProvider) -> Dict[str, Any]:
        """Get usage information for a provider."""
        # This is a generic method - specific providers may override this
        if hasattr(provider, 'get_usage_info'):
            return provider.get_usage_info()
        return {}

    def update_provider_config(self, provider_name: str, config: Dict[str, Any]) -> bool:
        """Update configuration for a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            self.logger.error(f"Provider {provider_name} not found")
            return False

        try:
            if provider_name == "chatgpt":
                api_key = config.get("api_key", "")
                model = config.get("model", "gpt-4")
                provider.update_config(api_key, model)

            elif provider_name == "gemini":
                api_key = config.get("api_key", "")
                model = config.get("model", "gemini-pro")
                provider.update_config(api_key, model)

            elif provider_name == "ollama":
                base_url = config.get("base_url", "http://localhost:11434")
                model = config.get("model", "llama2")
                provider.update_config(base_url, model)

            self.logger.info(f"Updated configuration for {provider_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating {provider_name} config: {e}")
            return False

    def test_all_providers(self) -> Dict[str, bool]:
        """Test all providers and return their status."""
        results = {}

        for name, provider in self.providers.items():
            try:
                results[name] = provider.test_connection()
            except Exception as e:
                self.logger.error(f"Error testing {name}: {e}")
                results[name] = False

        return results

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics for all providers."""
        stats = {
            "total_providers": len(self.providers),
            "active_provider": self.active_provider,
            "provider_stats": {}
        }

        for name, provider in self.providers.items():
            stats["provider_stats"][name] = {
                "configured": provider.is_configured(),
                "available": provider.test_connection(),
                "model": provider.model,
                "max_tokens": getattr(provider, 'max_tokens', None),
                "temperature": getattr(provider, 'temperature', None)
            }

        return stats

    def reset_provider_config(self, provider_name: str) -> bool:
        """Reset provider configuration to defaults."""
        provider = self.get_provider(provider_name)
        if not provider:
            return False

        try:
            # Reset to default configuration
            if provider_name == "chatgpt":
                provider.update_config("", "gpt-4")
            elif provider_name == "gemini":
                provider.update_config("", "gemini-pro")
            elif provider_name == "ollama":
                provider.update_config("http://localhost:11434", "llama2")

            self.logger.info(f"Reset configuration for {provider_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error resetting {provider_name} config: {e}")
            return False

    def get_provider_diagnostics(self) -> Dict[str, Any]:
        """Get comprehensive diagnostics for all providers."""
        diagnostics = {
            "timestamp": None,  # Will be set by caller
            "summary": self.get_provider_status_summary(),
            "configurations": self.validate_all_configurations(),
            "test_results": self.test_all_providers(),
            "capabilities": {},
            "issues": []
        }

        # Get capabilities for each provider
        for name in self.providers.keys():
            diagnostics["capabilities"][name] = self.get_provider_capabilities(name)

        # Collect all issues
        for name, issues in diagnostics["configurations"].items():
            diagnostics["issues"].extend([f"{name}: {issue}" for issue in issues])

        return diagnostics
