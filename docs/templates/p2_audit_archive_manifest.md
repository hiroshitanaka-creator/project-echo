# P2 Audit Archive Manifest Template

週次監査証跡を同一形式で保存するためのテンプレート。

## Archive Metadata
- week_id: `YYYY-Www`
- generated_at_utc: `YYYY-MM-DDTHH:MM:SSZ`
- operator: `<name or team>`
- branch_or_tag: `<git ref>`

## Evidence Bundle Paths
- benchmark_voice_boundary_log: `reports/audit/<week_id>/benchmark_voice_boundary.txt`
- benchmark_rth_log: `reports/audit/<week_id>/benchmark_rth.txt`
- demo_c_receipt: `reports/audit/<week_id>/demo_c_receipt.json`
- registry_snapshot: `reports/audit/<week_id>/registry_snapshot.json`
- triage_note: `reports/audit/<week_id>/triage_note.md`

## Verification Checklist
- [ ] Voice Boundary KPI (`min_seconds < 0.3`) を満たす
- [ ] RTH KPI (`tracker_entries <= max_seen_count`) を満たす
- [ ] Demo C `verification.status == VERIFIED`
- [ ] key status監査（active/inactive/revoked）差分確認
- [ ] replay/hash/signature の4層チェック記録

## Responsibility Boundary
- 本テンプレートは証跡保存の形式統一までを責任範囲とする。
- 公開可否の最終判断は人間オーナー/組織責任とする。
