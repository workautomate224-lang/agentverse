"""
Simulation Execution Service
Core engine for running AI agent simulations.
Supports both random and census-based persona generation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.simulation import AgentResponse, Scenario, SimulationRun
from app.services.openrouter import CompletionResponse, OpenRouterService
from app.services.persona import (
    Persona,
    PersonaGenerator,
    CensusBasedPersonaGenerator,
    get_persona_generator,
)


logger = logging.getLogger(__name__)


class SimulationResult:
    """Result from a single agent simulation."""
    def __init__(
        self,
        persona: Persona,
        response: dict[str, Any],
        reasoning: Optional[str],
        completion: CompletionResponse,
    ):
        self.persona = persona
        self.response = response
        self.reasoning = reasoning
        self.completion = completion


class SimulationService:
    """Service for executing AI agent simulations."""

    def __init__(
        self,
        openrouter: Optional[OpenRouterService] = None,
        persona_generator: Optional[Union[PersonaGenerator, CensusBasedPersonaGenerator]] = None,
        use_census_data: bool = True,
        regional_profile: Optional[dict] = None,
    ):
        self.openrouter = openrouter or OpenRouterService()

        # Use census-based persona generation by default if enabled in settings
        if persona_generator:
            self.persona_generator = persona_generator
        else:
            use_census = use_census_data and settings.USE_REAL_CENSUS_DATA
            self.persona_generator = get_persona_generator(
                use_census_data=use_census,
                regional_profile=regional_profile,
            )
            if use_census:
                logger.info("Using census-based persona generation for real demographic accuracy")

    async def run_simulation(
        self,
        scenario: Scenario,
        simulation_run: SimulationRun,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ) -> dict[str, Any]:
        """
        Execute a complete simulation.

        Args:
            scenario: The scenario configuration
            simulation_run: The simulation run record
            db: Database session
            progress_callback: Optional callback for progress updates

        Returns:
            Aggregated results summary
        """
        # Update status to running
        simulation_run.status = "running"
        simulation_run.started_at = datetime.utcnow()
        await db.flush()

        try:
            # Generate personas
            personas = self.persona_generator.generate_population(
                count=simulation_run.agent_count,
                custom_distribution=scenario.demographics,
            )

            # Process in batches
            batch_size = 50
            all_results = []
            total_tokens = 0
            total_cost = 0.0

            for batch_start in range(0, len(personas), batch_size):
                batch_end = min(batch_start + batch_size, len(personas))
                batch = personas[batch_start:batch_end]

                # Process batch
                batch_results = await self._process_batch(
                    batch=batch,
                    scenario=scenario,
                    model=simulation_run.model_used,
                )

                # Save responses to database
                for result in batch_results:
                    agent_response = AgentResponse(
                        run_id=simulation_run.id,
                        agent_index=result.persona.index,
                        persona={
                            "demographics": result.persona.demographics,
                            "psychographics": result.persona.psychographics,
                        },
                        question_id=scenario.questions[0].get("id") if scenario.questions else None,
                        response=result.response,
                        reasoning=result.reasoning,
                        tokens_used=result.completion.total_tokens,
                        response_time_ms=result.completion.response_time_ms,
                        model_used=result.completion.model,
                    )
                    db.add(agent_response)
                    all_results.append(result)
                    total_tokens += result.completion.total_tokens
                    total_cost += result.completion.cost_usd

                # Update progress
                progress = int((batch_end / len(personas)) * 100)
                simulation_run.progress = progress
                simulation_run.tokens_used = total_tokens
                simulation_run.cost_usd = total_cost
                await db.flush()

                if progress_callback:
                    await progress_callback(progress, batch_end, len(personas))

            # Calculate results summary
            results_summary = self._aggregate_results(all_results, scenario)

            # Update simulation run
            simulation_run.status = "completed"
            simulation_run.progress = 100
            simulation_run.completed_at = datetime.utcnow()
            simulation_run.results_summary = results_summary
            simulation_run.confidence_score = results_summary.get("confidence_score", 0.0)
            simulation_run.tokens_used = total_tokens
            simulation_run.cost_usd = total_cost

            # Update scenario status
            scenario.status = "completed"

            await db.flush()

            return results_summary

        except Exception as e:
            simulation_run.status = "failed"
            simulation_run.completed_at = datetime.utcnow()
            scenario.status = "ready"
            await db.flush()
            raise e

    async def _process_batch(
        self,
        batch: list[Persona],
        scenario: Scenario,
        model: Optional[str] = None,
    ) -> list[SimulationResult]:
        """Process a batch of personas."""
        requests = []

        for persona in batch:
            prompt = self._build_agent_prompt(persona, scenario)
            requests.append({
                "messages": [
                    {"role": "system", "content": persona.full_prompt},
                    {"role": "user", "content": prompt},
                ],
                "model": model,
                "temperature": 0.7,
                "max_tokens": 500,
            })

        completions = await self.openrouter.batch_complete(requests, concurrency=10)

        results = []
        for persona, completion in zip(batch, completions):
            response, reasoning = self._parse_response(completion.content, scenario)
            results.append(SimulationResult(
                persona=persona,
                response=response,
                reasoning=reasoning,
                completion=completion,
            ))

        return results

    def _build_agent_prompt(self, persona: Persona, scenario: Scenario) -> str:
        """Build the prompt for an agent to respond to."""
        prompt_parts = [
            "SCENARIO:",
            scenario.context,
            "",
        ]

        # Add questions
        for i, question in enumerate(scenario.questions, 1):
            q_type = question.get("type", "open_ended")
            q_text = question.get("text", "")

            prompt_parts.append(f"QUESTION {i}: {q_text}")

            if q_type == "multiple_choice":
                options = question.get("options", [])
                for j, opt in enumerate(options, 1):
                    prompt_parts.append(f"  {j}. {opt}")
            elif q_type == "yes_no":
                prompt_parts.append("  Options: Yes / No")
            elif q_type == "scale":
                scale_min = question.get("scale_min", 1)
                scale_max = question.get("scale_max", 10)
                prompt_parts.append(f"  Scale: {scale_min} to {scale_max}")

            prompt_parts.append("")

        prompt_parts.extend([
            "INSTRUCTIONS:",
            "Respond as your persona would. For each question:",
            "1. State your choice clearly",
            "2. Briefly explain your reasoning (1-2 sentences)",
            "",
            "Format your response as:",
            "[ANSWER]: Your choice",
            "[REASON]: Brief explanation",
        ])

        return "\n".join(prompt_parts)

    def _parse_response(
        self,
        content: str,
        scenario: Scenario,
    ) -> tuple[dict[str, Any], Optional[str]]:
        """Parse the LLM response into structured data."""
        response = {"raw": content}
        reasoning = None

        # Try to extract answer and reason
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("[ANSWER]:") or line.startswith("ANSWER:"):
                response["answer"] = line.split(":", 1)[1].strip()
            elif line.startswith("[REASON]:") or line.startswith("REASON:"):
                reasoning = line.split(":", 1)[1].strip()

        # If no structured answer found, use first line
        if "answer" not in response and lines:
            response["answer"] = lines[0].strip()

        return response, reasoning

    def _aggregate_results(
        self,
        results: list[SimulationResult],
        scenario: Scenario,
    ) -> dict[str, Any]:
        """Aggregate individual results into summary statistics."""
        total = len(results)

        # Count responses
        response_counts: dict[str, int] = {}
        for result in results:
            answer = result.response.get("answer", "Unknown")
            # Normalize the answer
            answer_lower = answer.lower().strip()
            if answer_lower in response_counts:
                response_counts[answer_lower] += 1
            else:
                response_counts[answer_lower] = 1

        # Calculate percentages
        response_percentages = {
            answer: (count / total) * 100
            for answer, count in response_counts.items()
        }

        # Calculate demographics breakdown
        demographics_breakdown = self._calculate_demographics_breakdown(results)

        # Confidence score based on response distribution
        max_percentage = max(response_percentages.values()) if response_percentages else 0
        confidence_score = min(0.95, max_percentage / 100 + 0.2)

        return {
            "total_agents": total,
            "response_distribution": response_counts,
            "response_percentages": response_percentages,
            "demographics_breakdown": demographics_breakdown,
            "confidence_score": round(confidence_score, 3),
            "top_response": max(response_counts, key=response_counts.get) if response_counts else None,
        }

    def _calculate_demographics_breakdown(
        self,
        results: list[SimulationResult],
    ) -> dict[str, dict[str, dict[str, int]]]:
        """Calculate response breakdown by demographics."""
        breakdown: dict[str, dict[str, dict[str, int]]] = {}

        demographic_fields = ["age", "gender", "income_bracket", "education"]

        for field in demographic_fields:
            breakdown[field] = {}

            for result in results:
                value = result.persona.demographics.get(field)
                answer = result.response.get("answer", "Unknown").lower().strip()

                # Handle age ranges
                if field == "age":
                    age = value
                    if age < 25:
                        value = "18-24"
                    elif age < 35:
                        value = "25-34"
                    elif age < 45:
                        value = "35-44"
                    elif age < 55:
                        value = "45-54"
                    else:
                        value = "55+"

                if value not in breakdown[field]:
                    breakdown[field][value] = {}

                if answer not in breakdown[field][value]:
                    breakdown[field][value][answer] = 0

                breakdown[field][value][answer] += 1

        return breakdown

    async def stream_simulation(
        self,
        scenario: Scenario,
        simulation_run: SimulationRun,
        db: AsyncSession,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream simulation results as they complete.

        Yields progress updates and individual agent responses.
        """
        simulation_run.status = "running"
        simulation_run.started_at = datetime.utcnow()
        await db.flush()

        personas = self.persona_generator.generate_population(
            count=simulation_run.agent_count,
            custom_distribution=scenario.demographics,
        )

        total_tokens = 0
        total_cost = 0.0

        for i, persona in enumerate(personas):
            prompt = self._build_agent_prompt(persona, scenario)

            try:
                completion = await self.openrouter.complete(
                    messages=[
                        {"role": "system", "content": persona.full_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    model=simulation_run.model_used,
                )

                response, reasoning = self._parse_response(completion.content, scenario)
                total_tokens += completion.total_tokens
                total_cost += completion.cost_usd

                # Save to database
                agent_response = AgentResponse(
                    run_id=simulation_run.id,
                    agent_index=i,
                    persona={
                        "demographics": persona.demographics,
                        "psychographics": persona.psychographics,
                    },
                    response=response,
                    reasoning=reasoning,
                    tokens_used=completion.total_tokens,
                    response_time_ms=completion.response_time_ms,
                    model_used=completion.model,
                )
                db.add(agent_response)

                # Yield result
                yield {
                    "type": "agent_response",
                    "index": i,
                    "total": len(personas),
                    "progress": int((i + 1) / len(personas) * 100),
                    "persona": persona.demographics,
                    "response": response,
                    "reasoning": reasoning,
                }

            except Exception as e:
                yield {
                    "type": "error",
                    "index": i,
                    "error": str(e),
                }

            # Update progress periodically
            if (i + 1) % 10 == 0:
                simulation_run.progress = int((i + 1) / len(personas) * 100)
                simulation_run.tokens_used = total_tokens
                simulation_run.cost_usd = total_cost
                await db.flush()

        # Final update
        simulation_run.status = "completed"
        simulation_run.progress = 100
        simulation_run.completed_at = datetime.utcnow()
        scenario.status = "completed"
        await db.flush()

        yield {
            "type": "complete",
            "total_agents": len(personas),
            "tokens_used": total_tokens,
            "cost_usd": total_cost,
        }
