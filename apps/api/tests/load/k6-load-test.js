/**
 * AgentVerse K6 Load Testing Suite
 * Reference: project.md §10.2 (Capacity Planning)
 *
 * Run with:
 *   k6 run k6-load-test.js
 *
 * With options:
 *   k6 run --vus 100 --duration 5m k6-load-test.js
 *
 * With cloud:
 *   k6 cloud k6-load-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomString, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// =============================================================================
// Configuration
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_BASE = `${BASE_URL}/api/v1`;

// Test user credentials
const TEST_USERS = [
    { email: 'loadtest1@example.com', password: 'LoadTest123!' },
    { email: 'loadtest2@example.com', password: 'LoadTest123!' },
    { email: 'loadtest3@example.com', password: 'LoadTest123!' },
];

// Target metrics (from project.md §10.2)
const TARGET_RPS = 500;
const TARGET_P95_LATENCY = 500; // ms
const TARGET_ERROR_RATE = 0.01; // 1%

// =============================================================================
// Test Scenarios
// =============================================================================

export const options = {
    scenarios: {
        // Smoke test - basic functionality check
        smoke: {
            executor: 'constant-vus',
            vus: 1,
            duration: '30s',
            tags: { scenario: 'smoke' },
            exec: 'smokeTest',
        },
        // Load test - sustained load
        load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 50 },   // Ramp up
                { duration: '5m', target: 50 },   // Stay at 50
                { duration: '2m', target: 100 },  // Ramp to 100
                { duration: '5m', target: 100 },  // Stay at 100
                { duration: '2m', target: 0 },    // Ramp down
            ],
            tags: { scenario: 'load' },
            exec: 'loadTest',
        },
        // Stress test - find breaking point
        stress: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 100 },
                { duration: '2m', target: 200 },
                { duration: '2m', target: 300 },
                { duration: '2m', target: 400 },
                { duration: '2m', target: 500 },
                { duration: '5m', target: 500 },
                { duration: '2m', target: 0 },
            ],
            tags: { scenario: 'stress' },
            exec: 'loadTest',
        },
        // Spike test - sudden traffic spike
        spike: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 10 },  // Baseline
                { duration: '10s', target: 200 }, // Spike!
                { duration: '1m', target: 200 },  // Hold spike
                { duration: '10s', target: 10 },  // Back down
                { duration: '30s', target: 10 },  // Baseline
            ],
            tags: { scenario: 'spike' },
            exec: 'loadTest',
        },
    },
    thresholds: {
        // Overall thresholds
        http_req_duration: ['p(95)<500', 'p(99)<1000'],
        http_req_failed: ['rate<0.01'],

        // Per-endpoint thresholds
        'http_req_duration{name:health}': ['p(95)<100'],
        'http_req_duration{name:list_projects}': ['p(95)<300'],
        'http_req_duration{name:get_node}': ['p(95)<200'],
        'http_req_duration{name:create_run}': ['p(95)<500'],

        // Custom metrics
        'login_duration': ['p(95)<1000'],
        'simulation_duration': ['p(95)<30000'],
    },
};

// =============================================================================
// Custom Metrics
// =============================================================================

const loginDuration = new Trend('login_duration');
const simulationDuration = new Trend('simulation_duration');
const apiErrors = new Counter('api_errors');
const slowRequests = new Counter('slow_requests');

// =============================================================================
// Helper Functions
// =============================================================================

function getRandomUser() {
    return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

function login(user) {
    const startTime = Date.now();

    const res = http.post(
        `${API_BASE}/auth/login`,
        JSON.stringify({
            email: user.email,
            password: user.password,
        }),
        {
            headers: { 'Content-Type': 'application/json' },
            tags: { name: 'login' },
        }
    );

    loginDuration.add(Date.now() - startTime);

    if (res.status === 200) {
        const body = JSON.parse(res.body);
        return body.access_token;
    } else if (res.status === 404 || res.status === 401) {
        // Try to register
        const registerRes = http.post(
            `${API_BASE}/auth/register`,
            JSON.stringify({
                email: user.email,
                password: user.password,
                full_name: 'Load Test User',
            }),
            {
                headers: { 'Content-Type': 'application/json' },
                tags: { name: 'register' },
            }
        );

        if (registerRes.status === 200 || registerRes.status === 201) {
            const body = JSON.parse(registerRes.body);
            return body.access_token;
        }
    }

    apiErrors.add(1);
    return null;
}

function authHeaders(token) {
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };
}

// =============================================================================
// Smoke Test
// =============================================================================

export function smokeTest() {
    group('Smoke Test', () => {
        // Health check
        const healthRes = http.get(`${BASE_URL}/health/ready`, {
            tags: { name: 'health' },
        });

        check(healthRes, {
            'health check returns 200': (r) => r.status === 200,
            'health check response time < 100ms': (r) => r.timings.duration < 100,
        });

        // Root endpoint
        const rootRes = http.get(BASE_URL, {
            tags: { name: 'root' },
        });

        check(rootRes, {
            'root returns 200': (r) => r.status === 200,
        });

        sleep(1);
    });
}

// =============================================================================
// Load Test
// =============================================================================

export function loadTest() {
    const user = getRandomUser();
    const token = login(user);

    if (!token) {
        console.error('Failed to authenticate');
        sleep(5);
        return;
    }

    const headers = authHeaders(token);
    let projectIds = [];
    let nodeIds = [];

    // Fetch existing projects
    group('Read Operations', () => {
        // List projects
        const projectsRes = http.get(`${API_BASE}/project-specs`, {
            headers,
            tags: { name: 'list_projects' },
        });

        check(projectsRes, {
            'list projects returns 200': (r) => r.status === 200,
        });

        if (projectsRes.status === 200) {
            try {
                const body = JSON.parse(projectsRes.body);
                projectIds = (body.items || []).map(p => p.id);
            } catch (e) {
                console.error('Failed to parse projects response');
            }
        }

        if (projectsRes.timings.duration > 1000) {
            slowRequests.add(1);
        }

        sleep(randomIntBetween(1, 3));

        // Get specific project
        if (projectIds.length > 0) {
            const projectId = projectIds[Math.floor(Math.random() * projectIds.length)];

            const projectRes = http.get(`${API_BASE}/project-specs/${projectId}`, {
                headers,
                tags: { name: 'get_project' },
            });

            check(projectRes, {
                'get project returns 200': (r) => r.status === 200,
            });

            // Get nodes for project
            const nodesRes = http.get(`${API_BASE}/nodes/universe-map/${projectId}`, {
                headers,
                tags: { name: 'list_nodes' },
            });

            check(nodesRes, {
                'list nodes returns 200': (r) => r.status === 200,
            });

            if (nodesRes.status === 200) {
                try {
                    const body = JSON.parse(nodesRes.body);
                    nodeIds = (body.nodes || []).map(n => n.id);
                } catch (e) {
                    console.error('Failed to parse nodes response');
                }
            }
        }

        sleep(randomIntBetween(1, 2));

        // Get specific node
        if (nodeIds.length > 0) {
            const nodeId = nodeIds[Math.floor(Math.random() * nodeIds.length)];

            const nodeRes = http.get(`${API_BASE}/nodes/${nodeId}`, {
                headers,
                tags: { name: 'get_node' },
            });

            check(nodeRes, {
                'get node returns 200': (r) => r.status === 200,
            });

            // Get telemetry for node
            const telemetryRes = http.get(`${API_BASE}/telemetry/${nodeId}`, {
                headers,
                tags: { name: 'get_telemetry' },
            });

            check(telemetryRes, {
                'get telemetry returns 2xx': (r) => r.status >= 200 && r.status < 300,
            });
        }
    });

    sleep(randomIntBetween(2, 5));

    // Write operations (less frequent)
    if (Math.random() < 0.1) {
        group('Write Operations', () => {
            // Create project
            const projectData = {
                name: `Load Test Project ${randomString(8)}`,
                description: 'Created by K6 load test',
                domain: 'consumer_goods',
                prediction_core: 'society',
                default_horizon_days: 30,
            };

            const createRes = http.post(
                `${API_BASE}/project-specs`,
                JSON.stringify(projectData),
                {
                    headers,
                    tags: { name: 'create_project' },
                }
            );

            check(createRes, {
                'create project returns 2xx': (r) => r.status >= 200 && r.status < 300,
            });

            if (createRes.status >= 200 && createRes.status < 300) {
                try {
                    const body = JSON.parse(createRes.body);
                    projectIds.push(body.id);
                } catch (e) {
                    console.error('Failed to parse create response');
                }
            }
        });
    }

    sleep(randomIntBetween(3, 8));

    // Simulation operations (even less frequent)
    if (Math.random() < 0.05 && projectIds.length > 0) {
        group('Simulation Operations', () => {
            const startTime = Date.now();
            const projectId = projectIds[Math.floor(Math.random() * projectIds.length)];

            // Create run
            const runConfig = {
                project_id: projectId,
                name: `Load Test Run ${randomString(8)}`,
                mode: 'society',
                config: {
                    ticks: randomIntBetween(10, 30),
                    seed: randomIntBetween(1, 1000000),
                },
            };

            const createRunRes = http.post(
                `${API_BASE}/runs`,
                JSON.stringify(runConfig),
                {
                    headers,
                    tags: { name: 'create_run' },
                }
            );

            check(createRunRes, {
                'create run returns 2xx': (r) => r.status >= 200 && r.status < 300,
            });

            if (createRunRes.status >= 200 && createRunRes.status < 300) {
                try {
                    const body = JSON.parse(createRunRes.body);
                    const runId = body.id;

                    // Start run
                    const startRunRes = http.post(
                        `${API_BASE}/runs/${runId}/start`,
                        '{}',
                        {
                            headers,
                            tags: { name: 'start_run' },
                        }
                    );

                    check(startRunRes, {
                        'start run returns 2xx': (r) => r.status >= 200 && r.status < 300,
                    });

                    // Poll for completion (limited attempts)
                    for (let i = 0; i < 5; i++) {
                        sleep(2);

                        const statusRes = http.get(`${API_BASE}/runs/${runId}`, {
                            headers,
                            tags: { name: 'poll_run' },
                        });

                        if (statusRes.status === 200) {
                            const statusBody = JSON.parse(statusRes.body);
                            if (['completed', 'failed', 'cancelled'].includes(statusBody.status)) {
                                break;
                            }
                        }
                    }

                    simulationDuration.add(Date.now() - startTime);
                } catch (e) {
                    console.error('Failed to run simulation');
                }
            }
        });
    }

    sleep(randomIntBetween(5, 15));
}

// =============================================================================
// Setup and Teardown
// =============================================================================

export function setup() {
    console.log('='.repeat(60));
    console.log('AgentVerse K6 Load Test Starting');
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`Target RPS: ${TARGET_RPS}`);
    console.log(`Target P95 Latency: ${TARGET_P95_LATENCY}ms`);
    console.log(`Target Error Rate: ${TARGET_ERROR_RATE * 100}%`);
    console.log('='.repeat(60));

    // Verify API is reachable
    const healthRes = http.get(`${BASE_URL}/health/ready`);
    if (healthRes.status !== 200) {
        throw new Error(`API health check failed: ${healthRes.status}`);
    }

    return { startTime: Date.now() };
}

export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log('='.repeat(60));
    console.log('AgentVerse K6 Load Test Complete');
    console.log(`Total Duration: ${duration.toFixed(2)}s`);
    console.log('='.repeat(60));
}

// =============================================================================
// Default Function
// =============================================================================

export default function() {
    loadTest();
}
