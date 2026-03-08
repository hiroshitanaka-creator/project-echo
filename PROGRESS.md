# Project Echo Progress Dashboard

最終更新: 2026-03-08
ステータス: **P2（運用定着フェーズ）Sprint-2進行中**

## 🎉 P0完了おめでとう！
Project EchoのP0スコープは、**不変原則を維持したまま完了**しました。
この進捗は「機能追加数」ではなく、**候補セット提示・証拠提示・責任境界明示**の実装証跡で判定されています。

> [!IMPORTANT]
> **次の意思決定ポイント（P2）**
> - 参照: [ECHO-20260308-007 P2 Sprint-2実行バックログ](#echo-20260308-007-p2-sprint-2実行バックログ)
> - 次マイルストーン: **v0.5.0**（監査自動化 / 継続KPI監視 / 配布運用標準化）

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

## フェーズ進捗サマリー（視覚化）

<!-- # Project Echo 不変原則：選択肢を残す -->
| フェーズ | 進捗率 | 進捗バー | 判定 |
|---|---:|---|---|
| P0（0〜2週間） | 100% | `██████████` 10/10 | ✅ 完了 |
| P1（次段階） | 100% | `██████████` 10/10 | ✅ 完了 |
| P2（運用定着） | 50% | `█████░░░░░` 5/10 | 🚧 Sprint-2進行中 |
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
| P1-High | Audio Channel の property-based test 拡張 | 音声入力系の回帰防止 | `voice_boundary`, `ear_handshake`, `rth` の性質テスト追加 | ✅ |
| P1-High | `po-cosmic voice` サブコマンド追加 | 実運用CLI統合 | 音声系フローをCLIから実行可能 | ✅ |
| P1-Mid | Demo C（音声起点 booking） | 実戦想定の可視化 | シナリオ・手順書・再現ログ整備 | ✅ |
| P1-Mid | 運用ドキュメント強化 | チーム導入性向上 | 鍵ローテーション/監査運用手順を文書化 | ✅ |
| P1-Low | パフォーマンス計測（候補1万件） | スケール耐性確認 | 計測レポートと閾値提案を作成 | ✅ |

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
- ✅ **v0.4.0（完了）**: P1の主要機能（音声テスト拡張・voice CLI・Demo C）
- 🚀 **v0.5.0（進行中）**: P2運用定着（監査自動化・継続KPI監視・配布運用の標準化）
- ⏳ **v1.0.0（将来）**: 公開監査運用を含む本番定着

## ECHO-20260308-004 P1クローズ & P2キックオフ（次フェーズ移行）

- P1バックログの未完了項目をクローズし、`docs/OPERATING_PROCEDURE.md` の鍵ローテーション/監査フロー手順と `docs/BENCHMARK_RESULTS.md` の10k benchmark証跡を完了根拠として紐付け。
- P1進捗率を 100% に更新し、次フェーズとして P2（運用定着）を開始。
- P2初期スコープは「監査自動化」「継続KPI監視」「xAI Gift package運用標準化」の3本柱とし、既存の不変原則（候補セット＋証拠＋責任境界）を継続適用。


## ECHO-20260308-005 P2 Sprint-1実行バックログ

| 優先度 | タスク | 目的 | 完了条件 | ステータス |
|---|---|---|---|---|
| P2-High | 監査ログ集約テンプレート統一 | 監査証跡の比較可能性を高める | `docs/OPERATING_PROCEDURE.md` の運用手順で同一フォーマットを固定 | ✅ |
| P2-Mid | KPI週次レビュー運用 | 劣化の早期検知 | benchmark / test / signature KPI の週次記録を定着 | ✅ |
| P2-Mid | Gift Package再生成リハーサル | 配布運用の再現性担保 | `scripts/make_xai_gift.py` の手順で再生成ログを保管 | ✅ |


## ECHO-20260308-006 P2 Sprint-1クローズ（次フェーズ移行）

- Sprint-1で定義した3タスク（監査ログテンプレート統一 / KPI週次レビュー導線 / Gift Package再生成導線）を完了としてクローズ。
- 完了根拠は `docs/OPERATING_PROCEDURE.md`（日次/週次運用・監査フロー）, `docs/BENCHMARK_RESULTS.md`（KPI判定基準）, `docs/README.md` + `scripts/make_xai_gift.py`（再生成導線）に紐付け。
- P2は Sprint-2へ移行し、次段は自動化と監査証跡の定常運用を中心に進行する。

## ECHO-20260308-007 P2 Sprint-2実行バックログ

| 優先度 | タスク | 目的 | 完了条件 | ステータス |
|---|---|---|---|---|
| P2-High | 監査証跡の定例アーカイブ運用 | 監査耐性の継続担保 | 週次で benchmark結果・署名検証結果・運用ログを同一命名規約で保存 | 🚧 |
| P2-Mid | KPI差分レポート雛形の固定化 | 劣化時の原因特定を高速化 | 前週比（性能/メモリ/署名成功率）を1ページで確認可能な雛形を運用定着 | 🚧 |
| P2-Mid | Gift Package生成の定期リハーサル | 外部共有時の再現性担保 | 月次で `python scripts/make_xai_gift.py` 実行ログを保管 | 🚧 |

## P2遷移時の意思決定境界
<!-- # Project Echo 不変原則：選択肢を残す -->
- 候補比較・証拠提示・責任境界明示はシステム責務。
- 本番反映可否、リスク受容、契約判断は人間/組織責務。
- 運用中に原則逸脱を検知した場合は、P2進行より是正を優先する。

## ECHO-20260302-003 候補B適用（長期運用堅牢化）

- `src/po_echo/rth.py` の collision追跡辞書に `max_seen_count=1000` 上限を導入し、上限超過時は `first_seen_ms` 最古エントリを prune して warning ログ（`rth_chain_hash_collision_dict_pruned`）を記録。
- `src/po_echo/voice_boundary.py` の `_safe_float` を `FieldName` Literal enum で型制約し、`amount` / `bias_score` / `battery_level` を監査対象フィールドとして固定。
- `tests/test_rth.py` に上限pruneテストを追加、`tests/test_voice_boundary.py` に FieldName enum完全性テストを追加し、既存4テストを維持したまま合計6テストへ拡張。

## ECHO-20260303-002 Voice Boundary / RTH Final Polish（Phase 2 Ambient Defense）

- `src/po_echo/rth.py` collision追跡を `CollisionTrackerConfig` + blake2b fingerprint に再編し、`max_seen_count` と `ttl_ms` の二段pruneで bounded 運用を明文化。
- `src/po_echo/voice_boundary.py` に `ScreenlessSafetyConfig` を追加し、screenless fallback / block 条件の設定注入を可能化（責任境界ルールは非破壊維持）。
- `tests/test_rth.py` に大量同時窓更新・TTL prune・collision warning 検証を追加。
- `tests/test_voice_boundary.py` に `semantic_delta + amount + screenless` 複合 edge case の Hypothesis テストを追加。
- `docs/GROK-COLLABORATION-BIBLE.md` v1.3 Full に Phase 2 Ambient Defense 運用規格を追記し、Voice Boundary / RTH の責任境界ルールを固定化。

## ECHO-20260304-001 Public Benchmark Suite & Performance Testing（Phase 3開始）

- Phase 2の確定状態（Voice Boundary / RTH Final Polish、Bible v1.3 Full）を保持したまま、`tests/benchmarks/` に公開ベンチマークを追加。
- `benchmark_voice_boundary.py` は Hypothesis 生成ケース + `timeit` により 10k / 100k 件の `classify_risk` 性能測定を実施可能化。
- `benchmark_rth.py` は 100,000 rolling windows を対象に `tracemalloc` でメモリ使用量を観測しつつ、collision tracker の prune 制約（`<= max_seen_count`）を検証。
- `docs/BENCHMARK_RESULTS.md` を基準文書として、再現性100%を担保する実行コマンドと結果整理フォーマットを固定。

### Phase 3 KPI（性能・メモリ・再現性）

| KPI | 計測方法 | 判定基準 |
|---|---|---|
| 性能（Voice Boundary） | `RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_voice_boundary.py` | 10k/100kケースがクラッシュなく完走し、throughputが正値 |
| メモリ（RTH） | `RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_rth.py` | 100k窓更新で `tracker_entries <= max_seen_count` を維持 |
| 再現性（公開検証耐性） | `docs/BENCHMARK_RESULTS.md` の固定コマンド再実行 | 同一コマンドで同一判定（pass/fail）が再現可能 |


## ECHO-20260304-002 Benchmark Final Polish & CI Integration（Phase 3最終調整）

- `docs/GROK-COLLABORATION-BIBLE.md` を v1.4 Full へ更新し、Phase 3運用規格（固定seed再現、KPI厳格値、CI benchmark gate、非破壊原則）を追加。
- `tests/benchmarks/benchmark_voice_boundary.py` を固定seed + `register_type_strategy` に更新し、10kケースKPIを `min_seconds < 0.3` でfail-fast化。
- `tests/benchmarks/benchmark_rth.py` を poetry/editable install 両対応の import に変更し、既存 `tracemalloc` と bounded tracker 検証を保持。
- `.github/workflows/benchmark.yml` を新設し、`RUN_PUBLIC_BENCHMARKS=1` で定期実行・KPI違反時failをCIに統合。
- `docs/DEMO_C.md` に Demo C軽量スケルトンを追加し、公開ベンチ結果を Echo Mark 形式で表示するCLI例を提示。

### Phase 3 KPI（最終厳格版）

| KPI | 計測方法 | 判定基準 |
|---|---|---|
| 性能（Voice Boundary） | `RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_voice_boundary.py` | 10kケース `min_seconds < 0.3` |
| メモリ（RTH） | `RUN_PUBLIC_BENCHMARKS=1 pytest -q tests/benchmarks/benchmark_rth.py` | 100k窓で `tracker_entries <= max_seen_count` |
| CI統合 | `.github/workflows/benchmark.yml` | schedule/dispatch どちらでも KPI違反時にfail |

## ECHO-20260305-001 xAI Presentation Materials & Demo C Finalization（Phase 4完了）

- `docs/XAI_PRESENTATION.md` を新規作成し、xAI向け10枚構成（不変原則・benchmark・脅威対策証跡・運用手順）を固定。
- `docs/THREAT_MODEL_UPDATE.md` を追加し、Phase 3 benchmark CI gate/固定seed/dual signature を脅威シナリオ別の証跡として整理。
- `docs/DEMO_C.md` を本実装版へ更新し、`docs/demo_c_example.py` の署名付きCLI運用と検証観点を明文化。
- `docs/OPERATING_PROCEDURE.md` を追加し、benchmark実行・key rotation・監査フロー・インシデント時対応を手順化。
- 既存 Phase 3成果（`docs/BENCHMARK_RESULTS.md`、Voice Boundary / RTH / Echo Mark v3）を非破壊で保持したまま、Phase 4プレゼン即使用可能な文書セットを完成。

### Phase 4 判定

| 項目 | 判定 | 根拠 |
|---|---|---|
| 不変原則適合 | ✅ | 候補/証拠/責任境界を全資料で明示 |
| 非破壊性 | ✅ | 既存benchmark・防御ロジックを未改変 |
| 公開検証耐性 | ✅ | Demo C署名検証 + benchmark gate運用 |
| プレゼン即使用性 | ✅ | スライド構成・運用手順・脅威証跡を文書化 |

## ECHO-20260305-002 Final Cleanup & xAI Gift Package Preparation（Phase 4完了）

- `docs/demo_c_example.py` のデフォルト鍵を完全撤廃し、`--ed25519-private-key` または `--hmac-secret` の明示入力を必須化（未指定時は安全な生成コマンドを提示して終了）。
- `.github/workflows/benchmark.yml` を `pyproject.toml` 由来の依存解決に統一し、`pip install -e .[dev]` のみで benchmark gate を実行可能化。
- `docs/XAI_PRESENTATION.md` へ Markdown→PDF 変換の1コマンドを追加し、配布準備を完了。
- `docs/README.md` を新設し、xAI Gift Package の資料一覧・zip生成導線・Elon向け贈呈メッセージテンプレートを明文化。
- `scripts/make_xai_gift.py` を追加し、docs一式・Demo C CLI・benchmark証跡・履歴文書を1コマンドで zip 生成可能化。
- `docs/GROK-COLLABORATION-BIBLE.md` を v1.5 Full へ更新し、Phase 4運用規格として「xAI贈呈手順」を追加。

### Phase 4 最終判定（xAI Gift Package）

| 項目 | 判定 | 根拠 |
|---|---|---|
| 不変原則適合 | ✅ | 候補/証拠/責任境界を資料・CLI・運用手順で維持 |
| 非破壊性 | ✅ | 既存Phase 1-3防御実装と実測値を保持 |
| 弱点潰し | ✅ | デフォルト鍵撤廃・依存導線統一・配布導線追加を完了 |
| 贈呈即応性 | ✅ | `python scripts/make_xai_gift.py` で一括配布物を生成 |


## ECHO-20260306-001 Final Pre-Gift Cleanup & Test Reconciliation（全Critical/High問題一掃）

- Echo Mark v3仕様に合わせて `tests/test_prop_echo_mark.py` / `tests/test_invariants.py` の引数・schema期待値・HMACフィールド・警告期待を同期。
- `hidden_lockin.py` を `tests/fixtures/hidden_lockin_demo.py` へ移動し、`sk-dummy-...` のデモ用ダミー鍵へ置換。
- `scripts/make_xai_gift.py` に Doberman 事前スキャンを追加し、漏洩検知時は Gift package 生成を停止。
- `src/po_echo/gumdrop_defense.py` の軽量監査を FreedomPressureV2 連携ベースへ更新し、affiliateフラグ依存を除去。
- `src/echo_register/` と `src/world_register/` を明示的ディレクトリ化（`.gitkeep` + README stub）。
- `src/pocore/__init__.py` に deprecated warning と `po_core` 互換エイリアスを追加。

## ECHO-20260306-002 Medium Issues Final Polish & Module Hygiene（全Medium問題一掃）

- Echo Mark v3 の実装責務を `echo_mark_core` / `echo_mark_verify` / `echo_mark_registry` に分割し、`echo_mark.py` は後方互換レイヤーとして既存公開APIを再エクスポート化。
- `diversity.__all__` から `_safe_*` を除外し、外部公開面を non-private のみへ固定。
- `VoiceBoundaryDecision` を immutable 化し、Execution Gate の確認待ちブロックは `replace()` で新インスタンス返却に変更（非破壊のまま挙動維持）。
- vendor分類を精緻化し、`protobuf` / `requests` / `numpy` を low-risk OSS へ移行。

## ECHO-20260308-001 P1 Audio Channel Property Test Expansion（Ear Handshake強化）

- `tests/test_prop_voice_stack.py` に Ear Handshake の性質テストを2件追加し、challenge timestamp の60秒境界（replay防御）を固定化。
- `derive_session_key` の challenge nonce 依存性を property-based で検証し、セッション鍵の再利用リスク低減をテストで担保。
- 既存の `voice_boundary` / `rth` 性質テスト群と合わせて、P1-High「Audio Channel の property-based test 拡張」の完了条件を満たした。

## ECHO-20260308-002 P1 Voice CLI Validation Strengthening（po-cosmic voice検証強化）

- `tests/test_voice_cli.py` に `--show-schema` 固定契約テストを追加し、input/output schema の型境界（object）をCLI出力で検証。
- safe search フローの成功系テストを追加し、`po-cosmic voice` が candidate/evidence/responsibility boundary/Echo Mark を含む出力JSONを生成することを確認。
- 既存の失敗系テスト（必須引数不足・鍵不足・危険操作ブロック）と合わせ、P1-High「`po-cosmic voice` サブコマンド追加」の運用導線をテストで担保した。

## ECHO-20260308-003 P1 Demo C Executability Hardening（実行可能性と互換性の固定）

- `docs/demo_c_example.py` に `src/` 追加パス解決を実装し、リポジトリ直下から単体CLI実行しても `po_echo` import が解決されるよう修正。
- Python 3.10互換のため `datetime.UTC` 依存を `timezone.utc` fallback に置換し、Demo C生成が環境差分で失敗しないよう是正。
- `tests/test_demo_c_example.py` を追加し、署名キー未指定時エラーと HMACモードでの `verification.status == VERIFIED` を回帰検知可能化。
