"""
测试槽位相关特性：
- 宝剑王牌 / 正位宝剑 行动限制
- 向心力 / 翼轴 / 贪心算法
- 盲拧 / 机械变式
"""
from core.models import (
    Action,
    ActionType,
    BattleState,
    DamageType,
    PetInstance,
    PetTemplate,
    PlayerState,
    Skill,
    SkillCategory,
    Trait,
)
from core.status_effects import StatusEffectType
from data_loader import DataLoader
from engine.action_generator import ActionGenerator
from engine.extended_battle_engine import ExtendedBattleEngine


def make_template(name: str, trait_names: list[str]) -> PetTemplate:
    return PetTemplate(
        id=1,
        name=name,
        types=["机械"],
        stats={"生命": 200, "物攻": 120, "魔攻": 120, "物防": 90, "魔防": 90, "速度": 100},
        traits=[Trait(name=t, desc=t) for t in trait_names],
        learnable_skills=[],
    )


def make_skill(name: str, power: int = 60, energy: int = 3, desc: str = "", category: SkillCategory = SkillCategory.ATTACK) -> Skill:
    return Skill(
        name=name,
        element="机械",
        category=category,
        damage_type=DamageType.PHYSICAL if category == SkillCategory.ATTACK else None,
        base_power=power,
        energy_cost=energy,
        desc=desc,
    )


def make_pet(name: str, trait_names: list[str], skills: list[Skill], energy: int = 10) -> PetInstance:
    template = make_template(name, trait_names)
    return PetInstance(
        template=template,
        current_hp=200,
        max_hp=200,
        stats=template.stats.copy(),
        skills=skills,
        current_energy=energy,
    )


loader = DataLoader()
engine = ExtendedBattleEngine(loader)
generator = ActionGenerator()

print("=== 槽位特性测试 ===\n")

print("1. 宝剑王牌：仅可使用1号和3号位技能")
skills1 = [make_skill("1号"), make_skill("2号"), make_skill("3号"), make_skill("4号")]
pet1 = make_pet("剑王牌", ["宝剑王牌"], skills1)
state1 = BattleState(
    player=PlayerState(team=[pet1], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [], [make_skill("挨打")])], active_index=0),
)
actions1 = generator.generate_actions(state1, True)
usable1 = [a.skill.name for a in actions1 if a.type == ActionType.USE_SKILL]
assert usable1 == ["1号", "3号"], usable1
print("   [PASS] 宝剑王牌行动限制正确\n")

print("2. 正位宝剑：仅可使用1号位技能")
skills2 = [make_skill("1号"), make_skill("2号"), make_skill("3号")]
pet2 = make_pet("正位剑", ["正位宝剑"], skills2)
state2 = BattleState(
    player=PlayerState(team=[pet2], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [], [make_skill("挨打")])], active_index=0),
)
actions2 = generator.generate_actions(state2, True)
usable2 = [a.skill.name for a in actions2 if a.type == ActionType.USE_SKILL]
assert usable2 == ["1号"], usable2
print("   [PASS] 正位宝剑行动限制正确\n")

print("3. 向心力：1号/2号位获得威力+30且有传动")
skills3 = [make_skill("A"), make_skill("B"), make_skill("C"), make_skill("D")]
pet3 = make_pet("向心宠", ["向心力"], skills3)
state3 = BattleState(
    player=PlayerState(team=[pet3], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [], [make_skill("挨打")])], active_index=0),
)
base_pet3 = make_pet("普通宠", [], [make_skill("A"), make_skill("B"), make_skill("C"), make_skill("D")])
base_state3 = BattleState(
    player=PlayerState(team=[base_pet3], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [], [make_skill("挨打")])], active_index=0),
)
result3 = engine.apply_action(state3, Action(type=ActionType.USE_SKILL, skill=skills3[0]), Action(type=ActionType.GATHER_ENERGY))
result3b = engine.apply_action(base_state3, Action(type=ActionType.USE_SKILL, skill=base_pet3.skills[0]), Action(type=ActionType.GATHER_ENERGY))
damage3 = 200 - result3.opponent.get_active_pet().current_hp
damage3b = 200 - result3b.opponent.get_active_pet().current_hp
order3 = [sk.name for sk in result3.player.get_active_pet().skills]
assert damage3 > damage3b, (damage3, damage3b)
assert order3 != ["A", "B", "C", "D"], order3
print("   [PASS] 向心力已提供槽位增威和传动\n")

