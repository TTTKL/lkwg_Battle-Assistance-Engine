"""
印记效果处理器
根据 wiki.lcx.cab/lk/terms.php 的权威数据实现

印记规则（已验证）：
- 攻击印记：每层使攻击技能威力+10（加法，非乘法）
- 风起印记：先手攻击时每层伤害+20%，仅生效1回合
- 龙噬印记：释放5能耗（非3能耗）技能时提升40%攻击，仅生效1回合
- 湿润印记：每层所有技能能耗-1
- 蓄势印记：旧数据，wiki无记载，暂保留原实现
- 迟缓印记：后手攻击时每层伤害+30%
- 星陨印记：每层30威力魔法伤害（在 status_processor.py 中处理）
"""
from typing import Tuple
from core.models import Skill, PetInstance, BattleState, SkillCategory
from core.status_effects import StatusEffectType


class MarkEffectsProcessor:
    """印记效果处理器"""

    @staticmethod
    def apply_mark_effects_to_skill(
        skill: Skill,
        attacker: PetInstance,
        is_player: bool,
        is_first_strike: bool,
        state: BattleState
    ) -> Tuple[int, int]:
        """
        应用印记效果到技能，返回 (修改后威力, 修改后能耗)
        is_first_strike: True=本回合先手出手
        """
        modified_power = skill.base_power
        modified_energy = skill.energy_cost
        trigger_energy_cost = getattr(skill, 'effective_energy_cost', skill.energy_cost)
        is_attack = skill.category == SkillCategory.ATTACK and skill.base_power > 0

        pos_mark, _ = state.get_marks(is_player)
        if pos_mark is None and modified_energy == skill.energy_cost:
            # 无正面印记时只处理蓄力
            if attacker.charging_skill == skill.name:
                modified_power = int(modified_power * 2)
            return modified_power, modified_energy

        if pos_mark:
            key = pos_mark.type_key
            stacks = pos_mark.stacks

            # 蓄电印记：入场首回合技能威力+10
            if key == StatusEffectType.CHARGE_MARK.value:
                if is_attack and attacker.burst_turns_remaining > 0:
                    modified_power += 10

            # 蓄势印记：全攻击技能威力+30%，能耗+1（旧数据，wiki无记载，保留）
            elif key == StatusEffectType.MOMENTUM_MARK.value:
                if is_attack:
                    modified_power = int(modified_power * 1.3)
                    modified_energy += 1

            # 攻击印记：每层使攻击技能威力+10（加法，wiki确认）
            elif key == StatusEffectType.ATTACK_MARK.value:
                if is_attack:
                    modified_power += 10 * stacks

            # 风起印记：先手攻击时每层伤害+20%，仅1回合（wiki确认）
            elif key == StatusEffectType.WIND_MARK.value:
                if is_attack and is_first_strike:
                    modified_power = int(modified_power * (1 + 0.2 * stacks))

            # 湿润印记：每层所有技能能耗-1（wiki确认）
            elif key == StatusEffectType.MOIST_MARK.value:
                modified_energy = max(0, modified_energy - stacks)

            # 迟缓印记：后手攻击时每层伤害+30%（wiki新增）
            elif key == StatusEffectType.SLOW_MARK.value:
                if is_attack and not is_first_strike:
                    modified_power = int(modified_power * (1 + 0.3 * stacks))

            # 龙噬印记：释放5能耗技能时提升40%攻击威力，仅1回合（wiki: 5能耗，非3能耗）
            elif key == StatusEffectType.DRAGON_BITE_MARK.value:
                if is_attack and trigger_energy_cost == 5:
                    modified_power = int(modified_power * 1.4)

        # 蓄力状态：威力翻倍（覆盖以上所有修改后的结果）
        if attacker.charging_skill == skill.name:
            modified_power = int(modified_power * 2)

        return modified_power, modified_energy

    @staticmethod
    def check_dragon_bite_trigger(
        skill: Skill,
        attacker: PetInstance,
        is_player: bool,
        state: BattleState
    ):
        """
        龙噬印记：释放5能耗（wiki: 5能耗，非3能耗）技能时提升40%攻击，仅生效1回合。
        实现：给攻击者标记一个临时攻击加成，由 _execute_skill 在伤害计算前应用，
        回合结束时自动清零（存入 dragon_bite_bonus 临时字段）。
        简化实现：直接提升本次技能威力不触发 stat_modifiers，避免永久 buff 问题。
        注意：此方法已调整为仅标记标志位，实际威力提升在 apply_mark_effects_to_skill 中处理。
        """
        pos_mark, _ = state.get_marks(is_player)
        if pos_mark and pos_mark.type_key == StatusEffectType.DRAGON_BITE_MARK.value:
            trigger_energy_cost = getattr(skill, 'effective_energy_cost', skill.energy_cost)
            if trigger_energy_cost == 5:
                # 记录本回合龙噬触发（仅1回合效果，不修改 stat_modifiers）
                attacker.dragon_bite_active = True

    @staticmethod
    def apply_dragon_bite_to_power(power: int, attacker: PetInstance) -> int:
        """应用龙噬印记的40%攻击提升到威力"""
        if getattr(attacker, 'dragon_bite_active', False):
            return int(power * 1.4)
        return power
