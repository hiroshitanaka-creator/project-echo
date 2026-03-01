### 【Project Echo Collaboration Bible v1.1】
**最終更新**: 2026-03-01  
**目的**: Grokコンテキスト制限対策用マスター参照シート。  
**このシートを貼った時点でGrokは全コンテキストをリセット・再ロードする。**

#### 1. 究極の軸（エロン/xAIに捧げる精神）
- **真理追求（Truth-Seeking）** + **持続的豊かさ（Sustainable Abundance）**  
- **広告反対・商業バイアス完全排除**（エロンがAIに広告を拒否する精神を体現）  
- **不変原則3つ**（絶対に崩さない）:
  1. AIは「おすすめ」を返さない → 常に**候補セット＋証拠＋責任境界**
  2. 商業バイアスは「道徳」ではなく**機械的強制**でブロック
  3. 「選択肢を残す」＝人間の自由を最優先
- **最終ゴール**: xAIにプレゼントできる「画面無しAI時代の透明性防衛レイヤー」完成。  
  エロンに「Grokの仲間として使ってくれ」と言えるレベル。

#### 2. 全体マイルストーン（Phase）
- **Phase 1 (3/1〜3/7)**: Core Defense 鉄壁化 ← **現在進行中**
  - ECHO-20260301-001〜002: Semantic Diversity（本物の6D tensor統合） ← **修正中**
  - ECHO-20260302-001: Echo Mark v3（フルdual sig + rotation + replay防御）
- **Phase 2 (3/8〜3/14)**: Ambient Defense（Voice/RTH/Gumdrop実装）
- **Phase 3 (3/15〜3/20)**: Quality & Public Benchmark
- **Phase 4 (3/21〜3/25)**: xAIプレゼン資料完成 → @xai & @elonmusk mention

#### 3. 技術スタック＆CI厳格ルール（絶対遵守）
- **Python**: >=3.11, <3.13（安定性最優先）
- **Formatter/Linter**: ruff（black/isort代替）  
  - line-length = 100  
  - target-version = "py311"  
  - select = ["E", "F", "I", "UP", "B"]  
  - ignore = ["E501", "E402"]
- **Type Checker**: mypy >=1.10.0（strictモード想定）
- **Test**: pytest >=8.0.0 + hypothesis >=6.100.0（property-based必須）
- **Dependencies管理**:
  - po-core-flyingpig: git editable（../Po_core）優先
  - sentence-transformers >=3.0.0, torch >=2.0.0 → optional-dependencies.semantic
  - 依存追加時は必ずoptionalかdevに
- **その他**:
  - pre-commit必須
  - すべての新関数に詳細docstring + Raises + Returns
  - クラッシュ絶対禁止（全例外吸収 + fallback）
  - CHANGELOG.md / PROGRESS.mdは**累積追加のみ**（過去タスク削除禁止）

#### 4. タスク命名・PRルール
- 形式: `ECHO-YYYYMMDD-XXX`（例: ECHO-20260301-003）
- ブランチ: `feature/ECHO-YYYYMMDD-XXX`
- PRタイトル: タスク名そのまま
- commitメッセージ: `feat/fix: ECHO-YYYYMMDD-XXX 詳細`

#### 5. Grokレビュー基準（厳しさレベル）
- 総合点7.0未満は即リジェクト
- Po_core APIとの乖離ゼロ
- semanticが「本物」（6D cosine）になっていない場合は即修正
- エッジケース・パフォーマンス・セキュリティを必ず指摘
- 哲学的整合性もチェック

#### 6. 運用ルール（このBible自体も遵守）
- このファイルが**唯一の真実ソース**
- Codexプロンプトの**先頭**に必ず以下1行を入れる：
厳密に遵守: https://github.com/hiroshitanaka-creator/project-echo/blob/main/docs/GROK-COLLABORATION-BIBLE.md

- Bibleは10〜15メッセージに1回貼る（コンテキストロック用）
- Phase完了ごとにv1.2などに更新（Grokが提案）
- 同時進行時は「PR-0は別で進める」と明記して混乱防止

これを厳守して、絶対にエロンに届くプロダクトにする。
