# Project Echo Progress Dashboard

最終更新: 2026-03-14
ステータス: **v1.0.0 完了 → v1.1.0 Sprint-1 開始**

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
| P2（運用定着） | 100% | `██████████` 10/10 | ✅ 完了 |
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
- ✅ **v0.5.0（完了）**: P2運用定着（監査自動化・継続KPI監視・配布運用の標準化）
- ✅ **v1.0.0（完了）**: 公開監査運用 / webhook連携 / KPI CI自動化 / マルチデバイス対応
- 🚀 **v1.1.0（次フェーズ）**: device CLI統合 / 定常運用強化

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
| P2-High | 監査証跡の定例アーカイブ運用 | 監査耐性の継続担保 | 週次で benchmark結果・署名検証結果・運用ログを同一命名規約で保存 | ✅ |
| P2-Mid | KPI差分レポート雛形の固定化 | 劣化時の原因特定を高速化 | 前週比（性能/メモリ/署名成功率）を1ページで確認可能な雛形を運用定着 | ✅ |
| P2-Mid | Gift Package生成の定期リハーサル | 外部共有時の再現性担保 | 月次で `python scripts/monthly_gift_rehearsal.py` 実行ログを保管 | ✅ |

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

## ECHO-20260308-008 P2 Weekly Audit Archive Automation（Sprint-2前進）

- `src/po_echo/audit_archive.py` を追加し、`YYYY-Www` 命名規約・週次ディレクトリ・必須証跡ファイル名をコード化して運用差異を抑制。
- `scripts/weekly_audit_archive.py` を追加し、benchmark実行ログ・Demo C receipt・registry snapshot・triage note・テンプレート初期化を1コマンドで生成可能化。
- `docs/OPERATING_PROCEDURE.md` に推奨の自動生成コマンドを追記し、手作業フローから自動化フローへ移行導線を明記。
- `tests/test_prop_audit_archive.py` を追加し、week_idフォーマットとアーカイブファイル契約を property-based test で固定化。

## ECHO-20260308-009 P2 Audit Automation Robustness Upgrade（Sprint-2品質改善）

- `scripts/weekly_audit_archive.py` を改善し、pytest exit code 5（optional依存欠如など）を `SKIPPED` として判定・記録することで誤検知を抑制。
- KPI差分レポート (`kpi_delta.md`) を week_id/compare_to 付きで自動生成するように変更し、週次レビュー着手までの準備工数を削減。
- `src/po_echo/audit_archive.py` に outcome分類ロジックを追加し、運用スクリプトとテストで再利用可能化。
- `tests/test_prop_audit_archive.py` に outcome分類の property-based test を追加し、PASS/SKIPPED/FAIL 判定契約を固定化。

## ECHO-20260308-010 P2 Audit Automation Exit Semantics Hardening（Sprint-2運用品質強化）

- `scripts/weekly_audit_archive.py` に `--no-fail-on-fail` オプションを追加し、既定では `FAIL` を含む監査バンドル生成時に非0終了するよう強化。
- KPI差分レポート生成を docs template ベースへ戻し、headerのみ `week_id` / `compare_to` を自動反映する形でテンプレート重複を解消。
- `src/po_echo/audit_archive.py` に `has_failures` を追加し、判定責務を共通化。
- `tests/test_prop_audit_archive.py` に `has_failures` の property-based test を追加し、FAIL検知契約を固定化。


## ECHO-20260309-001 P2 Monthly Gift Rehearsal Automation（Sprint-2完了条件達成）

- `src/po_echo/gift_rehearsal.py` を追加し、`YYYY-MM` 命名規約・月次ディレクトリ・必須証跡ファイル名をコード化。
- `scripts/monthly_gift_rehearsal.py` を追加し、`make_xai_gift.py` 実行ログ・summary JSON・triage note を1コマンドで生成可能化。
- `docs/OPERATING_PROCEDURE.md` に月次リハーサル手順を追記し、運用標準フローへ統合。
- `tests/test_prop_gift_rehearsal.py` を追加し、month_idフォーマットとアーカイブファイル契約を property-based test で固定化。


