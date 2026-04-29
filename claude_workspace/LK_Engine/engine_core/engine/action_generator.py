"""
行动生成器
生成给定状态下所有合法的行动
"""
from typing import List
from core.models import BattleState, Action, ActionType, PlayerState
from engine.slot_effects import SlotEffectsProcessor
from engine.energy_costs import compute_effective_skill_energy_cost, can_pay_skill_energy_cost


def _is_skill_available(active_pet, skill) -> bool:
    return active_pet.skill_cooldowns.get(skill.name, 0) <= 0


class ActionGenerator:
    """行动生成器"""

    @staticmethod
    def _build_non_switch_actions(
        state: BattleState,
        player_state: PlayerState,
        active_pet,
        is_player: bool,
        send_out_index=None,
    ) -> List[Action]:
        actions = []
        if not active_pet or not active_pet.is_alive:
            return actions

        if active_pet.stun_turns > 0:
            actions.append(Action(type=ActionType.GATHER_ENERGY, send_out_index=send_out_index))
            return actions

        if active_pet.charging_skill:
            for skill in active_pet.skills:
                if skill.name == active_pet.charging_skill:
                    actions.append(Action(
                        type=ActionType.USE_SKILL,
                        skill=skill,
                        send_out_index=send_out_index,
                    ))
                    break
            return actions

        for skill in active_pet.skills:
            allowed_slots = SlotEffectsProcessor.get_allowed_skill_slots(active_pet)
            if allowed_slots is not None:
                slot_index = SlotEffectsProcessor.get_skill_slot_index(active_pet, skill)
                if slot_index not in allowed_slots:
                    continue
            required_energy = compute_effective_skill_energy_cost(
                state, is_player, active_pet, skill
            )
            if (can_pay_skill_energy_cost(active_pet, required_energy) and
                    _is_skill_available(active_pet, skill)):
                actions.append(Action(
                    type=ActionType.USE_SKILL,
                    skill=skill,
                    send_out_index=send_out_index,
                ))

        if ActionGenerator._can_use_willpower_strike(player_state, active_pet):
            for skill in active_pet.skills:
                allowed_slots = SlotEffectsProcessor.get_allowed_skill_slots(active_pet)
                if allowed_slots is not None:
                    slot_index = SlotEffectsProcessor.get_skill_slot_index(active_pet, skill)
                    if slot_index not in allowed_slots:
                        continue
                required_energy = compute_effective_skill_energy_cost(
                    state, is_player, active_pet, skill
                )
                if (can_pay_skill_energy_cost(active_pet, required_energy) and
                        _is_skill_available(active_pet, skill) and
                        skill.base_power > 0):
                    actions.append(Action(
                        type=ActionType.WILLPOWER_STRIKE,
                        skill=skill,
                        send_out_index=send_out_index,
                    ))

        if ActionGenerator._can_use_leader_evolution(player_state, active_pet):
            actions.append(Action(type=ActionType.LEADER_EVOLUTION, send_out_index=send_out_index))

        actions.append(Action(type=ActionType.GATHER_ENERGY, send_out_index=send_out_index))
        return actions

    @staticmethod
    def _can_use_leader_evolution(player_state: PlayerState, active_pet) -> bool:
        """首领化合法性：次数>0 且 当前精灵是首领血脉 且 未选择愿力冲击"""
        if player_state.team_state.leader_evolution_uses <= 0 or not active_pet:
            return False
        bloodline = getattr(active_pet.template, "bloodline", "unknown")
        return bloodline == "leader"

    @staticmethod
    def _can_use_willpower_strike(player_state: PlayerState, active_pet) -> bool:
        """愿力冲击合法性：次数>0 且 当前精灵不是首领血脉 且 未选择首领化"""
        if player_state.team_state.willpower_strike_uses <= 0 or not active_pet:
            return False
        bloodline = getattr(active_pet.template, "bloodline", "unknown")
        return bloodline != "leader"

    @staticmethod
    def generate_actions(state: BattleState, is_player: bool) -> List[Action]:
        """
        生成所有合法行动

        Args:
            state: 当前对战状态
            is_player: True表示生成玩家行动，False表示生成对手行动

        Returns:
            所有合法行动的列表
        """
        SlotEffectsProcessor.prepare_state_for_turn(state)
        player_state = state.player if is_player else state.opponent
        actions = []

        active_pet = player_state.get_active_pet()
        if active_pet and active_pet.is_alive:
            actions.extend(ActionGenerator._build_non_switch_actions(
                state, player_state, active_pet, is_player
            ))

        # 当前在场精灵已死亡时，补位不是一个“耗回合的换宠动作”，
        # 而是进入本回合行动前的强制补位阶段；补位后的精灵仍可正常出招。
        if active_pet and not active_pet.is_alive:
            alive_pets = player_state.get_alive_pets()
            for idx, pet in alive_pets:
                if idx != player_state.active_index:
                    actions.extend(ActionGenerator._build_non_switch_actions(
                        state,
                        player_state,
                        pet,
                        is_player,
                        send_out_index=idx,
                    ))
            return actions

        # ── 5. 换精灵行动 ─────────────────────────────────────────
        # 蓄力中不能换精灵（除非有折返/离场效果）
        if active_pet and not active_pet.charging_skill:
            alive_pets = player_state.get_alive_pets()
            for idx, pet in alive_pets:
                if idx != player_state.active_index:
                    actions.append(Action(
                        type=ActionType.SWITCH_PET,
                        target_index=idx
                    ))

        return actions
