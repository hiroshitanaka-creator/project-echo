# P2 KPI Alert（初動テンプレート）

目的: KPI劣化検知時の初動を定型化し、判断までのリードタイムを短縮する。

## 1) Alert Header
- alert_id: `ALERT-YYYYMMDD-XXX`
- week_id: `YYYY-Www`
- detected_at_utc: `<set-by-operator>`
- severity: `SEV-1|SEV-2|SEV-3`
- detector: `automation|operator`

## 2) Trigger
- metric_name: `<voice_boundary_min_seconds | rth_tracker_entries | demo_c_verification_status | ...>`
- observed_value: `<value>`
- threshold: `<value>`
- comparison: `< | > | >= | <= | ==`
- result: `BREACH`

## 3) Evidence
- weekly_archive: `reports/audit/YYYY-Www/`
- kpi_delta_ref: `reports/audit/YYYY-Www/kpi_delta.md`
- benchmark_voice_boundary_log: `reports/audit/YYYY-Www/benchmark_voice_boundary.txt`
- benchmark_rth_log: `reports/audit/YYYY-Www/benchmark_rth.txt`
- demo_c_receipt: `reports/audit/YYYY-Www/demo_c_receipt.json`

## 4) First Response (T+15min)
- [ ] 実行コマンド再現（同一commit / 同一seed / 同一env）
- [ ] 一時切り分け（infra / dependency / logic / data drift）
- [ ] 影響範囲判定（公開停止要否）
- [ ] オーナー通知（Ops / Security / Product）

## 5) Responsibility Boundary
- 自動化責務: KPI閾値逸脱の検知・記録・証跡リンク生成まで。
- 人間責務: 公開可否、リスク受容、対外説明、恒久対策の承認。

## 6) Triage Outcome
- disposition: `mitigated | monitoring | blocked`
- mitigation_owner: `<name/team>`
- next_review_at_utc: `<timestamp>`
- notes:
  - `<short note 1>`
  - `<short note 2>`
