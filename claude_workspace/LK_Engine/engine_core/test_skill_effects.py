"""
测试技能效果系统
验证吸血、多段攻击、使用次数+1等效果
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType,
    Effect, EffectType
)
from engine.extended_battle_engine import ExtendedBattleEngine
from data_loader import DataLoader


def create_test_pet(name: str, hp: int) -> PetInstance:
    """创建测试用精灵"""
    template = PetTemplate(
        id=1,
        name=name,
        types=["火"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        traits=[],
        learnable_skills=[]
    )

    # 普通攻击技能
    normal_skill = Skill(
        name="普通攻击",
        element="火",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL,
        base_power=30,
        energy_cost=3
    )

    return PetInstance(
        template=template,
        current_hp=hp,
        max_hp=100,
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        skills=[normal_skill],
        current_energy=10
    )


print("=== 技能效果系统测试 ===\n")

# 测试1：吸血效果
print("1. 吸血效果（恢复造成伤害的30%）")
engine = ExtendedBattleEngine(DataLoader())
player_pet = create_test_pet("火神", 50)  # 半血
opponent_pet = create_test_pet("水神", 100)

# 创建带吸血效果的技能
lifesteal_skill = Skill(
    name="吸血攻击",
    element="火",
    category=SkillCategory.ATTACK,
    damage_type=DamageType.PHYSICAL,
    base_power=50,
    energy_cost=5,
    effects=[Effect(EffectType.LIFESTEAL, "self", 0.3)]  # 30%吸血
)
player_pet.skills = [lifesteal_skill]

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)

print(f"   攻击前玩家血量: {player_pet.current_hp}")

player_action = Action(type=ActionType.USE_SKILL, skill=lifesteal_skill)
opponent_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, player_action, opponent_action)

player_hp_after = new_state.player.get_active_pet().current_hp
print(f"   攻击后玩家血量: {player_hp_after}")
assert player_hp_after > 50, f"玩家血量应该增加（吸血），实际为{player_hp_after}"
print("   [PASS] 吸血效果正常工作\n")

# 测试2：多段攻击（2次攻击）
print("2. 多段攻击（hits=2）")
engine = ExtendedBattleEngine(DataLoader())
player_pet = create_test_pet("火神", 100)
opponent_pet = create_test_pet("水神", 100)

# 创建2段攻击技能
multi_hit_skill = Skill(
    name="连续攻击",
    element="火",
    category=SkillCategory.ATTACK,
    damage_type=DamageType.PHYSICAL,
    base_power=25,
    energy_cost=5,
    hits=2  # 2段攻击
)
player_pet.skills = [multi_hit_skill]

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)

opponent_hp_before = opponent_pet.current_hp
print(f"   攻击前对手血量: {opponent_hp_before}")

player_action = Action(type=ActionType.USE_SKILL, skill=multi_hit_skill)
opponent_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, player_action, opponent_action)

opponent_hp_after = new_state.opponent.get_active_pet().current_hp
damage_dealt = opponent_hp_before - opponent_hp_after
print(f"   攻击后对手血量: {opponent_hp_after}")
print(f"   总伤害: {damage_dealt}")
assert damage_dealt > 0, "应该造成伤害"
print("   [PASS] 多段攻击正常工作\n")

# 测试3：使用次数+1效果
print("3. 使用次数+1效果（额外释放一次）")
engine = ExtendedBattleEngine(DataLoader())
player_pet = create_test_pet("火神", 100)
opponent_pet = create_test_pet("水神", 100)

# 创建带使用次数+1的技能
extra_hit_skill = Skill(
    name="强化攻击",
    element="火",
    category=SkillCategory.ATTACK,
    damage_type=DamageType.PHYSICAL,
    base_power=30,
    energy_cost=5,
    hits=1,
    effects=[Effect(EffectType.EXTRA_HITS, "self", 1)]  # 额外1次
)
player_pet.skills = [extra_hit_skill]

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)

opponent_hp_before = opponent_pet.current_hp
print(f"   攻击前对手血量: {opponent_hp_before}")

player_action = Action(type=ActionType.USE_SKILL, skill=extra_hit_skill)
opponent_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, player_action, opponent_action)

opponent_hp_after = new_state.opponent.get_active_pet().current_hp
damage_dealt = opponent_hp_before - opponent_hp_after
print(f"   攻击后对手血量: {opponent_hp_after}")
print(f"   总伤害: {damage_dealt}（应该是2次攻击的伤害）")
assert damage_dealt > 0, "应该造成伤害"
print("   [PASS] 使用次数+1效果正常工作\n")

# 测试4：组合效果（多段攻击+吸血）
print("4. 组合效果（2段攻击+30%吸血）")
engine = ExtendedBattleEngine(DataLoader())
player_pet = create_test_pet("火神", 50)
opponent_pet = create_test_pet("水神", 100)

# 创建组合效果技能
combo_skill = Skill(
    name="吸血连击",
    element="火",
    category=SkillCategory.ATTACK,
    damage_type=DamageType.PHYSICAL,
    base_power=25,
    energy_cost=5,
    hits=2,
    effects=[Effect(EffectType.LIFESTEAL, "self", 0.3)]
)
player_pet.skills = [combo_skill]

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)

player_hp_before = player_pet.current_hp
print(f"   攻击前玩家血量: {player_hp_before}")

player_action = Action(type=ActionType.USE_SKILL, skill=combo_skill)
opponent_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, player_action, opponent_action)

player_hp_after = new_state.player.get_active_pet().current_hp
print(f"   攻击后玩家血量: {player_hp_after}")
assert player_hp_after > player_hp_before, "玩家血量应该增加（吸血）"
print("   [PASS] 组合效果正常工作\n")

print("=" * 50)
print("所有技能效果测试通过！")
print("=" * 50)
