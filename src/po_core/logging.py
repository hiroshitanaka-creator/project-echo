"""
Structured logging configuration for Project Echo.

Provides consistent logging across all modules with:
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Structured JSON output option for production
- Human-readable format for development
- Audit trail support for security-critical operations
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

# Environment variable for log level
LOG_LEVEL = os.getenv("ECHO_LOG_LEVEL", "INFO").upper()

# Environment variable for JSON output (set to "1" or "true" for structured logs)
LOG_JSON = os.getenv("ECHO_LOG_JSON", "").lower() in ("1", "true")


class EchoFormatter(logging.Formatter):
    """Custom formatter for Project Echo logs."""

    def format(self, record: logging.LogRecord) -> str:
        if LOG_JSON:
            # Structured JSON format for production
            import json

            log_data: dict[str, Any] = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            if hasattr(record, "audit"):
                log_data["audit"] = record.audit  # type: ignore[attr-defined]
            return json.dumps(log_data, ensure_ascii=False)
        else:
            # Human-readable format for development
            return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for the given module name.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

        # Console handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logger.level)

        # Formatter
        if LOG_JSON:
            formatter = EchoFormatter()
        else:
            formatter = EchoFormatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent propagation to root logger
        logger.propagate = False

    return logger


def audit_log(logger: logging.Logger, action: str, details: dict[str, Any]) -> None:
    """
    Log a security-critical audit event.

    Args:
        logger: Logger instance
        action: Action being audited (e.g., "signature_verify", "key_rotation")
        details: Structured details about the action
    """
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        f"AUDIT: {action}",
        (),
        None,
    )
    record.audit = {"action": action, **details}  # type: ignore[attr-defined]
    logger.handle(record)
