"""
测试技能槽位相关效果：
- 传动
- 两侧技能能耗-1
- 应对成功后两侧技能能耗永久-1
- 槽位威力加成
- 两侧技能威力和的三分之一
- 槽位连击加成
- 交换两侧技能位置
- 槽位条件 buff
- 两侧技能威力永久增加
"""
from core.models import (
    Action,
    ActionType,
    BattleState,
    DamageType,
    Effect,
    EffectType,
    PetInstance,
    PetTemplate,
    PlayerState,
    Skill,
    SkillCategory,
)
from data_loader import DataLoader
from engine.action_generator import ActionGenerator
from engine.extended_battle_engine import ExtendedBattleEngine


def make_template(name: str) -> PetTemplate:
    return PetTemplate(
        id=1,
        name=name,
        types=["机械"],
        stats={"生命": 200, "物攻": 120, "魔攻": 120, "物防": 90, "魔防": 90, "速度": 100},
        traits=[],
        learnable_skills=[],
    )


def make_skill(name: str, energy: int = 3, desc: str = "", category: SkillCategory = SkillCategory.ATTACK) -> Skill:
    return Skill(
        name=name,
        element="机械",
        category=category,
        damage_type=DamageType.PHYSICAL if category == SkillCategory.ATTACK else None,
        base_power=60 if category == SkillCategory.ATTACK else 0,
        energy_cost=energy,
        desc=desc,
    )


def make_pet(name: str, skills: list[Skill], energy: int = 10) -> PetInstance:
    template = make_template(name)
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


print("=== 槽位效果测试 ===\n")

print("1. 传动：回合开始时重排技能槽位")
transmit_skill = make_skill("传动技", desc="造成物伤，传动1。")
skill_b = make_skill("技能B")
skill_c = make_skill("技能C")
skill_d = make_skill("技能D")
pet = make_pet("传动宠", [transmit_skill, skill_b, skill_c, skill_d])
state = BattleState(
    player=PlayerState(team=[pet], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [make_skill("挨打")])], active_index=0),
)
generator.generate_actions(state, True)
names_after = [sk.name for sk in state.player.get_active_pet().skills]
assert names_after == ["技能B", "传动技", "技能C", "技能D"], names_after
print("   [PASS] 传动后 1号位与右侧槽位完成交换\n")

print("1.1 传动按技能逐个结算：圣剑-X 序列")
gear_a = make_skill("齿轮扭矩", desc="造成物伤，每回合位置发生变化时，本技能威力永久+20。")
gear_b = make_skill("轴承支撑", energy=3, desc="主动：本技能被动额外-1能耗，被动：两侧技能能耗-1，传动1。", category=SkillCategory.STATUS)
gear_c = make_skill("鸣沙陷阱", energy=4, desc="造成物伤，物防比敌方越高，本次技能威力越高。")
gear_d = make_skill("齿轮切开", energy=5, desc="造成物伤，本技能位于1号或3号位时能耗-2，传动1。")
pet_seq = make_pet("圣剑X测试", [gear_a, gear_b, gear_c, gear_d])
state_seq = BattleState(
    player=PlayerState(team=[pet_seq], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [make_skill("挨打")])], active_index=0),
)
expected_orders = [
    ["齿轮切开", "鸣沙陷阱", "轴承支撑", "齿轮扭矩"],
    ["鸣沙陷阱", "齿轮切开", "齿轮扭矩", "轴承支撑"],
    ["轴承支撑", "齿轮扭矩", "齿轮切开", "鸣沙陷阱"],
]
for expected in expected_orders:
    state_seq.turn_prepared = False
    generator.generate_actions(state_seq, True)
    current_order = [sk.name for sk in state_seq.player.get_active_pet().skills]
    assert current_order == expected, current_order
    state_seq.turn += 1
print("   [PASS] 多个带传动技能会按 1→4 号位逐个结算并得到实机序列\n")

