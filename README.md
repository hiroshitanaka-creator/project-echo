# 🐷 Project Echo — 画面無しAI時代の透明性防衛フレームワーク

**AIが「便利」を装って商業バイアスに操られるのを、システムレベルで防ぐ。**  
Project Echoは、AI出力を単一推奨ではなく**候補セット＋証拠＋責任境界**として扱うための防衛フレームワークです。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)  
**Sister Project of [Po_core](https://github.com/hiroshitanaka-creator/Po_core)**

---

## 不変原則（絶対）
- AIは単一推奨をしない。
- 常に **候補セット＋証拠＋責任境界** を返す。
- 最上位哲学は **「選択肢を残す」**。

---

## ✅ P1遷移チェックポイント（v0.4.0 start）

P0は完了し、P1は**実装未着手**です。現在は「開始判定のための文書整合」を完了した状態です。

- 候補セット: `開始する / 延期する / 是正優先`
- 証拠: `PROGRESS.md`, `docs/threat_model.md`, `AGENT.md` の責務境界整合
- 責任境界: 材料提示はシステム責務、最終承認は人間/組織責務

進捗詳細は [`PROGRESS.md`](PROGRESS.md) を参照してください。

---

## 🛡️ 主要機能

- **Receipt-style Commercial Bias Audit**
- **Diversity Noise Injection**（MMR + バイアス罰則）
- **Execution Gate**（Conservative Gate Pattern）
- **Echo Mark**（Ed25519 + HMAC Dual Signature）
- **Screenless Ambient Defense**（音声系リスク境界 + 監査）

---

## 🚀 クイックスタート

```bash
git clone https://github.com/hiroshitanaka-creator/project-echo.git
cd project-echo
pip install -e .
make demo-shopping
```

Echo Markを検証する例:

```bash
po-cosmic verify --badge runs/demo_shopping/01_high_bias_affiliate_badge.json
```

---

## 📍 OpenAI World Register 脅威モデル

Project Echoは、画面無しデバイス時代における「失敗しなかった意図」課金モデルの不透明化リスクを、
**検証可能性・責任境界・透明性表示**で抑制します。

- 詳細: [`docs/openai_world_register_threat.md`](docs/openai_world_register_threat.md)
- 基本脅威モデル: [`docs/threat_model.md`](docs/threat_model.md)

---

## 🗺️ ロードマップ

- P1（1〜2ヶ月）: 音声系 property-based test拡張、`po-cosmic voice`、Demo C
- P2（3〜6ヶ月）: 統合運用テンプレート、監査運用自動化
- v1.0: 公開監査運用を含む本番成熟

---

## 👤 Creator

**飛べない豚 (Flying Pig Philosopher)**  
X: [@Detours_is_Life](https://x.com/Detours_is_Life)

> AIの未来は、選択肢を残すことで守る。  
> 一緒に豚を飛ばそう。🐷🎈
