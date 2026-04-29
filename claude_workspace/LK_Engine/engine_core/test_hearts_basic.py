"""
测试心数系统基础功能
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType
)
from engine.extended_battle_engine import ExtendedBattleEngine
from data_loader import DataLoader


def create_test_pet(name: str, hp: int, is_legendary: bool = False) -> PetInstance:
    """创建测试用精灵"""
    pet_name = name
    if is_legendary:
        pet_name = f"传说{name}"

    template = PetTemplate(
        id=1,
        name=pet_name,
        types=["火"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        traits=[],
        learnable_skills=[],
        is_legendary=is_legendary,
    )

    skill = Skill(
        name="致命一击",
        element="火",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL,
        base_power=500,
        energy_cost=5
    )

    return PetInstance(
        template=template,
        current_hp=hp,
        max_hp=100,
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        skills=[skill],
        current_energy=10
    )


print("=== 心数系统测试 ===\n")

loader = DataLoader()

# 测试1：基础心数扣除
print("1. 基础心数扣除")
engine = ExtendedBattleEngine(loader)
player_pet = create_test_pet("火神", 100)
opponent_pet = create_test_pet("水神", 10)
state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)
player_action = Action(type=ActionType.USE_SKILL, skill=player_pet.skills[0])
opponent_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, player_action, opponent_action)
assert new_state.opponent_hearts == 3, f"对手心数应为3，实际为{new_state.opponent_hearts}"
print("   [PASS] 普通精灵死亡扣1心\n")

# 测试2：传说精灵心数扣除
print("2. 传说精灵心数扣除")
engine = ExtendedBattleEngine(loader)
player_pet = create_test_pet("火神", 100)
opponent_pet = create_test_pet("水神", 10, is_legendary=True)
state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0)
)
player_action = Action(type=ActionType.USE_SKILL, skill=player_pet.skills[0])
opponent_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, player_action, opponent_action)
assert new_state.opponent_hearts == 2, f"对手心数应为2（传说精灵扣2心），实际为{new_state.opponent_hearts}"
print("   [PASS] 传说精灵死亡扣2心\n")

# 测试3：战斗结束判定
print("3. 战斗结束判定")
engine = ExtendedBattleEngine(loader)
player_pet = create_test_pet("火神", 100)
opponent_pet = create_test_pet("水神", 10)
state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0),
    opponent_hearts=1,
)
player_action = Action(type=ActionType.USE_SKILL, skill=player_pet.skills[0])
opponent_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, player_action, opponent_action)
assert new_state.opponent_hearts == 0, f"对手心数应为0，实际为{new_state.opponent_hearts}"
assert engine.is_battle_over(new_state), "战斗应该结束"
assert engine.get_winner_by_hearts(new_state) == "player", "玩家应该获胜"
print("   [PASS] 心数归零时战斗结束\n")

print("=" * 50)
print("心数系统核心功能测试通过！")
print("=" * 50)
