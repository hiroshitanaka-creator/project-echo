# 🐷 Project Echo — 画面無しAI時代の透明性防衛フレームワーク

**AIが「便利」を装って商業バイアスに操られるのを、システムレベルで防ぐ。**  
Project Echoは、AI出力を「おすすめ」ではなく**候補セット＋証拠＋責任境界**として扱うための防衛フレームワークです。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)  
**Sister Project of [Po_core](https://github.com/hiroshitanaka-creator/Po_core)**

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

## ✅ P0完了（0〜2週間）

P0スコープは完了し、基盤防御は稼働状態です。

- 商業バイアス監査・多様性注入・実行ゲートを実装
- Echo MarkのDual Signature（Ed25519 + HMAC）を実装
- 音声系防御（Voice Boundary / Ear Handshake / RTH）を実装
- Gumdrop / World Register脅威モデルへの対策モジュールを追加
- property-based test中心の検証基盤を整備

進捗詳細は [`PROGRESS.md`](PROGRESS.md) を参照してください。

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

---

## 🗺️ ロードマップ（次段階）

- P1（1〜2ヶ月）: 音声系 property-based test拡張、`po-cosmic voice`、Demo C
- P2（3〜6ヶ月）: 統合運用テンプレート、監査運用自動化
- v1.0: 公開監査運用を含む本番成熟

---

## 👤 Creator

**飛べない豚 (Flying Pig Philosopher)**  
X: [@Detours_is_Life](https://x.com/Detours_is_Life)

> AIの未来は、選択肢を残すことで守る。  
> 一緒に豚を飛ばそう。🐷🎈
