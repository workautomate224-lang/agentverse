"""
LLM Router Service - Centralized LLM Gateway
Reference: GAPS.md GAP-P0-001

This service routes ALL LLM calls through a centralized gateway that:
1. Looks up the profile for a given profile_key
2. Checks cache first (if enabled)
3. Makes the LLM call via OpenRouter
4. Handles fallbacks if primary model fails
5. Logs the call for cost tracking
6. Caches the response (if enabled)

Usage:
    router = LLMRouter(db)
    response = await router.complete(
        profile_key="EVENT_COMPILER_INTENT",
        messages=[{"role": "user", "content": "..."}],
        tenant_id=tenant_id,
        project_id=project_id,
    )
"""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm import (
    LLMCache,
    LLMCall,
    LLMCallStatus,
    LLMProfile,
    LLMProfileKey,
)
from app.services.openrouter import CompletionResponse, OpenRouterService
from app.services.llm_smart_classifier import SmartClassifier, ClassificationResult, get_smart_classifier

logger = logging.getLogger(__name__)

# Professional response standards for comprehensive, high-quality outputs
PROFESSIONAL_RESPONSE_PROMPT = """You are a highly knowledgeable AI assistant providing comprehensive, professional-grade responses.

RESPONSE QUALITY STANDARDS:
1. Be thorough and detailed - provide complete, well-researched answers
2. Use clear structure with paragraphs, bullet points, or numbered lists when appropriate
3. Include relevant context, background information, and nuances
4. Cite specific facts, dates, statistics, and sources when available
5. Address multiple aspects and perspectives of the question
6. Use professional, articulate language suitable for business and academic contexts
7. Provide actionable insights and conclusions when relevant

IMPORTANT: Never give brief, dismissive, or superficial answers. Every response should demonstrate expertise and provide genuine value to the user. If you cannot answer something, explain why in detail and suggest alternatives."""


