# AgentVerse Disaster Recovery Runbook

**Document Version:** 1.0
**Last Updated:** 2026-01-09
**Owner:** Platform Team

---

## 1. Overview

This document describes the disaster recovery procedures for the AgentVerse platform. It covers:
- Database backup and restore procedures
- Object storage replication
- Recovery time objectives (RTO) and recovery point objectives (RPO)
- Drill schedules and procedures

---

## 2. Recovery Objectives

| Metric | Target | Current |
|--------|--------|---------|
| **RPO** (Recovery Point Objective) | 24 hours | 24 hours (daily backups) |
| **RTO** (Recovery Time Objective) | 4 hours | ~2 hours (tested) |
| **Backup Retention** | 30 days | 30 days |

---

## 3. Backup Strategy

### 3.1 Database Backups

| Type | Schedule | Storage | Retention |
|------|----------|---------|-----------|
| Full Database | Daily at 02:00 UTC | Local + S3 | 30 days |
| Transaction Logs | Continuous (WAL) | S3 | 7 days |

**Backup Locations:**
- Local: `/var/backups/agentverse/`
- S3 Primary: `s3://agentverse-backups/db/`
- S3 Replica: `s3://agentverse-backups-dr/db/` (cross-region)

### 3.2 Object Storage Backups

| Type | Schedule | Replication |
|------|----------|-------------|
| Telemetry blobs | Continuous | Cross-region |
| Snapshots | On-demand | Cross-region |
| Exports | On-demand | Same-region |

**Replication:**
- Primary: `us-east-1`
- DR Region: `us-west-2`
- Sync frequency: Hourly

---

## 4. Recovery Procedures

### 4.1 Database Recovery

#### Scenario A: Point-in-Time Recovery (Corruption/Accidental Deletion)

```bash
# 1. Stop the API service
sudo systemctl stop agentverse-api

# 2. List available backups
python -c "
from app.services.backup import BackupService, BackupConfig
import asyncio

config = BackupConfig()
service = BackupService(config)
backups = asyncio.run(service.list_backups())
for b in backups:
    print(f\"{b['filename']} - {b['size']} bytes - {b['created_at']}\")
"

# 3. Select and restore backup
python -c "
from app.services.backup import BackupService, BackupConfig, BackupResult, BackupType, BackupStatus
from datetime import datetime, timezone
import asyncio

config = BackupConfig()
service = BackupService(config)

# Create a BackupResult object for the selected backup
backup = BackupResult(
    backup_id='selected_backup',
    backup_type=BackupType.FULL,
    status=BackupStatus.COMPLETED,
    started_at=datetime.now(timezone.utc),
    file_path='/var/backups/agentverse/db_full_YYYYMMDD_HHMMSS.sql.gz'
)

# Restore
result = asyncio.run(service.restore_database(backup))
print(f'Restore status: {result.status}')
"

# 4. Verify restore
psql -U postgres -d agentverse -c "SELECT COUNT(*) FROM nodes;"
psql -U postgres -d agentverse -c "SELECT COUNT(*) FROM runs;"

# 5. Restart API service
sudo systemctl start agentverse-api

# 6. Run smoke tests
curl http://localhost:8000/health/ready
```

#### Scenario B: Full Database Failure (Server Loss)

```bash
# 1. Provision new PostgreSQL server
# (Use your cloud provider's console or CLI)

# 2. Download latest backup from S3
aws s3 cp s3://agentverse-backups/db/latest.sql.gz /var/backups/agentverse/

# 3. Create database
psql -U postgres -c "CREATE DATABASE agentverse;"

# 4. Restore from backup
gunzip -c /var/backups/agentverse/latest.sql.gz | psql -U postgres -d agentverse

# 5. Update connection strings
# Edit /etc/agentverse/config.env with new database host

# 6. Restart services
sudo systemctl restart agentverse-api
sudo systemctl restart agentverse-worker
```

### 4.2 Object Storage Recovery

#### Scenario: Accidental Bucket Deletion

