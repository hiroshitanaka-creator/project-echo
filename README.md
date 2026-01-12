# Project Echo - 責任あるAI開発フレームワーク

Project Echoは、責任あるAI開発のための倫理的フレームワークとツール集です。39人の哲学者による多元的分析、39次元の宇宙倫理評価、そしてAI権利と倫理的ジレンマの探求を通じて、AIシステムの倫理的側面を包括的に検討します。

## 主な機能

### 1. 🧠 39人の哲学者モジュール (`src/po_core/philosophers/`)

Po_coreから統合された39人の哲学者による多角的倫理分析：

- **西洋哲学**: Kant, Aristotle, Plato, Hegel, Nietzsche, Heidegger, Sartre, etc.
- **東洋哲学**: Confucius, Laozi, Zhuangzi, Nagarjuna, Dogen, Nishida, Watsuji
- **現代哲学**: Arendt, Foucault, Deleuze, Derrida, Butler, Levinas

```python
from po_core.philosophers import load_cosmic_philosophers

philosophers = load_cosmic_philosophers()
for philosopher in philosophers:
    perspective = philosopher.analyze(scenario, context)
    print(f"{perspective.name}: {perspective.reasoning}")
```

### 2. 🌌 Cosmic Ethics 39 (`examples/cosmic_ethics_39/`)

39の倫理的次元による宇宙規模の意思決定フレームワーク：

- **13カテゴリ × 3レベル = 39次元**の評価
- 超長期的視点（1000年以上）
- 不確実性と不可逆性の考慮
- AGI開発、火星テラフォーミング、SETI応答などのシナリオ

### 3. 🚃 トロッコ問題とAI倫理 (`examples/trolley_problem_basic/`)

古典的な倫理的ジレンマをAI意思決定に応用：

- 4つの倫理理論（功利主義、義務論、徳倫理、ケアの倫理）
- 自動運転車のジレンマ
- 人間の生命に関わる判断の限界

### 4. 🤖 AI権利の基本探求 (`examples/ai_rights_basic/`)

AIシステムの権利と倫理的地位の評価：

- 意識レベルと自律性に基づく権利評価
- 責任あるAI開発の5原則
- AIの能力段階に応じた権利付与モデル

## クイックスタート

### インストール

```bash
git clone https://github.com/hiroshitanaka-creator/project-echo.git
cd project-echo
```

### 実行例

#### po-cosmic CLI（推奨）

統合評価ツール - 哲学者プリセットで結果が変わることを体験：

```bash
# Cosmic13プリセット（デフォルト）: 長期思考の13哲学者
bin/po-cosmic cosmic-39 --scenario mars --preset cosmic13

# 東アジア哲学プリセット: 関係性と文脈重視
bin/po-cosmic cosmic-39 --scenario mars --preset east_asia

# カント主義プリセット: 義務論と普遍原則重視
bin/po-cosmic cosmic-39 --scenario mars --preset kantian

# 実存主義プリセット: 自由と個人的責任重視
bin/po-cosmic cosmic-39 --scenario mars --preset existentialist

# 古典ギリシャプリセット: 徳と実践知重視
bin/po-cosmic cosmic-39 --scenario mars --preset classical

# 全39人の哲学者を使用
bin/po-cosmic cosmic-39 --scenario agi --preset all --save
```

利用可能なシナリオ:
- `agi`: AGI開発の倫理
- `mars`: 火星テラフォーミング
- `digital`: デジタル意識アップロード
- `seti`: SETI信号への応答

#### 個別例の実行

##### 39人の哲学者による分析

```bash
cd examples/cosmic_ethics_39
python3 philosopher_integration.py
```

##### 宇宙倫理39次元評価

```bash
cd examples/cosmic_ethics_39
python3 run.py
```

##### トロッコ問題シミュレーション

```bash
cd examples/trolley_problem_basic
python3 run.py
```

##### AI権利評価

```bash
cd examples/ai_rights_basic
python3 run.py
```

## ディレクトリ構成

```
project-echo/
├── src/po_core/philosophers/     # 39人の哲学者モジュール
│   ├── base.py                   # PhilosopherPerspective
│   ├── kant.py                   # カント
│   ├── watsuji.py                # 和辻哲郎
│   └── ... (39 philosophers)
│
├── examples/
│   ├── ai_rights_basic/          # AI権利の基本探求
│   ├── trolley_problem_basic/    # トロッコ問題とAI倫理
│   └── cosmic_ethics_39/         # 宇宙倫理39次元
│       ├── run.py
│       ├── philosopher_integration.py
│       └── README.md
│
├── prompts/                      # AIプロンプトテンプレート集
│   ├── 01_code_generation.md
│   ├── 02_proofreading.md
│   └── ... (8 templates)
│
└── LICENSE                       # MIT License
```

## 設計思想

### 倫理的多元主義

単一の倫理理論では不十分。39人の哲学者による多角的分析により：

- **倫理的盲点の発見**: 一つの理論では見えないリスクを発見
- **文化的多様性**: 西洋/東洋、古代/現代の視点を統合
- **価値の多元性**: 定量化できない質的価値も考慮
- **張力の可視化**: どの価値同士が対立しているかを明示

