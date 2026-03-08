# P2 KPI Delta Report Template

前週比で劣化を即検知するための1ページ雛形。

## Header
- week_id: `YYYY-Www`
- compared_to: `YYYY-Www`
- reviewer: `<name or team>`

## KPI Delta Table

| KPI | Current | Previous | Delta | Target | Status | Note |
|---|---:|---:|---:|---|---|---|
| Voice Boundary min_seconds (10k) |  |  |  | `< 0.3` |  |  |
| RTH tracker_entries (100k) |  |  |  | `<= max_seen_count` |  |  |
| Signature verification success rate |  |  |  | `100%` |  |  |
| Invariant test pass rate |  |  |  | `100%` |  |  |

## Decision
- 判定: `GO / HOLD / BLOCK`
- 理由:
  -

## Follow-up Actions
- [ ] 劣化要因の切り分け
- [ ] 再計測コマンドの再実行
- [ ] 監査ログへの追記

## Responsibility Boundary
- 本レポートはKPI差分の可視化と一次判定を責任範囲とする。
- 本番反映可否とリスク受容は人間オーナー責任とする。
