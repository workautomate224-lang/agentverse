#!/usr/bin/env python3
"""
Comprehensive End-to-End Simulation Test
Tests the AgentVerse simulation platform with 100 agents on a complex topic.

Topic: 2024 US Presidential Election Prediction
This test validates:
1. Persona generation with diverse demographics
2. Product execution service
3. Response parsing and aggregation
4. Result generation and statistical analysis
5. Segment analysis
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_simulation.log')
    ]
)
logger = logging.getLogger(__name__)


# ============= Mock Classes for Testing =============

class MockCompletionResponse(BaseModel):
    """Mock response from LLM API."""
    content: str
    model: str = "openai/gpt-4o-mini"
    input_tokens: int = 500
    output_tokens: int = 200
    total_tokens: int = 700
    response_time_ms: int = 500
    cost_usd: float = 0.0003


class MockOpenRouterService:
    """Mock OpenRouter service that generates realistic election prediction responses."""

    def __init__(self):
        self.call_count = 0
        self.responses = []

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> MockCompletionResponse:
        """Generate mock LLM response based on persona."""
        self.call_count += 1

        # Extract persona info from system message
        system_content = messages[0]["content"] if messages else ""

        # Generate response based on persona characteristics
        response = self._generate_election_response(system_content, self.call_count)

        mock_response = MockCompletionResponse(
            content=response,
            input_tokens=len(system_content.split()),
            output_tokens=len(response.split()),
            total_tokens=len(system_content.split()) + len(response.split()),
        )

        self.responses.append(mock_response)
        return mock_response

    async def batch_complete(
        self,
        requests: list[dict],
        concurrency: int = 10
    ) -> list[MockCompletionResponse]:
        """Process batch of requests."""
        results = []
        for req in requests:
            result = await self.complete(**req)
            results.append(result)
        return results

    def _generate_election_response(self, persona_context: str, agent_id: int) -> str:
        """Generate realistic election prediction response based on persona."""
        import random

        # Seed based on agent_id for reproducibility
        random.seed(agent_id)

        # Candidates for 2024 election
        candidates = ["Candidate A (Democrat)", "Candidate B (Republican)", "Third Party", "Undecided"]

        # Determine likely vote based on persona characteristics
        if "Urban" in persona_context:
            weights = [0.55, 0.30, 0.08, 0.07]
        elif "Rural" in persona_context:
            weights = [0.30, 0.55, 0.08, 0.07]
        elif "Suburban" in persona_context:
            weights = [0.45, 0.40, 0.08, 0.07]
        else:
            weights = [0.45, 0.45, 0.05, 0.05]

        # Adjust based on age
        if "Gen Z" in persona_context or "Millennial" in persona_context:
            weights[0] += 0.10
            weights[1] -= 0.10
        elif "Baby Boomer" in persona_context:
            weights[0] -= 0.05
            weights[1] += 0.05

        # Normalize weights
        total = sum(weights)
        weights = [w/total for w in weights]

        choice = random.choices(candidates, weights=weights, k=1)[0]
        confidence = random.randint(5, 10)

        # Issues that matter
        issues = [
            "Economy", "Healthcare", "Immigration", "Climate Change",
            "Education", "National Security", "Social Issues", "Taxes"
        ]
        primary_issue = random.choice(issues)

        # Generate structured response
        yes_no = random.choice(["Yes", "No", "Maybe"])

        reasons = [
            f"I believe their stance on {primary_issue} aligns with my values",
            f"Their economic policies seem more practical",
            f"I trust their leadership experience",
            f"They represent change that we need",
            f"Their position on {primary_issue} is crucial for our future",
        ]

        response = f"""[Q1_ANSWER]: {choice}
[Q1_CONFIDENCE]: {confidence}
[Q1_REASON]: {random.choice(reasons)}

[Q2_ANSWER]: {confidence}
[Q2_CONFIDENCE]: {confidence}
[Q2_REASON]: I've been following the campaign closely and have strong opinions.

[Q3_ANSWER]: {primary_issue}
[Q3_CONFIDENCE]: {confidence}
[Q3_REASON]: This issue affects my daily life and my family's future the most.

