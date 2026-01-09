"""
Integration Tests for AgentVerse API.

Tests against the running API server at localhost:8000.
Run the server first: uvicorn app.main:app --reload
"""

import httpx
import pytest
import asyncio
from typing import Optional
import time

# Base URL for the running API
BASE_URL = "http://localhost:8000"


class TestRunner:
    """Test runner that maintains auth state."""

    def __init__(self):
        self.access_token: Optional[str] = None
        self.user_email = f"test_user_{int(time.time())}@test.com"
        self.user_password = "TestPassword123!"
        self.client = httpx.Client(base_url=BASE_URL, timeout=30.0)
        self.test_project_id: Optional[str] = None
        self.test_scenario_id: Optional[str] = None
        self.test_template_id: Optional[str] = None

    def get_headers(self) -> dict:
        """Get authorization headers."""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    def register_and_login(self):
        """Register a new user and login."""
        # Try to register
        register_data = {
            "email": self.user_email,
            "password": self.user_password,
            "full_name": "Test User",
            "company": "Test Company"
        }

        response = self.client.post("/api/v1/auth/register", json=register_data)
        print(f"Register response: {response.status_code}")

        # Login
        login_data = {
            "email": self.user_email,
            "password": self.user_password
        }

        response = self.client.post("/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
            print(f"Login successful, token obtained")
            return True
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return False


def test_health_check():
    """Test health check endpoint."""
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")


def test_api_docs():
    """Test API documentation endpoints."""
    with httpx.Client(base_url=BASE_URL) as client:
        # Docs
        response = client.get("/docs")
        assert response.status_code == 200
        print("✓ /docs accessible")

        # ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        print("✓ /redoc accessible")


def test_full_workflow():
    """Test complete workflow: auth, project, scenario, simulation."""
    runner = TestRunner()

    print("\n" + "=" * 60)
    print("COMPREHENSIVE API INTEGRATION TEST")
    print("=" * 60)

    # 1. Authentication
    print("\n[1/10] Testing Authentication...")
    success = runner.register_and_login()
    assert success, "Authentication failed"
    print("✓ Authentication successful")

    # 2. Get current user
    print("\n[2/10] Testing Get Current User...")
    response = runner.client.get("/api/v1/auth/me", headers=runner.get_headers())
    assert response.status_code == 200
    user_data = response.json()
    assert "email" in user_data
    print(f"✓ Current user: {user_data['email']}")

    # 3. Create Project
    print("\n[3/10] Testing Create Project...")
    project_data = {
        "name": "Advanced EV Market Study 2026",
        "description": "Comprehensive electric vehicle adoption study with 100 agents",
        "domain": "marketing",  # Must be: marketing, political, finance, or custom
        "settings": {"advanced_mode": True, "agent_count": 100}
    }
    response = runner.client.post(
        "/api/v1/projects/",
        json=project_data,
        headers=runner.get_headers()
    )
    assert response.status_code in [200, 201], f"Project creation failed: {response.text}"
    runner.test_project_id = response.json()["id"]
    print(f"✓ Project created: {runner.test_project_id}")

    # 4. List Projects
    print("\n[4/10] Testing List Projects...")
    response = runner.client.get("/api/v1/projects/", headers=runner.get_headers())
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) > 0
    print(f"✓ Listed {len(projects)} project(s)")

    # 5. Create Advanced Scenario with 100 agents
    print("\n[5/10] Testing Create Advanced Scenario (100 agents)...")
    scenario_data = {
        "project_id": runner.test_project_id,
        "name": "EV Adoption Deep Dive 2026",
        "description": "Comprehensive survey on EV adoption with diverse demographics",
        "scenario_type": "survey",
        "context": """You are participating in a comprehensive market research study about
        electric vehicle adoption in 2026. Consider these factors:

        MARKET CONTEXT:
        - EV range has improved to 400-600 miles for most models
        - Charging infrastructure covers 95% of highways
        - Battery costs have dropped 60% since 2023
        - Federal/state incentives range from $2,500 to $12,500
        - Used EV market is now mature with certified options
        - Major automakers offer 15+ EV models each

        RESPOND BASED ON:
        - Your personal financial situation and budget
        - Daily commute and travel patterns
        - Environmental values and concerns
        - Family needs and vehicle requirements
        - Technology comfort level
        - Current vehicle ownership

        Be specific and authentic in your responses.""",
        "questions": [
            {
                "id": "q1_likelihood",
                "text": "On a scale of 1-10, how likely are you to purchase an electric vehicle as your next vehicle?",
                "type": "scale",
                "scale_min": 1,
                "scale_max": 10,
                "required": True
            },
            {
                "id": "q2_budget",
                "text": "What is the maximum price you would consider paying for an electric vehicle?",
                "type": "multiple_choice",
                "options": [
                    "Under $25,000",
                    "$25,000 - $35,000",
                    "$35,000 - $50,000",
                    "$50,000 - $75,000",
                    "$75,000 - $100,000",
                    "Over $100,000"
                ],
                "required": True
            },
            {
                "id": "q3_concern",
                "text": "What is your PRIMARY concern about owning an electric vehicle?",
                "type": "multiple_choice",
                "options": [
                    "Range anxiety / fear of running out of charge",
                    "Lack of charging infrastructure",
                    "High upfront purchase cost",
                    "Battery longevity and replacement cost",
                    "Concerns about resale value",
                    "Limited model choices",
                    "I have no significant concerns"
                ],
                "required": True
            },
            {
                "id": "q4_environment",
                "text": "How important is environmental sustainability in your vehicle purchase decision? (1-10)",
                "type": "scale",
                "scale_min": 1,
                "scale_max": 10,
                "required": True
            },
            {
                "id": "q5_incentives",
                "text": "Would a $7,500 federal tax credit significantly influence your decision to buy an EV?",
                "type": "yes_no",
                "required": True
            },
            {
                "id": "q6_ideal_ev",
                "text": "Describe your ideal electric vehicle. Include features, range, price point, and vehicle type that would make it perfect for your needs.",
                "type": "open_ended",
                "required": True
            },
            {
                "id": "q7_comparison",
                "text": "If you had to choose between a $45,000 EV with 400-mile range or a $35,000 hybrid getting 50 MPG, which would you choose and why?",
                "type": "open_ended",
                "required": True
            }
        ],
        "variables": {
            "year": 2026,
            "market": "United States",
            "segment": "consumer",
            "study_type": "comprehensive_market_research"
        },
        "population_size": 100,
        "demographics": {
            "age_distribution": {
                "18-24": 0.12,
                "25-34": 0.22,
                "35-44": 0.24,
                "45-54": 0.20,
                "55-64": 0.14,
                "65+": 0.08
            },
            "gender_distribution": {
                "male": 0.48,
                "female": 0.50,
                "non_binary": 0.02
            },
            "income_distribution": {
                "under_30k": 0.15,
                "30k_50k": 0.20,
                "50k_75k": 0.25,
                "75k_100k": 0.20,
                "100k_150k": 0.12,
                "over_150k": 0.08
            },
            "education_distribution": {
                "high_school": 0.25,
                "some_college": 0.25,
                "bachelors": 0.30,
                "masters_plus": 0.20
            },
            "region_distribution": {
                "northeast": 0.18,
                "midwest": 0.21,
                "south": 0.38,
                "west": 0.23
            }
        }
    }

    response = runner.client.post(
        "/api/v1/scenarios/",
        json=scenario_data,
        headers=runner.get_headers()
    )
    assert response.status_code in [200, 201], f"Scenario creation failed: {response.text}"
    runner.test_scenario_id = response.json()["id"]
    print(f"✓ Advanced scenario created: {runner.test_scenario_id}")

    # 6. Validate Scenario
    print("\n[6/10] Testing Validate Scenario...")
    response = runner.client.post(
        f"/api/v1/scenarios/{runner.test_scenario_id}/validate",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    validation = response.json()
    print(f"✓ Scenario validation: {validation}")

    # 7. Create Persona Template
    print("\n[7/10] Testing Create Persona Template...")
    template_data = {
        "name": "US Automotive Consumers 2026",
        "description": "Diverse US consumers for automotive market research",
        "region": "us",
        "country": "United States",
        "industry": "Automotive",
        "topic": "Electric Vehicle Adoption",
        "keywords": ["EV", "sustainability", "technology", "transportation", "green"],
        "source_type": "ai_generated"
    }

    response = runner.client.post(
        "/api/v1/personas/templates",
        json=template_data,
        headers=runner.get_headers()
    )
    assert response.status_code in [200, 201], f"Template creation failed: {response.text}"
    runner.test_template_id = response.json()["id"]
    print(f"✓ Persona template created: {runner.test_template_id}")

    # 8. List Supported Regions
    print("\n[8/10] Testing List Supported Regions...")
    response = runner.client.get(
        "/api/v1/personas/regions",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    regions = response.json()
    print(f"✓ Supported regions: {[r.get('code', r) for r in regions]}")

    # 9. Test Census Data
    print("\n[9/10] Testing Census Data Endpoints...")
    response = runner.client.get(
        "/api/v1/data-sources/census/states",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    states = response.json()
    print(f"✓ US States loaded: {len(states)} states")

    # 10. Create Simulation
    print("\n[10/10] Testing Create 100-Agent Simulation...")
    simulation_data = {
        "scenario_id": runner.test_scenario_id,
        "agent_count": 100,
        "model_used": "gpt-4",
        "run_config": {
            "temperature": 0.8,
            "max_tokens": 1000,
            "batch_size": 10,
            "parallel_agents": 5
        }
    }

    response = runner.client.post(
        "/api/v1/simulations/",
        json=simulation_data,
        headers=runner.get_headers()
    )
    assert response.status_code in [200, 201], f"Simulation creation failed: {response.text}"
    simulation = response.json()
    print(f"✓ 100-Agent simulation created: {simulation['id']}")
    print(f"  - Agent count: {simulation['agent_count']}")
    print(f"  - Status: {simulation['status']}")

    # Get simulation stats
    print("\n[BONUS] Testing Simulation Stats...")
    response = runner.client.get(
        "/api/v1/simulations/stats/overview",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    stats = response.json()
    print(f"✓ Simulation stats: {stats}")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

    # Cleanup
    runner.client.close()

    return {
        "project_id": runner.test_project_id,
        "scenario_id": runner.test_scenario_id,
        "template_id": runner.test_template_id,
        "simulation": simulation
    }


def test_persona_template_crud():
    """Test persona template CRUD operations."""
    runner = TestRunner()
    runner.register_and_login()

    print("\n" + "=" * 60)
    print("PERSONA TEMPLATE CRUD TEST")
    print("=" * 60)

    # Create multiple templates for different regions
    regions = ["us", "europe", "asia", "china"]
    templates = []

    for region in regions:
        template_data = {
            "name": f"Test Template - {region.upper()}",
            "description": f"Test persona template for {region}",
            "region": region,
            "topic": "Technology Adoption",
            "industry": "Technology",
            "source_type": "ai_generated"
        }

        response = runner.client.post(
            "/api/v1/personas/templates",
            json=template_data,
            headers=runner.get_headers()
        )
        assert response.status_code in [200, 201]
        templates.append(response.json())
        print(f"✓ Created template for {region}")

    # List templates
    response = runner.client.get(
        "/api/v1/personas/templates",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    all_templates = response.json()
    print(f"✓ Listed {len(all_templates)} templates")

    # Filter by region
    response = runner.client.get(
        "/api/v1/personas/templates?region=us",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    us_templates = response.json()
    print(f"✓ Filtered US templates: {len(us_templates)}")

    # Get single template
    template_id = templates[0]["id"]
    response = runner.client.get(
        f"/api/v1/personas/templates/{template_id}",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    print(f"✓ Retrieved template: {template_id}")

    # Delete template
    response = runner.client.delete(
        f"/api/v1/personas/templates/{template_id}",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    print(f"✓ Deleted template: {template_id}")

    print("\n✓ PERSONA TEMPLATE CRUD TEST PASSED")
    runner.client.close()


def test_data_sources():
    """Test data source endpoints."""
    runner = TestRunner()
    runner.register_and_login()

    print("\n" + "=" * 60)
    print("DATA SOURCE TEST")
    print("=" * 60)

    # List data sources
    response = runner.client.get(
        "/api/v1/data-sources/",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    print(f"✓ Listed data sources: {len(response.json())}")

    # Create data source (admin only - expect 403 for regular user)
    data_source = {
        "name": "Test Data Source",
        "description": "Test census data source",
        "source_type": "census",
        "coverage_region": "us",
        "coverage_year": 2024
    }

    response = runner.client.post(
        "/api/v1/data-sources/",
        json=data_source,
        headers=runner.get_headers()
    )
    # Admin-only endpoint - 403 is expected for regular users, 201 for admins
    assert response.status_code in [200, 201, 403]
    if response.status_code == 403:
        print("✓ Data source creation correctly requires admin (403)")
    else:
        print("✓ Created data source (admin)")

    # List regional profiles
    response = runner.client.get(
        "/api/v1/data-sources/profiles/",
        headers=runner.get_headers()
    )
    assert response.status_code == 200
    print(f"✓ Listed regional profiles: {len(response.json())}")

    print("\n✓ DATA SOURCE TEST PASSED")
    runner.client.close()


def test_error_handling():
    """Test error handling."""
    with httpx.Client(base_url=BASE_URL) as client:
        print("\n" + "=" * 60)
        print("ERROR HANDLING TEST")
        print("=" * 60)

        # Unauthorized access
        response = client.get("/api/v1/projects/")
        assert response.status_code == 401
        print("✓ Unauthorized access returns 401")

        # Invalid endpoint
        response = client.get("/api/v1/invalid_endpoint")
        assert response.status_code == 404
        print("✓ Invalid endpoint returns 404")

        # Invalid request body
        runner = TestRunner()
        runner.register_and_login()

        response = runner.client.post(
            "/api/v1/projects/",
            json={"invalid": "data"},
            headers=runner.get_headers()
        )
        assert response.status_code == 422
        print("✓ Invalid request body returns 422")

        # Non-existent resource
        response = runner.client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            headers=runner.get_headers()
        )
        assert response.status_code == 404
        print("✓ Non-existent resource returns 404")

        print("\n✓ ERROR HANDLING TEST PASSED")
        runner.client.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("AGENTVERSE COMPREHENSIVE API INTEGRATION TEST SUITE")
    print("=" * 70)

    try:
        # Run all tests
        test_health_check()
        test_api_docs()
        test_error_handling()
        test_data_sources()
        test_persona_template_crud()
        result = test_full_workflow()

        print("\n" + "=" * 70)
        print("ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nTest Results Summary:")
        print(f"  - Project ID: {result['project_id']}")
        print(f"  - Scenario ID: {result['scenario_id']}")
        print(f"  - Template ID: {result['template_id']}")
        print(f"  - Simulation ID: {result['simulation']['id']}")
        print(f"  - Agent Count: {result['simulation']['agent_count']}")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