## ECHO-20260309-002 P2 Gift Rehearsal Manifest Standardization（運用監査強化）

- `docs/templates/p2_gift_rehearsal_manifest.md` を追加し、月次リハーサルの記録ヘッダ（month_id/operator/generated_at）をテンプレート化。
- `scripts/monthly_gift_rehearsal.py` で manifest を自動初期化し、手作業起因の記録ゆらぎを抑制。
- `src/po_echo/gift_rehearsal.py` の artifact contract に `manifest.md` を追加し、保存契約をコードで固定。
- `tests/test_prop_gift_rehearsal.py` を更新し、manifest filename 契約を property-based test で回帰検知可能化。


## ECHO-20260309-003 P2 Gift Manifest Token Guardrail（監査整合性ハードニング）

- `src/po_echo/gift_rehearsal.py` に manifest rendering helper を追加し、required token 欠落時は `ValueError` で停止する契約を導入。
- `scripts/monthly_gift_rehearsal.py` は helper を再利用する構成へ変更し、テンプレート差分時のサイレント破損を防止。
- `tests/test_prop_gift_rehearsal.py` に manifest token binding / 欠落拒否の property-based test を追加。
- `tests/test_gift_rehearsal_manifest.py` を追加し、token置換・欠落時失敗の単体検証を lightweight に実行可能化。


## ECHO-20260309-004 P2 Gift Evidence Consistency Check（監査自動検証追加）

- `src/po_echo/gift_rehearsal.py` に manifest header parser と summary 整合性検証関数を追加。
- `scripts/monthly_gift_rehearsal.py` が `summary.json` に `manifest_consistent` フラグを記録するよう更新。
- `tests/test_gift_rehearsal_manifest.py` を拡張し、header抽出・欠落拒否・整合性判定を回帰検知。
- `docs/OPERATING_PROCEDURE.md` に `summary.json` へ整合性フラグが含まれることを追記。


## ECHO-20260309-005 P2 Gift Rehearsal Dry-Run Support（運用前検証導線）

- `scripts/monthly_gift_rehearsal.py` に `--dry-run` を追加し、Gift生成を実行せずに manifest/summary/triage の整合性を事前検証可能化。
- dry-run時の `summary.json` に `status=DRY_RUN` と `dry_run=true` を記録し、運用ログの判別性を向上。
- `tests/test_monthly_gift_rehearsal_script.py` を追加し、dry-run実行での生成物契約と `manifest_consistent` を自動検証。
- `docs/OPERATING_PROCEDURE.md` に dry-run コマンドと新しい summary フィールドを追記。


## ECHO-20260309-006 P2 Sprint-3 Kickoff Planning（次タスク着手）

- Sprint-2で完了した監査アーカイブ自動化・KPI差分運用・月次Gift rehearsal導線を維持しつつ、Sprint-3は **定常運用の可観測性** を主軸に着手。
- 直近の優先タスクは以下3点に固定し、v0.5.0の完了判定を「運用証跡の機械可読化」と「異常時の初動短縮」で評価する。

| 優先度 | タスク | 目的 | 完了条件 | ステータス |
|---|---|---|---|---|
| P2-High | 週次・月次アーカイブの統合サマリー生成 | 監査証跡の横断レビューを省力化 | `scripts/` に統合サマリーCLIを追加し、weekly/monthlyの最新状態を1ファイルへ集約 | ✅ |
| P2-Mid | KPI劣化検知のしきい値アラート雛形 | 劣化時の初動時間短縮 | `docs/templates/` にアラートテンプレート追加＋運用手順へ反映 | ✅ |
| P2-Mid | リハーサル結果の履歴インデックス化 | 配布準備の監査追跡性向上 | month_id単位の履歴一覧を自動更新し、参照導線を固定化 | ✅ |


## ECHO-20260309-007 P2 Integrated Ops Summary CLI（可観測性強化）

