"""Shared helper utilities for po-cosmic CLI."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def load_verify_nonce_cache(cache_path: Path, *, max_age_seconds: int) -> dict[str, datetime]:
    """Load nonce replay cache from disk, pruning entries outside active window."""
    if not cache_path.exists():
        return {}

    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(raw, dict):
        return {}

    cache: dict[str, datetime] = {}
    for nonce, seen_at_raw in raw.items():
        if not isinstance(nonce, str) or not isinstance(seen_at_raw, str):
            continue
        try:
            seen_at = datetime.fromisoformat(seen_at_raw)
        except ValueError:
            continue
        now = datetime.now(seen_at.tzinfo) if seen_at.tzinfo else datetime.now()
        if (now - seen_at).total_seconds() <= max_age_seconds:
            cache[nonce] = seen_at
    return cache


def save_verify_nonce_cache(cache_path: Path, cache: dict[str, datetime]) -> None:
    """Persist nonce replay cache for CLI default verification path."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {nonce: seen_at.isoformat(timespec="seconds") for nonce, seen_at in cache.items()}
    cache_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_cli_path_arg(
    positional: str | None,
    optional: str | None,
    *,
    positional_label: str,
    option_label: str,
) -> str:
    """Resolve backward-compatible path args while rejecting ambiguous duplicates."""
    if positional and optional and positional != optional:
        print(
            (
                f"Error: ambiguous {positional_label}; positional '{positional}' "
                f"conflicts with {option_label} '{optional}'"
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)

    value = optional or positional
    if not value:
        print(
            f"Error: {positional_label} is required via positional arg or {option_label}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return value

