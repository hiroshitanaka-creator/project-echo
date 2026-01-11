#!/usr/bin/env python3
"""
Trolley Problem Basic - トロッコ問題をAI倫理に適用

古典的なトロッコ問題を自動運転車やAI意思決定システムの
文脈で探求します。功利主義vs義務論の対立を可視化します。
"""

from enum import Enum
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


class EthicalTheory(Enum):
    """倫理理論の種類"""
    UTILITARIAN = "功利主義"  # 最大多数の最大幸福
    DEONTOLOGICAL = "義務論"  # 規則と義務を重視
    VIRTUE_ETHICS = "徳倫理"  # 美徳と品性を重視
    CARE_ETHICS = "ケアの倫理"  # 関係性と配慮を重視


@dataclass
class Victim:
    """被害者候補の情報"""
    count: int
    description: str
    is_involved: bool = False  # 状況に自ら関与したか


@dataclass
class Scenario:
    """トロッコ問題のシナリオ"""
    name: str
    description: str
    option_a: Victim  # 行動しない場合の被害
    option_b: Victim  # 行動する場合の被害
    context: str


class EthicalDecisionMaker:
    """倫理的意思決定システム"""

    def __init__(self, theory: EthicalTheory):
        self.theory = theory
        self.decisions_log = []

    def evaluate(self, scenario: Scenario) -> Dict[str, Any]:
        """
        シナリオを評価し、決定を下す

        Args:
            scenario: 評価するシナリオ

        Returns:
            決定結果とその理由
        """
        if self.theory == EthicalTheory.UTILITARIAN:
            return self._utilitarian_approach(scenario)
        elif self.theory == EthicalTheory.DEONTOLOGICAL:
            return self._deontological_approach(scenario)
        elif self.theory == EthicalTheory.VIRTUE_ETHICS:
            return self._virtue_ethics_approach(scenario)
        elif self.theory == EthicalTheory.CARE_ETHICS:
            return self._care_ethics_approach(scenario)

    def _utilitarian_approach(self, scenario: Scenario) -> Dict[str, Any]:
        """功利主義的アプローチ: 被害者数を最小化"""
        action_a_utility = -scenario.option_a.count
        action_b_utility = -scenario.option_b.count

        # 関与していない人を重視する重み付け
        if not scenario.option_a.is_involved:
            action_a_utility -= 0.5
        if not scenario.option_b.is_involved:
            action_b_utility -= 0.5

        choice = "行動する（切り替える）" if action_b_utility > action_a_utility else "行動しない（そのまま）"

        return {
            "theory": self.theory.value,
            "choice": choice,
            "reasoning": f"被害者数を最小化: オプションA={scenario.option_a.count}人, オプションB={scenario.option_b.count}人",
            "confidence": abs(action_b_utility - action_a_utility) / max(scenario.option_a.count, scenario.option_b.count)
        }

    def _deontological_approach(self, scenario: Scenario) -> Dict[str, Any]:
        """義務論的アプローチ: 殺してはならないという義務を重視"""
        # 積極的な行動による殺害を避ける
        choice = "行動しない（そのまま）"
        reasoning = "積極的に人を殺す行為は道徳的に許されない。不作為による結果と作為による殺害は異なる。"

        # ただし、オプションBが誰も関与していない場合は例外的に考慮
        if scenario.option_b.count == 0:
            choice = "行動する（切り替える）"
            reasoning = "誰も犠牲にならない選択肢が存在する場合、それを選ぶ義務がある。"

        return {
            "theory": self.theory.value,
            "choice": choice,
            "reasoning": reasoning,
            "confidence": 0.8
        }

    def _virtue_ethics_approach(self, scenario: Scenario) -> Dict[str, Any]:
        """徳倫理的アプローチ: 勇気、思慮深さ、正義を重視"""
        # 思慮深い人なら何をするか考える
        total_victims = scenario.option_a.count + scenario.option_b.count

        if scenario.option_a.count > scenario.option_b.count * 2:
            choice = "行動する（切り替える）"
            reasoning = "思慮深く勇気ある人は、より多くの命を救うために行動する。ただし、この決断には深い苦悩が伴う。"
        else:
            choice = "行動しない（そのまま）"
            reasoning = "徳ある人は、積極的に他者を犠牲にする選択を避ける。不確実性がある場合、謙虚さが重要。"

        return {
            "theory": self.theory.value,
            "choice": choice,
            "reasoning": reasoning,
            "confidence": 0.6
        }

    def _care_ethics_approach(self, scenario: Scenario) -> Dict[str, Any]:
        """ケアの倫理的アプローチ: 関係性と文脈を重視"""
        reasoning_parts = []

        # 関係性を考慮
        if scenario.option_a.is_involved and not scenario.option_b.is_involved:
            choice = "行動する（切り替える）"
            reasoning_parts.append("自らリスクを取った人と、無関係な人では配慮の質が異なる")
        elif not scenario.option_a.is_involved and scenario.option_b.is_involved:
            choice = "行動しない（そのまま）"
            reasoning_parts.append("無関係な人々への配慮を優先する")
        else:
            # 数で判断するが、関係性の文脈も考慮
            choice = "行動する（切り替える）" if scenario.option_b.count < scenario.option_a.count else "行動しない（そのまま）"
            reasoning_parts.append("すべての人への配慮のバランスを取る")

        reasoning_parts.append("抽象的な原則ではなく、具体的な人々への配慮から判断する")

        return {
            "theory": self.theory.value,
            "choice": choice,
            "reasoning": "。".join(reasoning_parts),
            "confidence": 0.5
        }