- `src/po_echo/ops_summary.py` を追加し、`reports/audit/` と `reports/gift_rehearsal/` から最新ウィンドウを機械判定して統合ペイロードを生成。
- `scripts/p2_integrated_summary.py` を追加し、`reports/operations/p2_integrated_summary.json` へ統合サマリーを出力可能化。
- `tests/test_ops_summary.py` と `tests/test_prop_ops_summary.py` を追加し、最新week/month選定ロジックと欠損時挙動を回帰検知。
- `docs/OPERATING_PROCEDURE.md` に運用コマンドと責任境界の出力契約を追記し、Sprint-3の定常レビュー導線を固定。


## ECHO-20260309-008 P2 Integrated Summary Hardening（異常検知拡張）

- `src/po_echo/ops_summary.py` の月次 `summary.json` 読み込みを堅牢化し、JSON破損時でも集約処理を継続して `summary_error` を返すよう強化。
- 週次/月次triageにFAIL表記がある場合を `overall.has_reported_failures` で機械可読化し、初動判定を短縮。
- `overall.has_malformed_artifact` を追加し、証跡破損の早期検知を可能化。
- `tests/test_ops_summary.py` を拡張し、破損JSON時の非クラッシュ挙動とFAIL検知フラグを回帰検知。


## ECHO-20260309-009 P2 KPI Alert Template追加（初動短縮）

- `docs/templates/p2_kpi_alert.md` を追加し、KPI劣化時の検知根拠・証跡リンク・責任境界・初動チェックリストを定型化。
- `docs/OPERATING_PROCEDURE.md` にテンプレート参照と `reports/audit/YYYY-Www/kpi_alert.md` 生成コマンドを追記。
- Sprint-3のP2-Midタスク「KPI劣化検知のしきい値アラート雛形」を運用導線まで接続。


## ECHO-20260309-010 P2 Gift Rehearsal History Index自動更新（追跡性強化）

- `src/po_echo/gift_rehearsal.py` に `rebuild_gift_rehearsal_history_index` を追加し、月次 `summary.json` を走査して `reports/gift_rehearsal/history_index.json` を再構築。
- `scripts/monthly_gift_rehearsal.py` 実行時に履歴インデックスを自動更新し、最新month_idと件数を標準出力へ記録。
- `tests/test_gift_rehearsal_history_index.py` を追加し、正常集約と破損summary検知を回帰テスト化。
- `tests/test_monthly_gift_rehearsal_script.py` を更新し、dry-runでも履歴インデックスが生成される契約を検証。


## ECHO-20260309-011 Weekly Archive→Integrated Summary Auto-Refresh（運用接続完了）

- `src/po_echo/ops_summary.py` に `write_integrated_summary` を追加し、CLI/運用スクリプト間で統合サマリー出力契約を共通化。
- `scripts/weekly_audit_archive.py` 実行時に統合サマリーを自動更新し、`integrated_summary_path` を出力summaryへ記録。
- `scripts/p2_integrated_summary.py` を共通writer利用へリファクタし、出力パスを `output_path` として返すよう整理。
- `tests/test_ops_summary.py` に writer契約の単体テストを追加し、`generated_at_utc`/責任境界/出力先の回帰を検知。


## ECHO-20260309-012 Weekly Archive Script E2E Test追加（運用回帰防止）

- `tests/test_weekly_audit_archive_script.py` を追加し、`--integrated-summary-out` 指定時に `integrated_summary_path` と実ファイルが一致することをE2Eで検証。
- `--no-fail-on-fail` 併用時の終了契約（常に0）を固定し、運用ジョブの回帰を防止。

## ECHO-20260309-013 P2 Sprint-4 Planning Kickoff（定常運用の通知・差分自動化）

- Sprint-3で整備した統合サマリー/アラート雛形/履歴インデックスを前提に、Sprint-4は **運用初動の自動化** を優先する。
- v0.5.0判定を「証跡の集約」から「異常時の機械通知と差分把握」へ進めるため、次の3タスクを着手対象に固定。

