#!/usr/bin/env python3
"""
DevBlogger - Base AI provider interface
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AIResponse:
    """Response from AI provider."""
    text: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AIProvider(ABC):
    """Base class for AI providers."""

    def __init__(self, name: str, model: str):
        """Initialize AI provider."""
        self.name = name
        self.model = model
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to AI provider."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using AI model."""
        pass

    def generate_sync(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text synchronously (fallback for threading issues)."""
        import asyncio
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't use run_until_complete
                # This is a fallback - subclasses should implement proper sync methods
                raise NotImplementedError("Synchronous generation not implemented for this provider")
            else:
                # Loop exists but not running
                response = loop.run_until_complete(
                    self.generate_text(prompt, max_tokens, temperature, **kwargs)
                )
                return response.text
        except RuntimeError:
            # No event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(
                    self.generate_text(prompt, max_tokens, temperature, **kwargs)
                )
                return response.text
            finally:
                loop.close()

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider."""
        pass

    @abstractmethod
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        pass

    def validate_config(self) -> List[str]:
        """Validate provider configuration and return list of issues."""
        issues = []
        if not self.is_configured():
            issues.append(f"{self.name} provider is not configured")
        return issues

    def get_status(self) -> Dict[str, Any]:
        """Get provider status information."""
        return {
            "name": self.name,
            "model": self.model,
            "configured": self.is_configured(),
            "available": self.test_connection(),
            "issues": self.validate_config()
        }


class AIProviderManager:
    """Manager for multiple AI providers."""

    def __init__(self):
        """Initialize AI provider manager."""
        self.providers: Dict[str, AIProvider] = {}
        self.active_provider: Optional[str] = None
        self.logger = logging.getLogger(__name__)

    def register_provider(self, provider: AIProvider):
        """Register an AI provider."""
        self.providers[provider.name] = provider
        self.logger.info(f"Registered AI provider: {provider.name}")

    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Get provider by name."""
        return self.providers.get(name)

    def set_active_provider(self, name: str):
        """Set active provider."""
        if name in self.providers:
            self.active_provider = name
            self.logger.info(f"Set active provider: {name}")
        else:
            raise ValueError(f"Provider {name} not found")

    def get_active_provider(self) -> Optional[AIProvider]:
        """Get active provider."""
        if self.active_provider:
            return self.providers.get(self.active_provider)
        return None

    def get_all_providers(self) -> Dict[str, AIProvider]:
        """Get all registered providers."""
        return self.providers.copy()

    def get_provider_status(self, name: str) -> Dict[str, Any]:
        """Get status of a specific provider."""
        provider = self.get_provider(name)
        if provider:
            return provider.get_status()
        return {"name": name, "error": "Provider not found"}

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers."""
        return {
            name: provider.get_status()
            for name, provider in self.providers.items()
        }

    def validate_all_providers(self) -> Dict[str, List[str]]:
        """Validate all providers and return issues."""
        return {
            name: provider.validate_config()
            for name, provider in self.providers.items()
        }

    async def generate_with_active(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using active provider."""
        provider = self.get_active_provider()
        if not provider:
            raise ValueError("No active AI provider set")

        if not provider.is_configured():
            raise ValueError(f"Active provider {provider.name} is not configured")

        return await provider.generate_text(prompt, max_tokens, temperature, **kwargs)

    def get_configured_providers(self) -> List[str]:
        """Get list of configured providers."""
        return [
            name for name, provider in self.providers.items()
            if provider.is_configured()
        ]

    def get_working_providers(self) -> List[str]:
        """Get list of providers that are both configured and working."""
        return [
            name for name, provider in self.providers.items()
            if provider.is_configured() and provider.test_connection()
        ]
