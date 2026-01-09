"""
Secret Management Service
Reference: project.md §8.4, §11 Phase 9

Provides:
- Secure secret storage abstraction (environment, AWS Secrets Manager, Vault)
- Key rotation mechanism
- Secret validation and health checks
- Audit logging for secret access
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
import hashlib
import hmac
import os
import re
import secrets
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class SecretBackend(str, Enum):
    """Supported secret storage backends."""
    ENVIRONMENT = "environment"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    HASHICORP_VAULT = "hashicorp_vault"
    FILE = "file"  # For development only


class SecretType(str, Enum):
    """Types of secrets for categorization."""
    JWT_KEY = "jwt_key"
    DATABASE_PASSWORD = "database_password"
    API_KEY = "api_key"
    STORAGE_KEY = "storage_key"
    ENCRYPTION_KEY = "encryption_key"
    WEBHOOK_SECRET = "webhook_secret"


@dataclass
class SecretMetadata:
    """Metadata about a secret for rotation tracking."""
    name: str
    secret_type: SecretType
    created_at: datetime
    rotated_at: Optional[datetime] = None
    rotation_period_days: int = 90
    last_accessed_at: Optional[datetime] = None
    access_count: int = 0
    version: int = 1

    @property
    def needs_rotation(self) -> bool:
        """Check if secret needs rotation based on age."""
        reference_date = self.rotated_at or self.created_at
        age = datetime.utcnow() - reference_date
        return age > timedelta(days=self.rotation_period_days)

    @property
    def days_until_rotation(self) -> int:
        """Days until rotation is needed."""
        reference_date = self.rotated_at or self.created_at
        age = datetime.utcnow() - reference_date
        return max(0, self.rotation_period_days - age.days)


@dataclass
class SecretValue:
    """Secure wrapper for secret values with masking."""
    _value: str
    metadata: SecretMetadata

    def __repr__(self) -> str:
        """Never show actual value in repr."""
        return f"SecretValue(name={self.metadata.name}, type={self.metadata.secret_type.value}, masked=True)"

    def __str__(self) -> str:
        """Never show actual value in str."""
        return f"[SECRET:{self.metadata.name}]"

    def get_value(self) -> str:
        """Get the actual secret value. Use sparingly."""
        self.metadata.last_accessed_at = datetime.utcnow()
        self.metadata.access_count += 1
        return self._value

    def get_masked(self, show_chars: int = 4) -> str:
        """Get masked version for logging."""
        if len(self._value) <= show_chars:
            return "*" * len(self._value)
        return self._value[:show_chars] + "*" * (len(self._value) - show_chars)


class SecretBackendBase(ABC):
    """Abstract base class for secret backends."""

    @abstractmethod
    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve a secret value."""
        pass

    @abstractmethod
    def set_secret(self, name: str, value: str) -> bool:
        """Store a secret value."""
        pass

    @abstractmethod
    def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        pass

    @abstractmethod
    def list_secrets(self) -> list[str]:
        """List all secret names."""
        pass


class EnvironmentSecretBackend(SecretBackendBase):
    """Environment variable-based secret backend (for development/simple deployments)."""

    def __init__(self, prefix: str = "AGENTVERSE_"):
        self.prefix = prefix

    def get_secret(self, name: str) -> Optional[str]:
        """Get secret from environment variable."""
        env_name = f"{self.prefix}{name.upper()}"
        return os.environ.get(env_name)

    def set_secret(self, name: str, value: str) -> bool:
        """Set environment variable (runtime only)."""
        env_name = f"{self.prefix}{name.upper()}"
        os.environ[env_name] = value
        return True

    def delete_secret(self, name: str) -> bool:
        """Delete environment variable."""
        env_name = f"{self.prefix}{name.upper()}"
        if env_name in os.environ:
            del os.environ[env_name]
            return True
        return False

    def list_secrets(self) -> list[str]:
        """List all secrets with our prefix."""
        return [
            key.replace(self.prefix, "").lower()
            for key in os.environ.keys()
            if key.startswith(self.prefix)
        ]


