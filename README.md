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
- **Multi-Device Boundary Adapters**（マルチデバイス責任境界アダプタ）

---

## 📊 進捗サマリー

| フェーズ | 進捗率 | 判定 |
|---|---:|---|
| P0（基盤防御） | 100% | ✅ 完了 |
| P1（音声CLI・Demo C） | 100% | ✅ 完了 |
| P2（運用定着） | 100% | ✅ 完了 |
| v1.0.0（本番成熟） | 100% | ✅ 完了 |
| v1.1.0（運用強化） | 100% | ✅ 完了 |

**次マイルストーン: v1.2.0**（定常運用安定化 / CI全カバレッジ維持 / policy lab 本格運用）

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

### ✅ v1.0.0 完了項目

- 公開監査マニフェスト（`public_audit_v1` スキーマ / 改ざん検知チェックサム）
- Slack / PagerDuty 実webhook連携（`webhook_dispatch.py`）
- KPI CI自動化（PR毎の benchmark 結果コメント自動投稿）
- マルチデバイス境界アダプタ（SmartSpeaker / SmartWatch / ARGlasses）
- `po-cosmic device` CLI サブコマンド（device_boundary の CLI統合）

### ✅ v1.1.0 完了項目

- **CI全カバレッジ**: 未実行だった16テストファイルをCIに追加。Smoke / Unit / Voice integration の3ステップに整理
- **Webhook dispatch強化**: リトライ対象をネットワーク例外のみに限定（5xx はリトライしない）、`X-Request-Id` ヘッダー付与
- **Voice integration テスト**: `run_voice_flow()` APIを直接呼ぶ14件の統合テストを追加
- **Property-based テスト拡充**: `test_prop_sentinel_v2.py`（7件）で意味的多様性の不変条件を検証
- **policy_v1 パッケージ移管**: `pocore/policy_v1` → `po_core/policy_v1` へ正規化
- **Policy Lab**: 閾値摂動レポート生成スクリプト（`scripts/policy_lab.py`）を正規パッケージ参照に修正
- **mypy設定一元化**: `pyproject.toml` を唯一の設定源として `warn_redundant_casts / warn_unused_ignores` を有効化
- **オペレーター向けガイド**: `docs/operations.md`（env var一覧 / キー生成 / ローテーション手順）を追加
- **全306テストパス**（property-based test / hypothesis statistics 含む）

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

## 🐷 Flying Pig Mascot — Project Echo公式マスコット