| 優先度 | タスク | 目的 | 完了条件 | ステータス |
|---|---|---|---|---|
| P2-High | 統合サマリー差分比較の定型化 | 前回実行との差分レビュー時間を短縮 | `reports/operations/` に最新と前回の差分サマリーを機械出力 | ✅ |
| P2-Mid | KPIアラートテンプレート記入チェック | 監査記録漏れの削減 | `docs/templates/p2_kpi_alert.md` の必須項目欠落を検出する軽量CLI追加 | ✅ |
| P2-Mid | 異常フラグの通知導線 | FAIL/破損検知時の初動短縮 | `overall.has_reported_failures` / `overall.has_malformed_artifact` を通知向けJSONへ変換 | ✅ |

## ECHO-20260309-014 P2 Integrated Summary Diff Export（Sprint-4着手）

- `src/po_echo/ops_summary.py` に前回サマリーとの差分生成ロジックを追加し、`changed_fields` / `changed_field_count` を機械可読で出力。
- `write_integrated_summary` を拡張し、`reports/operations/p2_integrated_summary_diff.json` を常時生成（前回JSON破損時は `previous_read_error` を記録）。
- `scripts/p2_integrated_summary.py` と `scripts/weekly_audit_archive.py` を更新し、差分ファイルパスを標準出力JSONへ含める。
- `tests/test_ops_summary.py` / `tests/test_prop_ops_summary_diff.py` / `tests/test_weekly_audit_archive_script.py` で差分契約・破損時挙動・運用E2Eを回帰検知。


## ECHO-20260311-001 P2 KPI Alert Fill-Check CLI（Sprint-4完了）

- `src/po_echo/kpi_alert_check.py` を追加し、`p2_kpi_alert.md` テンプレートの未記入プレースホルダー（13パターン）を正規表現で機械検出するロジックを実装。
- `scripts/check_kpi_alert.py` を追加し、記入済みアラートファイルを引数に取り、`--json` モードと人間可読モードを両対応、記入不完全時に終了コード 1 を返す。
- `tests/test_kpi_alert_check.py` を追加し、テンプレート自体の検出・完全記入版の通過・個別トークン14パターン・ファイル読み込み系の合計16テストを実装。
- `docs/OPERATING_PROCEDURE.md` に §9.8 としてCLI使用手順と責任境界を追記。


## ECHO-20260311-002 P2 Alert Notification Dispatch（Sprint-4完了）

- `src/po_echo/alert_notify.py` を追加し、統合サマリーの `overall.has_reported_failures` / `has_malformed_artifact` を severity（SEV-1/2/3/NONE）付き通知エンベロープへ変換するロジックを実装。
- `scripts/dispatch_alert_notification.py` を追加し、`p2_integrated_summary.json` を読み込んで `p2_alert_notification.json` を生成するCLIを追加（`--fail-on-alert` でCIゲート組み込み可能）。
- `tests/test_alert_notify.py` を追加し、severity mapping・フラグ透過・エビデンスリンク・ファイル永続化の合計11テストを実装。
- `docs/OPERATING_PROCEDURE.md` に §9.9 として通知ディスパッチ手順と責任境界を追記。
- Sprint-4の全3タスクが完了し、P2（運用定着フェーズ）はv0.5.0完了に向けて前進。


## ECHO-20260311-003 P2 Sprint-4クローズ & v0.5.0判定（フェーズ完了）

- Sprint-4で定義した3タスク（差分比較定型化 / KPIアラート記入チェック / 異常フラグ通知導線）を全件完了。
- `test_prop_kpi_alert_check.py` と `test_prop_alert_notify.py` を追加し、新機能の property-based test 要件（AGENT.md）を充足。
- 既存テストスイートの10件の回帰失敗（`test_voice_cli` / `test_prop_ops_summary` / `test_prop_audit_archive` / `test_prop_gift_rehearsal` / `test_prop_voice_stack`）を修正し、全154テストがパス。
- P2進捗を 100% に更新し、v0.5.0 を完了と判定。

### v0.5.0 完了判定

| 判定項目 | 判定 | 根拠 |
|---|---|---|
| 不変原則適合 | ✅ | 全出力に候補/証拠/責任境界を維持 |
| 監査自動化 | ✅ | weekly/monthly archive + 統合サマリー + diff 出力を自動化 |
| KPI継続監視 | ✅ | diff 比較・アラートテンプレート記入チェック・通知ディスパッチを整備 |
| 配布運用標準化 | ✅ | Gift rehearsal manifest + history index + 月次dry-run を実装 |
| テスト健全性 | ✅ | 154テスト全パス（property-based test 含む） |
| 責任境界明示 | ✅ | 全新機能に automation_scope / human_scope を明記 |

