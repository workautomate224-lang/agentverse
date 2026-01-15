"""
LLM Smart Classifier Service

This service analyzes prompts to automatically determine if web search
or thinking mode should be enabled. It uses LLM-based pre-classification
to make intelligent decisions without manual intervention.

Key Design:
- Uses gpt-5.2 for accurate classification
- Caches classification results for similar prompts
- Timeout: 3 seconds max with fallback to defaults
- For multi-agent orchestration: fully automatic (no manual override)
- For user prompts: optional manual override available

Reference: Plan "Smart Auto-Trigger for Web Search & Thinking Mode"
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClassificationResult(BaseModel):
    """Result from the smart classifier."""
    web_search: bool = False
    thinking_mode: bool = False
    confidence: float = 0.0
    reasoning: Optional[str] = None
    classification_time_ms: int = 0
    from_cache: bool = False


# Classification cache (in-memory, TTL-based)
# Key: hash of prompt, Value: (ClassificationResult, timestamp)
_classification_cache: Dict[str, tuple[ClassificationResult, float]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


# Classifier prompt - concise for fast classification
CLASSIFIER_SYSTEM_PROMPT = """You are a prompt classifier. Analyze the user's prompt and determine which capabilities are needed.

OUTPUT FORMAT (JSON only, no markdown):
{"web_search": true/false, "thinking_mode": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}

CLASSIFICATION RULES:

WEB_SEARCH = true if prompt:
- Asks about current events, news, recent happenings
- Requests real-time data (stock prices, weather, sports scores)
- Contains words like "today", "latest", "current", "now", "recent", "2025", "2026"
- Asks about things that change frequently (prices, availability, status)
- Requests up-to-date information that may have changed since training

WEB_SEARCH = false if prompt:
- Asks about general knowledge, concepts, history
- Requests code, math, or logical problem solving
- Asks for opinions, analysis, or explanations of stable topics

THINKING_MODE = true if prompt:
- Requires deep analysis, comparison, or evaluation
- Uses words like "analyze", "compare", "evaluate", "pros and cons"
- Asks for step-by-step reasoning or explanations
- Involves complex multi-part problems
- Requests strategic planning or decision-making
- Needs careful consideration of trade-offs