print("4. 翼轴：1号位技能获得迅捷和传动1")
swift_skill = make_skill("翼轴技")
pet4 = make_pet("翼轴宠", ["翼轴"], [swift_skill, make_skill("B"), make_skill("C")])
opp4 = make_pet("对手", [], [make_skill("攻击")])
opp4.stats["速度"] = 200
state4 = BattleState(
    player=PlayerState(team=[pet4], active_index=0),
    opponent=PlayerState(team=[opp4], active_index=0),
)
result4 = engine.apply_action(
    state4,
    Action(type=ActionType.USE_SKILL, skill=swift_skill),
    Action(type=ActionType.USE_SKILL, skill=opp4.skills[0]),
)
assert result4.opponent.get_active_pet().current_hp < 200
assert [sk.name for sk in result4.player.get_active_pet().skills] != ["翼轴技", "B", "C"]
print("   [PASS] 翼轴已提供先手与传动\n")

print("5. 贪心算法：1号位技能使用后灼烧敌方")
burn_skill = make_skill("贪心技")
pet5 = make_pet("贪心宠", ["贪心算法"], [burn_skill, make_skill("B")])
opp5 = make_pet("对手", [], [make_skill("挨打")])
state5 = BattleState(
    player=PlayerState(team=[pet5], active_index=0),
    opponent=PlayerState(team=[opp5], active_index=0),
)
result5 = engine.apply_action(
    state5,
    Action(type=ActionType.USE_SKILL, skill=burn_skill),
    Action(type=ActionType.GATHER_ENERGY),
)
assert result5.opponent.get_active_pet().get_status_stacks(StatusEffectType.BURN) == 3
print("   [PASS] 贪心算法已在1号位技能后附加灼烧\n")

print("6. 盲拧：回合开始打乱技能顺序，4号位技能能耗-4")
skills6 = [make_skill("A", energy=3), make_skill("B", energy=3), make_skill("C", energy=3), make_skill("D", energy=5)]
pet6 = make_pet("盲拧宠", ["盲拧"], skills6, energy=1)
state6 = BattleState(
    player=PlayerState(team=[pet6], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [], [make_skill("挨打")])], active_index=0),
)
actions6 = generator.generate_actions(state6, True)
order6 = [sk.name for sk in state6.player.get_active_pet().skills]
assert order6 != ["A", "B", "C", "D"], order6
usable6 = [a.skill.name for a in actions6 if a.type == ActionType.USE_SKILL]
assert usable6, usable6
print("   [PASS] 盲拧已确定性打乱顺序并允许4号位减耗技能进入可用集\n")

print("7. 机械变式：位置变化的技能能耗-1")
skills7 = [make_skill("A", energy=4), make_skill("B", energy=4), make_skill("C", energy=4), make_skill("D", energy=4)]
pet7 = make_pet("机械变式宠", ["盲拧", "机械变式"], skills7)
state7 = BattleState(
    player=PlayerState(team=[pet7], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [], [make_skill("挨打")])], active_index=0),
)
generator.generate_actions(state7, True)
energies7 = [sk.energy_cost for sk in state7.player.get_active_pet().skills]
assert any(cost == 3 for cost in energies7), energies7
print("   [PASS] 机械变式已对位置变化技能应用减耗\n")

print("=" * 50)
print("所有槽位特性测试通过！")
print("=" * 50)