### 哲学者レイヤーアーキテクチャ

哲学者を個別に呼び出すのではなく、「哲学者レイヤー」として処理：

```python
# ✅ 推奨パターン
philosophers = load_cosmic_philosophers()
perspectives = [p.analyze(scenario, context) for p in philosophers]
aggregate_analysis(perspectives)

# ❌ アンチパターン
if scenario.type == "AGI":
    kant_view = Kant().analyze(scenario)
```

### Po_core内面レジスタ

AIの「何を考え、何を考慮しなかったか」を記録：

- `cosmic_weights`: 39次元への重み付け
- `freedom_pressure`: 自由圧力テンソル
- `tension_elements`: 哲学的張力
- `blocked_options`: ブロックされた選択肢とその理由

## 哲学者プリセットによる結果の変化

同一シナリオでも、哲学者プリセットを変えると評価結果が劇的に変わります。これは**倫理的多元主義**の実証です。

### Mars Terraforming シナリオの比較

#### Cosmic13プリセット（13人: 長期思考重視）
```
Top dimensions:
  - deep_time                    1.00  ← 時間スケールが最優先
  - unknown_unknowns             0.53
  - irreversible_risk            0.53
  - existential_risk             0.53
  - direct_responsibility        0.53

Tension topk:
  - deep_time                   +0.102  ← 哲学者間で最大の意見対立
  - unknown_unknowns            +0.068
  - irreversible_risk           +0.068

Active philosophers: 13
```

#### Kantianプリセット（6人: 義務論重視）
```
Top dimensions:
  - deep_time                    0.95
  - universal_rights             0.52  ← 普遍的権利が上位に
  - direct_responsibility        0.52  ← 直接的責任が強調
  - rational_deliberation        0.52  ← 理性的熟慮が重視

Tension topk:
  - universal_rights            +0.048
  - direct_responsibility       +0.048
  - rational_deliberation       +0.048

Active philosophers: 6
```

#### Existentialistプリセット（5人: 自由重視）
```
Top dimensions:
  - deep_time                    1.00
  - unknown_unknowns             0.60  ← リスク次元が高い
  - irreversible_risk            0.60
  - existential_risk             0.60
  - individual_autonomy          0.56  ← 個人の自律性が強調
  - direct_responsibility        0.56  ← 直接責任が重視
  - qualitative_value            0.56  ← 質的価値が上位に

Active philosophers: 5
```

#### East Asiaプリセット（7人: 関係性重視）
```
Top dimensions:
  - deep_time                    0.95
  - present_generation           0.50  ← 全次元がフラット
  - future_generation            0.50
  - local                        0.50
  - global                       0.50

Tension topk:
  - (全次元で tension ≈ 0)  ← 東アジア哲学者間の調和

Active philosophers: 7
```

### 観察されるパターン

1. **Cosmic13**: リスク次元が高く、張力も大きい → 長期視点の哲学者間でも意見が割れる
2. **Kantian**: 義務論的次元（権利・責任・理性）が強調される
3. **Existentialist**: 個人の自律性と質的価値が重視され、リスクも高く評価
4. **East Asia**: 関係性と調和を重視し、張力が小さい（consensus-oriented）

この違いは**哲学者レイヤーアーキテクチャの価値**を実証しています：
- 単一の倫理理論では見えない盲点を発見
- 文化的・哲学的背景によって重視される価値が変わる
- 倫理的判断の「内面レジスタ」として機能

## 責任あるAI開発の原則

1. **透明性**: AIの能力と限界を明確にする
2. **説明責任**: 決定プロセスを説明可能にする
3. **公平性**: すべてのAIシステムに基本的な保護を提供
4. **安全性**: 適切なガードレールと監督機構を実装
5. **人間中心**: 最終的な責任は人間が持つ

## 応用例

- **AI開発チームの倫理トレーニング**
- **AI倫理委員会での議論材料**
- **大学・研究機関での教育ツール**
- **企業のAIガバナンスフレームワーク策定**
- **自動運転車の倫理設定**
- **医療AIの治療優先順位決定**

## 参考文献

### AI倫理
- Stuart Russell - "Human Compatible" (2019)
- Partnership on AI - Responsible AI Practices
- IEEE Ethically Aligned Design
- EU AI Act

### 宇宙倫理・長期主義
- Nick Bostrom - "Astronomical Waste" (2003)
- Toby Ord - "The Precipice" (2020)
- William MacAskill - "What We Owe The Future" (2022)

### 倫理哲学
- Philippa Foot - "The Trolley Problem"
- Derek Parfit - "Reasons and Persons"
- 和辻哲郎 - 「風土」「倫理学」

## コントリビューション

このプロジェクトは教育・研究目的で公開されています。Issue、Pull Request、フィードバックを歓迎します。

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 謝辞

- Po_core: 39人の哲学者モジュールの提供元
- 責任あるAI開発に取り組むすべてのコミュニティ

---

**重要**: 人間の生命に関わる判断をAIに完全に委ねてはならない。AIは意思決定の支援ツールであり、最終的な責任は人間が負う。