[Q4_ANSWER]: {yes_no}
[Q4_CONFIDENCE]: {random.randint(6, 10)}
[Q4_REASON]: I would recommend based on their policy positions and leadership qualities."""

        return response


# ============= Test Data Models =============

class MockProduct:
    """Mock Product model for testing."""

    def __init__(self, product_type: str = "predict", persona_count: int = 100):
        self.id = uuid4()
        self.project_id = uuid4()
        self.user_id = uuid4()
        self.name = "2024 US Presidential Election Prediction"
        self.description = "Comprehensive election prediction study with 100 diverse synthetic voters"
        self.product_type = product_type
        self.sub_type = "election"
        self.persona_count = persona_count
        self.persona_template_id = None
        self.status = "configured"
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.completed_at = None

        # Target market configuration
        self.target_market = {
            "regions": ["us"],
            "countries": ["United States"],
            "sample_size": persona_count,
            "demographics": {
                "age_range": [18, 85],
                "include_all_income_levels": True,
                "include_all_education_levels": True
            }
        }

        # Product configuration
        self.configuration = {
            "prediction_type": "election",
            "topic": "election",
            "industry": "politics",
            "questions": [
                {"text": "Which candidate would you vote for in the 2024 presidential election?", "type": "choice"},
                {"text": "How certain are you about your choice?", "type": "scale"},
                {"text": "What is the most important issue influencing your vote?", "type": "open_ended"},
                {"text": "Would you recommend your candidate to friends and family?", "type": "yes_no"},
            ],
            "model": "openai/gpt-4o-mini"
        }

        # Stimulus materials
        self.stimulus_materials = {
            "concepts": [
                "The 2024 Presidential Election is approaching. You will be asked about your voting intentions.",
                "Consider the major issues: economy, healthcare, immigration, climate change, and national security.",
            ],
            "messages": [
                "Your vote matters. Consider all factors before making your decision.",
                "Think about which candidate best represents your values and priorities."
            ]
        }

        self.methodology = {
            "type": "survey",
            "confidence_level": 0.95,
            "margin_of_error": 0.03
        }

        self.validation_config = None
        self.confidence_target = 0.90


class MockProductRun:
    """Mock ProductRun model for testing."""

    def __init__(self, product_id):
        self.id = uuid4()
        self.product_id = product_id
        self.run_number = 1
        self.name = "Test Run - 100 Agents"
        self.status = "pending"
        self.progress = 0
        self.agents_total = 0
        self.agents_completed = 0
        self.agents_failed = 0
        self.tokens_used = 0
        self.estimated_cost = 0.0
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.config_snapshot = {}
        self.persona_snapshot = None


class MockAgentInteraction:
    """Mock AgentInteraction model for testing."""

    def __init__(self, run_id, agent_index, persona_summary, interaction_type, conversation, responses):
        self.id = uuid4()
        self.run_id = run_id
        self.agent_index = agent_index
        self.persona_summary = persona_summary
        self.interaction_type = interaction_type
        self.conversation = conversation
        self.responses = responses
        self.sentiment_overall = 0.5
        self.key_themes = []
        self.behavioral_signals = None
        self.coherence_score = 0.8
        self.authenticity_score = 0.85
        self.tokens_used = 0
        self.status = "completed"
        self.created_at = datetime.utcnow()
        self.completed_at = datetime.utcnow()


class MockProductResult:
    """Mock ProductResult model for testing."""

    def __init__(self, product_id, run_id, result_type):
        self.id = uuid4()
        self.product_id = product_id
        self.run_id = run_id
        self.result_type = result_type
        self.predictions = None
        self.insights = None
        self.simulation_outcomes = None
        self.statistical_analysis = None
        self.segment_analysis = None
        self.validation_results = None
        self.confidence_score = 0.0
        self.quality_metrics = None
        self.executive_summary = None
        self.key_takeaways = []
        self.recommendations = []
        self.visualizations = None
        self.created_at = datetime.utcnow()


class MockDatabase:
    """Mock database for storing test results."""

    def __init__(self):
        self.interactions = []
        self.results = []
        self.flush_count = 0
        self.commit_count = 0

    def add(self, obj):
        if isinstance(obj, MockAgentInteraction):
            self.interactions.append(obj)
        elif isinstance(obj, MockProductResult):
            self.results.append(obj)

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1

    async def execute(self, query):
        class MockResult:
            def scalars(self):
                class Scalars:
                    def all(self):
                        return []
                return Scalars()
        return MockResult()


# ============= Import Actual Services =============

try:
    from app.services.advanced_persona import (
        AdvancedPersonaGenerator,
        PersonaGenerationConfig,
        GeneratedPersona
    )
    from app.services.product_execution import (
        ProductPromptBuilder,
        ResponseParser,
        ResultAggregator
    )
    from app.services.regional_data import MultiRegionDataService
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import services: {e}")
    SERVICES_AVAILABLE = False


# ============= Test Runner =============

class SimulationTestRunner:
    """Comprehensive test runner for the simulation platform."""

    def __init__(self, agent_count: int = 100):
        self.agent_count = agent_count
        self.test_results = {
            "test_name": "2024 US Presidential Election Prediction",
            "agent_count": agent_count,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "status": "running",
            "errors": [],
            "warnings": [],
            "metrics": {},
            "personas": [],
            "interactions": [],
            "aggregated_results": None
        }

        # Initialize services
        self.mock_openrouter = MockOpenRouterService()
        self.prompt_builder = ProductPromptBuilder()
        self.response_parser = ResponseParser()
        self.result_aggregator = ResultAggregator()
        self.db = MockDatabase()

    async def run_all_tests(self):
        """Run all tests and save results."""
        logger.info("=" * 60)
        logger.info("AGENTVERSE COMPREHENSIVE SIMULATION TEST")
        logger.info("=" * 60)
        logger.info(f"Testing with {self.agent_count} agents")
        logger.info(f"Topic: 2024 US Presidential Election Prediction")
        logger.info("=" * 60)

        try:
            # Test 1: Persona Generation
            await self.test_persona_generation()

            # Test 2: Prompt Building
            await self.test_prompt_building()

            # Test 3: Response Parsing
            await self.test_response_parsing()

            # Test 4: Full Simulation Execution
            await self.test_full_simulation()

            # Test 5: Result Aggregation
            await self.test_result_aggregation()

            # Test 6: Segment Analysis
            await self.test_segment_analysis()

            # Set completion status
            self.test_results["status"] = "completed"
            self.test_results["completed_at"] = datetime.utcnow().isoformat()

            logger.info("=" * 60)
            logger.info("ALL TESTS COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            self.test_results["status"] = "failed"
            self.test_results["errors"].append(str(e))
            import traceback
            logger.error(traceback.format_exc())

        # Save test results
        await self.save_results()

        return self.test_results

    async def test_persona_generation(self):
        """Test persona generation with US census data."""
        logger.info("\n--- TEST 1: Persona Generation ---")

        if not SERVICES_AVAILABLE:
            logger.warning("Services not available, skipping persona generation test")
            self.test_results["warnings"].append("Persona generation test skipped - services not available")
            return

        try:
            # Create persona configuration
            config = PersonaGenerationConfig(
                region="us",
                topic="election",
                industry="politics",
                count=self.agent_count,
                include_psychographics=True,
                include_behavioral=True,
                include_cultural=True,
                include_topic_knowledge=True
            )

            # Generate personas
            logger.info(f"Generating {self.agent_count} personas...")
            generator = AdvancedPersonaGenerator(config)
            personas = await generator.generate_personas(self.agent_count)

            logger.info(f"✓ Generated {len(personas)} personas")

            # Validate personas
            age_distribution = {}
            gender_distribution = {}
            income_distribution = {}
            urban_rural_distribution = {}

            for persona in personas:
                # Track demographics
                age_bracket = persona.demographics.get("age_bracket", "Unknown")
                age_distribution[age_bracket] = age_distribution.get(age_bracket, 0) + 1

                gender = persona.demographics.get("gender", "Unknown")
                gender_distribution[gender] = gender_distribution.get(gender, 0) + 1

                income = persona.demographics.get("income_bracket", "Unknown")
                income_distribution[income] = income_distribution.get(income, 0) + 1

                urban_rural = persona.demographics.get("urban_rural", "Unknown")
                urban_rural_distribution[urban_rural] = urban_rural_distribution.get(urban_rural, 0) + 1

                # Store persona summary
                self.test_results["personas"].append({
                    "demographics": persona.demographics,
                    "professional": persona.professional,
                    "psychographics": {
                        "personality_type": persona.psychographics.get("personality_type"),
                        "values_primary": persona.psychographics.get("values_primary"),
                        "decision_style": persona.psychographics.get("decision_style"),
                        "innovation_adoption": persona.psychographics.get("innovation_adoption"),
                    },
                    "topic_knowledge": persona.topic_knowledge,
                    "confidence_score": persona.confidence_score
                })

            # Store distribution metrics
            self.test_results["metrics"]["persona_generation"] = {
                "total_generated": len(personas),
                "age_distribution": age_distribution,
                "gender_distribution": gender_distribution,
                "income_distribution": income_distribution,
                "urban_rural_distribution": urban_rural_distribution
            }

            logger.info(f"  Age Distribution: {age_distribution}")
            logger.info(f"  Gender Distribution: {gender_distribution}")
            logger.info(f"  Urban/Rural: {urban_rural_distribution}")

            # Validation checks
            assert len(personas) == self.agent_count, f"Expected {self.agent_count} personas, got {len(personas)}"
            assert all(p.demographics.get("age") for p in personas), "Some personas missing age"
            assert all(p.demographics.get("gender") for p in personas), "Some personas missing gender"

            logger.info("✓ Persona generation test PASSED")

        except Exception as e:
            logger.error(f"✗ Persona generation test FAILED: {str(e)}")
            self.test_results["errors"].append(f"Persona generation: {str(e)}")
            raise

    async def test_prompt_building(self):
        """Test prompt building for different product types."""
        logger.info("\n--- TEST 2: Prompt Building ---")

        try:
            # Create mock product and persona
            product = MockProduct()

            # Create a sample persona for testing
            if self.test_results["personas"]:
                persona_data = self.test_results["personas"][0]
            else:
                persona_data = {
                    "demographics": {"age": 35, "gender": "Male", "urban_rural": "Suburban"},
                    "professional": {"occupation": "Software Engineer"},
                    "psychographics": {"personality_type": "INTJ"},
                    "topic_knowledge": {"political_engagement": "Active"},
                    "confidence_score": 0.9
                }

            # Create GeneratedPersona object
            class SimplePersona:
                def __init__(self, data):
                    self.demographics = data.get("demographics", {})
                    self.professional = data.get("professional", {})
                    self.psychographics = data.get("psychographics", {})
                    self.behavioral = data.get("behavioral", {})
                    self.interests = data.get("interests", {})
                    self.topic_knowledge = data.get("topic_knowledge")
                    self.cultural_context = data.get("cultural_context")
                    self.full_prompt = self._build_prompt()
                    self.confidence_score = data.get("confidence_score", 0.85)

                def _build_prompt(self):
                    return f"""You are a {self.demographics.get('age', 35)}-year-old {self.demographics.get('gender', 'person')} living in a {self.demographics.get('urban_rural', 'urban')} area.