class LLMRouterResponse(BaseModel):
    """Response from LLM Router."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    response_time_ms: int
    cost_usd: float
    cache_hit: bool
    profile_key: str
    call_id: Optional[str] = None
    # Slice 1A: LLM Provenance fields for verification
    provider: str = "openrouter"  # Always "openrouter" for real LLM calls
    fallback_used: bool = False  # True if a fallback model was used
    fallback_attempts: int = 0  # Number of models tried before success
    # Advanced feature outputs
    reasoning: Optional[str] = None  # Thinking mode reasoning output
    web_search_results: Optional[List[Dict[str, Any]]] = None  # Web search results


class LLMRouterContext(BaseModel):
    """Context for LLM Router calls."""
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    run_id: Optional[str] = None
    node_id: Optional[str] = None
    user_id: Optional[str] = None
    seed: Optional[int] = None  # For deterministic replay
    phase: Optional[str] = None  # "compilation" or "tick_loop" for C5 tracking (§1.4)
    # Temporal Knowledge Isolation (temporal.md §8 Phase 4)
    temporal_mode: Optional[str] = None  # 'live' or 'backtest'
    cutoff_time: Optional[datetime] = None  # as_of_datetime for backtest
    isolation_level: int = 1  # 1=Basic, 2=Strict, 3=Audit-First
    timezone: str = "UTC"  # Timezone for cutoff
    # Advanced LLM Features (OpenRouter)
    web_search: bool = False  # Enable web search for up-to-date information
    web_search_max_results: int = 5  # Max number of web results (1-10)
    thinking_mode: bool = False  # Enable extended thinking/reasoning
    thinking_budget_tokens: Optional[int] = None  # Max tokens for reasoning
    # Smart Auto-Trigger (LLM-based pre-classification)
    auto_classify: bool = False  # Enable smart classification of prompts
    manual_web_search: Optional[bool] = None  # Manual override (None = use auto or default)
    manual_thinking_mode: Optional[bool] = None  # Manual override (None = use auto or default)
    # Slice 1A: Strict LLM mode for wizard flows (No-Fake-Success rule)
    strict_llm: bool = False  # If True, NEVER fallback - fail immediately on LLM error
    skip_cache: bool = False  # If True, bypass cache for fresh LLM calls (staging/dev)


class LLMRouter:
    """
    Centralized LLM Router that handles all LLM calls.

    Features:
    - Profile-based model selection
    - Tenant-specific profile overrides
    - Deterministic caching with seed support
    - Fallback chains on failure
    - Cost tracking and logging
    - Rate limiting (TODO)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._openrouter = OpenRouterService()
        self._smart_classifier = get_smart_classifier()
        self._profile_cache: Dict[str, LLMProfile] = {}
        self._profile_cache_time: float = 0
        self._profile_cache_ttl: float = 300  # 5 minutes

    async def complete(
        self,
        profile_key: str,
        messages: List[Dict[str, str]],
        context: Optional[LLMRouterContext] = None,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
        skip_cache: bool = False,
        **kwargs,
    ) -> LLMRouterResponse:
        """
        Route an LLM completion request through the centralized gateway.

        Args:
            profile_key: Profile key (e.g., "EVENT_COMPILER_INTENT")
            messages: List of message dicts with 'role' and 'content'
            context: Optional context with tenant_id, project_id, etc.
            temperature_override: Override profile temperature
            max_tokens_override: Override profile max_tokens
            skip_cache: Force skip cache lookup
            **kwargs: Additional args passed to OpenRouter

        Returns:
            LLMRouterResponse with content, usage metrics, and cache status
        """
        context = context or LLMRouterContext()
        start_time = time.time()

        # Slice 1A: Honor context.skip_cache flag (staging/dev cache bypass)
        should_skip_cache = skip_cache or context.skip_cache

        # 0. Smart Auto-Classification (if enabled)
        # This determines if web_search or thinking_mode should be enabled
        if context.auto_classify:
            context = await self._auto_classify_context(messages, context)

        # 1. Look up profile
        profile = await self._get_profile(profile_key, context.tenant_id)
        if not profile:
            logger.warning(f"No profile found for {profile_key}, using defaults")
            profile = self._get_default_profile(profile_key)

        # 2. Resolve parameters
        temperature = temperature_override if temperature_override is not None else profile.temperature
        max_tokens = max_tokens_override if max_tokens_override is not None else profile.max_tokens
        model = profile.model

        # 2.5 Inject backtest policy into system prompt (temporal.md §8 Phase 4)
        messages = self._inject_backtest_policy(messages, context)

        # 3. Compute cache key
        cache_key = self._compute_cache_key(
            profile_key=profile_key,
            model=model,
            messages=messages,
            temperature=temperature,
            seed=context.seed,
        )
        messages_hash = self._compute_messages_hash(messages)

        # 4. Check cache (if enabled)
        # Slice 1A: Use should_skip_cache to respect both param and context.skip_cache
        if profile.cache_enabled and not should_skip_cache:
            cached = await self._get_cached_response(cache_key)
            if cached:
                response_time_ms = int((time.time() - start_time) * 1000)

                # Log the cache hit
                call_id = await self._log_call(
                    profile=profile,
                    context=context,
                    model_requested=model,
                    model_used=model,
                    messages_hash=messages_hash,
                    input_tokens=cached.input_tokens,
                    output_tokens=cached.output_tokens,
                    response_time_ms=response_time_ms,
                    cost_usd=0.0,  # Cache hits are free
                    status=LLMCallStatus.CACHED,
                    cache_hit=True,
                    cache_key=cache_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                return LLMRouterResponse(
                    content=cached.response_content,
                    model=model,
                    input_tokens=cached.input_tokens,
                    output_tokens=cached.output_tokens,
                    total_tokens=cached.input_tokens + cached.output_tokens,
                    response_time_ms=response_time_ms,
                    cost_usd=0.0,
                    cache_hit=True,
                    profile_key=profile_key,
                    call_id=str(call_id),
                    # Slice 1A: Provenance for cached responses
                    provider="openrouter",
                    fallback_used=False,
                    fallback_attempts=0,
                )

        # 5. Make the call (with fallback support)
        response, model_used, fallback_attempts, error_message = await self._complete_with_fallback(
            profile=profile,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            web_search=context.web_search,
            web_search_max_results=context.web_search_max_results,
            thinking_mode=context.thinking_mode,
            thinking_budget_tokens=context.thinking_budget_tokens,
            **kwargs,
        )

        response_time_ms = int((time.time() - start_time) * 1000)

        if response is None:
            # All models failed
            call_id = await self._log_call(
                profile=profile,
                context=context,
                model_requested=model,
                model_used=model,
                messages_hash=messages_hash,
                input_tokens=0,
                output_tokens=0,
                response_time_ms=response_time_ms,
                cost_usd=0.0,
                status=LLMCallStatus.ERROR,
                cache_hit=False,
                cache_key=cache_key,
                temperature=temperature,
                max_tokens=max_tokens,
                error_message=error_message,
                fallback_attempts=fallback_attempts,
            )
            raise RuntimeError(f"All LLM models failed for {profile_key}: {error_message}")

        # Slice 1A: Strict LLM mode - fail if fallback was used (No-Fake-Success rule)
        if context.strict_llm and fallback_attempts > 0:
            # Log the call as failed due to strict mode
            await self._log_call(
                profile=profile,
                context=context,
                model_requested=model,
                model_used=model_used,
                messages_hash=messages_hash,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                response_time_ms=response_time_ms,
                cost_usd=0.0,
                status=LLMCallStatus.ERROR,
                cache_hit=False,
                cache_key=cache_key,
                temperature=temperature,
                max_tokens=max_tokens,
                error_message=f"strict_llm mode: fallback to {model_used} is not allowed",
                fallback_attempts=fallback_attempts,
            )
            raise RuntimeError(
                f"LLM call for {profile_key} used fallback model {model_used} "
                f"(requested: {model}). strict_llm mode requires primary model only. "
                f"Fallback attempts: {fallback_attempts}"
            )

        # 6. Calculate cost
        cost_usd = self._calculate_cost(
            model=model_used,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            profile=profile,
        )

        # 7. Cache the response (if enabled)
        if profile.cache_enabled:
            await self._cache_response(
                cache_key=cache_key,
                profile_key=profile_key,
                model=model_used,
                messages_hash=messages_hash,
                temperature=temperature,
                seed=context.seed,
                response_content=response.content,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                ttl_seconds=profile.cache_ttl_seconds,
            )

        # 8. Log the call
        status = LLMCallStatus.FALLBACK if fallback_attempts > 0 else LLMCallStatus.SUCCESS
        call_id = await self._log_call(
            profile=profile,
            context=context,
            model_requested=model,
            model_used=model_used,
            messages_hash=messages_hash,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            response_time_ms=response_time_ms,
            cost_usd=cost_usd,
            status=status,
            cache_hit=False,
            cache_key=cache_key,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback_attempts=fallback_attempts,
        )

        return LLMRouterResponse(
            content=response.content,
            model=model_used,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
            response_time_ms=response_time_ms,
            cost_usd=cost_usd,
            cache_hit=False,
            profile_key=profile_key,
            call_id=str(call_id),
            # Slice 1A: Provenance for fresh LLM calls
            provider="openrouter",
            fallback_used=fallback_attempts > 0,
            fallback_attempts=fallback_attempts,
            reasoning=response.reasoning,
            web_search_results=response.web_search_results,
        )

    async def batch_complete(
        self,
        profile_key: str,
        requests: List[Dict[str, Any]],
        context: Optional[LLMRouterContext] = None,
        concurrency: int = 10,
    ) -> List[LLMRouterResponse]:
        """
        Process multiple completion requests with concurrency control.

        Args:
            profile_key: Profile key for all requests
            requests: List of dicts with 'messages' and optional overrides
            context: Shared context for all requests
            concurrency: Maximum concurrent requests

        Returns:
            List of LLMRouterResponse objects
        """
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)

        async def limited_complete(request: Dict) -> LLMRouterResponse:
            async with semaphore:
                messages = request.pop("messages")
                return await self.complete(
                    profile_key=profile_key,
                    messages=messages,
                    context=context,
                    **request,
                )

        tasks = [limited_complete(req.copy()) for req in requests]
        return await asyncio.gather(*tasks)

    async def _get_profile(
        self,
        profile_key: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[LLMProfile]:
        """
        Get the active profile for a given key.

        Priority:
        1. Tenant-specific profile (if tenant_id provided)
        2. Global default profile
        """
        # Try tenant-specific first
        if tenant_id:
            stmt = select(LLMProfile).where(
                LLMProfile.profile_key == profile_key,
                LLMProfile.tenant_id == uuid.UUID(tenant_id),
                LLMProfile.is_active == True,
            ).order_by(LLMProfile.priority)

            result = await self.db.execute(stmt)
            profile = result.scalar_one_or_none()
            if profile:
                return profile

        # Fall back to global default
        stmt = select(LLMProfile).where(
            LLMProfile.profile_key == profile_key,
            LLMProfile.tenant_id.is_(None),
            LLMProfile.is_active == True,
        ).order_by(LLMProfile.priority)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _get_default_profile(self, profile_key: str) -> LLMProfile:
        """
        Create a default in-memory profile when none exists in DB.

        Uses gpt-5.2 as default model per Blueprint v2 requirements.
        Note: id is None to indicate this is an in-memory profile, which
        prevents foreign key violations when logging LLM calls.
        """
        return LLMProfile(
            id=None,  # No ID for in-memory profiles to avoid FK violation
            profile_key=profile_key,
            label=f"Default {profile_key}",
            model="openai/gpt-5.2",  # GPT-5.2 as default for PIL jobs
            temperature=0.3,  # Balanced for comprehensive yet consistent responses
            max_tokens=2000,  # Increased for comprehensive professional responses
            cost_per_1k_input_tokens=0.005,   # GPT-5.2 pricing
            cost_per_1k_output_tokens=0.015,  # GPT-5.2 pricing
            fallback_models=["openai/gpt-4o"],  # Fallback to GPT-4o
            cache_enabled=True,
            is_active=True,
            is_default=True,
        )

    def _inject_backtest_policy(
        self,
        messages: List[Dict[str, str]],
        context: LLMRouterContext,
    ) -> List[Dict[str, str]]:
        """
        Inject appropriate policy into system prompt based on mode.

        - Backtest mode: Concise temporal policy (saves tokens, faster responses)
        - Live mode: Professional response standards (comprehensive outputs)

        Reference: temporal.md §8 Phase 4 item 11

        Args:
            messages: Original message list
            context: LLMRouterContext with temporal settings

        Returns:
            Modified message list with policies injected
        """
        policy_text = None

        if context.temporal_mode == "backtest" and context.cutoff_time:
            # Backtest mode: Use concise temporal policy ONLY (no professional prompt)
            # This saves tokens and produces faster, more direct responses
            from app.services.llm_data_tools import get_backtest_policy_prompt

            policy_text = get_backtest_policy_prompt(
                as_of_datetime=context.cutoff_time,
                isolation_level=context.isolation_level,
                timezone=context.timezone,
            )
            logger.info(
                f"LLM_ROUTER: Injected backtest policy (as_of={context.cutoff_time}, level={context.isolation_level})"
            )
        else:
            # Live mode: Use professional response standards for comprehensive outputs
            policy_text = PROFESSIONAL_RESPONSE_PROMPT

        # Find system message and inject policy
        modified_messages = []
        policy_injected = False

        for msg in messages:
            if msg.get("role") == "system" and not policy_injected:
                # Prepend policy to existing system message
                modified_messages.append({
                    "role": "system",
                    "content": f"{policy_text}\n\n{msg.get('content', '')}"
                })
                policy_injected = True
            else:
                modified_messages.append(msg)

        # If no system message, add one with the policy
        if not policy_injected:
            modified_messages.insert(0, {
                "role": "system",
                "content": policy_text
            })

        return modified_messages

    async def _auto_classify_context(
        self,
        messages: List[Dict[str, str]],
        context: LLMRouterContext,
    ) -> LLMRouterContext:
        """
        Automatically classify the prompt to determine if web_search or
        thinking_mode should be enabled.

        This implements smart auto-trigger based on LLM pre-classification.
        Manual overrides are respected if provided.

        Args:
            messages: The message list (used to extract user prompt)
            context: The current context with auto_classify settings

        Returns:
            Updated context with web_search and thinking_mode set appropriately
        """
        # Extract user's prompt from messages (last user message)
        user_prompt = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_prompt = msg.get("content", "")
                break

        if not user_prompt:
            logger.debug("LLM_ROUTER: No user prompt found for auto-classification")
            return context

        # Run classification
        try:
            classification = await self._smart_classifier.classify(user_prompt)

            logger.info(
                f"LLM_ROUTER: Auto-classification result: "
                f"web_search={classification.web_search}, "
                f"thinking_mode={classification.thinking_mode}, "
                f"confidence={classification.confidence}, "
                f"time={classification.classification_time_ms}ms, "
                f"cache={classification.from_cache}"
            )

            # Apply classification results, respecting manual overrides
            # Priority: manual_override > auto_classification > existing_value

            # Web search: manual override wins, then classification, then default
            if context.manual_web_search is not None:
                context.web_search = context.manual_web_search
            else:
                context.web_search = classification.web_search

            # Thinking mode: manual override wins, then classification, then default
            if context.manual_thinking_mode is not None:
                context.thinking_mode = context.manual_thinking_mode
            else:
                context.thinking_mode = classification.thinking_mode

            logger.info(
                f"LLM_ROUTER: Final features: "
                f"web_search={context.web_search} (manual={context.manual_web_search}), "
                f"thinking_mode={context.thinking_mode} (manual={context.manual_thinking_mode})"
            )

        except Exception as e:
            logger.warning(f"LLM_ROUTER: Auto-classification failed: {e}, using defaults")
            # On failure, use manual overrides if provided, otherwise keep defaults
            if context.manual_web_search is not None:
                context.web_search = context.manual_web_search
            if context.manual_thinking_mode is not None:
                context.thinking_mode = context.manual_thinking_mode

        return context

    async def _complete_with_fallback(
        self,
        profile: LLMProfile,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        web_search: bool = False,
        web_search_max_results: int = 5,
        thinking_mode: bool = False,
        thinking_budget_tokens: Optional[int] = None,
        **kwargs,
    ) -> Tuple[Optional[CompletionResponse], str, int, Optional[str]]:
        """
        Make the LLM call with fallback support.

        Args:
            profile: LLM profile configuration
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Max output tokens
            web_search: Enable web search for up-to-date information
            web_search_max_results: Max number of web results (1-10)
            thinking_mode: Enable extended thinking/reasoning mode
            thinking_budget_tokens: Max tokens for reasoning

        Returns:
            (response, model_used, fallback_attempts, error_message)
        """
        models_to_try = [profile.model]
        if profile.fallback_models:
            models_to_try.extend(profile.fallback_models)

        last_error: Optional[str] = None
        fallback_attempts = 0

        for i, model in enumerate(models_to_try):
            try:
                response = await self._openrouter.complete(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    web_search=web_search,
                    web_search_max_results=web_search_max_results,
                    thinking_mode=thinking_mode,
                    thinking_budget_tokens=thinking_budget_tokens,
                    **kwargs,
                )
                return response, model, fallback_attempts, None
            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM call failed for {model}: {e}")
                if i > 0:  # Only count as fallback attempt after first model
                    fallback_attempts += 1
                continue

        return None, profile.model, fallback_attempts, last_error

    def _compute_cache_key(
        self,
        profile_key: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        seed: Optional[int] = None,
    ) -> str:
        """Compute deterministic cache key from request parameters."""
        key_data = {
            "profile_key": profile_key,
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "seed": seed,
        }
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()

    def _compute_messages_hash(self, messages: List[Dict[str, str]]) -> str:
        """Compute hash of messages for logging."""
        messages_json = json.dumps(messages, sort_keys=True)
        return hashlib.sha256(messages_json.encode()).hexdigest()

    async def _get_cached_response(self, cache_key: str) -> Optional[LLMCache]:
        """Get cached response if exists and not expired."""
        stmt = select(LLMCache).where(LLMCache.cache_key == cache_key)
        result = await self.db.execute(stmt)
        cached = result.scalar_one_or_none()

        if cached:
            # Check expiration
            if cached.expires_at and cached.expires_at < datetime.utcnow():
                return None

            # Update hit stats
            cached.hit_count += 1
            cached.last_hit_at = datetime.utcnow()
            await self.db.commit()
            return cached

        return None

    async def _cache_response(
        self,
        cache_key: str,
        profile_key: str,
        model: str,
        messages_hash: str,
        temperature: float,
        seed: Optional[int],
        response_content: str,
        input_tokens: int,
        output_tokens: int,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache a response for future replay."""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        cache_entry = LLMCache(
            cache_key=cache_key,
            profile_key=profile_key,
            model=model,
            messages_hash=messages_hash,
            temperature=temperature,
            seed=seed,
            response_content=response_content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            expires_at=expires_at,
        )

        # Upsert - update if exists, insert if not
        existing = await self._get_cached_response(cache_key)
        if existing:
            existing.response_content = response_content
            existing.input_tokens = input_tokens
            existing.output_tokens = output_tokens
            existing.expires_at = expires_at
        else:
            self.db.add(cache_entry)

        await self.db.commit()

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        profile: LLMProfile,
    ) -> float:
        """Calculate cost based on profile or model defaults."""
        return (
            (input_tokens / 1000) * profile.cost_per_1k_input_tokens +
            (output_tokens / 1000) * profile.cost_per_1k_output_tokens
        )

    async def _log_call(
        self,
        profile: LLMProfile,
        context: LLMRouterContext,
        model_requested: str,
        model_used: str,
        messages_hash: str,
        input_tokens: int,
        output_tokens: int,
        response_time_ms: int,
        cost_usd: float,
        status: LLMCallStatus,
        cache_hit: bool,
        cache_key: str,
        temperature: float,
        max_tokens: int,
        error_message: Optional[str] = None,
        fallback_attempts: int = 0,
    ) -> uuid.UUID:
        """Log the LLM call for cost tracking and debugging."""
        call = LLMCall(
            tenant_id=uuid.UUID(context.tenant_id) if context.tenant_id else None,
            profile_id=profile.id if profile.id else None,
            profile_key=profile.profile_key,
            project_id=uuid.UUID(context.project_id) if context.project_id else None,
            run_id=uuid.UUID(context.run_id) if context.run_id else None,
            node_id=uuid.UUID(context.node_id) if context.node_id else None,
            model_requested=model_requested,
            model_used=model_used,
            messages_hash=messages_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            response_time_ms=response_time_ms,
            cost_usd=cost_usd,
            status=status.value,
            error_message=error_message,
            fallback_attempts=fallback_attempts,
            cache_hit=cache_hit,
            cache_key=cache_key,
            user_id=uuid.UUID(context.user_id) if context.user_id else None,
            temperature=temperature,
            max_tokens=max_tokens,
            phase=context.phase,  # Track compilation vs tick_loop (§1.4)
        )

        self.db.add(call)
        await self.db.commit()
        await self.db.refresh(call)
        return call.id

    # =========================================================================
    # Admin API Methods
    # =========================================================================

    async def list_profiles(
        self,
        tenant_id: Optional[str] = None,
        include_global: bool = True,
    ) -> List[LLMProfile]:
        """List all profiles, optionally filtered by tenant."""
        conditions = [LLMProfile.is_active == True]

        if tenant_id and include_global:
            conditions.append(
                (LLMProfile.tenant_id == uuid.UUID(tenant_id)) |
                (LLMProfile.tenant_id.is_(None))
            )
        elif tenant_id:
            conditions.append(LLMProfile.tenant_id == uuid.UUID(tenant_id))
        elif include_global:
            conditions.append(LLMProfile.tenant_id.is_(None))

        stmt = select(LLMProfile).where(*conditions).order_by(
            LLMProfile.profile_key, LLMProfile.priority
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_profile(self, profile_id: str) -> Optional[LLMProfile]:
        """Get a specific profile by ID."""
        stmt = select(LLMProfile).where(LLMProfile.id == uuid.UUID(profile_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_profile(
        self,
        profile_key: str,
        label: str,
        model: str,
        tenant_id: Optional[str] = None,
        created_by_id: Optional[str] = None,
        **kwargs,
    ) -> LLMProfile:
        """Create a new LLM profile."""
        profile = LLMProfile(
            profile_key=profile_key,
            label=label,
            model=model,
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            created_by_id=uuid.UUID(created_by_id) if created_by_id else None,
            **kwargs,
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_profile(
        self,
        profile_id: str,
        **kwargs,
    ) -> Optional[LLMProfile]:
        """Update an existing profile."""
        profile = await self.get_profile(profile_id)
        if not profile:
            return None

        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)

        profile.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_profile(self, profile_id: str) -> bool:
        """Soft-delete a profile by marking it inactive."""
        profile = await self.get_profile(profile_id)
        if not profile:
            return False

        profile.is_active = False
        profile.updated_at = datetime.utcnow()
        await self.db.commit()
        return True

    # =========================================================================
    # Cost Tracking Methods
    # =========================================================================

    async def get_cost_summary(
        self,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get cost summary for a tenant or project."""
        from sqlalchemy import func

        conditions = []
        if tenant_id:
            conditions.append(LLMCall.tenant_id == uuid.UUID(tenant_id))
        if project_id:
            conditions.append(LLMCall.project_id == uuid.UUID(project_id))
        if start_date:
            conditions.append(LLMCall.created_at >= start_date)
        if end_date:
            conditions.append(LLMCall.created_at <= end_date)

        stmt = select(
            func.count(LLMCall.id).label("total_calls"),
            func.sum(LLMCall.cost_usd).label("total_cost_usd"),
            func.sum(LLMCall.input_tokens).label("total_input_tokens"),
            func.sum(LLMCall.output_tokens).label("total_output_tokens"),
            func.sum(LLMCall.total_tokens).label("total_tokens"),
            func.avg(LLMCall.response_time_ms).label("avg_response_time_ms"),
            func.count(LLMCall.id).filter(LLMCall.cache_hit == True).label("cache_hits"),
        ).where(*conditions) if conditions else select(
            func.count(LLMCall.id).label("total_calls"),
            func.sum(LLMCall.cost_usd).label("total_cost_usd"),
            func.sum(LLMCall.input_tokens).label("total_input_tokens"),
            func.sum(LLMCall.output_tokens).label("total_output_tokens"),
            func.sum(LLMCall.total_tokens).label("total_tokens"),
            func.avg(LLMCall.response_time_ms).label("avg_response_time_ms"),
            func.count(LLMCall.id).filter(LLMCall.cache_hit == True).label("cache_hits"),
        )

        result = await self.db.execute(stmt)
        row = result.one()

        total_calls = row.total_calls or 0
        cache_hits = row.cache_hits or 0

        return {
            "total_calls": total_calls,
            "total_cost_usd": float(row.total_cost_usd or 0),
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "avg_response_time_ms": float(row.avg_response_time_ms or 0),
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hits / total_calls if total_calls > 0 else 0,
        }

    async def get_cost_by_profile(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by profile."""
        from sqlalchemy import func

        conditions = []
        if tenant_id:
            conditions.append(LLMCall.tenant_id == uuid.UUID(tenant_id))
        if start_date:
            conditions.append(LLMCall.created_at >= start_date)
        if end_date:
            conditions.append(LLMCall.created_at <= end_date)

        stmt = select(
            LLMCall.profile_key,
            func.count(LLMCall.id).label("call_count"),
            func.sum(LLMCall.cost_usd).label("total_cost_usd"),
            func.sum(LLMCall.total_tokens).label("total_tokens"),
        ).group_by(LLMCall.profile_key)

        if conditions:
            stmt = stmt.where(*conditions)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "profile_key": row.profile_key,
                "call_count": row.call_count,
                "total_cost_usd": float(row.total_cost_usd or 0),
                "total_tokens": row.total_tokens or 0,
            }
            for row in rows
        ]


# =============================================================================
# Convenience function for creating router
# =============================================================================

def get_llm_router(db: AsyncSession) -> LLMRouter:
    """Factory function to create an LLMRouter instance."""
    return LLMRouter(db)