![Flying Pig](https://raw.githubusercontent.com/hiroshitanaka-creator/project-echo/main/IMG_9074.jpeg)

**Flying Pig (飛べない豚)** is the official mascot of Project Echo.

> "豚も飛べるかも。でも飛んでいい豚かどうかは、Echo Markが決める。"
> *("Even a pig might fly. But whether it *should* fly — that's for the Echo Mark to decide.")*

### Mascot Behavior

| Echo Mark Label | Pig State |
|---|---|
| `ECHO_VERIFIED` — low bias | 🐷🌈 Pig flies freely, ripples spread |
| `ECHO_CHECK` — human confirm needed | 🐷⚠️ Pig hovers cautiously |
| `ECHO_BLOCKED` — high bias | 🐷💥 "Buhi!" — pig is grounded |

The ripple animation on the SVG badge represents Echo Mark signatures propagating
as verifiable receipts — tamper-evident, auditable, traceable.

**Creator:** 飛べない豚 [@Detours_is_Life](https://x.com/Detours_is_Life)

---

## 🌐 Web Demo Dashboard (`make demo-web`)

```bash
export ECHO_MARK_SECRET="demo-secret-key-16chars"
export ECHO_MARK_PRIVATE_KEY="1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100"
pip install -e ".[demo]"
make demo-web
# Open http://localhost:7860
```

Enter a **voice intent** and **transcript** in the browser UI. The demo:
1. Calls `po_echo.voice_orchestration.run_voice_flow()` directly
2. Displays the candidate set (diversified, bias-audited)
3. Shows the dual-signed Echo Mark badge (Ed25519 + HMAC-SHA256)
4. Animates the Flying Pig mascot based on the bias verdict

## 🌐 Node Gateway (`server.js`)

`server.js` は固定成功レスポンスではなく、実装済み能力を明示する薄いゲートウェイです。

- `GET /health`: ヘルスチェック
- `GET /api/voice/schema`: canonical Python (`po_echo.voice_orchestration`) の schema/inventory を返却
- `POST /api/voice/run`: 永続 trust/session 基盤未接続のため、構造化 `501 not_implemented` を返却

Node 側で責任境界判定・署名検証ロジックは重複実装せず、Python を唯一の判定源として保持します。

---

## 🏅 Echo Mark SVG Badge (`make generate-badge`)

Generate a v1-certified flying pig badge from any badge JSON:

```bash
# After running demo-shopping:
make generate-badge BADGE=runs/high_bias_affiliate.badge.json
# → runs/high_bias_affiliate.badge.svg

# Or directly:
python tools/generate_badge.py runs/high_bias_affiliate.badge.json -o my_badge.svg
```

The SVG badge shows:
- `ECHO VERIFIED` / `ECHO CHECK` / `ECHO BLOCKED` label in brand colour
- "v1 certified flying pig" inscription
- Animated ripple rings (VERIFIED state only)
- Schema version (`echo_mark_v3`)

To regenerate the animated GIF:

```bash
pip install Pillow
python assets/flying_pig_anim.py
```

---

## 🎙️ Voice CLI（`po-cosmic voice`）

`src/po_echo` の Voice Boundary / Ear Handshake / RTH を薄いオーケストレーション層で束ね、CLIから**候補セット＋証拠＋責任境界**を返します。

固定JSON schema:
- Input: `{"intent": string, "transcript": string, "metadata": object, "device_id": string, "challenge_id": string, "response_hex": string}`
- Output: `{"candidate_set": array, "evidence": array, "responsibility_boundary": object, "voice_text": string, "echo_mark": object}`

```bash
export ECHO_MARK_SECRET="demo-secret-1234567890"
export ECHO_MARK_PRIVATE_KEY="1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100"
export ECHO_TRUSTED_DEVICE_SECRETS="default=abababababababababababababababababababababababababababababababab"

po-cosmic voice   --intent booking   --transcript "土曜夜、2名、予算1万円で予約候補"   --meta '{"amount": 10000}'   --simulate-ok   --device-secret "abababababababababababababababababababababababababababababababab"   --in runs/high_bias_affiliate.audit.json   --out runs/voice_demo.json

# 固定schemaの確認
po-cosmic voice --show-schema --intent search --transcript "候補" --in runs/high_bias_affiliate.audit.json --out /tmp/unused.json
```

> Ear Handshake は登録済み device_id との照合を必須化しています。`--device-secret` 単体では認証に使えず、`ECHO_TRUSTED_DEVICE_SECRETS` 側の登録と一致した場合のみ通過します。

## 📱 マルチデバイス対応（`device_boundary.py`）

`src/po_echo/device_boundary.py` が `voice_boundary.py` を継承・拡張し、4種類のデバイスに対して**同一の責任境界契約**を機械的に強制します。

| デバイス | 確認手段（medium） | bias 閾値 | 特徴 |
|---|---|---|---|
| `earworn` | `double_tap` | 0.6 | Sweetpea耳装着型（基準実装） |
| `smart_speaker` | `voice_passphrase` | **0.5**（より厳格） | 共有空間、タッチ不可 |
| `smart_watch` | `haptic_tap` | 0.6 | ハプティクス＋小画面 |
| `ar_glasses` | `gaze_confirm` | 0.6 | 視線確認＋音声ハイブリッド |

**不変原則（全デバイス共通）:**
- high-risk → `requires_human_confirm = True`（固定）
- `bias_score >= 閾値` / `replay_detected` / `tamper_detected` → `execution_allowed = False`（固定）
- `responsibility_boundary` は常に `channel / device / risk / required_action / reasons` を含む

```python
from po_echo.device_boundary import decide_for_device

# SmartSpeaker でのbooking（medium → voice_passphrase）
dec = decide_for_device("smart_speaker", "booking", bias_score=0.1)
print(dec.required_action)   # "voice_passphrase"
print(dec.requires_human_confirm)  # True

# 高バイアスは全デバイスで自動ブロック
dec = decide_for_device("ar_glasses", "search", bias_score=0.7)
print(dec.execution_allowed)  # False
```

または `po-cosmic device` CLI から直接実行:

```bash
# SmartSpeaker での booking → voice_passphrase
po-cosmic device --device smart_speaker --intent booking

# 高バイアスで ARGlasses → ブロック
po-cosmic device --device ar_glasses --intent search --bias-score 0.7

# 登録デバイス一覧
po-cosmic device --list-devices --intent dummy

# 結果をファイルへ保存
po-cosmic device --device smart_watch --intent payment --out runs/device_result.json
```

---

## 📍 OpenAI World Register 脅威モデル

Project Echoは、画面無しデバイス時代における「失敗しなかった意図」課金モデルの不透明化リスクを、
**検証可能性・責任境界・透明性表示**で抑制します。

- 詳細: [`docs/openai_world_register_threat.md`](docs/openai_world_register_threat.md)

---

## 🗺️ ロードマップ

- ✅ **v0.3.1**: P0クローズ、基盤防御稼働
- ✅ **v0.4.0**: P1完了（音声テスト拡張・voice CLI・Demo C・公開ベンチマーク）
- ✅ **v0.5.0**: P2運用定着（監査自動化・KPI継続監視・配布標準化）
- ✅ **v1.0.0**（完了）: 公開監査 / webhook / KPI CI自動化 / マルチデバイス対応
- ✅ **v1.1.0**（完了）: CI全カバレッジ / webhook強化 / voice integration tests / policy_v1正規化 / 306テスト
- 🚀 **v1.2.0**（次フェーズ）: 定常運用安定化 / policy lab 本格運用 / ドキュメント拡充

---


## 🧪 CIゲート運用（開発者向け判定基準）

PRでは**高速ゲートのみ必須**、重いbenchmarkは**定期ゲート**で実行します。

### PR必須ゲート（高速）
- `smoke`: lint / typing / smoke test
- `invariants`: 不変原則テスト（失敗時は違反原則サマリを出力）
- `prop-core`: property-based core test
- `kpi-quick`: KPI軽量計測（**結果を PR コメントに自動投稿**）

収集規約（workflow更新漏れ防止）:
- `prop-core` は `tests/test_prop_*.py` を規約ベースで自動収集
- `kpi-quick` は `tests/test_voice_*.py` と `tests/test_device_*.py` を規約ベースで収集
- `smoke` の Unit tests は `tests/` を広く収集しつつ、`test_prop_*`・`test_invariants.py`・smoke専用・kpi-quick専用を除外
- `tests/benchmarks/` は PR必須ゲートに含めない（定期benchmarkのみ）

マージ可否の基準:
- 4つすべてが `success` であること。
- `invariants` が失敗した場合は、CI summaryに表示される違反候補（例: `responsibility boundary missing/invalid`）を優先修正すること。
- `kpi-quick` の結果は PR コメントで確認できます（`<!-- echo-kpi-quick-check -->` マーカーで管理・更新）。

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
