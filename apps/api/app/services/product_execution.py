"""
Product Execution Service
Orchestrates the execution of Product runs (Predict, Insight, Simulate).
Handles agent spawning, LLM calls, response parsing, and result aggregation.
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.product import (
    Product, ProductRun, AgentInteraction, ProductResult,
    ProductType
)
from app.models.persona import PersonaTemplate, PersonaRecord
from app.services.openrouter import OpenRouterService, CompletionResponse
from app.services.advanced_persona import (
    AdvancedPersonaGenerator,
    PersonaGenerationConfig,
    GeneratedPersona
)


logger = logging.getLogger(__name__)


# ============= Progress Callback Type =============

ProgressCallback = Callable[[int, int, int, Optional[dict]], None]
# (progress_percent, agents_completed, agents_failed, optional_data)


# ============= Prompt Templates =============

class ProductPromptBuilder:
    """Builds prompts tailored to each product type."""

    @staticmethod
    def build_predict_prompt(product: Product, persona: GeneratedPersona) -> list[dict]:
        """Build prompt for Predict product type."""
        config = product.configuration
        prediction_type = config.get("prediction_type", "market_adoption")
        variables = config.get("variables", [])
        stimulus = product.stimulus_materials or {}

        system_prompt = f"""{persona.full_prompt}

You are participating in a market research study. Based on your background, preferences, and decision-making style, you will be asked about your likely behavior or choices in a specific scenario.

Guidelines:
- Respond authentically based on your persona's characteristics
- Consider your values, priorities, and past behaviors
- Be specific and decisive in your responses
- Explain your reasoning briefly"""

        # Build the user prompt based on prediction type
        user_prompt_parts = ["# Scenario\n"]

        if "concepts" in stimulus:
            user_prompt_parts.append("## Options to Consider:\n")
            for i, concept in enumerate(stimulus["concepts"], 1):
                user_prompt_parts.append(f"**Option {i}:** {concept}\n")

        if "messages" in stimulus:
            user_prompt_parts.append("\n## Messages:\n")
            for msg in stimulus["messages"]:
                user_prompt_parts.append(f"- {msg}\n")

        user_prompt_parts.append(f"\n# Questions\n")

        questions = config.get("questions", [])
        if not questions:
            # Default questions based on prediction type
            questions = ProductPromptBuilder._get_default_questions(prediction_type)

        for i, q in enumerate(questions, 1):
            q_text = q.get("text", q) if isinstance(q, dict) else q
            q_type = q.get("type", "open_ended") if isinstance(q, dict) else "open_ended"
            user_prompt_parts.append(f"**Q{i}:** {q_text}\n")
            if q_type == "scale":
                user_prompt_parts.append("(Rate on a scale of 1-10)\n")
            elif q_type == "yes_no":
                user_prompt_parts.append("(Answer: Yes or No)\n")

        user_prompt_parts.append("""
# Response Format
For each question, provide:
[Q1_ANSWER]: Your answer
[Q1_CONFIDENCE]: Your confidence (1-10)
[Q1_REASON]: Brief explanation (1-2 sentences)

(Repeat for each question)""")

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "".join(user_prompt_parts)}
        ]

    @staticmethod
    def build_insight_prompt(product: Product, persona: GeneratedPersona) -> list[dict]:
        """Build prompt for Insight product type."""
        config = product.configuration
        insight_type = config.get("insight_type", "motivation_analysis")
        themes = config.get("themes", [])
        depth = config.get("depth", "comprehensive")
        stimulus = product.stimulus_materials or {}

        system_prompt = f"""{persona.full_prompt}

You are participating in a qualitative research interview. The researcher wants to understand your deeper motivations, feelings, and decision-making processes.

Guidelines:
- Share your genuine thoughts and feelings
- Reflect deeply on your motivations and barriers
- Be specific with examples from your experience
- Express any concerns, doubts, or enthusiasm naturally"""

        user_prompt_parts = ["# Interview Topic\n"]

        if "concepts" in stimulus:
            user_prompt_parts.append("## Topic for Discussion:\n")
            for concept in stimulus["concepts"]:
                user_prompt_parts.append(f"{concept}\n\n")

        questions = config.get("questions", [])
        if not questions:
            questions = ProductPromptBuilder._get_insight_questions(insight_type)

        user_prompt_parts.append("# Interview Questions\n\n")
        for i, q in enumerate(questions, 1):
            q_text = q.get("text", q) if isinstance(q, dict) else q
            user_prompt_parts.append(f"**Question {i}:** {q_text}\n\n")

        user_prompt_parts.append("""
# Response Format
Please answer each question thoughtfully. For each response:
[Q{N}_RESPONSE]: Your detailed answer (2-4 sentences)
[Q{N}_EMOTION]: Primary emotion (e.g., excited, concerned, indifferent)
[Q{N}_INTENSITY]: Emotion intensity (1-10)
""")

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "".join(user_prompt_parts)}
        ]

    @staticmethod
    def build_simulate_prompt(product: Product, persona: GeneratedPersona, context: dict = None) -> list[dict]:
        """Build prompt for Simulate product type (focus group, product test, etc.)."""
        config = product.configuration
        simulation_type = config.get("simulation_type", "focus_group")
        moderator_style = config.get("moderator_style", "exploratory")
        stimulus = product.stimulus_materials or {}

        system_prompt = f"""{persona.full_prompt}

You are participating in a {simulation_type.replace('_', ' ')}. Engage naturally as yourself, sharing your genuine reactions and opinions.

Guidelines:
- React naturally and authentically
- Share both positive and negative thoughts
- Engage with the topic as you would in real life
- Be conversational and expressive"""

        user_prompt_parts = ["# Session Context\n"]

        if "concepts" in stimulus:
            user_prompt_parts.append("## What we're discussing:\n")
            for concept in stimulus["concepts"]:
                user_prompt_parts.append(f"{concept}\n\n")

        # Add discussion guide
        guide = config.get("discussion_guide", [])
        if guide:
            user_prompt_parts.append("# Discussion Points\n\n")
            for i, point in enumerate(guide, 1):
                user_prompt_parts.append(f"{i}. {point}\n")

        user_prompt_parts.append("""
# Your Task
Please share your reaction to what's being discussed. Include:
[INITIAL_REACTION]: Your first impression (1-2 sentences)
[DETAILED_THOUGHTS]: Deeper analysis (2-3 sentences)
[KEY_CONCERN]: Main concern or hesitation (if any)
[ENTHUSIASM_LEVEL]: Rate 1-10
[LIKELIHOOD_TO_ACT]: Rate 1-10 (e.g., likelihood to purchase/adopt/vote)
[REASONING]: Why you feel this way (2-3 sentences)
""")

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "".join(user_prompt_parts)}
        ]

    @staticmethod
    def _get_default_questions(prediction_type: str) -> list[dict]:
        """Get default questions based on prediction type."""
        defaults = {
            "market_adoption": [
                {"text": "How likely are you to try this product/service?", "type": "scale"},
                {"text": "What is the primary factor that would influence your decision?", "type": "open_ended"},
                {"text": "Would you recommend this to others?", "type": "yes_no"},
            ],
            "election": [
                {"text": "Which candidate would you vote for?", "type": "choice"},
                {"text": "How certain are you about your choice?", "type": "scale"},
                {"text": "What is the most important issue influencing your vote?", "type": "open_ended"},
            ],
            "product_launch": [
                {"text": "How interested are you in this product?", "type": "scale"},
                {"text": "What price would you expect to pay?", "type": "open_ended"},
                {"text": "Would you purchase this within the first month of launch?", "type": "yes_no"},
            ],
            "brand_perception": [
                {"text": "How would you rate this brand overall?", "type": "scale"},
                {"text": "What three words come to mind when you think of this brand?", "type": "open_ended"},
                {"text": "Would you choose this brand over competitors?", "type": "yes_no"},
            ],
        }
        return defaults.get(prediction_type, defaults["market_adoption"])

    @staticmethod
    def _get_insight_questions(insight_type: str) -> list[dict]:
        """Get default questions for insight types."""
        defaults = {
            "motivation_analysis": [
                {"text": "What drives your interest in this topic/product?"},
                {"text": "What emotions do you associate with this?"},
                {"text": "What would make this more appealing to you?"},
            ],
            "decision_journey": [
                {"text": "Walk me through how you typically make decisions like this."},
                {"text": "What sources do you consult when making this type of decision?"},
                {"text": "What would cause you to change your mind?"},
            ],
            "barrier_identification": [
                {"text": "What concerns or hesitations do you have?"},
                {"text": "What would prevent you from moving forward?"},
                {"text": "What would need to change for you to feel more comfortable?"},
            ],
        }
        return defaults.get(insight_type, defaults["motivation_analysis"])

    # ============= ORACLE Prompts (Market Intelligence) =============

    @staticmethod
    def build_oracle_prompt(product: Product, persona: GeneratedPersona) -> list[dict]:
        """
        Build prompt for ORACLE product type (Market Intelligence).
        Simulates customer decisions, models hard-to-reach segments, predicts market behavior.
        Equivalent to Aaru Lumen.
        """
        config = product.configuration
        oracle_type = config.get("oracle_type", "consumer_decision")
        time_horizon = config.get("time_horizon", "6_months")
        stimulus = product.stimulus_materials or {}

        system_prompt = f"""{persona.full_prompt}

