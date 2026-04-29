"""
对手行为预测器 (BehaviorPredictor)

在暗箱对战中，我们无法预知对手的行动选择，但可以通过以下信息
推断对手在当前局面下最可能采取的行动分布：

1. 历史行为模式 — 对手在本场对局中的行动倾向
   （攻击比例、换宠频率、聚能频率、应对成功率等）
2. 局面特征 — 当前 HP/能量/属性克制等直接影响行动选择
3. 博弈常识 — 基于游戏机制的通用策略偏好
   （低血换宠、克制时攻击、能量不足聚能等）

输出：对手每个合法行动的概率分布 → 供搜索引擎做期望值搜索
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.events import BattleSide
from ..core.observation import ObservationState


# ── 对手行为档案 ─────────────────────────────────────────────────

@dataclass(slots=True)
class ActionRecord:
    """单条对手行动记录"""
    turn: int
    pet_name: str
    action_type: str       # "skill" | "switch" | "gather_energy" | "leader" | "willpower"
    skill_name: str = ""
    switch_to: str = ""
    was_low_hp: bool = False   # 行动时 HP < 40%
    had_type_advantage: bool = False  # 当时是否有属性克制优势


@dataclass(slots=True)
class BehaviorProfile:
    """对手行为画像"""
    total_actions: int = 0
    skill_uses: int = 0
    switch_count: int = 0
    gather_count: int = 0
    leader_count: int = 0
    willpower_count: int = 0

    # 上下文行为计数
    switch_when_low_hp: int = 0       # 低血量时换宠次数
    low_hp_action_count: int = 0      # 低血量时总行动次数
    attack_when_advantage: int = 0    # 有克制时攻击次数
    advantage_action_count: int = 0   # 有克制时总行动次数

    # 技能使用分布
    skill_use_counts: dict[str, int] = field(default_factory=dict)

    # 换宠偏好
    switch_targets: dict[str, int] = field(default_factory=dict)

    @property
    def attack_tendency(self) -> float:
        """攻击倾向 (0~1)"""
        if self.total_actions == 0:
            return 0.5
        return self.skill_uses / self.total_actions

    @property
    def switch_tendency(self) -> float:
        """换宠倾向 (0~1)"""
        if self.total_actions == 0:
            return 0.15
        return self.switch_count / self.total_actions

    @property
    def low_hp_switch_rate(self) -> float:
        """低血量时的换宠率"""
        if self.low_hp_action_count == 0:
            return 0.5  # 先验：半数情况会换宠
        return self.switch_when_low_hp / self.low_hp_action_count

    @property
    def advantage_attack_rate(self) -> float:
        """有属性克制时的攻击率"""
        if self.advantage_action_count == 0:
            return 0.7  # 先验：大概率会选择攻击
        return self.attack_when_advantage / self.advantage_action_count


# ── 行动概率条目 ─────────────────────────────────────────────────

@dataclass(slots=True)
class ActionProbability:
    """单个行动的预测概率"""
    action_type: str       # "skill" | "switch" | "gather_energy" | "leader" | "willpower"
    skill_name: str = ""
    switch_target: str = ""
    probability: float = 0.0
    rationale: str = ""


@dataclass(slots=True)
class PredictionResult:
    """对手行为预测结果"""
    action_distribution: list[ActionProbability] = field(default_factory=list)
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def most_likely_action(self) -> ActionProbability | None:
        if not self.action_distribution:
            return None
        return max(self.action_distribution, key=lambda a: a.probability)

    def get_probability(self, action_type: str, skill_name: str = "") -> float:
        """获取特定行动的概率"""
        for ap in self.action_distribution:
            if ap.action_type == action_type:
                if action_type == "skill" and ap.skill_name != skill_name:
                    continue
                return ap.probability
        return 0.0


# ── 对手行为预测器 ───────────────────────────────────────────────

class BehaviorPredictor:
    """
    基于历史行为模式和局面特征预测对手行动分布。

    工作流程：
    1. record_action() — 每回合对手行动后，记录历史
    2. predict() — 在需要决策时，输出对手行动概率分布
    3. 搜索引擎使用概率分布做加权期望搜索

    预测模型（分层贝叶斯思路）：
      P(action | 局面) ∝ P_prior(action) × P_situation(action | 局面特征) × P_history(action | 历史)
    """

    def __init__(self) -> None:
        self._history: list[ActionRecord] = []
        self._profile = BehaviorProfile()

    # ── 历史记录 ─────────────────────────────────────────────────

    def record_action(self, record: ActionRecord) -> None:
        """记录一条对手行动"""
        self._history.append(record)
        p = self._profile
        p.total_actions += 1

        if record.action_type == "skill":
            p.skill_uses += 1
            p.skill_use_counts[record.skill_name] = (
                p.skill_use_counts.get(record.skill_name, 0) + 1
            )
        elif record.action_type == "switch":
            p.switch_count += 1
            if record.switch_to:
                p.switch_targets[record.switch_to] = (
                    p.switch_targets.get(record.switch_to, 0) + 1
                )
        elif record.action_type == "gather_energy":
            p.gather_count += 1
        elif record.action_type == "leader":
            p.leader_count += 1
        elif record.action_type == "willpower":
            p.willpower_count += 1

        if record.was_low_hp:
            p.low_hp_action_count += 1
            if record.action_type == "switch":
                p.switch_when_low_hp += 1

        if record.had_type_advantage:
            p.advantage_action_count += 1
            if record.action_type == "skill":
                p.attack_when_advantage += 1

    def record_from_event(
        self,
        turn: int,
        pet_name: str,
        action_type: str,
        skill_name: str = "",
        switch_to: str = "",
        hp_percent: float | None = None,
        has_type_advantage: bool = False,
    ) -> None:
        """从事件数据构建记录"""
        self.record_action(ActionRecord(
            turn=turn,
            pet_name=pet_name,
            action_type=action_type,
            skill_name=skill_name,
            switch_to=switch_to,
            was_low_hp=(hp_percent is not None and hp_percent < 40.0),
            had_type_advantage=has_type_advantage,
        ))

    @property
    def profile(self) -> BehaviorProfile:
        return self._profile

    # ── 行为预测 ─────────────────────────────────────────────────

    def predict(
        self,
        observation: ObservationState,
        opponent_pet_name: str,
        my_pet_name: str,
        opponent_hp_percent: float | None = None,
        opponent_energy: int | None = None,
        opponent_observed_skills: list[str] | None = None,
        my_hp_percent: float | None = None,
        has_type_advantage_over_me: bool = False,
        i_have_type_advantage: bool = False,
        opponent_alive_bench: list[str] | None = None,
    ) -> PredictionResult:
        """
        预测对手在当前局面下的行动分布。

        参数：
            observation: 当前观测状态
            opponent_pet_name: 对手当前出战精灵
            my_pet_name: 我方当前出战精灵
            opponent_hp_percent: 对手精灵HP%（0~100）
            opponent_energy: 对手精灵当前能量
            opponent_observed_skills: 对手已观测的技能列表
            my_hp_percent: 我方精灵HP%
            has_type_advantage_over_me: 对手是否克制我
            i_have_type_advantage: 我是否克制对手
            opponent_alive_bench: 对手后备存活精灵列表

        Returns:
            PredictionResult: 行动概率分布
        """
        scores: dict[str, float] = {}
        notes: list[str] = []

        hp = opponent_hp_percent if opponent_hp_percent is not None else 100.0
        energy = opponent_energy if opponent_energy is not None else 5
        skills = opponent_observed_skills or []
        bench = opponent_alive_bench or []
        p = self._profile

        # ═══════════════════════════════════════════════════════════
        # 第一层：先验分数（博弈常识）
        # ═══════════════════════════════════════════════════════════

        # 技能使用是默认行为
        for skill_name in skills:
            scores[f"skill:{skill_name}"] = 3.0

        # 换宠基础分
        if bench:
            for bench_pet in bench:
                scores[f"switch:{bench_pet}"] = 1.0

        # 聚能基础分
        scores["gather_energy"] = 1.5

        # ═══════════════════════════════════════════════════════════
        # 第二层：局面特征调整
        # ═══════════════════════════════════════════════════════════

        # ── 血量相关 ─────────────────────────────────────────────
        if hp < 25.0:
            # 残血：大幅提升换宠概率
            for key in list(scores):
                if key.startswith("switch:"):
                    scores[key] *= 3.0
            notes.append("对手残血，预计大概率换宠")
        elif hp < 40.0:
            for key in list(scores):
                if key.startswith("switch:"):
                    scores[key] *= 2.0
            notes.append("对手低血量，可能换宠")

        if hp > 80.0:
            # 满血：降低换宠概率
            for key in list(scores):
                if key.startswith("switch:"):
                    scores[key] *= 0.5

        # ── 能量相关 ─────────────────────────────────────────────
        if energy <= 2:
            scores["gather_energy"] *= 2.5
            # 低能量时高耗能技能不太可能
            notes.append("对手能量低，可能聚能")

        if energy >= 8:
            # 高能量时聚能概率降低
            scores["gather_energy"] *= 0.3
            # 高能量时更可能用强力技能
            for key in list(scores):
                if key.startswith("skill:"):
                    scores[key] *= 1.3

        # ── 属性克制相关 ─────────────────────────────────────────
        if has_type_advantage_over_me:
            # 对手克制我：更可能攻击
            for key in list(scores):
                if key.startswith("skill:"):
                    scores[key] *= 1.8
            for key in list(scores):
                if key.startswith("switch:"):
                    scores[key] *= 0.5
            notes.append("对手克制我方，预计偏向攻击")

        if i_have_type_advantage:
            # 我克制对手：对手更可能换宠
            for key in list(scores):
                if key.startswith("switch:"):
                    scores[key] *= 2.0
            for key in list(scores):
                if key.startswith("skill:"):
                    scores[key] *= 0.7
            notes.append("我方克制对手，对手可能换宠")

        # ── 我方低血量：对手可能读切 ─────────────────────────────
        my_hp = my_hp_percent if my_hp_percent is not None else 100.0
        if my_hp < 30.0:
            # 我方残血，对手可能预读我方换宠而选择"埋伏"类技能
            # 或者直接收人头
            for key in list(scores):
                if key.startswith("skill:"):
                    scores[key] *= 1.5
            notes.append("我方残血，对手可能强攻收人头")

        # ═══════════════════════════════════════════════════════════
        # 第三层：历史行为模式修正
        # ═══════════════════════════════════════════════════════════
        if p.total_actions >= 3:
            # 有足够历史数据，用历史倾向修正

            # 攻击倾向
            attack_bias = p.attack_tendency / 0.5  # 归一化到先验0.5
            for key in list(scores):
                if key.startswith("skill:"):
                    scores[key] *= max(0.3, min(2.0, attack_bias))

            # 换宠倾向
            switch_bias = p.switch_tendency / 0.15  # 归一化到先验0.15
            for key in list(scores):
                if key.startswith("switch:"):
                    scores[key] *= max(0.3, min(2.5, switch_bias))

            # 低血换宠率
            if hp < 40.0 and p.low_hp_action_count >= 2:
                low_hp_switch = p.low_hp_switch_rate / 0.5
                for key in list(scores):
                    if key.startswith("switch:"):
                        scores[key] *= max(0.5, min(2.0, low_hp_switch))

            # 有克制时的攻击率
            if has_type_advantage_over_me and p.advantage_action_count >= 2:
                adv_attack = p.advantage_attack_rate / 0.7
                for key in list(scores):
                    if key.startswith("skill:"):
                        scores[key] *= max(0.5, min(2.0, adv_attack))

            # 偏好特定技能
            for skill_name in skills:
                key = f"skill:{skill_name}"
                if key in scores and skill_name in p.skill_use_counts:
                    use_count = p.skill_use_counts[skill_name]
                    # 频繁使用的技能概率上升
                    scores[key] *= 1.0 + min(0.5, use_count * 0.1)

            # 偏好换到特定精灵
            for bench_pet in bench:
                key = f"switch:{bench_pet}"
                if key in scores and bench_pet in p.switch_targets:
                    target_count = p.switch_targets[bench_pet]
                    scores[key] *= 1.0 + min(0.8, target_count * 0.2)

            notes.append(f"基于{p.total_actions}条历史记录修正")

        # ═══════════════════════════════════════════════════════════
        # 第四层：特定精灵技能的策略推断
        # ═══════════════════════════════════════════════════════════

        # 如果没有后备可换，排除所有换宠选项
        if not bench:
            scores = {k: v for k, v in scores.items() if not k.startswith("switch:")}

        # ═══════════════════════════════════════════════════════════
        # 归一化为概率分布
        # ═══════════════════════════════════════════════════════════
        total = sum(scores.values())
        if total <= 0:
            return PredictionResult(
                confidence=0.0,
                notes=["无法预测：无合法行动信息"],
            )

        distribution: list[ActionProbability] = []
        for key, score in sorted(scores.items(), key=lambda x: -x[1]):
            prob = score / total
            if prob < 0.01:
                continue  # 忽略极低概率行动

            if key.startswith("skill:"):
                skill_name = key[6:]
                distribution.append(ActionProbability(
                    action_type="skill",
                    skill_name=skill_name,
                    probability=prob,
                    rationale=f"技能 {skill_name}",
                ))
            elif key.startswith("switch:"):
                target = key[7:]
                distribution.append(ActionProbability(
                    action_type="switch",
                    switch_target=target,
                    probability=prob,
                    rationale=f"换宠至 {target}",
                ))
            elif key == "gather_energy":
                distribution.append(ActionProbability(
                    action_type="gather_energy",
                    probability=prob,
                    rationale="聚能",
                ))

        # 置信度：基于信息量
        confidence = min(0.9, 0.3 + 0.05 * p.total_actions + 0.05 * len(skills))

        return PredictionResult(
            action_distribution=distribution,
            confidence=confidence,
            notes=notes,
        )

    # ── 预读分析 ─────────────────────────────────────────────────

    def analyze_reads(
        self,
        prediction: PredictionResult,
        threshold: float = 0.35,
    ) -> list[dict]:
        """
        分析预读（reads/yomi）机会。

        预读 = 确信对手会做某个行动时，选择针对该行动的最优反制。
        例如：预读对手换宠 → 使用"埋伏"类技能（敌方换宠时多段攻击）
              预读对手攻击 → 使用应对技能

        参数：
            prediction: 对手行为预测结果
            threshold: 概率阈值（>= 此值的行动才生成预读建议）

        返回：
            预读机会列表，每个包含 {
                "read_type": "读切" | "读攻" | "读能",
                "opponent_action": 预判的对手行动,
                "probability": 发生概率,
                "suggested_counter": 建议的反制策略描述,
                "risk": 预读失败的风险描述,
            }
        """
        reads: list[dict] = []

        if not prediction.action_distribution:
            return reads

        # 汇总同类行动概率
        skill_total = 0.0
        switch_total = 0.0
        gather_total = 0.0
        top_skill = ""
        top_skill_prob = 0.0
        top_switch = ""
        top_switch_prob = 0.0

        for ap in prediction.action_distribution:
            if ap.action_type == "skill":
                skill_total += ap.probability
                if ap.probability > top_skill_prob:
                    top_skill = ap.skill_name
                    top_skill_prob = ap.probability
            elif ap.action_type == "switch":
                switch_total += ap.probability
                if ap.probability > top_switch_prob:
                    top_switch = ap.switch_target
                    top_switch_prob = ap.probability
            elif ap.action_type == "gather_energy":
                gather_total += ap.probability

        # ── 读切（预判对手换宠）───────────────────────────────
        if switch_total >= threshold:
            reads.append({
                "read_type": "读切",
                "opponent_action": f"换宠（概率{switch_total:.0%}，最可能换{top_switch}）",
                "probability": switch_total,
                "suggested_counter": (
                    "使用「埋伏」「灵光」「回旋踢」「针刺射击」等"
                    "对换宠有额外效果的技能，或用强力攻击预打下一只精灵"
                ),
                "risk": f"若对手实际攻击（概率{skill_total:.0%}），则可能损失先手或浪费回合",
            })

        # ── 读攻（预判对手使用技能）───────────────────────────
        if skill_total >= threshold:
            reads.append({
                "read_type": "读攻",
                "opponent_action": f"攻击（概率{skill_total:.0%}，最可能用{top_skill}）",
                "probability": skill_total,
                "suggested_counter": (
                    "使用应对技能应对其攻击类别，或在确认克制时换上对抗精灵"
                ),
                "risk": f"若对手实际换宠（概率{switch_total:.0%}），应对技能可能落空",
            })

        # ── 读能（预判对手聚能）───────────────────────────────
        if gather_total >= threshold:
            reads.append({
                "read_type": "读能",
                "opponent_action": f"聚能（概率{gather_total:.0%}）",
                "probability": gather_total,
                "suggested_counter": (
                    "对手放弃行动聚能时是最佳攻击/施加状态窗口，"
                    "使用高威力技能或设置印记/buff"
                ),
                "risk": f"若对手实际攻击（概率{skill_total:.0%}），则可能被先手击杀",
            })

        return reads

    # ── 状态重置 ─────────────────────────────────────────────────

    def reset(self) -> None:
        """清空历史，开始新对局"""
        self._history.clear()
        self._profile = BehaviorProfile()

    def get_summary(self) -> dict:
        """获取当前行为画像摘要"""
        p = self._profile
        return {
            "total_actions": p.total_actions,
            "attack_tendency": round(p.attack_tendency, 3),
            "switch_tendency": round(p.switch_tendency, 3),
            "low_hp_switch_rate": round(p.low_hp_switch_rate, 3),
            "advantage_attack_rate": round(p.advantage_attack_rate, 3),
            "top_skills": sorted(
                p.skill_use_counts.items(), key=lambda x: -x[1]
            )[:5],
            "top_switch_targets": sorted(
                p.switch_targets.items(), key=lambda x: -x[1]
            )[:3],
        }
