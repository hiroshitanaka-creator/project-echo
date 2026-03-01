# xAI Presentation Material（Phase 4）

Task: **ECHO-20260305-001 xAI Presentation Materials & Demo C Finalization**  
Phase: **Phase 4 xAI Presentation**

## 1. プレゼン目的（Elon/xAI向け）

Project Echo の価値を、以下の順序で即座に検証可能な形で提示する。

1. **不変原則**（候補セット + 証拠 + 責任境界）
2. **非破壊性**（Phase 3実測・Voice Boundary / RTH / Echo Mark v3を保持）
3. **公開検証耐性**（固定seed + benchmark CI gate + dual signature）
4. **運用可能性**（key rotation / benchmark実行 / 監査フロー）

---

## 2. 推奨スライド構成（10枚）

### Slide 1 — Mission
- 画面なしAI時代の透明性防衛レイヤー
- Truth-Seeking / Sustainable Abundance / Freedom Preservation

### Slide 2 — 不変原則（絶対）
- AIはおすすめしない
- 商業バイアスを機械的制約で遮断
- 人間の選択肢を残す

### Slide 3 — 防御アーキテクチャ
- Voice Boundary
- RTH（Rolling Transcript Hash）
- Echo Mark v3（Ed25519 + HMAC dual signature）

### Slide 4 — Phase 3 Benchmark実測（保持）
- Voice Boundary 10k KPI: `min_seconds < 0.3`
- RTH 100k KPI: `tracker_entries <= max_seen_count`
- 固定seed再現性 + CI benchmark gate

### Slide 5 — 公開検証耐性
- ローカル/CI同一コマンドで再現
- KPI違反時はCI fail
- 非破壊ルール（既存実測履歴・防御ロジックを変更しない）

### Slide 6 — 脅威対策証跡
- replay防御（nonce + 5分窓）
- key_id registry + revoked拒否
- BLOCKED と INVALID の責任分離

### Slide 7 — Demo C（署名付きベンチ証跡）
- benchmark結果を Echo Mark receipt として生成
- `verify_echo_mark` でその場検証

### Slide 8 — 運用手順
- benchmark運用
- key rotation
- 監査ログ/証跡管理

### Slide 9 — ガバナンス境界
- システム責務: 候補・証拠・責任境界
- 人間責務: 実行可否/リスク受容

### Slide 10 — Ask
- xAI共同公開検証
- 赤チーム評価
- screenless展開PoC

---

## 3. ベンチマーク結果（Phase 3証跡の再掲）

| 指標 | 結果 | 判定 |
|---|---:|---|
| Voice Boundary 10k | `0.21s`（KPI `< 0.3`） | Pass |
| RTH 100k | `tracker_entries=1980 / max_seen_count=2000` | Pass |
| 再現性 | 固定seed `20260304` + CI gate | Pass |

> 本表は Phase 3確定値を Demo C表示用に再利用する。既存 `docs/BENCHMARK_RESULTS.md` の記述を破壊せず、Phase 4の提示素材として追加整理する。

---

## 4. 脅威対策証跡（プレゼンで強調するポイント）

- **Tamper-evident**: payload hash + dual signature により改ざん検知。
- **Replay defense**: nonce再利用拒否と timestamp 5分窓で再送攻撃を遮断。
- **Key lifecycle**: registry status (`active/inactive/revoked`) による運用拒否制御。
- **責任境界の可視化**: `BLOCKED`（境界拒否）と `INVALID`（署名/整合性破綻）を混同しない。

---

## 5. Demo C 実行コマンド（本番プレゼン用）

```bash
python docs/demo_c_example.py --pretty
```

期待される確認点:
- `echo_mark_badge.verification_method == "Ed25519+HMAC"`（PyNaCl未導入環境では `HMAC` で検証）
- `verification.status == "VERIFIED"`
- `benchmark_evidence.voice_boundary.measured_min_seconds < 0.3`
- `benchmark_evidence.rth.tracker_entries <= benchmark_evidence.rth.max_seen_count`

---

## 6. 発表時トークトラック（要約）

1. 「Echoはおすすめをしない。候補・証拠・責任境界だけを返す。」
2. 「Phase 3の性能/再現性を壊さず、Phase 4で公開説明可能な証跡に変換した。」
3. 「Demo Cは署名付きベンチ結果で、会場で即時検証できる。」
4. 「運用は key rotation / benchmark gate / 監査フローまで実装済み。」
