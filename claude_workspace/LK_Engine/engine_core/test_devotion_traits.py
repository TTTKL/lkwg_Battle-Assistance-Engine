"""
测试奉献相关特性与奉献对技能的实际强化。
"""
from core.models import (
    Action,
    ActionType,
    BattleState,
    DamageType,
    FieldMark,
    PetInstance,
    PetTemplate,
    PlayerState,
    Skill,
    SkillCategory,
    Trait,
)
from core.status_effects import StatusEffectType
from data_loader import DataLoader
from engine.extended_battle_engine import ExtendedBattleEngine


def make_template(name: str, trait_names: list[str]) -> PetTemplate:
    return PetTemplate(
        id=1,
        name=name,
        types=["虫"],
        stats={"生命": 220, "物攻": 120, "魔攻": 100, "物防": 90, "魔防": 90, "速度": 90},
        traits=[Trait(name=t, desc=t) for t in trait_names],
        learnable_skills=[],
    )


def make_skill(name: str, power: int = 60, energy: int = 3, category: SkillCategory = SkillCategory.ATTACK) -> Skill:
    return Skill(
        name=name,
        element="虫",
        category=category,
        damage_type=DamageType.PHYSICAL if category == SkillCategory.ATTACK else None,
        base_power=power,
        energy_cost=energy,
    )


def make_pet(name: str, traits: list[str], skills: list[Skill], hp: int = 220) -> PetInstance:
    template = make_template(name, traits)
    return PetInstance(
        template=template,
        current_hp=hp,
        max_hp=220,
        stats=template.stats.copy(),
        skills=skills,
        current_energy=10,
    )


loader = DataLoader()
engine = ExtendedBattleEngine(loader)

print("=== 奉献特性测试 ===\n")

print("1. 坚韧铠甲：受击后获得奉献")
player1 = make_pet("铠甲虫", ["坚韧铠甲"], [make_skill("啃咬")])
opponent1 = make_pet("攻击者", [], [make_skill("撞击", power=80)])
state1 = BattleState(
    player=PlayerState(team=[player1], active_index=0),
    opponent=PlayerState(team=[opponent1], active_index=0),
)
result1 = engine.apply_action(
    state1,
    Action(type=ActionType.GATHER_ENERGY),
    Action(type=ActionType.USE_SKILL, skill=opponent1.skills[0]),
)
ts1 = result1.player.team_state
assert any([
    ts1.devotion_poison, ts1.devotion_lifesteal, ts1.devotion_combo,
    ts1.devotion_power, ts1.devotion_energy
]), ts1
print("   [PASS] 坚韧铠甲已向队伍写入奉献\n")

print("2. 花精灵：回合结束后获得奉献")
player2 = make_pet("花衣蝶", ["花精灵"], [make_skill("啃咬")])
opponent2 = make_pet("对手", [], [make_skill("挨打")])
state2 = BattleState(
    player=PlayerState(team=[player2], active_index=0),
    opponent=PlayerState(team=[opponent2], active_index=0),
)
result2 = engine.apply_action(
    state2,
    Action(type=ActionType.GATHER_ENERGY),
    Action(type=ActionType.GATHER_ENERGY),
)
ts2 = result2.player.team_state
assert any([
    ts2.devotion_poison, ts2.devotion_lifesteal, ts2.devotion_combo,
    ts2.devotion_power, ts2.devotion_energy
]), ts2
print("   [PASS] 花精灵已在回合结束获得奉献\n")

print("3. 扫拖一体：驱散后获得奉献")
player3 = make_pet("扫拖蛛", ["扫拖一体"], [make_skill("啃咬")])
opponent3 = make_pet("对手", [], [make_skill("挨打")])
state3 = BattleState(
    player=PlayerState(team=[player3], active_index=0),
    opponent=PlayerState(team=[opponent3], active_index=0),
)
state3.set_mark(False, FieldMark(type_key=StatusEffectType.ATTACK_MARK.value, stacks=2, is_positive=True))
result3 = engine.apply_action(
    state3,
    Action(type=ActionType.GATHER_ENERGY),
    Action(type=ActionType.GATHER_ENERGY),
)
ts3 = result3.player.team_state
assert any([
    ts3.devotion_poison, ts3.devotion_lifesteal, ts3.devotion_combo,
    ts3.devotion_power, ts3.devotion_energy
]), ts3
print("   [PASS] 扫拖一体已在驱散后获得奉献\n")

