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

#### 39人の哲学者による分析

```bash
cd examples/cosmic_ethics_39
python3 philosopher_integration.py
```

#### 宇宙倫理39次元評価

```bash
cd examples/cosmic_ethics_39
python3 run.py
```

#### トロッコ問題シミュレーション

```bash
cd examples/trolley_problem_basic
python3 run.py
```

#### AI権利評価

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