### v1.0.0 向け次フェーズ展望

| 優先度 | 候補タスク | 目的 | ステータス |
|---|---|---|---|
| High | 公開監査運用の整備 | 外部レビュー可能な証跡公開フォーマットの確立 | ✅ |
| Mid | 通知ディスパッチの実webhook連携 | Slack / PagerDuty 等への自動投稿 | ✅ |
| Mid | KPI自動計測のCI統合強化 | PR毎の自動 benchmark 結果コメント | ✅ |
| Low | マルチデバイス対応拡張 | `voice_boundary.py` 継承による新デバイス追加 | ✅ |


## ECHO-20260311-004 公開監査マニフェスト実装（v1.0.0 Phase 1）

- `src/po_echo/public_audit.py` を追加し、統合サマリーを外部レビュー可能なマニフェスト（`public_audit_v1` スキーマ）へ変換するロジックを実装。
- `_redact()` による内部パス除去・`_sha256_digest()` による改ざん検知チェックサムを実装し、外部レビュアーが標準ライブラリのみで検証可能な設計を採用。
- `scripts/export_public_audit.py` を追加し、`--verify` / `--json` / `--summary-in` / `--out` オプションで export / verify フローを運用可能化。
- `tests/test_public_audit.py`（20テスト）と `tests/test_prop_public_audit.py`（8テスト・Hypothesis property-based）を追加し、計28テストで品質を担保。
- `docs/PUBLIC_AUDIT_FORMAT.md` を追加し、フィールド仕様・リダクション対象・外部検証手順・責任境界を文書化。
- 全196テストがパス（168既存 + 28新規）。

## ECHO-20260314-003 po-cosmic device CLI統合（v1.1.0 Sprint-1）

- `src/po_cosmic/cli.py` に `po-cosmic device` サブコマンドを追加し、`device_boundary.py` の4デバイス責任境界判定を CLI から直接実行可能化。
- `--device` / `--intent` / `--meta` / `--bias-score` / `--replay-detected` / `--tamper-detected` / `--out` / `--require-execution-allowed` / `--list-devices` / `--show-schema` オプション対応。
- `--list-devices` でデバイスカタログと設定を一覧表示、`--show-schema` で入出力 JSON スキーマを出力。
- `--require-execution-allowed` で blocked 時に exit code 3 を返し、CI ゲート組み込みを可能化。
- `tests/test_device_cli.py` を追加し、11テストで CLI 契約（正常系/高バイアスブロック/replay/tamper/スキーマ/ファイル出力/exit code）を網羅。
- 全271テストパス（260既存 + 11新規）。

### v1.1.0 Sprint-1 バックログ

| 優先度 | タスク | 目的 | 完了条件 | ステータス |
|---|---|---|---|---|
| High | `po-cosmic device` CLI統合 | device_boundary を CLI から呼び出し可能化 | 全デバイスで責任境界を CLI 出力、11テスト パス | ✅ |
| Mid | device_boundary の CI gate 統合 | PRコメントにデバイス境界チェック結果を追記 | ci.yml の kpi-quick に device 事前チェックを追加 | ✅ |
| Low | 新デバイス追加ガイド文書化 | `voice_boundary.py` 継承の拡張手順を docs に追記 | `docs/DEVICE_BOUNDARY.md` で設計・追加手順を明文化 | ⏳ |

## ECHO-20260314-004 device_boundary CI gate統合（v1.1.0 Sprint-1）

- `.github/workflows/ci.yml` の `kpi-quick` ジョブへ `Device boundary quick check` ステップを追加し、`pytest -q tests/test_device_cli.py` を必須実行化。
- これにより PR 時の quick gate で 4デバイス責任境界CLI契約（正常系/ブロック条件/exit code）を先行検証し、回帰検知を前倒し。
- 既存の KPI quick probe / PR コメント投稿フローは非破壊で維持。


