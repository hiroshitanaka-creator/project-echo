# Project Echo Progress Dashboard

最終更新: 2026-02-24  
ステータス: **P0（0〜2週間）完了**

## 不変原則（運用中）
- AIは「おすすめ」を返さず、**候補セット＋証拠＋責任境界**を返す。
- 商業バイアス対策は道徳訴求ではなく、**機械的強制**で実装する。
- 最上位哲学は「**選択肢を残す**」。

## P0 完了サマリー

| 項目 | ステータス | 根拠（実装/資料） | 備考 |
|---|---|---|---|
| 商業バイアス監査 | ✅ 完了 | `src/po_echo/sentinel.py`, `src/po_echo/sentinel_v2.py`, `tools/threshold_audit.py` | 候補の監査・閾値判定を実装 |
| 候補多様性注入（MMR + bias penalty） | ✅ 完了 | `src/po_core/diversity.py` | 高バイアス優勢を抑制 |
| 実行ゲート（Conservative Gate） | ✅ 完了 | `src/po_echo/execution_gate.py` | 実行可否を安全側で制御 |
| Echo Mark署名（Ed25519 + HMAC Dual） | ✅ 完了 | `src/po_echo/echo_mark.py`, `tools/generate_keypair.py` | 公開検証性と後方互換を両立 |
| 音声系防御（Voice Boundary / Ear Handshake / RTH） | ✅ 完了 | `src/po_echo/voice_boundary.py`, `src/po_echo/ear_handshake.py`, `src/po_echo/rth.py` | 画面無し環境の責任境界を保持 |
| Gumdrop / World Register対策 | ✅ 完了 | `src/po_echo/gumdrop_defense.py`, `docs/openai_world_register_threat.md` | 課金モデルの不透明化リスクを防御 |
| CLI/デモ運用導線 | ✅ 完了 | `src/po_cosmic/cli.py`, `tools/demo_shopping.py`, `docs/DEMO_SHOPPING.md` | 検証可能な再現導線あり |
| 性質ベーステスト群 | ✅ 完了 | `tests/test_prop_*.py`, `tests/test_invariants.py` | 重要不変条件を継続監視 |

## 残タスク（P1開始向け）

| 優先度 | タスク | 目的 | 完了条件 |
|---|---|---|---|
| P1-High | Audio Channel の property-based test 拡張 | 音声入力系の回帰防止 | `voice_boundary`, `ear_handshake`, `rth` の性質テスト追加 |
| P1-High | `po-cosmic voice` サブコマンド追加 | 実運用CLI統合 | 音声系フローをCLIから実行可能 |
| P1-Mid | Demo C（音声起点 booking） | 実戦想定の可視化 | シナリオ・手順書・再現ログ整備 |
| P1-Mid | 運用ドキュメント強化 | チーム導入性向上 | 鍵ローテーション/監査運用手順を文書化 |
| P1-Low | パフォーマンス計測（候補1万件） | スケール耐性確認 | 計測レポートと閾値提案を作成 |

## KPI（P0完了時点 / P1監視開始）

| KPI | 定義 | 現在値 | 次マイルストーン目標 |
|---|---|---:|---:|
| 不変原則準拠率 | 出力が「候補セット＋証拠＋責任境界」を満たす割合 | 100%（設計目標） | 維持 |
| テスト成功率 | CI/ローカルでのテストパス率 | 100%（最新実行で確認） | 維持 |
| 高バイアス候補混入率 | 閾値超え候補が最終候補に残る割合 | 低位（監査対象） | さらに低減 |
| 署名検証成功率 | Echo Mark検証成功の割合 | 100%（正常系） | 維持 |
| 責任境界明示率 | 出力に責任境界を含む割合 | 100%（設計目標） | 維持 |

## マイルストーン
- **v0.3.1（完了）**: P0クローズ、進捗と運用文書の統合更新
- **v0.4.0（予定）**: P1の主要機能（音声テスト拡張・voice CLI・Demo C）
- **v1.0.0（将来）**: 公開監査運用を含む本番定着
