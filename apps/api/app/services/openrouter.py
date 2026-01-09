"""
OpenRouter Integration Service
Provides access to multiple LLM providers through a unified API.
"""

import asyncio
import time
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings


class ModelConfig(BaseModel):
    """Configuration for a specific model."""
    model: str
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    max_tokens: int = 1000
    temperature: float = 0.7
    description: str = ""


# Available models via OpenRouter
AVAILABLE_MODELS = {
    "fast": ModelConfig(
        model="openai/gpt-4o-mini",
        cost_per_1k_input_tokens=0.00015,
        cost_per_1k_output_tokens=0.0006,
        max_tokens=500,
        temperature=0.7,
        description="Fast and cost-effective for high-volume simulations",
    ),
    "balanced": ModelConfig(
        model="anthropic/claude-3-haiku-20240307",
        cost_per_1k_input_tokens=0.00025,
        cost_per_1k_output_tokens=0.00125,
        max_tokens=750,
        temperature=0.7,
        description="Good balance of quality and cost",
    ),
    "quality": ModelConfig(
        model="anthropic/claude-3-5-sonnet-20241022",
        cost_per_1k_input_tokens=0.003,
        cost_per_1k_output_tokens=0.015,
        max_tokens=1000,
        temperature=0.7,
        description="High quality for complex scenarios",
    ),
    "premium": ModelConfig(
        model="openai/gpt-4o",
        cost_per_1k_input_tokens=0.0025,
        cost_per_1k_output_tokens=0.01,
        max_tokens=1000,
        temperature=0.7,
        description="Premium quality for critical simulations",
    ),
}


class CompletionResponse(BaseModel):
    """Response from OpenRouter completion."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    response_time_ms: int
    cost_usd: float


class OpenRouterService:
    """Service for interacting with OpenRouter API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.default_model = settings.DEFAULT_MODEL

        if not self.api_key:
            raise ValueError("OpenRouter API key is required")

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> CompletionResponse:
        """
        Get a completion from OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., 'openai/gpt-4o-mini')
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response

        Returns:
            CompletionResponse with content and usage metrics
        """
        model = model or self.default_model
        start_time = time.time()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://agentverse.ai",
                    "X-Title": "AgentVerse Simulation",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs,
                },
                timeout=60.0,
            )

            response.raise_for_status()
            data = response.json()

        response_time_ms = int((time.time() - start_time) * 1000)

        # Extract usage info
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Calculate cost based on model
        model_config = self._get_model_config(model)
        cost_usd = (
            (input_tokens / 1000) * model_config.cost_per_1k_input_tokens +
            (output_tokens / 1000) * model_config.cost_per_1k_output_tokens
        )

        return CompletionResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            response_time_ms=response_time_ms,
            cost_usd=cost_usd,
        )

    async def batch_complete(
        self,
        requests: list[dict[str, Any]],
        concurrency: int = 10,
    ) -> list[CompletionResponse]:
        """
        Process multiple completion requests with concurrency control.

        Args:
            requests: List of dicts with 'messages' and optional 'model', 'temperature', etc.
            concurrency: Maximum concurrent requests

        Returns:
            List of CompletionResponse objects
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_complete(request: dict) -> CompletionResponse:
            async with semaphore:
                return await self.complete(**request)

        tasks = [limited_complete(req) for req in requests]
        return await asyncio.gather(*tasks)

    def _get_model_config(self, model: str) -> ModelConfig:
        """Get model configuration by model ID or preset name."""
        # Check if it's a preset name
        if model in AVAILABLE_MODELS:
            return AVAILABLE_MODELS[model]

        # Check if any preset matches the model ID
        for preset in AVAILABLE_MODELS.values():
            if preset.model == model:
                return preset

        # Default to fast model costs if unknown
        return AVAILABLE_MODELS["fast"]

    @staticmethod
    def list_available_models() -> dict[str, ModelConfig]:
        """List all available model presets."""
        return AVAILABLE_MODELS

    async def test_connection(self) -> bool:
        """Test the OpenRouter connection."""
        try:
            response = await self.complete(
                messages=[{"role": "user", "content": "Say 'OK' and nothing else."}],
                max_tokens=10,
            )
            return "ok" in response.content.lower()
        except Exception:
            return False
