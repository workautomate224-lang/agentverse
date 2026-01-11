"""
PII Redaction Service for Step 4 Production Hardening

Implements:
- Email detection and redaction
- Phone number detection and redaction
- API key / secret detection and redaction
- SSN and credit card number detection
- Custom pattern redaction
- Configurable redaction strategies

Used to sanitize:
- Trace files (trace.ndjson)
- LLM ledger entries (llm_ledger.ndjson)
- Report content (report.md)
- Agent personas and outputs
"""

import re
import logging
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RedactionStrategy(str, Enum):
    """How to redact detected PII."""
    MASK = "mask"  # Replace with [REDACTED]
    HASH = "hash"  # Replace with deterministic hash
    PLACEHOLDER = "placeholder"  # Replace with type placeholder
    REMOVE = "remove"  # Remove entirely


@dataclass
class PIIPattern:
    """A pattern for detecting PII."""
    name: str
    pattern: re.Pattern
    strategy: RedactionStrategy
    placeholder: str
    description: str


# Compiled regex patterns for PII detection
PII_PATTERNS = [
    PIIPattern(
        name="email",
        pattern=re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[EMAIL]",
        description="Email addresses"
    ),
    PIIPattern(
        name="phone_us",
        pattern=re.compile(
            r'\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[PHONE]",
        description="US phone numbers"
    ),
    PIIPattern(
        name="phone_intl",
        pattern=re.compile(
            r'\+[0-9]{1,3}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}'
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[PHONE]",
        description="International phone numbers"
    ),
    PIIPattern(
        name="ssn",
        pattern=re.compile(
            r'\b[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4}\b'
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[SSN]",
        description="US Social Security Numbers"
    ),
    PIIPattern(
        name="credit_card",
        pattern=re.compile(
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[CREDIT_CARD]",
        description="Credit card numbers"
    ),
    PIIPattern(
        name="api_key_generic",
        pattern=re.compile(
            r'\b(?:sk|pk|api|key|token|secret|password|auth)[-_]?[A-Za-z0-9]{20,}\b',
            re.IGNORECASE
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[API_KEY]",
        description="API keys and tokens"
    ),
    PIIPattern(
        name="bearer_token",
        pattern=re.compile(
            r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+'
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[BEARER_TOKEN]",
        description="Bearer tokens (JWT)"
    ),
    PIIPattern(
        name="openai_key",
        pattern=re.compile(r'sk-[A-Za-z0-9]{48}'),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[OPENAI_KEY]",
        description="OpenAI API keys"
    ),
    PIIPattern(
        name="anthropic_key",
        pattern=re.compile(r'sk-ant-[A-Za-z0-9\-]{40,}'),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[ANTHROPIC_KEY]",
        description="Anthropic API keys"
    ),
    PIIPattern(
        name="aws_key",
        pattern=re.compile(r'AKIA[0-9A-Z]{16}'),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[AWS_KEY]",
        description="AWS access key IDs"
    ),
    PIIPattern(
        name="ip_address",
        pattern=re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        ),
        strategy=RedactionStrategy.PLACEHOLDER,
        placeholder="[IP_ADDRESS]",
        description="IPv4 addresses"
    ),
]


class PIIRedactionService:
    """
    Service for detecting and redacting PII from text and structured data.
    """

    def __init__(
        self,
        patterns: Optional[List[PIIPattern]] = None,
        default_strategy: RedactionStrategy = RedactionStrategy.PLACEHOLDER,
        hash_salt: str = ""
    ):
        self.patterns = patterns or PII_PATTERNS
        self.default_strategy = default_strategy
        self.hash_salt = hash_salt
        self._stats = {
            "total_redactions": 0,
            "redactions_by_type": {}
        }

    def _hash_value(self, value: str) -> str:
        """Create deterministic hash of a value."""
        salted = f"{self.hash_salt}{value}"
        return hashlib.sha256(salted.encode()).hexdigest()[:16]

    def _apply_redaction(
        self,
        match: re.Match,
        pattern: PIIPattern
    ) -> str:
        """Apply redaction strategy to a match."""
        value = match.group()
        strategy = pattern.strategy

        if strategy == RedactionStrategy.MASK:
            return "[REDACTED]"
        elif strategy == RedactionStrategy.HASH:
            return f"[{pattern.name.upper()}:{self._hash_value(value)}]"
        elif strategy == RedactionStrategy.PLACEHOLDER:
            return pattern.placeholder
        elif strategy == RedactionStrategy.REMOVE:
            return ""
        else:
            return pattern.placeholder

    def redact_text(
        self,
        text: str,
        patterns: Optional[List[str]] = None
    ) -> tuple[str, Dict[str, int]]:
        """
        Redact PII from text.

        Args:
            text: Input text to redact
            patterns: Optional list of pattern names to apply (default: all)

        Returns:
            Tuple of (redacted_text, redaction_counts)
        """
        if not text:
            return text, {}

        redacted = text
        counts = {}

        for pattern in self.patterns:
            if patterns and pattern.name not in patterns:
                continue

            matches = list(pattern.pattern.finditer(redacted))
            if matches:
                counts[pattern.name] = len(matches)
                self._stats["total_redactions"] += len(matches)
                self._stats["redactions_by_type"][pattern.name] = (
                    self._stats["redactions_by_type"].get(pattern.name, 0) + len(matches)
                )

                # Apply redactions (in reverse to preserve positions)
                for match in reversed(matches):
                    replacement = self._apply_redaction(match, pattern)
                    redacted = redacted[:match.start()] + replacement + redacted[match.end():]

        return redacted, counts

    def redact_dict(
        self,
        data: Dict[str, Any],
        recursive: bool = True,
        exclude_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Redact PII from dictionary values.

        Args:
            data: Dictionary to redact
            recursive: Whether to recurse into nested dicts/lists
            exclude_keys: Keys to skip (e.g., "id", "created_at")

        Returns:
            Redacted dictionary
        """
        exclude_keys = exclude_keys or []
        result = {}

        for key, value in data.items():
            if key in exclude_keys:
                result[key] = value
            elif isinstance(value, str):
                redacted, _ = self.redact_text(value)
                result[key] = redacted
            elif isinstance(value, dict) and recursive:
                result[key] = self.redact_dict(value, recursive, exclude_keys)
            elif isinstance(value, list) and recursive:
                result[key] = self.redact_list(value, exclude_keys)
            else:
                result[key] = value

        return result

    def redact_list(
        self,
        data: List[Any],
        exclude_keys: Optional[List[str]] = None
    ) -> List[Any]:
        """Redact PII from list items."""
        result = []

        for item in data:
            if isinstance(item, str):
                redacted, _ = self.redact_text(item)
                result.append(redacted)
            elif isinstance(item, dict):
                result.append(self.redact_dict(item, True, exclude_keys))
            elif isinstance(item, list):
                result.append(self.redact_list(item, exclude_keys))
            else:
                result.append(item)

        return result

    def redact_ndjson(
        self,
        content: str,
        exclude_keys: Optional[List[str]] = None
    ) -> str:
        """
        Redact PII from NDJSON content.

        Args:
            content: NDJSON string (newline-delimited JSON)
            exclude_keys: Keys to skip in each JSON object

        Returns:
            Redacted NDJSON string
        """
        import json

        lines = content.strip().split('\n')
        redacted_lines = []

        for line in lines:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                redacted_obj = self.redact_dict(obj, True, exclude_keys)
                redacted_lines.append(json.dumps(redacted_obj))
            except json.JSONDecodeError:
                # If not valid JSON, redact as plain text
                redacted, _ = self.redact_text(line)
                redacted_lines.append(redacted)

        return '\n'.join(redacted_lines)

    def redact_trace_file(self, content: str) -> str:
        """Redact PII from trace.ndjson content."""
        return self.redact_ndjson(
            content,
            exclude_keys=["tick", "timestamp", "event_type", "agent_id", "run_id"]
        )

    def redact_llm_ledger(self, content: str) -> str:
        """Redact PII from llm_ledger.ndjson content."""
        return self.redact_ndjson(
            content,
            exclude_keys=["call_id", "model", "tokens_in", "tokens_out", "cost_usd", "cache_hit"]
        )

    def redact_report(self, content: str) -> str:
        """Redact PII from report.md content."""
        redacted, _ = self.redact_text(content)
        return redacted

    def redact_agent_persona(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact PII from agent persona.
        Preserves structure but removes identifying info.
        """
        return self.redact_dict(
            persona,
            recursive=True,
            exclude_keys=["agent_id", "role", "traits"]
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get redaction statistics."""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset redaction statistics."""
        self._stats = {
            "total_redactions": 0,
            "redactions_by_type": {}
        }

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text without redacting.
        Returns list of detections with type and position.
        """
        detections = []

        for pattern in self.patterns:
            for match in pattern.pattern.finditer(text):
                detections.append({
                    "type": pattern.name,
                    "start": match.start(),
                    "end": match.end(),
                    "description": pattern.description,
                    # Don't include the actual value for security
                    "length": len(match.group())
                })

        return detections

    def has_pii(self, text: str) -> bool:
        """Check if text contains any PII."""
        for pattern in self.patterns:
            if pattern.pattern.search(text):
                return True
        return False


# Singleton instance for convenience
_default_service: Optional[PIIRedactionService] = None


def get_pii_service() -> PIIRedactionService:
    """Get default PII redaction service instance."""
    global _default_service
    if _default_service is None:
        _default_service = PIIRedactionService()
    return _default_service


def redact_text(text: str) -> str:
    """Convenience function to redact text using default service."""
    service = get_pii_service()
    redacted, _ = service.redact_text(text)
    return redacted
