"""
测试印记效果
验证各种印记对技能威力和能耗的影响
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType, FieldMark
)
from core.status_effects import StatusEffectType
from engine.extended_battle_engine import ExtendedBattleEngine
from engine.mark_effects import MarkEffectsProcessor
from data_loader import DataLoader


def create_test_pet(name: str) -> PetInstance:
    """创建测试用精灵"""
    template = PetTemplate(
        id=1,
        name=name,
        types=["火"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        traits=[],
        learnable_skills=[]
    )

    skill = Skill(
        name="火焰喷射",
        element="火",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL,
        base_power=50,
        energy_cost=5
    )

    return PetInstance(
        template=template,
        current_hp=100,
        max_hp=100,
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        skills=[skill],
        current_energy=10
    )


def make_state(is_player_mark: bool, mark: FieldMark) -> BattleState:
    """创建带有印记的战斗状态"""
    pet = create_test_pet("测试")
    state = BattleState(
        player=PlayerState(team=[pet], active_index=0),
        opponent=PlayerState(team=[create_test_pet("对手")], active_index=0),
    )
    state.set_mark(is_player_mark, mark)
    return state


print("=== 印记效果测试 ===\n")

pet = create_test_pet("火神")
skill = pet.skills[0]

# 测试1：攻击印记（每层威力+10，加法，wiki已确认）
print("1. 攻击印记（每层威力+10，加法）")
state = make_state(True, FieldMark(type_key=StatusEffectType.ATTACK_MARK.value, stacks=1, is_positive=True))
modified_power, modified_energy = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill, pet, True, False, state
)
assert modified_power == 60, f"威力应为60（50+10），实际为{modified_power}"
assert modified_energy == 5, f"能耗应为5，实际为{modified_energy}"
print(f"   原始威力: 50 -> 修改后: {modified_power}（+10加法，wiki确认）")
print("   [PASS]\n")

# 测试2：蓄势印记（威力+30%，能耗+1）
print("2. 蓄势印记（威力+30%，能耗+1）")
state = make_state(True, FieldMark(type_key=StatusEffectType.MOMENTUM_MARK.value, stacks=1, is_positive=True))
modified_power, modified_energy = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill, pet, True, False, state
)
assert modified_power == 65, f"威力应为65（50*1.3），实际为{modified_power}"
assert modified_energy == 6, f"能耗应为6（5+1），实际为{modified_energy}"
print(f"   原始威力: 50 -> 修改后: {modified_power}")
print(f"   原始能耗: 5 -> 修改后: {modified_energy}")
print("   [PASS]\n")

# 测试3：湿润印记（能耗-1）
print("3. 湿润印记（能耗-1）")
state = make_state(True, FieldMark(type_key=StatusEffectType.MOIST_MARK.value, stacks=1, is_positive=True))
modified_power, modified_energy = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill, pet, True, False, state
)
assert modified_power == 50, f"威力应为50，实际为{modified_power}"
assert modified_energy == 4, f"能耗应为4（5-1），实际为{modified_energy}"
print(f"   原始能耗: 5 -> 修改后: {modified_energy}")
print("   [PASS]\n")

# 测试4：风起印记（先手时威力+20%）
print("4. 风起印记（先手时威力+20%）")
state = make_state(True, FieldMark(type_key=StatusEffectType.WIND_MARK.value, stacks=1, is_positive=True))
modified_power_first, _ = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill, pet, True, True, state
)
modified_power_second, _ = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill, pet, True, False, state
)
assert modified_power_first == 60, f"先手时威力应为60（50*1.2），实际为{modified_power_first}"
assert modified_power_second == 50, f"后手时威力应为50，实际为{modified_power_second}"
print(f"   先手时: 50 -> {modified_power_first}")
print(f"   后手时: 50 -> {modified_power_second}")
print("   [PASS]\n")

# 测试5：蓄电印记（迸发时威力+10）
print("5. 蓄电印记（迸发时威力+10）")
state = make_state(True, FieldMark(type_key=StatusEffectType.CHARGE_MARK.value, stacks=1, is_positive=True))
pet2 = create_test_pet("火神2")
pet2.burst_turns_remaining = 1  # 设置迸发状态
modified_power, _ = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill, pet2, True, False, state
)
assert modified_power == 60, f"迸发时威力应为60（50+10），实际为{modified_power}"
print(f"   迸发时: 50 -> {modified_power}")
print("   [PASS]\n")

# 测试6：龙噬印记（wiki: 释放5能耗技能时提升40%攻击威力，仅1回合）
print("6. 龙噬印记（释放5能耗技能时威力+40%，wiki确认能耗为5非3）")
state = make_state(True, FieldMark(type_key=StatusEffectType.DRAGON_BITE_MARK.value, stacks=1, is_positive=True))
pet3 = create_test_pet("火神3")
# 5能耗技能 → 应触发龙噬
skill_5_energy = Skill(
    name="强力攻击",
    element="火",
    category=SkillCategory.ATTACK,
    damage_type=DamageType.PHYSICAL,
    base_power=50,
    energy_cost=5
)
modified_power_5, _ = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill_5_energy, pet3, True, False, state
)
assert modified_power_5 == int(50 * 1.4), f"5能耗技能威力应为{int(50*1.4)}（50*1.4），实际为{modified_power_5}"
# 3能耗技能 → 不应触发龙噬
skill_3_energy = Skill(
    name="快速攻击",
    element="火",
    category=SkillCategory.ATTACK,
    damage_type=DamageType.PHYSICAL,
    base_power=50,
    energy_cost=3
)
modified_power_3, _ = MarkEffectsProcessor.apply_mark_effects_to_skill(
    skill_3_energy, pet3, True, False, state
)
assert modified_power_3 == 50, f"3能耗技能威力不应变化，实际为{modified_power_3}"
print(f"   5能耗技能: 50 -> {modified_power_5}（+40%，触发）")
print(f"   3能耗技能: 50 -> {modified_power_3}（不触发）")
print("   [PASS]\n")

print("=" * 50)
print("所有印记效果测试通过！")
print("=" * 50)
