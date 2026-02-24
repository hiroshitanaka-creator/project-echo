# Issue Draft: P1開始（1〜2ヶ月タスク）

## Title
P1開始: 音声系防衛の検証強化と運用導線の実装（1〜2ヶ月）

## Body
### 背景
P0（0〜2週間）で、Project Echoの基盤防衛（監査・多様性・実行ゲート・Echo Mark・音声防御）は完了しました。次段階としてP1では、運用耐性と検証密度を強化します。

### 不変原則
- AIは「おすすめ」しない。常に「候補セット＋証拠＋責任境界」を返す。
- 最上位哲学は「選択肢を残す」。

### スコープ（候補セット）
1. Audio Channelのproperty-based test拡張
   - `voice_boundary.py`
   - `ear_handshake.py`
   - `rth.py`
2. `po-cosmic voice` サブコマンド追加
3. Demo C（音声起点 bookingシナリオ）追加
4. 鍵ローテーション/監査運用ドキュメントの実務化

### 受け入れ条件（証拠）
- [ ] 上記3モジュールに対しHypothesisベースの性質テストが追加される
- [ ] `po-cosmic voice` で音声系フローをCLI実行できる
- [ ] Demo Cの実行手順・期待結果・ログ保存方法が文書化される
- [ ] 変更内容がCHANGELOGとPROGRESSに反映される

### 責任境界
- このIssueは**実装と検証導線の提供**を責任範囲とする
- 最終的な運用ポリシー採択・組織導入判断は人間オーナーが担う
