# Demo C（Phase 4 Implementation）

Task: **ECHO-20260305-001 xAI Presentation Materials & Demo C Finalization**

## 目的

- Phase 3 benchmark実測を **Echo Mark v3署名付きreceipt** として提示する。
- 発表会場でCLI実行し、署名検証とKPI整合性を即時に確認可能にする。
- 不変原則（候補セット + 証拠 + 責任境界）をDemo出力でも維持する。

## 実装ファイル

- `docs/demo_c_example.py`
  - benchmark証跡を構造化データで保持
  - Echo Mark v3署名（PyNaCl利用時はEd25519+HMAC、未導入時はHMAC fallback）
  - `verify_echo_mark` で検証して結果を同時出力

## 実行コマンド

```bash
python docs/demo_c_example.py --pretty --hmac-secret "$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

## CLIオプション

- `--key-id`: receiptに埋め込む key ID（default: `demo-key-20260305`）
- `--hmac-secret`: demo用HMAC secret（`--ed25519-private-key` 未指定時は必須）
- `--ed25519-private-key`: demo用Ed25519 private key（hex、`--hmac-secret` とどちらか必須）
- `--pretty`: pretty JSONで出力

## 検証観点

1. `verification.status == "VERIFIED"`
2. `echo_mark_badge.verification_method == "Ed25519+HMAC"`（PyNaCl未導入環境では `HMAC` fallback）
3. `benchmark_evidence.voice_boundary.measured_min_seconds < 0.3`
4. `benchmark_evidence.rth.tracker_entries <= benchmark_evidence.rth.max_seen_count`

## 出力の意味

- `benchmark_evidence`: Phase 3実測証跡（プレゼン提示値）
- `echo_mark_badge`: tamper-evidentな署名済みreceipt
- `verification`: 署名・hash・timestamp・replayの検証結果

## 運用注意

- デフォルト鍵は廃止済み。`--ed25519-private-key` または `--hmac-secret` を必ず明示し、本番では `tools/generate_keypair.py` で生成した鍵を利用すること。
- benchmark evidenceを更新する際は、先に benchmark を再実行し、`docs/BENCHMARK_RESULTS.md` の履歴整合を維持すること。
- `BLOCKED` と `INVALID` は運用上の意味が異なるため、監査時に混同しないこと。


## Voice CLI 最小実行例（棚卸し + オーケストレーション層）

`po-cosmic voice` は `src/po_echo` 配下の実装を以下の順で薄く束ねます。

1. Voice Boundary (`po_echo.voice_boundary`) で責任境界を決定
2. Ear Handshake (`po_echo.ear_handshake`) でデバイス境界を証跡化
3. RTH (`po_echo.rth`, `po_echo.execution_gate`) で transcript 近傍ハッシュを付与
4. Echo Mark (`po_echo.echo_mark`) を dual signature で発行

固定JSON schema（ヘルプと同一）:

- Input: `{"intent": string, "transcript": string, "metadata": object}`
- Output: `{"candidate_set": array, "evidence": array, "responsibility_boundary": object, "voice_text": string, "echo_mark": object}`

```bash
# 1) スキーマ表示（固定仕様）
po-cosmic voice --show-schema --intent search --transcript "候補を出して" --in runs/high_bias_affiliate.audit.json --out /tmp/unused.json

# 2) 最小実行
export ECHO_MARK_SECRET="demo-secret-1234567890"
export ECHO_MARK_PRIVATE_KEY="1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100"
po-cosmic voice   --intent booking   --transcript "土曜夜、2名、予算1万円で予約候補"   --meta '{"amount": 10000}'   --simulate-ok   --in runs/high_bias_affiliate.audit.json   --out runs/demo_voice.json

# 3) 検証（候補セット＋証拠＋責任境界）
python -c 'import json;d=json.load(open("runs/demo_voice.json"));print(sorted(d.keys()));assert {"candidate_set","evidence","responsibility_boundary"}.issubset(d.keys())'
```