THINKING_MODE = false if prompt:
- Simple factual questions
- Straightforward requests
- Creative writing without complex analysis
- Basic information retrieval"""


class SmartClassifier:
    """
    LLM-based smart classifier that analyzes prompts to determine
    if web search or thinking mode should be enabled.

    Usage:
        classifier = SmartClassifier()
        result = await classifier.classify("What is Tesla stock price today?")
        # result.web_search = True, result.thinking_mode = False

        result = await classifier.classify("Analyze pros and cons of EVs vs hydrogen")
        # result.web_search = False, result.thinking_mode = True
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        classifier_model: str = "openai/gpt-5.2",
        timeout_seconds: float = 3.0,
    ):
        """
        Initialize the smart classifier.

        Args:
            api_key: OpenRouter API key (defaults to settings)
            base_url: OpenRouter base URL (defaults to settings)
            classifier_model: Model to use for classification (fast & cheap)
            timeout_seconds: Maximum time for classification before fallback
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.classifier_model = classifier_model
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            logger.warning("SmartClassifier: No API key configured, will use defaults")

    async def classify(
        self,
        prompt: str,
        skip_cache: bool = False,
    ) -> ClassificationResult:
        """
        Classify a prompt to determine if web search or thinking mode is needed.

        Args:
            prompt: The user prompt to classify
            skip_cache: Force skip cache lookup

        Returns:
            ClassificationResult with web_search and thinking_mode decisions
        """
        start_time = time.time()

        # 1. Check cache first
        if not skip_cache:
            cached = self._get_cached(prompt)
            if cached:
                cached.from_cache = True
                cached.classification_time_ms = int((time.time() - start_time) * 1000)
                logger.debug(f"SmartClassifier: Cache hit for prompt hash")
                return cached

        # 2. Quick heuristic check (skip LLM for obvious cases)
        heuristic_result = self._quick_heuristic_check(prompt)
        if heuristic_result and heuristic_result.confidence >= 0.9:
            self._cache_result(prompt, heuristic_result)
            heuristic_result.classification_time_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"SmartClassifier: Heuristic match (confidence={heuristic_result.confidence})")
            return heuristic_result

        # 3. LLM classification with timeout
        try:
            result = await asyncio.wait_for(
                self._classify_with_llm(prompt),
                timeout=self.timeout_seconds
            )
            result.classification_time_ms = int((time.time() - start_time) * 1000)
            self._cache_result(prompt, result)
            return result

        except asyncio.TimeoutError:
            logger.warning(f"SmartClassifier: Timeout after {self.timeout_seconds}s, using defaults")
            return ClassificationResult(
                web_search=False,
                thinking_mode=False,
                confidence=0.0,
                reasoning="Classification timed out, using defaults",
                classification_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.warning(f"SmartClassifier: Error during classification: {e}")
            return ClassificationResult(
                web_search=False,
                thinking_mode=False,
                confidence=0.0,
                reasoning=f"Classification error: {str(e)}",
                classification_time_ms=int((time.time() - start_time) * 1000),
            )

    def _quick_heuristic_check(self, prompt: str) -> Optional[ClassificationResult]:
        """
        Quick heuristic check for obvious cases to avoid LLM call.
        Returns None if uncertain and LLM should be used.
        """
        prompt_lower = prompt.lower()

        # Strong web search indicators
        web_search_keywords = [
            "today", "latest", "current", "now", "recent",
            "stock price", "weather", "news", "happening",
            "2025", "2026", "right now", "this week", "this month",
            "breaking", "update", "score", "result"
        ]

        # Strong thinking mode indicators
        thinking_keywords = [
            "analyze", "analyse", "compare", "evaluate", "pros and cons",
            "step by step", "explain why", "reasoning", "trade-off",
            "design", "architect", "plan", "strategy", "decision",
            "advantages and disadvantages", "in-depth", "comprehensive analysis"
        ]

        # Check for web search indicators
        web_search_score = sum(1 for kw in web_search_keywords if kw in prompt_lower)

        # Check for thinking mode indicators
        thinking_score = sum(1 for kw in thinking_keywords if kw in prompt_lower)

        # High confidence if multiple strong indicators
        if web_search_score >= 2:
            return ClassificationResult(
                web_search=True,
                thinking_mode=thinking_score >= 2,
                confidence=0.9,
                reasoning=f"Heuristic: {web_search_score} web search keywords detected"
            )

        if thinking_score >= 2:
            return ClassificationResult(
                web_search=False,
                thinking_mode=True,
                confidence=0.9,
                reasoning=f"Heuristic: {thinking_score} thinking mode keywords detected"
            )

        # Not confident enough, use LLM
        return None

    async def _classify_with_llm(self, prompt: str) -> ClassificationResult:
        """
        Use LLM to classify the prompt.
        """
        if not self.api_key:
            return ClassificationResult(
                web_search=False,
                thinking_mode=False,
                confidence=0.0,
                reasoning="No API key configured"
            )

        messages = [
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify this prompt:\n\n{prompt}"}
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://agentverse.ai",
                    "X-Title": "AgentVerse SmartClassifier",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.classifier_model,
                    "messages": messages,
                    "temperature": 0.0,  # Deterministic for consistent classification
                    "max_tokens": 150,   # Small output needed
                },
                timeout=self.timeout_seconds + 1,
            )

            response.raise_for_status()
            data = response.json()

        # Parse the classification result
        content = data["choices"][0]["message"]["content"].strip()

        try:
            # Handle potential markdown wrapping
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            result = json.loads(content)
            return ClassificationResult(
                web_search=result.get("web_search", False),
                thinking_mode=result.get("thinking_mode", False),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", ""),
            )
        except json.JSONDecodeError:
            logger.warning(f"SmartClassifier: Failed to parse LLM response: {content}")
            # Try to extract boolean values from text
            return ClassificationResult(
                web_search="web_search\": true" in content.lower() or "web_search\":true" in content.lower(),
                thinking_mode="thinking_mode\": true" in content.lower() or "thinking_mode\":true" in content.lower(),
                confidence=0.5,
                reasoning=f"Parsed from malformed response: {content[:100]}",
            )

    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:32]

    def _get_cached(self, prompt: str) -> Optional[ClassificationResult]:
        """Get cached classification result if exists and not expired."""
        cache_key = self._get_cache_key(prompt)
        if cache_key in _classification_cache:
            result, timestamp = _classification_cache[cache_key]
            if time.time() - timestamp < _CACHE_TTL_SECONDS:
                return ClassificationResult(
                    web_search=result.web_search,
                    thinking_mode=result.thinking_mode,
                    confidence=result.confidence,
                    reasoning=result.reasoning,
                )
        return None

    def _cache_result(self, prompt: str, result: ClassificationResult) -> None:
        """Cache a classification result."""
        cache_key = self._get_cache_key(prompt)
        _classification_cache[cache_key] = (result, time.time())

        # Prune cache if too large
        if len(_classification_cache) > 10000:
            # Remove oldest entries
            sorted_keys = sorted(
                _classification_cache.keys(),
                key=lambda k: _classification_cache[k][1]
            )
            for key in sorted_keys[:5000]:
                del _classification_cache[key]

    @staticmethod
    def clear_cache() -> None:
        """Clear the classification cache."""
        global _classification_cache
        _classification_cache = {}


# Singleton instance for convenience
_classifier_instance: Optional[SmartClassifier] = None


def get_smart_classifier() -> SmartClassifier:
    """Get or create the singleton SmartClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = SmartClassifier()
    return _classifier_instance
