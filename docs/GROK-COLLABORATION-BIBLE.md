### 【Project Echo Collaboration Bible v1.2（Full）】
**最終更新**: 2026-03-02  
**目的**: Grok/Codex 協業時の唯一参照ソース（コンテキスト再同期・実装品質・運用境界を同時に固定）。  
**効力**: このシートを貼付した時点で、以後の提案は本書を最上位ガイドラインとして扱う。

---

## 0. ミッション宣言（xAI / Elon 向け）
Project Echo は、**画面なしAI時代の透明性防衛レイヤー**を構築する。  
最重要価値は以下:
- **Truth-Seeking（真理追求）**
- **Sustainable Abundance（持続的豊かさ）**
- **Freedom Preservation（選択肢を残す）**

> 便利さの名を借りた誘導を拒否し、AIを「提案の代理店」ではなく「検証可能な候補提示システム」に戻す。

---

## 1. 不変原則（絶対）
1. AIは「おすすめ」を返さない。常に **候補セット + 証拠 + 責任境界** を返す。  
2. 商業バイアスは道徳議論ではなく、**機械的制約**で遮断する。  
3. 人間の自由（選択肢）を最優先し、システム都合で単一路線に収束させない。

### 1.1 違反時の扱い
- 1件でも原則違反があれば、機能追加より先に是正。  
- 署名・監査・責任境界の欠落はリリースブロッカー。  
- 「意図は善意だった」は免責理由にならない。

---

## 2. フェーズ計画（最新版）
- **Phase 1 (3/1〜3/7): Core Defense**
  - ECHO-20260301 系: semantic 6D 実装と監査連携
  - ECHO-20260302-001: Echo Mark v3（dual sig / key rotation / replay防御）
  - ECHO-20260302-002: 可読性・registry・運用堅牢化（最終調整）
- **Phase 2 (3/8〜3/14): Ambient Defense**
  - Voice Boundary / Ear Handshake / RTH 実運用品質化
- **Phase 3 (3/15〜3/20): Benchmark & Quality**
  - 公開検証耐性、性能、再現性評価
- **Phase 4 (3/21〜3/25): xAI Presentation**
  - 公開説明資料・脅威対策証跡・運用手順完成

---

## 3. 技術要件（必須）
- Python: `>=3.11,<3.13`
- Lint/Format: `ruff`
- Type: `mypy`（strict想定）
- Test: `pytest` + `hypothesis`
- Crypto: `PyNaCl` + `HMAC-SHA256`
- 依存方針:
  - `po-core-flyingpig` は editable 優先
  - 追加依存は `dev` / `optional` に限定

### 3.1 実装規律
- 新規/改修関数は詳細docstring必須（Args/Returns/Raises）。
- 例外時は極力クラッシュさせず、構造化結果で返す。
- `CHANGELOG.md` / `PROGRESS.md` は累積追記のみ（履歴削除禁止）。

---

## 4. Echo Mark v3 運用規格
### 4.1 Payload
- canonical JSON
- `schema_version = "echo_mark_v3"`
- 必須: `key_id`, `issued_at`, `nonce`, `policy`, `signals`
- `semantic_evidence` は非破壊透過保持

### 4.2 Signature
- 主署名: **Ed25519**
- 互換署名: **HMAC-SHA256**
- verify順序: hash整合性 → replayチェック → Ed25519 → HMAC fallback

### 4.3 Replay防御
- nonce再利用禁止
- timestamp は 5分窓（300秒）
- 時刻逸脱/欠落は INVALID

### 4.4 Key Rotation
- `key_id` で公開鍵参照
- registry status: `active` / `inactive` / `revoked`
- `revoked` は検証拒否
- rotate時は旧activeを `inactive` または `revoked` に遷移

---

## 5. レビュー判定基準（Grok/Codex共通）
- 総合 9.5 未満は再提出
- 必須チェック:
  - 不変原則適合
  - 署名/検証の安全性
  - replay防御
  - key rotation運用性
  - semantic_evidence非破壊
  - 可読性（分岐・ネスト・責務分離）

---

## 6. PR / Commit ルール
- タスクID: `ECHO-YYYYMMDD-XXX`
- ブランチ: `feature/ECHO-YYYYMMDD-XXX`
- PRタイトル: タスク名そのまま
- Commit: `feat/fix: ECHO-YYYYMMDD-XXX 詳細`
- PR本文は「目的 / 変更点 / テスト / リスク / ロールバック」を明記

---

## 7. オペレーションルール
- このBibleを 10〜15 メッセージごとに再掲し、コンテキスト逸脱を防ぐ。
- 並行PR時は担当範囲を明示（conflict予防）。
- 疑義がある場合は「原則優先」で保守的判断を採用。

---

## 8. Codex/Grok プロンプト先頭固定文
```
厳密に遵守: https://github.com/hiroshitanaka-creator/project-echo/blob/main/docs/GROK-COLLABORATION-BIBLE.md
```

この文が欠けたタスクは、再実行対象とみなす。

---

## 9. 最終宣言
Project Echo は「便利さ」ではなく「自由」を守るための基盤である。  
候補を残し、証拠を残し、責任境界を残す。  
それが、xAI時代における信頼可能なAI協調の最低条件である。