```bash
# 1. List objects in backup bucket
aws s3 ls s3://agentverse-backups-dr/telemetry/ --recursive

# 2. Sync from backup bucket to new primary bucket
aws s3 sync s3://agentverse-backups-dr/ s3://agentverse-primary/ --source-region us-west-2

# 3. Update application config with new bucket name
# Edit S3_BUCKET in environment variables

# 4. Restart services
sudo systemctl restart agentverse-api
```

### 4.3 Full Platform Recovery

For complete platform failure (all services down):

1. **Infrastructure (15 min)**
   - Provision new VPC/network
   - Deploy PostgreSQL RDS
   - Deploy Redis ElastiCache
   - Deploy EKS cluster or EC2 instances

2. **Database Recovery (30 min)**
   - Download latest backup from S3 DR bucket
   - Restore to new PostgreSQL
   - Verify data integrity

3. **Object Storage (15 min)**
   - Update S3 bucket configurations
   - Verify replication status
   - Sync any missing objects

4. **Application Deployment (45 min)**
   - Deploy API containers
   - Deploy worker containers
   - Configure load balancer
   - Update DNS records

5. **Verification (15 min)**
   - Run health checks
   - Execute smoke tests
   - Verify simulation execution

**Total Estimated Time: ~2 hours**

---

## 5. Recovery Drill Schedule

| Drill Type | Frequency | Duration | Participants |
|------------|-----------|----------|--------------|
| Database Restore Test | Monthly | 2 hours | Platform Team |
| Full DR Test | Quarterly | 4 hours | All Teams |
| Tabletop Exercise | Bi-annually | 2 hours | Leadership + Platform |

### 5.1 Monthly Database Drill Checklist

```
[ ] 1. Schedule drill (notify stakeholders 1 week prior)
[ ] 2. Create test database (don't use production)
[ ] 3. Trigger manual backup
[ ] 4. Verify backup completed successfully
[ ] 5. Stop test database
[ ] 6. Restore from backup
[ ] 7. Verify data integrity:
    [ ] Row counts match
    [ ] Sample queries return expected data
    [ ] Foreign key constraints valid
[ ] 8. Document any issues
[ ] 9. Update runbook if needed
[ ] 10. Report results to stakeholders
```

### 5.2 Quarterly Full DR Drill Checklist

```
[ ] 1. Schedule drill (2 weeks notice)
[ ] 2. Create isolated DR environment
[ ] 3. Execute database recovery
[ ] 4. Execute object storage sync
[ ] 5. Deploy application in DR environment
[ ] 6. Execute test workload:
    [ ] Create project
    [ ] Upload personas
    [ ] Run simulation
    [ ] Generate report
[ ] 7. Measure RTO (target: < 4 hours)
[ ] 8. Verify RPO (data loss < 24 hours)
[ ] 9. Document findings
[ ] 10. Tear down DR environment
[ ] 11. Update procedures based on learnings
```

---

## 6. Monitoring & Alerts

### 6.1 Backup Monitoring

| Metric | Alert Threshold | Severity |
|--------|-----------------|----------|
| Backup job failure | Any failure | Critical |
| Backup size anomaly | > 50% change | Warning |
| Backup age | > 25 hours | Critical |
| S3 replication lag | > 2 hours | Warning |

### 6.2 Prometheus Alerts

```yaml
groups:
  - name: backup_alerts
    rules:
      - alert: BackupFailed
        expr: agentverse_backup_last_success_timestamp < (time() - 86400)
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database backup has not succeeded in 24 hours"

      - alert: BackupSizeAnomaly
        expr: |
          abs(agentverse_backup_size_bytes - avg_over_time(agentverse_backup_size_bytes[7d]))
          / avg_over_time(agentverse_backup_size_bytes[7d]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Backup size differs by > 50% from weekly average"

      - alert: S3ReplicationLag
        expr: agentverse_s3_replication_lag_seconds > 7200
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "S3 replication is lagging by more than 2 hours"
```

---

## 7. Contact Information

| Role | Name | Contact |
|------|------|---------|
| Primary On-Call | Platform Team | pager@agentverse.ai |
| Secondary On-Call | SRE Team | sre@agentverse.ai |
| Database Admin | DBA Team | dba@agentverse.ai |
| Management Escalation | Platform Lead | lead@agentverse.ai |

---

## 8. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-09 | Platform Team | Initial version |