You work as a {self.professional.get('occupation', 'professional')}.
Your personality type is {self.psychographics.get('personality_type', 'INTJ')}."""

            persona = SimplePersona(persona_data)

            # Test predict prompt building
            predict_prompt = self.prompt_builder.build_predict_prompt(product, persona)

            assert len(predict_prompt) == 2, "Expected system and user messages"
            assert predict_prompt[0]["role"] == "system", "First message should be system"
            assert predict_prompt[1]["role"] == "user", "Second message should be user"
            assert len(predict_prompt[0]["content"]) > 100, "System prompt too short"
            assert "candidate" in predict_prompt[1]["content"].lower() or "vote" in predict_prompt[1]["content"].lower(), \
                "User prompt should mention voting"

            logger.info(f"✓ Built predict prompt ({len(predict_prompt[0]['content'])} chars system, {len(predict_prompt[1]['content'])} chars user)")

            # Test insight prompt building
            product.product_type = "insight"
            insight_prompt = self.prompt_builder.build_insight_prompt(product, persona)

            assert len(insight_prompt) == 2, "Expected system and user messages"
            logger.info(f"✓ Built insight prompt ({len(insight_prompt[0]['content'])} chars system)")

            # Test simulate prompt building
            product.product_type = "simulate"
            simulate_prompt = self.prompt_builder.build_simulate_prompt(product, persona)

            assert len(simulate_prompt) == 2, "Expected system and user messages"
            logger.info(f"✓ Built simulate prompt ({len(simulate_prompt[0]['content'])} chars system)")

            self.test_results["metrics"]["prompt_building"] = {
                "predict_system_length": len(predict_prompt[0]["content"]),
                "predict_user_length": len(predict_prompt[1]["content"]),
                "insight_system_length": len(insight_prompt[0]["content"]),
                "simulate_system_length": len(simulate_prompt[0]["content"])
            }

            logger.info("✓ Prompt building test PASSED")

        except Exception as e:
            logger.error(f"✗ Prompt building test FAILED: {str(e)}")
            self.test_results["errors"].append(f"Prompt building: {str(e)}")
            raise

    async def test_response_parsing(self):
        """Test response parsing for different response formats."""
        logger.info("\n--- TEST 3: Response Parsing ---")

        try:
            # Test predict response parsing
            predict_response = """[Q1_ANSWER]: Candidate A (Democrat)
