# Changelog

All notable changes to Project Echo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- ECHO-20260304-002: `.github/workflows/benchmark.yml` を新規追加し、`RUN_PUBLIC_BENCHMARKS=1` の定期 benchmark gate（schedule + manual dispatch）を導入。
- ECHO-20260304-002: `docs/DEMO_C.md` を新規追加し、ベンチマーク結果を Echo Mark 形式で表示する軽量CLIスケルトンを定義。
- ECHO-20260305-001: `docs/XAI_PRESENTATION.md` を追加し、xAI向けプレゼン構成（不変原則・benchmark結果・脅威対策証跡・運用手順）を即使用可能な形で固定化。
- ECHO-20260305-001: `docs/OPERATING_PROCEDURE.md` を追加し、benchmark運用・key rotation・監査フローをPhase 4手順として明文化。
- ECHO-20260305-001: `docs/demo_c_example.py` を追加し、Phase 3 benchmark証跡を Echo Mark v3 dual signature 付き receipt として出力・検証する Demo C CLI を実装。

### Changed
- ECHO-20260304-002: `docs/GROK-COLLABORATION-BIBLE.md` を v1.4 Full へ更新し、Phase 3 Benchmark & Quality 運用規格（再現性 / KPI / CI統合 / 非破壊）を追加。
- ECHO-20260304-002: `tests/benchmarks/benchmark_voice_boundary.py` のケース生成を Hypothesis 固定seed + `register_type_strategy` で再現可能化し、10k KPI（`< 0.3s`）を厳格化。
- ECHO-20260304-002: `tests/benchmarks/benchmark_rth.py` / `benchmark_voice_boundary.py` の import を poetry / editable install 両対応の安全な import パターンへ更新。
- ECHO-20260304-002: `docs/BENCHMARK_RESULTS.md` のKPI定義を厳格化し、Phase 3最終運用コマンドを明確化。
- ECHO-20260305-001: `docs/DEMO_C.md` をスケルトンから本実装手順へ更新し、署名付きbenchmark receipt CLIの運用観点を追加。
- ECHO-20260305-001: `docs/THREAT_MODEL_UPDATE.md` を追加し、Phase 3 benchmark証跡を脅威対策シナリオへ接続して公開検証耐性を明文化。

### Added
- ECHO-20260302-002: `docs/GROK-COLLABORATION-BIBLE.md` を v1.2 Full へ更新。
- ECHO-20260302-001: `tests/test_echo_mark.py` を追加し、Hypothesisベースで dual signature 検証成功・replay拒否・rotation後旧署名無効を検証。
- `docs/GROK-COLLABORATION-BIBLE.md` を追加し、Grok連携時のマスター参照シート（v1.0）をリポジトリ内で固定化。
- ECHO-20260301-005: `docs/GROK-COLLABORATION-BIBLE.md` を v1.1 に更新。
- ECHO-20260301-004: `po_echo.diversity.apply_semantic_diversity` に 6D cosine semantic evidence（`semantic_delta`, `6d_values`, `freedom_pressure_snapshot`）を追加。
- `src/po_echo/diversity.py` を追加し、`po_core` API互換のセマンティック多様性ラッパーと安全フォールバックを実装。
- 回帰検知用テストとして `tests/test_diversity.py` と `tests/test_sentinel_v2.py` を追加。

### Changed
- ECHO-20260302-002: `src/po_echo/echo_mark.py` を可読性重視で整理（helper分離・ネスト簡略化）し、registry status（active/inactive/revoked）連携を強化。
- ECHO-20260302-002: `tools/generate_keypair.py` の rotate を堅牢化（atomic registry write / previous-active status制御）。
- ECHO-20260302-001: `src/po_echo/echo_mark.py` を Echo Mark v3 実装へ刷新し、canonical payload、Ed25519+HMAC dual署名、key_id検証、nonce+timestamp（5分窓）のreplay防御を実装。
- ECHO-20260302-001: `tools/generate_keypair.py` を v3運用向けに更新し、`generate`/`rotate` サブコマンドで Ed25519 鍵生成とローテーションをサポート。
- `src/po_echo/sentinel_v2.py` に既存 Doberman / `scan_directory` を保持したまま `apply_semantic_diversity` を末尾追加し、ECHO-20260301-002 の回帰を補正。
- ECHO-20260301-005: `create_freedom_pressure_v2` 初期化経路を整理し、`compute_v2(text)` ベースの6D計算を安定化。
- ECHO-20260301-005: `tests/test_diversity.py` の大量候補ケースを 10,000 件に拡張。
- `src/po_echo/execution_gate.py` に `enrich_audit_with_semantic_evidence` を追加し、既存 `gate_audio` フローを維持したまま監査証跡を拡張。