class AWSSecretsManagerBackend(SecretBackendBase):
    """AWS Secrets Manager backend for production deployments."""

    def __init__(
        self,
        region: str = "us-east-1",
        prefix: str = "agentverse/",
    ):
        self.region = region
        self.prefix = prefix
        self._client = None

    @property
    def client(self):
        """Lazy-load boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "secretsmanager",
                    region_name=self.region,
                )
            except ImportError:
                raise ImportError("boto3 required for AWS Secrets Manager backend")
        return self._client

    def get_secret(self, name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            response = self.client.get_secret_value(
                SecretId=f"{self.prefix}{name}",
            )
            return response.get("SecretString")
        except self.client.exceptions.ResourceNotFoundException:
            return None
        except Exception as e:
            logger.error(f"Failed to get secret {name}: {type(e).__name__}")
            return None

    def set_secret(self, name: str, value: str) -> bool:
        """Store or update secret in AWS Secrets Manager."""
        secret_id = f"{self.prefix}{name}"
        try:
            try:
                self.client.update_secret(
                    SecretId=secret_id,
                    SecretString=value,
                )
            except self.client.exceptions.ResourceNotFoundException:
                self.client.create_secret(
                    Name=secret_id,
                    SecretString=value,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {name}: {type(e).__name__}")
            return False

    def delete_secret(self, name: str) -> bool:
        """Delete secret from AWS Secrets Manager."""
        try:
            self.client.delete_secret(
                SecretId=f"{self.prefix}{name}",
                ForceDeleteWithoutRecovery=False,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {type(e).__name__}")
            return False

    def list_secrets(self) -> list[str]:
        """List all secrets with our prefix."""
        try:
            paginator = self.client.get_paginator("list_secrets")
            secrets = []
            for page in paginator.paginate():
                for secret in page["SecretList"]:
                    name = secret["Name"]
                    if name.startswith(self.prefix):
                        secrets.append(name.replace(self.prefix, ""))
            return secrets
        except Exception as e:
            logger.error(f"Failed to list secrets: {type(e).__name__}")
            return []


class HashiCorpVaultBackend(SecretBackendBase):
    """HashiCorp Vault backend for enterprise deployments."""

    def __init__(
        self,
        url: str = "http://localhost:8200",
        token: Optional[str] = None,
        mount_point: str = "secret",
        path_prefix: str = "agentverse/",
    ):
        self.url = url
        self.token = token or os.environ.get("VAULT_TOKEN")
        self.mount_point = mount_point
        self.path_prefix = path_prefix
        self._client = None

    @property
    def client(self):
        """Lazy-load hvac client."""
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(url=self.url, token=self.token)
            except ImportError:
                raise ImportError("hvac required for HashiCorp Vault backend")
        return self._client

    def get_secret(self, name: str) -> Optional[str]:
        """Get secret from Vault."""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                mount_point=self.mount_point,
                path=f"{self.path_prefix}{name}",
            )
            return response["data"]["data"].get("value")
        except Exception as e:
            logger.error(f"Failed to get secret {name} from Vault: {type(e).__name__}")
            return None

    def set_secret(self, name: str, value: str) -> bool:
        """Store secret in Vault."""
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.mount_point,
                path=f"{self.path_prefix}{name}",
                secret={"value": value},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {name} in Vault: {type(e).__name__}")
            return False

    def delete_secret(self, name: str) -> bool:
        """Delete secret from Vault."""
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                mount_point=self.mount_point,
                path=f"{self.path_prefix}{name}",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name} from Vault: {type(e).__name__}")
            return False

    def list_secrets(self) -> list[str]:
        """List all secrets in path."""
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                mount_point=self.mount_point,
                path=self.path_prefix,
            )
            return response["data"]["keys"]
        except Exception as e:
            logger.error(f"Failed to list secrets in Vault: {type(e).__name__}")
            return []


@dataclass
class RotationPolicy:
    """Policy for secret rotation."""
    rotation_period_days: int = 90
    pre_rotation_hook: Optional[Callable[[str, str], bool]] = None  # old_value, new_value -> success
    post_rotation_hook: Optional[Callable[[str, str], None]] = None  # old_value, new_value
    generate_new_value: Optional[Callable[[], str]] = None  # Custom generator


class SecretManager:
    """
    Central secret management service.

    Features:
    - Secure secret retrieval with masking
    - Key rotation with hooks
    - Audit logging
    - Health checks
    """

    def __init__(
        self,
        backend: Optional[SecretBackendBase] = None,
        fallback_to_env: bool = True,
    ):
        self.backend = backend or EnvironmentSecretBackend()
        self.fallback_to_env = fallback_to_env
        self._metadata: dict[str, SecretMetadata] = {}
        self._rotation_policies: dict[str, RotationPolicy] = {}
        self._cache: dict[str, SecretValue] = {}

        # Initialize standard secrets metadata
        self._init_standard_secrets()

    def _init_standard_secrets(self):
        """Initialize metadata for standard secrets."""
        standard_secrets = [
            ("SECRET_KEY", SecretType.JWT_KEY, 90),
            ("DATABASE_PASSWORD", SecretType.DATABASE_PASSWORD, 180),
            ("OPENROUTER_API_KEY", SecretType.API_KEY, 365),
            ("STORAGE_ACCESS_KEY", SecretType.STORAGE_KEY, 180),
            ("STORAGE_SECRET_KEY", SecretType.STORAGE_KEY, 180),
            ("CENSUS_API_KEY", SecretType.API_KEY, 365),
        ]

        for name, secret_type, rotation_days in standard_secrets:
            self._metadata[name] = SecretMetadata(
                name=name,
                secret_type=secret_type,
                created_at=datetime.utcnow(),
                rotation_period_days=rotation_days,
            )

    def get(
        self,
        name: str,
        default: Optional[str] = None,
        secret_type: SecretType = SecretType.API_KEY,
    ) -> Optional[SecretValue]:
        """
        Get a secret value wrapped for security.

        Args:
            name: Secret name
            default: Default value if not found
            secret_type: Type of secret for metadata

        Returns:
            SecretValue wrapper or None
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        # Try primary backend
        value = self.backend.get_secret(name)

        # Fallback to environment if enabled
        if value is None and self.fallback_to_env:
            value = os.environ.get(name)

        # Use default if still not found
        if value is None:
            if default is not None:
                value = default
            else:
                return None

        # Get or create metadata
        if name not in self._metadata:
            self._metadata[name] = SecretMetadata(
                name=name,
                secret_type=secret_type,
                created_at=datetime.utcnow(),
            )

        # Wrap and cache
        secret = SecretValue(_value=value, metadata=self._metadata[name])
        self._cache[name] = secret

        return secret

    def get_raw(
        self,
        name: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get raw secret value (use sparingly - prefer get() for security).

        This method should only be used when the actual value is needed
        for cryptographic operations.
        """
        secret = self.get(name, default)
        if secret:
            return secret.get_value()
        return None

    def set(
        self,
        name: str,
        value: str,
        secret_type: SecretType = SecretType.API_KEY,
    ) -> bool:
        """Store a new secret."""
        success = self.backend.set_secret(name, value)

        if success:
            self._metadata[name] = SecretMetadata(
                name=name,
                secret_type=secret_type,
                created_at=datetime.utcnow(),
            )
            # Invalidate cache
            if name in self._cache:
                del self._cache[name]

        return success

    def rotate(
        self,
        name: str,
        new_value: Optional[str] = None,
    ) -> bool:
        """
        Rotate a secret to a new value.

        Args:
            name: Secret name
            new_value: New value (generated if not provided)

        Returns:
            True if rotation successful
        """
        # Get current value
        current = self.get_raw(name)
        if current is None:
            logger.error(f"Cannot rotate non-existent secret: {name}")
            return False

        # Get rotation policy
        policy = self._rotation_policies.get(name, RotationPolicy())

        # Generate new value if not provided
        if new_value is None:
            if policy.generate_new_value:
                new_value = policy.generate_new_value()
            else:
                new_value = self.generate_secure_key()

        # Run pre-rotation hook
        if policy.pre_rotation_hook:
            if not policy.pre_rotation_hook(current, new_value):
                logger.warning(f"Pre-rotation hook failed for {name}")
                return False

        # Store new value
        success = self.backend.set_secret(name, new_value)

        if success:
            # Update metadata
            if name in self._metadata:
                self._metadata[name].rotated_at = datetime.utcnow()
                self._metadata[name].version += 1

            # Invalidate cache
            if name in self._cache:
                del self._cache[name]

            # Run post-rotation hook
            if policy.post_rotation_hook:
                policy.post_rotation_hook(current, new_value)

            logger.info(f"Successfully rotated secret: {name}")

        return success

    def set_rotation_policy(
        self,
        name: str,
        policy: RotationPolicy,
    ):
        """Set rotation policy for a secret."""
        self._rotation_policies[name] = policy
        if name in self._metadata:
            self._metadata[name].rotation_period_days = policy.rotation_period_days

    def get_secrets_needing_rotation(self) -> list[SecretMetadata]:
        """Get list of secrets that need rotation."""
        return [
            meta for meta in self._metadata.values()
            if meta.needs_rotation
        ]

    def get_rotation_schedule(self) -> list[dict[str, Any]]:
        """Get rotation schedule for all secrets."""
        schedule = []
        for meta in self._metadata.values():
            schedule.append({
                "name": meta.name,
                "type": meta.secret_type.value,
                "days_until_rotation": meta.days_until_rotation,
                "needs_rotation": meta.needs_rotation,
                "last_rotated": meta.rotated_at.isoformat() if meta.rotated_at else None,
                "version": meta.version,
            })
        return sorted(schedule, key=lambda x: x["days_until_rotation"])

    def health_check(self) -> dict[str, Any]:
        """Check health of secret management system."""
        issues = []

        # Check for secrets needing rotation
        needs_rotation = self.get_secrets_needing_rotation()
        if needs_rotation:
            issues.append({
                "severity": "warning",
                "message": f"{len(needs_rotation)} secrets need rotation",
                "secrets": [m.name for m in needs_rotation],
            })

        # Check for missing required secrets
        required = ["SECRET_KEY", "DATABASE_PASSWORD"]
        for name in required:
            if self.get_raw(name) is None:
                issues.append({
                    "severity": "critical",
                    "message": f"Required secret missing: {name}",
                })

        # Check for weak secrets
        secret_key = self.get_raw("SECRET_KEY")
        if secret_key and len(secret_key) < 32:
            issues.append({
                "severity": "warning",
                "message": "SECRET_KEY is too short (< 32 chars)",
            })

        return {
            "healthy": len([i for i in issues if i["severity"] == "critical"]) == 0,
            "issues": issues,
            "total_secrets": len(self._metadata),
            "secrets_needing_rotation": len(needs_rotation),
        }

    @staticmethod
    def generate_secure_key(length: int = 64) -> str:
        """Generate a cryptographically secure key."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_api_key(prefix: str = "av") -> str:
        """Generate an API key with prefix."""
        key = secrets.token_urlsafe(32)
        return f"{prefix}_{key}"

    def clear_cache(self):
        """Clear the secret cache."""
        self._cache.clear()


class SecretRedactor:
    """
    Redacts secrets from strings for safe logging.

    Usage:
        redactor = SecretRedactor()
        redactor.register_secret("my_api_key")
        safe_text = redactor.redact("Connection with key my_api_key failed")
        # Result: "Connection with key [REDACTED] failed"
    """

    def __init__(self):
        self._patterns: list[re.Pattern] = []
        self._literal_secrets: set[str] = set()

    def register_secret(self, secret: str, min_length: int = 8):
        """Register a secret value for redaction."""
        if len(secret) >= min_length:
            self._literal_secrets.add(secret)

    def register_pattern(self, pattern: str):
        """Register a regex pattern for redaction."""
        self._patterns.append(re.compile(pattern))

    def add_common_patterns(self):
        """Add common patterns for API keys, tokens, etc."""
        patterns = [
            r'(?i)api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]{20,}',  # API keys
            r'(?i)secret[_-]?key["\']?\s*[:=]\s*["\']?[\w-]{20,}',  # Secret keys
            r'(?i)password["\']?\s*[:=]\s*["\']?[^\s"\']{8,}',  # Passwords
            r'(?i)token["\']?\s*[:=]\s*["\']?[\w-]{20,}',  # Tokens
            r'(?i)authorization:\s*bearer\s+[\w-]+',  # Auth headers
            r'(?i)aws_secret_access_key\s*=\s*[\w/+=]+',  # AWS keys
            r'postgresql://[^@]+:[^@]+@',  # Database URLs with creds
        ]
        for pattern in patterns:
            self.register_pattern(pattern)

    def redact(self, text: str) -> str:
        """Redact all registered secrets from text."""
        result = text

        # Redact literal secrets
        for secret in self._literal_secrets:
            if secret in result:
                result = result.replace(secret, "[REDACTED]")

        # Redact patterns
        for pattern in self._patterns:
            result = pattern.sub("[REDACTED]", result)

        return result


# Global singleton instances
_secret_manager: Optional[SecretManager] = None
_secret_redactor: Optional[SecretRedactor] = None


def get_secret_manager() -> SecretManager:
    """Get the global secret manager instance."""
    global _secret_manager
    if _secret_manager is None:
        # Determine backend from environment
        backend_type = os.environ.get("SECRET_BACKEND", "environment")

        if backend_type == "aws_secrets_manager":
            backend = AWSSecretsManagerBackend(
                region=os.environ.get("AWS_REGION", "us-east-1"),
            )
        elif backend_type == "hashicorp_vault":
            backend = HashiCorpVaultBackend(
                url=os.environ.get("VAULT_ADDR", "http://localhost:8200"),
            )
        else:
            backend = EnvironmentSecretBackend()

        _secret_manager = SecretManager(backend=backend)

    return _secret_manager


def get_secret_redactor() -> SecretRedactor:
    """Get the global secret redactor instance."""
    global _secret_redactor
    if _secret_redactor is None:
        _secret_redactor = SecretRedactor()
        _secret_redactor.add_common_patterns()

        # Register known secrets
        manager = get_secret_manager()
        for name in manager._metadata.keys():
            value = manager.get_raw(name)
            if value:
                _secret_redactor.register_secret(value)

    return _secret_redactor
