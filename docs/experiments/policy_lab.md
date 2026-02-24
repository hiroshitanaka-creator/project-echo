# Policy Lab v1

Policy Lab は policy 閾値（`UNKNOWN_BLOCK` / `TIME_PRESSURE_DAYS`）を意図的に揺らし、
ケースごとの差分を機械的に出すための **実験用ツール** です。

> この実験は `scripts/` と `reports/` に隔離されており、CI 必須実行には含めません。

## 使い方

```bash
python scripts/policy_lab.py \
  --unknown-block 3 \
  --time-pressure-days 2 \
  --compare-baseline
```

```bash
python scripts/policy_lab.py \
  --unknown-block 1 \
  --time-pressure-days 5 \
  --now 2026-01-01T00:00:00Z \
  --seed 42 \
  --scenarios-dir scenarios/ \
  --output-dir reports/policy_lab/ \
  --compare-baseline
```

## 出力

- `reports/policy_lab/<timestamp>_ubX_tpY.json`（機械用）
- `reports/policy_lab/<timestamp>_ubX_tpY.md`（人間用）

## 解釈

- baseline（デフォルト policy）と variant（指定 policy）を同じ `now` / `seed` で比較します。
- 差分が出たケースには `impacted_requirements` を付与します。
- `impacted_requirements` は `docs/traceability/traceability_v1.yaml` の `code_refs` を逆引きして推定します。
