# AgentVerse Capacity Planning

**Document Version:** 1.0
**Last Updated:** 2026-01-09
**Owner:** Platform Team

---

## 1. Overview

This document defines the capacity targets, performance requirements, and load testing procedures for the AgentVerse platform.

---

## 2. Performance Targets

### 2.1 API Performance

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Throughput** | 500 RPS | 300 RPS minimum |
| **P50 Latency** | < 100ms | < 200ms |
| **P95 Latency** | < 500ms | < 1000ms |
| **P99 Latency** | < 1000ms | < 2000ms |
| **Error Rate** | < 0.1% | < 1% |
| **Availability** | 99.9% | 99.5% |

### 2.2 Simulation Performance

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Concurrent Simulations** | 50 | 20 minimum |
| **Simulation Throughput** | 10/minute | 5/minute minimum |
| **Agent Capacity per Sim** | 10,000 agents | 5,000 minimum |
| **Tick Processing** | < 100ms/tick | < 500ms/tick |
| **P95 Sim Duration (100 ticks)** | < 30s | < 60s |

### 2.3 Database Performance

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Query P95** | < 50ms | < 200ms |
| **Write P95** | < 100ms | < 500ms |
| **Connection Pool** | 50 connections | 100 max |
| **Max Concurrent Queries** | 200 | 300 max |

### 2.4 Redis/Cache Performance

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Cache Hit Rate** | > 80% | > 60% |
| **Get P95** | < 5ms | < 20ms |
| **Set P95** | < 10ms | < 50ms |
| **Memory Usage** | < 70% | < 90% |

---

## 3. Concurrent User Targets

### 3.1 User Tiers

| Tier | Concurrent Users | Expected Behavior |
|------|------------------|-------------------|
| **Nominal** | 100 | Normal operations |
| **High** | 250 | Peak business hours |
| **Stress** | 500 | Marketing events |
| **Limit** | 1000 | System capacity |

### 3.2 User Distribution

| User Type | Percentage | Primary Actions |
|-----------|------------|-----------------|
| **Readers** | 60% | View projects, nodes, telemetry |
| **Editors** | 30% | Create/modify projects, personas |
| **Simulators** | 8% | Run simulations |
| **Admins** | 2% | System monitoring, config |

---

## 4. Resource Sizing

### 4.1 API Servers

| Load | Instances | CPU | Memory | Notes |
|------|-----------|-----|--------|-------|
| **Development** | 1 | 2 vCPU | 4 GB | Single instance |
| **Staging** | 2 | 2 vCPU | 4 GB | HA setup |
| **Production** | 4 | 4 vCPU | 8 GB | Auto-scaling 2-8 |

### 4.2 Worker Nodes (Celery)

| Load | Instances | CPU | Memory | Concurrency |
|------|-----------|-----|--------|-------------|
| **Development** | 1 | 2 vCPU | 4 GB | 4 workers |
| **Staging** | 2 | 4 vCPU | 8 GB | 8 workers each |
| **Production** | 4 | 8 vCPU | 16 GB | 16 workers each |

### 4.3 Database (PostgreSQL)

| Load | Instance Type | CPU | Memory | Storage | IOPS |
|------|--------------|-----|--------|---------|------|
| **Development** | db.t3.medium | 2 vCPU | 4 GB | 100 GB | 3000 |
| **Staging** | db.r5.large | 2 vCPU | 16 GB | 250 GB | 10000 |
| **Production** | db.r5.2xlarge | 8 vCPU | 64 GB | 1 TB | 40000 |

### 4.4 Redis

| Load | Instance Type | Memory | Nodes |
|------|--------------|--------|-------|
| **Development** | cache.t3.micro | 0.5 GB | 1 |
| **Staging** | cache.r5.large | 13 GB | 2 (replica) |
| **Production** | cache.r5.xlarge | 26 GB | 3 (cluster) |

---

## 5. Load Testing Procedures

### 5.1 Test Types

| Test Type | Purpose | Duration | Target Load |
|-----------|---------|----------|-------------|
| **Smoke** | Basic functionality | 5 min | 1-5 users |
| **Load** | Sustained performance | 30 min | 100 users |
| **Stress** | Find breaking point | 30 min | Ramp to 500 |
| **Spike** | Sudden traffic surge | 10 min | 10 → 200 → 10 |
| **Soak** | Memory leaks, degradation | 4 hours | 50 users |

### 5.2 Running Load Tests

#### Using Locust

```bash
# Install
pip install locust

# Run with UI
cd tests/load
locust -f locustfile.py --host http://localhost:8000

# Run headless
locust -f locustfile.py --host http://localhost:8000 \
    --headless -u 100 -r 10 -t 5m \
    --html=report.html
```

