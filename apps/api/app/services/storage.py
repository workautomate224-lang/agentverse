"""
Object Storage Service
Reference: project.md §5.4, §8.1, §8.4

Provides S3-compatible object storage for:
- Telemetry blobs (replay data)
- Snapshots (world state at specific points)
- Large artifacts

Supports:
- AWS S3
- MinIO (self-hosted S3-compatible)
- DigitalOcean Spaces
- Local filesystem (for development)

Key features:
- Tenant isolation via path prefixes
- Signed URLs for secure downloads
- Compression support (gzip, zstd)
"""

import gzip
import hashlib
import io
import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

from app.core.config import settings


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class StorageNotFoundError(StorageError):
    """Raised when a requested object is not found."""
    pass


class StorageRef:
    """
    Reference to a stored object.
    Used as the storage_ref field in database records.
    """

    def __init__(
        self,
        bucket: str,
        key: str,
        size_bytes: int,
        content_type: str = "application/octet-stream",
        checksum: Optional[str] = None,
        compression: str = "none",
        created_at: Optional[str] = None,
    ):
        self.bucket = bucket
        self.key = key
        self.size_bytes = size_bytes
        self.content_type = content_type
        self.checksum = checksum
        self.compression = compression
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "bucket": self.bucket,
            "key": self.key,
            "size_bytes": self.size_bytes,
            "content_type": self.content_type,
            "checksum": self.checksum,
            "compression": self.compression,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StorageRef":
        """Create from dictionary."""
        return cls(
            bucket=data["bucket"],
            key=data["key"],
            size_bytes=data["size_bytes"],
            content_type=data.get("content_type", "application/octet-stream"),
            checksum=data.get("checksum"),
            compression=data.get("compression", "none"),
            created_at=data.get("created_at"),
        )


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> StorageRef:
        """Upload an object to storage."""
        pass

    @abstractmethod
    async def get_object(self, key: str) -> bytes:
        """Download an object from storage."""
        pass

    @abstractmethod
    async def delete_object(self, key: str) -> bool:
        """Delete an object from storage."""
        pass

    @abstractmethod
    async def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        pass

    @abstractmethod
    async def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        """Generate a signed URL for direct access."""
        pass

    @abstractmethod
    async def list_objects(
        self,
        prefix: str,
        max_keys: int = 1000,
    ) -> list[str]:
        """List objects with a given prefix."""
        pass


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage backend.
    Useful for development and testing.
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, key: str) -> Path:
        """Get full filesystem path for a key."""
        # Ensure key doesn't escape base path
        safe_key = key.lstrip("/").replace("..", "")
        return self.base_path / safe_key

    async def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> StorageRef:
        """Upload an object to local storage."""
        path = self._get_full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            content = data
        else:
            content = data.read()

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Write content
        path.write_bytes(content)

        # Write metadata
        meta_path = path.with_suffix(path.suffix + ".meta")
        meta_data = {
            "content_type": content_type,
            "checksum": checksum,
            "size_bytes": len(content),
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }
        meta_path.write_text(json.dumps(meta_data))

        return StorageRef(
            bucket="local",
            key=key,
            size_bytes=len(content),
            content_type=content_type,
            checksum=checksum,
        )

    async def get_object(self, key: str) -> bytes:
        """Download an object from local storage."""
        path = self._get_full_path(key)
        if not path.exists():
            raise StorageNotFoundError(f"Object not found: {key}")
        return path.read_bytes()

    async def delete_object(self, key: str) -> bool:
        """Delete an object from local storage."""
        path = self._get_full_path(key)
        meta_path = path.with_suffix(path.suffix + ".meta")

        deleted = False
        if path.exists():
            path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()

        return deleted

    async def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        return self._get_full_path(key).exists()

    async def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        """
        Generate a 'signed URL' for local storage.
        In local mode, this returns a file:// URL (for development only).
        """
        path = self._get_full_path(key)
        return f"file://{path.absolute()}"

    async def list_objects(
        self,
        prefix: str,
        max_keys: int = 1000,
    ) -> list[str]:
        """List objects with a given prefix."""
        prefix_path = self._get_full_path(prefix)
        base = prefix_path.parent
        pattern = prefix_path.name + "*"

        results = []
        if base.exists():
            for path in base.glob(pattern):
                if path.suffix != ".meta":
                    # Convert back to key
                    rel_path = path.relative_to(self.base_path)
                    results.append(str(rel_path))
                    if len(results) >= max_keys:
                        break

        return results


