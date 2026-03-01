# Threat Model Update（Phase 4）

Task: **ECHO-20260305-001**  
Based on: **Phase 3 benchmark evidence + Echo Mark v3 operation contract**

## 1. 更新目的

Phase 3で確定した benchmark CI gate / 固定seed再現性 / Voice Boundary・RTH の公開検証耐性を、脅威対策証跡として明文化する。

## 2. 最新脅威シナリオと対策証跡

### TMU-01: Benchmark Cosmetic Pass（見せかけの性能合格）
- **攻撃**: ローカルだけ通る条件で benchmark を実行し、公開値を偽装する。
- **対策**:
  - `RUN_PUBLIC_BENCHMARKS=1` を必須化。
  - CI（`benchmark.yml`）で schedule + manual dispatch 双方を運用。
  - KPI違反を job fail 化。
- **証跡**:
  - `docs/BENCHMARK_RESULTS.md` の固定コマンド。
  - Demo C receipt 内の benchmark evidence。

### TMU-02: Reproducibility Drift（再現性ドリフト）
- **攻撃**: seed未固定のテストデータ生成で、都合のよい結果のみを提示する。
- **対策**:
  - Hypothesis固定seedを benchmark生成で必須化。
  - 型strategy明示登録で生成形状を固定。
- **証跡**:
  - seed `20260304` を Demo C evidence に埋め込み。

### TMU-03: Signature Downgrade（署名ダウングレード）
- **攻撃**: Ed25519が使える環境でもHMAC単独結果をVERIFIED扱いにする。
- **対策**:
  - Echo Mark v3 verify順序（hash→replay→Ed25519→HMAC）を固定。
  - デモでも `verification_method="Ed25519+HMAC"` を標準表示。
- **証跡**:
  - Demo Cの署名済みreceipt + verify結果。

### TMU-04: Replay-on-Stage（発表会場での再送攻撃）
- **攻撃**: 既知の署名済みreceiptを再送して偽の最新結果に見せる。
- **対策**:
  - nonce + timestamp(±300s) で replay拒否。
  - 検証理由コードを監査ログへ保存。
- **証跡**:
  - Echo Mark verify結果（`replay_safe`, `timestamp_valid`）。

### TMU-05: Responsibility Boundary Blur（責任境界の曖昧化）
- **攻撃**: `BLOCKED` と `INVALID` を混同し、署名失敗をポリシー拒否として隠す。
- **対策**:
  - 判定ラベル運用を明文化（VERIFIED/BLOCKED/INVALIDを厳密分離）。
  - 監査/プレゼンでは必ず label + reason を併記。
- **証跡**:
  - Demo C出力に verification detail を含める。

## 3. Phase 4 証跡要件（必須）

- 署名付き benchmark receipt を生成・検証できること。
- 既存 benchmark結果文書を破壊せず再利用すること。
- 運用者が benchmark / key rotation / audit flow を手順書で再実行できること。

## 4. 受け入れ判定

- 不変原則に1件でも違反があれば reject。
- benchmark KPI違反は公開資料採用不可。
- 署名検証失敗または replay不正は即 `INVALID`。
