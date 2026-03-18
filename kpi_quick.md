## CI KPI Quick Check

候補セット（自動判定）:
- ✅ `voice_boundary_10k_runtime`: PASS (observed=0.00311854 seconds, target<=0.3 seconds)
  - evidence: min_seconds=0.003119
- ✅ `rth_tracker_boundedness`: PASS (observed=2000 entries, target<=2000 entries)
  - evidence: tracker_entries=2000

責任境界:
- ここでの自動判定はKPI逸脱の一次検知まで。
- マージ可否・運用エスカレーション判断は人間レビュー責任。
