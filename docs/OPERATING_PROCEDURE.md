# Operating Procedure（Phase 4）

Task: **ECHO-20260305-001**

## 1. 目的

Phase 3/4の防御品質を本番運用で維持するため、benchmark・key rotation・監査フローを統一手順として定義する。

## 2. 日次/週次運用サイクル

### 日次（軽量確認）
1. 主要テスト実行
2. Demo C receipt生成
3. 署名検証結果を監査ログへ保存

### 週次（品質ゲート確認）
1. 公開benchmark 10k/100k 実行
2. KPI判定と前週比較
3. key status（active/inactive/revoked）監査

## 3. Benchmark 実行手順

```bash
pytest -q tests/test_voice_boundary.py tests/test_rth.py
RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_voice_boundary.py
RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_rth.py
python docs/demo_c_example.py --pretty
```

判定基準:
- Voice Boundary 10k: `min_seconds < 0.3`
- RTH 100k: `tracker_entries <= max_seen_count`
- Demo C: `verification.status == VERIFIED`

## 4. Key Rotation 手順

1. 新規鍵生成（ローテーション対象key_idを指定）
2. registry更新（旧activeをinactiveまたはrevokedへ遷移）
3. Demo Cで新key_id署名を検証
4. 監査ログへ「誰が・いつ・なぜ」を記録

例:

```bash
python tools/generate_keypair.py rotate --key-id echo-prod-202603 --registry .keys/registry.json
python docs/demo_c_example.py --key-id echo-prod-202603 --pretty
```

## 5. 監査フロー

1. **収集**: benchmarkログ、Demo C出力JSON、registry差分
2. **検証**: hash / replay / signature / KPI の4層チェック
3. **判定**:
   - VERIFIED: 公開可能
   - BLOCKED: 境界ポリシー上の再確認が必要
   - INVALID: 署名・整合性破綻のため公開不可
4. **保管**: 監査チケットに証跡を添付（削除禁止）

## 6. インシデント時対応

- replay検知: 該当nonceを封鎖し、発表用receiptを再発行。
- key漏えい疑い: 即時revoked + 新key_idへ切替。
- KPI劣化: 公開停止、原因分析後に再計測。

## 7. 変更管理ルール

- 既存 `docs/BENCHMARK_RESULTS.md` の履歴は累積追記のみ。
- 防御ロジック変更時は不変原則適合レビューを先行。
- プレゼン資料更新時も、署名付き証跡の再生成を必須化。
