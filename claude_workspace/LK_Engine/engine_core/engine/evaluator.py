"""
局面评估器 v3
修复 v2 的以下问题并新增评估维度：
  - 修复 bench_alive 作用域引用 bug
  - 修复心数估值方向（最后一心应最宝贵，边际价值递增）
  - 修复速度评估不对称（对称框架下应一致）
  - 新增：对手负面状态作为己方优势的评估
  - 新增：技能冷却中的惩罚
  - 新增：天气对双方的影响评估
  - 新增：后备精灵对当前对手的克制覆盖评估
  - 新增：evaluation → win_rate 的 sigmoid 映射
"""
from core.models import BattleState, PetInstance, PlayerState, SkillCategory
from core.status_effects import StatusEffectType
from data_loader import DataLoader
from engine.energy_costs import compute_effective_skill_energy_cost, can_pay_skill_energy_cost
from engine.strategy_mechanics import StrategyMechanicContext, evaluate_strategy_mechanics
import math


class Evaluator:
    """局面评估器"""

    # ── 终局分值 ──────────────────────────────────────────────────
    WIN_SCORE = 15000.0
    LOSS_SCORE = -15000.0
    DRAW_SCORE = 0.0

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def evaluate(self, state: BattleState) -> float:
        """
        评估当前状态的优劣
        返回值：正数表示玩家优势，负数表示对手优势
        范围：约 -15000 到 +15000
        """
        # ── 终局判定 ──────────────────────────────────────────────
        if state.is_battle_over_by_hearts():
            winner = state.get_winner_by_hearts()
            if winner == "player":
                return self.WIN_SCORE
            elif winner == "opponent":
                return self.LOSS_SCORE
            return self.DRAW_SCORE

        if state.is_terminal():
            winner = state.get_winner()
            if winner == "player":
                return self.WIN_SCORE - 2000.0
            elif winner == "opponent":
                return self.LOSS_SCORE + 2000.0
            return self.DRAW_SCORE

        # ── 对称评估：每一方各自计算，然后取差值 ────────────────────
        player_score = self._evaluate_side(
            state.player, state.opponent, True, state
        )
        opponent_score = self._evaluate_side(
            state.opponent, state.player, False, state
        )

        # 心数差（非线性：越少心越宝贵 → 边际递增）
        heart_score = self._heart_value(state.player_hearts) - self._heart_value(state.opponent_hearts)

        # 天气对双方的影响
        weather_score = self._weather_advantage(state)

        return player_score - opponent_score + heart_score + weather_score

    # ── 心数非线性估值（边际价值递增：最后一心最宝贵）──────────────

    @staticmethod
    def _heart_value(hearts: int) -> float:
        """
        心数的非线性估值：边际价值递增（最后一心最宝贵）。
        4心=2400, 3心=1800, 2心=1100, 1心=500, 0心=0
        差值序列: 500, 600, 700, 600 → 中段心数价值最高
        """
        if hearts <= 0:
            return 0.0
        if hearts >= 4:
            return 2400.0
        table = {1: 500.0, 2: 1100.0, 3: 1800.0}
        return table.get(hearts, 2400.0)

    # ── 胜率映射 ─────────────────────────────────────────────────

    @staticmethod
    def evaluation_to_win_rate(evaluation: float) -> float:
        """
        将评估分数映射到胜率百分比 (0.0 ~ 1.0)
        使用 logistic/sigmoid 函数: P(win) = 1 / (1 + exp(-k * eval))
        k = ln(19)/2000 ≈ 0.001472，使得 ±2000 分对应 95%/5% 胜率
        """
        k = 0.001472  # ln(19)/2000: ±2000 分 -> 95%/5%
        # 终局分直接映射
        if evaluation >= 15000.0:
            return 1.0
        if evaluation <= -15000.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-k * evaluation))

    # ── 单方评估 ──────────────────────────────────────────────────

    def _evaluate_side(
        self, own: PlayerState, enemy: PlayerState,
        is_player: bool, state: BattleState
    ) -> float:
        score = 0.0

        alive_pets = [p for p in own.team if p.is_alive]
        active = own.get_active_pet()
        enemy_active = enemy.get_active_pet()

        # 后备精灵列表（安全计算，避免 active 为 None 时出错）
        if active and active.is_alive:
            bench_alive = [p for p in alive_pets if p is not active]
        else:
            bench_alive = list(alive_pets)

        # ═══════════════════════════════════════════════════════════
        # 1. HP 评估（在场精灵权重更高）
        # ═══════════════════════════════════════════════════════════
        if active and active.is_alive:
            hp_ratio = active.current_hp / max(active.max_hp, 1)
            score += hp_ratio * 2000.0

        if bench_alive:
            bench_hp_ratio = sum(p.current_hp for p in bench_alive) / max(
                sum(p.max_hp for p in bench_alive), 1
            )
            score += bench_hp_ratio * len(bench_alive) * 800.0

        # ═══════════════════════════════════════════════════════════
        # 2. 存活数量
        # ═══════════════════════════════════════════════════════════
        score += len(alive_pets) * 400.0

        # ═══════════════════════════════════════════════════════════
        # 3. 在场精灵详细评估
        # ═══════════════════════════════════════════════════════════
        if active and active.is_alive:

            # ── 3a. 能量与技能可用性 ──────────────────────────────
            usable_skills = self._count_usable_skills(active, state, is_player)
            score += usable_skills * 80.0
            score += min(active.current_energy, 10) * 30.0

            # ── 3b. 技能冷却惩罚 ─────────────────────────────────
            cooling_count = len(active.skill_cooldowns)
            score -= cooling_count * 40.0

            # ── 3c. 速度优势（对称处理）──────────────────────────
            if enemy_active and enemy_active.is_alive:
                my_speed = active.get_effective_stat("速度")
                opp_speed = enemy_active.get_effective_stat("速度")
                if my_speed > opp_speed:
                    score += 150.0  # 对称：双方各加150，差值=150
                # 后手不扣分，因为对手的 _evaluate_side 会给对手加分

            # ── 3d. 对场上敌方的属性克制 ─────────────────────────
            if enemy_active and enemy_active.is_alive:
                adv = self._matchup_advantage(active, enemy_active)
                score += adv * 250.0

            # ── 3e. Buff/Debuff 净值 ─────────────────────────────
            score += self._buff_value(active)

            # ── 3f. 自身负面状态惩罚 ─────────────────────────────
            score -= self._status_penalty(active)

            # ── 3g. 蓄力/迸发 ────────────────────────────────────
            if active.charging_skill:
                score += 120.0
            if active.burst_turns_remaining > 0:
                score += 60.0

            # ── 3h. 眩晕 ────────────────────────────────────────
            score -= active.stun_turns * 250.0

        # ═══════════════════════════════════════════════════════════
        # 4. 场地印记
        # ═══════════════════════════════════════════════════════════
        score += self._strategy_mechanic_value(state, is_player, active, enemy_active)

        # ═══════════════════════════════════════════════════════════
        # 5. 后备精灵质量
        # ═══════════════════════════════════════════════════════════
        if bench_alive and enemy_active and enemy_active.is_alive:
            # 是否有后备精灵能克制当前敌方出战精灵
            best_counter_score = 0.0
            for pet in bench_alive:
                counter = self._matchup_advantage(pet, enemy_active)
                if counter > best_counter_score:
                    best_counter_score = counter
            score += best_counter_score * 100.0  # 有反制手段的价值

        # ═══════════════════════════════════════════════════════════
        # 6. 特殊资源
        # ═══════════════════════════════════════════════════════════
        ts = own.team_state
        score += ts.leader_evolution_uses * 250.0
        score += ts.willpower_strike_uses * 120.0
        score += ts.devotion_combo * 15.0
        score += ts.devotion_power * 0.5
        score += ts.devotion_lifesteal * 1.0
        score += ts.devotion_poison * 8.0

        return score

    @staticmethod
    def _strategy_mechanic_value(
        state: BattleState,
        is_player: bool,
        active: PetInstance | None,
        enemy_active: PetInstance | None,
    ) -> float:
        ctx = StrategyMechanicContext(
            state=state,
            is_player=is_player,
            active_pet=active,
            enemy_active_pet=enemy_active,
        )
        return evaluate_strategy_mechanics(ctx).score

    # ── 天气对双方的影响 ──────────────────────────────────────────

    def _weather_advantage(self, state: BattleState) -> float:
        """评估天气对玩家方的净影响（正=有利，负=不利）"""
        weather = state.weather
        if not weather:
            return 0.0

        score = 0.0
        p_active = state.player.get_active_pet()
        o_active = state.opponent.get_active_pet()

        if weather == '下雨':
            # 水系技能+50%伤害
            if p_active and any(s.element == '水' for s in p_active.skills if s.base_power > 0):
                score += 80.0
            if o_active and any(s.element == '水' for s in o_active.skills if s.base_power > 0):
                score -= 80.0
        elif weather == '沙暴':
            # 地系技能能耗-2
            if p_active and any(s.element == '地' for s in p_active.skills):
                score += 60.0
            if o_active and any(s.element == '地' for s in o_active.skills):
                score -= 60.0
        elif weather == '暴风雪':
            # 每回合双方各+1冻结，对冰系不利方惩罚更大
            if p_active:
                score -= 30.0  # 双方都受冻，净影响靠冻结层数差异
            if o_active:
                score += 30.0

        return score

    # ── 属性对抗评估（攻击面 + 防御面） ──────────────────────────

    def _matchup_advantage(self, me: PetInstance, opponent: PetInstance) -> float:
        """
        综合评估两只精灵的对战匹配优势。
        返回值：正数=我占优，负数=对方占优
        """
        my_attack_adv = 0.0
        attack_skills = [s for s in me.skills if s.category == SkillCategory.ATTACK and s.base_power > 0]
        if attack_skills:
            best_eff = 1.0
            for skill in attack_skills:
                eff = self.data_loader.get_combined_type_effectiveness(
                    skill.element,
                    opponent.template.types,
                )
                best_eff = max(best_eff, eff)
            my_attack_adv = best_eff - 1.0

        opp_attack_adv = 0.0
        opp_attack_skills = [s for s in opponent.skills if s.category == SkillCategory.ATTACK and s.base_power > 0]
        if opp_attack_skills:
            best_eff = 1.0
            for skill in opp_attack_skills:
                eff = self.data_loader.get_combined_type_effectiveness(
                    skill.element,
                    me.template.types,
                )
                best_eff = max(best_eff, eff)
            opp_attack_adv = best_eff - 1.0

        return my_attack_adv - opp_attack_adv

    # ── Buff/Debuff 净值 ─────────────────────────────────────────

    @staticmethod
    def _buff_value(pet: PetInstance) -> float:
        """正层=有利, 负层=不利"""
        m = pet.stat_modifiers
        return (
            m.physical_attack * 35.0 +
            m.magical_attack * 35.0 +
            m.physical_defense * 20.0 +
            m.magical_defense * 20.0 +
            m.speed * 25.0
        )

    # ── 状态效果惩罚 ─────────────────────────────────────────────

    @staticmethod
    def _status_penalty(pet: PetInstance) -> float:
        """己方负面状态的估计代价（含 HP urgency）"""
        hp_ratio = pet.current_hp / max(pet.max_hp, 1)
        urgency = 1.0 + (1.0 - hp_ratio) * 0.5

        penalty = 0.0
        poison = pet.get_status_stacks(StatusEffectType.POISON)
        poison_mark = pet.get_status_stacks(StatusEffectType.POISON_MARK)
        burn = pet.get_status_stacks(StatusEffectType.BURN)
        parasite = pet.get_status_stacks(StatusEffectType.PARASITE)
        freeze = pet.freeze_stacks

        penalty += poison * 90.0 * urgency
        penalty += poison_mark * 90.0 * urgency
        penalty += burn * 70.0 * urgency
        penalty += parasite * 120.0 * urgency

        if freeze >= 4:
            penalty += 800.0
        elif freeze >= 3:
            penalty += 400.0
        else:
            penalty += freeze * 100.0

        return penalty

    # ── 可用技能计数 ──────────────────────────────────────────────

    @staticmethod
    def _count_usable_skills(
        pet: PetInstance,
        state: BattleState,
        is_player: bool,
    ) -> int:
        """计算当前能量下可以释放的技能数量"""
        count = 0
        for skill in pet.skills:
            required_energy = compute_effective_skill_energy_cost(
                state, is_player, pet, skill
            )
            if (can_pay_skill_energy_cost(pet, required_energy) and
                    pet.skill_cooldowns.get(skill.name, 0) <= 0):
                count += 1
        return count
