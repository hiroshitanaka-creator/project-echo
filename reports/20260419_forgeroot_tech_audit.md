# ForgeRoot 総合技術評価レポート

- 監査日: 2026-04-19 (UTC)
- 監査対象: `project-echo`
- 監査方式: 静的コードレビュー（主要ソース/設定/テストを直接精読）

## 1. エグゼクティブサマリー

### プロジェクト目的
Project Echo は、AIの出力を「おすすめ」ではなく「候補セット＋証拠＋責任境界」として強制し、商業バイアス抑制と監査可能性を担保する実装を中心に据えたフレームワーク。

### 技術スタック（実測）
- Python 3.11+（`pyproject.toml`）
- 主要依存は `pynacl`（Ed25519署名）
- テスト/品質: `pytest`, `hypothesis`, `ruff`, `mypy`
- 補助的に Node.js (`server.js`) を同梱

### 総合評価スコア
**84 / 100**

理由（要約）:
- 強い点: 署名検証・リプレイ対策・責任境界の明示・property-based test が実装レベルで徹底。
- 減点: 例外握りつぶしや責務混在（CLI/Scannerの肥大化）、一部エラーパスで KeyError を誘発し得る箇所が残存。

---

## 2. アーキテクチャと設計の評価

### 良い点
- エントリーポイントが明確: `po-cosmic` は `po_cosmic.cli:main` に集約される。
- Voice系は `voice_orchestration.py` で統合し、入力スキーマ、ハンドシェイク、ゲート、署名の流れが明示。
- `voice_boundary.attach_boundary` は upstream の境界を緩めない「fail-closed」なマージ戦略を採用。

### 課題
- `src/po_cosmic/cli.py` が多責務（引数処理、業務ロジック、表示、状態遷移、I/O）で肥大化。変更時の影響範囲が広い。
- `src/po_echo/sentinel_v2.py` は ASTスキャンと semantic diversity を同居させており、関心の分離が不十分。

---

## 3. コード品質と保守性

### 【Good】
1. **責任境界の単調性維持（安全側）**
   - `attach_boundary` で upstream `execution_allowed` と voice decision を AND 結合し、緩和を防止。
2. **自己署名トラストの拒否**
   - `verify_echo_mark` は badge内の `public_key` を信頼アンカーとして使わない設計。
3. **通知配信の実運用性**
   - Webhook の retry 対象をネットワーク障害に限定し、HTTP応答系は重送を避ける。
4. **Property-based test が広い不変条件を担保**
   - sentinel/voice で adversarial 条件を含む不変条件テストを実施。

### 【Bad/技術的負債】
1. **エラーハンドリング不整合（実バグ候補）**
   - `audit_requirements` はファイル欠落時に `{"error":...}` を返すが、`run_audit` 側は `score`/`dominant_vendor` 前提で参照しており KeyError になり得る。
2. **例外の握りつぶしが広すぎる箇所**
   - `sentinel_v2.scan_directory` の `except Exception` は構文不正やファイルI/O異常を単に表示して継続するため、監査の完全性を誤認させる恐れ。
   - `echo_mark_verify.verify_echo_mark` の最上位 `except Exception` も同様にバグと検証失敗の区別を曖昧化。
3. **設計凝集度**
   - `cli.py` の責務集中は保守性・テスト容易性の低下要因。

---

## 4. セキュリティとパフォーマンスのリスク

### セキュリティ
- **肯定的所見**
  - Ed25519/HMAC 両系統を持ち、nonce/timestamp 付きのリプレイ防止を実装。
  - インライン公開鍵の自己信頼を禁止（外部信頼源必須）。
- **リスク所見**
  - スキャナ/検証器の広域 `except` は、攻撃ではなく実装修正の退行を見逃す温床。
  - `sentinel.py` のエラーパス破綻（前述）は CI 安定性リスク。

### パフォーマンス
- `scan_directory` は `os.walk` で `.py` を全探索するため、巨大リポジトリでは線形に重くなる。
- Webhook retry は指数的バックオフだが上限3回で制御され、運用上は許容範囲。

---

## 5. 改善のためのネクストアクション（優先順位順）

1. **[Highest] `sentinel.py` のエラーパスを fail-safe 化**
   - `run_audit` で `error` キー分岐を追加し、KeyError を防止。CLI終了コードを明確化。
2. **[Medium] 例外ポリシーの整理**
   - `except Exception` の適用範囲を縮小し、監査不能状態を「失敗」として明示。
3. **[Low] CLI/Scanner の責務分離**
   - `cli.py` をサブコマンド別モジュールへ分割、`sentinel_v2` を scanner と semantic 層に分離。



---

## 6. 95点到達ロードマップ（機能削減禁止）

前提: **既存機能は一切削除しない**。すべて「安全性・運用性・保守性の上積み」で95点を目指す。

### Phase 1（即効: 1〜2週間）— 84点 → 88点
- `sentinel.py` のエラーパス整合: `error` 応答時の表示/終了コードを明確化し、KeyError経路を排除。
- `sentinel_v2.scan_directory` の例外粒度を分離（構文エラー、I/Oエラー、権限エラー）し、監査不能件数を明示出力。
- `verify_echo_mark` の top-level `except Exception` を段階化し、実装バグと署名不正を区別できる reason を返す。
- 上記3点に対する unit test/property test を追加し、退行をCIで固定。

### Phase 2（構造改善: 2〜4週間）— 88点 → 91点
- `po_cosmic/cli.py` をサブコマンド単位（cosmic39 / voice / verify / audit）に分割し、表示層と業務ロジック層を分離。
- `sentinel_v2.py` を scanner層 と semantic-diversity層に分離し、責務境界を明確化。
- 既存 public API 互換テストを追加し、機能縮退なしを自動検証。

### Phase 3（セキュリティ強化: 3〜5週間）— 91点 → 93点
- Echo Mark鍵運用の強化: key rotation手順をCLI化し、期限切れ鍵/失効鍵の検証シナリオを標準化。
- 監査ログ（RTH/Merkle/Public Audit）に対し「改ざん検証の定期ジョブ」を追加。
- webhook dispatch に通知先別の失敗メトリクス（成功率・遅延）を追加し、運用での劣化を早期検知。

### Phase 4（性能・運用完成: 3〜4週間）— 93点 → 95点
- `scan_directory` の大規模リポジトリ向け最適化（除外パターン強化、並列走査オプション、差分スキャン）を追加。
- property-based test の実行プロファイルを2段化（PR軽量 / nightly重厚）して速度と検出力を両立。
- KPIダッシュボード（失敗率、再送率、検証失敗率、平均処理時間）を運用SLOに接続。

### 完了判定（Definition of Done）
- 既存コマンド/既存出力スキーマ互換: **100%維持**。
- 重大例外の未分類件数: **0**。
- セキュリティ回帰テスト（署名/リプレイ/失効鍵）: **全パス**。
- 大規模監査ジョブの処理時間: 現状比 **30%以上短縮**（同等精度）。