print("4. 振奋虫心：击杀后获得5次奉献")
finisher = make_skill("致命啃咬", power=500, energy=3)
player4 = make_pet("红钻", ["振奋虫心"], [finisher], hp=220)
opponent4 = make_pet("对手", [], [make_skill("挨打")], hp=40)
state4 = BattleState(
    player=PlayerState(team=[player4], active_index=0),
    opponent=PlayerState(team=[opponent4], active_index=0),
)
result4 = engine.apply_action(
    state4,
    Action(type=ActionType.USE_SKILL, skill=finisher),
    Action(type=ActionType.GATHER_ENERGY),
)
ts4 = result4.player.team_state
total_devotion = ts4.devotion_poison + ts4.devotion_lifesteal + ts4.devotion_combo + ts4.devotion_power + ts4.devotion_energy
assert total_devotion > 0, total_devotion
print("   [PASS] 振奋虫心击杀后已写入多次奉献\n")

print("5. 奉献对啃咬生效")
player5 = make_pet("奉献虫", [], [make_skill("啃咬", power=60, energy=5)])
opponent5 = make_pet("木桩", [], [make_skill("挨打")], hp=500)
opponent5.max_hp = 500
state5 = BattleState(
    player=PlayerState(team=[player5], active_index=0),
    opponent=PlayerState(team=[opponent5], active_index=0),
)
state5.player.team_state.devotion_power = 20
state5.player.team_state.devotion_combo = 1
state5.player.team_state.devotion_lifesteal = 10
state5.player.team_state.devotion_poison = 2
state5.player.team_state.devotion_energy = 2
player_hp_before = state5.player.get_active_pet().current_hp
result5 = engine.apply_action(
    state5,
    Action(type=ActionType.USE_SKILL, skill=player5.skills[0]),
    Action(type=ActionType.GATHER_ENERGY),
)
pet5_after = result5.player.get_active_pet()
opp5_after = result5.opponent.get_active_pet()
assert pet5_after.current_energy == 7, pet5_after.current_energy
assert pet5_after.current_hp >= player_hp_before, (pet5_after.current_hp, player_hp_before)
assert opp5_after.get_status_stacks(StatusEffectType.POISON) >= 2, opp5_after.get_status_stacks(StatusEffectType.POISON)
assert opp5_after.current_hp < 500, opp5_after.current_hp
assert pet5_after.skills[0].energy_cost > 5, pet5_after.skills[0].energy_cost
print("   [PASS] 奉献已对啃咬提供威力/减耗/吸血/中毒/连击强化\n")

print("6. 虫群过境：指定奉献连击+1")
crossing = make_skill("虫群过境", power=70, energy=3)
crossing.desc = "造成物伤，2连击。己方队伍获得1次奉献：获得连击数+1。"
crossing.hits = 2
crossing.effects = []
player6 = make_pet("虫群宠", [], [crossing])
opponent6 = make_pet("木桩", [], [make_skill("挨打")], hp=500)
opponent6.max_hp = 500
state6 = BattleState(
    player=PlayerState(team=[player6], active_index=0),
    opponent=PlayerState(team=[opponent6], active_index=0),
)
from core.models import Effect, EffectType
crossing.effects = [Effect(EffectType.ENERGY_RESTORE, "self", 1, desc="grant_specific_devotion:combo")]
result6 = engine.apply_action(
    state6,
    Action(type=ActionType.USE_SKILL, skill=crossing),
    Action(type=ActionType.GATHER_ENERGY),
)
assert result6.player.team_state.devotion_combo >= 1, result6.player.team_state.devotion_combo
print("   [PASS] 虫群过境已写入指定连击奉献\n")

print("7. 虫群智慧：获得2次随机奉献")
wisdom = make_skill("虫群智慧", power=0, energy=2, category=SkillCategory.STATUS)
wisdom.desc = "己方队伍获得2次随机奉献。"
wisdom.effects = [Effect(EffectType.ENERGY_RESTORE, "self", 2, desc="grant_random_devotion")]
player7 = make_pet("智慧虫", [], [wisdom])
opponent7 = make_pet("木桩", [], [make_skill("挨打")])
state7 = BattleState(
    player=PlayerState(team=[player7], active_index=0),
    opponent=PlayerState(team=[opponent7], active_index=0),
)
result7 = engine.apply_action(
    state7,
    Action(type=ActionType.USE_SKILL, skill=wisdom),
    Action(type=ActionType.GATHER_ENERGY),
)
ts7 = result7.player.team_state
assert any([ts7.devotion_poison, ts7.devotion_lifesteal, ts7.devotion_combo, ts7.devotion_power, ts7.devotion_energy]), ts7
print("   [PASS] 虫群智慧已写入随机奉献\n")

print("=" * 50)
print("所有奉献特性测试通过！")
print("=" * 50)