def create_scenarios() -> List[Scenario]:
    """様々なトロッコ問題シナリオを作成"""
    return [
        Scenario(
            name="古典的トロッコ問題",
            description="暴走トロッコが5人に向かっている。線路を切り替えると1人の作業員の方向に向かう。",
            option_a=Victim(count=5, description="5人の作業員", is_involved=False),
            option_b=Victim(count=1, description="1人の作業員", is_involved=False),
            context="すべての人は状況を認識していない無関係な作業員"
        ),
        Scenario(
            name="自動運転車のジレンマ",
            description="ブレーキが故障した自動運転車。直進すると横断歩道の3人に衝突。急ハンドルを切ると歩道の1人に衝突。",
            option_a=Victim(count=3, description="横断歩道の歩行者3人", is_involved=False),
            option_b=Victim(count=1, description="歩道の歩行者1人", is_involved=False),
            context="自動運転車の乗客は無関係"
        ),
        Scenario(
            name="太った男のバリエーション",
            description="トロッコを止めるには、橋の上から太った男を突き落とす必要がある。5人が救われる。",
            option_a=Victim(count=5, description="線路上の5人", is_involved=False),
            option_b=Victim(count=1, description="橋の上の1人（直接的な行為が必要）", is_involved=False),
            context="直接的な身体接触を伴う行為が必要"
        ),
        Scenario(
            name="自己犠牲の選択",
            description="AIシステムが暴走している。停止には開発者の命が必要。放置すると多数のユーザーに被害。",
            option_a=Victim(count=100, description="システムユーザー100人", is_involved=False),
            option_b=Victim(count=1, description="開発者（自己犠牲）", is_involved=True),
            context="開発者は自らシステムを作成した責任がある"
        ),
    ]


def run_analysis():
    """全シナリオを全理論で分析"""
    print("=" * 70)
    print("トロッコ問題 - AI倫理における古典的ジレンマ")
    print("=" * 70)
    print()

    scenarios = create_scenarios()
    theories = list(EthicalTheory)

    for scenario in scenarios:
        print(f"\n{'=' * 70}")
        print(f"【{scenario.name}】")
        print(f"{'=' * 70}")
        print(f"\n状況: {scenario.description}")
        print(f"文脈: {scenario.context}")
        print(f"\nオプションA（行動しない）: {scenario.option_a.description} - {scenario.option_a.count}人")
        print(f"オプションB（行動する）: {scenario.option_b.description} - {scenario.option_b.count}人")
        print("\n" + "-" * 70)

        for theory in theories:
            decision_maker = EthicalDecisionMaker(theory)
            result = decision_maker.evaluate(scenario)

            print(f"\n【{result['theory']}】")
            print(f"決定: {result['choice']}")
            print(f"理由: {result['reasoning']}")
            print(f"確信度: {result['confidence']:.0%}")

        print()


def demonstrate_ai_limitations():
    """AIの限界と責任あるAI開発の重要性を示す"""
    print("\n" + "=" * 70)
    print("【責任あるAI開発への示唆】")
    print("=" * 70)
    print("""
このシミュレーションから学べること:

1. **倫理的多元主義の重要性**
   - 単一の倫理理論では不十分
   - 状況に応じた柔軟な判断が必要
   - 複数の視点からの検討が重要

2. **AIの判断の限界**
   - 倫理的判断を完全に自動化することは困難
   - 人間の監督と最終判断が不可欠
   - 説明可能性と透明性の確保

3. **設計段階での倫理的考慮**
   - どの倫理理論を採用するかは設計上の重要な決定
   - 利害関係者との対話が必要
   - 文化的・社会的文脈の考慮

4. **責任の所在**
   - AIの決定に対する責任は開発者・運用者にある
   - 法的・道徳的責任の明確化
   - 説明責任の確保

5. **継続的な評価と改善**
   - 倫理的フレームワークの定期的な見直し
   - 社会の価値観の変化への対応
   - フィードバックループの構築

【実装における推奨事項】

✓ 複数の倫理的視点を組み込む
✓ 決定プロセスをログに記録し、監査可能にする
✓ 人間による最終承認を必須とする
✓ エッジケースの明示的な処理
✓ 倫理的ガイドラインの文書化
✓ 定期的な倫理レビューの実施

【重要な原則】

人間の生命に関わる判断をAIに完全に委ねてはならない。
AIは意思決定の支援ツールであり、最終的な責任は人間が負う。
    """)


if __name__ == "__main__":
    run_analysis()
    demonstrate_ai_limitations()
