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

## 6. CI失敗時トリアージ手順（再現→分類→修正→再検証）

1. **再現（Reproduce）**
   - 失敗したジョブをローカルで同じコマンドで再現する。
   - 例（PR必須ゲート）:
     ```bash
     pytest -q tests/test_smoke.py
     pytest -q tests/test_invariants.py
     pytest -q tests/test_prop_*.py --hypothesis-show-statistics
     ```

2. **分類（Classify）**
   - 失敗種別を以下に分類する。
     - `smoke`: lint / typing / import破綻
     - `invariants`: 不変原則違反（例: responsibility boundary missing/invalid）
     - `prop-core`: 境界条件・確率的反例
     - `benchmark`: KPI劣化（週次重ゲート）
   - `invariants` 失敗時はCI summaryの「Violated principle candidates」を一次判定として利用する。

3. **修正（Fix）**
   - まず不変原則違反を優先（AI never recommends / conservative gate / evidence-first / no hidden monetization / verifiable outputs）。
   - 次に副作用（型、lint、周辺property）を解消。
   - 修正内容には「どの原則を回復したか」をコミットメッセージまたはPR説明に明記する。

4. **再検証（Re-verify）**
   - 失敗ジョブ単体 → PR必須ゲート一式 → 必要に応じてbenchmarkの順で再実行する。
   - 合格後、監査ログに「原因・対処・再検証結果」を追記する。

## 7. インシデント時対応

- replay検知: 該当nonceを封鎖し、発表用receiptを再発行。
- key漏えい疑い: 即時revoked + 新key_idへ切替。
- KPI劣化: 公開停止、原因分析後に再計測。

## 8. 変更管理ルール

- 既存 `docs/BENCHMARK_RESULTS.md` の履歴は累積追記のみ。
- 防御ロジック変更時は不変原則適合レビューを先行。
- プレゼン資料更新時も、署名付き証跡の再生成を必須化。


## 9. P2 Sprint-2 監査アーカイブ運用（定例）

### 9.1 命名規約
- 週次アーカイブディレクトリ: `reports/audit/YYYY-Www/`
- 必須ファイル:
  - `benchmark_voice_boundary.txt`
  - `benchmark_rth.txt`
  - `demo_c_receipt.json`
  - `registry_snapshot.json`
  - `triage_note.md`

### 9.2 テンプレート
- 監査アーカイブmanifest: `docs/templates/p2_audit_archive_manifest.md`
- KPI差分レポート雛形: `docs/templates/p2_kpi_delta_report.md`
- KPI劣化アラート雛形: `docs/templates/p2_kpi_alert.md`

### 9.3 初期化コマンド例
```bash
WEEK_ID=$(date +%G-W%V)
mkdir -p "reports/audit/${WEEK_ID}"
cp docs/templates/p2_audit_archive_manifest.md "reports/audit/${WEEK_ID}/manifest.md"
cp docs/templates/p2_kpi_delta_report.md "reports/audit/${WEEK_ID}/kpi_delta.md"
```

### 9.4 自動生成コマンド（推奨）

手作業による漏れを防ぐため、週次証跡は以下の1コマンドで生成する。

```bash
python scripts/weekly_audit_archive.py --operator "ops-team" --compare-to "<previous-week-id>" --hmac-secret "$DEMO_C_HMAC_SECRET"
```

出力:
- `reports/audit/YYYY-Www/` へ benchmarkログ・Demo C receipt・registry snapshot・triage noteを保存
- `manifest.md` / `kpi_delta.md` をテンプレートから初期化
- 実行結果のreturn codeと status（PASS/FAIL/SKIPPED）をJSON summaryで標準出力
- 実行時に `reports/operations/p2_integrated_summary.json` を自動更新し、横断レビュー導線を維持
- 統合サマリー出力先は `--integrated-summary-out` で上書き可能
- 既定では `FAIL` を含む場合にスクリプトは非0終了（`--no-fail-on-fail` で抑止可能）

### 9.5 月次 Gift Package リハーサル（推奨）

外部共有の再現性を担保するため、月次でGift Package再生成の実行証跡を保存する。

```bash
python scripts/monthly_gift_rehearsal.py --operator "ops-team"
python scripts/monthly_gift_rehearsal.py --operator "ops-team" --dry-run  # 月次事前検証
```

