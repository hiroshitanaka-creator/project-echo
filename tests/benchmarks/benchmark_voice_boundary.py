from __future__ import annotations

import os
import statistics
import sys
import timeit
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis")
HealthCheck = hypothesis.HealthCheck
seed = hypothesis.seed
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies
register_type_strategy = st.register_type_strategy



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



def _load_classify_risk():
    """Load classify_risk without importing po_echo package __init__."""
    module_path = _resolve_module_path("voice_boundary.py")
    spec = spec_from_file_location("po_echo_voice_boundary_benchmark", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to resolve voice_boundary module spec")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.classify_risk


classify_risk = _load_classify_risk()
RUN_PUBLIC_BENCHMARKS = os.getenv("RUN_PUBLIC_BENCHMARKS") == "1"
VOICE_BENCHMARK_SEED = 20260304


@dataclass(frozen=True)
class BenchmarkVoiceCase:
    """Typed benchmark case for deterministic Hypothesis materialization."""

    intent: str
    amount: float | int | str


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


register_type_strategy(
    BenchmarkVoiceCase,
    _intent_and_meta().map(lambda pair: BenchmarkVoiceCase(intent=pair[0], amount=pair[1]["amount"])),
)



def _build_cases(
    case_count: int,
    seed_value: int = VOICE_BENCHMARK_SEED,
) -> list[tuple[str, dict[str, float | int | str]]]:
    """Build deterministic benchmark cases using seeded Hypothesis generation.

    Args:
        case_count: Number of cases to materialize.
        seed_value: Fixed seed used to ensure reproducible generation.

    Returns:
        Intent/meta tuples ready to pass to ``classify_risk``.

    Raises:
        ValueError: If case_count is not positive.
    """
    if case_count <= 0:
        raise ValueError("case_count must be positive")

    captured_cases: list[BenchmarkVoiceCase] = []

    @settings(
        max_examples=1,
        deadline=None,
        database=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @seed(seed_value)
    @given(st.lists(st.from_type(BenchmarkVoiceCase), min_size=case_count, max_size=case_count))
    def _materialize(cases: list[BenchmarkVoiceCase]) -> None:
        captured_cases.extend(cases)

    _materialize()
    return [(case.intent, {"amount": case.amount}) for case in captured_cases]



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
    assert stats["min_seconds"] < 0.3
    assert stats["throughput_case_per_sec"] > 0


@pytest.mark.skipif(not RUN_PUBLIC_BENCHMARKS, reason="Set RUN_PUBLIC_BENCHMARKS=1 to execute")
def test_benchmark_voice_boundary_100k() -> None:
    """Benchmark 100k voice risk classification cases."""
    stats = _measure(_build_cases(case_count=100_000))
    assert stats["throughput_case_per_sec"] > 0
