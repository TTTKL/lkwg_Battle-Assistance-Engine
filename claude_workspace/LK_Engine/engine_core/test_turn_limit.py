"""
测试50回合强制结束机制
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType
)
from engine.extended_battle_engine import ExtendedBattleEngine
from data_loader import DataLoader


def create_test_pet(name: str, hp: int = 100, pet_id: int = 1) -> PetInstance:
    template = PetTemplate(
        id=pet_id, name=name, types=["火"],
        stats={"生命": hp, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        traits=[], learnable_skills=[]
    )
    skill = Skill(
        name="攻击", element="火", category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL, base_power=1, energy_cost=1
    )
    return PetInstance(
        template=template, current_hp=hp, max_hp=hp,
        stats={"生命": hp, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        skills=[skill], current_energy=10
    )


print("=== 50回合强制结束测试 ===\n")

loader = DataLoader()

# 测试1：模拟50回合后强制结束（双方完全对称 → 平局）
print("测试1: 双方对称时50回合后判平局")
engine = ExtendedBattleEngine(loader)
player_pet = create_test_pet("火神", hp=100, pet_id=1)
opponent_pet = create_test_pet("水神", hp=100, pet_id=2)

state = BattleState(
    player=PlayerState(team=[player_pet], active_index=0),
    opponent=PlayerState(team=[opponent_pet], active_index=0),
    turn=49,
)

print(f"当前回合: {state.turn}")
print(f"初始心数 - 玩家: {state.player_hearts}, 对手: {state.opponent_hearts}")

gather_action = Action(type=ActionType.GATHER_ENERGY)
new_state = engine.apply_action(state, gather_action, gather_action)

print(f"执行后回合: {new_state.turn}")
print(f"执行后心数 - 玩家: {new_state.player_hearts}, 对手: {new_state.opponent_hearts}")

assert engine.is_battle_over(new_state), "战斗应该在第50回合后结束"
assert new_state.player_hearts == 0 and new_state.opponent_hearts == 0, "双方对称时应为平局"
winner = engine.get_winner_by_hearts(new_state)
assert winner == "draw", "双方对称时应为平局"
print(f"结果: {winner}")
print("[PASS] 50回合强制结束（平局）机制正常工作\n")

# 测试2：一方HP更多时该方获胜
print("测试2: HP多的一方获胜")
engine2 = ExtendedBattleEngine(loader)
player_pet2 = create_test_pet("火神", hp=100, pet_id=1)
opponent_pet2 = create_test_pet("水神", hp=60, pet_id=2)  # 对手HP更低

state2 = BattleState(
    player=PlayerState(team=[player_pet2], active_index=0),
    opponent=PlayerState(team=[opponent_pet2], active_index=0),
    turn=49,
)

new_state2 = engine2.apply_action(state2, gather_action, gather_action)
winner2 = engine2.get_winner_by_hearts(new_state2)
assert winner2 == "player", "HP多的一方应获胜"
print(f"玩家HP={player_pet2.current_hp}, 对手HP={opponent_pet2.current_hp}")
print(f"结果: {winner2}")
print("[PASS] HP优势方确定性获胜\n")

# 测试3：心数优势方获胜
print("测试3: 心数多的一方获胜")
engine3 = ExtendedBattleEngine(loader)
state3 = BattleState(
    player=PlayerState(team=[create_test_pet("火神", pet_id=1)], active_index=0),
    opponent=PlayerState(team=[create_test_pet("水神", pet_id=2)], active_index=0),
    turn=49,
    player_hearts=4,
    opponent_hearts=3,
)

new_state3 = engine3.apply_action(state3, gather_action, gather_action)
winner3 = engine3.get_winner_by_hearts(new_state3)
assert winner3 == "player", "心数多的一方应获胜"
print(f"结果: {winner3}")
print("[PASS] 心数优势方确定性获胜\n")

# 测试4：确认结果是确定性的（运行10次结果一致）
print("测试4: 确定性验证（运行10次结果一致）")
results = []
for i in range(10):
    e = ExtendedBattleEngine(loader)
    s = BattleState(
        player=PlayerState(team=[create_test_pet("火神", hp=80, pet_id=1)], active_index=0),
        opponent=PlayerState(team=[create_test_pet("水神", hp=100, pet_id=2)], active_index=0),
        turn=49,
    )
    ns = e.apply_action(s, gather_action, gather_action)
    w = e.get_winner_by_hearts(ns)
    results.append(w)

assert all(r == results[0] for r in results), "10次结果应完全一致"
print(f"10次结果全部为: {results[0]}")
print("[PASS] 确定性判定正常工作\n")

print("=" * 50)
print("50回合强制结束测试通过！")
print("=" * 50)
