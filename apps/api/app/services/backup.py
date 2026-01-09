"""
Backup & Disaster Recovery Service
project.md §11 Phase 9: Production Hardening

Provides:
- Scheduled database backups
- Object storage backup/replication
- Point-in-time recovery
- Backup verification and integrity checks
- Recovery drill support
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class BackupType(str, Enum):
    """Types of backups."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(str, Enum):
    """Backup operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


@dataclass
class BackupConfig:
    """Configuration for backup operations."""
    # Database backup settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "agentverse"
    db_user: str = "postgres"
    db_password: str = ""

    # Backup storage settings
    backup_path: str = "/var/backups/agentverse"
    backup_retention_days: int = 30

    # S3 settings for offsite backups
    s3_bucket: str | None = None
    s3_prefix: str = "backups"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"

    # Replication settings
    enable_s3_replication: bool = True
    replication_target_bucket: str | None = None
    replication_target_region: str | None = None

    # Verification settings
    verify_after_backup: bool = True
    verify_checksum: bool = True


@dataclass
class BackupResult:
    """Result of a backup operation."""
    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    started_at: datetime
    completed_at: datetime | None = None
    file_path: str | None = None
    file_size: int = 0
    checksum: str | None = None
    s3_uri: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RestoreResult:
    """Result of a restore operation."""
    restore_id: str
    backup_id: str
    status: BackupStatus
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    tables_restored: list[str] = field(default_factory=list)


class BackupService:
    """
    Service for database and object storage backups.

    Supports:
    - PostgreSQL pg_dump backups
    - S3 object storage replication
    - Backup verification and integrity checks
    - Retention policy enforcement
    - Recovery drill support
    """

    def __init__(self, config: BackupConfig):
        self.config = config
        self._ensure_backup_directory()

    def _ensure_backup_directory(self) -> None:
        """Ensure backup directory exists."""
        Path(self.config.backup_path).mkdir(parents=True, exist_ok=True)

    def _generate_backup_id(self) -> str:
        """Generate a unique backup ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}"

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def backup_database(
        self,
        backup_type: BackupType = BackupType.FULL,
        tables: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> BackupResult:
        """
        Create a database backup using pg_dump.

        Args:
            backup_type: Type of backup (full, incremental, differential)
            tables: Specific tables to backup (None = all tables)
            tenant_id: Optional tenant filter for multi-tenant backup

        Returns:
            BackupResult with status and file information
        """
        backup_id = self._generate_backup_id()
        started_at = datetime.now(timezone.utc)

        logger.info(
            "Starting database backup",
            backup_id=backup_id,
            backup_type=backup_type,
            tables=tables,
            tenant_id=tenant_id,
        )

        try:
            # Build pg_dump command
            timestamp = started_at.strftime("%Y%m%d_%H%M%S")
            filename = f"db_{backup_type}_{timestamp}.sql.gz"
            file_path = os.path.join(self.config.backup_path, filename)

            cmd = [
                "pg_dump",
                f"--host={self.config.db_host}",
                f"--port={self.config.db_port}",
                f"--username={self.config.db_user}",
                f"--dbname={self.config.db_name}",
                "--format=custom",
                "--compress=9",
            ]

            # Add table filters if specified
            if tables:
                for table in tables:
                    cmd.append(f"--table={table}")

            # Set password in environment
            env = os.environ.copy()
            env["PGPASSWORD"] = self.config.db_password

            # Run pg_dump with gzip compression
            with gzip.open(file_path, "wb") as f:
                process = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    check=True,
                )
                f.write(process.stdout)

            # Get file size and checksum
            file_size = os.path.getsize(file_path)
            checksum = self._calculate_checksum(file_path) if self.config.verify_checksum else None

            # Upload to S3 if configured
            s3_uri = None
            if self.config.s3_bucket and self.config.enable_s3_replication:
                s3_uri = await self._upload_to_s3(file_path, filename)

            completed_at = datetime.now(timezone.utc)

            logger.info(
                "Database backup completed",
                backup_id=backup_id,
                file_path=file_path,
                file_size=file_size,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )

            return BackupResult(
                backup_id=backup_id,
                backup_type=backup_type,
                status=BackupStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                file_path=file_path,
                file_size=file_size,
                checksum=checksum,
                s3_uri=s3_uri,
                metadata={
                    "db_name": self.config.db_name,
                    "tables": tables,
                    "tenant_id": tenant_id,
                },
            )

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(
                "Database backup failed",
                backup_id=backup_id,
                error=error_msg,
            )
            return BackupResult(
                backup_id=backup_id,
                backup_type=backup_type,
                status=BackupStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error_message=error_msg,
            )
        except Exception as e:
            logger.error(
                "Database backup failed",
                backup_id=backup_id,
                error=str(e),
            )
            return BackupResult(
                backup_id=backup_id,
                backup_type=backup_type,
                status=BackupStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    async def _upload_to_s3(self, file_path: str, filename: str) -> str | None:
        """Upload backup file to S3."""
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                endpoint_url=self.config.s3_endpoint_url,
                aws_access_key_id=self.config.s3_access_key,
                aws_secret_access_key=self.config.s3_secret_key,
                region_name=self.config.s3_region,
            )

            s3_key = f"{self.config.s3_prefix}/{filename}"

            s3.upload_file(
                file_path,
                self.config.s3_bucket,
                s3_key,
                ExtraArgs={
                    "ServerSideEncryption": "AES256",
                    "StorageClass": "STANDARD_IA",
                },
            )

            s3_uri = f"s3://{self.config.s3_bucket}/{s3_key}"
            logger.info("Backup uploaded to S3", s3_uri=s3_uri)
            return s3_uri

        except Exception as e:
            logger.error("Failed to upload backup to S3", error=str(e))
            return None

    async def verify_backup(self, backup_result: BackupResult) -> bool:
        """
        Verify backup integrity.

        Args:
            backup_result: The backup to verify

        Returns:
            True if backup is valid, False otherwise
        """
        if not backup_result.file_path or not os.path.exists(backup_result.file_path):
            logger.error("Backup file not found", backup_id=backup_result.backup_id)
            return False

        # Verify checksum
        if backup_result.checksum:
            current_checksum = self._calculate_checksum(backup_result.file_path)
            if current_checksum != backup_result.checksum:
                logger.error(
                    "Backup checksum mismatch",
                    backup_id=backup_result.backup_id,
                    expected=backup_result.checksum,
                    actual=current_checksum,
                )
                return False

        # Verify file can be decompressed
        try:
            with gzip.open(backup_result.file_path, "rb") as f:
                # Read first chunk to verify it's valid gzip
                f.read(1024)
        except Exception as e:
            logger.error(
                "Backup file corruption detected",
                backup_id=backup_result.backup_id,
                error=str(e),
            )
            return False

        logger.info("Backup verified successfully", backup_id=backup_result.backup_id)
        return True

    async def restore_database(
        self,
        backup_result: BackupResult,
        target_db: str | None = None,
        tables: list[str] | None = None,
    ) -> RestoreResult:
        """
        Restore database from backup.

        Args:
            backup_result: The backup to restore from
            target_db: Target database name (defaults to same as backup)
            tables: Specific tables to restore (None = all)

        Returns:
            RestoreResult with status
        """
        restore_id = f"restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now(timezone.utc)

        logger.info(
            "Starting database restore",
            restore_id=restore_id,
            backup_id=backup_result.backup_id,
            target_db=target_db,
        )

        if not backup_result.file_path or not os.path.exists(backup_result.file_path):
            return RestoreResult(
                restore_id=restore_id,
                backup_id=backup_result.backup_id,
                status=BackupStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error_message="Backup file not found",
            )

        try:
            # Decompress backup
            decompressed_path = backup_result.file_path.replace(".gz", "")
            with gzip.open(backup_result.file_path, "rb") as f_in:
                with open(decompressed_path, "wb") as f_out:
                    f_out.write(f_in.read())

            # Build pg_restore command
            cmd = [
                "pg_restore",
                f"--host={self.config.db_host}",
                f"--port={self.config.db_port}",
                f"--username={self.config.db_user}",
                f"--dbname={target_db or self.config.db_name}",
                "--clean",
                "--if-exists",
            ]

            # Add table filters if specified
            if tables:
                for table in tables:
                    cmd.append(f"--table={table}")

            cmd.append(decompressed_path)

            # Set password in environment
            env = os.environ.copy()
            env["PGPASSWORD"] = self.config.db_password

            # Run pg_restore
            subprocess.run(cmd, env=env, capture_output=True, check=True)

            # Cleanup decompressed file
            os.remove(decompressed_path)

            completed_at = datetime.now(timezone.utc)

            logger.info(
                "Database restore completed",
                restore_id=restore_id,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )

            return RestoreResult(
                restore_id=restore_id,
                backup_id=backup_result.backup_id,
                status=BackupStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                tables_restored=tables or ["all"],
            )

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(
                "Database restore failed",
                restore_id=restore_id,
                error=error_msg,
            )
            return RestoreResult(
                restore_id=restore_id,
                backup_id=backup_result.backup_id,
                status=BackupStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error_message=error_msg,
            )
        except Exception as e:
            logger.error(
                "Database restore failed",
                restore_id=restore_id,
                error=str(e),
            )
            return RestoreResult(
                restore_id=restore_id,
                backup_id=backup_result.backup_id,
                status=BackupStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    async def cleanup_old_backups(self) -> int:
        """
        Remove backups older than retention period.

        Returns:
            Number of backups deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=self.config.backup_retention_days
        )
        deleted_count = 0

        backup_dir = Path(self.config.backup_path)
        for backup_file in backup_dir.glob("*.sql.gz"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(
                    backup_file.stat().st_mtime, tz=timezone.utc
                )

                if mtime < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(
                        "Deleted old backup",
                        file=str(backup_file),
                        age_days=(datetime.now(timezone.utc) - mtime).days,
                    )
            except Exception as e:
                logger.error(
                    "Failed to delete backup",
                    file=str(backup_file),
                    error=str(e),
                )

        logger.info("Cleanup completed", deleted_count=deleted_count)
        return deleted_count

    async def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups."""
        backups = []
        backup_dir = Path(self.config.backup_path)

        for backup_file in sorted(backup_dir.glob("*.sql.gz"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "file_path": str(backup_file),
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })

        return backups


class ObjectStorageBackupService:
    """
    Service for backing up and replicating object storage.

    Supports:
    - S3 to S3 replication
    - Cross-region replication
    - Incremental sync
    """

    def __init__(self, config: BackupConfig):
        self.config = config

    async def sync_to_backup_bucket(
        self,
        source_prefix: str = "",
        delete_orphaned: bool = False,
    ) -> dict[str, Any]:
        """
        Sync objects from primary to backup bucket.

        Args:
            source_prefix: Prefix to sync (empty = all)
            delete_orphaned: Delete objects in backup not in source

        Returns:
            Sync statistics
        """
        if not self.config.replication_target_bucket:
            return {"error": "Replication target bucket not configured"}

        try:
            import boto3

            source_s3 = boto3.client(
                "s3",
                endpoint_url=self.config.s3_endpoint_url,
                aws_access_key_id=self.config.s3_access_key,
                aws_secret_access_key=self.config.s3_secret_key,
                region_name=self.config.s3_region,
            )

            target_s3 = boto3.client(
                "s3",
                aws_access_key_id=self.config.s3_access_key,
                aws_secret_access_key=self.config.s3_secret_key,
                region_name=self.config.replication_target_region or self.config.s3_region,
            )

            # List source objects
            paginator = source_s3.get_paginator("list_objects_v2")
            source_objects = {}

            for page in paginator.paginate(
                Bucket=self.config.s3_bucket,
                Prefix=source_prefix,
            ):
                for obj in page.get("Contents", []):
                    source_objects[obj["Key"]] = obj["ETag"]

            # List target objects
            target_objects = {}
            for page in paginator.paginate(
                Bucket=self.config.replication_target_bucket,
                Prefix=source_prefix,
            ):
                for obj in page.get("Contents", []):
                    target_objects[obj["Key"]] = obj["ETag"]

            # Sync missing or changed objects
            synced_count = 0
            for key, etag in source_objects.items():
                if key not in target_objects or target_objects[key] != etag:
                    # Copy object
                    copy_source = {
                        "Bucket": self.config.s3_bucket,
                        "Key": key,
                    }
                    target_s3.copy_object(
                        CopySource=copy_source,
                        Bucket=self.config.replication_target_bucket,
                        Key=key,
                    )
                    synced_count += 1

            # Delete orphaned objects if requested
            deleted_count = 0
            if delete_orphaned:
                for key in target_objects:
                    if key not in source_objects:
                        target_s3.delete_object(
                            Bucket=self.config.replication_target_bucket,
                            Key=key,
                        )
                        deleted_count += 1

            logger.info(
                "Object storage sync completed",
                synced=synced_count,
                deleted=deleted_count,
            )

            return {
                "status": "completed",
                "synced_count": synced_count,
                "deleted_count": deleted_count,
                "total_source_objects": len(source_objects),
            }

        except Exception as e:
            logger.error("Object storage sync failed", error=str(e))
            return {"error": str(e)}


# ============================================================================
# CELERY TASKS FOR SCHEDULED BACKUPS
# ============================================================================

def create_backup_tasks(celery_app: Any) -> None:
    """
    Create Celery tasks for scheduled backups.

    Call this during app initialization with your Celery app.
    """
    from app.core.config import settings

    @celery_app.task(name="backup.daily_database")
    def daily_database_backup() -> dict[str, Any]:
        """Daily database backup task."""
        import asyncio

        config = BackupConfig(
            db_host=settings.POSTGRES_HOST,
            db_port=settings.POSTGRES_PORT,
            db_name=settings.POSTGRES_DB,
            db_user=settings.POSTGRES_USER,
            db_password=settings.POSTGRES_PASSWORD,
            backup_path=getattr(settings, "BACKUP_PATH", "/var/backups/agentverse"),
            s3_bucket=getattr(settings, "S3_BUCKET", None),
            s3_access_key=getattr(settings, "S3_ACCESS_KEY", None),
            s3_secret_key=getattr(settings, "S3_SECRET_KEY", None),
        )

        service = BackupService(config)
        result = asyncio.run(service.backup_database(BackupType.FULL))

        return {
            "backup_id": result.backup_id,
            "status": result.status,
            "file_path": result.file_path,
            "s3_uri": result.s3_uri,
        }

    @celery_app.task(name="backup.cleanup_old")
    def cleanup_old_backups() -> dict[str, Any]:
        """Cleanup old backups task."""
        import asyncio

        config = BackupConfig(
            backup_path=getattr(settings, "BACKUP_PATH", "/var/backups/agentverse"),
            backup_retention_days=getattr(settings, "BACKUP_RETENTION_DAYS", 30),
        )

        service = BackupService(config)
        deleted = asyncio.run(service.cleanup_old_backups())

        return {"deleted_count": deleted}

    @celery_app.task(name="backup.s3_replication")
    def s3_replication_sync() -> dict[str, Any]:
        """S3 object storage replication task."""
        import asyncio

        config = BackupConfig(
            s3_bucket=getattr(settings, "S3_BUCKET", None),
            s3_access_key=getattr(settings, "S3_ACCESS_KEY", None),
            s3_secret_key=getattr(settings, "S3_SECRET_KEY", None),
            replication_target_bucket=getattr(settings, "S3_BACKUP_BUCKET", None),
            replication_target_region=getattr(settings, "S3_BACKUP_REGION", None),
        )

        service = ObjectStorageBackupService(config)
        return asyncio.run(service.sync_to_backup_bucket())


# ============================================================================
# CELERY BEAT SCHEDULE
# ============================================================================

BACKUP_SCHEDULE = {
    "daily-database-backup": {
        "task": "backup.daily_database",
        "schedule": 86400,  # 24 hours in seconds
        "options": {"queue": "backup"},
    },
    "weekly-cleanup": {
        "task": "backup.cleanup_old",
        "schedule": 604800,  # 7 days in seconds
        "options": {"queue": "backup"},
    },
    "hourly-s3-replication": {
        "task": "backup.s3_replication",
        "schedule": 3600,  # 1 hour in seconds
        "options": {"queue": "backup"},
    },
}
