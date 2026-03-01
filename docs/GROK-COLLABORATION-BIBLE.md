### 【Project Echo Collaboration Bible v1.6（Full）】
**最終更新**: 2026-03-06  
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

## 4. Echo Mark v3 運用規格（v1.3確定）
### 4.1 Payload Contract
- canonical JSON（`sort_keys=True`, `separators=(',', ':')`）を唯一の署名対象とする。
- `schema_version = "echo_mark_v3"` を必須化。
- 必須フィールド:
  - `key_id`
  - `issued_at`（ISO8601 / UTC）
  - `nonce`
  - `policy`
  - `signals`
- `semantic_evidence` は**非破壊透過保持**（順序再構成・内容削除を禁止）。
- Echo Mark本文の正規化は署名処理より前段で確定し、署名後の再正規化は禁止。

### 4.2 Signature Contract
- 主署名: **Ed25519**（`signature_ed25519`）
- 互換署名: **HMAC-SHA256**（`signature_hmac`）
- 署名対象は必ず `payload_hash` 一致済み payload のみ。
- verify順序（固定）:
  1. hash整合性チェック
  2. replayチェック（nonce + 時刻窓）
  3. Ed25519検証
  4. HMAC fallback検証
- Ed25519が検証可能な環境では、HMAC単独成功を最終成功とみなさない方針を推奨。

### 4.3 Replay 防御
- nonce再利用禁止（同一 `key_id` / time-window 内は厳格拒否）。
- timestamp は 5分窓（±300秒）で評価。
- 時刻逸脱・欠落・未来過大値は **INVALID**。
- 検証失敗時は理由コード（`replay_detected`, `timestamp_out_of_window` 等）を監査ログへ記録。

### 4.4 Key Rotation / Registry 運用
- `key_id` により公開鍵を registry 解決。
- registry status: `active` / `inactive` / `revoked`。
- `revoked` は常時検証拒否。
- rotate時は旧activeを `inactive` もしくは `revoked` へ遷移。
- key更新は監査イベント（誰が・いつ・なぜ）を必須記録。

### 4.5 Echo Mark v3 判定ラベル運用
- `VERIFIED`: hash + replay + signature を満たす。
- `BLOCKED`: 境界ポリシー上の実行拒否（署名系は成立している場合あり）。
- `INVALID`: payload整合性・署名・時刻・replayのいずれかで破綻。
- 監査UI/ログでは `BLOCKED` と `INVALID` を混同しない。


### 4.6 Phase 2 Ambient Defense 運用規格（Voice Boundary / RTH）
- **責任境界ルール**:
  - `low`: 自動実行可。ただし Echo Mark receipt へ責任境界 (`required_action`) を必ず付与。
  - `medium`: `double_tap` 等の明示的 human confirm を必須化。
  - `high`: `app_confirm` を強制し、screenless 単独での最終実行を禁止。
- **RTH collision対応**:
  - chain hash 追跡は bounded + TTL 構造を使い、メモリ上限超過と stale entry を機械的に prune。
  - 衝突検知時は warning ログ (`rth_chain_hash_collision_detected`) を出力し、監査で追跡可能にする。
  - 追跡キーは blake2b fingerprint を用いてメモリ効率と可搬性を両立。
- **screenless config例**:
  - `high_bias_block_threshold = 0.60`
  - `low_battery_threshold = 0.15`
  - `fallback_mode_normal = "normal"`
  - `fallback_mode_safe = "on_device_safe_mode"`
  - `block_required_action = "app_confirm"`
  - しきい値はハードコード禁止、config オブジェクト経由で注入可能にする。


### 4.7 Phase 3 Benchmark & Quality 運用規格（v1.4追加）
- **再現性固定化**:
  - benchmark生成は Hypothesis の固定seedを必須化し、型strategyは `register_type_strategy` で明示登録する。
  - benchmark実行は `RUN_PUBLIC_BENCHMARKS=1` を前提とし、CIとローカルで同一コマンドを使う。
- **公開KPI（厳格版）**:
  - Voice Boundary 10k ケース: `min_seconds < 0.3` を必達。
  - RTH 100k windows: `tracker_entries <= max_seen_count` を必達。
- **CI統合ルール**:
  - `.github/workflows/benchmark.yml` で schedule + manual dispatch を提供し、KPI違反は job fail にする。
  - benchmark job は品質ゲートの補完であり、通常CI（lint/type/test）を置換しない。
- **非破壊ルール（Phase 3）**:
  - 既存 `BENCHMARK_RESULTS.md` の実測履歴、`tracemalloc` 計測、Hypothesis生成、`__repr__/__str__` は破壊しない。
  - 既存防御ロジック（Echo Mark / Voice Boundary / RTH）の意味変更は禁止。



### 4.8 Phase 4 xAI Gift Package 運用規格（v1.5追加）
- **デフォルト鍵禁止**:
  - Demo/CLI含め、秘密鍵・共有鍵のハードコード配布は禁止。
  - 署名CLIは `--ed25519-private-key` または `--hmac-secret` の明示入力を必須化し、未指定時は安全な生成手順を返して停止する。
- **配布物の再現可能生成**:
  - xAI贈呈物は `python scripts/make_xai_gift.py` の単一コマンドで生成可能であること。
  - zipには docs一式、Demo C CLI、benchmark証跡、変更履歴（CHANGELOG/PROGRESS）を必ず含める。
- **依存導線の一元化**:
  - CI benchmarkは `pyproject.toml` の optional dependencies (`.[dev]`) のみを参照し、重複する requirements 系導線を増やさない。
- **贈呈前チェックリスト**:
  1. benchmark gate の実行経路がCI/ローカルで一致していること。
  2. Demo C 署名検証が `VERIFIED` を返すこと（環境差分時は理由を明記）。
  3. プレゼン資料は Markdown→PDF 変換コマンドを同梱すること。
  4. Bible / CHANGELOG / PROGRESS の履歴追記が完了していること。
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


---

## 10. v1.6 Final Pre-Gift Cleanup 規格（ECHO-20260306-001）
- Echo Mark v3移行後は、テスト期待値（timestamp引数、schema_version、署名フィールド）を実装契約と完全同期させる。
- hardcoded key検知は Doberman を Gift package 生成前に必ず実行し、漏洩時は zip 生成を即時中断する。
- `hidden_lockin` のような教育用fixtureは `sk-dummy-...` と「デモ用ダミー」注記を必須化する。
- Gumdrop軽量監査は affiliate フラグ単独に依存せず、FreedomPressureV2互換スナップショットを伴う観測可能指標を使う。
- 空レジストリはファイルではなくディレクトリとして保持し、存在意義を README で説明する。
- `pocore` は deprecated として明示し、`po_core` への移行導線を壊さず維持する。
