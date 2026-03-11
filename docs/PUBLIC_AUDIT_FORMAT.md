# Public Audit Manifest Format

**Schema version**: `public_audit_v1`
**Module**: `src/po_echo/public_audit.py`
**CLI**: `python scripts/export_public_audit.py`

---

## 概要

Project Echo の公開監査マニフェスト（Public Audit Manifest）は、内部運用データ（統合サマリー・KPI証跡）を**外部レビュー可能な形式**に変換した JSON ファイルです。

### 設計原則

| 原則 | 実装 |
|---|---|
| 候補セット＋証拠＋責任境界 | `kpi_status` / `audit_coverage` / `responsibility_boundary` を必須フィールドとして固定 |
| 内部情報の非開示 | `archive_dir` / `operator` 等の内部パスを自動リダクション |
| 改ざん検知 | `integrity.sha256` による SHA-256 チェックサム（core payload の決定論的 JSON から計算） |
| ゼロ依存検証 | `verify_public_audit_manifest(manifest)` は標準ライブラリのみで検証可能 |

---

## フィールド仕様

```json
{
  "schema_version": "public_audit_v1",
  "project": "Project Echo",
  "kpi_status": {
    "has_reported_failures": false,
    "has_malformed_artifact": false,
    "has_weekly_and_monthly": true
  },
  "audit_coverage": {
    "latest_week_id": "2026-W10",
    "latest_month_id": "2026-02",
    "weekly_has_triage_note": true,
    "weekly_has_manifest": true,
    "weekly_has_kpi_delta": true,
    "monthly_has_triage_note": true,
    "monthly_has_manifest": true
  },
  "invariant_compliance": {
    "principle": "候補セット＋証拠＋責任境界",
    "candidates_provided": true,
    "evidence_provided": true,
    "responsibility_boundary_provided": true,
    "note": "..."
  },
  "generated_at_utc": "2026-03-11T12:00:00Z",
  "responsibility_boundary": {
    "automation_scope": "...",
    "human_scope": "..."
  },
  "integrity": {
    "sha256": "<64 hex chars>"
  }
}
```

### フィールド詳細

| フィールド | 型 | 説明 |
|---|---|---|
| `schema_version` | string | `public_audit_v1`（非互換変更時にバンプ） |
| `project` | string | プロジェクト名 |
| `kpi_status.has_reported_failures` | bool | 直近監査に FAIL 記録があるか |
| `kpi_status.has_malformed_artifact` | bool | 証跡 JSON が破損しているか |
| `kpi_status.has_weekly_and_monthly` | bool | 週次・月次両方の証跡が存在するか |
| `audit_coverage.latest_week_id` | string\|null | 最新週次 ID（`YYYY-Www`） |
| `audit_coverage.latest_month_id` | string\|null | 最新月次 ID（`YYYY-MM`） |
| `audit_coverage.*_has_*` | bool | 各証跡ファイルの存在フラグ |
| `invariant_compliance` | object | 不変原則準拠の自己申告（外部レビュアーが証跡と照合） |
| `generated_at_utc` | string | ISO-8601 UTC タイムスタンプ |
| `responsibility_boundary` | object | 自動化スコープと人間責任スコープの明示 |
| `integrity.sha256` | string | core payload（`generated_at_utc` / `responsibility_boundary` / `integrity` 除外）の SHA-256 |

---

## 生成手順

```bash
# 1. 統合サマリーを最新化
python scripts/p2_integrated_summary.py

# 2. 公開監査マニフェストを生成
python scripts/export_public_audit.py

# 出力: reports/operations/public_audit_manifest.json
```

### オプション

```bash
# 出力先を指定
python scripts/export_public_audit.py --out /tmp/audit_2026-W10.json

# 機械可読 JSON 出力
python scripts/export_public_audit.py --json

# 既存マニフェストの整合性検証
python scripts/export_public_audit.py --verify
python scripts/export_public_audit.py --verify --out /tmp/audit_2026-W10.json
```

---

## 外部レビュアー向け検証手順

外部レビュアーはマニフェストを受け取った後、以下のコードで整合性を検証できます。
**内部ツールへの依存は不要**です。

```python
import hashlib, json

def verify(manifest: dict) -> bool:
    stored = (manifest.get("integrity") or {}).get("sha256")
    if not stored:
        return False
    core = {
        k: v for k, v in manifest.items()
        if k not in {"generated_at_utc", "responsibility_boundary", "integrity"}
    }
    digest = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return stored == digest

with open("public_audit_manifest.json", encoding="utf-8") as f:
    m = json.load(f)

print("VERIFIED" if verify(m) else "INTEGRITY CHECK FAILED")
```

---

## リダクション対象フィールド

以下のキーは内部情報保護のため、公開マニフェストへ**出力されません**。

| キー | 理由 |
|---|---|
| `archive_dir` | 内部ディレクトリパス |
| `output_path` | 内部出力パス |
| `diff_path` | 内部差分ファイルパス |
| `operator` | オペレーター識別子 |
| `monthly_archive_dir` | 内部月次ディレクトリパス |
| `weekly_archive_dir` | 内部週次ディレクトリパス |
| `integrated_summary_path` | 内部サマリーパス |

---

## 責任境界

| スコープ | 主体 |
|---|---|
| 公開マニフェスト生成・KPIフラグ抽出・整合性チェックサム計算 | 自動化（このモジュール） |
| 公開可否判断・リスク受容・対外説明・是正承認・最終監査判定 | 運用者 / 組織 |