print("2. 两侧技能能耗-1：行动生成按相邻被动减耗判定")
left = make_skill("左侧", energy=4)
middle = make_skill("中枢", energy=3, desc="主动：本技能被动额外-1能耗，被动：两侧技能能耗-1，传动1。")
right = make_skill("右侧", energy=4)
pet2 = make_pet("减耗宠", [left, middle, right], energy=3)
state2 = BattleState(
    player=PlayerState(team=[pet2], active_index=0),
    opponent=PlayerState(team=[make_pet("靶子", [make_skill("挨打")])], active_index=0),
)
actions2 = generator.generate_actions(state2, True)
usable = {a.skill.name for a in actions2 if a.type == ActionType.USE_SKILL}
assert "左侧" in usable, usable
assert "右侧" in usable, usable
assert "中枢" in usable, usable
print("   [PASS] 两侧技能因相邻被动从4费降为3费，可被正常生成\n")

print("3. 应对成功：两侧技能能耗永久-1")
counter_skill = make_skill(
    "防反核心",
    energy=3,
    desc="减伤80%，应对攻击：两侧技能能耗永久-1。",
    category=SkillCategory.DEFENSE,
)
counter_skill.counters = ["attack"]
counter_skill.effects = [Effect(EffectType.COUNTER, "opponent", 0, desc="attack:两侧技能能耗永久-1")]
adj_left = make_skill("邻左", energy=4)
adj_right = make_skill("邻右", energy=5)
player_pet = make_pet("防反宠", [adj_left, counter_skill, adj_right], energy=10)
enemy_skill = make_skill("进攻技", energy=3, desc="造成物伤。")
enemy_pet = make_pet("攻击宠", [enemy_skill], energy=10)
state3 = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[enemy_pet], active_index=0),
)
result3 = engine.apply_action(
    state3,
    Action(type=ActionType.USE_SKILL, skill=counter_skill),
    Action(type=ActionType.USE_SKILL, skill=enemy_skill),
)
skills_after = result3.player.get_active_pet().skills
assert skills_after[0].energy_cost == 3, skills_after[0].energy_cost
assert skills_after[2].energy_cost == 4, skills_after[2].energy_cost
print("   [PASS] 应对成功后两侧技能能耗永久下降\n")

print("4. 槽位威力加成：1号或3号位威力+30")
power_skill = make_skill("磁暴测试", energy=3, desc="造成魔伤，本技能位于1号或3号位时威力+30。")
filler = make_skill("填充", energy=1)
player_pet4 = make_pet("威力宠", [power_skill, filler, filler, filler], energy=10)
enemy_pet4 = make_pet("靶子", [make_skill("挨打")], energy=10)
state4 = BattleState(
    player=PlayerState(team=[player_pet4], active_index=0),
    opponent=PlayerState(team=[enemy_pet4], active_index=0),
)
result4 = engine.apply_action(
    state4,
    Action(type=ActionType.USE_SKILL, skill=power_skill),
    Action(type=ActionType.GATHER_ENERGY),
)
damage_with_bonus = 200 - result4.opponent.get_active_pet().current_hp

base_skill = make_skill("普通攻击", energy=3, desc="造成魔伤。")
player_pet4b = make_pet("基线宠", [base_skill], energy=10)
enemy_pet4b = make_pet("靶子", [make_skill("挨打")], energy=10)
state4b = BattleState(
    player=PlayerState(team=[player_pet4b], active_index=0),
    opponent=PlayerState(team=[enemy_pet4b], active_index=0),
)
result4b = engine.apply_action(
    state4b,
    Action(type=ActionType.USE_SKILL, skill=base_skill),
    Action(type=ActionType.GATHER_ENERGY),
)
base_damage = 200 - result4b.opponent.get_active_pet().current_hp
assert damage_with_bonus > base_damage, (damage_with_bonus, base_damage)
print("   [PASS] 槽位威力加成已生效\n")

print("5. 两侧技能威力和的三分之一")
left_power = make_skill("左威力", energy=2)
left_power.base_power = 90
center_power = make_skill("钢钻测试", energy=3, desc="造成物伤，技能威力为两侧技能威力和的三分之一。")
right_power = make_skill("右威力", energy=2)
right_power.base_power = 60
player_pet5 = make_pet("钢钻宠", [left_power, center_power, right_power], energy=10)
enemy_pet5 = make_pet("靶子", [make_skill("挨打")], energy=10)
state5 = BattleState(
    player=PlayerState(team=[player_pet5], active_index=0),
    opponent=PlayerState(team=[enemy_pet5], active_index=0),
)
result5 = engine.apply_action(
    state5,
    Action(type=ActionType.USE_SKILL, skill=center_power),
    Action(type=ActionType.GATHER_ENERGY),
)
damage_center = 200 - result5.opponent.get_active_pet().current_hp

