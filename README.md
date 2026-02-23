# 🐷 Project Echo — 画面無しAI時代の透明性防衛フレームワーク

**AIが「便利」を装って商業バイアスに操られるのを、システムレベルで防ぐ。**  
OpenAIの「World Register」戦略（状態保持チップ＋「失敗しなかった意図」課金モデル）に対する直接カウンター。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
**Sister Project of [Po_core](https://github.com/hiroshitanaka-creator/Po_core)**

---

## 🌟 これは何？

画面無しデバイス（screenless ambient device）が主流になる時代、  
AIはユーザーの「意図」に責任を持つ中間層になろうとしています。  
しかしその「責任」は**不透明**です。

Project Echoは**改ざん耐性のあるEcho Mark**で、  
- 商業バイアスを監査  
- 多様性を強制注入  
- 実行をゲート  
- すべての判断を検証可能にする  

ことで、**選択肢を残す**ことを強制します。

---

## 🛡️ 主要機能

- **Receipt-style Commercial Bias Audit**  
- **Diversity Noise Injection**（MMR + バイアス罰則）  
- **Execution Gate**（Conservative Gate Pattern）  
- **Echo Mark**（Ed25519 + HMAC Dual Signature）  
- **screenless ambient defense**（画面無しデバイス専用モジュール追加済み）

---

## 🚀 クイックスタート

```bash
git clone https://github.com/hiroshitanaka-creator/project-echo.git
cd project-echo
pip install -e .
make demo-shopping