### Fixed
- ECHO-20260301-002 で発生した semantic 統合の不安定化（`po_core` import 揺れ、Rec変換の脆弱性、テスト欠落）を ECHO-20260301-003 で是正。

### Planned
- P1（1〜2ヶ月）開始: 音声系 property-based test 拡張、`po-cosmic voice`、Demo C

## [v0.3.1] - 2026-02-24

### Added
- `PROGRESS.md` を新規追加し、P0（0〜2週間）完了状況・残タスク・KPIを統合管理。
- P1着手向けIssueドラフト方針を整理（進捗起点のマイルストーン運用）。

### Changed
- `README.md` を更新し、P0完了セクションを追加。
- 現在状態を「候補セット＋証拠＋責任境界」哲学に合わせて明文化。

### Philosophy
- 「AIはおすすめしない」「選択肢を残す」を運用文書・進捗管理に反映し、
  実装だけでなくプロジェクトガバナンスにも不変原則を適用。

## [v0.3.0] - 2026-02-24

### Added
- `src/po_echo/gumdrop_defense.py`（screenless ambient device向けEcho Mark強化）
- `AGENT.md`（AIエージェント開発ガイド）
- `docs/openai_world_register_threat.md`（World Register脅威モデル）
- README全面刷新（脅威モデル前面配置・一般化）

### Changed
- 商品名を「screenless ambient device」に一般化（リスク低減）

### Philosophy
- AIの「失敗しなかった意図」課金モデルに対して、透明性と責任境界を強制する防御を追加。
- 選択肢を残すことをシステムで守る。

## [v0.2.0] - 2026-01-24

### Added
- Audio Channel for Ear-worn Devices（Voice Boundary / Ear-Handshake / RTH）
- Ed25519 Signatures（Dual Signature）
- Keypair generation tool（`tools/generate_keypair.py`）
- Public key registry support
- Timestamp validation for replay mitigation
- Extended property-based tests（Ed25519 + timestamp）
- CLI enhancements（`badge`, `verify`）

### Changed
- Echo Mark schema version: v2 → v3
- Dependencies: Added PyNaCl >=1.5.0

### Security
- Replay attack mitigation, key rotation support, public verification model

### Testing
- 51 tests passing（当時時点）

## [v0.1.1] - 2026-01-12

### Added
- Demo B: Shopping Bias Defense（3シナリオ）
- Public Verification Design（`docs/VERIFICATION_DESIGN.md`）
- Ed25519 Migration Design（`docs/ED25519_MIGRATION.md`）
- Threat Model（`docs/threat_model.md`）
- Demo guide（`docs/DEMO_SHOPPING.md`）
- `po-cosmic` CLI と関連ツール群
- 正規化・監査・ゲート・署名の基盤実装
- Property-based tests（24件）とCI基盤

### Fixed
- Conservative gate violation bug
- High-utility high-bias dominance in MMR selection

## [v0.1.0] - 2026-01-10

### Added
- 初期リリース
- 商業バイアス監査、候補多様性制御、実行ゲート、Echo Mark基本機能

---

[v0.3.1]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.3.1
[v0.3.0]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.3.0
[v0.2.0]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.2.0
[v0.1.1]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.1.1
[v0.1.0]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.1.0

## [Unreleased]

### Changed
- ECHO-20260303-002: `rth` collision追跡を blake2b fingerprint + bounded/TTL prune に更新し、長時間稼働時のメモリ効率と耐障害性を強化。
- ECHO-20260303-002: `voice_boundary` の screenless fallback 条件を `ScreenlessSafetyConfig` に集約し、ハードコード依存を排除。
- ECHO-20260303-002: Bible v1.3 Full に Phase 2 Ambient Defense 運用規格（Voice Boundary / RTH）を追記。

### Testing
- ECHO-20260303-002: `tests/test_rth.py` と `tests/test_voice_boundary.py` を Hypothesis ベースの複合 edge case テストで拡張。

- ECHO-20260304-001: `tests/benchmarks/benchmark_voice_boundary.py` と `tests/benchmarks/benchmark_rth.py` を追加し、Phase 3公開ベンチマーク（性能・メモリ）を再現可能コマンド付きで整備。
- ECHO-20260304-001: `docs/BENCHMARK_RESULTS.md` を追加し、実行手順・結果テーブル・Phase 3 KPIを明文化。

### Changed
- ECHO-20260304-001: `src/po_echo/voice_boundary.py` と `src/po_echo/rth.py` に軽量 `__repr__` / `__str__` を追加し、非機能デバッグ性を向上。

### Documentation
- ECHO-20260304-001: `PROGRESS.md` に Phase 3開始宣言と公開検証耐性（再現性）方針を追記。
