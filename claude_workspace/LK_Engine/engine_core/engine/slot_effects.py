"""
技能槽位相关效果工具。

当前把 `pet.skills` 的顺序直接视作 1~4 号技能位。
"""
from __future__ import annotations

import random
import re

from core.models import BattleState, PetInstance, Skill


class SlotEffectsProcessor:
    """处理技能槽位、相邻技能与传动规则。"""

    @staticmethod
    def ensure_initial_skill_order(pet: PetInstance) -> None:
        if pet.get_runtime_flag("_initial_skill_order_names", None) is None:
            pet.set_runtime_flag("_initial_skill_order_names", [skill.name for skill in pet.skills])

    @staticmethod
    def restore_initial_skill_order(pet: PetInstance) -> None:
        """
        精灵重新入场时恢复初始配招槽位顺序。
        只重排已有技能对象，保留永久能耗/威力等运行时改动。
        """
        SlotEffectsProcessor.ensure_initial_skill_order(pet)
        initial_names = pet.get_runtime_flag("_initial_skill_order_names", []) or []
        if not initial_names or len(pet.skills) <= 1:
            return

        remaining = list(pet.skills)
        restored = []
        for name in initial_names:
            matched_index = next((idx for idx, skill in enumerate(remaining) if skill.name == name), None)
            if matched_index is None:
                continue
            restored.append(remaining.pop(matched_index))

        if remaining:
            restored.extend(remaining)

        if len(restored) == len(pet.skills):
            pet.skills = restored

    @staticmethod
    def prepare_state_for_turn(state: BattleState) -> BattleState:
        """确保每回合开始阶段的槽位处理只执行一次。"""
        if state.turn_prepared:
            return state
        for ps in (state.player, state.opponent):
            pet = ps.get_active_pet()
            if pet and pet.is_alive:
                SlotEffectsProcessor.ensure_initial_skill_order(pet)
                SlotEffectsProcessor.apply_turn_start_trait_effects(pet, state.turn)
                SlotEffectsProcessor.process_skill_transmission(pet)
                SlotEffectsProcessor.apply_position_change_trait_effects(pet)
        state.turn_prepared = True
        return state

    @staticmethod
    def has_trait(pet: PetInstance, trait_name: str) -> bool:
        return any(t.name == trait_name for t in getattr(pet.template, "traits", []))

    @staticmethod
    def adjust_energy_delta_for_traits(pet: PetInstance, delta: int) -> int:
        """根据特性修正能耗变化方向。负数表示减耗，正数表示增耗。"""
        if SlotEffectsProcessor.has_trait(pet, "对流"):
            return -delta
        return delta

    @staticmethod
    def apply_energy_cost_delta(pet: PetInstance, skill: Skill, delta: int) -> int:
        """将能耗变化应用到技能本体，并处理对流反转。"""
        actual_delta = SlotEffectsProcessor.adjust_energy_delta_for_traits(pet, delta)
        skill.energy_cost = max(0, skill.energy_cost + actual_delta)
        return skill.energy_cost

    @staticmethod
    def get_next_skill_energy_delta(pet: PetInstance) -> int:
        """返回下次技能的额外能耗修正。负数表示减耗，正数表示增耗。"""
        discount = getattr(pet, "next_skill_energy_discount", 0)
        if discount <= 0:
            return 0
        return SlotEffectsProcessor.adjust_energy_delta_for_traits(pet, -discount)

    @staticmethod
    def get_allowed_skill_slots(pet: PetInstance) -> set[int] | None:
        if SlotEffectsProcessor.has_trait(pet, "正位宝剑"):
            return {0}
        if SlotEffectsProcessor.has_trait(pet, "宝剑王牌"):
            return {0, 2}
        return None

    @staticmethod
    def get_skill_slot_index(pet: PetInstance, skill: Skill) -> int:
        for idx, current in enumerate(pet.skills):
            if current is skill:
                return idx
        for idx, current in enumerate(pet.skills):
            if current.name == skill.name:
                return idx
        return -1

    @staticmethod
    def get_adjacent_skill_indices(skill_count: int, slot_index: int) -> list[int]:
        if skill_count <= 1 or slot_index < 0 or slot_index >= skill_count:
            return []
        left = (slot_index - 1) % skill_count
        right = (slot_index + 1) % skill_count
        if left == right:
            return [left]
        return [left, right]

    @staticmethod
    def get_adjacent_skills(pet: PetInstance, skill: Skill) -> list[Skill]:
        slot_index = SlotEffectsProcessor.get_skill_slot_index(pet, skill)
        return [
            pet.skills[idx]
            for idx in SlotEffectsProcessor.get_adjacent_skill_indices(len(pet.skills), slot_index)
            if 0 <= idx < len(pet.skills)
        ]

    @staticmethod
    def swap_adjacent_skills(pet: PetInstance, skill: Skill) -> bool:
        """
        交换当前技能两侧槽位的技能位置。
        返回是否发生了交换。
        """
        slot_index = SlotEffectsProcessor.get_skill_slot_index(pet, skill)
        adjacent = SlotEffectsProcessor.get_adjacent_skill_indices(len(pet.skills), slot_index)
        if len(adjacent) < 2:
            return False
        left, right = adjacent[0], adjacent[1]
        if left == right or left < 0 or right < 0:
            return False
        pet.skills[left], pet.skills[right] = pet.skills[right], pet.skills[left]
        return True

    @staticmethod
    def adjust_adjacent_skill_power(pet: PetInstance, skill: Skill, delta: int) -> bool:
        """永久调整当前技能两侧技能的基础威力。"""
        changed = False
        for adjacent in SlotEffectsProcessor.get_adjacent_skills(pet, skill):
            adjacent.base_power = max(1, adjacent.base_power + delta)
            changed = True
        return changed

    @staticmethod
    def get_skill_energy_delta(pet: PetInstance, skill: Skill) -> int:
        """
        返回槽位/相邻技能带来的能耗修正。
        负数表示减耗，正数表示增耗。
        """
        desc = getattr(skill, "desc", "") or ""
        slot_index = SlotEffectsProcessor.get_skill_slot_index(pet, skill)
        delta = 0

        if "本技能被动额外-1能耗" in desc:
            delta -= 1

        if SlotEffectsProcessor.has_trait(pet, "盲拧") and slot_index == 3:
            delta -= 4

        if slot_index in (0, 2):
            match = re.search(r"本技能位于1号或3号位时能耗-(\d+)", desc)
            if match:
                delta -= int(match.group(1))

        if slot_index == 0:
            match = re.search(r"本技能位于1号位时能耗-(\d+)", desc)
            if match:
                delta -= int(match.group(1))
        elif slot_index == 2:
            match = re.search(r"本技能位于3号位时能耗-(\d+)", desc)
            if match:
                delta -= int(match.group(1))

        for adjacent in SlotEffectsProcessor.get_adjacent_skills(pet, skill):
            adjacent_desc = getattr(adjacent, "desc", "") or ""
            match = re.search(r"被动：两侧技能能耗-(\d+)", adjacent_desc)
            if match:
                delta -= int(match.group(1))

        return delta

    @staticmethod
    def get_effective_energy_cost(pet: PetInstance, skill: Skill) -> int:
        return max(
            0,
            skill.energy_cost
            + SlotEffectsProcessor.get_skill_energy_delta(pet, skill)
            + SlotEffectsProcessor.get_next_skill_energy_delta(pet)
        )

    @staticmethod
    def get_skill_power(power: int, pet: PetInstance, skill: Skill) -> int:
        """
        返回应用槽位规则后的技能威力。
        目前支持：
        - 1号位 / 3号位固定威力加成
        - 1号或3号位固定威力加成
        - 威力 = 两侧技能威力和的三分之一
        """
        desc = getattr(skill, "desc", "") or ""
        slot_index = SlotEffectsProcessor.get_skill_slot_index(pet, skill)
        modified_power = power

        if "技能威力为两侧技能威力和的三分之一" in desc:
            adjacent_power = sum(adj.base_power for adj in SlotEffectsProcessor.get_adjacent_skills(pet, skill))
            modified_power = max(1, adjacent_power // 3)

        trait_power_bonus = pet.get_runtime_flag("_slot_trait_power_bonus", {}) or {}
        modified_power += int(trait_power_bonus.get(skill.name, 0))

        if slot_index in (0, 2):
            match = re.search(r"本技能位于1号或3号位时(?:,)?威力\+(\d+)", desc)
            if match:
                modified_power += int(match.group(1))

        if slot_index == 0:
            match = re.search(r"本技能位于1号位时(?:,)?威力\+(\d+)", desc)
            if match:
                modified_power += int(match.group(1))
        elif slot_index == 2:
            match = re.search(r"本技能位于3号位时(?:,)?威力\+(\d+)", desc)
            if match:
                modified_power += int(match.group(1))

        return max(1, modified_power)

    @staticmethod
    def get_skill_hits_delta(pet: PetInstance, skill: Skill) -> int:
        """返回槽位规则带来的连击增量。"""
        desc = getattr(skill, "desc", "") or ""
        slot_index = SlotEffectsProcessor.get_skill_slot_index(pet, skill)
        delta = 0

        if slot_index in (0, 2):
            match = re.search(r"本技能位于1号或3号位时连击\+(\d+)", desc)
            if match:
                delta += int(match.group(1))

        if slot_index == 0:
            match = re.search(r"本技能位于1号位时连击\+(\d+)", desc)
            if match:
                delta += int(match.group(1))
        elif slot_index == 2:
            match = re.search(r"本技能位于3号位时连击\+(\d+)", desc)
            if match:
                delta += int(match.group(1))

        return delta

    @staticmethod
    def is_trait_slot_swift(pet: PetInstance, skill: Skill) -> bool:
        swift_skill = pet.get_runtime_flag("_slot_trait_swift_skill", None)
        return swift_skill == skill.name

    @staticmethod
    def apply_turn_start_trait_effects(pet: PetInstance, turn: int) -> None:
        previous_positions = {sk.name: idx for idx, sk in enumerate(pet.skills)}
        pet.set_runtime_flag("_previous_skill_positions", previous_positions)

        trait_power_bonus = {}
        if SlotEffectsProcessor.has_trait(pet, "向心力"):
            for idx in (0, 1):
                if idx < len(pet.skills):
                    trait_power_bonus[pet.skills[idx].name] = trait_power_bonus.get(pet.skills[idx].name, 0) + 30
        pet.set_runtime_flag("_slot_trait_power_bonus", trait_power_bonus)

        if SlotEffectsProcessor.has_trait(pet, "翼轴") and pet.skills:
            pet.set_runtime_flag("_slot_trait_swift_skill", pet.skills[0].name)
        else:
            pet.set_runtime_flag("_slot_trait_swift_skill", None)

        if SlotEffectsProcessor.has_trait(pet, "贪心算法") and pet.skills:
            pet.set_runtime_flag("_slot_trait_greedy_skill", pet.skills[0].name)
        else:
            pet.set_runtime_flag("_slot_trait_greedy_skill", None)

        if SlotEffectsProcessor.has_trait(pet, "盲拧") and len(pet.skills) > 1:
            rng = random.Random(f"{pet.template.name}:{turn}:blind_twist")
            rng.shuffle(pet.skills)

    @staticmethod
    def process_skill_transmission(pet: PetInstance):
        """
        回合开始时处理传动。
        规则：
        - 把 1~4 号技能位视作一个环。
        - 按当前 1→4 号位顺序依次扫描。
        - 某个技能若有剩余“传动X”，则先消耗 1 次，并尝试与下一位交换。
        - 若下一位也有剩余传动，则把它一并纳入，继续向后推进。
        - 若整圈都有传动，则执行整圈右移（1234 -> 4123）。

        传动次数按“当前技能”独立结算；未标注传动的技能不会参与。
        """
        skill_count = len(pet.skills)
        if skill_count <= 1:
            return

        effective_transmission = [0] * skill_count
        for idx, skill in enumerate(pet.skills):
            desc = getattr(skill, "desc", "") or ""
            match = re.search(r"传动(\d+)", desc)
            if match:
                effective_transmission[idx] += int(match.group(1))

        for idx, extra in getattr(pet, "skill_transmission", {}).items():
            if 0 <= idx < skill_count:
                effective_transmission[idx] += int(extra)

        if SlotEffectsProcessor.has_trait(pet, "向心力"):
            effective_transmission[0] += 1
            if skill_count > 1:
                effective_transmission[1] += 1
        if SlotEffectsProcessor.has_trait(pet, "翼轴"):
            effective_transmission[0] += 1
        if SlotEffectsProcessor.has_trait(pet, "贪心算法"):
            effective_transmission[0] += 1

        if not any(effective_transmission):
            return

        for start_pos in range(skill_count):
            if effective_transmission[start_pos] <= 0:
                continue

            effective_transmission[start_pos] -= 1
            chain = [start_pos]
            current = start_pos

            while True:
                nxt = (current + 1) % skill_count
                if nxt == start_pos:
                    break
                chain.append(nxt)
                if effective_transmission[nxt] > 0:
                    effective_transmission[nxt] -= 1
                    current = nxt
                    continue
                break

            if len(chain) > 1:
                moved_skill = pet.skills[chain[-1]]
                moved_transmission = effective_transmission[chain[-1]]
                for i in range(len(chain) - 1, 0, -1):
                    pet.skills[chain[i]] = pet.skills[chain[i - 1]]
                    effective_transmission[chain[i]] = effective_transmission[chain[i - 1]]
                pet.skills[chain[0]] = moved_skill
                effective_transmission[chain[0]] = moved_transmission

    @staticmethod
    def apply_position_change_trait_effects(pet: PetInstance) -> None:
        if not SlotEffectsProcessor.has_trait(pet, "机械变式"):
            return
        previous_positions = pet.get_runtime_flag("_previous_skill_positions", {}) or {}
        if not previous_positions:
            return
        for idx, skill in enumerate(pet.skills):
            prev_idx = previous_positions.get(skill.name)
            if prev_idx is not None and prev_idx != idx:
                SlotEffectsProcessor.apply_energy_cost_delta(pet, skill, -1)