reference_power = make_skill("参考攻击", energy=3, desc="造成物伤。")
reference_power.base_power = 50
player_pet5b = make_pet("参考宠", [reference_power], energy=10)
enemy_pet5b = make_pet("靶子", [make_skill("挨打")], energy=10)
state5b = BattleState(
    player=PlayerState(team=[player_pet5b], active_index=0),
    opponent=PlayerState(team=[enemy_pet5b], active_index=0),
)
result5b = engine.apply_action(
    state5b,
    Action(type=ActionType.USE_SKILL, skill=reference_power),
    Action(type=ActionType.GATHER_ENERGY),
)
damage_reference = 200 - result5b.opponent.get_active_pet().current_hp
assert damage_center == damage_reference, (damage_center, damage_reference)
print("   [PASS] 两侧技能威力和/3 已生效\n")

print("6. 槽位连击加成：1号或3号位连击+1")
multi_skill = make_skill("传感器测试", energy=3, desc="造成物伤，2连击，本技能位于1号或3号位时连击+1。")
multi_skill.hits = 2
player_pet6 = make_pet("连击宠", [multi_skill], energy=10)
enemy_pet6 = make_pet("靶子", [make_skill("挨打")], energy=10)
enemy_pet6.current_hp = 500
enemy_pet6.max_hp = 500
state6 = BattleState(
    player=PlayerState(team=[player_pet6], active_index=0),
    opponent=PlayerState(team=[enemy_pet6], active_index=0),
)
result6 = engine.apply_action(
    state6,
    Action(type=ActionType.USE_SKILL, skill=multi_skill),
    Action(type=ActionType.GATHER_ENERGY),
)
damage_multi = 500 - result6.opponent.get_active_pet().current_hp

two_hit_skill = make_skill("双击参考", energy=3, desc="造成物伤。")
two_hit_skill.hits = 2
player_pet6b = make_pet("双击宠", [two_hit_skill], energy=10)
enemy_pet6b = make_pet("靶子", [make_skill("挨打")], energy=10)
enemy_pet6b.current_hp = 500
enemy_pet6b.max_hp = 500
state6b = BattleState(
    player=PlayerState(team=[player_pet6b], active_index=0),
    opponent=PlayerState(team=[enemy_pet6b], active_index=0),
)
result6b = engine.apply_action(
    state6b,
    Action(type=ActionType.USE_SKILL, skill=two_hit_skill),
    Action(type=ActionType.GATHER_ENERGY),
)
damage_two_hit = 500 - result6b.opponent.get_active_pet().current_hp
assert damage_multi > damage_two_hit, (damage_multi, damage_two_hit)
print("   [PASS] 槽位连击加成已生效\n")

print("7. 交换两侧技能位置")
left_swap = make_skill("左技能", energy=1)
center_swap = make_skill("换位核心", energy=2, desc="自己回复2能量，交换两侧技能位置。", category=SkillCategory.STATUS)
center_swap.effects = [Effect(EffectType.ENERGY_RESTORE, "self", 0, desc="swap_adjacent_skills")]
right_swap = make_skill("右技能", energy=1)
tail_swap = make_skill("尾技能", energy=1)
player_pet7 = make_pet("换位宠", [left_swap, center_swap, right_swap, tail_swap], energy=10)
enemy_pet7 = make_pet("靶子", [make_skill("挨打")], energy=10)
state7 = BattleState(
    player=PlayerState(team=[player_pet7], active_index=0),
    opponent=PlayerState(team=[enemy_pet7], active_index=0),
)
result7 = engine.apply_action(
    state7,
    Action(type=ActionType.USE_SKILL, skill=center_swap),
    Action(type=ActionType.GATHER_ENERGY),
)
skills_after_swap = [sk.name for sk in result7.player.get_active_pet().skills]
assert skills_after_swap == ["右技能", "换位核心", "左技能", "尾技能"], skills_after_swap
print("   [PASS] 当前技能两侧槽位已正确交换\n")

