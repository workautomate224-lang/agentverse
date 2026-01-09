"""
Persona Expansion Service (LLM-powered)
Reference: project.md §6.2, §6.3, Phase 1

Uses LLMs to expand minimal persona data into rich, simulation-ready profiles.
Key principle from project.md: LLMs are planners/compilers, NOT tick-by-tick brains.

Capabilities:
1. Expand demographics into perception weights and bias parameters
2. Generate action priors based on persona characteristics
3. Deep search enrichment with evidence refs
4. Convert personas to agents for simulation

This follows C5: LLMs are compilers/planners - we use LLM once at persona
compilation time, not during the simulation loop.
"""

import json
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class PersonaSource(str, Enum):
    """How the persona was created."""
    UPLOADED = "uploaded"
    GENERATED = "generated"
    DEEP_SEARCH = "deep_search"
    LLM_EXPANDED = "llm_expanded"


class PersonaExpansionLevel(str, Enum):
    """Level of expansion to apply."""
    MINIMAL = "minimal"        # Just structured demographics
    STANDARD = "standard"      # + perception weights, bias params
    FULL = "full"              # + action priors, detailed preferences
    DEEP = "deep"              # + evidence refs, uncertainty scores


@dataclass
class PerceptionWeights:
    """
    How the persona weighs different information sources.
    Reference: project.md §6.2 (Perception weights)
    """
    trust_mainstream_media: float = 0.5
    trust_social_media: float = 0.5
    trust_personal_network: float = 0.7
    trust_experts: float = 0.6
    trust_government: float = 0.5
    attention_span: float = 0.5  # 0-1, how much info they process
    confirmation_bias: float = 0.5  # 0-1, tendency to seek confirming info

    def to_dict(self) -> dict:
        return {
            "trust_mainstream_media": self.trust_mainstream_media,
            "trust_social_media": self.trust_social_media,
            "trust_personal_network": self.trust_personal_network,
            "trust_experts": self.trust_experts,
            "trust_government": self.trust_government,
            "attention_span": self.attention_span,
            "confirmation_bias": self.confirmation_bias,
        }


@dataclass
class BiasParameters:
    """
    Cognitive biases that affect decision-making.
    Reference: project.md §6.2 (Bias parameters)
    """
    loss_aversion: float = 0.5      # 0-1, how much losses hurt vs gains
    status_quo_bias: float = 0.5    # 0-1, preference for current state
    conformity: float = 0.5         # 0-1, tendency to follow others
    optimism_bias: float = 0.5      # 0-1, tendency to expect positive outcomes
    recency_bias: float = 0.5       # 0-1, overweighting recent events
    anchoring: float = 0.5          # 0-1, reliance on first information

    def to_dict(self) -> dict:
        return {
            "loss_aversion": self.loss_aversion,
            "status_quo_bias": self.status_quo_bias,
            "conformity": self.conformity,
            "optimism_bias": self.optimism_bias,
            "recency_bias": self.recency_bias,
            "anchoring": self.anchoring,
        }


@dataclass
class ActionPriors:
    """
    Prior probabilities for different action types.
    Reference: project.md §6.2 (Action priors)
    """
    adopt_new_product: float = 0.3
    switch_brand: float = 0.2
    recommend_to_others: float = 0.4
    seek_information: float = 0.5
    engage_socially: float = 0.4
    take_financial_risk: float = 0.2
    change_behavior: float = 0.3

    def to_dict(self) -> dict:
        return {
            "adopt_new_product": self.adopt_new_product,
            "switch_brand": self.switch_brand,
            "recommend_to_others": self.recommend_to_others,
            "seek_information": self.seek_information,
            "engage_socially": self.engage_socially,
            "take_financial_risk": self.take_financial_risk,
            "change_behavior": self.change_behavior,
        }


