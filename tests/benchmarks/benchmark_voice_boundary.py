from __future__ import annotations

import importlib.util
import os
import statistics
import sys
import timeit
from collections.abc import Iterable
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis")
st = hypothesis.strategies


def _load_classify_risk():
    """Load classify_risk without importing po_echo package __init__."""
    module_path = Path(__file__).resolve().parents[2] / "src" / "po_echo" / "voice_boundary.py"
    spec = importlib.util.spec_from_file_location("po_echo_voice_boundary_benchmark", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to resolve voice_boundary module spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.classify_risk


classify_risk = _load_classify_risk()
RUN_PUBLIC_BENCHMARKS = os.getenv("RUN_PUBLIC_BENCHMARKS") == "1"


@st.composite
def _intent_and_meta(draw) -> tuple[str, dict[str, float | int | str]]:
    """Generate realistic intent/meta pairs for voice boundary benchmarks."""
    intent = draw(
        st.sampled_from(
            [
                "search",
                "summary",
                "booking",
                "itinerary",
                "payment",
                "purchase",
                "identity_disclosure",
                "semantic_delta",
            ]
        )
    )
    amount = draw(st.one_of(st.floats(min_value=0, max_value=50_000), st.integers(0, 50_000)))
    meta: dict[str, float | int | str] = {"amount": amount}

    if draw(st.booleans()):
        meta["amount"] = draw(st.text(min_size=0, max_size=6))

    return intent, meta


def _build_cases(case_count: int) -> list[tuple[str, dict[str, float | int | str]]]:
    """Build deterministic benchmark cases using Hypothesis examples.

    Args:
        case_count: Number of cases to materialize.

    Returns:
        Intent/meta tuples ready to pass to ``classify_risk``.

    Raises:
        ValueError: If case_count is not positive.
    """
    if case_count <= 0:
        raise ValueError("case_count must be positive")

    return [_intent_and_meta().example() for _ in range(case_count)]


def _run_risk_classification(cases: Iterable[tuple[str, dict[str, float | int | str]]]) -> None:
    """Execute risk classification over all generated cases.

    Args:
        cases: Intent/meta inputs for classification.

    Returns:
        None.

    Raises:
        This function does not raise exceptions by design.
    """
    for intent, meta in cases:
        risk = classify_risk(intent, meta)
        if risk not in {"low", "medium", "high"}:
            raise AssertionError(f"Unexpected risk label: {risk}")


def _measure(cases: list[tuple[str, dict[str, float | int | str]]], repeat: int = 3) -> dict[str, float]:
    """Measure voice boundary classification runtime.

    Args:
        cases: Materialized benchmark cases.
        repeat: Number of repeated timeit runs.

    Returns:
        Runtime statistics in seconds.

    Raises:
        ValueError: If repeat is not positive.
    """
    if repeat <= 0:
        raise ValueError("repeat must be positive")

    timer = timeit.Timer(lambda: _run_risk_classification(cases))
    durations = timer.repeat(repeat=repeat, number=1)
    case_count = len(cases)
    return {
        "cases": float(case_count),
        "min_seconds": min(durations),
        "mean_seconds": statistics.mean(durations),
        "p95_seconds": statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0],
        "throughput_case_per_sec": case_count / min(durations),
    }


@pytest.mark.skipif(not RUN_PUBLIC_BENCHMARKS, reason="Set RUN_PUBLIC_BENCHMARKS=1 to execute")
def test_benchmark_voice_boundary_10k() -> None:
    """Benchmark 10k voice risk classification cases."""
    stats = _measure(_build_cases(case_count=10_000))
    assert stats["throughput_case_per_sec"] > 0


@pytest.mark.skipif(not RUN_PUBLIC_BENCHMARKS, reason="Set RUN_PUBLIC_BENCHMARKS=1 to execute")
def test_benchmark_voice_boundary_100k() -> None:
    """Benchmark 100k voice risk classification cases."""
    stats = _measure(_build_cases(case_count=100_000))
    assert stats["throughput_case_per_sec"] > 0
