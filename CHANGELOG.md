# Changelog

All notable changes to Project Echo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
