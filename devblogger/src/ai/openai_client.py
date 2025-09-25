#!/usr/bin/env python3
"""
DevBlogger - OpenAI ChatGPT provider
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import os

try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None
    AsyncOpenAI = None

from .base import AIProvider, AIResponse
from ..config.settings import Settings


class OpenAIProvider(AIProvider):
    """OpenAI ChatGPT provider."""

    def __init__(self, settings: Settings):
        """Initialize OpenAI provider."""
        super().__init__("chatgpt", "gpt-4")

        self.settings = settings
        self.client: Optional[AsyncOpenAI] = None
        self.api_key = ""

        # Load configuration
        self._load_config()

        if OPENAI_AVAILABLE and self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)

    def _load_config(self):
        """Load OpenAI configuration from settings."""
        try:
            config = self.settings.get_ai_provider_config("chatgpt")
            self.api_key = config.get("api_key", "")
            self.model = config.get("model", "gpt-4")
            self.max_tokens = config.get("max_tokens", 2000)
            self.temperature = config.get("temperature", 0.7)
        except Exception as e:
            self.logger.error(f"Error loading OpenAI config: {e}")

    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured."""
        return bool(self.api_key and OPENAI_AVAILABLE)

    def test_connection(self) -> bool:
        """Test connection to OpenAI API."""
        if not self.is_configured() or not self.client:
            return False

        try:
            # Simple synchronous test - just check if client is configured
            return bool(self.api_key and self.validate_api_key(self.api_key))
        except Exception as e:
            self.logger.error(f"OpenAI connection test failed: {e}")
            return False

    async def _test_api_call(self) -> bool:
        """Test OpenAI API with a simple call."""
        try:
            response = await self.client.models.list()
            return len(response.data) > 0
        except Exception:
            return False

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using OpenAI ChatGPT."""
        if not self.client:
            raise ValueError("OpenAI client not initialized")

        # Use provided parameters or defaults
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        try:
            # Create chat completion
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes professional development blog entries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Extract response data
            choice = response.choices[0]
            text = choice.message.content.strip()

            # Get token usage
            tokens_used = None
            if response.usage:
                tokens_used = response.usage.total_tokens

            return AIResponse(
                text=text,
                model=self.model,
                provider=self.name,
                tokens_used=tokens_used,
                finish_reason=choice.finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "model": response.model,
                    "id": response.id
                }
            )

        except Exception as e:
            self.logger.error(f"OpenAI generation error: {e}")
            raise ValueError(f"OpenAI API error: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models."""
        if not self.client:
            return []

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview"]  # Common models
            else:
                response = asyncio.run(self.client.models.list())
                return [model.id for model in response.data if "gpt" in model.id]
        except Exception as e:
            self.logger.error(f"Error getting OpenAI models: {e}")
            return ["gpt-4", "gpt-3.5-turbo"]  # Fallback to known models

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific OpenAI model."""
        return {
            "name": model,
            "provider": "OpenAI",
            "type": "chat",
            "context_length": 8192 if "gpt-3.5" in model else 128000,
            "max_tokens": 4096 if "gpt-3.5" in model else 4096,
            "description": f"OpenAI {model} model"
        }

    def update_config(self, api_key: str, model: str = "gpt-4"):
        """Update OpenAI configuration."""
        self.api_key = api_key
        self.model = model

        # Save to settings
        config = {
            "api_key": api_key,
            "model": model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        self.settings.set_ai_provider_config("chatgpt", config)

        # Reinitialize client
        if OPENAI_AVAILABLE:
            self.client = AsyncOpenAI(api_key=api_key)

        self.logger.info(f"Updated OpenAI config: model={model}")

    def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenAI API key format."""
        if not api_key:
            return False

        # OpenAI API keys start with 'sk-'
        return api_key.startswith("sk-") and len(api_key) > 20

    def get_usage_info(self) -> Dict[str, Any]:
        """Get OpenAI usage information."""
        if not self.client:
            return {"configured": False}

        return {
            "configured": True,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "api_key_valid": self.validate_api_key(self.api_key)
        }


class OpenAIProviderSync(OpenAIProvider):
    """Synchronous version of OpenAI provider for compatibility."""

    def __init__(self, settings: Settings):
        """Initialize synchronous OpenAI provider."""
        super().__init__(settings)

        if OPENAI_AVAILABLE and self.api_key:
            # Use sync client for compatibility
            import openai
            self.sync_client = openai.OpenAI(api_key=self.api_key)
        else:
            self.sync_client = None

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using OpenAI ChatGPT (sync version)."""
        if not self.sync_client:
            raise ValueError("OpenAI client not initialized")

        # Use provided parameters or defaults
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        try:
            # Create chat completion using sync client
            response = self.sync_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes professional development blog entries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Extract response data
            choice = response.choices[0]
            text = choice.message.content.strip()

            # Get token usage
            tokens_used = None
            if response.usage:
                tokens_used = response.usage.total_tokens

            return AIResponse(
                text=text,
                model=self.model,
                provider=self.name,
                tokens_used=tokens_used,
                finish_reason=choice.finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "model": response.model,
                    "id": response.id
                }
            )

        except Exception as e:
            self.logger.error(f"OpenAI generation error: {e}")
            raise ValueError(f"OpenAI API error: {str(e)}")
