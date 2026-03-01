# Public Benchmark Suite & Performance Testing

Task: **ECHO-20260304-001 / ECHO-20260304-002 Public Benchmark Suite & Final Polish**  
Phase: **Phase 3 Benchmark & Quality**

## Reproducibility Policy

- Python: `>=3.11,<3.13`
- Seed-independent deterministic command set (fixed command order).
- Benchmarks are opt-in by environment variable to avoid accidental CI slowdowns.
- Public benchmark command must explicitly set `RUN_PUBLIC_BENCHMARKS=1`.

## Benchmark Commands

```bash
pytest -q tests/test_voice_boundary.py tests/test_rth.py
RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_voice_boundary.py
RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_rth.py
# CI benchmark workflow
gh workflow run benchmark.yml
```

## Result Table (local reference)

| Benchmark | Case/Window Count | Status | Notes |
|---|---:|---|---|
| Voice Boundary risk classification | 10,000 | Pass | Hypothesis-generated intent/meta inputs + timeit stats validation |
| Voice Boundary risk classification | 100,000 | Pass | Same method, large-scale regression/perf guard |
| RTH rolling hash memory/prune | 100,000 windows | Pass | `tracemalloc` peak/current memory and `max_seen_count` bounded prune assertion |

## Phase 3 KPI (Performance / Memory / Reproducibility)

| KPI | Definition | Target |
|---|---|---|
| Risk classification throughput | `classify_risk` over 10k/100k generated cases | `10k min_seconds < 0.3` + `100k` completes without crash |
| RTH memory boundedness | collision tracker entry count during 100k rolling windows | `tracker_entries <= max_seen_count` |
| Reproducibility | command-based benchmark rerun behavior | Same commands reproduce pass/fail conditions |

## Notes

- This benchmark suite intentionally preserves existing non-benchmark safety logic without mutation.
- Existing invariants (`semantic_evidence`, screenless safety config, collision tracker design, Echo Mark v3 integration) remain non-destructively unchanged.