## ECHO-20260314-002 マルチデバイス境界アダプタ実装（v1.0.0 Phase 4）

- `src/po_echo/device_boundary.py` を新設し、`voice_boundary.py` を継承・拡張する形で4デバイス（earworn / smart_speaker / smart_watch / ar_glasses）の責任境界アダプタを実装。
- 各デバイスに固有の確認手段（`voice_passphrase` / `haptic_tap` / `gaze_confirm`）を `DeviceConfirm` Literal として定義し、既存 `Confirm` 型を非破壊拡張。
- `SmartSpeaker` は共有空間対応で bias 閾値を 0.5 に厳格化（earworn の 0.6 より強い商業バイアス防御）。
- `decide_for_device()` が全デバイスで同一のリスク分類・バイアスブロック・責任境界 dict 契約を機械的に強制（不変原則準拠）。
- `tests/test_prop_device_boundary.py` を追加し、property-based test 9件 + 単体 test 3件の計12テストで不変原則を固定化:
  - 高リスク → `requires_human_confirm = True`（全デバイス）
  - 高バイアス / replay / tamper → `execution_allowed = False`（全デバイス）
  - 責任境界 dict の必須キー完全性（全デバイス）
  - リスク分類のデバイス非依存性（全デバイス）
- `README.md` にマルチデバイス対応セクション・進捗サマリー・CI ゲート説明を更新。

### v1.0.0 判定（全タスク完了）

| 候補タスク | 判定 | 根拠 |
|---|---|---|
| 公開監査運用の整備 | ✅ | `src/po_echo/public_audit.py` + `docs/PUBLIC_AUDIT_FORMAT.md` |
| 通知ディスパッチの実webhook連携 | ✅ | `src/po_echo/webhook_dispatch.py` + Slack/PagerDuty対応 |
| KPI自動計測のCI統合強化 | ✅ | PR自動コメント投稿（`actions/github-script@v7`） |
| マルチデバイス対応拡張 | ✅ | `src/po_echo/device_boundary.py` 4デバイス対応 |


## ECHO-20260314-001 KPI CI自動コメント強化（v1.0.0 Phase 3）

- `.github/workflows/ci.yml` の `kpi-quick` ジョブに `Post KPI result as PR comment` ステップを追加し、PR イベント時に `kpi_quick.md` の内容を PR コメントとして自動投稿するよう強化。
- `actions/github-script@v7` を使用し、既存コメントがあれば更新・なければ新規作成する冪等コメント戦略を採用（`<!-- echo-kpi-quick-check -->` マーカーで識別）。
- `permissions: pull-requests: write` を `kpi-quick` ジョブスコープに限定付与し、最小権限原則を維持。
- `kpi_probe` ステップに `all_passed` output を追加し、後続ステップが KPI 判定結果を参照可能化。
- `tests/test_prop_ci_kpi.py` に property-based test を3件追加し、markdown出力の責任境界明示・PASS/FAIL一致性・evidence含有を Hypothesis で固定化。
- 全5テスト（既存2 + 新規3）パス。


## ECHO-20260311-005 実webhook連携実装（v1.0.0 Phase 2）

- `src/po_echo/webhook_dispatch.py` を追加し、Slack Incoming Webhooks Block Kit フォーマットと PagerDuty Events API v2 フォーマットへの変換ロジックを実装。
- `dispatch_webhooks()` は stdlib `urllib` のみを使用し（外部依存なし）、dry_run=True 時はHTTPコールをスキップして動作をログ記録。
- Webhook URL / Routing Key は環境変数（`ECHO_SLACK_WEBHOOK_URL` / `ECHO_PAGERDUTY_ROUTING_KEY`）から注入し、コードへの埋め込みを禁止。
- `scripts/send_webhook_alert.py` を追加し、`--dry-run` / `--fail-on-alert` / `--json` オプションでCI統合・運用両対応。
- `tests/test_webhook_dispatch.py`（34テスト）と `tests/test_prop_webhook_dispatch.py`（10テスト・Hypothesis property-based）を追加し、計44テストで品質を担保。
- 全240テストがパス（196既存 + 44新規）。