出力:
- `reports/gift_rehearsal/YYYY-MM/` へ `make_xai_gift.py` 実行ログを保存
- `manifest.md` をテンプレートから初期化し、required token 欠落時は失敗させて記録不整合を防止
- `summary.json` にステータス（PASS/FAIL/DRY_RUN）と実行メタデータ、および `manifest_consistent` / `dry_run` を記録
- `reports/gift_rehearsal/history_index.json` を自動更新し、month_id単位の履歴参照を固定
- `triage_note.md` に責任境界（記録責務と最終判断責務の分離）を明示
- 既定では失敗時に非0終了（`--no-fail-on-fail` で抑止可能）

### 9.6 週次・月次統合サマリー（Sprint-4 差分比較対応）

定常運用の横断レビュー時間を短縮するため、最新の週次監査アーカイブと月次Gift rehearsalを1ファイルへ集約する。

```bash
python scripts/p2_integrated_summary.py --out reports/operations/p2_integrated_summary.json
```

出力:
- `weekly.latest_week_id` / `monthly.latest_month_id` に最新ウィンドウIDを記録
- `reports/operations/p2_integrated_summary_diff.json` に前回実行との差分（changed_fields / changed_field_count）を記録
- `monthly.summary` に最新 `reports/gift_rehearsal/YYYY-MM/summary.json` の内容を埋め込み
- 月次 `summary.json` が破損している場合は `monthly.summary_error` と `overall.has_malformed_artifact` で検知
- 週次/月次の triage に `FAIL` 表記がある場合は `overall.has_reported_failures` を true 化
- 週次/月次それぞれの必須補助ファイル（manifest・triage・kpi_delta）の存在フラグを記録
- `responsibility_boundary` で自動化責務（集約）と人間責務（公開判断）を明示


### 9.7 KPI劣化アラート運用（Sprint-3 初動短縮）

KPI逸脱時は以下テンプレートをコピーし、初動15分以内に一次トリアージを記録する。

```bash
WEEK_ID=$(date +%G-W%V)
cp docs/templates/p2_kpi_alert.md "reports/audit/${WEEK_ID}/kpi_alert.md"
```

運用ルール:
- `metric_name / observed_value / threshold / comparison` を必須記入し、逸脱判定根拠を機械可読で残す。
- `Evidence` セクションは週次アーカイブ内の実ファイルパスを埋める。
- 公開可否の最終判断はテンプレート内 `Responsibility Boundary` に従い人間責務で確定する。

### 9.8 KPIアラート記入チェック（Sprint-4 自動検証）

記入済みのアラートファイルにプレースホルダーが残っていないか機械的に検証する。

```bash
# 単ファイル検証
python scripts/check_kpi_alert.py reports/audit/$(date +%G-W%V)/kpi_alert.md

# JSON出力モード（CI組み込み用）
python scripts/check_kpi_alert.py reports/audit/$(date +%G-W%V)/kpi_alert.md --json
```

判定:
- `is_valid: true` → 記入完了（プレースホルダーなし）
- `is_valid: false` → `unfilled_placeholders` に未記入項目の説明を列挙して終了コード 1 を返す

責任境界:
- **自動化責務**: プレースホルダートークンの機械検出まで。
- **人間責務**: アラート内容の妥当性・公開可否の最終判断。

### 9.9 異常フラグ通知ディスパッチ（Sprint-4 通知導線）

統合サマリーの `overall.has_reported_failures` / `overall.has_malformed_artifact` を通知エンベロープへ変換する。

```bash
# 通知JSONを生成（デフォルト出力: reports/operations/p2_alert_notification.json）
python scripts/dispatch_alert_notification.py

# stdout にも出力
python scripts/dispatch_alert_notification.py --json

# アラートがある場合に終了コード 1 を返す（CIゲート組み込み用）
python scripts/dispatch_alert_notification.py --fail-on-alert
```

出力フィールド:
- `has_alert`: 異常フラグのいずれかが true のとき true
- `severity`: `SEV-1`（両方）/ `SEV-2`（FAIL のみ）/ `SEV-3`（破損のみ）/ `NONE`
- `flags`: `has_reported_failures` / `has_malformed_artifact` の生値
- `evidence`: 週次/月次アーカイブへのパスリンク
- `responsibility_boundary`: 自動化責務（検知・通知生成）と人間責務（公開停止・対策承認）を明示
