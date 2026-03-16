# Device Boundary Design & Extension Guide

> **対象バージョン**: v1.1.0 Sprint-1
> **関連ファイル**: `src/po_echo/device_boundary.py`, `src/po_echo/voice_boundary.py`, `src/po_cosmic/cli.py`

---

## 概要

`device_boundary.py` は、Project Echo の責任境界契約（候補セット + 証拠 + 責任境界）を
**画面のないマルチデバイス環境**へ機械的に適用するアダプタ層です。

デバイスごとに確認手段（ボタン / 振動 / 視線）は異なりますが、
以下の**不変原則**はすべてのデバイスで例外なく強制されます。

---

## 不変原則（絶対 — 拡張時も変更不可）

| # | 原則 | 強制箇所 |
|---|------|---------|
| 1 | 高リスク intent → `requires_human_confirm = True` | `decide_for_device()` |
| 2 | `bias_score >= threshold` → `execution_allowed = False` | `decide_for_device()` |
| 3 | replay / tamper 検知 → `execution_allowed = False` | `decide_for_device()` |
| 4 | `responsibility_boundary` dict に必須キーが常に存在する | `to_responsibility_boundary()` |
| 5 | リスク分類はデバイス非依存（`classify_risk()` を共有） | `voice_boundary.classify_risk` |

必須キー: `channel`, `device`, `risk`, `required_action`,
`execution_allowed`, `requires_human_confirm`, `reasons`

---

## アーキテクチャ

```
voice_boundary.py          ← リスク分類 / 基本ポリシー / _safe_float
        │
        └── device_boundary.py   ← デバイス別アダプタ層
                │
                ├── DeviceBoundaryConfig   (ポリシーテーブル + バイアス閾値)
                ├── DeviceBoundaryDecision (不変原則を満たす決定結果)
                ├── decide_for_device()    (中央ディスパッチ — 全デバイス共通)
                └── DEVICE_CONFIGS         (登録済みデバイス辞書)
```

`decide_for_device()` は **全デバイス共通の関門** です。
デバイス固有のポリシーは「中リスク時の確認手段」にのみ影響し、
ブロック条件（バイアス / replay / tamper）はデバイス設定で変えられません。

---

## 登録済みデバイス

| `DeviceType` | 確認手段（中リスク） | バイアス閾値 | 説明 |
|---|---|---|---|
| `earworn` | `double_tap` | 0.60 | イヤーウォーン（Sweetpea）参照実装 |
| `smart_speaker` | `voice_passphrase` | **0.50** | 共有空間のためバイアス閾値を厳格化 |
| `smart_watch` | `haptic_tap` | 0.60 | 手首ウェアラブル（触覚+小画面） |
| `ar_glasses` | `gaze_confirm` | 0.60 | HUD + 音声ハイブリッド確認 |

---

## 新デバイスの追加手順

### Step 1 — 確認手段の定義

`DeviceConfirm` Literal に新しい確認アクション名を追加します（既存値との重複不可）。

```python
# device_boundary.py
DeviceConfirm = Literal[
    "none",
    "double_tap",
    "passphrase",
    "app_confirm",
    "voice_passphrase",
    "haptic_tap",
    "gaze_confirm",
    "your_new_action",   # ← 追加
]
```

### Step 2 — `DeviceType` への登録

```python
DeviceType = Literal[
    "earworn", "smart_speaker", "smart_watch", "ar_glasses",
    "your_new_device",   # ← 追加
]
```

### Step 3 — ポリシーテーブルの作成

```python
_YOUR_DEVICE_POLICY: dict[str, dict[str, Any]] = {
    "low":    {"required_action": "none",            "requires_human_confirm": False},
    "medium": {"required_action": "your_new_action", "requires_human_confirm": True},
    "high":   {"required_action": "app_confirm",     "requires_human_confirm": True},
    # ↑ high は必ず app_confirm / requires_human_confirm=True (不変原則 #1)
}
```

### Step 4 — `DEVICE_CONFIGS` への追加

```python
DEVICE_CONFIGS: dict[DeviceType, DeviceBoundaryConfig] = {
    # ... 既存デバイス ...
    "your_new_device": DeviceBoundaryConfig(
        device="your_new_device",
        policy=_YOUR_DEVICE_POLICY,
        high_bias_block_threshold=0.60,  # 共有空間なら 0.50 を推奨
        description="One-line description of device characteristics.",
    ),
}
```

### Step 5 — テストの追加

`tests/test_prop_device_boundary.py` に以下のプロパティテストを追加してください。

```python
@given(
    intent=st.sampled_from(["payment", "booking", "search"]),
    bias=st.floats(min_value=0.7, max_value=1.0),
)
def test_your_device_high_bias_blocks(intent, bias):
    d = decide_for_device("your_new_device", intent, bias_score=bias)
    assert not d.execution_allowed

@given(intent=st.sampled_from(CRITICAL_INTENTS))
def test_your_device_high_risk_requires_confirm(intent):
    d = decide_for_device("your_new_device", intent)
    assert d.requires_human_confirm

def test_your_device_responsibility_boundary_keys():
    d = decide_for_device("your_new_device", "search")
    rb = d.to_responsibility_boundary()
    for key in ("channel", "device", "risk", "required_action",
                "execution_allowed", "requires_human_confirm", "reasons"):
        assert key in rb
```

最低限カバーすべき3系統:
1. 高バイアス → `execution_allowed = False`
2. 高リスク intent → `requires_human_confirm = True`
3. `to_responsibility_boundary()` の必須キー完全性

### Step 6 — CLI から利用可能にする

`src/po_cosmic/cli.py` の `--device` 選択肢は `DEVICE_CONFIGS` を動的に参照するため、
`DEVICE_CONFIGS` に追加するだけで `po-cosmic device --list-devices` に自動反映されます。
追加作業は不要です。

---

## バイアス閾値の設計ガイドライン

| デバイス環境 | 推奨閾値 | 理由 |
|---|---|---|
| プライベート空間（個人使用） | 0.60 | earworn / smart_watch 標準 |
| 共有・公共空間 | **0.50** | 傍聴リスク → より厳格なバイアスブロック |
| 高セキュリティ環境 | 0.30 以下 | 要件次第で個別設定 |

`high_bias_block_threshold` を下げることは安全側への変更（fail-closed）です。
上げることは意図的な緩和であり、設計レビューを要します。

---

## 責任境界の自動化スコープ

| スコープ | 内容 |
|---|---|
| **automation_scope** | リスク分類・バイアスブロック・replay / tamper 検知 |
| **human_scope** | 高リスク・中リスク時の最終承認（`requires_human_confirm = True` の場合） |

`execution_allowed = True` であっても、`requires_human_confirm = True` の場合は
人間の明示的な確認が完了するまで実行してはなりません。

---

## CLI での確認方法

```bash
# 登録済みデバイスの一覧と設定を確認
po-cosmic device --list-devices

# 新デバイスの動作確認
po-cosmic device --device your_new_device --intent payment --bias-score 0.8

# CI ゲート組み込み（blocked 時に exit code 3）
po-cosmic device --device your_new_device --intent search --require-execution-allowed
```

---

## 関連ドキュメント

- `docs/OPERATING_PROCEDURE.md` — 運用手順全般
- `src/po_echo/voice_boundary.py` — リスク分類・基本ポリシーの実装
- `src/po_echo/device_boundary.py` — マルチデバイスアダプタ実装
- `tests/test_prop_device_boundary.py` — 不変原則の property-based テスト
- `tests/test_device_cli.py` — CLI 契約テスト
