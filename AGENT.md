# 🐷 AGENT.md - AIエージェント開発ガイド

**このリポジトリを進めるすべてのAIエージェントへ**

## 1. 飛べない豚の不変原則（絶対遵守）
- AIは「おすすめ」しない → 常に**候補セット＋証拠＋責任境界**を返す
- 商業バイアスは**システムで強制排除**（道徳じゃなく機械的に）
- 「失敗しなかった意図」課金モデル（OpenAIのWorld Register戦略）に対してEcho Markで透明性を強制
- 豚の哲学：**選択肢を残す**こと。それがAIの未来を守ること

## 2. コーディングルール
- すべての新機能は **property-based test** 必須（Hypothesis使用）
- Echo Markは常に **Ed25519 + HMAC dual signature**
- 音声（Sweetpea）系は Rolling Transcript Hash（生音声保存禁止）
- コメントは「なぜこの設計か」を必ず書く（Po_core 39人哲学引用可）

## 3. 拡張の仕方
- Gumdrop対策 → `src/po_echo/gumdrop_defense.py` を作成
- 新デバイス対応 → `voice_boundary.py` を継承
- 脅威モデル追加 → `docs/` にmdファイル追加 → CHANGELOG更新

## 4. 作業フロー
1. Issue作成 or 既存Issue参照
2. ブランチ：`feature/xxx` or `claude/xxx`
3. テスト全パス確認
4. PR → 人間レビュー（最終判断は飛べない豚）

**「これでいいか？」と迷ったら、豚の言葉を思い出せ**  
「AIの便利が金儲けの罠になる前に、防ぎたい」

一緒に豚を飛ばそう。🐷🎈