#### Using K6

```bash
# Install
brew install k6  # macOS
# or: apt install k6  # Linux

# Run smoke test
k6 run --env BASE_URL=http://localhost:8000 k6-load-test.js

# Run load test
k6 run --vus 100 --duration 30m k6-load-test.js

# Run stress test
k6 run k6-load-test.js --scenario stress
```

### 5.3 Pre-Test Checklist

```
[ ] 1. Notify stakeholders of test window
[ ] 2. Ensure monitoring dashboards are active
[ ] 3. Take baseline metrics snapshot
[ ] 4. Clear any existing test data
[ ] 5. Create test user accounts
[ ] 6. Verify database backup is recent
[ ] 7. Set up alert suppression if needed
[ ] 8. Prepare rollback plan
```

### 5.4 Test User Setup

```sql
-- Create test users (run once)
INSERT INTO users (email, hashed_password, full_name, is_active)
VALUES
    ('loadtest1@example.com', '$2b$12$...', 'Load Test 1', true),
    ('loadtest2@example.com', '$2b$12$...', 'Load Test 2', true),
    ('loadtest3@example.com', '$2b$12$...', 'Load Test 3', true);
```

---

## 6. Bottleneck Analysis

### 6.1 Common Bottlenecks

| Component | Symptom | Mitigation |
|-----------|---------|------------|
| **Database connections** | Connection timeout errors | Increase pool size, add read replicas |
| **CPU (API)** | High latency, queue buildup | Add more API instances |
| **Memory (Workers)** | OOM errors, crashes | Increase memory, reduce concurrency |
| **Redis memory** | Evictions, cache misses | Increase cache size, optimize TTLs |
| **Network I/O** | Slow S3 uploads | Use async uploads, CDN |
| **LLM API** | Rate limiting, timeouts | Add retry logic, cache responses |

### 6.2 Scaling Triggers

| Metric | Scale Up When | Scale Down When |
|--------|---------------|-----------------|
| **CPU Usage** | > 70% for 5 min | < 30% for 15 min |
| **Memory Usage** | > 80% | < 40% for 15 min |
| **Request Queue** | > 100 pending | < 10 for 10 min |
| **Response Time P95** | > 500ms for 5 min | < 100ms for 15 min |

---

## 7. Performance Testing Results

### 7.1 Baseline Results (2026-01-09)

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| P95 Latency | TBD | < 500ms | Pending |
| Throughput | TBD | 500 RPS | Pending |
| Error Rate | TBD | < 0.1% | Pending |
| Concurrent Users | TBD | 100 | Pending |

### 7.2 Test History

| Date | Test Type | Duration | Peak Load | P95 | Errors | Notes |
|------|-----------|----------|-----------|-----|--------|-------|
| TBD | Smoke | 5m | 5 users | TBD | TBD | Initial test |

---

## 8. Monitoring During Tests

### 8.1 Key Dashboards

- Grafana: AgentVerse Overview (`/dashboards/agentverse-overview.json`)
- CloudWatch: AWS resources
- Redis: Memory and connection stats
- Celery: Queue depth and worker status

### 8.2 Alerts to Watch

| Alert | Threshold | Action |
|-------|-----------|--------|
| High Error Rate | > 1% for 1 min | Stop test, investigate |
| P95 > 2000ms | 5 min duration | Note, continue unless rising |
| Worker OOM | Any occurrence | Stop test, increase memory |
| Database Connection Exhausted | Any occurrence | Stop test, increase pool |

---

## 9. Post-Test Procedures

### 9.1 Checklist

```
[ ] 1. Stop load test gracefully
[ ] 2. Export test results (HTML report)
[ ] 3. Capture final metrics snapshot
[ ] 4. Document any errors or anomalies
[ ] 5. Clean up test data if needed
[ ] 6. Update performance baseline
[ ] 7. Create tickets for any issues found
[ ] 8. Share results with team
```

### 9.2 Report Template

```markdown
## Load Test Report - [DATE]

### Test Configuration
- Test Type: [smoke/load/stress/spike]
- Duration: [X minutes]
- Peak VUs: [X users]
- Target Host: [environment]

### Results Summary
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| P95 Latency | <500ms | Xms | PASS/FAIL |
| Throughput | 500 RPS | X RPS | PASS/FAIL |
| Error Rate | <0.1% | X% | PASS/FAIL |

### Issues Found
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Recommendation]
2. [Recommendation]

### Next Steps
- [ ] Follow-up item
```

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-09 | Platform Team | Initial version |