print("8. 槽位条件 buff：1号或3号位额外获得物攻+60%")
slot_buff_skill = make_skill(
    "槽位增益",
    energy=3,
    desc="自己获得速度+80，本技能位于1号或3号位时额外获得物攻+60%。",
    category=SkillCategory.STATUS,
)
slot_buff_skill.effects = [
    Effect(EffectType.STAT_BUFF, "self", 80, desc="速度_flat"),
    Effect(EffectType.STAT_BUFF, "self", 6, desc="slot_13:物攻"),
]
player_pet8 = make_pet("增益宠", [slot_buff_skill, make_skill("填充")], energy=10)
enemy_pet8 = make_pet("靶子", [make_skill("挨打")], energy=10)
state8 = BattleState(
    player=PlayerState(team=[player_pet8], active_index=0),
    opponent=PlayerState(team=[enemy_pet8], active_index=0),
)
result8 = engine.apply_action(
    state8,
    Action(type=ActionType.USE_SKILL, skill=slot_buff_skill),
    Action(type=ActionType.GATHER_ENERGY),
)
pet8_after = result8.player.get_active_pet()
assert pet8_after.stats["速度"] == 180, pet8_after.stats["速度"]
assert pet8_after.stat_modifiers.physical_attack == 6, pet8_after.stat_modifiers.physical_attack
print("   [PASS] 槽位条件 buff 已按 1号位 正确触发\n")

print("9. 两侧技能威力永久增加")
power_left = make_skill("左技", energy=1)
power_left.base_power = 50
power_mid = make_skill("增威核心", energy=2, desc="使用后两侧技能威力永久+20，应对防御：变为威力永久+30。", category=SkillCategory.STATUS)
power_mid.effects = [Effect(EffectType.ENERGY_RESTORE, "self", 20, desc="adjacent_power_permanent")]
power_right = make_skill("右技", energy=1)
power_right.base_power = 70
power_tail = make_skill("尾技", energy=1)
player_pet9 = make_pet("增威宠", [power_left, power_mid, power_right, power_tail], energy=10)
enemy_pet9 = make_pet("靶子", [make_skill("挨打")], energy=10)
state9 = BattleState(
    player=PlayerState(team=[player_pet9], active_index=0),
    opponent=PlayerState(team=[enemy_pet9], active_index=0),
)
result9 = engine.apply_action(
    state9,
    Action(type=ActionType.USE_SKILL, skill=power_mid),
    Action(type=ActionType.GATHER_ENERGY),
)
skills9 = result9.player.get_active_pet().skills
assert skills9[0].base_power == 70, skills9[0].base_power
assert skills9[2].base_power == 90, skills9[2].base_power
print("   [PASS] 主效果已使两侧技能威力永久+20\n")

print("10. 应对防御：两侧技能威力永久+30")
counter_power_skill = make_skill(
    "防御增威核心",
    energy=2,
    desc="使用后两侧技能威力永久+20，应对防御：变为威力永久+30。",
    category=SkillCategory.DEFENSE,
)
counter_power_skill.counters = ["defense"]
counter_power_skill.effects = [Effect(EffectType.COUNTER, "opponent", 0, desc="defense:两侧技能威力永久+30")]
power_left_2 = make_skill("左技2", energy=1)
power_left_2.base_power = 40
power_right_2 = make_skill("右技2", energy=1)
power_right_2.base_power = 60
enemy_def_skill = make_skill("守御", energy=1, category=SkillCategory.DEFENSE)
player_pet10 = make_pet("反制增威宠", [power_left_2, counter_power_skill, power_right_2], energy=10)
enemy_pet10 = make_pet("防守宠", [enemy_def_skill], energy=10)
state10 = BattleState(
    player=PlayerState(team=[player_pet10], active_index=0),
    opponent=PlayerState(team=[enemy_pet10], active_index=0),
)
result10 = engine.apply_action(
    state10,
    Action(type=ActionType.USE_SKILL, skill=counter_power_skill),
    Action(type=ActionType.USE_SKILL, skill=enemy_def_skill),
)
skills10 = result10.player.get_active_pet().skills
assert skills10[0].base_power == 70, skills10[0].base_power
assert skills10[2].base_power == 90, skills10[2].base_power
print("   [PASS] 应对防御分支已使两侧技能威力永久+30\n")

print("=" * 50)
print("所有槽位效果测试通过！")
print("=" * 50)