class ExpandedPersona(BaseModel):
    """
    Fully expanded persona ready for simulation.
    Reference: project.md §6.2
    """
    # Identity
    persona_id: str
    label: str
    source: PersonaSource = PersonaSource.LLM_EXPANDED

    # Demographics (structured, normalized)
    demographics: Dict[str, Any]

    # Preferences
    preferences: Dict[str, Any] = Field(default_factory=dict)

    # Perception weights
    perception_weights: Dict[str, float] = Field(default_factory=dict)

    # Bias parameters
    bias_parameters: Dict[str, float] = Field(default_factory=dict)

    # Action priors
    action_priors: Dict[str, float] = Field(default_factory=dict)

    # Metadata
    uncertainty_score: float = 0.5
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)

    # Versioning
    persona_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    expansion_level: PersonaExpansionLevel = PersonaExpansionLevel.STANDARD

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expanded_at: Optional[str] = None

    class Config:
        use_enum_values = True


class PersonaExpansionService:
    """
    Service for LLM-powered persona expansion.

    Key principle (C5): LLMs are used at compilation time to expand personas,
    NOT during the simulation loop. This ensures deterministic simulation.
    """

    def __init__(self, llm_service=None):
        """
        Initialize with optional LLM service.

        Args:
            llm_service: OpenRouterService or compatible LLM service
        """
        self.llm_service = llm_service

    async def expand_persona(
        self,
        demographics: Dict[str, Any],
        level: PersonaExpansionLevel = PersonaExpansionLevel.STANDARD,
        label: Optional[str] = None,
        use_llm: bool = True,
    ) -> ExpandedPersona:
        """
        Expand minimal demographics into a full persona profile.

        Args:
            demographics: Basic demographic data
            level: How much expansion to apply
            label: Optional label for the persona
            use_llm: Whether to use LLM for expansion (False = heuristic only)

        Returns:
            Fully expanded persona
        """
        # Generate persona ID from demographics hash
        demo_hash = hashlib.md5(json.dumps(demographics, sort_keys=True).encode()).hexdigest()[:12]
        persona_id = f"persona_{demo_hash}"

        # Generate label if not provided
        if not label:
            age = demographics.get("age", "unknown")
            gender = demographics.get("gender", "person")
            occupation = demographics.get("occupation", "worker")
            label = f"{gender}, {age}, {occupation}"

        if use_llm and self.llm_service:
            return await self._expand_with_llm(
                persona_id=persona_id,
                label=label,
                demographics=demographics,
                level=level,
            )
        else:
            return self._expand_heuristic(
                persona_id=persona_id,
                label=label,
                demographics=demographics,
                level=level,
            )

    def _expand_heuristic(
        self,
        persona_id: str,
        label: str,
        demographics: Dict[str, Any],
        level: PersonaExpansionLevel,
    ) -> ExpandedPersona:
        """
        Expand persona using heuristic rules (no LLM).
        Fast fallback when LLM is not available.
        """
        age = demographics.get("age", 35)
        education = demographics.get("education", "")
        income = demographics.get("income_bracket", "")
        occupation = demographics.get("occupation", "")
        location = demographics.get("location_type", "")

        # Generate perception weights based on demographics
        perception = PerceptionWeights()

        # Age affects trust in different sources
        if age < 30:
            perception.trust_social_media = 0.7
            perception.trust_mainstream_media = 0.4
            perception.attention_span = 0.4
        elif age > 55:
            perception.trust_social_media = 0.3
            perception.trust_mainstream_media = 0.6
            perception.attention_span = 0.6

        # Education affects trust in experts
        if "Graduate" in education or "Bachelor" in education:
            perception.trust_experts = 0.7
            perception.confirmation_bias = 0.4

        # Location affects trust
        if location == "Rural":
            perception.trust_government = 0.4
            perception.trust_personal_network = 0.8

        # Generate bias parameters
        bias = BiasParameters()

        # Age affects biases
        if age < 30:
            bias.status_quo_bias = 0.3
            bias.optimism_bias = 0.6
            bias.conformity = 0.6
        elif age > 55:
            bias.status_quo_bias = 0.7
            bias.loss_aversion = 0.7
            bias.recency_bias = 0.4

        # Income affects loss aversion
        if "Under" in income or "25,000" in income:
            bias.loss_aversion = 0.8
        elif "150,000" in income:
            bias.loss_aversion = 0.4

        # Generate action priors
        action = ActionPriors()

        # Age affects adoption
        if age < 30:
            action.adopt_new_product = 0.5
            action.engage_socially = 0.6
        elif age > 55:
            action.adopt_new_product = 0.2
            action.seek_information = 0.6

        # Income affects risk-taking
        if "150,000" in income or "100,000" in income:
            action.take_financial_risk = 0.4
        else:
            action.take_financial_risk = 0.2

        # Preferences based on demographics
        preferences = self._generate_preferences(demographics)

        return ExpandedPersona(
            persona_id=persona_id,
            label=label,
            source=PersonaSource.GENERATED,
            demographics=demographics,
            preferences=preferences,
            perception_weights=perception.to_dict(),
            bias_parameters=bias.to_dict(),
            action_priors=action.to_dict(),
            uncertainty_score=0.3,  # Low uncertainty for heuristic
            expansion_level=level,
            expanded_at=datetime.utcnow().isoformat(),
        )

    async def _expand_with_llm(
        self,
        persona_id: str,
        label: str,
        demographics: Dict[str, Any],
        level: PersonaExpansionLevel,
    ) -> ExpandedPersona:
        """
        Expand persona using LLM for richer, more nuanced profiles.
        Uses LLMRouter for centralized model management (GAPS.md GAP-P0-001).
        """
        # Build expansion prompt
        prompt = self._build_expansion_prompt(demographics, level)

        try:
            # Call LLM via LLMRouter with PERSONA_ENRICHMENT profile
            response = await self.llm_service.complete(
                profile_key="PERSONA_ENRICHMENT",
                messages=[
                    {"role": "system", "content": PERSONA_EXPANSION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature_override=0.7,
                max_tokens_override=1500,
            )

            # Parse LLM response
            expanded_data = json.loads(response.content)

            return ExpandedPersona(
                persona_id=persona_id,
                label=label,
                source=PersonaSource.LLM_EXPANDED,
                demographics=demographics,
                preferences=expanded_data.get("preferences", {}),
                perception_weights=expanded_data.get("perception_weights", {}),
                bias_parameters=expanded_data.get("bias_parameters", {}),
                action_priors=expanded_data.get("action_priors", {}),
                uncertainty_score=expanded_data.get("uncertainty_score", 0.5),
                expansion_level=level,
                expanded_at=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            # Fallback to heuristic on LLM failure
            persona = self._expand_heuristic(persona_id, label, demographics, level)
            persona.uncertainty_score = 0.7  # Higher uncertainty on fallback
            return persona

    def _build_expansion_prompt(
        self,
        demographics: Dict[str, Any],
        level: PersonaExpansionLevel,
    ) -> str:
        """Build the LLM prompt for persona expansion."""
        demo_text = "\n".join([f"- {k}: {v}" for k, v in demographics.items()])

        if level == PersonaExpansionLevel.MINIMAL:
            fields = "perception_weights"
        elif level == PersonaExpansionLevel.STANDARD:
            fields = "perception_weights, bias_parameters"
        elif level == PersonaExpansionLevel.FULL:
            fields = "perception_weights, bias_parameters, action_priors, preferences"
        else:
            fields = "all fields including uncertainty_score"

        return f"""Expand this persona profile based on their demographics.

DEMOGRAPHICS:
{demo_text}

Generate {fields} as a JSON object. Each weight/parameter should be a float 0-1.

Consider:
1. How their age affects trust in different information sources
2. How their education affects analytical vs intuitive thinking
3. How their income affects risk tolerance and loss aversion
4. How their occupation affects decision-making style
5. How their location affects community influence

Return valid JSON with these fields:
- perception_weights: trust levels for different information sources
- bias_parameters: cognitive bias strengths
- action_priors: probability weights for different action types
- preferences: media, brand, lifestyle preferences
- uncertainty_score: confidence in these estimates (0-1)
"""

    def _generate_preferences(self, demographics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate preferences based on demographics."""
        age = demographics.get("age", 35)
        income = demographics.get("income_bracket", "")
        education = demographics.get("education", "")

        preferences = {
            "media_channels": [],
            "brand_affinity": "moderate",
            "price_sensitivity": "moderate",
            "quality_focus": "moderate",
        }

        # Age affects media preferences
        if age < 30:
            preferences["media_channels"] = ["social_media", "streaming", "podcasts"]
            preferences["price_sensitivity"] = "high"
        elif age < 50:
            preferences["media_channels"] = ["news_websites", "social_media", "email"]
            preferences["price_sensitivity"] = "moderate"
        else:
            preferences["media_channels"] = ["television", "newspapers", "radio"]
            preferences["price_sensitivity"] = "low"

        # Income affects brand affinity
        if "150,000" in income:
            preferences["brand_affinity"] = "premium"
            preferences["quality_focus"] = "high"
        elif "Under" in income:
            preferences["brand_affinity"] = "value"
            preferences["price_sensitivity"] = "high"

        return preferences

    async def expand_population(
        self,
        personas: List[Dict[str, Any]],
        level: PersonaExpansionLevel = PersonaExpansionLevel.STANDARD,
        use_llm: bool = True,
    ) -> List[ExpandedPersona]:
        """
        Expand a population of personas.

        Args:
            personas: List of basic persona dicts with demographics
            level: Expansion level to apply
            use_llm: Whether to use LLM

        Returns:
            List of expanded personas
        """
        expanded = []
        for i, persona in enumerate(personas):
            demographics = persona.get("demographics", persona)
            label = persona.get("label", f"Persona {i + 1}")

            exp = await self.expand_persona(
                demographics=demographics,
                level=level,
                label=label,
                use_llm=use_llm,
            )
            expanded.append(exp)

        return expanded

    def persona_to_agent_profile(
        self,
        persona: ExpandedPersona,
    ) -> Dict[str, Any]:
        """
        Convert expanded persona to agent profile for simulation.
        Reference: project.md §6.3 (Agent runtime instance)
        """
        return {
            "persona_id": persona.persona_id,
            "label": persona.label,
            "demographics": persona.demographics,
            "preferences": persona.preferences,
            "perception_weights": persona.perception_weights,
            "bias_parameters": persona.bias_parameters,
            "action_priors": persona.action_priors,
            "uncertainty_score": persona.uncertainty_score,
        }


# System prompt for LLM expansion
PERSONA_EXPANSION_SYSTEM_PROMPT = """You are a persona expansion system for simulation.
Given demographics, you generate realistic psychological and behavioral attributes.

Your outputs MUST be valid JSON with numeric values between 0 and 1.
Base your estimates on established research in:
- Consumer behavior
- Cognitive psychology
- Sociology
- Demographics research

Be consistent and realistic. Higher education typically correlates with:
- Higher trust in experts and data
- Lower confirmation bias
- More analytical decision style

Older age typically correlates with:
- Higher status quo bias
- Lower social media trust
- Higher loss aversion

Lower income typically correlates with:
- Higher price sensitivity
- Higher loss aversion
- More cautious decision-making

Return ONLY valid JSON, no explanations."""


# Factory function
def get_persona_expansion_service(llm_router=None, db=None) -> PersonaExpansionService:
    """
    Get the persona expansion service.

    Args:
        llm_router: LLMRouter instance (will create default if db provided)
        db: AsyncSession for creating default LLMRouter

    Uses LLMRouter for centralized model management (GAPS.md GAP-P0-001).
    """
    if llm_router is None and db is not None:
        # Create LLMRouter with db session
        try:
            from app.services.llm_router import LLMRouter
            llm_router = LLMRouter(db)
        except Exception:
            pass  # Will use heuristic fallback

    return PersonaExpansionService(llm_service=llm_router)
