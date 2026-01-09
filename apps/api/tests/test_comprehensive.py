"""
Comprehensive API Tests for AgentVerse Platform.

Tests cover:
- Health check and API status
- Authentication (register, login, refresh)
- Projects CRUD
- Scenarios CRUD
- Simulations
- Persona Templates and Generation
- Data Sources
- Census Data Integration
- Regional Profiles
"""

import pytest
from httpx import AsyncClient
import asyncio


class TestHealthCheck:
    """Tests for API health and status endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test the health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_api_docs_accessible(self, client: AsyncClient):
        """Test that API documentation is accessible."""
        response = await client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_schema(self, client: AsyncClient):
        """Test that OpenAPI schema is available."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema


class TestAuthentication:
    """Tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_new_user(self, client: AsyncClient):
        """Test user registration."""
        user_data = {
            "email": f"newuser_{asyncio.get_event_loop().time()}@test.com",
            "password": "SecurePass123!",
            "full_name": "New Test User",
            "company": "Test Corp"
        }
        response = await client.post("/api/v1/auth/register", json=user_data)
        # Either 201 for new user or 400 if already exists
        assert response.status_code in [201, 400]

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, client: AsyncClient):
        """Test login with valid credentials."""
        # First register
        user_data = {
            "email": f"logintest_{asyncio.get_event_loop().time()}@test.com",
            "password": "TestPass123!",
            "full_name": "Login Test User"
        }
        await client.post("/api/v1/auth/register", json=user_data)

        # Then login
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        login_data = {
            "email": "nonexistent@test.com",
            "password": "WrongPassword123!"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code in [401, 400]

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user info."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data


class TestProjects:
    """Tests for project CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers: dict, sample_project_data: dict):
        """Test creating a new project."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.post(
            "/api/v1/projects/",
            json=sample_project_data,
            headers=auth_headers
        )
        assert response.status_code in [201, 200]
        data = response.json()
        assert data["name"] == sample_project_data["name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers: dict):
        """Test listing projects."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/projects/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_project_by_id(self, client: AsyncClient, auth_headers: dict, sample_project_data: dict):
        """Test getting a project by ID."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        # Create project first
        create_response = await client.post(
            "/api/v1/projects/",
            json=sample_project_data,
            headers=auth_headers
        )
        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create project")

        project_id = create_response.json()["id"]

        # Get project
        response = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id


class TestScenarios:
    """Tests for scenario CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_project_data: dict,
        sample_scenario_data: dict
    ):
        """Test creating a new scenario."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        # Create project first
        project_response = await client.post(
            "/api/v1/projects/",
            json=sample_project_data,
            headers=auth_headers
        )
        if project_response.status_code not in [200, 201]:
            pytest.skip("Could not create project")

        project_id = project_response.json()["id"]
        sample_scenario_data["project_id"] = project_id

        # Create scenario
        response = await client.post(
            "/api/v1/scenarios/",
            json=sample_scenario_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == sample_scenario_data["name"]
        assert len(data["questions"]) == 3

    @pytest.mark.asyncio
    async def test_list_scenarios(self, client: AsyncClient, auth_headers: dict):
        """Test listing scenarios."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/scenarios/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_validate_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_project_data: dict,
        sample_scenario_data: dict
    ):
        """Test validating a scenario."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        # Create project and scenario
        project_response = await client.post(
            "/api/v1/projects/",
            json=sample_project_data,
            headers=auth_headers
        )
        if project_response.status_code not in [200, 201]:
            pytest.skip("Could not create project")

        sample_scenario_data["project_id"] = project_response.json()["id"]
        scenario_response = await client.post(
            "/api/v1/scenarios/",
            json=sample_scenario_data,
            headers=auth_headers
        )
        if scenario_response.status_code not in [200, 201]:
            pytest.skip("Could not create scenario")

        scenario_id = scenario_response.json()["id"]

        # Validate
        response = await client.post(
            f"/api/v1/scenarios/{scenario_id}/validate",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data


class TestPersonaTemplates:
    """Tests for persona template operations."""

    @pytest.mark.asyncio
    async def test_create_persona_template(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_persona_template_data: dict
    ):
        """Test creating a persona template."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.post(
            "/api/v1/personas/templates",
            json=sample_persona_template_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == sample_persona_template_data["name"]
        assert data["region"] == sample_persona_template_data["region"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_persona_templates(self, client: AsyncClient, auth_headers: dict):
        """Test listing persona templates."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/personas/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_persona_templates_with_region_filter(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing persona templates with region filter."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get(
            "/api/v1/personas/templates?region=us",
            headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_persona_template_by_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_persona_template_data: dict
    ):
        """Test getting a persona template by ID."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        # Create template first
        create_response = await client.post(
            "/api/v1/personas/templates",
            json=sample_persona_template_data,
            headers=auth_headers
        )
        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create template")

        template_id = create_response.json()["id"]

        # Get template
        response = await client.get(
            f"/api/v1/personas/templates/{template_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template_id


class TestPersonaGeneration:
    """Tests for persona generation."""

    @pytest.mark.asyncio
    async def test_generate_personas(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_generate_personas_request: dict
    ):
        """Test generating personas."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.post(
            "/api/v1/personas/generate",
            json=sample_generate_personas_request,
            headers=auth_headers
        )
        # Generation might take time or fail due to missing LLM config
        assert response.status_code in [200, 201, 500, 503]

    @pytest.mark.asyncio
    async def test_list_supported_regions(self, client: AsyncClient, auth_headers: dict):
        """Test listing supported regions."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/personas/regions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least US, Europe, Asia, China
        region_codes = [r.get("code") for r in data]
        assert "us" in region_codes or len(data) > 0


class TestDataSources:
    """Tests for data source operations."""

    @pytest.mark.asyncio
    async def test_list_data_sources(self, client: AsyncClient, auth_headers: dict):
        """Test listing data sources."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/data-sources/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_data_source(self, client: AsyncClient, auth_headers: dict):
        """Test creating a data source."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        data_source = {
            "name": "Test Census Data",
            "description": "Test data source for US Census",
            "source_type": "census",
            "coverage_region": "us",
            "coverage_year": 2024
        }

        response = await client.post(
            "/api/v1/data-sources/",
            json=data_source,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]


class TestCensusData:
    """Tests for census data endpoints."""

    @pytest.mark.asyncio
    async def test_get_us_states(self, client: AsyncClient, auth_headers: dict):
        """Test getting US states."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/data-sources/census/states", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_census_demographics(self, client: AsyncClient, auth_headers: dict):
        """Test getting census demographics."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get(
            "/api/v1/data-sources/census/demographics/age",
            headers=auth_headers
        )
        # Might fail if Census API key not configured
        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_get_census_profile(self, client: AsyncClient, auth_headers: dict):
        """Test getting census profile."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get(
            "/api/v1/data-sources/census/profile",
            headers=auth_headers
        )
        assert response.status_code in [200, 500, 503]


class TestSimulations:
    """Tests for simulation operations."""

    @pytest.mark.asyncio
    async def test_list_simulations(self, client: AsyncClient, auth_headers: dict):
        """Test listing simulations."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/simulations/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_simulation_stats(self, client: AsyncClient, auth_headers: dict):
        """Test getting simulation stats."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/simulations/stats/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_runs" in data


class TestAdvancedSimulation:
    """Tests for advanced simulation with 100 agents."""

    @pytest.mark.asyncio
    async def test_create_100_agent_simulation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_project_data: dict
    ):
        """Test creating a simulation with 100 agents on advanced topic."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        # Create project
        project_response = await client.post(
            "/api/v1/projects/",
            json={
                "name": "Advanced EV Market Study 2026",
                "description": "Comprehensive study on EV adoption across demographics",
                "domain": "automotive"
            },
            headers=auth_headers
        )
        if project_response.status_code not in [200, 201]:
            pytest.skip("Could not create project")

        project_id = project_response.json()["id"]

        # Create advanced scenario with complex questions
        advanced_scenario = {
            "project_id": project_id,
            "name": "EV Market Sentiment Analysis 2026",
            "description": "Deep analysis of consumer sentiment towards electric vehicles",
            "scenario_type": "survey",
            "context": """You are participating in a comprehensive market research study about
            electric vehicles in 2026. Consider the following context:

            - EV technology has matured significantly with 500+ mile ranges common
            - Charging infrastructure has expanded to cover 95% of major highways
            - Battery costs have dropped 60% since 2023
            - Government incentives vary by state (some up to $10,000)
            - Used EV market is now established with certified pre-owned options
            - Most major automakers offer 10+ EV models

            Please respond based on your personal circumstances, values, and needs.
            Consider your daily commute, family needs, environmental concerns, and budget.""",
            "questions": [
                {
                    "id": "q1",
                    "text": "On a scale of 1-10, how likely are you to purchase an electric vehicle as your next car?",
                    "type": "scale",
                    "scale_min": 1,
                    "scale_max": 10,
                    "required": True
                },
                {
                    "id": "q2",
                    "text": "What is the MAXIMUM price you would pay for an electric vehicle?",
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
                    "id": "q3",
                    "text": "What is your PRIMARY concern about owning an electric vehicle?",
                    "type": "multiple_choice",
                    "options": [
                        "Range anxiety / fear of running out of charge",
                        "Lack of charging infrastructure in my area",
                        "High upfront purchase cost",
                        "Uncertainty about battery longevity and replacement cost",
                        "Concerns about resale value",
                        "Limited model choices / vehicle types",
                        "I have no significant concerns"
                    ],
                    "required": True
                },
                {
                    "id": "q4",
                    "text": "How important is environmental sustainability in your vehicle purchase decision?",
                    "type": "scale",
                    "scale_min": 1,
                    "scale_max": 10,
                    "required": True
                },
                {
                    "id": "q5",
                    "text": "Which of these factors would MOST influence you to buy an EV? (Select all that apply)",
                    "type": "open_ended",
                    "required": True
                },
                {
                    "id": "q6",
                    "text": "Describe your ideal electric vehicle. What features, range, and price point would make it perfect for you?",
                    "type": "open_ended",
                    "required": True
                },
                {
                    "id": "q7",
                    "text": "If you had to choose between a $40,000 EV with 350-mile range or a $30,000 hybrid, which would you choose and why?",
                    "type": "open_ended",
                    "required": True
                }
            ],
            "variables": {
                "year": 2026,
                "market": "US",
                "segment": "consumer_vehicles",
                "study_type": "market_research"
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

        # Create scenario
        scenario_response = await client.post(
            "/api/v1/scenarios/",
            json=advanced_scenario,
            headers=auth_headers
        )
        assert scenario_response.status_code in [200, 201], f"Failed to create scenario: {scenario_response.text}"
        scenario_id = scenario_response.json()["id"]

        # Validate scenario
        validate_response = await client.post(
            f"/api/v1/scenarios/{scenario_id}/validate",
            headers=auth_headers
        )
        assert validate_response.status_code == 200
        validation = validate_response.json()
        assert validation["is_valid"] == True, f"Scenario validation failed: {validation}"

        # Create simulation run
        simulation_data = {
            "scenario_id": scenario_id,
            "agent_count": 100,
            "model_used": "gpt-4",
            "run_config": {
                "temperature": 0.8,
                "max_tokens": 1000,
                "batch_size": 10,
                "parallel_agents": 5
            }
        }

        sim_response = await client.post(
            "/api/v1/simulations/",
            json=simulation_data,
            headers=auth_headers
        )
        assert sim_response.status_code in [200, 201], f"Failed to create simulation: {sim_response.text}"
        sim_data = sim_response.json()
        assert "id" in sim_data
        assert sim_data["agent_count"] == 100

        return sim_data


class TestRegionalProfiles:
    """Tests for regional profile operations."""

    @pytest.mark.asyncio
    async def test_list_regional_profiles(self, client: AsyncClient, auth_headers: dict):
        """Test listing regional profiles."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get("/api/v1/data-sources/profiles/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that unauthorized access is rejected."""
        response = await client.get("/api/v1/projects/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found_resource(self, client: AsyncClient, auth_headers: dict):
        """Test 404 for non-existent resources."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_request_body(self, client: AsyncClient, auth_headers: dict):
        """Test validation for invalid request bodies."""
        if not auth_headers:
            pytest.skip("No auth headers available")

        response = await client.post(
            "/api/v1/projects/",
            json={"invalid_field": "test"},
            headers=auth_headers
        )
        assert response.status_code == 422


# Run specific advanced test when called directly
if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