You are participating in an advanced market intelligence study. As a consumer/decision-maker, you will evaluate products, brands, and purchasing scenarios based on your authentic preferences, values, and decision-making patterns.

Your Role:
- You represent a specific market segment with unique needs and preferences
- Your decisions reflect real-world consumer behavior and psychology
- Consider your budget constraints, lifestyle, and personal values
- Factor in your information sources and purchase triggers

Analysis Context: {oracle_type.replace('_', ' ').title()} study over {time_horizon.replace('_', ' ')} timeframe."""

        user_prompt_parts = ["# Market Intelligence Analysis\n\n"]

        # Add product/brand information
        if "concepts" in stimulus:
            user_prompt_parts.append("## Products/Brands Under Evaluation:\n\n")
            for i, concept in enumerate(stimulus["concepts"], 1):
                user_prompt_parts.append(f"**Option {i}:** {concept}\n\n")

        if "prices" in stimulus:
            user_prompt_parts.append("## Price Points:\n")
            for price in stimulus["prices"]:
                user_prompt_parts.append(f"- {price}\n")
            user_prompt_parts.append("\n")

        if "messages" in stimulus:
            user_prompt_parts.append("## Marketing Messages:\n")
            for msg in stimulus["messages"]:
                user_prompt_parts.append(f"- {msg}\n")
            user_prompt_parts.append("\n")

        # Oracle-specific questions
        oracle_questions = ProductPromptBuilder._get_oracle_questions(oracle_type)
        user_prompt_parts.append("# Analysis Questions\n\n")
        for i, q in enumerate(oracle_questions, 1):
            user_prompt_parts.append(f"**Q{i}:** {q}\n\n")

        user_prompt_parts.append("""
# Response Format
Provide structured responses:

[PURCHASE_INTENT]: Rate 1-10 (10 = definitely will purchase/adopt)
[BRAND_PREFERENCE]: Your preferred option and why (1-2 sentences)
[PRICE_SENSITIVITY]: Rate 1-10 (10 = highly price sensitive)
[SWITCHING_LIKELIHOOD]: Rate 1-10 (10 = very likely to switch from current choice)
[KEY_DRIVERS]: Top 3 factors driving your decision (comma-separated)
[BARRIERS]: Main barriers to purchase/adoption (comma-separated)
[TIMELINE]: When would you make this decision? (immediate/1-3 months/3-6 months/6-12 months/1+ year)
[CHANNEL_PREFERENCE]: How would you prefer to purchase? (online/in-store/direct/subscription)
[INFLUENCE_FACTORS]: Who/what influences this decision? (1-2 sentences)
[CONFIDENCE]: How confident are you in these responses? (1-10)
""")

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "".join(user_prompt_parts)}
        ]

    @staticmethod
    def _get_oracle_questions(oracle_type: str) -> list[str]:
        """Get questions based on Oracle study type."""
        questions = {
            "market_share": [
                "Considering all options available, which would you choose and why?",
                "What would make you switch from your current choice?",
                "How does price factor into your decision?",
            ],
            "consumer_decision": [
                "Walk through your typical decision process for this type of purchase.",
                "What information do you seek before making this decision?",
                "What would cause you to delay or abandon this purchase?",
            ],
            "brand_switching": [
                "What would it take for you to switch from your current brand?",
                "What keeps you loyal to your current choice?",
                "What new brand features would be compelling enough to switch?",
            ],
            "purchase_behavior": [
                "Describe your typical purchase journey for products like this.",
                "What triggers you to start considering a purchase?",
                "How do you validate your purchase decisions?",
            ],
            "segment_discovery": [
                "What unmet needs do you have in this category?",
                "What frustrates you about current options?",
                "What would your ideal solution look like?",
            ],
            "price_elasticity": [
                "At what price point would this be a 'must have'?",
                "At what price would you start to question the value?",
                "What premium features justify a higher price for you?",
            ],
        }
        return questions.get(oracle_type, questions["consumer_decision"])

    # ============= PULSE Prompts (Political Simulation) =============

    @staticmethod
    def build_pulse_prompt(product: Product, persona: GeneratedPersona) -> list[dict]:
        """
        Build prompt for PULSE product type (Political & Election Simulation).
        Voter agents that simulate electoral behavior, campaign response, and political dynamics.
        Equivalent to Aaru Dynamo.
        """
        config = product.configuration
        pulse_type = config.get("pulse_type", "voter_behavior")
        election_context = config.get("election_context", "general_election")
        stimulus = product.stimulus_materials or {}

        system_prompt = f"""{persona.full_prompt}

You are participating in a political behavior simulation study. As a voter/citizen, you will evaluate candidates, policies, and political messages based on your authentic values, priorities, and political identity.

Your Role:
- You represent a specific voter segment with real concerns and priorities
- Your voting behavior reflects genuine political psychology and decision-making
- Consider your values, community context, and information sources
- Factor in your level of political engagement and past voting patterns

Study Context: {pulse_type.replace('_', ' ').title()} analysis for {election_context.replace('_', ' ')} context."""

        user_prompt_parts = ["# Political Behavior Analysis\n\n"]

        # Add candidate/policy information
        if "concepts" in stimulus:
            user_prompt_parts.append("## Candidates/Policies Under Evaluation:\n\n")
            for i, concept in enumerate(stimulus["concepts"], 1):
                user_prompt_parts.append(f"**Option {i}:** {concept}\n\n")

        if "messages" in stimulus:
            user_prompt_parts.append("## Campaign Messages:\n")
            for msg in stimulus["messages"]:
                user_prompt_parts.append(f"- {msg}\n")
            user_prompt_parts.append("\n")

        # Pulse-specific questions
        pulse_questions = ProductPromptBuilder._get_pulse_questions(pulse_type)
        user_prompt_parts.append("# Analysis Questions\n\n")
        for i, q in enumerate(pulse_questions, 1):
            user_prompt_parts.append(f"**Q{i}:** {q}\n\n")

        user_prompt_parts.append("""
# Response Format
Provide structured responses:

[VOTE_CHOICE]: Your voting preference (candidate name or policy position)
[VOTE_CERTAINTY]: How certain are you? (1-10, 10 = absolutely certain)
[ENTHUSIASM]: How enthusiastic about your choice? (1-10)
[TURNOUT_LIKELIHOOD]: How likely to actually vote? (1-10)
[TOP_ISSUES]: Your top 3 issues driving this decision (comma-separated)
[CANDIDATE_PERCEPTION]: Brief assessment of main candidates (1-2 sentences each)
[PERSUADABILITY]: How persuadable are you? (1-10, 10 = open to changing mind)
[SWING_FACTORS]: What could change your vote? (1-2 sentences)
[INFORMATION_SOURCES]: Where do you get political information? (comma-separated)
[PARTY_ALIGNMENT]: How strongly do you identify with a party? (1-10)
[POLICY_VS_PERSONALITY]: What matters more - policy positions or candidate character? (policy/personality/equal)
[CONFIDENCE]: Confidence in these responses (1-10)
""")

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "".join(user_prompt_parts)}
        ]

    @staticmethod
    def _get_pulse_questions(pulse_type: str) -> list[str]:
        """Get questions based on Pulse study type."""
        questions = {
            "election_forecast": [
                "Given the current candidates, who would you vote for and why?",
                "What issues are most important to your vote?",
                "How has your position changed over the campaign?",
            ],
            "voter_behavior": [
                "What drives your voting decisions?",
                "How engaged are you in the political process?",
                "What would motivate you to vote/not vote?",
            ],
            "campaign_impact": [
                "How effective are the campaign messages you've seen?",
                "What messages resonate with you?",
                "What campaign tactics turn you off?",
            ],
            "swing_voter": [
                "What keeps you from committing to one candidate?",
                "What information would help you decide?",
                "What's your threshold for making a final decision?",
            ],
            "turnout_prediction": [
                "What would definitely get you to the polls?",
                "What barriers might prevent you from voting?",
                "How important is this election to you personally?",
            ],
            "policy_response": [
                "How do you react to this policy proposal?",
                "What are the benefits and drawbacks you see?",
                "Would this change your vote?",
            ],
        }
        return questions.get(pulse_type, questions["voter_behavior"])

    # ============= PRISM Prompts (Public Sector Analytics) =============

    @staticmethod
    def build_prism_prompt(product: Product, persona: GeneratedPersona) -> list[dict]:
        """
        Build prompt for PRISM product type (Public Sector & Policy Analytics).
        Configurable simulations for policy impact, crisis management, and stakeholder analysis.
        Equivalent to Aaru Seraph.
        """
        config = product.configuration
        prism_type = config.get("prism_type", "policy_impact")
        context_setting = config.get("context_setting", "current")
        stimulus = product.stimulus_materials or {}

        system_prompt = f"""{persona.full_prompt}

You are participating in a public policy and impact simulation study. As a citizen/stakeholder, you will evaluate policies, government initiatives, and crisis scenarios based on your authentic perspective, values, and concerns.

Your Role:
- You represent a specific stakeholder group with real interests and concerns
- Your responses reflect genuine public opinion and behavior patterns
- Consider your community context, personal impact, and trust in institutions
- Factor in your past experiences with government and public services

