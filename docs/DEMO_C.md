# Demo C（Phase 3 Skeleton）

Task: **ECHO-20260304-002 Benchmark Final Polish & CI Integration**

## 目的

- 公開ベンチマーク結果を Echo Mark 形式で可視化し、CLI から再現可能に表示する。
- Project Echo の不変原則（候補セット + 証拠 + 責任境界）をデモ出力に保持する。

## 軽量CLIスケルトン（例）

```python
from __future__ import annotations

import json
from datetime import UTC, datetime


def build_demo_c_echo_mark(voice_10k_seconds: float, rth_tracker_entries: int, rth_max_seen: int) -> dict:
    """Build a lightweight Echo Mark style payload for Demo C benchmark output."""
    return {
        "schema_version": "echo_mark_v3",
        "issued_at": datetime.now(UTC).isoformat(),
        "policy": {
            "responsibility_boundary": "human_review_required_for_release",
            "required_action": "review_benchmark_receipt",
        },
        "signals": {
            "voice_boundary_10k_min_seconds": voice_10k_seconds,
            "rth_tracker_entries": rth_tracker_entries,
            "rth_max_seen_count": rth_max_seen,
            "kpi_voice_10k_under_0_3": voice_10k_seconds < 0.3,
            "kpi_rth_bounded": rth_tracker_entries <= rth_max_seen,
        },
        "semantic_evidence": [
            "phase3_public_benchmark",
            "non_destructive_policy",
            "ci_integrated_kpi_gate",
        ],
    }


if __name__ == "__main__":
    receipt = build_demo_c_echo_mark(voice_10k_seconds=0.21, rth_tracker_entries=1980, rth_max_seen=2000)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
```

## 実行例

```bash
python docs/demo_c_example.py
```

> この文書はスケルトンであり、本番Demo Cでは既存 Echo Mark 署名/検証フローと統合する。
