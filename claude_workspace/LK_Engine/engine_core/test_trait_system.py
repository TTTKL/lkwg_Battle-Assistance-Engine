"""
测试特性系统
验证精灵特性在不同时机的触发
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType, Trait
)
from engine.extended_battle_engine import ExtendedBattleEngine
from data_loader import DataLoader


def create_pet_with_trait(name: str, hp: int, trait_name: str) -> PetInstance:
    """创建带特性的测试精灵"""
    trait = Trait(name=trait_name, desc=f"{trait_name}特性")

    template = PetTemplate(
        id=1,
        name=name,
        types=["火"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        traits=[trait],
        learnable_skills=[]
    )

    skill = Skill(
        name="攻击",
        element="火",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL,
        base_power=50,
        energy_cost=3
    )

    return PetInstance(
        template=template,
        current_hp=hp,
        max_hp=100,
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        skills=[skill],
        current_energy=10
    )


print("=== 特性系统测试 ===\n")

# 测试1：威吓特性（入场时降低对手物攻）
print("1. 威吓特性（入场时降低对手物攻）")
engine = ExtendedBattleEngine(DataLoader())
player_pet = create_pet_with_trait("火神", 100, "威吓")
opponent_pet = create_pet_with_trait("水神", 100, "无特性")

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)

# 模拟换精灵触发入场特性
initial_phys_attack = opponent_pet.stat_modifiers.physical_attack
print(f"   对手初始物攻修正: {initial_phys_attack}")

# 创建第二只精灵用于换精灵
player_pet2 = create_pet_with_trait("火神2", 100, "威吓")
state.player.team.append(player_pet2)

# 换到第二只精灵（触发威吓）
switch_action = Action(type=ActionType.SWITCH_PET, target_index=1)
gather_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, switch_action, gather_action)

opponent_phys_attack = new_state.opponent.get_active_pet().stat_modifiers.physical_attack
print(f"   威吓触发后对手物攻修正: {opponent_phys_attack}")
assert opponent_phys_attack < initial_phys_attack, "威吓应该降低对手物攻"
print("   [PASS] 威吓特性正常触发\n")

# 测试2：反击特性（受击时反击）
print("2. 反击特性（受击时反击30%伤害）")
engine = ExtendedBattleEngine(DataLoader())
player_pet = create_pet_with_trait("火神", 100, "无特性")
opponent_pet = create_pet_with_trait("水神", 100, "反击")

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)

player_hp_before = player_pet.current_hp
print(f"   攻击前玩家血量: {player_hp_before}")

# 玩家攻击对手（对手有反击特性）
attack_action = Action(type=ActionType.USE_SKILL, skill=player_pet.skills[0])
gather_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, attack_action, gather_action)

player_hp_after = new_state.player.get_active_pet().current_hp
print(f"   攻击后玩家血量: {player_hp_after}")
assert player_hp_after < player_hp_before, "反击特性应该造成反伤"
print("   [PASS] 反击特性正常触发\n")

# 测试3：收割特性（击杀时恢复生命）
print("3. 收割特性（击杀时恢复20%最大生命）")
engine = ExtendedBattleEngine(DataLoader())
player_pet = create_pet_with_trait("火神", 50, "收割")  # 半血
opponent_pet = create_pet_with_trait("水神", 10, "无特性")  # 低血量

# 创建高威力技能确保秒杀
high_damage_skill = Skill(
    name="致命一击",
    element="火",
    category=SkillCategory.ATTACK,
    damage_type=DamageType.PHYSICAL,
    base_power=500,
    energy_cost=5
)
player_pet.skills = [high_damage_skill]

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)

player_hp_before = player_pet.current_hp
print(f"   击杀前玩家血量: {player_hp_before}")

# 击杀对手
attack_action = Action(type=ActionType.USE_SKILL, skill=high_damage_skill)
gather_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, attack_action, gather_action)

player_hp_after = new_state.player.get_active_pet().current_hp
opponent_alive = new_state.opponent.get_active_pet().is_alive
print(f"   击杀后玩家血量: {player_hp_after}")
print(f"   对手是否存活: {opponent_alive}")

assert not opponent_alive, "对手应该被击杀"
assert player_hp_after > player_hp_before, "收割特性应该恢复生命"
print("   [PASS] 收割特性正常触发\n")

print("=" * 50)
print("特性系统测试通过！")
print("=" * 50)
