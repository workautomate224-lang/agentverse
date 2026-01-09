"""
AI Research Service
Automatically researches and gathers demographic/psychographic data for topics.
Uses LLMs to analyze topics and generate appropriate persona configurations.
"""

import json
import logging
from typing import Any, Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.persona import (
    PersonaTemplate,
    PersonaRecord,
    AIResearchJob,
    PersonaSourceType,
)
# LLM Router Integration (GAPS.md GAP-P0-001)
from app.services.llm_router import LLMRouter, LLMRouterContext
from app.services.regional_data import MultiRegionDataService
from app.services.advanced_persona import (
    AdvancedPersonaGenerator,
    PersonaGenerationConfig,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============= Schema Models =============

class ResearchConfig(BaseModel):
    """Configuration for AI research."""
    topic: str
    region: str
    country: Optional[str] = None
    industry: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    research_depth: str = "standard"  # quick, standard, comprehensive
    target_persona_count: int = 100


class ResearchInsights(BaseModel):
    """Insights discovered during research."""
    target_audience_profile: dict[str, Any]
    key_demographics: dict[str, Any]
    psychographic_factors: list[str]
    behavioral_patterns: list[str]
    decision_drivers: list[str]
    pain_points: list[str]
    media_consumption: list[str]
    purchase_influences: list[str]
    recommended_distributions: dict[str, dict[str, float]]
    confidence_score: float


class ResearchResult(BaseModel):
    """Result of a research job."""
    job_id: UUID
    status: str
    insights: Optional[ResearchInsights] = None
    personas_generated: int = 0
    error: Optional[str] = None


# ============= Prompt Templates =============

class ResearchPrompts:
    """Prompts for AI research."""

    TARGET_AUDIENCE_PROMPT = """You are an expert market researcher and consumer insights analyst.

Analyze the following topic and provide a detailed target audience profile:

TOPIC: {topic}
REGION: {region}
{country_context}
{industry_context}
KEYWORDS: {keywords}

Provide your analysis in the following JSON structure:
{{
    "target_audience_profile": {{
        "primary_segment": "Description of primary target",
        "secondary_segments": ["segment1", "segment2"],
        "market_size_estimate": "Large/Medium/Small",
        "growth_trend": "Growing/Stable/Declining"
    }},
    "key_demographics": {{
        "age_range": "XX-XX",
        "gender_skew": "balanced/male/female/other",
        "income_levels": ["income bracket 1", "income bracket 2"],
        "education_levels": ["level1", "level2"],
        "urban_rural_split": "urban/suburban/rural/mixed",
        "geographic_concentration": ["area1", "area2"]
    }},
    "psychographic_factors": [
        "Factor 1: Description",
        "Factor 2: Description",
        "Factor 3: Description"
    ],
    "behavioral_patterns": [
        "Pattern 1: Description",
        "Pattern 2: Description"
    ],
    "decision_drivers": [
        "Driver 1",
        "Driver 2",
        "Driver 3"
    ],
    "pain_points": [
        "Pain point 1",
        "Pain point 2"
    ],
    "media_consumption": [
        "Platform/Channel 1",
        "Platform/Channel 2"
    ],
    "purchase_influences": [
        "Influence 1",
        "Influence 2"
    ]
}}

Be specific and data-driven. Base your analysis on real market research principles."""

    DISTRIBUTION_PROMPT = """Based on the target audience analysis for:

TOPIC: {topic}
REGION: {region}
PRIMARY AUDIENCE: {audience_summary}

Provide realistic demographic distributions for this target audience.
Use percentages that sum to 1.0 (100%) for each category.

Return ONLY valid JSON in this exact format:
{{
    "age_distribution": {{
        "18-24": 0.XX,
        "25-34": 0.XX,
        "35-44": 0.XX,
        "45-54": 0.XX,
        "55-64": 0.XX,
        "65-74": 0.XX,
        "75+": 0.XX
    }},
    "gender_distribution": {{
        "Male": 0.XX,
        "Female": 0.XX
    }},
    "income_distribution": {{
        "Low": 0.XX,
        "Lower-Middle": 0.XX,
        "Middle": 0.XX,
        "Upper-Middle": 0.XX,
        "High": 0.XX
    }},
    "education_distribution": {{
        "High School or below": 0.XX,
        "Some College": 0.XX,
        "Bachelor's Degree": 0.XX,
        "Graduate Degree": 0.XX
    }},
    "innovation_adoption": {{
        "Innovator": 0.XX,
        "Early Adopter": 0.XX,
        "Early Majority": 0.XX,
        "Late Majority": 0.XX,
        "Laggard": 0.XX
    }},
    "confidence_score": 0.XX
}}

Make sure:
1. Each distribution's values sum to exactly 1.0
2. Values are realistic for this topic and region
3. Confidence score reflects data quality (0.7-0.95 range)"""

    TOPIC_KNOWLEDGE_PROMPT = """You are creating topic-specific knowledge for personas in a simulation.

TOPIC: {topic}
PERSONA PROFILE:
- Age: {age}
- Gender: {gender}
- Income: {income}
- Education: {education}
- Values: {values}

Generate specific knowledge, attitudes, and behaviors this persona would have regarding the topic.

Return ONLY valid JSON:
{{
    "awareness_level": "Expert/Knowledgeable/Aware/Limited/None",
    "interest_level": X (1-10),
    "current_behavior": "Description of current behavior related to topic",
    "pain_points": ["pain1", "pain2"],
    "decision_factors": ["factor1", "factor2", "factor3"],
    "brand_preferences": ["brand1", "brand2"] or [],
    "price_sensitivity": X (1-10),
    "feature_priorities": ["feature1", "feature2", "feature3"],
    "information_sources": ["source1", "source2"],
    "purchase_timeline": "Immediate/Soon/Considering/Not interested",
    "barriers_to_action": ["barrier1", "barrier2"],
    "influencers": ["type1", "type2"]
}}"""


# ============= AI Research Service =============

class AIResearchService:
    """
    Service for AI-powered market research and persona generation.
    Uses LLMs to analyze topics and generate informed persona configurations.

    Uses LLMRouter for centralized model management (GAPS.md GAP-P0-001).
    """

    def __init__(self, db: AsyncSession, llm_router: Optional[LLMRouter] = None):
        self.db = db
        self.llm_router = llm_router or LLMRouter(db)
        self.multi_region_service = MultiRegionDataService()

    async def create_research_job(
        self,
        user_id: UUID,
        config: ResearchConfig,
        template_id: Optional[UUID] = None,
    ) -> AIResearchJob:
        """Create a new research job."""
        job = AIResearchJob(
            user_id=user_id,
            template_id=template_id,
            topic=config.topic,
            region=config.region,
            country=config.country,
            industry=config.industry,
            keywords=config.keywords,
            research_depth=config.research_depth,
            target_persona_count=config.target_persona_count,
            status="pending",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def run_research(self, job_id: UUID) -> ResearchResult:
        """Execute a research job."""
        # Get job
        result = await self.db.execute(
            select(AIResearchJob).where(AIResearchJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            return ResearchResult(
                job_id=job_id,
                status="failed",
                error="Job not found"
            )

        try:
            # Update status
            await self._update_job_status(job_id, "researching", 10)

            # Step 1: Research target audience
            insights = await self._research_target_audience(job)
            await self._update_job_status(job_id, "researching", 40)

            # Step 2: Get distribution recommendations
            distributions = await self._get_distribution_recommendations(job, insights)
            insights.recommended_distributions = distributions
            await self._update_job_status(job_id, "generating", 60)

            # Step 3: Generate personas
            personas_count = await self._generate_personas(job, insights)
            await self._update_job_status(job_id, "completed", 100)

            # Update job with results
            await self.db.execute(
                update(AIResearchJob)
                .where(AIResearchJob.id == job_id)
                .values(
                    status="completed",
                    progress=100,
                    insights=insights.model_dump(),
                    personas_generated=personas_count,
                    completed_at=datetime.utcnow(),
                )
            )
            await self.db.commit()

            return ResearchResult(
                job_id=job_id,
                status="completed",
                insights=insights,
                personas_generated=personas_count,
            )

        except Exception as e:
            logger.error(f"Research job {job_id} failed: {e}")
            await self.db.execute(
                update(AIResearchJob)
                .where(AIResearchJob.id == job_id)
                .values(status="failed")
            )
            await self.db.commit()

            return ResearchResult(
                job_id=job_id,
                status="failed",
                error=str(e)
            )

    async def _update_job_status(
        self,
        job_id: UUID,
        status: str,
        progress: int
    ) -> None:
        """Update job status and progress."""
        updates = {"status": status, "progress": progress}
        if status == "researching" and progress == 10:
            updates["started_at"] = datetime.utcnow()

        await self.db.execute(
            update(AIResearchJob)
            .where(AIResearchJob.id == job_id)
            .values(**updates)
        )
        await self.db.commit()

    async def _research_target_audience(self, job: AIResearchJob) -> ResearchInsights:
        """Research target audience using AI."""
        country_context = f"COUNTRY: {job.country}" if job.country else ""
        industry_context = f"INDUSTRY: {job.industry}" if job.industry else ""

        prompt = ResearchPrompts.TARGET_AUDIENCE_PROMPT.format(
            topic=job.topic,
            region=job.region,
            country_context=country_context,
            industry_context=industry_context,
            keywords=", ".join(job.keywords) if job.keywords else "N/A",
        )

        # Call LLM via LLMRouter with DEEP_SEARCH profile
        response = await self.llm_router.complete(
            profile_key="DEEP_SEARCH",
            messages=[
                {"role": "system", "content": "You are an expert market researcher. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens_override=2000,
            temperature_override=0.7,
        )

        # Parse response
        try:
            data = self._extract_json(response.content)
        except json.JSONDecodeError:
            # Fallback to default insights
            data = self._get_default_insights()

        return ResearchInsights(
            target_audience_profile=data.get("target_audience_profile", {}),
            key_demographics=data.get("key_demographics", {}),
            psychographic_factors=data.get("psychographic_factors", []),
            behavioral_patterns=data.get("behavioral_patterns", []),
            decision_drivers=data.get("decision_drivers", []),
            pain_points=data.get("pain_points", []),
            media_consumption=data.get("media_consumption", []),
            purchase_influences=data.get("purchase_influences", []),
            recommended_distributions={},
            confidence_score=0.8,
        )

    async def _get_distribution_recommendations(
        self,
        job: AIResearchJob,
        insights: ResearchInsights
    ) -> dict[str, dict[str, float]]:
        """Get recommended demographic distributions from AI."""
        audience_summary = json.dumps(insights.target_audience_profile, indent=2)

        prompt = ResearchPrompts.DISTRIBUTION_PROMPT.format(
            topic=job.topic,
            region=job.region,
            audience_summary=audience_summary[:500],  # Truncate if too long
        )

        # Call LLM via LLMRouter with DEEP_SEARCH profile
        response = await self.llm_router.complete(
            profile_key="DEEP_SEARCH",
            messages=[
                {"role": "system", "content": "You are a demographic data analyst. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens_override=1000,
            temperature_override=0.5,
        )

        try:
            data = self._extract_json(response.content)
            # Validate and normalize distributions
            distributions = {}
            for key in ["age_distribution", "gender_distribution", "income_distribution",
                       "education_distribution", "innovation_adoption"]:
                if key in data:
                    dist = data[key]
                    # Normalize to sum to 1.0
                    total = sum(dist.values())
                    if total > 0:
                        distributions[key] = {k: round(v/total, 4) for k, v in dist.items()}
            return distributions
        except (json.JSONDecodeError, KeyError):
            return self._get_default_distributions()

    async def _generate_personas(
        self,
        job: AIResearchJob,
        insights: ResearchInsights
    ) -> int:
        """Generate personas based on research insights."""
        # Create persona config
        config = PersonaGenerationConfig(
            region=job.region,
            country=job.country,
            topic=job.topic,
            industry=job.industry,
            keywords=job.keywords,
            count=job.target_persona_count,
            source_type=PersonaSourceType.AI_RESEARCHED.value,
            include_topic_knowledge=True,
            include_cultural=True,
        )

        # Get regional demographics as base
        regional_demo = await self.multi_region_service.get_demographics(
            region=job.region,
            country=job.country,
        )

        # Override with research-based distributions
        if insights.recommended_distributions:
            if "age_distribution" in insights.recommended_distributions:
                regional_demo.age_distribution = insights.recommended_distributions["age_distribution"]
            if "gender_distribution" in insights.recommended_distributions:
                regional_demo.gender_distribution = insights.recommended_distributions["gender_distribution"]
            if "income_distribution" in insights.recommended_distributions:
                regional_demo.income_distribution = insights.recommended_distributions["income_distribution"]
            if "education_distribution" in insights.recommended_distributions:
                regional_demo.education_distribution = insights.recommended_distributions["education_distribution"]

        # Generate personas
        generator = AdvancedPersonaGenerator(config, regional_demo)
        generated = await generator.generate_personas(job.target_persona_count)

        # Enhance with topic-specific knowledge
        for persona in generated:
            topic_knowledge = await self._generate_topic_knowledge(
                job.topic, persona
            )
            if topic_knowledge:
                persona.topic_knowledge = topic_knowledge

        # Save to database
        for persona in generated:
            record = PersonaRecord(
                template_id=job.template_id,
                demographics=persona.demographics,
                professional=persona.professional,
                psychographics=persona.psychographics,
                behavioral=persona.behavioral,
                interests=persona.interests,
                topic_knowledge=persona.topic_knowledge,
                cultural_context=persona.cultural_context,
                source_type=PersonaSourceType.AI_RESEARCHED.value,
                confidence_score=insights.confidence_score,
                generation_context={
                    "topic": job.topic,
                    "region": job.region,
                    "research_job_id": str(job.id),
                },
                full_prompt=persona.full_prompt,
            )
            self.db.add(record)

        await self.db.commit()
        return len(generated)

    async def _generate_topic_knowledge(
        self,
        topic: str,
        persona: Any
    ) -> Optional[dict[str, Any]]:
        """Generate topic-specific knowledge for a persona."""
        try:
            prompt = ResearchPrompts.TOPIC_KNOWLEDGE_PROMPT.format(
                topic=topic,
                age=persona.demographics.get("age", "Unknown"),
                gender=persona.demographics.get("gender", "Unknown"),
                income=persona.demographics.get("income_bracket", "Unknown"),
                education=persona.professional.get("education_level", "Unknown"),
                values=", ".join(persona.psychographics.get("values_primary", [])[:3]),
            )

            # Call LLM via LLMRouter with PERSONA_ENRICHMENT profile
            response = await self.llm_router.complete(
                profile_key="PERSONA_ENRICHMENT",
                messages=[
                    {"role": "system", "content": "Generate persona topic knowledge. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens_override=500,
                temperature_override=0.8,
            )

            return self._extract_json(response.content)
        except Exception as e:
            logger.warning(f"Failed to generate topic knowledge: {e}")
            return None

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON in the response
        text = text.strip()

        # If it starts with ``json, extract the content
        if text.startswith("```"):
            lines = text.split("\n")
            start_idx = 1 if lines[0].startswith("```") else 0
            end_idx = len(lines)
            for i, line in enumerate(lines[1:], 1):
                if line.startswith("```"):
                    end_idx = i
                    break
            text = "\n".join(lines[start_idx:end_idx])

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end > start:
            return json.loads(text[start:end])

        raise json.JSONDecodeError("No JSON found", text, 0)

    def _get_default_insights(self) -> dict[str, Any]:
        """Get default insights if AI fails."""
        return {
            "target_audience_profile": {
                "primary_segment": "General consumers",
                "secondary_segments": [],
                "market_size_estimate": "Medium",
            },
            "key_demographics": {
                "age_range": "25-54",
                "gender_skew": "balanced",
            },
            "psychographic_factors": ["Quality-conscious", "Value-oriented"],
            "behavioral_patterns": ["Research before purchase"],
            "decision_drivers": ["Price", "Quality", "Convenience"],
            "pain_points": ["Finding reliable information"],
            "media_consumption": ["Social Media", "Search Engines"],
            "purchase_influences": ["Reviews", "Word of mouth"],
        }

    def _get_default_distributions(self) -> dict[str, dict[str, float]]:
        """Get default distributions if AI fails."""
        return {
            "age_distribution": {
                "18-24": 0.12, "25-34": 0.22, "35-44": 0.22,
                "45-54": 0.18, "55-64": 0.14, "65-74": 0.08, "75+": 0.04
            },
            "gender_distribution": {"Male": 0.50, "Female": 0.50},
            "income_distribution": {
                "Low": 0.20, "Lower-Middle": 0.25, "Middle": 0.30,
                "Upper-Middle": 0.18, "High": 0.07
            },
            "education_distribution": {
                "High School or below": 0.30, "Some College": 0.25,
                "Bachelor's Degree": 0.30, "Graduate Degree": 0.15
            },
        }

    async def get_job_status(self, job_id: UUID) -> Optional[AIResearchJob]:
        """Get the status of a research job."""
        result = await self.db.execute(
            select(AIResearchJob).where(AIResearchJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> list[AIResearchJob]:
        """List research jobs for a user."""
        result = await self.db.execute(
            select(AIResearchJob)
            .where(AIResearchJob.user_id == user_id)
            .order_by(AIResearchJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
