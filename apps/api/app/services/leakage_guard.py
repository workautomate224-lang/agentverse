"""
Leakage Guard Service
Reference: verification_checklist_v2.md §1.3

Prevents access to future data during backtests.
Enforces time cutoff to ensure no data leakage.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class LeakageAttempt:
    """Record of a blocked data access attempt."""
    timestamp: datetime
    data_type: str  # e.g., "market_data", "event", "external_source"
    requested_time: datetime
    cutoff_time: datetime
    source: str
    details: Optional[str] = None


@dataclass
class LeakageGuardStats:
    """Statistics from leakage guard enforcement."""
    blocked_attempts: int = 0
    allowed_accesses: int = 0
    blocked_by_type: Dict[str, int] = field(default_factory=dict)
    attempts: List[LeakageAttempt] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Export stats for Evidence Pack."""
        return {
            "blocked_attempts": self.blocked_attempts,
            "allowed_accesses": self.allowed_accesses,
            "blocked_by_type": dict(self.blocked_by_type),
            "attempt_count": len(self.attempts),
            "first_blocked": self.attempts[0].timestamp.isoformat() if self.attempts else None,
            "last_blocked": self.attempts[-1].timestamp.isoformat() if self.attempts else None,
        }


class LeakageGuard:
    """
    Enforces time cutoff for backtest scenarios.

    When enabled, blocks access to any data timestamped after cutoff_time.
    This prevents future data leakage in validation runs.

    Reference: verification_checklist_v2.md §1.3
    """

    def __init__(
        self,
        cutoff_time: Optional[datetime] = None,
        enabled: bool = False,
        strict_mode: bool = True,
    ):
        """
        Initialize LeakageGuard.

        Args:
            cutoff_time: Data after this time is blocked
            enabled: Whether the guard is active
            strict_mode: If True, raises exception on violation; if False, just logs
        """
        self.cutoff_time = cutoff_time
        self.enabled = enabled
        self.strict_mode = strict_mode
        self.stats = LeakageGuardStats()

    def is_active(self) -> bool:
        """Check if leakage guard is active."""
        return self.enabled and self.cutoff_time is not None

    def check_access(
        self,
        data_time: datetime,
        data_type: str,
        source: str,
        details: Optional[str] = None,
    ) -> bool:
        """
        Check if data access is allowed.

        Args:
            data_time: Timestamp of the data being accessed
            data_type: Type of data (for logging)
            source: Source of the access request
            details: Additional context

        Returns:
            True if access is allowed, False if blocked

        Raises:
            LeakageViolationError: If strict_mode is True and access is blocked
        """
        if not self.is_active():
            self.stats.allowed_accesses += 1
            return True

        # Check if data_time is after cutoff
        if data_time > self.cutoff_time:
            # Block access
            self.stats.blocked_attempts += 1
            self.stats.blocked_by_type[data_type] = (
                self.stats.blocked_by_type.get(data_type, 0) + 1
            )

            attempt = LeakageAttempt(
                timestamp=datetime.utcnow(),
                data_type=data_type,
                requested_time=data_time,
                cutoff_time=self.cutoff_time,
                source=source,
                details=details,
            )
            self.stats.attempts.append(attempt)

            msg = (
                f"LEAKAGE BLOCKED: {data_type} from {source} "
                f"requested time={data_time.isoformat()} > cutoff={self.cutoff_time.isoformat()}"
            )
            logger.warning(msg)

            if self.strict_mode:
                raise LeakageViolationError(msg, attempt)

            return False

        # Access allowed
        self.stats.allowed_accesses += 1
        return True

    def filter_dataset(
        self,
        dataset: List[Dict[str, Any]],
        time_field: str = "timestamp",
    ) -> List[Dict[str, Any]]:
        """
        Filter a dataset to remove entries after cutoff.

        Args:
            dataset: List of records with timestamps
            time_field: Field name containing the timestamp

        Returns:
            Filtered dataset with only pre-cutoff entries
        """
        if not self.is_active():
            return dataset

        filtered = []
        blocked_count = 0

        for record in dataset:
            record_time = record.get(time_field)
            if record_time is None:
                # No timestamp, include by default
                filtered.append(record)
                continue

            # Parse timestamp if string
            if isinstance(record_time, str):
                try:
                    record_time = datetime.fromisoformat(record_time.replace('Z', '+00:00'))
                except ValueError:
                    # Can't parse, include by default
                    filtered.append(record)
                    continue

            if record_time <= self.cutoff_time:
                filtered.append(record)
            else:
                blocked_count += 1

        if blocked_count > 0:
            logger.info(
                f"LeakageGuard filtered {blocked_count} records after cutoff "
                f"{self.cutoff_time.isoformat()}"
            )
            self.stats.blocked_attempts += blocked_count
            self.stats.blocked_by_type["dataset_filter"] = (
                self.stats.blocked_by_type.get("dataset_filter", 0) + blocked_count
            )

        return filtered

    def get_stats(self) -> LeakageGuardStats:
        """Get current enforcement statistics."""
        return self.stats

    def reset_stats(self):
        """Reset enforcement statistics."""
        self.stats = LeakageGuardStats()


class LeakageViolationError(Exception):
    """Raised when a leakage guard violation is detected in strict mode."""

    def __init__(self, message: str, attempt: LeakageAttempt):
        super().__init__(message)
        self.attempt = attempt


# =============================================================================
# Factory Functions
# =============================================================================

def create_leakage_guard_from_config(
    config: Dict[str, Any],
    strict_mode: bool = True,
) -> LeakageGuard:
    """
    Create a LeakageGuard from run configuration.

    Args:
        config: Run configuration dict with cutoff_time and leakage_guard fields
        strict_mode: Whether to raise exceptions on violations

    Returns:
        Configured LeakageGuard instance
    """
    cutoff_time = config.get("cutoff_time")
    if isinstance(cutoff_time, str):
        cutoff_time = datetime.fromisoformat(cutoff_time.replace('Z', '+00:00'))

    enabled = config.get("leakage_guard", False)

    return LeakageGuard(
        cutoff_time=cutoff_time,
        enabled=enabled,
        strict_mode=strict_mode,
    )


def get_leakage_guard(
    cutoff_time: Optional[datetime] = None,
    enabled: bool = False,
) -> LeakageGuard:
    """Get a LeakageGuard instance."""
    return LeakageGuard(
        cutoff_time=cutoff_time,
        enabled=enabled,
    )
