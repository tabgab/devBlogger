#!/usr/bin/env python3
"""
DevBlogger - Google Gemini provider
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import os

try:
    import google.generativeai as genai
    from google.generativeai.types import RequestOptions
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    RequestOptions = None

from .base import AIProvider, AIResponse
from ..config.settings import Settings


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, settings: Settings):
        """Initialize Gemini provider."""
        super().__init__("gemini", "gemini-pro")

        self.settings = settings
        self.api_key = ""
        self.model_instance = None

        # Load configuration
        self._load_config()

        if GENAI_AVAILABLE and self.api_key:
            self._initialize_client()

    def _load_config(self):
        """Load Gemini configuration from settings."""
        try:
            config = self.settings.get_ai_provider_config("gemini")
            self.api_key = config.get("api_key", "")
            self.model = config.get("model", "gemini-pro")
            self.max_tokens = config.get("max_tokens", 2000)
            self.temperature = config.get("temperature", 0.7)
        except Exception as e:
            self.logger.error(f"Error loading Gemini config: {e}")

    def _initialize_client(self):
        """Initialize Google Generative AI client."""
        try:
            genai.configure(api_key=self.api_key)
            self.model_instance = genai.GenerativeModel(self.model)
            self.logger.info(f"Initialized Gemini client with model: {self.model}")
        except Exception as e:
            self.logger.error(f"Error initializing Gemini client: {e}")
            self.model_instance = None

    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
        return bool(self.api_key and GENAI_AVAILABLE and self.model_instance)

    def test_connection(self) -> bool:
        """Test connection to Gemini API."""
        if not self.is_configured():
            return False

        try:
            # Try to get model information as a connection test
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return True  # Assume configured means working
            else:
                # Test with a simple generation
                response = asyncio.run(self._test_generation())
                return bool(response)
        except Exception as e:
            self.logger.error(f"Gemini connection test failed: {e}")
            return False

    async def _test_generation(self) -> bool:
        """Test Gemini API with a simple generation."""
        try:
            response = await self.model_instance.generate_content_async(
                "Hello",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0.1
                )
            )
            return bool(response.text)
        except Exception:
            return False

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using Google Gemini."""
        if not self.model_instance:
            raise ValueError("Gemini model not initialized")

        # Use provided parameters or defaults
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        try:
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Generate content
            response = await self.model_instance.generate_content_async(
                prompt,
                generation_config=generation_config
            )

            # Extract response data
            text = response.text.strip()

            # Get token usage if available
            tokens_used = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens_used = (response.usage_metadata.prompt_token_count +
                             response.usage_metadata.candidates_token_count)

            return AIResponse(
                text=text,
                model=self.model,
                provider=self.name,
                tokens_used=tokens_used,
                finish_reason=getattr(response, 'finish_reason', None),
                metadata={
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    "model": self.model,
                    "id": getattr(response, 'id', None)
                }
            )

        except Exception as e:
            self.logger.error(f"Gemini generation error: {e}")
            raise ValueError(f"Gemini API error: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get list of available Gemini models."""
        if not GENAI_AVAILABLE:
            return []

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return ["gemini-pro", "gemini-pro-vision"]  # Common models
            else:
                # Get available models
                models = []
                for model in genai.list_models():
                    if "gemini" in model.name:
                        models.append(model.name.split("/")[-1])
                return models
        except Exception as e:
            self.logger.error(f"Error getting Gemini models: {e}")
            return ["gemini-pro", "gemini-pro-vision"]  # Fallback to known models

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific Gemini model."""
        model_configs = {
            "gemini-pro": {
                "name": "gemini-pro",
                "provider": "Google",
                "type": "chat",
                "context_length": 30720,
                "max_tokens": 2048,
                "description": "Google Gemini Pro model for text generation"
            },
            "gemini-pro-vision": {
                "name": "gemini-pro-vision",
                "provider": "Google",
                "type": "multimodal",
                "context_length": 16384,
                "max_tokens": 2048,
                "description": "Google Gemini Pro Vision model for text and image understanding"
            }
        }

        return model_configs.get(model, {
            "name": model,
            "provider": "Google",
            "type": "chat",
            "context_length": 30720,
            "max_tokens": 2048,
            "description": f"Google {model} model"
        })

    def update_config(self, api_key: str, model: str = "gemini-pro"):
        """Update Gemini configuration."""
        self.api_key = api_key
        self.model = model

        # Save to settings
        config = {
            "api_key": api_key,
            "model": model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        self.settings.set_ai_provider_config("gemini", config)

        # Reinitialize client
        if GENAI_AVAILABLE:
            self._initialize_client()

        self.logger.info(f"Updated Gemini config: model={model}")

    def validate_api_key(self, api_key: str) -> bool:
        """Validate Google API key format."""
        if not api_key:
            return False

        # Google API keys are typically 39 characters long and start with 'AIza'
        return api_key.startswith("AIza") and len(api_key) == 39

    def get_usage_info(self) -> Dict[str, Any]:
        """Get Gemini usage information."""
        return {
            "configured": self.is_configured(),
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "api_key_valid": self.validate_api_key(self.api_key)
        }


class GeminiProviderSync(GeminiProvider):
    """Synchronous version of Gemini provider for compatibility."""

    def __init__(self, settings: Settings):
        """Initialize synchronous Gemini provider."""
        super().__init__(settings)

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using Google Gemini (sync version)."""
        if not self.model_instance:
            raise ValueError("Gemini model not initialized")

        # Use provided parameters or defaults
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        try:
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Generate content using sync method
            response = self.model_instance.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Extract response data
            text = response.text.strip()

            # Get token usage if available
            tokens_used = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens_used = (response.usage_metadata.prompt_token_count +
                             response.usage_metadata.candidates_token_count)

            return AIResponse(
                text=text,
                model=self.model,
                provider=self.name,
                tokens_used=tokens_used,
                finish_reason=getattr(response, 'finish_reason', None),
                metadata={
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    "model": self.model,
                    "id": getattr(response, 'id', None)
                }
            )

        except Exception as e:
            self.logger.error(f"Gemini generation error: {e}")
            raise ValueError(f"Gemini API error: {str(e)}")
