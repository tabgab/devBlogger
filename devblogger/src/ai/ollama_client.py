#!/usr/bin/env python3
"""
DevBlogger - Ollama local AI provider
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
import aiohttp
import requests

from .base import AIProvider, AIResponse
from ..config.settings import Settings


class OllamaProvider(AIProvider):
    """Ollama local AI provider."""

    def __init__(self, settings: Settings):
        """Initialize Ollama provider."""
        super().__init__("ollama", "llama2")

        self.settings = settings
        self.base_url = "http://localhost:11434"
        self.client = None

        # Load configuration
        self._load_config()

    def _load_config(self):
        """Load Ollama configuration from settings."""
        try:
            config = self.settings.get_ai_provider_config("ollama")
            self.base_url = config.get("base_url", "http://localhost:11434")
            self.model = config.get("model", "llama2")
            self.max_tokens = config.get("max_tokens", 2000)
            self.temperature = config.get("temperature", 0.7)
        except Exception as e:
            self.logger.error(f"Error loading Ollama config: {e}")

    def is_configured(self) -> bool:
        """Check if Ollama is properly configured."""
        # Ollama is always considered "configured" if the base URL is set
        # The actual availability will be checked at runtime
        return bool(self.base_url and self.model)

    def test_connection(self) -> bool:
        """Test connection to Ollama server."""
        if not self.is_configured():
            return False

        try:
            # Try to get available models as a connection test
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return True  # Assume configured means working
            else:
                # Test with a simple API call
                response = asyncio.run(self._test_api_call())
                return bool(response)
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {e}")
            return False

    async def _test_api_call(self) -> bool:
        """Test Ollama API with a simple call."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return "models" in data
                    return False
        except Exception:
            return False

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using Ollama."""
        # Use provided parameters or defaults
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        try:
            # Prepare request data
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    **kwargs
                }
            }

            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"Ollama API error: {response.status} - {error_text}")

                    data = await response.json()

            # Extract response data
            text = data.get("response", "").strip()

            # Calculate token usage (approximate)
            tokens_used = len(prompt.split()) + len(text.split())

            return AIResponse(
                text=text,
                model=self.model,
                provider=self.name,
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata={
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "eval_duration": data.get("eval_duration"),
                    "eval_count": data.get("eval_count")
                }
            )

        except Exception as e:
            self.logger.error(f"Ollama generation error: {e}")
            raise ValueError(f"Ollama API error: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return [self.model]  # Return current model if in async context
            else:
                # Get available models from API
                response = asyncio.run(self._get_models_api())
                return response
        except Exception as e:
            self.logger.error(f"Error getting Ollama models: {e}")
            return [self.model]  # Fallback to current model

    async def _get_models_api(self) -> List[str]:
        """Get available models from Ollama API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["name"] for model in data.get("models", [])]
                    return [self.model]
        except Exception:
            return [self.model]

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific Ollama model."""
        return {
            "name": model,
            "provider": "Ollama",
            "type": "local",
            "context_length": 4096,  # Default for most Ollama models
            "max_tokens": self.max_tokens,
            "description": f"Local Ollama {model} model"
        }

    def update_config(self, base_url: str, model: str = "llama2"):
        """Update Ollama configuration."""
        self.base_url = base_url
        self.model = model

        # Save to settings
        config = {
            "base_url": base_url,
            "model": model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        self.settings.set_ai_provider_config("ollama", config)

        self.logger.info(f"Updated Ollama config: base_url={base_url}, model={model}")

    def validate_base_url(self, base_url: str) -> bool:
        """Validate Ollama base URL format."""
        if not base_url:
            return False

        try:
            # Basic URL validation
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def get_usage_info(self) -> Dict[str, Any]:
        """Get Ollama usage information."""
        return {
            "configured": self.is_configured(),
            "model": self.model,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "base_url_valid": self.validate_base_url(self.base_url)
        }

    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return False  # Can't pull in async context
            else:
                return asyncio.run(self._pull_model_async(model_name))
        except Exception as e:
            self.logger.error(f"Error pulling model {model_name}: {e}")
            return False

    async def _pull_model_async(self, model_name: str) -> bool:
        """Pull model asynchronously."""
        try:
            request_data = {"name": model_name}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/pull",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=600)  # 10 minute timeout for pulls
                ) as response:
                    if response.status == 200:
                        # Stream the response to show progress
                        async for line in response.content:
                            if line:
                                try:
                                    data = json.loads(line.decode())
                                    if "status" in data:
                                        self.logger.info(f"Pull progress: {data['status']}")
                                except json.JSONDecodeError:
                                    pass
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Pull failed: {response.status} - {error_text}")
                        return False
        except Exception as e:
            self.logger.error(f"Error pulling model: {e}")
            return False

    def check_model_exists(self, model_name: str) -> bool:
        """Check if a model exists locally."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return model_name == self.model  # Assume current model exists
            else:
                models = asyncio.run(self._get_models_api())
                return model_name in models
        except Exception:
            return model_name == self.model  # Fallback


class OllamaProviderSync(OllamaProvider):
    """Synchronous version of Ollama provider for compatibility."""

    def __init__(self, settings: Settings):
        """Initialize synchronous Ollama provider."""
        super().__init__(settings)

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using Ollama (sync version)."""
        # Use provided parameters or defaults
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        try:
            # Prepare request data
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    **kwargs
                }
            }

            # Make synchronous API call
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_data,
                timeout=300  # 5 minute timeout
            )

            if response.status_code != 200:
                raise ValueError(f"Ollama API error: {response.status_code} - {response.text}")

            data = response.json()

            # Extract response data
            text = data.get("response", "").strip()

            # Calculate token usage (approximate)
            tokens_used = len(prompt.split()) + len(text.split())

            return AIResponse(
                text=text,
                model=self.model,
                provider=self.name,
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata={
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "eval_duration": data.get("eval_duration"),
                    "eval_count": data.get("eval_count")
                }
            )

        except Exception as e:
            self.logger.error(f"Ollama generation error: {e}")
            raise ValueError(f"Ollama API error: {str(e)}")
