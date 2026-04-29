"""
战斗引擎
处理伤害计算、先手判定、效果触发等战斗逻辑
"""
from typing import Tuple, Optional
import random
from core.models import (
    BattleState, Action, ActionType, PetInstance, Skill,
    DamageType, EffectType, StatModifier
)
from data_loader import DataLoader


class BattleEngine:
    """战斗引擎"""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def apply_action(self, state: BattleState, player_action: Action,
                     opponent_action: Action) -> BattleState:
        """
        应用双方行动，返回新状态
        """
        new_state = state.copy()

        # 处理换精灵（换精灵优先于使用技能）
        if player_action.type == ActionType.SWITCH_PET:
            self._switch_pet(new_state.player, player_action.target_index)
        if opponent_action.type == ActionType.SWITCH_PET:
            self._switch_pet(new_state.opponent, opponent_action.target_index)

        # 处理聚能
        if player_action.type == ActionType.GATHER_ENERGY:
            self._gather_energy(new_state.player)
        if opponent_action.type == ActionType.GATHER_ENERGY:
            self._gather_energy(new_state.opponent)

        # 如果双方都是使用技能，判定先手
        if (player_action.type == ActionType.USE_SKILL and
            opponent_action.type == ActionType.USE_SKILL):
            first, second = self._determine_order(
                new_state.player.get_active_pet(),
                new_state.opponent.get_active_pet(),
                player_action.skill,
                opponent_action.skill
            )

            if first == "player":
                self._execute_skill(new_state, True, player_action.skill)
                if not new_state.is_terminal():
                    self._execute_skill(new_state, False, opponent_action.skill)
            else:
                self._execute_skill(new_state, False, opponent_action.skill)
                if not new_state.is_terminal():
                    self._execute_skill(new_state, True, player_action.skill)
        else:
            # 只有一方使用技能
            if player_action.type == ActionType.USE_SKILL:
                self._execute_skill(new_state, True, player_action.skill)
            if opponent_action.type == ActionType.USE_SKILL:
                self._execute_skill(new_state, False, opponent_action.skill)

        # 回合结束处理
        new_state.turn += 1
        self._end_turn_cleanup(new_state)

        return new_state

    def _gather_energy(self, player_state):
        """聚能：恢复3点能量"""
        pet = player_state.get_active_pet()
        if pet and pet.is_alive:
            pet.current_energy = min(10, pet.current_energy + 3)

    def _switch_pet(self, player_state, target_index: int):
        """换精灵"""
        if 0 <= target_index < len(player_state.team):
            if player_state.team[target_index].is_alive:
                # 清除当前精灵的buff
                current = player_state.get_active_pet()
                if current:
                    current.stat_modifiers = StatModifier()

                player_state.active_index = target_index

    def _determine_order(self, player_pet: PetInstance, opponent_pet: PetInstance,
                        player_skill: Skill, opponent_skill: Skill) -> Tuple[str, str]:
        """
        判定先手顺序
        返回 ("player", "opponent") 或 ("opponent", "player")
        """
        # 1. 先手等级高的先行动
        if player_skill.priority > opponent_skill.priority:
            return ("player", "opponent")
        elif opponent_skill.priority > player_skill.priority:
            return ("opponent", "player")

        # 2. 先手等级相同：速度快的先行动
        player_speed = player_pet.get_effective_stat("速度")
        opponent_speed = opponent_pet.get_effective_stat("速度")

        if player_speed > opponent_speed:
            return ("player", "opponent")
        elif opponent_speed > player_speed:
            return ("opponent", "player")

        # 3. 速度一致：随机先手
        return ("player", "opponent") if random.random() < 0.5 else ("opponent", "player")

    def _execute_skill(self, state: BattleState, is_player: bool, skill: Skill):
        """执行技能"""
        attacker_state = state.player if is_player else state.opponent
        defender_state = state.opponent if is_player else state.player

        attacker = attacker_state.get_active_pet()
        defender = defender_state.get_active_pet()

        if not attacker or not defender:
            return

        # 扣除能量
        attacker.current_energy = max(0, attacker.current_energy - skill.energy_cost)

        # 设置技能冷却
        if skill.cooldown > 0:
            attacker.skill_cooldowns[skill.name] = skill.cooldown

        # 如果是攻击技能，计算伤害
        if skill.base_power > 0 and skill.damage_type:
            damage = self._calculate_damage(attacker, defender, skill, state)
            defender.current_hp = max(0, defender.current_hp - damage)

            if defender.current_hp == 0:
                defender.is_alive = False

        # 应用技能效果
        self._apply_skill_effects(attacker, defender, skill)

    def _calculate_damage(self, attacker: PetInstance, defender: PetInstance,
                         skill: Skill, state: BattleState) -> int:
        """
        计算伤害
        公式：进攻方攻击 / 防御方防御 × 0.9 × 技能威力 × 本系加成 × 克制关系
        """
        # 获取攻击和防御属性
        if skill.damage_type == DamageType.PHYSICAL:
            attack = attacker.get_effective_stat("物攻")
            defense = defender.get_effective_stat("物防")
        else:
            attack = attacker.get_effective_stat("魔攻")
            defense = defender.get_effective_stat("魔防")

        # 基础伤害
        base_damage = (attack / defense) * 0.9 * skill.base_power

        # 本系加成（技能属性与精灵属性相同时×1.5）
        stab = 1.5 if skill.element in attacker.template.types else 1.0

        # 属性克制
        type_effectiveness = self.data_loader.get_combined_type_effectiveness(
            skill.element,
            defender.template.types,
        )

        # 最终伤害
        total_damage = base_damage * stab * type_effectiveness

        return int(total_damage)

    def _apply_skill_effects(self, attacker: PetInstance, defender: PetInstance, skill: Skill):
        """应用技能效果"""
        for effect in skill.effects:
            if effect.type == EffectType.ENERGY_RESTORE:
                if effect.target == "self":
                    attacker.current_energy = min(10, attacker.current_energy + int(effect.value))
                else:
                    defender.current_energy = min(10, defender.current_energy + int(effect.value))

            elif effect.type == EffectType.STAT_BUFF:
                # 增加属性buff（每层10%）
                target = attacker if effect.target == "self" else defender
                layers = int(effect.value / 10)  # 假设value是百分比
                # 这里简化处理，实际需要根据具体属性名称
                target.stat_modifiers.physical_attack += layers

            elif effect.type == EffectType.STAT_DEBUFF:
                # 降低属性
                target = attacker if effect.target == "self" else defender
                layers = int(effect.value / 10)
                target.stat_modifiers.physical_defense -= layers

    def _end_turn_cleanup(self, state: BattleState):
        """回合结束清理"""
        # 减少技能冷却
        for player_state in [state.player, state.opponent]:
            pet = player_state.get_active_pet()
            if pet:
                for skill_name in list(pet.skill_cooldowns.keys()):
                    pet.skill_cooldowns[skill_name] -= 1
                    if pet.skill_cooldowns[skill_name] <= 0:
                        del pet.skill_cooldowns[skill_name]
