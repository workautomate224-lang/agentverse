"""
Focus Group Service
Orchestrates virtual focus group interviews with LLM-powered AI agents.

Features:
- Real-time streaming interview responses
- Follow-up questions with conversation history
- Multi-agent group discussions
- Sentiment and emotion analysis
"""

import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator, Optional, List, Dict, Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.focus_group import FocusGroupSession, FocusGroupMessage
from app.models.product import Product, ProductRun, AgentInteraction
# LLM Router Integration (GAPS.md GAP-P0-001)
from app.services.llm_router import LLMRouter, LLMRouterContext
# Keep AVAILABLE_MODELS for model selection in focus groups
from app.services.openrouter import AVAILABLE_MODELS


class FocusGroupService:
    """Service for managing virtual focus group sessions."""

    def __init__(self, db: AsyncSession, user_id: UUID, llm_router: Optional[LLMRouter] = None):
        self.db = db
        self.user_id = user_id
        self.llm_router = llm_router or LLMRouter(db)

    # ============= Session Management =============

    async def create_session(
        self,
        product_id: UUID,
        name: str,
        agent_ids: List[str],
        run_id: Optional[UUID] = None,
        session_type: str = "individual_interview",
        topic: Optional[str] = None,
        objectives: Optional[List[str]] = None,
        discussion_guide: Optional[List[dict]] = None,
        model_preset: str = "balanced",
        temperature: float = 0.7,
        moderator_style: str = "neutral",
    ) -> FocusGroupSession:
        """Create a new focus group session."""
        # Load agent contexts from interactions
        agent_contexts = await self._load_agent_contexts(agent_ids)

        session = FocusGroupSession(
            product_id=product_id,
            run_id=run_id,
            user_id=self.user_id,
            name=name,
            session_type=session_type,
            topic=topic,
            objectives=objectives or [],
            agent_ids=agent_ids,
            agent_contexts=agent_contexts,
            discussion_guide=discussion_guide,
            model_preset=model_preset,
            temperature=temperature,
            moderator_style=moderator_style,
        )

        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def get_session(self, session_id: UUID) -> Optional[FocusGroupSession]:
        """Get a session by ID."""
        result = await self.db.execute(
            select(FocusGroupSession)
            .options(selectinload(FocusGroupSession.messages))
            .where(FocusGroupSession.id == session_id)
            .where(FocusGroupSession.user_id == self.user_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        product_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FocusGroupSession]:
        """List focus group sessions."""
        query = select(FocusGroupSession).where(
            FocusGroupSession.user_id == self.user_id
        )

        if product_id:
            query = query.where(FocusGroupSession.product_id == product_id)
        if status:
            query = query.where(FocusGroupSession.status == status)

        query = query.order_by(FocusGroupSession.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_session(
        self,
        session_id: UUID,
        **updates
    ) -> Optional[FocusGroupSession]:
        """Update a session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        for key, value in updates.items():
            if hasattr(session, key) and value is not None:
                setattr(session, key, value)

        session.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def end_session(self, session_id: UUID) -> Optional[FocusGroupSession]:
        """End a focus group session and generate summary."""
        session = await self.get_session(session_id)
        if not session:
            return None

        session.status = "completed"
        session.ended_at = datetime.utcnow()

        # Generate insights summary
        summary = await self._generate_session_summary(session)
        session.insights_summary = summary.get("executive_summary")
        session.key_themes = summary.get("key_themes", [])

        await self.db.flush()
        await self.db.refresh(session)

        return session

    # ============= Interview Operations =============

    async def interview_agent(
        self,
        session_id: UUID,
        question: str,
        target_agent_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a question to an agent and get a response."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        # Get target agent
        agent_id = target_agent_id or (session.agent_ids[0] if session.agent_ids else None)
        if not agent_id:
            raise ValueError("No agent specified")

        agent_context = session.agent_contexts.get(agent_id, {})

        # Get conversation history for this agent
        history = await self._get_conversation_history(session_id, agent_id)

        # Build messages for LLM
        messages = self._build_interview_messages(
            agent_context=agent_context,
            history=history,
            question=question,
            additional_context=context,
            moderator_style=session.moderator_style,
        )

        # Get model config for max_tokens
        model_config = AVAILABLE_MODELS.get(session.model_preset, AVAILABLE_MODELS["balanced"])

        start_time = time.time()

        # Call LLM via LLMRouter with FOCUS_GROUP_DIALOGUE profile
        # Phase="interactive" for focus group sessions (§1.4 - distinct from compilation/tick_loop)
        context = LLMRouterContext(phase="interactive")
        response = await self.llm_router.complete(
            profile_key="FOCUS_GROUP_DIALOGUE",
            messages=messages,
            context=context,
            temperature_override=session.temperature,
            max_tokens_override=model_config.max_tokens,
        )

        response_time_ms = int((time.time() - start_time) * 1000)

        # Analyze sentiment and emotion
        analysis = await self._analyze_response(response.content)

        # Save moderator message
        await self._save_message(
            session_id=session_id,
            role="moderator",
            content=question,
        )

        # Save agent response
        message = await self._save_message(
            session_id=session_id,
            role="agent",
            content=response.content,
            agent_id=agent_id,
            agent_name=agent_context.get("persona", {}).get("name", f"Agent {agent_id[:8]}"),
            sentiment_score=analysis.get("sentiment_score"),
            emotion=analysis.get("emotion"),
            confidence=analysis.get("confidence"),
            key_points=analysis.get("key_points"),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            response_time_ms=response_time_ms,
        )

        # Update session stats
        session.message_count += 2
        session.total_tokens += response.total_tokens
        session.estimated_cost += response.cost_usd
        await self.db.flush()

        return {
            "agent_id": agent_id,
            "agent_name": agent_context.get("persona", {}).get("name"),
            "persona_summary": agent_context.get("persona", {}),
            "response": response.content,
            "sentiment_score": analysis.get("sentiment_score", 0),
            "emotion": analysis.get("emotion", "neutral"),
            "confidence": analysis.get("confidence", 0.7),
            "key_points": analysis.get("key_points", []),
            "response_time_ms": response_time_ms,
        }

    async def interview_agent_stream(
        self,
        session_id: UUID,
        question: str,
        target_agent_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream an interview response from an agent."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        # Get target agent
        agent_id = target_agent_id or (session.agent_ids[0] if session.agent_ids else None)
        if not agent_id:
            raise ValueError("No agent specified")

        agent_context = session.agent_contexts.get(agent_id, {})
        agent_name = agent_context.get("persona", {}).get("name", f"Agent {agent_id[:8]}")

        # Get conversation history
        history = await self._get_conversation_history(session_id, agent_id)

        # Build messages
        messages = self._build_interview_messages(
            agent_context=agent_context,
            history=history,
            question=question,
            additional_context=context,
            moderator_style=session.moderator_style,
        )

        model_config = AVAILABLE_MODELS.get(session.model_preset, AVAILABLE_MODELS["balanced"])

        start_time = time.time()
        full_response = ""
        input_tokens = 0
        output_tokens = 0

        # Save moderator message first
        await self._save_message(
            session_id=session_id,
            role="moderator",
            content=question,
        )

        # Stream response (uses direct OpenRouter API for streaming support)
        base_url = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
        api_key = settings.OPENROUTER_API_KEY

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://agentverse.ai",
                    "X-Title": "AgentVerse Focus Group",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_config.model,
                    "messages": messages,
                    "temperature": session.temperature,
                    "max_tokens": model_config.max_tokens,
                    "stream": True,
                },
                timeout=60.0,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                full_response += content
                                yield {
                                    "agent_id": agent_id,
                                    "agent_name": agent_name,
                                    "chunk": content,
                                    "is_final": False,
                                }

                            # Get usage if available
                            usage = chunk_data.get("usage", {})
                            if usage:
                                input_tokens = usage.get("prompt_tokens", 0)
                                output_tokens = usage.get("completion_tokens", 0)

                        except json.JSONDecodeError:
                            continue

        response_time_ms = int((time.time() - start_time) * 1000)

        # Analyze final response
        analysis = await self._analyze_response(full_response)

        # Save agent response
        await self._save_message(
            session_id=session_id,
            role="agent",
            content=full_response,
            agent_id=agent_id,
            agent_name=agent_name,
            sentiment_score=analysis.get("sentiment_score"),
            emotion=analysis.get("emotion"),
            confidence=analysis.get("confidence"),
            key_points=analysis.get("key_points"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=response_time_ms,
        )

        # Update session stats
        session.message_count += 2
        session.total_tokens += input_tokens + output_tokens
        await self.db.flush()

        # Yield final chunk with analysis
        yield {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "chunk": "",
            "is_final": True,
            "sentiment_score": analysis.get("sentiment_score"),
            "emotion": analysis.get("emotion"),
        }

    async def group_discussion(
        self,
        session_id: UUID,
        topic: str,
        initial_question: str,
        max_turns: int = 5,
        agent_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run a group discussion with multiple agents."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        participants = agent_ids or session.agent_ids
        if len(participants) < 2:
            raise ValueError("Group discussion requires at least 2 agents")

        turns = []
        consensus_points = []
        disagreement_points = []
        all_themes = []

        # Save moderator opening
        await self._save_message(
            session_id=session_id,
            role="moderator",
            content=f"Topic: {topic}\n\n{initial_question}",
        )

        # Initial round - everyone responds
        for agent_id in participants:
            response = await self.interview_agent(
                session_id=session_id,
                question=initial_question,
                target_agent_id=agent_id,
                context=f"This is a group discussion about: {topic}. You are one of {len(participants)} participants.",
            )
            turns.append({
                "turn_number": 1,
                "agent_id": agent_id,
                "agent_name": response["agent_name"],
                "response": response["response"],
                "responding_to": None,
                "sentiment_score": response["sentiment_score"],
                "emotion": response["emotion"],
            })
            all_themes.extend(response.get("key_points", []))

        # Discussion rounds
        for turn_num in range(2, max_turns + 1):
            # Pick a random agent to respond
            for agent_id in participants:
                # Build context from previous turns
                prev_responses = "\n".join([
                    f"{t['agent_name']}: {t['response'][:200]}..."
                    for t in turns[-len(participants):]
                ])

                follow_up = f"Based on what others have said:\n{prev_responses}\n\nWhat are your thoughts? Do you agree or disagree with any points?"

                response = await self.interview_agent(
                    session_id=session_id,
                    question=follow_up,
                    target_agent_id=agent_id,
                    context=f"This is turn {turn_num} of a group discussion about: {topic}",
                )

                turns.append({
                    "turn_number": turn_num,
                    "agent_id": agent_id,
                    "agent_name": response["agent_name"],
                    "response": response["response"],
                    "responding_to": "group",
                    "sentiment_score": response["sentiment_score"],
                    "emotion": response["emotion"],
                })
                all_themes.extend(response.get("key_points", []))

        # Analyze for consensus and disagreement
        consensus_points, disagreement_points = await self._analyze_group_discussion(turns)

        # Get unique themes
        key_themes = list(set(all_themes))[:10]

        # Calculate sentiment summary
        sentiments = [t["sentiment_score"] for t in turns if t.get("sentiment_score")]
        sentiment_summary = {
            "average": sum(sentiments) / len(sentiments) if sentiments else 0,
            "min": min(sentiments) if sentiments else 0,
            "max": max(sentiments) if sentiments else 0,
        }

        return {
            "topic": topic,
            "turns": turns,
            "consensus_points": consensus_points,
            "disagreement_points": disagreement_points,
            "key_themes": key_themes,
            "sentiment_summary": sentiment_summary,
        }

    # ============= Agent Context Management =============

    async def _load_agent_contexts(self, agent_ids: List[str]) -> Dict[str, Any]:
        """Load agent contexts from their previous interactions."""
        contexts = {}

        for agent_id in agent_ids:
            try:
                agent_uuid = UUID(agent_id)
                result = await self.db.execute(
                    select(AgentInteraction).where(AgentInteraction.id == agent_uuid)
                )
                interaction = result.scalar_one_or_none()

                if interaction:
                    contexts[agent_id] = {
                        "persona": interaction.persona_summary,
                        "previous_responses": interaction.responses,
                        "sentiment_baseline": interaction.sentiment_overall,
                        "key_themes": interaction.key_themes,
                    }
            except (ValueError, Exception):
                # Invalid UUID or interaction not found
                contexts[agent_id] = {"persona": {}, "previous_responses": {}}

        return contexts

    async def get_available_agents(
        self,
        product_id: UUID,
        run_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Get available agents for a product that can be interviewed."""
        query = select(AgentInteraction).join(ProductRun)

        if run_id:
            query = query.where(AgentInteraction.run_id == run_id)
        else:
            query = query.where(ProductRun.product_id == product_id)

        query = query.where(AgentInteraction.status == "completed")
        query = query.order_by(AgentInteraction.agent_index)
        query = query.limit(100)

        result = await self.db.execute(query)
        interactions = result.scalars().all()

        return [
            {
                "agent_id": str(interaction.id),
                "agent_index": interaction.agent_index,
                "persona_summary": interaction.persona_summary,
                "original_sentiment": interaction.sentiment_overall,
                "key_themes": interaction.key_themes,
            }
            for interaction in interactions
        ]

    # ============= Message Management =============

    async def _get_conversation_history(
        self,
        session_id: UUID,
        agent_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, str]]:
        """Get conversation history for context."""
        query = select(FocusGroupMessage).where(
            FocusGroupMessage.session_id == session_id
        )

        if agent_id:
            query = query.where(
                (FocusGroupMessage.role == "moderator") |
                (FocusGroupMessage.agent_id == agent_id)
            )

        query = query.order_by(FocusGroupMessage.sequence_number.desc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        # Reverse to get chronological order
        messages.reverse()

        return [
            {
                "role": "user" if msg.role == "moderator" else "assistant",
                "content": msg.content,
            }
            for msg in messages
        ]

    async def _save_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        emotion: Optional[str] = None,
        confidence: Optional[float] = None,
        key_points: Optional[List[str]] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        response_time_ms: int = 0,
    ) -> FocusGroupMessage:
        """Save a message to the database."""
        # Get next sequence number
        result = await self.db.execute(
            select(func.max(FocusGroupMessage.sequence_number)).where(
                FocusGroupMessage.session_id == session_id
            )
        )
        max_seq = result.scalar() or 0

        message = FocusGroupMessage(
            session_id=session_id,
            sequence_number=max_seq + 1,
            role=role,
            content=content,
            agent_id=agent_id,
            agent_name=agent_name,
            sentiment_score=sentiment_score,
            emotion=emotion,
            confidence=confidence,
            key_points=key_points,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=response_time_ms,
        )

        self.db.add(message)
        await self.db.flush()

        return message

    async def get_messages(
        self,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FocusGroupMessage]:
        """Get messages for a session."""
        query = select(FocusGroupMessage).where(
            FocusGroupMessage.session_id == session_id
        )
        query = query.order_by(FocusGroupMessage.sequence_number)
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============= LLM Helpers =============

    def _build_interview_messages(
        self,
        agent_context: Dict[str, Any],
        history: List[Dict[str, str]],
        question: str,
        additional_context: Optional[str] = None,
        moderator_style: str = "neutral",
    ) -> List[Dict[str, str]]:
        """Build messages for the LLM interview."""
        persona = agent_context.get("persona", {})
        previous_responses = agent_context.get("previous_responses", {})

        # Build persona description
        persona_desc = self._format_persona_for_prompt(persona)

        # Previous survey responses for context
        prev_resp_text = ""
        if previous_responses:
            prev_resp_text = "\n\nIn a previous survey, you responded:\n"
            for q_id, resp in list(previous_responses.items())[:5]:
                if isinstance(resp, dict) and "answer" in resp:
                    prev_resp_text += f"- {resp.get('answer', '')}\n"

        # Moderator style instructions
        style_instructions = {
            "neutral": "Respond naturally and honestly.",
            "probing": "Think deeply and provide detailed explanations for your answers.",
            "supportive": "Feel comfortable sharing your thoughts openly.",
            "challenging": "Consider different perspectives and defend your viewpoints.",
        }

        system_prompt = f"""You are participating in a focus group interview. You are a real person with the following background:

{persona_desc}
{prev_resp_text}

{style_instructions.get(moderator_style, style_instructions['neutral'])}

Guidelines:
- Stay in character based on your persona
- Provide thoughtful, authentic responses
- Share your genuine opinions and feelings
- Reference your background when relevant
- Be conversational but substantive
- Keep responses focused and to the point (2-4 paragraphs max)"""

        if additional_context:
            system_prompt += f"\n\nAdditional context: {additional_context}"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        return messages

    def _format_persona_for_prompt(self, persona: Dict[str, Any]) -> str:
        """Format persona data for inclusion in prompt."""
        if not persona:
            return "You are a typical consumer."

        parts = []

        if persona.get("name"):
            parts.append(f"Name: {persona['name']}")
        if persona.get("age"):
            parts.append(f"Age: {persona['age']}")
        if persona.get("gender"):
            parts.append(f"Gender: {persona['gender']}")
        if persona.get("occupation"):
            parts.append(f"Occupation: {persona['occupation']}")
        if persona.get("income_level"):
            parts.append(f"Income: {persona['income_level']}")
        if persona.get("education"):
            parts.append(f"Education: {persona['education']}")
        if persona.get("location"):
            parts.append(f"Location: {persona['location']}")
        if persona.get("personality_traits"):
            traits = persona['personality_traits']
            if isinstance(traits, list):
                parts.append(f"Personality: {', '.join(traits)}")
        if persona.get("values"):
            values = persona['values']
            if isinstance(values, list):
                parts.append(f"Values: {', '.join(values)}")
        if persona.get("interests"):
            interests = persona['interests']
            if isinstance(interests, list):
                parts.append(f"Interests: {', '.join(interests)}")

        return "\n".join(parts) if parts else "You are a typical consumer."

    async def _analyze_response(self, response: str) -> Dict[str, Any]:
        """Analyze response for sentiment, emotion, and key points."""
        # Quick sentiment analysis using simple heuristics
        # In production, this could use a dedicated sentiment model

        positive_words = ["love", "great", "excellent", "amazing", "happy", "enjoy", "like", "prefer", "good", "wonderful"]
        negative_words = ["hate", "bad", "terrible", "awful", "disappointed", "frustrated", "angry", "dislike", "poor", "worst"]

        response_lower = response.lower()

        pos_count = sum(1 for word in positive_words if word in response_lower)
        neg_count = sum(1 for word in negative_words if word in response_lower)

        total = pos_count + neg_count + 1
        sentiment_score = (pos_count - neg_count) / total

        # Determine emotion
        if sentiment_score > 0.3:
            emotion = "positive"
        elif sentiment_score < -0.3:
            emotion = "negative"
        else:
            emotion = "neutral"

        # Extract key points (simple sentence extraction)
        sentences = response.replace("!", ".").replace("?", ".").split(".")
        key_points = [s.strip() for s in sentences if len(s.strip()) > 20][:3]

        return {
            "sentiment_score": round(sentiment_score, 2),
            "emotion": emotion,
            "confidence": 0.75,  # Default confidence
            "key_points": key_points,
        }

    async def _analyze_group_discussion(
        self,
        turns: List[Dict[str, Any]]
    ) -> tuple[List[str], List[str]]:
        """Analyze group discussion for consensus and disagreement."""
        # Simple analysis - in production use LLM for more sophisticated analysis
        consensus_points = []
        disagreement_points = []

        # Look for agreement/disagreement patterns
        for turn in turns:
            response_lower = turn.get("response", "").lower()

            if "agree" in response_lower or "i think so too" in response_lower:
                consensus_points.append(f"{turn['agent_name']} agreed with the group")
            elif "disagree" in response_lower or "i don't think" in response_lower:
                disagreement_points.append(f"{turn['agent_name']} disagreed")

        return consensus_points[:5], disagreement_points[:5]

    async def _generate_session_summary(
        self,
        session: FocusGroupSession
    ) -> Dict[str, Any]:
        """Generate a summary of the session."""
        messages = await self.get_messages(session.id)

        if not messages:
            return {
                "executive_summary": "No messages in this session.",
                "key_themes": [],
            }

        # Collect all key points and themes
        all_points = []
        all_themes = []
        quotes = []

        for msg in messages:
            if msg.key_points:
                all_points.extend(msg.key_points)
            if msg.themes:
                all_themes.extend(msg.themes)
            if msg.role == "agent" and len(msg.content) > 50:
                quotes.append({
                    "agent": msg.agent_name,
                    "quote": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content,
                })

        # Generate simple summary
        agent_count = len(session.agent_ids)
        message_count = len(messages)

        summary = f"Focus group session with {agent_count} participants and {message_count} messages. "

        if all_themes:
            unique_themes = list(set(all_themes))[:5]
            summary += f"Key themes discussed: {', '.join(unique_themes)}. "

        return {
            "executive_summary": summary,
            "key_themes": list(set(all_themes))[:10],
            "key_points": list(set(all_points))[:10],
            "notable_quotes": quotes[:5],
        }
