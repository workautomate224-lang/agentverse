"""
Test configuration and fixtures for AgentVerse API tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.main import app
from app.core.config import settings
from app.db.session import get_db, Base

# Use the same database for testing
TEST_DATABASE_URL = settings.DATABASE_URL


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Get authentication headers for a test user."""
    # Register a test user
    register_data = {
        "email": f"test_user_{asyncio.get_event_loop().time()}@test.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "company": "Test Company"
    }

    register_response = await client.post("/api/v1/auth/register", json=register_data)

    if register_response.status_code != 201:
        # User might already exist, try login
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

        # Create with fixed test email
        register_data["email"] = "test@example.com"
        register_response = await client.post("/api/v1/auth/register", json=register_data)

    # Login to get token
    login_response = await client.post("/api/v1/auth/login", json={
        "email": register_data["email"],
        "password": register_data["password"]
    })

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return {}


@pytest.fixture
def sample_project_data():
    """Sample project data for tests."""
    return {
        "name": "Test AI Project",
        "description": "A comprehensive test project for AI simulations",
        "domain": "technology",
        "settings": {"advanced_mode": True}
    }


@pytest.fixture
def sample_scenario_data():
    """Sample scenario data for tests."""
    return {
        "name": "Electric Vehicle Adoption Survey",
        "description": "Comprehensive survey on EV adoption intentions",
        "scenario_type": "survey",
        "context": """You are participating in a research study about electric vehicle adoption.
        The year is 2026 and EV technology has advanced significantly. Consider your personal
        financial situation, environmental concerns, and practical needs when responding.""",
        "questions": [
            {
                "id": "q1",
                "text": "How likely are you to purchase an electric vehicle in the next 2 years?",
                "type": "scale",
                "scale_min": 1,
                "scale_max": 10,
                "required": True
            },
            {
                "id": "q2",
                "text": "What is your primary concern about electric vehicles?",
                "type": "multiple_choice",
                "options": ["Range anxiety", "Charging infrastructure", "Purchase cost", "Battery life", "Resale value"],
                "required": True
            },
            {
                "id": "q3",
                "text": "What features would make you more likely to buy an EV?",
                "type": "open_ended",
                "required": True
            }
        ],
        "variables": {
            "year": 2026,
            "market_segment": "consumer"
        },
        "population_size": 100,
        "demographics": {
            "age_distribution": {"18-24": 0.15, "25-34": 0.25, "35-44": 0.25, "45-54": 0.20, "55+": 0.15},
            "gender_distribution": {"male": 0.48, "female": 0.50, "other": 0.02},
            "income_distribution": {"low": 0.25, "middle": 0.50, "high": 0.25}
        }
    }


@pytest.fixture
def sample_persona_template_data():
    """Sample persona template data for tests."""
    return {
        "name": "US Tech Consumers 2026",
        "description": "Technology-savvy consumers in the United States for product testing",
        "region": "us",
        "country": "United States",
        "industry": "Technology",
        "topic": "Electric Vehicles",
        "keywords": ["EV", "sustainable", "tech-savvy", "early adopter"],
        "source_type": "ai_generated"
    }


@pytest.fixture
def sample_generate_personas_request():
    """Sample generate personas request for tests."""
    return {
        "region": "us",
        "topic": "Electric Vehicle Adoption",
        "industry": "Automotive",
        "keywords": ["sustainability", "technology", "transportation"],
        "count": 10,
        "include_psychographics": True,
        "include_behavioral": True,
        "include_cultural": True,
        "include_topic_knowledge": True
    }


@pytest.fixture
def sample_ai_research_request():
    """Sample AI research request for tests."""
    return {
        "topic": "Cryptocurrency Investment Behavior",
        "region": "us",
        "industry": "Finance",
        "keywords": ["bitcoin", "blockchain", "digital assets", "investment"],
        "research_depth": "standard",
        "target_persona_count": 50
    }