[Q1_CONFIDENCE]: 8
[Q1_REASON]: Their economic policies align with my values.

[Q2_ANSWER]: 8
[Q2_CONFIDENCE]: 7
[Q2_REASON]: I've been following the campaign closely.

[Q3_ANSWER]: Economy
[Q3_CONFIDENCE]: 9
[Q3_REASON]: This affects my family's future directly."""

            parsed_predict = self.response_parser.parse_predict_response(predict_response)

            assert "answers" in parsed_predict, "Missing answers in parsed predict"
            assert "confidence_scores" in parsed_predict, "Missing confidence_scores"
            assert "reasoning" in parsed_predict, "Missing reasoning"
            assert "Q1" in parsed_predict["answers"], "Missing Q1 answer"

            logger.info(f"✓ Parsed predict response: {len(parsed_predict['answers'])} answers")

            # Test insight response parsing
            insight_response = """[Q1_RESPONSE]: I feel strongly about climate change policies and believe we need immediate action.
[Q1_EMOTION]: concerned
[Q1_INTENSITY]: 8

[Q2_RESPONSE]: Economic stability is crucial for my family's wellbeing.
[Q2_EMOTION]: anxious
[Q2_INTENSITY]: 7"""

            parsed_insight = self.response_parser.parse_insight_response(insight_response)

            assert "responses" in parsed_insight, "Missing responses in parsed insight"
            assert "emotions" in parsed_insight, "Missing emotions"
            assert "intensities" in parsed_insight, "Missing intensities"

            logger.info(f"✓ Parsed insight response: {len(parsed_insight['responses'])} responses")

            # Test simulate response parsing
            simulate_response = """[INITIAL_REACTION]: This is an interesting proposal that could address some key issues.
[DETAILED_THOUGHTS]: I see both potential benefits and concerns. The economic implications are significant.
[KEY_CONCERN]: Implementation timeline seems aggressive
[ENTHUSIASM_LEVEL]: 7
[LIKELIHOOD_TO_ACT]: 8
[REASONING]: The policy aligns with my values but execution will be challenging."""

            parsed_simulate = self.response_parser.parse_simulate_response(simulate_response)

            assert "initial_reaction" in parsed_simulate, "Missing initial_reaction"
            assert "enthusiasm_level" in parsed_simulate, "Missing enthusiasm_level"
            assert "likelihood_to_act" in parsed_simulate, "Missing likelihood_to_act"
            assert parsed_simulate["enthusiasm_level"] == 7, "Wrong enthusiasm level"

            logger.info(f"✓ Parsed simulate response: enthusiasm={parsed_simulate['enthusiasm_level']}, likelihood={parsed_simulate['likelihood_to_act']}")

            self.test_results["metrics"]["response_parsing"] = {
                "predict_answers_count": len(parsed_predict["answers"]),
                "insight_responses_count": len(parsed_insight["responses"]),
                "simulate_enthusiasm": parsed_simulate["enthusiasm_level"],
                "simulate_likelihood": parsed_simulate["likelihood_to_act"]
            }

            logger.info("✓ Response parsing test PASSED")

        except Exception as e:
            logger.error(f"✗ Response parsing test FAILED: {str(e)}")
            self.test_results["errors"].append(f"Response parsing: {str(e)}")
            raise

    async def test_full_simulation(self):
        """Test full simulation with 100 agents."""
        logger.info("\n--- TEST 4: Full Simulation Execution ---")

        try:
            product = MockProduct(persona_count=self.agent_count)
            run = MockProductRun(product.id)

            # Generate personas or use existing
            if not self.test_results["personas"]:
                logger.info("Generating personas for simulation...")
                if SERVICES_AVAILABLE:
                    config = PersonaGenerationConfig(
                        region="us",
                        topic="election",
                        count=self.agent_count
                    )
                    generator = AdvancedPersonaGenerator(config)
                    personas = await generator.generate_personas(self.agent_count)
                else:
                    # Create mock personas
                    personas = []
                    import random
                    for i in range(self.agent_count):
                        random.seed(i)
                        personas.append(type('Persona', (), {
                            'demographics': {
                                'age': random.randint(18, 85),
                                'gender': random.choice(['Male', 'Female']),
                                'urban_rural': random.choice(['Urban', 'Suburban', 'Rural']),
                                'income_bracket': random.choice(['low', 'middle', 'upper-middle', 'high']),
                                'age_bracket': random.choice(['18-24', '25-34', '35-44', '45-54', '55-64', '65+']),
                            },
                            'professional': {'occupation': random.choice(['Engineer', 'Teacher', 'Manager', 'Retail', 'Healthcare'])},
                            'psychographics': {'personality_type': random.choice(['INTJ', 'ENFP', 'ISTJ', 'ESFP'])},
                            'behavioral': {},
                            'interests': {},
                            'topic_knowledge': {'political_engagement': random.choice(['Active', 'Moderate', 'Low'])},
                            'cultural_context': None,
                            'full_prompt': f"You are a {random.randint(18, 85)}-year-old voter.",
                            'confidence_score': 0.85
                        })())
            else:
                # Use existing persona data
                personas = []
                for pd in self.test_results["personas"]:
                    personas.append(type('Persona', (), {
                        'demographics': pd['demographics'],
                        'professional': pd['professional'],
                        'psychographics': pd['psychographics'],
                        'behavioral': {},
                        'interests': {},
                        'topic_knowledge': pd.get('topic_knowledge'),
                        'cultural_context': None,
                        'full_prompt': f"You are a {pd['demographics'].get('age', 35)}-year-old voter.",
                        'confidence_score': pd.get('confidence_score', 0.85)
                    })())

            logger.info(f"Running simulation with {len(personas)} agents...")

            # Simulate batch processing
            all_interactions = []
            batch_size = 50
            total_tokens = 0
            total_cost = 0.0

            for batch_start in range(0, len(personas), batch_size):
                batch_end = min(batch_start + batch_size, len(personas))
                batch = personas[batch_start:batch_end]

                logger.info(f"  Processing batch {batch_start//batch_size + 1}: agents {batch_start+1}-{batch_end}")

                for i, persona in enumerate(batch):
                    agent_index = batch_start + i

                    # Build prompt
                    messages = self.prompt_builder.build_predict_prompt(product, persona)

                    # Get LLM response (mock)
                    response = await self.mock_openrouter.complete(messages=messages)

                    # Parse response
                    parsed = self.response_parser.parse_predict_response(response.content)

                    # Create interaction record
                    interaction = MockAgentInteraction(
                        run_id=run.id,
                        agent_index=agent_index,
                        persona_summary={
                            "demographics": persona.demographics,
                            "professional": persona.professional,
                            "psychographics": persona.psychographics
                        },
                        interaction_type="predict",
                        conversation=[
                            {"role": "system", "content": persona.full_prompt},
                            {"role": "user", "content": messages[-1]["content"]},
                            {"role": "agent", "content": response.content}
                        ],
                        responses=parsed
                    )
                    interaction.tokens_used = response.total_tokens

                    all_interactions.append(interaction)
                    self.db.add(interaction)

                    total_tokens += response.total_tokens
                    total_cost += response.cost_usd

                # Progress update
                progress = int((batch_end / len(personas)) * 100)
                logger.info(f"    Progress: {progress}% ({batch_end}/{len(personas)} agents)")

            # Update run stats
            run.agents_total = len(personas)
            run.agents_completed = len(all_interactions)
            run.tokens_used = total_tokens
            run.estimated_cost = total_cost
            run.status = "completed"

            # Store interactions for later analysis
            self.test_results["interactions"] = [
                {
                    "agent_index": i.agent_index,
                    "persona_summary": i.persona_summary,
                    "responses": i.responses,
                    "tokens_used": i.tokens_used
                }
                for i in all_interactions
            ]

            self.test_results["metrics"]["simulation"] = {
                "agents_total": len(personas),
                "agents_completed": len(all_interactions),
                "total_tokens": total_tokens,
                "estimated_cost_usd": round(total_cost, 4),
                "avg_tokens_per_agent": total_tokens // len(personas) if personas else 0,
                "success_rate": len(all_interactions) / len(personas) if personas else 0
            }

            logger.info(f"✓ Simulation completed: {len(all_interactions)} agents, {total_tokens} tokens, ${total_cost:.4f}")
            logger.info("✓ Full simulation test PASSED")

            # Store interactions for aggregation test
            self._interactions = all_interactions
            self._product = product

        except Exception as e:
            logger.error(f"✗ Full simulation test FAILED: {str(e)}")
            self.test_results["errors"].append(f"Full simulation: {str(e)}")
            raise

    async def test_result_aggregation(self):
        """Test result aggregation from agent interactions."""
        logger.info("\n--- TEST 5: Result Aggregation ---")

        try:
            if not hasattr(self, '_interactions') or not self._interactions:
                logger.warning("No interactions available, creating mock data")
                self._interactions = []
                self._product = MockProduct()

            # Aggregate predict results
            aggregated = self.result_aggregator.aggregate_predict_results(
                self._interactions,
                self._product
            )

            assert "predictions" in aggregated, "Missing predictions"
            assert "statistical_analysis" in aggregated, "Missing statistical_analysis"

            predictions = aggregated["predictions"]
            assert "primary_prediction" in predictions, "Missing primary_prediction"
            assert "response_distribution" in predictions, "Missing response_distribution"

            primary = predictions["primary_prediction"]
            assert "outcome" in primary, "Missing outcome"
            assert "value" in primary, "Missing value"
            assert "confidence_interval" in primary, "Missing confidence_interval"

            logger.info(f"✓ Primary prediction: {primary['outcome']} ({primary['value']:.1%})")
            logger.info(f"  95% CI: [{primary['confidence_interval'][0]:.1%}, {primary['confidence_interval'][1]:.1%}]")
            logger.info(f"  Response distribution: {predictions['response_distribution']}")

            stats = aggregated["statistical_analysis"]
            logger.info(f"  Sample size: {stats['sample_size']}")
            logger.info(f"  Margin of error: {stats['margin_of_error']:.1%}")
            logger.info(f"  Confidence score: {aggregated['confidence_score']:.1%}")

            self.test_results["aggregated_results"] = {
                "predictions": predictions,
                "statistical_analysis": stats,
                "confidence_score": aggregated["confidence_score"]
            }

            self.test_results["metrics"]["aggregation"] = {
                "primary_outcome": primary["outcome"],
                "primary_value": primary["value"],
                "confidence_interval": primary["confidence_interval"],
                "sample_size": stats["sample_size"],
                "margin_of_error": stats["margin_of_error"],
                "confidence_score": aggregated["confidence_score"]
            }

            logger.info("✓ Result aggregation test PASSED")

        except Exception as e:
            logger.error(f"✗ Result aggregation test FAILED: {str(e)}")
            self.test_results["errors"].append(f"Result aggregation: {str(e)}")
            raise

    async def test_segment_analysis(self):
        """Test segment-level analysis."""
        logger.info("\n--- TEST 6: Segment Analysis ---")

        try:
            if not hasattr(self, '_interactions') or not self._interactions:
                logger.warning("No interactions available, skipping segment analysis")
                return

            # Calculate segment analysis
            segment_analysis = self.result_aggregator.calculate_segment_analysis(
                self._interactions,
                self._product
            )

            assert "by_age" in segment_analysis, "Missing age segments"
            assert "by_income" in segment_analysis, "Missing income segments"
            assert "by_gender" in segment_analysis, "Missing gender segments"

            logger.info(f"✓ Age segments: {list(segment_analysis['by_age'].keys())}")
            logger.info(f"✓ Income segments: {list(segment_analysis['by_income'].keys())}")
            logger.info(f"✓ Gender segments: {list(segment_analysis['by_gender'].keys())}")

            # Log segment details
            for age_group, data in segment_analysis["by_age"].items():
                logger.info(f"  Age {age_group}: {data}")

            self.test_results["metrics"]["segment_analysis"] = segment_analysis

            logger.info("✓ Segment analysis test PASSED")

        except Exception as e:
            logger.error(f"✗ Segment analysis test FAILED: {str(e)}")
            self.test_results["errors"].append(f"Segment analysis: {str(e)}")
            raise

    async def save_results(self):
        """Save test results to files."""
        logger.info("\n--- Saving Test Results ---")

        # Create results directory
        results_dir = Path(__file__).parent / "test_results"
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save full results as JSON
        results_file = results_dir / f"simulation_test_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        logger.info(f"✓ Full results saved to: {results_file}")

        # Save summary report
        summary_file = results_dir / f"simulation_summary_{timestamp}.md"
        with open(summary_file, 'w') as f:
            f.write(self._generate_summary_report())
        logger.info(f"✓ Summary report saved to: {summary_file}")

        # Save personas data
        if self.test_results["personas"]:
            personas_file = results_dir / f"personas_{timestamp}.json"
            with open(personas_file, 'w') as f:
                json.dump(self.test_results["personas"], f, indent=2)
            logger.info(f"✓ Personas data saved to: {personas_file}")

        # Save interactions data
        if self.test_results["interactions"]:
            interactions_file = results_dir / f"interactions_{timestamp}.json"
            with open(interactions_file, 'w') as f:
                json.dump(self.test_results["interactions"], f, indent=2)
            logger.info(f"✓ Interactions data saved to: {interactions_file}")

    def _generate_summary_report(self) -> str:
        """Generate markdown summary report."""
        metrics = self.test_results["metrics"]

        report = f"""# AgentVerse Simulation Test Report

**Test Name:** {self.test_results['test_name']}
**Agent Count:** {self.test_results['agent_count']}
**Started:** {self.test_results['started_at']}
**Completed:** {self.test_results['completed_at']}
**Status:** {self.test_results['status']}

---

## Executive Summary

"""

        if self.test_results.get("aggregated_results"):
            results = self.test_results["aggregated_results"]
            predictions = results.get("predictions", {})
            primary = predictions.get("primary_prediction", {})
            stats = results.get("statistical_analysis", {})

            report += f"""### Primary Prediction
- **Outcome:** {primary.get('outcome', 'N/A')}
- **Value:** {primary.get('value', 0):.1%}
- **95% Confidence Interval:** [{primary.get('confidence_interval', [0,0])[0]:.1%}, {primary.get('confidence_interval', [0,0])[1]:.1%}]

### Statistical Analysis
- **Sample Size:** {stats.get('sample_size', 0)}
- **Margin of Error:** {stats.get('margin_of_error', 0):.1%}
- **Confidence Score:** {results.get('confidence_score', 0):.1%}

### Response Distribution
"""
            for answer, percentage in predictions.get("response_distribution", {}).items():
                report += f"- {answer}: {percentage:.1%}\n"

        report += """
---

## Test Metrics

### Persona Generation
"""
        if "persona_generation" in metrics:
            pg = metrics["persona_generation"]
            report += f"- Total Generated: {pg.get('total_generated', 0)}\n"
            report += f"- Age Distribution: {pg.get('age_distribution', {})}\n"
            report += f"- Gender Distribution: {pg.get('gender_distribution', {})}\n"
            report += f"- Urban/Rural: {pg.get('urban_rural_distribution', {})}\n"

        report += """
### Simulation Execution
"""
        if "simulation" in metrics:
            sim = metrics["simulation"]
            report += f"- Agents Completed: {sim.get('agents_completed', 0)}/{sim.get('agents_total', 0)}\n"
            report += f"- Success Rate: {sim.get('success_rate', 0):.1%}\n"
            report += f"- Total Tokens: {sim.get('total_tokens', 0):,}\n"
            report += f"- Avg Tokens/Agent: {sim.get('avg_tokens_per_agent', 0)}\n"
            report += f"- Estimated Cost: ${sim.get('estimated_cost_usd', 0):.4f}\n"

        report += """
### Segment Analysis
"""
        if "segment_analysis" in metrics:
            seg = metrics["segment_analysis"]
            report += f"- Age Segments: {list(seg.get('by_age', {}).keys())}\n"
            report += f"- Income Segments: {list(seg.get('by_income', {}).keys())}\n"
            report += f"- Gender Segments: {list(seg.get('by_gender', {}).keys())}\n"

        if self.test_results["errors"]:
            report += f"""
---

## Errors
"""
            for error in self.test_results["errors"]:
                report += f"- {error}\n"

        if self.test_results["warnings"]:
            report += f"""
---

## Warnings
"""
            for warning in self.test_results["warnings"]:
                report += f"- {warning}\n"

        report += """
---

*Generated by AgentVerse Test Suite*
"""

        return report


# ============= Main Entry Point =============

async def main():
    """Run comprehensive simulation test."""
    runner = SimulationTestRunner(agent_count=100)
    results = await runner.run_all_tests()

    # Print final summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Errors: {len(results['errors'])}")
    print(f"Warnings: {len(results['warnings'])}")

    if results.get("metrics", {}).get("simulation"):
        sim = results["metrics"]["simulation"]
        print(f"Agents Completed: {sim.get('agents_completed', 0)}/{sim.get('agents_total', 0)}")

    if results.get("aggregated_results"):
        primary = results["aggregated_results"]["predictions"]["primary_prediction"]
        print(f"Primary Prediction: {primary['outcome']} ({primary['value']:.1%})")

    print("=" * 60)

    return results


if __name__ == "__main__":
    asyncio.run(main())
