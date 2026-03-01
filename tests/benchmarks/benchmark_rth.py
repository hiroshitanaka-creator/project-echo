from __future__ import annotations

import os
import sys
import tracemalloc
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest



def _resolve_module_path(filename: str) -> Path:
    """Resolve po_echo module path for editable installs and local source trees."""
    for entry in sys.path:
        if not entry:
            continue
        candidate = Path(entry) / "po_echo" / filename
        if candidate.exists():
            return candidate

    fallback = Path(__file__).resolve().parents[2] / "src" / "po_echo" / filename
    if fallback.exists():
        return fallback
    raise RuntimeError(f"Unable to resolve po_echo/{filename}")



def _load_rth_symbols() -> tuple[type, type]:
    """Load RTH symbols without importing po_echo package __init__."""
    module_path = _resolve_module_path("rth.py")
    spec = spec_from_file_location("po_echo_rth_benchmark", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to resolve rth module spec")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CollisionTrackerConfig, module.RollingTranscriptHash


CollisionTrackerConfig, RollingTranscriptHash = _load_rth_symbols()
RUN_PUBLIC_BENCHMARKS = os.getenv("RUN_PUBLIC_BENCHMARKS") == "1"



def _run_rolling_hash(window_count: int) -> dict[str, int | float]:
    """Run long-horizon RTH updates and capture memory/collision statistics.

    Args:
        window_count: Number of transcript windows to process.

    Returns:
        Aggregated benchmark metrics for memory usage and tracker behavior.

    Raises:
        ValueError: If window_count is not positive.
    """
    if window_count <= 0:
        raise ValueError("window_count must be positive")

    rth = RollingTranscriptHash(
        collision_tracker_config=CollisionTrackerConfig(max_seen_count=2_000, ttl_ms=120_000)
    )
    tracemalloc.start()

    for idx in range(window_count):
        # The modulo keeps feature variety bounded so collisions/pruning are exercised.
        rth.update_text(f"booking window {idx % 1500} payment amount {idx % 50_000}")

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    seen = rth.state.seen_chain_hash_to_feat_fp or {}
    return {
        "windows": window_count,
        "current_bytes": current_bytes,
        "peak_bytes": peak_bytes,
        "tracker_entries": len(seen),
        "max_seen_count": rth._collision_tracker_config.max_seen_count,
    }


@pytest.mark.skipif(not RUN_PUBLIC_BENCHMARKS, reason="Set RUN_PUBLIC_BENCHMARKS=1 to execute")
def test_benchmark_rth_rolling_100k_windows() -> None:
    """Benchmark 100k rolling transcript windows for memory and prune stability."""
    stats = _run_rolling_hash(window_count=100_000)
    assert stats["tracker_entries"] <= stats["max_seen_count"]
    assert stats["peak_bytes"] >= stats["current_bytes"]
