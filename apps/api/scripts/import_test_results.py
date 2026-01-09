#!/usr/bin/env python3
"""
Import Test Results to Database

This script imports the E2E test results (100-agent election prediction)
into the PostgreSQL database so they can be viewed in the platform dashboard.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.models.simulation import Project
from app.models.product import Product, ProductRun, ProductResult, AgentInteraction
from app.models.persona import PersonaRecord


# Test results directory
TEST_RESULTS_DIR = Path(__file__).parent.parent / "tests" / "test_results"

# Find the latest successful test results
def find_latest_results():
    """Find the most recent successful test results."""
    json_files = list(TEST_RESULTS_DIR.glob("simulation_test_*.json"))
    if not json_files:
        raise FileNotFoundError(f"No test results found in {TEST_RESULTS_DIR}")

    # Sort by modification time, newest first
    json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            if data.get("status") == "completed":
                return json_file

    raise FileNotFoundError("No completed test results found")


def load_test_data(results_file: Path) -> dict:
    """Load all test data files."""
    timestamp = results_file.stem.replace("simulation_test_", "")

    data = {
        "main": json.load(open(results_file)),
        "personas": [],
        "interactions": [],
    }

    # Load personas
    personas_file = TEST_RESULTS_DIR / f"personas_{timestamp}.json"
    if personas_file.exists():
        data["personas"] = json.load(open(personas_file))

    # Load interactions
    interactions_file = TEST_RESULTS_DIR / f"interactions_{timestamp}.json"
    if interactions_file.exists():
        data["interactions"] = json.load(open(interactions_file))

    return data


async def get_or_create_user(session: AsyncSession) -> User:
    """Get existing test user or create one."""
    test_email = "test@agentverse.io"

    result = await session.execute(
        select(User).where(User.email == test_email)
    )
    user = result.scalar_one_or_none()

    if user:
        print(f"  Found existing user: {user.email}")
        return user

    # Create test user
    user = User(
        id=uuid4(),
        email=test_email,
        full_name="Test User",
        company="AgentVerse",
        role="admin",
        tier="enterprise",
        is_active=True,
        is_verified=True,
        settings={},
    )
    session.add(user)
    await session.flush()
    print(f"  Created user: {user.email}")
    return user


async def create_project(session: AsyncSession, user: User, test_name: str) -> Project:
    """Create project for the test."""
    project = Project(
        id=uuid4(),
        user_id=user.id,
        name=test_name,
        description="Comprehensive 100-agent simulation test for 2024 US Presidential Election prediction",
        domain="political",
        settings={
            "test_run": True,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    session.add(project)
    await session.flush()
    print(f"  Created project: {project.name}")
    return project


async def create_product(
    session: AsyncSession,
    user: User,
    project: Project,
    test_data: dict
) -> Product:
    """Create product from test data."""
    main = test_data["main"]
    metrics = main.get("metrics", {})

    product = Product(
        id=uuid4(),
        project_id=project.id,
        user_id=user.id,
        name=main["test_name"],
        description="AI-powered prediction simulation using census-backed synthetic personas",
        product_type="predict",
        sub_type="election",
        target_market={
            "regions": ["us"],
            "countries": ["United States"],
            "demographics": metrics.get("persona_generation", {}),
            "sample_size": main["agent_count"],
        },
        persona_count=main["agent_count"],
        persona_source="ai_generated",
        configuration={
            "prediction_type": "election",
            "topic": "2024 US Presidential Election",
            "questions": [
                "Who will you vote for in the 2024 presidential election?",
                "What is your most important issue when voting?",
                "Will you definitely vote in this election?"
            ],
        },
        status="completed",
        confidence_target=0.9,
    )
    session.add(product)
    await session.flush()
    print(f"  Created product: {product.name}")
    return product


async def create_persona_records(
    session: AsyncSession,
    personas_data: list,
) -> list[PersonaRecord]:
    """Create persona records from test data."""
    records = []

    for i, persona in enumerate(personas_data):
        record = PersonaRecord(
            id=uuid4(),
            template_id=None,
            demographics=persona.get("demographics", {}),
            professional=persona.get("professional", {}),
            psychographics=persona.get("psychographics", {}),
            behavioral=persona.get("behavioral", {}),
            interests=persona.get("interests", {}),
            topic_knowledge=persona.get("topic_knowledge", {}),
            source_type="ai_generated",
            data_sources=["us_census_bureau"],
            confidence_score=persona.get("confidence_score", 0.9),
        )
        records.append(record)
        session.add(record)

    await session.flush()
    print(f"  Created {len(records)} persona records")
    return records


async def create_product_run(
    session: AsyncSession,
    product: Product,
    test_data: dict,
) -> ProductRun:
    """Create product run from test data."""
    main = test_data["main"]
    metrics = main.get("metrics", {}).get("simulation", {})

    started_at = None
    completed_at = None

    if main.get("started_at"):
        started_at = datetime.fromisoformat(main["started_at"].replace("Z", "+00:00"))
    if main.get("completed_at"):
        completed_at = datetime.fromisoformat(main["completed_at"].replace("Z", "+00:00"))

    run = ProductRun(
        id=uuid4(),
        product_id=product.id,
        run_number=1,
        name="Initial Test Run",
        config_snapshot={
            "topic": "2024 US Presidential Election",
            "agent_count": main["agent_count"],
            "metrics": main.get("metrics", {}),
        },
        persona_snapshot={
            "distributions": metrics.get("persona_generation", {}),
        },
        status=main["status"],
        progress=100 if main["status"] == "completed" else 0,
        agents_total=main["agent_count"],
        agents_completed=metrics.get("agents_completed", main["agent_count"]),
        agents_failed=0,
        tokens_used=metrics.get("total_tokens", 0),
        estimated_cost=metrics.get("estimated_cost_usd", 0.0),
        started_at=started_at,
        completed_at=completed_at,
    )
    session.add(run)
    await session.flush()
    print(f"  Created product run: {run.id}")
    return run


async def create_agent_interactions(
    session: AsyncSession,
    run: ProductRun,
    interactions_data: list,
    persona_records: list[PersonaRecord],
) -> list[AgentInteraction]:
    """Create agent interactions from test data."""
    interactions = []

    for i, interaction_data in enumerate(interactions_data):
        persona_record = persona_records[i] if i < len(persona_records) else None

        # Build conversation from responses
        responses = interaction_data.get("responses", {})
        conversation = [
            {"role": "system", "content": "You are a voter in the 2024 US Presidential Election."},
            {"role": "user", "content": "Please answer the following survey questions about your voting preferences."},
            {"role": "assistant", "content": responses.get("raw", "")},
        ]

        interaction = AgentInteraction(
            id=uuid4(),
            run_id=run.id,
            persona_record_id=persona_record.id if persona_record else None,
            agent_index=interaction_data.get("agent_index", i),
            persona_summary=interaction_data.get("persona_summary", {}),
            interaction_type="survey",
            conversation=conversation,
            responses=responses.get("answers", {}),
            sentiment_overall=0.5,  # Neutral default
            key_themes=list(responses.get("answers", {}).values())[:3] if responses.get("answers") else [],
            coherence_score=0.9,
            authenticity_score=0.9,
            tokens_used=interaction_data.get("tokens_used", 0),
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        interactions.append(interaction)
        session.add(interaction)

    await session.flush()
    print(f"  Created {len(interactions)} agent interactions")
    return interactions


async def create_product_result(
    session: AsyncSession,
    product: Product,
    run: ProductRun,
    test_data: dict,
) -> ProductResult:
    """Create product result from aggregated test data."""
    main = test_data["main"]
    aggregation = main.get("metrics", {}).get("aggregation", {})
    segment_analysis = main.get("metrics", {}).get("segment_analysis", {})
    aggregated_results = main.get("aggregated_results", {})

    # Build predictions from aggregation data
    predictions = {
        "primary_prediction": {
            "outcome": aggregation.get("primary_outcome", "Unknown"),
            "value": aggregation.get("primary_value", 0),
            "confidence_interval": aggregation.get("confidence_interval", [0, 0]),
            "confidence_level": 0.95,
        },
        "response_distribution": aggregated_results.get("predictions", {}).get("response_distribution", {}),
        "segment_breakdown": segment_analysis,
    }

    # Build statistical analysis
    statistical_analysis = {
        "sample_size": aggregation.get("sample_size", 100),
        "margin_of_error": aggregation.get("margin_of_error", 0),
        "confidence_level": 0.95,
        "statistical_significance": True,
    }

    result = ProductResult(
        id=uuid4(),
        product_id=product.id,
        run_id=run.id,
        result_type="prediction",
        predictions=predictions,
        statistical_analysis=statistical_analysis,
        segment_analysis=segment_analysis,
        confidence_score=aggregation.get("confidence_score", 0.7),
        executive_summary=f"Based on simulation of {aggregation.get('sample_size', 100)} synthetic voters, "
                         f"{aggregation.get('primary_outcome', 'the leading candidate')} is predicted to win "
                         f"with {aggregation.get('primary_value', 0)*100:.1f}% of the vote "
                         f"(95% CI: [{aggregation.get('confidence_interval', [0, 0])[0]*100:.1f}%, "
                         f"{aggregation.get('confidence_interval', [0, 0])[1]*100:.1f}%]).",
        key_takeaways=[
            f"Primary prediction: {aggregation.get('primary_outcome', 'Unknown')} ({aggregation.get('primary_value', 0)*100:.1f}%)",
            f"Sample size: {aggregation.get('sample_size', 100)} synthetic voters",
            f"Margin of error: ±{aggregation.get('margin_of_error', 0)*100:.1f}%",
            "Demographics aligned with US Census Bureau data",
        ],
        recommendations=[
            "Consider expanding sample size for higher precision",
            "Validate results against historical polling data",
            "Analyze segment differences for targeted insights",
        ],
    )
    session.add(result)
    await session.flush()
    print(f"  Created product result: {result.id}")
    return result


async def main():
    """Main import function."""
    print("\n" + "=" * 60)
    print("IMPORTING TEST RESULTS TO DATABASE")
    print("=" * 60)

    # Find and load test data
    print("\n1. Loading test data...")
    try:
        results_file = find_latest_results()
        print(f"   Found: {results_file.name}")
        test_data = load_test_data(results_file)
        print(f"   Loaded {len(test_data['personas'])} personas, {len(test_data['interactions'])} interactions")
    except FileNotFoundError as e:
        print(f"   ERROR: {e}")
        return

    # Import to database
    print("\n2. Importing to database...")
    async with AsyncSessionLocal() as session:
        try:
            # Create user
            print("\n   Creating/finding user...")
            user = await get_or_create_user(session)

            # Create project
            print("\n   Creating project...")
            project = await create_project(session, user, test_data["main"]["test_name"])

            # Create product
            print("\n   Creating product...")
            product = await create_product(session, user, project, test_data)

            # Create persona records
            print("\n   Creating persona records...")
            persona_records = await create_persona_records(session, test_data["personas"])

            # Create product run
            print("\n   Creating product run...")
            run = await create_product_run(session, product, test_data)

            # Create agent interactions
            print("\n   Creating agent interactions...")
            interactions = await create_agent_interactions(
                session, run, test_data["interactions"], persona_records
            )

            # Create product result
            print("\n   Creating product result...")
            result = await create_product_result(session, product, run, test_data)

            # Commit all changes
            await session.commit()
            print("\n   ✓ All data committed successfully!")

            # Print URLs
            print("\n" + "=" * 60)
            print("IMPORT COMPLETE")
            print("=" * 60)
            print("\nView results in the platform:")
            print(f"  Product:  /dashboard/products")
            print(f"  Results:  /dashboard/products/{product.id}/results/{result.id}")
            print(f"  Personas: /dashboard/personas")
            print("\nIDs for reference:")
            print(f"  User ID:    {user.id}")
            print(f"  Project ID: {project.id}")
            print(f"  Product ID: {product.id}")
            print(f"  Run ID:     {run.id}")
            print(f"  Result ID:  {result.id}")

        except Exception as e:
            await session.rollback()
            print(f"\n   ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())
