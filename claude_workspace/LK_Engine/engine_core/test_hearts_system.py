"""
测试心数系统
验证精灵死亡时的心数扣除和胜负判定
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType
)
from core.status_effects import StatusEffectType
from engine.extended_battle_engine import ExtendedBattleEngine
from data_loader import DataLoader


def create_test_pet(name: str, hp: int, is_legendary: bool = False) -> PetInstance:
    pet_name = f"传说{name}" if is_legendary else name
    template = PetTemplate(
        id=1, name=pet_name,
        types=["火"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        traits=[], learnable_skills=[],
        is_legendary=is_legendary,
    )
    skill = Skill(
        name="致命一击", element="火",
        category=SkillCategory.ATTACK, damage_type=DamageType.PHYSICAL,
        base_power=500, energy_cost=5
    )
    return PetInstance(
        template=template, current_hp=hp, max_hp=100,
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        skills=[skill], current_energy=10
    )


loader = DataLoader()


def test_basic_heart_deduction():
    print("=== 测试基础心数扣除 ===")
    engine = ExtendedBattleEngine(loader)
    player_pet = create_test_pet("火神", 100)
    opponent_pet = create_test_pet("水神", 10)
    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0),
        opponent=PlayerState(team=[opponent_pet], active_index=0)
    )
    print(f"初始心数 - 玩家: {state.player_hearts}, 对手: {state.opponent_hearts}")
    player_action = Action(type=ActionType.USE_SKILL, skill=player_pet.skills[0])
    opponent_action = Action(type=ActionType.GATHER_ENERGY)
    new_state = engine.apply_action(state, player_action, opponent_action)
    print(f"对手精灵存活: {new_state.opponent.get_active_pet().is_alive}")
    print(f"战斗后心数 - 玩家: {new_state.player_hearts}, 对手: {new_state.opponent_hearts}")
    assert new_state.opponent_hearts == 3, f"对手心数应为3，实际为{new_state.opponent_hearts}"
    assert not new_state.opponent.get_active_pet().is_alive
    print("[PASS] 基础心数扣除测试通过\n")


def test_legendary_heart_deduction():
    print("=== 测试传说精灵心数扣除 ===")
    engine = ExtendedBattleEngine(loader)
    player_pet = create_test_pet("火神", 100)
    opponent_pet = create_test_pet("水神", 10, is_legendary=True)
    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0),
        opponent=PlayerState(team=[opponent_pet], active_index=0)
    )
    print(f"初始心数 - 玩家: {state.player_hearts}, 对手: {state.opponent_hearts}")
    print(f"对手精灵: {opponent_pet.template.name}，is_legendary={opponent_pet.template.is_legendary}")
    player_action = Action(type=ActionType.USE_SKILL, skill=player_pet.skills[0])
    opponent_action = Action(type=ActionType.GATHER_ENERGY)
    new_state = engine.apply_action(state, player_action, opponent_action)
    print(f"战斗后心数 - 玩家: {new_state.player_hearts}, 对手: {new_state.opponent_hearts}")
    assert new_state.opponent_hearts == 2, f"对手心数应为2（传说精灵扣2心），实际为{new_state.opponent_hearts}"
    print("[PASS] 传说精灵心数扣除测试通过\n")


def test_battle_end_by_hearts():
    print("=== 测试基于心数的战斗结束判定 ===")
    engine = ExtendedBattleEngine(loader)
    player_pet = create_test_pet("火神", 100)
    opponent_pet = create_test_pet("水神", 10)
    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0),
        opponent=PlayerState(team=[opponent_pet], active_index=0),
        opponent_hearts=1,
    )
    print(f"初始心数 - 玩家: {state.player_hearts}, 对手: {state.opponent_hearts}")
    player_action = Action(type=ActionType.USE_SKILL, skill=player_pet.skills[0])
    opponent_action = Action(type=ActionType.GATHER_ENERGY)
    new_state = engine.apply_action(state, player_action, opponent_action)
    print(f"战斗后心数 - 玩家: {new_state.player_hearts}, 对手: {new_state.opponent_hearts}")
    assert new_state.opponent_hearts == 0, f"对手心数应为0，实际为{new_state.opponent_hearts}"
    assert engine.is_battle_over(new_state), "战斗应该结束"
    assert engine.get_winner_by_hearts(new_state) == "player", "玩家应该获胜"
    print("[PASS] 基于心数的战斗结束判定测试通过\n")


def test_status_effect_heart_deduction():
    print("=== 测试状态效果导致死亡的心数扣除 ===")
    engine = ExtendedBattleEngine(loader)
    player_pet = create_test_pet("火神", 100)

    template = PetTemplate(
        id=2, name="水神", types=["水"],
        stats={"生命": 100, "物攻": 50, "魔攻": 50, "物防": 50, "魔防": 50, "速度": 50},
        traits=[], learnable_skills=[]
    )
    opponent_pet = PetInstance(
        template=template, current_hp=3, max_hp=100,
        stats={"生命": 100, "物攻": 50, "魔攻": 50, "物防": 50, "魔防": 50, "速度": 50},
        skills=[], current_energy=10
    )

    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0),
        opponent=PlayerState(team=[opponent_pet], active_index=0)
    )

    print(f"初始心数 - 玩家: {state.player_hearts}, 对手: {state.opponent_hearts}")
    print(f"对手血量: {opponent_pet.current_hp}, 最大血量: {opponent_pet.max_hp}")

    # 先执行一次行动，然后给对手添加中毒
    gather = Action(type=ActionType.GATHER_ENERGY)
    state = engine.apply_action(state, gather, gather)

    # 给对手添加5层中毒
    opp = state.opponent.get_active_pet()
    opp.add_status(StatusEffectType.POISON, 5)
    print(f"添加中毒后 - 中毒层数: {opp.get_status_stacks(StatusEffectType.POISON)}")
    print(f"预期中毒伤害: {int(opp.max_hp * 0.03 * 5)}")

    new_state = engine.apply_action(state, gather, gather)
    print(f"回合结束后对手血量: {new_state.opponent.get_active_pet().current_hp}")
    print(f"战斗后心数 - 玩家: {new_state.player_hearts}, 对手: {new_state.opponent_hearts}")

    assert not new_state.opponent.get_active_pet().is_alive, "对手应该因中毒死亡"
    assert new_state.opponent_hearts == 3, f"对手心数应为3，实际为{new_state.opponent_hearts}"
    print("[PASS] 状态效果导致死亡的心数扣除测试通过\n")


if __name__ == "__main__":
    try:
        test_basic_heart_deduction()
        test_legendary_heart_deduction()
        test_battle_end_by_hearts()
        test_status_effect_heart_deduction()
        print("=" * 50)
        print("所有心数系统测试通过！")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
    except Exception as e:
        print(f"\n[ERROR] 运行错误: {e}")
        import traceback
        traceback.print_exc()
