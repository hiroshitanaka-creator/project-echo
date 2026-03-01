# Project Echo Progress Dashboard

最終更新: 2026-02-24
ステータス: **P0（0〜2週間）完了**

## 🎉 P0完了おめでとう！
Project EchoのP0スコープは、**不変原則を維持したまま完了**しました。
この進捗は「機能追加数」ではなく、**候補セット提示・証拠提示・責任境界明示**の実装証跡で判定されています。

> [!IMPORTANT]
> **次の意思決定ポイント（P1）**
> - 参照: [P1開始向け実行バックログ](#p1開始向け実行バックログ)
> - 次マイルストーン: **v0.4.0**（音声テスト拡張 / voice CLI / Demo C）

## ECHO-20260301-003 回帰修正サマリー（追加）

- 背景（ECHO-20260301-002 の弱点）:
  - semantic 統合ポイントが `po_echo` 側で欠落し、`po_core` 連携の責務境界が不明瞭。
  - sentinel_v2 に semantic 多様性ブリッジがなく、監査と多様化が分断。
  - execution_gate で semantic 証拠の付与APIが不足し、後段検証が不安定。
  - 回帰検知テスト（numpy optional環境・大量候補）が不足。
- 是正（ECHO-20260301-003）:
  - `src/po_echo/diversity.py` を新設し、`from po_core.diversity import Rec, ...` に統一。
  - `po_core.tensors.engine.create_freedom_pressure_v2` を優先しつつ、非存在時の安全フォールバックを実装。
  - `Rec.from_dict` が存在しないケースでも dict から復元可能なフォールバックを追加。
  - `sentinel_v2` / `execution_gate` に最小追加で回帰を抑止し、既存フローを非破壊で維持。

- 追補（ECHO-20260301-004）:
  - `compute_v2(prompt_text)` / `compute_v2(candidate_text)` ベースの6D cosineを導入し、semantic差分を `semantic_delta` として監査に記録。
  - `execution_gate` と `sentinel_v2` の拡張関数で semantic証拠キーを透過的に注入し、既存ゲート挙動は維持。

- 追補（ECHO-20260301-005）:
  - Bibleをv1.1へ更新し、Phase 1最終調整ルールを明文化。
  - semanticエンジン初期化を `compute_v2(text)` 前提で再調整。
  - 大規模候補テストを10,000件へ拡張し、耐障害性を強化。

## ECHO-20260302-001 Echo Mark v3 完了（Phase 2前進）

- `src/po_echo/echo_mark.py` を v3へ刷新し、**Ed25519を主署名**、HMACを後方互換fallbackとして維持。
- canonical payload（`schema_version=echo_mark_v3`）に nonce/timestamp を導入し、5分窓で replay 防御を強制。
- `tools/generate_keypair.py` に `rotate` コマンドを追加し、active key のローテーション運用を自動化。
- `tests/test_echo_mark.py` で property-based 3系統（dual成功/replay拒否/rotation無効化）を追加。
- semantic_evidence 連携は payload 透過保持で非破壊継続。

## ECHO-20260302-002 Echo Mark v3 最終調整 完了（Phase 2品質強化）

- 良い部分（dual署名/replay防御/semantic連携/既存property test）は保持したまま、`echo_mark.py` の helper 分離で可読性を改善。
- verification の分岐を整理し、`active/inactive/revoked` を含む registry status を明示的に扱うよう強化。
- `tools/generate_keypair.py` を強化し、rotate 時の registry 更新を atomic 化、旧activeキーの遷移先（inactive/revoked）を選択可能化。
- Bible を v1.2 Full に更新し、Phase運用・レビュー基準・署名運用規格を拡張。

## 不変原則（運用中）
<!-- # Project Echo 不変原則：選択肢を残す -->
- AIは「おすすめ」を返さず、**候補セット＋証拠＋責任境界**を返す。
- 商業バイアス対策は道徳訴求ではなく、**機械的強制**で実装する。
- 最上位哲学は「**選択肢を残す**」。

## P0進捗サマリー（視覚化）

<!-- # Project Echo 不変原則：選択肢を残す -->
| フェーズ | 進捗率 | 進捗バー | 判定 |
|---|---:|---|---|
| P0（0〜2週間） | 100% | `██████████` 10/10 | ✅ 完了 |
| P1（次段階） | 0% | `░░░░░░░░░░` 0/10 | ⏳ 未着手 |
| リスク逸脱タスク | 0件 | `██████████` 逸脱なし | ✅ 監視中 |

## P0完了項目（証拠リンク付き）

<!-- # Project Echo 不変原則：選択肢を残す -->
| 項目 | ステータス | 根拠（実装/資料） | 責任境界 |
|---|---|---|---|
| 商業バイアス監査 | ✅ 完了 | `src/po_echo/sentinel.py`, `src/po_echo/sentinel_v2.py`, `tools/threshold_audit.py` | 監査ロジックは候補評価まで。最終採否判断は運用者責任。 |
| 候補多様性注入（MMR + bias penalty） | ✅ 完了 | `src/po_core/diversity.py` | 候補集合の偏り抑制まで。選定ポリシー確定は運用者責任。 |
| 実行ゲート（Conservative Gate） | ✅ 完了 | `src/po_echo/execution_gate.py` | 実行可否の安全側判定まで。実行承認は人間/上位システム責任。 |
| Echo Mark署名（Ed25519 + HMAC Dual） | ✅ 完了 | `src/po_echo/echo_mark.py`, `tools/generate_keypair.py` | 署名生成・検証まで。鍵管理・ローテーションは運用責任。 |
| 音声系防御（Voice Boundary / Ear Handshake / RTH） | ✅ 完了 | `src/po_echo/voice_boundary.py`, `src/po_echo/ear_handshake.py`, `src/po_echo/rth.py` | 音声境界の技術的制約まで。業務適用判断は運用責任。 |
| Gumdrop / World Register対策 | ✅ 完了 | `src/po_echo/gumdrop_defense.py`, `docs/openai_world_register_threat.md` | リスク検知・抑制まで。契約/事業判断は組織責任。 |
| CLI/デモ運用導線 | ✅ 完了 | `src/po_cosmic/cli.py`, `tools/demo_shopping.py`, `docs/DEMO_SHOPPING.md` | 再現導線提供まで。本番利用可否判定は運用責任。 |
| 性質ベーステスト群 | ✅ 完了 | `tests/test_prop_*.py`, `tests/test_invariants.py` | 不変条件の検証まで。合否基準策定は品質管理責任。 |

## P1開始向け実行バックログ

<!-- # Project Echo 不変原則：選択肢を残す -->
| 優先度 | タスク | 目的 | 完了条件 | ステータス |
|---|---|---|---|---|
| P1-High | Audio Channel の property-based test 拡張 | 音声入力系の回帰防止 | `voice_boundary`, `ear_handshake`, `rth` の性質テスト追加 | ⏳ |
| P1-High | `po-cosmic voice` サブコマンド追加 | 実運用CLI統合 | 音声系フローをCLIから実行可能 | ⏳ |
| P1-Mid | Demo C（音声起点 booking） | 実戦想定の可視化 | シナリオ・手順書・再現ログ整備 | ⏳ |
| P1-Mid | 運用ドキュメント強化 | チーム導入性向上 | 鍵ローテーション/監査運用手順を文書化 | ⏳ |
| P1-Low | パフォーマンス計測（候補1万件） | スケール耐性確認 | 計測レポートと閾値提案を作成 | ⏳ |

## KPI定義（P0完了時点 / P1監視開始）

<!-- # Project Echo 不変原則：選択肢を残す -->
| KPI | 定義（計測対象） | 現在値 | 次マイルストーン目標 |
|---|---|---:|---:|
| 不変原則準拠率 | 生成出力が「候補セット＋証拠＋責任境界」を**同時に満たす割合** | 100%（設計目標） | 維持 |
| Evidence Coverage | 最終出力内の主張に対し、実装/ログ/文書の**検証可能な根拠が紐づく割合** | 100%（P0対象範囲） | 維持 |
| テスト成功率 | CI/ローカルで実行したテストのパス率 | 100%（最新実行で確認） | 維持 |
| 高バイアス候補混入率 | 閾値超え候補が最終候補集合に残る割合 | 低位（監査対象） | さらに低減 |
| 署名検証成功率 | Echo Mark検証成功の割合（正常系） | 100% | 維持 |
| 責任境界明示率 | 出力に責任境界が含まれる割合 | 100%（設計目標） | 維持 |

## マイルストーン
<!-- # Project Echo 不変原則：選択肢を残す -->
- ✅ **v0.3.1（完了）**: P0クローズ、進捗と運用文書の統合更新
- ⏳ **v0.4.0（予定）**: P1の主要機能（音声テスト拡張・voice CLI・Demo C）
- ⏳ **v1.0.0（将来）**: 公開監査運用を含む本番定着

## P1遷移時の意思決定境界
<!-- # Project Echo 不変原則：選択肢を残す -->
- 候補比較・証拠提示・責任境界明示はシステム責務。
- 本番反映可否、リスク受容、契約判断は人間/組織責務。
- 運用中に原則逸脱を検知した場合は、P1進行より是正を優先する。

## ECHO-20260302-003 候補B適用（長期運用堅牢化）

- `src/po_echo/rth.py` の collision追跡辞書に `max_seen_count=1000` 上限を導入し、上限超過時は `first_seen_ms` 最古エントリを prune して warning ログ（`rth_chain_hash_collision_dict_pruned`）を記録。
- `src/po_echo/voice_boundary.py` の `_safe_float` を `FieldName` Literal enum で型制約し、`amount` / `bias_score` / `battery_level` を監査対象フィールドとして固定。
- `tests/test_rth.py` に上限pruneテストを追加、`tests/test_voice_boundary.py` に FieldName enum完全性テストを追加し、既存4テストを維持したまま合計6テストへ拡張。