class S3StorageBackend(StorageBackend):
    """
    S3-compatible storage backend.
    Works with AWS S3, MinIO, DigitalOcean Spaces, etc.
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoint_url: Optional[str] = None,
        use_ssl: bool = True,
    ):
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        self.use_ssl = use_ssl

        # Lazy import boto3 (optional dependency)
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            )

        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            use_ssl=use_ssl,
            config=Config(signature_version="s3v4"),
        )

    async def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> StorageRef:
        """Upload an object to S3."""
        if isinstance(data, bytes):
            content = data
            body = io.BytesIO(content)
        else:
            content = data.read()
            body = io.BytesIO(content)

        checksum = hashlib.sha256(content).hexdigest()

        extra_args = {
            "ContentType": content_type,
        }
        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            **extra_args,
        )

        return StorageRef(
            bucket=self.bucket,
            key=key,
            size_bytes=len(content),
            content_type=content_type,
            checksum=checksum,
        )

    async def get_object(self, key: str) -> bytes:
        """Download an object from S3."""
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except self._client.exceptions.NoSuchKey:
            raise StorageNotFoundError(f"Object not found: {key}")

    async def delete_object(self, key: str) -> bool:
        """Delete an object from S3."""
        self._client.delete_object(Bucket=self.bucket, Key=key)
        return True

    async def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False

    async def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        """Generate a signed URL for direct access."""
        client_method = "get_object" if method == "GET" else "put_object"
        return self._client.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    async def list_objects(
        self,
        prefix: str,
        max_keys: int = 1000,
    ) -> list[str]:
        """List objects with a given prefix."""
        response = self._client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
        return [obj["Key"] for obj in response.get("Contents", [])]


class StorageService:
    """
    High-level storage service with tenant isolation.
    Reference: project.md §8.1 (tenant isolation via path prefixes)
    """

    def __init__(self, backend: StorageBackend):
        self.backend = backend

    def _build_key(
        self,
        tenant_id: str,
        artifact_type: str,
        artifact_id: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        Build a storage key with tenant isolation.
        Format: {prefix}/{tenant_id}/{artifact_id}/{filename}
        """
        prefix_map = {
            "telemetry": settings.STORAGE_TELEMETRY_PREFIX,
            "snapshot": settings.STORAGE_SNAPSHOTS_PREFIX,
            "artifact": settings.STORAGE_ARTIFACTS_PREFIX,
        }
        prefix = prefix_map.get(artifact_type, "other")

        parts = [prefix, tenant_id, artifact_id]
        if filename:
            parts.append(filename)

        return "/".join(parts)

    async def store_telemetry(
        self,
        tenant_id: str,
        telemetry_id: str,
        data: dict,
        compress: bool = True,
    ) -> StorageRef:
        """
        Store telemetry data.
        Reference: project.md §6.8
        """
        key = self._build_key(tenant_id, "telemetry", telemetry_id, "data.json")

        # Serialize to JSON
        json_data = json.dumps(data, separators=(",", ":")).encode("utf-8")

        # Optionally compress
        if compress:
            compressed = gzip.compress(json_data)
            ref = await self.backend.put_object(
                key=key,
                data=compressed,
                content_type="application/gzip",
                metadata={"original_size": len(json_data)},
            )
            ref.compression = "gzip"
        else:
            ref = await self.backend.put_object(
                key=key,
                data=json_data,
                content_type="application/json",
            )

        return ref

    async def get_telemetry(self, storage_ref: StorageRef) -> dict:
        """Retrieve telemetry data."""
        data = await self.backend.get_object(storage_ref.key)

        # Decompress if needed
        if storage_ref.compression == "gzip":
            data = gzip.decompress(data)

        return json.loads(data.decode("utf-8"))

    async def store_snapshot(
        self,
        tenant_id: str,
        node_id: str,
        tick: int,
        data: dict,
        compress: bool = True,
    ) -> StorageRef:
        """
        Store a world state snapshot.
        """
        snapshot_id = f"tick_{tick}"
        key = self._build_key(tenant_id, "snapshot", node_id, f"{snapshot_id}.json")

        json_data = json.dumps(data, separators=(",", ":")).encode("utf-8")

        if compress:
            compressed = gzip.compress(json_data)
            ref = await self.backend.put_object(
                key=key,
                data=compressed,
                content_type="application/gzip",
            )
            ref.compression = "gzip"
        else:
            ref = await self.backend.put_object(
                key=key,
                data=json_data,
                content_type="application/json",
            )

        return ref

    async def get_snapshot(self, storage_ref: StorageRef) -> dict:
        """Retrieve a snapshot."""
        data = await self.backend.get_object(storage_ref.key)

        if storage_ref.compression == "gzip":
            data = gzip.decompress(data)

        return json.loads(data.decode("utf-8"))

    async def store_artifact(
        self,
        tenant_id: str,
        artifact_type: str,
        artifact_id: str,
        filename: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
    ) -> StorageRef:
        """Store a generic artifact."""
        key = self._build_key(tenant_id, artifact_type, artifact_id, filename)
        return await self.backend.put_object(key, data, content_type)

    async def get_signed_download_url(
        self,
        storage_ref: StorageRef,
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Get a signed URL for downloading.
        Reference: project.md §8.4 (short-lived signed URLs)
        """
        expiry = expires_in or settings.STORAGE_URL_EXPIRATION_SECONDS
        return await self.backend.get_signed_url(storage_ref.key, expiry, "GET")

    async def delete_artifact(self, storage_ref: StorageRef) -> bool:
        """Delete an artifact."""
        return await self.backend.delete_object(storage_ref.key)

    async def list_telemetry(
        self,
        tenant_id: str,
        max_results: int = 100,
    ) -> list[str]:
        """List telemetry objects for a tenant."""
        prefix = f"{settings.STORAGE_TELEMETRY_PREFIX}/{tenant_id}/"
        return await self.backend.list_objects(prefix, max_results)


def create_storage_service() -> StorageService:
    """
    Factory function to create the storage service based on configuration.
    """
    backend_type = settings.STORAGE_BACKEND.lower()

    if backend_type == "local":
        backend = LocalStorageBackend(settings.STORAGE_LOCAL_PATH)
    elif backend_type == "s3":
        backend = S3StorageBackend(
            bucket=settings.STORAGE_BUCKET,
            region=settings.STORAGE_REGION,
            access_key=settings.STORAGE_ACCESS_KEY,
            secret_key=settings.STORAGE_SECRET_KEY,
            endpoint_url=settings.STORAGE_ENDPOINT_URL,
            use_ssl=settings.STORAGE_USE_SSL,
        )
    else:
        raise ValueError(f"Unsupported storage backend: {backend_type}")

    return StorageService(backend)


# Singleton instance (lazy initialized)
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = create_storage_service()
    return _storage_service