Study Context: {prism_type.replace('_', ' ').title()} analysis in {context_setting} setting."""

        user_prompt_parts = ["# Public Sector Impact Analysis\n\n"]

        # Add policy/scenario information
        if "concepts" in stimulus:
            user_prompt_parts.append("## Policies/Scenarios Under Evaluation:\n\n")
            for i, concept in enumerate(stimulus["concepts"], 1):
                user_prompt_parts.append(f"**Scenario {i}:** {concept}\n\n")

        if "messages" in stimulus:
            user_prompt_parts.append("## Government Communications:\n")
            for msg in stimulus["messages"]:
                user_prompt_parts.append(f"- {msg}\n")
            user_prompt_parts.append("\n")

        # Prism-specific questions
        prism_questions = ProductPromptBuilder._get_prism_questions(prism_type)
        user_prompt_parts.append("# Analysis Questions\n\n")
        for i, q in enumerate(prism_questions, 1):
            user_prompt_parts.append(f"**Q{i}:** {q}\n\n")

        user_prompt_parts.append("""
# Response Format
Provide structured responses:

[POLICY_SUPPORT]: Rate support for this policy/initiative (1-10, 10 = strongly support)
[PERSONAL_IMPACT]: How would this affect you personally? (positive/neutral/negative)
[IMPACT_MAGNITUDE]: How significant is the impact? (1-10)
[TRUST_LEVEL]: Trust in government to implement this well (1-10)
[COMPLIANCE_LIKELIHOOD]: How likely to comply/participate? (1-10)
[KEY_CONCERNS]: Top 3 concerns about this policy (comma-separated)
[BENEFITS_PERCEIVED]: Top 3 benefits you see (comma-separated)
[STAKEHOLDER_POSITION]: Your stakeholder group's likely position (support/oppose/neutral)
[COMMUNITY_IMPACT]: Impact on your community (1-2 sentences)
[ALTERNATIVE_PREFERRED]: Would you prefer an alternative approach? If so, what? (1-2 sentences)
[CRISIS_PREPAREDNESS]: How prepared do you feel for this scenario? (1-10)
[INFORMATION_NEEDS]: What information would help you? (comma-separated)
[BEHAVIORAL_CHANGE]: Would this change your behavior? How? (1-2 sentences)
[CONFIDENCE]: Confidence in these responses (1-10)
""")

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "".join(user_prompt_parts)}
        ]

    @staticmethod
    def _get_prism_questions(prism_type: str) -> list[str]:
        """Get questions based on Prism study type."""
        questions = {
            "policy_impact": [
                "How would this policy affect your daily life?",
                "What are the potential unintended consequences you foresee?",
                "How should the government communicate about this?",
            ],
            "crisis_response": [
                "How would you respond to this crisis scenario?",
                "What resources or support would you need?",
                "How confident are you in the government's crisis response?",
            ],
            "public_opinion": [
                "What is your overall sentiment toward this initiative?",
                "How does this align with your values?",
                "What would change your opinion?",
            ],
            "stakeholder_mapping": [
                "How would your community/group be affected?",
                "What is your group's likely response?",
                "Who should be consulted in the decision-making?",
            ],
            "scenario_planning": [
                "How likely is this scenario in your view?",
                "What preparations should be made?",
                "What would you do personally in this situation?",
            ],
            "regulatory_impact": [
                "How would this regulation affect your sector/activities?",
                "What compliance challenges do you foresee?",
                "Is this regulation fair and proportionate?",
            ],
        }
        return questions.get(prism_type, questions["policy_impact"])


# ============= Response Parser =============

class ResponseParser:
    """Parses LLM responses into structured data."""

    @staticmethod
    def parse_predict_response(content: str) -> dict:
        """Parse Predict product response."""
        result = {"raw": content, "answers": {}, "confidence_scores": {}, "reasoning": {}}

        lines = content.split("\n")
        current_q = None

        for line in lines:
            line = line.strip()

            # Match [Q1_ANSWER]: format
            if "_ANSWER]:" in line or "_ANSWER]" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    # Extract question number
                    q_part = parts[0].replace("[", "").replace("]", "")
                    q_num = q_part.split("_")[0]
                    result["answers"][q_num] = parts[1].strip()
                    current_q = q_num
            elif "_CONFIDENCE]:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    q_part = parts[0].replace("[", "").replace("]", "")
                    q_num = q_part.split("_")[0]
                    try:
                        result["confidence_scores"][q_num] = int(parts[1].strip())
                    except ValueError:
                        result["confidence_scores"][q_num] = 5
            elif "_REASON]:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    q_part = parts[0].replace("[", "").replace("]", "")
                    q_num = q_part.split("_")[0]
                    result["reasoning"][q_num] = parts[1].strip()

        return result

    @staticmethod
    def parse_insight_response(content: str) -> dict:
        """Parse Insight product response."""
        result = {
            "raw": content,
            "responses": {},
            "emotions": {},
            "intensities": {}
        }

        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            if "_RESPONSE]:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    q_part = parts[0].replace("[", "").replace("]", "")
                    q_num = q_part.split("_")[0]
                    result["responses"][q_num] = parts[1].strip()
            elif "_EMOTION]:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    q_part = parts[0].replace("[", "").replace("]", "")
                    q_num = q_part.split("_")[0]
                    result["emotions"][q_num] = parts[1].strip().lower()
            elif "_INTENSITY]:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    q_part = parts[0].replace("[", "").replace("]", "")
                    q_num = q_part.split("_")[0]
                    try:
                        result["intensities"][q_num] = int(parts[1].strip())
                    except ValueError:
                        result["intensities"][q_num] = 5

        return result

    @staticmethod
    def parse_simulate_response(content: str) -> dict:
        """Parse Simulate product response."""
        result = {
            "raw": content,
            "initial_reaction": "",
            "detailed_thoughts": "",
            "key_concern": "",
            "enthusiasm_level": 5,
            "likelihood_to_act": 5,
            "reasoning": ""
        }

        field_mapping = {
            "INITIAL_REACTION": "initial_reaction",
            "DETAILED_THOUGHTS": "detailed_thoughts",
            "KEY_CONCERN": "key_concern",
            "ENTHUSIASM_LEVEL": "enthusiasm_level",
            "LIKELIHOOD_TO_ACT": "likelihood_to_act",
            "REASONING": "reasoning"
        }

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            for key, field in field_mapping.items():
                if f"[{key}]:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        value = parts[1].strip()
                        if field in ["enthusiasm_level", "likelihood_to_act"]:
                            try:
                                result[field] = int(value)
                            except ValueError:
                                pass
                        else:
                            result[field] = value
                    break

        return result

    # ============= ORACLE Response Parser =============

    @staticmethod
    def parse_oracle_response(content: str) -> dict:
        """Parse ORACLE product response (Market Intelligence)."""
        result = {
            "raw": content,
            "purchase_intent": 5,
            "brand_preference": "",
            "price_sensitivity": 5,
            "switching_likelihood": 5,
            "key_drivers": [],
            "barriers": [],
            "timeline": "3-6 months",
            "channel_preference": "online",
            "influence_factors": "",
            "confidence": 5
        }

        field_mapping = {
            "PURCHASE_INTENT": ("purchase_intent", "int"),
            "BRAND_PREFERENCE": ("brand_preference", "str"),
            "PRICE_SENSITIVITY": ("price_sensitivity", "int"),
            "SWITCHING_LIKELIHOOD": ("switching_likelihood", "int"),
            "KEY_DRIVERS": ("key_drivers", "list"),
            "BARRIERS": ("barriers", "list"),
            "TIMELINE": ("timeline", "str"),
            "CHANNEL_PREFERENCE": ("channel_preference", "str"),
            "INFLUENCE_FACTORS": ("influence_factors", "str"),
            "CONFIDENCE": ("confidence", "int")
        }

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            for key, (field, field_type) in field_mapping.items():
                if f"[{key}]:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        value = parts[1].strip()
                        if field_type == "int":
                            try:
                                # Extract first number from string
                                import re
                                nums = re.findall(r'\d+', value)
                                result[field] = int(nums[0]) if nums else 5
                            except (ValueError, IndexError):
                                pass
                        elif field_type == "list":
                            result[field] = [x.strip() for x in value.split(",") if x.strip()]
                        else:
                            result[field] = value
                    break

        return result

    # ============= PULSE Response Parser =============

    @staticmethod
    def parse_pulse_response(content: str) -> dict:
        """Parse PULSE product response (Political Simulation)."""
        result = {
            "raw": content,
            "vote_choice": "",
            "vote_certainty": 5,
            "enthusiasm": 5,
            "turnout_likelihood": 5,
            "top_issues": [],
            "candidate_perception": "",
            "persuadability": 5,
            "swing_factors": "",
            "information_sources": [],
            "party_alignment": 5,
            "policy_vs_personality": "equal",
            "confidence": 5
        }

        field_mapping = {
            "VOTE_CHOICE": ("vote_choice", "str"),
            "VOTE_CERTAINTY": ("vote_certainty", "int"),
            "ENTHUSIASM": ("enthusiasm", "int"),
            "TURNOUT_LIKELIHOOD": ("turnout_likelihood", "int"),
            "TOP_ISSUES": ("top_issues", "list"),
            "CANDIDATE_PERCEPTION": ("candidate_perception", "str"),
            "PERSUADABILITY": ("persuadability", "int"),
            "SWING_FACTORS": ("swing_factors", "str"),
            "INFORMATION_SOURCES": ("information_sources", "list"),
            "PARTY_ALIGNMENT": ("party_alignment", "int"),
            "POLICY_VS_PERSONALITY": ("policy_vs_personality", "str"),
            "CONFIDENCE": ("confidence", "int")
        }

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            for key, (field, field_type) in field_mapping.items():
                if f"[{key}]:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        value = parts[1].strip()
                        if field_type == "int":
                            try:
                                import re
                                nums = re.findall(r'\d+', value)
                                result[field] = int(nums[0]) if nums else 5
                            except (ValueError, IndexError):
                                pass
                        elif field_type == "list":
                            result[field] = [x.strip() for x in value.split(",") if x.strip()]
                        else:
                            result[field] = value
                    break

        return result

    # ============= PRISM Response Parser =============

    @staticmethod
    def parse_prism_response(content: str) -> dict:
        """Parse PRISM product response (Public Sector Analytics)."""
        result = {
            "raw": content,
            "policy_support": 5,
            "personal_impact": "neutral",
            "impact_magnitude": 5,
            "trust_level": 5,
            "compliance_likelihood": 5,
            "key_concerns": [],
            "benefits_perceived": [],
            "stakeholder_position": "neutral",
            "community_impact": "",
            "alternative_preferred": "",
            "crisis_preparedness": 5,
            "information_needs": [],
            "behavioral_change": "",
            "confidence": 5
        }

        field_mapping = {
            "POLICY_SUPPORT": ("policy_support", "int"),
            "PERSONAL_IMPACT": ("personal_impact", "str"),
            "IMPACT_MAGNITUDE": ("impact_magnitude", "int"),
            "TRUST_LEVEL": ("trust_level", "int"),
            "COMPLIANCE_LIKELIHOOD": ("compliance_likelihood", "int"),
            "KEY_CONCERNS": ("key_concerns", "list"),
            "BENEFITS_PERCEIVED": ("benefits_perceived", "list"),
            "STAKEHOLDER_POSITION": ("stakeholder_position", "str"),
            "COMMUNITY_IMPACT": ("community_impact", "str"),
            "ALTERNATIVE_PREFERRED": ("alternative_preferred", "str"),
            "CRISIS_PREPAREDNESS": ("crisis_preparedness", "int"),
            "INFORMATION_NEEDS": ("information_needs", "list"),
            "BEHAVIORAL_CHANGE": ("behavioral_change", "str"),
            "CONFIDENCE": ("confidence", "int")
        }

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            for key, (field, field_type) in field_mapping.items():
                if f"[{key}]:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        value = parts[1].strip()
                        if field_type == "int":
                            try:
                                import re
                                nums = re.findall(r'\d+', value)
                                result[field] = int(nums[0]) if nums else 5
                            except (ValueError, IndexError):
                                pass
                        elif field_type == "list":
                            result[field] = [x.strip() for x in value.split(",") if x.strip()]
                        else:
                            result[field] = value
                    break

        return result


# ============= Result Aggregator =============

class ResultAggregator:
    """Aggregates agent responses into ProductResult."""

    @staticmethod
    def aggregate_predict_results(
        interactions: list[AgentInteraction],
        product: Product
    ) -> dict:
        """Aggregate Predict product results."""
        all_answers = []
        all_confidences = []
        answer_counts = {}

        for interaction in interactions:
            responses = interaction.responses
            answers = responses.get("answers", {})
            confidences = responses.get("confidence_scores", {})

            for q_id, answer in answers.items():
                answer_lower = answer.lower().strip()
                all_answers.append(answer_lower)
                if answer_lower not in answer_counts:
                    answer_counts[answer_lower] = 0
                answer_counts[answer_lower] += 1

            for conf in confidences.values():
                if isinstance(conf, (int, float)):
                    all_confidences.append(conf)

        total = len(interactions)

        # Calculate primary prediction
        if answer_counts:
            top_answer = max(answer_counts, key=answer_counts.get)
            top_percentage = answer_counts[top_answer] / total if total > 0 else 0
        else:
            top_answer = "Unknown"
            top_percentage = 0

        # Calculate confidence interval (simplified)
        margin_of_error = 1.96 * (0.5 / (total ** 0.5)) if total > 0 else 0.5

        avg_confidence = statistics.mean(all_confidences) / 10 if all_confidences else 0.5

        return {
            "predictions": {
                "primary_prediction": {
                    "outcome": top_answer,
                    "value": round(top_percentage, 4),
                    "confidence_interval": [
                        round(max(0, top_percentage - margin_of_error), 4),
                        round(min(1, top_percentage + margin_of_error), 4)
                    ],
                    "confidence_level": 0.95
                },
                "response_distribution": {
                    answer: round(count / total, 4) if total > 0 else 0
                    for answer, count in answer_counts.items()
                }
            },
            "statistical_analysis": {
                "sample_size": total,
                "margin_of_error": round(margin_of_error, 4),
                "avg_confidence": round(avg_confidence, 4)
            },
            "confidence_score": round(avg_confidence * 0.7 + top_percentage * 0.3, 4)
        }

    @staticmethod
    def aggregate_insight_results(
        interactions: list[AgentInteraction],
        product: Product
    ) -> dict:
        """Aggregate Insight product results."""
        all_emotions = []
        emotion_counts = {}
        all_intensities = []
        themes = []

        for interaction in interactions:
            responses = interaction.responses
            emotions = responses.get("emotions", {})
            intensities = responses.get("intensities", {})
            key_themes = interaction.key_themes or []

            for emotion in emotions.values():
                all_emotions.append(emotion)
                if emotion not in emotion_counts:
                    emotion_counts[emotion] = 0
                emotion_counts[emotion] += 1

            for intensity in intensities.values():
                if isinstance(intensity, (int, float)):
                    all_intensities.append(intensity)

            themes.extend(key_themes)

        total = len(interactions)

        # Count theme frequencies
        theme_counts = {}
        for theme in themes:
            if theme not in theme_counts:
                theme_counts[theme] = 0
            theme_counts[theme] += 1

        avg_intensity = statistics.mean(all_intensities) if all_intensities else 5

        return {
            "insights": {
                "key_insights": [
                    {
                        "theme": theme,
                        "frequency": count,
                        "percentage": round(count / total, 4) if total > 0 else 0
                    }
                    for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1])[:10]
                ],
                "emotion_analysis": {
                    emotion: round(count / total, 4) if total > 0 else 0
                    for emotion, count in sorted(emotion_counts.items(), key=lambda x: -x[1])
                },
                "avg_intensity": round(avg_intensity, 2)
            },
            "statistical_analysis": {
                "sample_size": total,
                "unique_themes": len(theme_counts),
                "unique_emotions": len(emotion_counts)
            },
            "confidence_score": round(min(0.95, total / 100 * 0.5 + avg_intensity / 10 * 0.5), 4)
        }

    @staticmethod
    def aggregate_simulate_results(
        interactions: list[AgentInteraction],
        product: Product
    ) -> dict:
        """Aggregate Simulate product results."""
        enthusiasm_levels = []
        likelihood_scores = []
        concerns = []
        reactions = []

        for interaction in interactions:
            responses = interaction.responses

            if "enthusiasm_level" in responses:
                enthusiasm_levels.append(responses["enthusiasm_level"])
            if "likelihood_to_act" in responses:
                likelihood_scores.append(responses["likelihood_to_act"])
            if responses.get("key_concern"):
                concerns.append(responses["key_concern"])
            if responses.get("initial_reaction"):
                reactions.append(responses["initial_reaction"])

        total = len(interactions)

        avg_enthusiasm = statistics.mean(enthusiasm_levels) if enthusiasm_levels else 5
        avg_likelihood = statistics.mean(likelihood_scores) if likelihood_scores else 5

        # Categorize sentiment
        positive = len([e for e in enthusiasm_levels if e >= 7])
        neutral = len([e for e in enthusiasm_levels if 4 <= e < 7])
        negative = len([e for e in enthusiasm_levels if e < 4])

        return {
            "simulation_outcomes": {
                "session_dynamics": {
                    "avg_enthusiasm": round(avg_enthusiasm, 2),
                    "avg_likelihood": round(avg_likelihood, 2),
                    "sentiment_distribution": {
                        "positive": round(positive / total, 4) if total > 0 else 0,
                        "neutral": round(neutral / total, 4) if total > 0 else 0,
                        "negative": round(negative / total, 4) if total > 0 else 0
                    }
                },
                "key_quotes": reactions[:10],  # Top 10 reactions
                "common_concerns": concerns[:10]
            },
            "statistical_analysis": {
                "sample_size": total,
                "enthusiasm_std": round(statistics.stdev(enthusiasm_levels), 2) if len(enthusiasm_levels) > 1 else 0,
                "likelihood_std": round(statistics.stdev(likelihood_scores), 2) if len(likelihood_scores) > 1 else 0
            },
            "confidence_score": round(avg_likelihood / 10, 4)
        }

    # ============= ORACLE Results Aggregator =============

    @staticmethod
    def aggregate_oracle_results(
        interactions: list[AgentInteraction],
        product: Product
    ) -> dict:
        """Aggregate ORACLE product results (Market Intelligence)."""
        purchase_intents = []
        price_sensitivities = []
        switching_likelihoods = []
        brand_preferences = {}
        all_drivers = []
        all_barriers = []
        timelines = {}
        channels = {}
        confidences = []

        for interaction in interactions:
            responses = interaction.responses

            if "purchase_intent" in responses:
                purchase_intents.append(responses["purchase_intent"])
            if "price_sensitivity" in responses:
                price_sensitivities.append(responses["price_sensitivity"])
            if "switching_likelihood" in responses:
                switching_likelihoods.append(responses["switching_likelihood"])
            if responses.get("brand_preference"):
                pref = responses["brand_preference"].lower().strip()[:50]  # Truncate for grouping
                brand_preferences[pref] = brand_preferences.get(pref, 0) + 1
            if responses.get("key_drivers"):
                all_drivers.extend(responses["key_drivers"])
            if responses.get("barriers"):
                all_barriers.extend(responses["barriers"])
            if responses.get("timeline"):
                t = responses["timeline"].lower()
                timelines[t] = timelines.get(t, 0) + 1
            if responses.get("channel_preference"):
                c = responses["channel_preference"].lower()
                channels[c] = channels.get(c, 0) + 1
            if "confidence" in responses:
                confidences.append(responses["confidence"])

        total = len(interactions)

        # Calculate metrics
        avg_purchase_intent = statistics.mean(purchase_intents) if purchase_intents else 5
        avg_price_sensitivity = statistics.mean(price_sensitivities) if price_sensitivities else 5
        avg_switching = statistics.mean(switching_likelihoods) if switching_likelihoods else 5
        avg_confidence = statistics.mean(confidences) if confidences else 5

        # Count driver frequencies
        driver_counts = {}
        for d in all_drivers:
            d_lower = d.lower().strip()
            driver_counts[d_lower] = driver_counts.get(d_lower, 0) + 1

        barrier_counts = {}
        for b in all_barriers:
            b_lower = b.lower().strip()
            barrier_counts[b_lower] = barrier_counts.get(b_lower, 0) + 1

        # Calculate market forecast
        high_intent_count = len([p for p in purchase_intents if p >= 7])
        predicted_adoption = high_intent_count / total if total > 0 else 0
        margin = 1.96 * (0.5 / (total ** 0.5)) if total > 0 else 0.5

        return {
            "oracle_analysis": {
                "market_forecast": {
                    "predicted_adoption_rate": round(predicted_adoption, 4),
                    "confidence_interval": [
                        round(max(0, predicted_adoption - margin), 4),
                        round(min(1, predicted_adoption + margin), 4)
                    ],
                    "avg_purchase_intent": round(avg_purchase_intent, 2),
                    "intent_distribution": {
                        "high_intent": round(high_intent_count / total, 4) if total > 0 else 0,
                        "medium_intent": round(len([p for p in purchase_intents if 4 <= p < 7]) / total, 4) if total > 0 else 0,
                        "low_intent": round(len([p for p in purchase_intents if p < 4]) / total, 4) if total > 0 else 0
                    }
                },
                "consumer_segments": {
                    "price_sensitivity": {
                        "avg_score": round(avg_price_sensitivity, 2),
                        "high_sensitivity": round(len([p for p in price_sensitivities if p >= 7]) / total, 4) if total > 0 else 0
                    },
                    "switching_propensity": {
                        "avg_score": round(avg_switching, 2),
                        "likely_switchers": round(len([s for s in switching_likelihoods if s >= 7]) / total, 4) if total > 0 else 0
                    }
                },
                "decision_drivers": [
                    {"driver": k, "frequency": v, "percentage": round(v / total, 4) if total > 0 else 0}
                    for k, v in sorted(driver_counts.items(), key=lambda x: -x[1])[:10]
                ],
                "purchase_barriers": [
                    {"barrier": k, "frequency": v, "percentage": round(v / total, 4) if total > 0 else 0}
                    for k, v in sorted(barrier_counts.items(), key=lambda x: -x[1])[:10]
                ],
                "brand_preferences": {
                    k: round(v / total, 4) if total > 0 else 0
                    for k, v in sorted(brand_preferences.items(), key=lambda x: -x[1])[:5]
                },
                "timeline_analysis": {
                    k: round(v / total, 4) if total > 0 else 0
                    for k, v in timelines.items()
                },
                "channel_preferences": {
                    k: round(v / total, 4) if total > 0 else 0
                    for k, v in channels.items()
                }
            },
            "statistical_analysis": {
                "sample_size": total,
                "margin_of_error": round(margin, 4),
                "avg_confidence": round(avg_confidence / 10, 4)
            },
            "confidence_score": round(avg_confidence / 10 * 0.5 + predicted_adoption * 0.5, 4)
        }

    # ============= PULSE Results Aggregator =============

    @staticmethod
    def aggregate_pulse_results(
        interactions: list[AgentInteraction],
        product: Product
    ) -> dict:
        """Aggregate PULSE product results (Political Simulation)."""
        vote_choices = {}
        certainties = []
        enthusiasms = []
        turnout_likelihoods = []
        all_issues = []
        persuadabilities = []
        party_alignments = []
        policy_vs_personality = {"policy": 0, "personality": 0, "equal": 0}
        confidences = []

        for interaction in interactions:
            responses = interaction.responses

            if responses.get("vote_choice"):
                choice = responses["vote_choice"].strip()
                vote_choices[choice] = vote_choices.get(choice, 0) + 1
            if "vote_certainty" in responses:
                certainties.append(responses["vote_certainty"])
            if "enthusiasm" in responses:
                enthusiasms.append(responses["enthusiasm"])
            if "turnout_likelihood" in responses:
                turnout_likelihoods.append(responses["turnout_likelihood"])
            if responses.get("top_issues"):
                all_issues.extend(responses["top_issues"])
            if "persuadability" in responses:
                persuadabilities.append(responses["persuadability"])
            if "party_alignment" in responses:
                party_alignments.append(responses["party_alignment"])
            if responses.get("policy_vs_personality"):
                pvp = responses["policy_vs_personality"].lower()
                if pvp in policy_vs_personality:
                    policy_vs_personality[pvp] += 1
            if "confidence" in responses:
                confidences.append(responses["confidence"])

        total = len(interactions)

        # Calculate vote distribution
        vote_distribution = {
            k: {"votes": v, "percentage": round(v / total, 4) if total > 0 else 0}
            for k, v in sorted(vote_choices.items(), key=lambda x: -x[1])
        }

        # Determine predicted winner
        if vote_choices:
            predicted_winner = max(vote_choices, key=vote_choices.get)
            winner_votes = vote_choices[predicted_winner]
            win_probability = winner_votes / total if total > 0 else 0
        else:
            predicted_winner = "Undetermined"
            win_probability = 0

        # Issue frequency
        issue_counts = {}
        for issue in all_issues:
            issue_lower = issue.lower().strip()
            issue_counts[issue_lower] = issue_counts.get(issue_lower, 0) + 1

        # Calculate averages
        avg_certainty = statistics.mean(certainties) if certainties else 5
        avg_enthusiasm = statistics.mean(enthusiasms) if enthusiasms else 5
        avg_turnout = statistics.mean(turnout_likelihoods) if turnout_likelihoods else 5
        avg_persuadability = statistics.mean(persuadabilities) if persuadabilities else 5
        avg_party_alignment = statistics.mean(party_alignments) if party_alignments else 5
        avg_confidence = statistics.mean(confidences) if confidences else 5

        # Margin of error calculation
        margin = 1.96 * (0.5 / (total ** 0.5)) if total > 0 else 0.5

        return {
            "pulse_analysis": {
                "election_forecast": {
                    "candidates": [
                        {
                            "name": k,
                            "predicted_vote": round(v / total, 4) if total > 0 else 0,
                            "vote_count": v,
                            "confidence_interval": [
                                round(max(0, v / total - margin), 4) if total > 0 else 0,
                                round(min(1, v / total + margin), 4) if total > 0 else 0
                            ]
                        }
                        for k, v in sorted(vote_choices.items(), key=lambda x: -x[1])
                    ],
                    "predicted_winner": predicted_winner,
                    "win_probability": round(win_probability, 4)
                },
                "voter_engagement": {
                    "avg_certainty": round(avg_certainty, 2),
                    "avg_enthusiasm": round(avg_enthusiasm, 2),
                    "avg_turnout_likelihood": round(avg_turnout, 2),
                    "predicted_turnout": round(len([t for t in turnout_likelihoods if t >= 7]) / total, 4) if total > 0 else 0,
                    "high_enthusiasm_voters": round(len([e for e in enthusiasms if e >= 7]) / total, 4) if total > 0 else 0
                },
                "swing_voter_analysis": {
                    "avg_persuadability": round(avg_persuadability, 2),
                    "swing_voters": round(len([p for p in persuadabilities if p >= 6]) / total, 4) if total > 0 else 0,
                    "committed_voters": round(len([p for p in persuadabilities if p <= 3]) / total, 4) if total > 0 else 0
                },
                "issue_importance": [
                    {"issue": k, "mentions": v, "percentage": round(v / total, 4) if total > 0 else 0}
                    for k, v in sorted(issue_counts.items(), key=lambda x: -x[1])[:10]
                ],
                "party_dynamics": {
                    "avg_party_alignment": round(avg_party_alignment, 2),
                    "strong_partisans": round(len([p for p in party_alignments if p >= 8]) / total, 4) if total > 0 else 0,
                    "independents": round(len([p for p in party_alignments if p <= 3]) / total, 4) if total > 0 else 0
                },
                "decision_factors": {
                    k: round(v / total, 4) if total > 0 else 0
                    for k, v in policy_vs_personality.items()
                }
            },
            "statistical_analysis": {
                "sample_size": total,
                "margin_of_error": round(margin, 4),
                "avg_confidence": round(avg_confidence / 10, 4)
            },
            "confidence_score": round(avg_confidence / 10 * 0.4 + avg_certainty / 10 * 0.3 + win_probability * 0.3, 4)
        }

    # ============= PRISM Results Aggregator =============

    @staticmethod
    def aggregate_prism_results(
        interactions: list[AgentInteraction],
        product: Product
    ) -> dict:
        """Aggregate PRISM product results (Public Sector Analytics)."""
        policy_supports = []
        personal_impacts = {"positive": 0, "neutral": 0, "negative": 0}
        impact_magnitudes = []
        trust_levels = []
        compliance_likelihoods = []
        all_concerns = []
        all_benefits = []
        stakeholder_positions = {"support": 0, "oppose": 0, "neutral": 0}
        crisis_preparedness = []
        confidences = []

        for interaction in interactions:
            responses = interaction.responses

            if "policy_support" in responses:
                policy_supports.append(responses["policy_support"])
            if responses.get("personal_impact"):
                impact = responses["personal_impact"].lower()
                if impact in personal_impacts:
                    personal_impacts[impact] += 1
            if "impact_magnitude" in responses:
                impact_magnitudes.append(responses["impact_magnitude"])
            if "trust_level" in responses:
                trust_levels.append(responses["trust_level"])
            if "compliance_likelihood" in responses:
                compliance_likelihoods.append(responses["compliance_likelihood"])
            if responses.get("key_concerns"):
                all_concerns.extend(responses["key_concerns"])
            if responses.get("benefits_perceived"):
                all_benefits.extend(responses["benefits_perceived"])
            if responses.get("stakeholder_position"):
                pos = responses["stakeholder_position"].lower()
                if pos in stakeholder_positions:
                    stakeholder_positions[pos] += 1
            if "crisis_preparedness" in responses:
                crisis_preparedness.append(responses["crisis_preparedness"])
            if "confidence" in responses:
                confidences.append(responses["confidence"])

        total = len(interactions)

        # Calculate averages
        avg_support = statistics.mean(policy_supports) if policy_supports else 5
        avg_magnitude = statistics.mean(impact_magnitudes) if impact_magnitudes else 5
        avg_trust = statistics.mean(trust_levels) if trust_levels else 5
        avg_compliance = statistics.mean(compliance_likelihoods) if compliance_likelihoods else 5
        avg_preparedness = statistics.mean(crisis_preparedness) if crisis_preparedness else 5
        avg_confidence = statistics.mean(confidences) if confidences else 5

        # Count concern frequencies
        concern_counts = {}
        for c in all_concerns:
            c_lower = c.lower().strip()
            concern_counts[c_lower] = concern_counts.get(c_lower, 0) + 1

        benefit_counts = {}
        for b in all_benefits:
            b_lower = b.lower().strip()
            benefit_counts[b_lower] = benefit_counts.get(b_lower, 0) + 1

        # Overall support calculation
        supporters = len([s for s in policy_supports if s >= 7])
        opposers = len([s for s in policy_supports if s <= 3])
        overall_support = supporters / total if total > 0 else 0
        margin = 1.96 * (0.5 / (total ** 0.5)) if total > 0 else 0.5

        return {
            "prism_analysis": {
                "policy_impact": {
                    "overall_support": round(overall_support, 4),
                    "confidence_interval": [
                        round(max(0, overall_support - margin), 4),
                        round(min(1, overall_support + margin), 4)
                    ],
                    "avg_support_score": round(avg_support, 2),
                    "support_distribution": {
                        "strong_support": round(supporters / total, 4) if total > 0 else 0,
                        "moderate": round(len([s for s in policy_supports if 4 <= s < 7]) / total, 4) if total > 0 else 0,
                        "opposition": round(opposers / total, 4) if total > 0 else 0
                    }
                },
                "stakeholder_map": {
                    "positions": {
                        k: round(v / total, 4) if total > 0 else 0
                        for k, v in stakeholder_positions.items()
                    },
                    "personal_impact_distribution": {
                        k: round(v / total, 4) if total > 0 else 0
                        for k, v in personal_impacts.items()
                    },
                    "avg_impact_magnitude": round(avg_magnitude, 2)
                },
                "trust_analysis": {
                    "avg_trust_level": round(avg_trust, 2),
                    "high_trust": round(len([t for t in trust_levels if t >= 7]) / total, 4) if total > 0 else 0,
                    "low_trust": round(len([t for t in trust_levels if t <= 3]) / total, 4) if total > 0 else 0
                },
                "compliance_forecast": {
                    "avg_compliance": round(avg_compliance, 2),
                    "likely_compliance": round(len([c for c in compliance_likelihoods if c >= 7]) / total, 4) if total > 0 else 0,
                    "resistance_expected": round(len([c for c in compliance_likelihoods if c <= 3]) / total, 4) if total > 0 else 0
                },
                "key_concerns": [
                    {"concern": k, "frequency": v, "percentage": round(v / total, 4) if total > 0 else 0}
                    for k, v in sorted(concern_counts.items(), key=lambda x: -x[1])[:10]
                ],
                "perceived_benefits": [
                    {"benefit": k, "frequency": v, "percentage": round(v / total, 4) if total > 0 else 0}
                    for k, v in sorted(benefit_counts.items(), key=lambda x: -x[1])[:10]
                ],
                "crisis_readiness": {
                    "avg_preparedness": round(avg_preparedness, 2),
                    "well_prepared": round(len([p for p in crisis_preparedness if p >= 7]) / total, 4) if total > 0 else 0,
                    "unprepared": round(len([p for p in crisis_preparedness if p <= 3]) / total, 4) if total > 0 else 0
                }
            },
            "statistical_analysis": {
                "sample_size": total,
                "margin_of_error": round(margin, 4),
                "avg_confidence": round(avg_confidence / 10, 4)
            },
            "confidence_score": round(avg_confidence / 10 * 0.4 + overall_support * 0.3 + avg_trust / 10 * 0.3, 4)
        }

    @staticmethod
    def calculate_segment_analysis(
        interactions: list[AgentInteraction],
        product: Product
    ) -> dict:
        """Calculate segment-level analysis."""
        segments = {
            "by_age": {},
            "by_income": {},
            "by_gender": {},
            "by_region": {}
        }

        for interaction in interactions:
            persona = interaction.persona_summary
            demographics = persona.get("demographics", {})
            responses = interaction.responses

            # Get primary metric based on product type
            if product.product_type == "predict":
                metric = responses.get("answers", {}).get("Q1", "Unknown")
            elif product.product_type == "insight":
                metric = responses.get("emotions", {}).get("Q1", "neutral")
            else:  # simulate
                metric = responses.get("likelihood_to_act", 5)

            # Segment by age
            age = demographics.get("age", 0)
            age_group = ResultAggregator._get_age_group(age)
            if age_group not in segments["by_age"]:
                segments["by_age"][age_group] = []
            segments["by_age"][age_group].append(metric)

            # Segment by income
            income = demographics.get("income_bracket", "middle")
            if income not in segments["by_income"]:
                segments["by_income"][income] = []
            segments["by_income"][income].append(metric)

            # Segment by gender
            gender = demographics.get("gender", "unknown")
            if gender not in segments["by_gender"]:
                segments["by_gender"][gender] = []
            segments["by_gender"][gender].append(metric)

        # Aggregate segment data
        result = {}
        for segment_type, segment_data in segments.items():
            result[segment_type] = {}
            for segment_value, metrics in segment_data.items():
                if metrics:
                    if all(isinstance(m, (int, float)) for m in metrics):
                        result[segment_type][segment_value] = {
                            "count": len(metrics),
                            "avg": round(statistics.mean(metrics), 2)
                        }
                    else:
                        counts = {}
                        for m in metrics:
                            m_str = str(m).lower()
                            counts[m_str] = counts.get(m_str, 0) + 1
                        result[segment_type][segment_value] = {
                            "count": len(metrics),
                            "distribution": counts
                        }

        return result

    @staticmethod
    def _get_age_group(age: int) -> str:
        if age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        elif age < 65:
            return "55-64"
        else:
            return "65+"


# ============= Main Execution Service =============

class ProductExecutionService:
    """
    Main service for executing Product runs.
    Orchestrates persona generation, LLM calls, and result aggregation.
    """

    def __init__(
        self,
        openrouter: Optional[OpenRouterService] = None,
        batch_size: int = 50,
        max_concurrency: int = 10
    ):
        self.openrouter = openrouter or OpenRouterService()
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.prompt_builder = ProductPromptBuilder()
        self.response_parser = ResponseParser()
        self.result_aggregator = ResultAggregator()

    async def execute_run(
        self,
        product: Product,
        run: ProductRun,
        db: AsyncSession,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProductResult:
        """
        Execute a product run.

        Args:
            product: The Product configuration
            run: The ProductRun to execute
            db: Database session
            progress_callback: Optional callback for progress updates

        Returns:
            ProductResult with aggregated analysis
        """
        logger.info(f"Starting execution for Product {product.id}, Run {run.id}")

        # Update run status
        run.status = "running"
        run.started_at = datetime.utcnow()
        await db.flush()

        try:
            # Generate personas
            personas = await self._generate_personas(product, db)
            run.agents_total = len(personas)
            await db.flush()

            # Process in batches
            all_interactions = []
            total_tokens = 0
            total_cost = 0.0
            agents_completed = 0
            agents_failed = 0

            for batch_start in range(0, len(personas), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(personas))
                batch = personas[batch_start:batch_end]

                # Process batch
                batch_results = await self._process_batch(
                    product=product,
                    run=run,
                    personas=batch,
                    start_index=batch_start,
                    db=db
                )

                # Record results
                for result in batch_results:
                    if result["success"]:
                        agents_completed += 1
                        total_tokens += result["tokens"]
                        total_cost += result["cost"]
                        all_interactions.append(result["interaction"])
                    else:
                        agents_failed += 1

                # Update progress
                progress = int((batch_end / len(personas)) * 100)
                run.progress = progress
                run.agents_completed = agents_completed
                run.agents_failed = agents_failed
                run.tokens_used = total_tokens
                run.estimated_cost = total_cost
                await db.flush()

                if progress_callback:
                    await progress_callback(
                        progress,
                        agents_completed,
                        agents_failed,
                        {"batch_end": batch_end, "total": len(personas)}
                    )

            # Aggregate results
            result = await self._create_result(
                product=product,
                run=run,
                interactions=all_interactions,
                db=db
            )

            # Finalize run
            run.status = "completed"
            run.progress = 100
            run.completed_at = datetime.utcnow()
            product.status = "completed"
            product.completed_at = datetime.utcnow()

            await db.commit()

            logger.info(f"Completed execution for Product {product.id}, Run {run.id}")
            return result

        except Exception as e:
            logger.error(f"Execution failed for Product {product.id}: {str(e)}")
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            product.status = "failed"
            await db.commit()
            raise e

    async def _generate_personas(
        self,
        product: Product,
        db: AsyncSession
    ) -> list[GeneratedPersona]:
        """Generate personas for the product run."""
        target_market = product.target_market
        regions = target_market.get("regions", ["us"])
        count = product.persona_count

        # Check for existing persona template
        if product.persona_template_id:
            # Load personas from template
            query = select(PersonaRecord).where(
                PersonaRecord.template_id == product.persona_template_id
            ).limit(count)
            result = await db.execute(query)
            records = result.scalars().all()

            if records:
                return [
                    GeneratedPersona(
                        demographics=r.demographics,
                        professional=r.professional,
                        psychographics=r.psychographics,
                        behavioral=r.behavioral,
                        interests=r.interests,
                        topic_knowledge=r.topic_knowledge,
                        cultural_context=r.cultural_context,
                        full_prompt=r.full_prompt,
                        confidence_score=r.confidence_score
                    )
                    for r in records
                ]

        # Generate new personas
        # Determine topic from configuration
        config = product.configuration
        topic = config.get("topic") or config.get("prediction_type") or config.get("insight_type")
        industry = config.get("industry")

        personas = []
        personas_per_region = count // len(regions)
        remainder = count % len(regions)

        for i, region in enumerate(regions):
            region_count = personas_per_region + (1 if i < remainder else 0)

            gen_config = PersonaGenerationConfig(
                region=region,
                topic=topic,
                industry=industry,
                count=region_count,
                include_psychographics=True,
                include_behavioral=True,
                include_cultural=True,
                include_topic_knowledge=True
            )

            # Create generator with config and generate personas
            generator = AdvancedPersonaGenerator(gen_config)
            region_personas = await generator.generate_personas(region_count)
            personas.extend(region_personas)

        return personas

    async def _process_batch(
        self,
        product: Product,
        run: ProductRun,
        personas: list[GeneratedPersona],
        start_index: int,
        db: AsyncSession
    ) -> list[dict]:
        """Process a batch of personas."""
        # Build prompts
        requests = []
        for persona in personas:
            if product.product_type == "predict":
                messages = self.prompt_builder.build_predict_prompt(product, persona)
            elif product.product_type == "insight":
                messages = self.prompt_builder.build_insight_prompt(product, persona)
            elif product.product_type == "simulate":
                messages = self.prompt_builder.build_simulate_prompt(product, persona)
            elif product.product_type == "oracle":
                messages = self.prompt_builder.build_oracle_prompt(product, persona)
            elif product.product_type == "pulse":
                messages = self.prompt_builder.build_pulse_prompt(product, persona)
            elif product.product_type == "prism":
                messages = self.prompt_builder.build_prism_prompt(product, persona)
            else:
                # Default fallback to predict
                messages = self.prompt_builder.build_predict_prompt(product, persona)

            requests.append({
                "messages": messages,
                "model": product.configuration.get("model", "openai/gpt-4o-mini"),
                "temperature": 0.7,
                "max_tokens": 1000
            })

        # Execute LLM calls
        completions = await self.openrouter.batch_complete(
            requests,
            concurrency=self.max_concurrency
        )

        # Parse responses and create interactions
        results = []
        for i, (persona, completion) in enumerate(zip(personas, completions)):
            agent_index = start_index + i

            try:
                # Parse response based on product type
                if product.product_type == "predict":
                    parsed = self.response_parser.parse_predict_response(completion.content)
                elif product.product_type == "insight":
                    parsed = self.response_parser.parse_insight_response(completion.content)
                elif product.product_type == "simulate":
                    parsed = self.response_parser.parse_simulate_response(completion.content)
                elif product.product_type == "oracle":
                    parsed = self.response_parser.parse_oracle_response(completion.content)
                elif product.product_type == "pulse":
                    parsed = self.response_parser.parse_pulse_response(completion.content)
                elif product.product_type == "prism":
                    parsed = self.response_parser.parse_prism_response(completion.content)
                else:
                    parsed = self.response_parser.parse_predict_response(completion.content)

                # Create interaction record
                interaction = AgentInteraction(
                    run_id=run.id,
                    agent_index=agent_index,
                    persona_summary={
                        "demographics": persona.demographics,
                        "professional": persona.professional,
                        "psychographics": persona.psychographics
                    },
                    interaction_type=product.product_type,
                    conversation=[
                        {"role": "system", "content": persona.full_prompt},
                        {"role": "user", "content": requests[i]["messages"][-1]["content"]},
                        {"role": "agent", "content": completion.content}
                    ],
                    responses=parsed,
                    sentiment_overall=self._calculate_sentiment(parsed),
                    tokens_used=completion.total_tokens,
                    status="completed",
                    completed_at=datetime.utcnow()
                )
                db.add(interaction)

                results.append({
                    "success": True,
                    "interaction": interaction,
                    "tokens": completion.total_tokens,
                    "cost": completion.cost_usd
                })

            except Exception as e:
                logger.warning(f"Failed to process agent {agent_index}: {str(e)}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "tokens": 0,
                    "cost": 0
                })

        await db.flush()
        return results

    def _calculate_sentiment(self, parsed: dict) -> float:
        """Calculate overall sentiment from parsed response."""
        # For predict: use confidence
        if "confidence_scores" in parsed:
            scores = list(parsed["confidence_scores"].values())
            if scores:
                return sum(scores) / len(scores) / 10

        # For insight: use intensities
        if "intensities" in parsed:
            scores = list(parsed["intensities"].values())
            if scores:
                return sum(scores) / len(scores) / 10

        # For simulate: use enthusiasm
        if "enthusiasm_level" in parsed:
            return parsed["enthusiasm_level"] / 10

        # For oracle: use purchase intent
        if "purchase_intent" in parsed:
            return parsed["purchase_intent"] / 10

        # For pulse: use enthusiasm and certainty
        if "enthusiasm" in parsed and "vote_certainty" in parsed:
            return (parsed["enthusiasm"] + parsed["vote_certainty"]) / 20

        # For prism: use policy support
        if "policy_support" in parsed:
            return parsed["policy_support"] / 10

        # Fallback: check for generic confidence
        if "confidence" in parsed:
            return parsed["confidence"] / 10

        return 0.5

    async def _create_result(
        self,
        product: Product,
        run: ProductRun,
        interactions: list[AgentInteraction],
        db: AsyncSession
    ) -> ProductResult:
        """Create aggregated ProductResult."""
        # Aggregate based on product type
        if product.product_type == "predict":
            aggregated = self.result_aggregator.aggregate_predict_results(interactions, product)
            result_type = "prediction"
        elif product.product_type == "insight":
            aggregated = self.result_aggregator.aggregate_insight_results(interactions, product)
            result_type = "theme_analysis"
        elif product.product_type == "simulate":
            aggregated = self.result_aggregator.aggregate_simulate_results(interactions, product)
            result_type = "session_summary"
        elif product.product_type == "oracle":
            aggregated = self.result_aggregator.aggregate_oracle_results(interactions, product)
            result_type = "oracle_analysis"
        elif product.product_type == "pulse":
            aggregated = self.result_aggregator.aggregate_pulse_results(interactions, product)
            result_type = "pulse_analysis"
        elif product.product_type == "prism":
            aggregated = self.result_aggregator.aggregate_prism_results(interactions, product)
            result_type = "prism_analysis"
        else:
            aggregated = self.result_aggregator.aggregate_predict_results(interactions, product)
            result_type = "prediction"

        # Calculate segment analysis
        segment_analysis = self.result_aggregator.calculate_segment_analysis(interactions, product)

        # Generate executive summary (placeholder - can be enhanced with LLM)
        executive_summary = self._generate_executive_summary(product, aggregated, len(interactions))

        # Create result
        result = ProductResult(
            product_id=product.id,
            run_id=run.id,
            result_type=result_type,
            predictions=aggregated.get("predictions"),
            insights=aggregated.get("insights"),
            simulation_outcomes=aggregated.get("simulation_outcomes"),
            oracle_analysis=aggregated.get("oracle_analysis"),
            pulse_analysis=aggregated.get("pulse_analysis"),
            prism_analysis=aggregated.get("prism_analysis"),
            statistical_analysis=aggregated.get("statistical_analysis"),
            segment_analysis=segment_analysis,
            confidence_score=aggregated.get("confidence_score", 0.5),
            executive_summary=executive_summary,
            key_takeaways=self._extract_key_takeaways(aggregated),
            recommendations=self._generate_recommendations(product, aggregated)
        )

        db.add(result)
        await db.flush()

        return result

    def _generate_executive_summary(
        self,
        product: Product,
        aggregated: dict,
        sample_size: int
    ) -> str:
        """Generate executive summary."""
        if product.product_type == "predict":
            prediction = aggregated.get("predictions", {}).get("primary_prediction", {})
            outcome = prediction.get("outcome", "Unknown")
            value = prediction.get("value", 0)
            ci = prediction.get("confidence_interval", [0, 0])

            return (
                f"Based on a sample of {sample_size} synthetic respondents, "
                f"the primary prediction is '{outcome}' at {value:.1%} "
                f"(95% CI: {ci[0]:.1%} - {ci[1]:.1%}). "
                f"The overall confidence score is {aggregated.get('confidence_score', 0):.1%}."
            )
        elif product.product_type == "insight":
            insights = aggregated.get("insights", {})
            key_insights = insights.get("key_insights", [])
            top_theme = key_insights[0]["theme"] if key_insights else "No clear theme"

            return (
                f"Analysis of {sample_size} respondents reveals key themes. "
                f"The most prominent theme is '{top_theme}'. "
                f"Average emotional intensity: {insights.get('avg_intensity', 5):.1f}/10."
            )
        elif product.product_type == "simulate":
            outcomes = aggregated.get("simulation_outcomes", {})
            dynamics = outcomes.get("session_dynamics", {})

            return (
                f"Focus group simulation with {sample_size} participants completed. "
                f"Average enthusiasm: {dynamics.get('avg_enthusiasm', 5):.1f}/10. "
                f"Likelihood to act: {dynamics.get('avg_likelihood', 5):.1f}/10."
            )
        elif product.product_type == "oracle":
            oracle = aggregated.get("oracle_analysis", {})
            forecast = oracle.get("market_forecast", {})
            adoption = forecast.get("predicted_adoption_rate", 0)
            ci = forecast.get("confidence_interval", [0, 0])
            intent = forecast.get("avg_purchase_intent", 5)

            return (
                f"ORACLE Market Intelligence analysis of {sample_size} consumer agents completed. "
                f"Predicted adoption rate: {adoption:.1%} (95% CI: {ci[0]:.1%} - {ci[1]:.1%}). "
                f"Average purchase intent: {intent:.1f}/10. "
                f"Overall confidence score: {aggregated.get('confidence_score', 0):.1%}."
            )
        elif product.product_type == "pulse":
            pulse = aggregated.get("pulse_analysis", {})
            forecast = pulse.get("election_forecast", {})
            winner = forecast.get("predicted_winner", "Undetermined")
            win_prob = forecast.get("win_probability", 0)
            engagement = pulse.get("voter_engagement", {})
            turnout = engagement.get("predicted_turnout", 0)

            return (
                f"PULSE Political Simulation of {sample_size} voter agents completed. "
                f"Predicted winner: {winner} (win probability: {win_prob:.1%}). "
                f"Expected turnout: {turnout:.1%}. "
                f"Overall confidence score: {aggregated.get('confidence_score', 0):.1%}."
            )
        elif product.product_type == "prism":
            prism = aggregated.get("prism_analysis", {})
            impact = prism.get("policy_impact", {})
            support = impact.get("overall_support", 0)
            ci = impact.get("confidence_interval", [0, 0])
            trust = prism.get("trust_analysis", {}).get("avg_trust_level", 5)

            return (
                f"PRISM Public Sector Analysis of {sample_size} stakeholder agents completed. "
                f"Overall policy support: {support:.1%} (95% CI: {ci[0]:.1%} - {ci[1]:.1%}). "
                f"Average trust level: {trust:.1f}/10. "
                f"Overall confidence score: {aggregated.get('confidence_score', 0):.1%}."
            )
        else:
            return f"Analysis of {sample_size} respondents completed with confidence score {aggregated.get('confidence_score', 0):.1%}."

    def _extract_key_takeaways(self, aggregated: dict) -> list[str]:
        """Extract key takeaways from aggregated results."""
        takeaways = []

        if "predictions" in aggregated:
            pred = aggregated["predictions"]
            if "primary_prediction" in pred:
                takeaways.append(
                    f"Primary outcome: {pred['primary_prediction'].get('outcome', 'N/A')}"
                )

        if "insights" in aggregated:
            key_insights = aggregated["insights"].get("key_insights", [])
            for insight in key_insights[:3]:
                takeaways.append(f"Key theme: {insight.get('theme', 'N/A')}")

        if "simulation_outcomes" in aggregated:
            outcomes = aggregated["simulation_outcomes"]
            concerns = outcomes.get("common_concerns", [])
            if concerns:
                takeaways.append(f"Top concern: {concerns[0]}")

        # ORACLE takeaways
        if "oracle_analysis" in aggregated:
            oracle = aggregated["oracle_analysis"]
            forecast = oracle.get("market_forecast", {})
            takeaways.append(f"Predicted adoption: {forecast.get('predicted_adoption_rate', 0):.1%}")
            takeaways.append(f"Average purchase intent: {forecast.get('avg_purchase_intent', 0):.1f}/10")
            drivers = oracle.get("decision_drivers", [])
            if drivers:
                takeaways.append(f"Top driver: {drivers[0].get('driver', 'N/A')}")
            barriers = oracle.get("purchase_barriers", [])
            if barriers:
                takeaways.append(f"Top barrier: {barriers[0].get('barrier', 'N/A')}")

        # PULSE takeaways
        if "pulse_analysis" in aggregated:
            pulse = aggregated["pulse_analysis"]
            forecast = pulse.get("election_forecast", {})
            takeaways.append(f"Predicted winner: {forecast.get('predicted_winner', 'N/A')}")
            takeaways.append(f"Win probability: {forecast.get('win_probability', 0):.1%}")
            issues = pulse.get("issue_importance", [])
            if issues:
                takeaways.append(f"Top issue: {issues[0].get('issue', 'N/A')}")
            swing = pulse.get("swing_voter_analysis", {})
            takeaways.append(f"Swing voters: {swing.get('swing_voters', 0):.1%}")

        # PRISM takeaways
        if "prism_analysis" in aggregated:
            prism = aggregated["prism_analysis"]
            impact = prism.get("policy_impact", {})
            takeaways.append(f"Overall support: {impact.get('overall_support', 0):.1%}")
            trust = prism.get("trust_analysis", {})
            takeaways.append(f"Trust level: {trust.get('avg_trust_level', 0):.1f}/10")
            concerns = prism.get("key_concerns", [])
            if concerns:
                takeaways.append(f"Top concern: {concerns[0].get('concern', 'N/A')}")
            compliance = prism.get("compliance_forecast", {})
            takeaways.append(f"Expected compliance: {compliance.get('likely_compliance', 0):.1%}")

        return takeaways

    def _generate_recommendations(
        self,
        product: Product,
        aggregated: dict
    ) -> list[str]:
        """Generate recommendations based on results."""
        recommendations = []
        confidence = aggregated.get("confidence_score", 0.5)

        if confidence < 0.5:
            recommendations.append(
                "Consider increasing sample size for higher confidence"
            )

        if "predictions" in aggregated:
            dist = aggregated["predictions"].get("response_distribution", {})
            if len(dist) > 3:
                recommendations.append(
                    "High response fragmentation - consider refining options"
                )

        if "simulation_outcomes" in aggregated:
            dynamics = aggregated["simulation_outcomes"].get("session_dynamics", {})
            if dynamics.get("avg_enthusiasm", 5) < 4:
                recommendations.append(
                    "Low enthusiasm detected - review product positioning"
                )

        return recommendations


# ============= Factory Function =============

def get_product_execution_service(
    openrouter: Optional[OpenRouterService] = None
) -> ProductExecutionService:
    """Get ProductExecutionService instance."""
    return ProductExecutionService(openrouter=openrouter)
