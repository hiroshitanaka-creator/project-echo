from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FAILURE_DIR = Path("tests/.artifacts/invariant_failures")


def persist_minimal_repro(*, test_name: str, mode: str, repro_input: Any, detail: str) -> None:
    """Persist minimized repro payload for deterministic local reruns."""
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    payload = {
        "timestamp_utc": ts,
        "test_name": test_name,
        "mode": mode,
        "detail": detail,
        "minimal_repro_input": repro_input,
    }
    out = FAILURE_DIR / f"{test_name}__{mode}__{ts}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def assert_or_log(
    *,
    condition: bool,
    test_name: str,
    mode: str,
    repro_input: Any,
    message: str,
) -> None:
    """Assert with a persisted minimal repro payload on failure."""
    if condition:
        return
    persist_minimal_repro(test_name=test_name, mode=mode, repro_input=repro_input, detail=message)
    raise AssertionError(message)
