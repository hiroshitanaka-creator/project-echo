# 🐷 Project Echo — 画面無しAI時代の透明性防衛フレームワーク

> **E.C.H.O** = **E**valuate **C**redibility of **H**ype & **O**pinions
> 誇張と意見の信頼性を評価する

**AIが「便利」を装って商業バイアスに操られるのを、システムレベルで防ぐ。**
Project Echoは、AI出力を「おすすめ」ではなく**候補セット＋証拠＋責任境界**として扱うための防衛フレームワークです。

[![License: AGPLv3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE) [![Commercial License](https://img.shields.io/badge/Commercial-Contact%20Required-orange.svg)](COMMERCIAL_LICENSE.md)
**Sister Project of [Po_core](https://github.com/hiroshitanaka-creator/Po_core)**

> **Dual License:** Free for non-commercial/research use (AGPLv3). Commercial use requires a separate license — see [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md).
> **License note:** Past tags (`v0.1.0` / `v0.3.0`) are MIT; current `main` branch is dual-licensed (AGPLv3 + Commercial).

---

## 不変原則（絶対）
- AIは「おすすめ」をしない。
- 常に **候補セット＋証拠＋責任境界** を返す。
- 最上位哲学は **「選択肢を残す」**。

---

## 🌟 これは何？

画面無しデバイス（screenless ambient device）が主流になる時代、AIはユーザー意思決定の中間層になります。  
Project Echoは、その中間層がブラックボックス化しないように、以下を機械的に強制します。

- 商業バイアス監査
- 候補多様性の注入
- 実行ゲートによる安全側判定
- 改ざん耐性のある Echo Mark 署名
- 音声系の責任境界維持（Voice Boundary / Ear Handshake / RTH）

---

## 🛡️ 主要機能

- **Receipt-style Commercial Bias Audit**
- **Diversity Noise Injection**（MMR + バイアス罰則）
- **Execution Gate**（Conservative Gate Pattern）
- **Echo Mark**（Ed25519 + HMAC Dual Signature）
- **Screenless Ambient Defense**（音声系リスク境界 + 監査）

---

## 📊 進捗サマリー

| フェーズ | 進捗率 | 判定 |
|---|---:|---|
| P0（基盤防御） | 100% | ✅ 完了 |
| P1（音声CLI・Demo C） | 100% | ✅ 完了 |
| P2（運用定着） | 100% | ✅ 完了 |

**次マイルストーン: v1.0.0**（公開監査運用 / webhook通知連携 / マルチデバイス対応）

### ✅ P0・P1 完了項目

- 商業バイアス監査・多様性注入・実行ゲートを実装
- Echo Mark v3（Ed25519主署名 + HMAC fallback / replay防御）を実装
- 音声系防御（Voice Boundary / Ear Handshake / RTH）を実装
- `po-cosmic voice` CLIサブコマンドを実装
- Gumdrop / World Register脅威モデルへの対策モジュールを追加
- 公開ベンチマークスイート（10k/100kケース）とCI benchmark gateを整備
- xAI Gift Package配布導線を完成

### ✅ P2 完了項目（Sprint-1〜Sprint-4）

- 週次/月次アーカイブの自動生成・統合サマリー diff 出力
- KPI劣化検知アラートテンプレート記入チェックCLI
- 異常フラグ（`has_reported_failures` / `has_malformed_artifact`）の通知エンベロープ化
- Gift rehearsal manifest / history index の自動更新
- 全168テストパス（property-based test を含む）

進捗詳細は [`PROGRESS.md`](PROGRESS.md) を参照してください。

---

## 🚀 クイックスタート

```bash
git clone https://github.com/hiroshitanaka-creator/project-echo.git
cd project-echo
pip install -e .
export ECHO_MARK_SECRET="demo-secret-key-16chars"
export ECHO_MARK_KEYS="v1=$ECHO_MARK_SECRET"
make demo-shopping
```

Echo Markを検証する例（`ECHO_MARK_SECRET` が16文字以上である必要があります）:

現在のデモバッジは `key_id="v1"` で署名されるため、`ECHO_MARK_KEYS` の `v1` マッピングが必要です（例: `export ECHO_MARK_KEYS="v1=$ECHO_MARK_SECRET"`）。

```bash
po-cosmic verify runs/high_bias_affiliate.badge.json
```

---



## 🎙️ Voice CLI（`po-cosmic voice`）

`src/po_echo` の Voice Boundary / Ear Handshake / RTH を薄いオーケストレーション層で束ね、CLIから**候補セット＋証拠＋責任境界**を返します。

固定JSON schema:
- Input: `{"intent": string, "transcript": string, "metadata": object}`
- Output: `{"candidate_set": array, "evidence": array, "responsibility_boundary": object, "voice_text": string, "echo_mark": object}`

```bash
export ECHO_MARK_SECRET="demo-secret-1234567890"
export ECHO_MARK_PRIVATE_KEY="1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100"

po-cosmic voice   --intent booking   --transcript "土曜夜、2名、予算1万円で予約候補"   --meta '{"amount": 10000}'   --simulate-ok   --in runs/high_bias_affiliate.audit.json   --out runs/voice_demo.json

# 固定schemaの確認
po-cosmic voice --show-schema --intent search --transcript "候補" --in runs/high_bias_affiliate.audit.json --out /tmp/unused.json
```

## 📍 OpenAI World Register 脅威モデル

Project Echoは、画面無しデバイス時代における「失敗しなかった意図」課金モデルの不透明化リスクを、
**検証可能性・責任境界・透明性表示**で抑制します。

- 詳細: [`docs/openai_world_register_threat.md`](docs/openai_world_register_threat.md)

---

## 🗺️ ロードマップ

- ✅ **v0.3.1**: P0クローズ、基盤防御稼働
- ✅ **v0.4.0**: P1完了（音声テスト拡張・voice CLI・Demo C・公開ベンチマーク）
- ✅ **v0.5.0**: P2運用定着（監査自動化・KPI継続監視・配布標準化）
- 🚀 **v1.0.0**（次フェーズ）: 公開監査運用を含む本番成熟

---


## 🧪 CIゲート運用（開発者向け判定基準）

PRでは**高速ゲートのみ必須**、重いbenchmarkは**定期ゲート**で実行します。

### PR必須ゲート（高速）
- `smoke`: lint / typing / smoke test
- `invariants`: 不変原則テスト（失敗時は違反原則サマリを出力）
- `prop-core`: property-based core test

マージ可否の基準:
- 3つすべてが `success` であること。
- `invariants` が失敗した場合は、CI summaryに表示される違反候補（例: `responsibility boundary missing/invalid`）を優先修正すること。

### 定期ゲート（重いbenchmark）
- `benchmark` workflow（毎週 + 手動実行）
- KPI基準:
  - Voice Boundary 10k: `min_seconds < 0.3`
  - RTH 100k: `tracker_entries <= max_seen_count`

運用判断:
- PRではbenchmark未実行でも可（高速性優先）。
- 週次benchmarkで失敗した場合は公開停止判断を含めて是正し、再計測で合格させること。

---

## 👤 Creator

**飛べない豚 (Flying Pig Philosopher)**  
X: [@Detours_is_Life](https://x.com/Detours_is_Life)

> AIの未来は、選択肢を残すことで守る。  
> 一緒に豚を飛ばそう。🐷🎈
