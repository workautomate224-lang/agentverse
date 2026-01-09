"""
AgentVerse Load Testing Suite
Reference: project.md §10.2 (Capacity Planning)

Uses Locust for load testing with realistic user scenarios.

Run with:
    locust -f locustfile.py --host http://localhost:8000

Or headless:
    locust -f locustfile.py --host http://localhost:8000 --headless -u 100 -r 10 -t 5m
"""

import json
import random
import time
from uuid import uuid4
from typing import Optional

from locust import HttpUser, task, between, tag, events
from locust.exception import StopUser


# =============================================================================
# Configuration
# =============================================================================

# Test user credentials (should be created before running tests)
TEST_USERS = [
    {"email": "loadtest1@example.com", "password": "LoadTest123!"},
    {"email": "loadtest2@example.com", "password": "LoadTest123!"},
    {"email": "loadtest3@example.com", "password": "LoadTest123!"},
]

# Target concurrency levels (from project.md §10.2)
TARGET_CONCURRENT_USERS = 100
TARGET_RPS_API = 500
TARGET_RPS_SIMULATION = 50


# =============================================================================
# Base User Class
# =============================================================================

class AuthenticatedUser(HttpUser):
    """Base class for authenticated API users."""

    wait_time = between(1, 3)
    abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.project_ids: list = []
        self.node_ids: list = []

    def on_start(self):
        """Authenticate before starting tasks."""
        self._login()
        if self.token:
            self._fetch_projects()

    def _login(self):
        """Login and get JWT token."""
        user = random.choice(TEST_USERS)

        with self.client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": user["password"]},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                response.success()
            elif response.status_code == 404:
                # User doesn't exist, try to register
                self._register(user)
            else:
                response.failure(f"Login failed: {response.status_code}")

    def _register(self, user: dict):
        """Register a new test user."""
        with self.client.post(
            "/api/v1/auth/register",
            json={
                "email": user["email"],
                "password": user["password"],
                "full_name": "Load Test User",
            },
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")

    def _fetch_projects(self):
        """Fetch existing projects for the user."""
        headers = self._auth_headers()
        with self.client.get(
            "/api/v1/project-specs",
            headers=headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.project_ids = [p["id"] for p in data.get("items", [])]
                response.success()
            else:
                response.failure(f"Fetch projects failed: {response.status_code}")

    def _auth_headers(self) -> dict:
        """Get authentication headers."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}


# =============================================================================
# API Load Test Users
# =============================================================================

class APIUser(AuthenticatedUser):
    """Simulates typical API usage patterns."""

    weight = 10  # Most common user type

    @task(10)
    @tag("read", "health")
    def health_check(self):
        """Check API health endpoint."""
        self.client.get("/health/ready")

    @task(5)
    @tag("read", "projects")
    def list_projects(self):
        """List user's projects."""
        self.client.get(
            "/api/v1/project-specs",
            headers=self._auth_headers(),
        )

    @task(3)
    @tag("read", "projects")
    def get_project(self):
        """Get a specific project."""
        if self.project_ids:
            project_id = random.choice(self.project_ids)
            self.client.get(
                f"/api/v1/project-specs/{project_id}",
                headers=self._auth_headers(),
            )

    @task(2)
    @tag("read", "nodes")
    def list_nodes(self):
        """List nodes for a project."""
        if self.project_ids:
            project_id = random.choice(self.project_ids)
            with self.client.get(
                f"/api/v1/nodes/universe-map/{project_id}",
                headers=self._auth_headers(),
                catch_response=True,
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    self.node_ids = [n["id"] for n in data.get("nodes", [])]
                    response.success()
                else:
                    response.failure(f"List nodes failed: {response.status_code}")

    @task(2)
    @tag("read", "nodes")
    def get_node(self):
        """Get a specific node."""
        if self.node_ids:
            node_id = random.choice(self.node_ids)
            self.client.get(
                f"/api/v1/nodes/{node_id}",
                headers=self._auth_headers(),
            )

    @task(1)
    @tag("read", "runs")
    def list_runs(self):
        """List simulation runs."""
        if self.project_ids:
            project_id = random.choice(self.project_ids)
            self.client.get(
                f"/api/v1/runs?project_id={project_id}",
                headers=self._auth_headers(),
            )

    @task(1)
    @tag("read", "telemetry")
    def get_telemetry(self):
        """Get telemetry data for a node."""
        if self.node_ids:
            node_id = random.choice(self.node_ids)
            self.client.get(
                f"/api/v1/telemetry/{node_id}",
                headers=self._auth_headers(),
            )

    @task(1)
    @tag("write", "projects")
    def create_project(self):
        """Create a new project."""
        project_data = {
            "name": f"Load Test Project {uuid4().hex[:8]}",
            "description": "Created by load test",
            "domain": "consumer_goods",
            "prediction_core": "society",
            "default_horizon_days": 30,
        }

        with self.client.post(
            "/api/v1/project-specs",
            json=project_data,
            headers=self._auth_headers(),
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                data = response.json()
                self.project_ids.append(data["id"])
                response.success()
            else:
                response.failure(f"Create project failed: {response.status_code}")


class SimulationUser(AuthenticatedUser):
    """Simulates users running simulations."""

    weight = 2  # Less common but more intensive
    wait_time = between(5, 15)  # Longer wait times

    @task(3)
    @tag("simulation", "create")
    def create_and_run_simulation(self):
        """Create a run and execute it."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        # Create run configuration
        run_config = {
            "project_id": project_id,
            "name": f"Load Test Run {uuid4().hex[:8]}",
            "mode": "society",
            "config": {
                "ticks": random.randint(10, 50),
                "seed": random.randint(1, 1000000),
            },
        }

        with self.client.post(
            "/api/v1/runs",
            json=run_config,
            headers=self._auth_headers(),
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                run_id = response.json().get("id")
                response.success()

                # Start the run
                self._start_run(run_id)
            else:
                response.failure(f"Create run failed: {response.status_code}")

    def _start_run(self, run_id: str):
        """Start a simulation run."""
        with self.client.post(
            f"/api/v1/runs/{run_id}/start",
            headers=self._auth_headers(),
            catch_response=True,
        ) as response:
            if response.status_code in (200, 202):
                response.success()
                # Poll for completion
                self._poll_run_status(run_id)
            else:
                response.failure(f"Start run failed: {response.status_code}")

    def _poll_run_status(self, run_id: str, max_polls: int = 10):
        """Poll run status until completion."""
        for _ in range(max_polls):
            time.sleep(2)
            with self.client.get(
                f"/api/v1/runs/{run_id}",
                headers=self._auth_headers(),
                name="/api/v1/runs/[id] (poll)",
                catch_response=True,
            ) as response:
                if response.status_code == 200:
                    status = response.json().get("status")
                    response.success()
                    if status in ("completed", "failed", "cancelled"):
                        return
                else:
                    response.failure(f"Poll run failed: {response.status_code}")
                    return

    @task(2)
    @tag("simulation", "fork")
    def fork_node(self):
        """Fork an existing node with modified parameters."""
        if not self.node_ids:
            return

        node_id = random.choice(self.node_ids)

        fork_config = {
            "parent_node_id": node_id,
            "variable_deltas": {
                "economy_confidence": random.uniform(-0.2, 0.2),
                "media_sentiment": random.uniform(-0.3, 0.3),
            },
            "name": f"Fork {uuid4().hex[:8]}",
        }

        with self.client.post(
            "/api/v1/nodes/fork",
            json=fork_config,
            headers=self._auth_headers(),
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                new_node_id = response.json().get("id")
                self.node_ids.append(new_node_id)
                response.success()
            else:
                response.failure(f"Fork node failed: {response.status_code}")


class AskUser(AuthenticatedUser):
    """Simulates users using the Ask (event compiler) feature."""

    weight = 1  # Less common, heavy processing
    wait_time = between(10, 30)

    @task(1)
    @tag("ask", "compile")
    def ask_compile(self):
        """Submit an Ask prompt for compilation."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        prompts = [
            "What if the economy improves by 20%?",
            "Simulate a media crisis about product safety",
            "How would a competitor price cut affect our market share?",
            "What if trust in the brand increases significantly?",
        ]

        ask_request = {
            "project_id": project_id,
            "prompt": random.choice(prompts),
            "max_scenarios": random.randint(3, 10),
            "use_clustering": True,
        }

        with self.client.post(
            "/api/v1/ask/compile",
            json=ask_request,
            headers=self._auth_headers(),
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            else:
                response.failure(f"Ask compile failed: {response.status_code}")


class AdminUser(AuthenticatedUser):
    """Simulates admin users checking system status."""

    weight = 1
    wait_time = between(30, 60)

    @task(3)
    @tag("admin", "health")
    def check_health(self):
        """Check detailed health status."""
        self.client.get("/health/ready")

    @task(2)
    @tag("admin", "metrics")
    def get_metrics(self):
        """Fetch Prometheus metrics."""
        self.client.get("/metrics")

    @task(1)
    @tag("admin", "audit")
    def list_audit_logs(self):
        """List recent audit logs."""
        self.client.get(
            "/api/v1/privacy/retention/policies",
            headers=self._auth_headers(),
        )


# =============================================================================
# Event Handlers
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment."""
    print("=" * 60)
    print("AgentVerse Load Test Starting")
    print(f"Target Host: {environment.host}")
    print(f"Target Concurrent Users: {TARGET_CONCURRENT_USERS}")
    print(f"Target RPS (API): {TARGET_RPS_API}")
    print(f"Target RPS (Simulation): {TARGET_RPS_SIMULATION}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Report test results."""
    print("=" * 60)
    print("AgentVerse Load Test Complete")

    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    avg_response_time = stats.total.avg_response_time

    print(f"Total Requests: {total_requests}")
    print(f"Total Failures: {total_failures} ({100 * total_failures / max(1, total_requests):.2f}%)")
    print(f"Average Response Time: {avg_response_time:.2f}ms")
    print(f"RPS: {stats.total.current_rps:.2f}")

    # Check against targets
    if stats.total.current_rps >= TARGET_RPS_API * 0.8:
        print("PASS: RPS target achieved")
    else:
        print(f"FAIL: RPS below target ({TARGET_RPS_API})")

    if total_failures / max(1, total_requests) < 0.01:
        print("PASS: Error rate below 1%")
    else:
        print("FAIL: Error rate above 1%")

    if avg_response_time < 500:
        print("PASS: Average response time below 500ms")
    else:
        print(f"FAIL: Average response time above 500ms")

    print("=" * 60)


# =============================================================================
# Custom Metrics
# =============================================================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics per request."""
    # Track slow requests (> 1 second)
    if response_time > 1000 and exception is None:
        print(f"SLOW REQUEST: {name} took {response_time:.2f}ms")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import subprocess
    import sys

    # Run locust with default parameters
    cmd = [
        "locust",
        "-f", __file__,
        "--host", "http://localhost:8000",
        "--headless",
        "-u", "50",
        "-r", "5",
        "-t", "2m",
    ]

    sys.exit(subprocess.call(cmd))
