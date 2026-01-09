"""
Secure Logging Configuration
Reference: project.md §8.4, §11 Phase 9

Features:
- Secret redaction from all log output
- Structured JSON logging for production
- Request/response logging with sensitive data masking
- Audit trail for security events
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Optional
import os

# Import redactor lazily to avoid circular imports
_redactor = None


def get_redactor():
    """Get redactor lazily to avoid circular imports."""
    global _redactor
    if _redactor is None:
        from app.core.secrets import get_secret_redactor
        _redactor = get_secret_redactor()
    return _redactor


class SecretRedactingFormatter(logging.Formatter):
    """
    Logging formatter that redacts secrets from log messages.

    This ensures no secrets are accidentally logged even if
    developers forget to sanitize sensitive data.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = '%',
    ):
        super().__init__(fmt, datefmt, style)
        self._sensitive_fields = {
            'password', 'secret', 'token', 'api_key', 'apikey',
            'authorization', 'auth', 'credential', 'private_key',
            'access_key', 'secret_key', 'session_id', 'cookie',
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with secret redaction."""
        # Get the formatted message
        formatted = super().format(record)

        # Redact using the global redactor
        try:
            redactor = get_redactor()
            formatted = redactor.redact(formatted)
        except Exception:
            # If redactor fails, still log but without redaction
            pass

        return formatted

    def _redact_dict(self, data: dict) -> dict:
        """Recursively redact sensitive fields from dict."""
        result = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self._sensitive_fields):
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class JSONFormatter(SecretRedactingFormatter):
    """
    JSON formatter for structured logging in production.

    Outputs logs as JSON objects for easy parsing by log aggregators
    like DataDog, Splunk, or ELK stack.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with secret redaction."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'tenant_id'):
            log_data['tenant_id'] = record.tenant_id
        if hasattr(record, 'action'):
            log_data['action'] = record.action

        # Add exception info
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info),
            }

        # Redact sensitive fields
        log_data = self._redact_dict(log_data)

        # Apply text redaction
        json_str = json.dumps(log_data)
        try:
            redactor = get_redactor()
            json_str = redactor.redact(json_str)
        except Exception:
            pass

        return json_str


class SecurityAuditLogger:
    """
    Specialized logger for security-related events.

    Logs security events with structured data for compliance
    and incident response.
    """

    def __init__(self, logger_name: str = "security.audit"):
        self.logger = logging.getLogger(logger_name)

    def log_authentication(
        self,
        user_id: Optional[str],
        success: bool,
        method: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """Log authentication attempt."""
        extra = {
            'action': 'authentication',
            'user_id': user_id,
            'success': success,
            'method': method,
            'ip_address': ip_address,
            'user_agent': user_agent,
        }
        message = f"Authentication {'succeeded' if success else 'failed'} for {user_id or 'unknown'}"
        if reason:
            message += f": {reason}"

        if success:
            self.logger.info(message, extra=extra)
        else:
            self.logger.warning(message, extra=extra)

    def log_authorization(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        tenant_id: Optional[str] = None,
    ):
        """Log authorization decision."""
        extra = {
            'action': 'authorization',
            'user_id': user_id,
            'resource': resource,
            'resource_action': action,
            'allowed': allowed,
            'tenant_id': tenant_id,
        }
        message = f"Authorization {'granted' if allowed else 'denied'}: {user_id} -> {action} on {resource}"

        if allowed:
            self.logger.info(message, extra=extra)
        else:
            self.logger.warning(message, extra=extra)

    def log_secret_access(
        self,
        secret_name: str,
        accessor: Optional[str] = None,
        operation: str = "read",
    ):
        """Log secret access for audit."""
        extra = {
            'action': 'secret_access',
            'secret_name': secret_name,
            'accessor': accessor,
            'operation': operation,
        }
        self.logger.info(
            f"Secret accessed: {secret_name} ({operation})",
            extra=extra,
        )

    def log_secret_rotation(
        self,
        secret_name: str,
        success: bool,
        rotated_by: Optional[str] = None,
    ):
        """Log secret rotation event."""
        extra = {
            'action': 'secret_rotation',
            'secret_name': secret_name,
            'success': success,
            'rotated_by': rotated_by,
        }
        if success:
            self.logger.info(f"Secret rotated: {secret_name}", extra=extra)
        else:
            self.logger.error(f"Secret rotation failed: {secret_name}", extra=extra)

    def log_data_export(
        self,
        user_id: str,
        export_type: str,
        resource_ids: list[str],
        tenant_id: Optional[str] = None,
    ):
        """Log data export for compliance."""
        extra = {
            'action': 'data_export',
            'user_id': user_id,
            'export_type': export_type,
            'resource_count': len(resource_ids),
            'tenant_id': tenant_id,
        }
        self.logger.info(
            f"Data export: {user_id} exported {len(resource_ids)} {export_type} items",
            extra=extra,
        )

    def log_permission_change(
        self,
        admin_id: str,
        target_user_id: str,
        old_role: Optional[str],
        new_role: Optional[str],
        tenant_id: Optional[str] = None,
    ):
        """Log permission/role changes."""
        extra = {
            'action': 'permission_change',
            'admin_id': admin_id,
            'target_user_id': target_user_id,
            'old_role': old_role,
            'new_role': new_role,
            'tenant_id': tenant_id,
        }
        self.logger.info(
            f"Permission change: {target_user_id} {old_role} -> {new_role} by {admin_id}",
            extra=extra,
        )

    def log_suspicious_activity(
        self,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """Log suspicious activity for security review."""
        extra = {
            'action': 'suspicious_activity',
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details,
        }
        self.logger.warning(f"Suspicious activity: {description}", extra=extra)


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None,
):
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON format (for production)
        log_file: Optional file path for log output
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Choose formatter
    if json_output:
        formatter = JSONFormatter()
    else:
        formatter = SecretRedactingFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Security audit logger - always use JSON
    security_logger = logging.getLogger("security.audit")
    security_handler = logging.StreamHandler(sys.stdout)
    security_handler.setFormatter(JSONFormatter())
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)

    # Reduce noise from third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_audit_logger() -> SecurityAuditLogger:
    """Get the security audit logger instance."""
    return SecurityAuditLogger()


# Context variables for request-scoped logging
class LogContext:
    """Thread-local context for request-scoped log data."""

    _data: dict = {}

    @classmethod
    def set(cls, **kwargs):
        """Set context values."""
        cls._data.update(kwargs)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get context value."""
        return cls._data.get(key, default)

    @classmethod
    def clear(cls):
        """Clear all context."""
        cls._data.clear()

    @classmethod
    def as_dict(cls) -> dict:
        """Get all context as dict."""
        return cls._data.copy()


class ContextInjectingFilter(logging.Filter):
    """Logging filter that injects context into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in LogContext.as_dict().items():
            setattr(record, key, value)
        return True
