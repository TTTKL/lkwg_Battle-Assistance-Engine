"""
测试聚能功能
验证基础引擎和扩展引擎的聚能结算是否正常工作
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType
)
from engine.battle_engine import BattleEngine
from engine.extended_battle_engine import ExtendedBattleEngine
from data_loader import DataLoader


def create_test_pet(name: str, hp: int, energy: int) -> PetInstance:
    """创建测试用精灵"""
    template = PetTemplate(
        id=1,
        name=name,
        types=["火"],
        stats={"生命": hp, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        traits=[],
        learnable_skills=[]
    )

    skill = Skill(
        name="测试技能",
        element="火",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL,
        base_power=50,
        energy_cost=3
    )

    return PetInstance(
        template=template,
        current_hp=hp,
        max_hp=hp,
        stats={"生命": hp, "物攻": 100, "魔攻": 100, "物防": 50, "魔防": 50, "速度": 80},
        skills=[skill],
        current_energy=energy
    )


def test_basic_engine_gather_energy():
    """测试基础引擎的聚能功能"""
    print("=== 测试基础引擎聚能 ===")

    # 创建数据加载器
    data_loader = DataLoader()
    engine = BattleEngine(data_loader)

    # 创建测试状态
    player_pet = create_test_pet("火神", 100, 4)
    opponent_pet = create_test_pet("水神", 100, 5)

    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0),
        opponent=PlayerState(team=[opponent_pet], active_index=0)
    )

    print(f"初始状态 - 玩家能量: {player_pet.current_energy}, 对手能量: {opponent_pet.current_energy}")

    # 双方都聚能
    gather_action = Action(type=ActionType.GATHER_ENERGY)
    new_state = engine.apply_action(state, gather_action, gather_action)

    player_energy = new_state.player.get_active_pet().current_energy
    opponent_energy = new_state.opponent.get_active_pet().current_energy

    print(f"聚能后 - 玩家能量: {player_energy}, 对手能量: {opponent_energy}")

    # 验证能量增加了3点
    assert player_energy == 7, f"玩家能量应为7，实际为{player_energy}"
    assert opponent_energy == 8, f"对手能量应为8，实际为{opponent_energy}"

    print("[PASS] 基础引擎聚能测试通过\n")


def test_extended_engine_gather_energy():
    """测试扩展引擎的聚能功能"""
    print("=== 测试扩展引擎聚能 ===")

    # 创建数据加载器
    data_loader = DataLoader()
    engine = ExtendedBattleEngine(data_loader)

    # 创建测试状态
    player_pet = create_test_pet("火神", 100, 2)
    opponent_pet = create_test_pet("水神", 100, 9)

    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0),
        opponent=PlayerState(team=[opponent_pet], active_index=0)
    )

    print(f"初始状态 - 玩家能量: {player_pet.current_energy}, 对手能量: {opponent_pet.current_energy}")

    # 双方都聚能
    gather_action = Action(type=ActionType.GATHER_ENERGY)
    new_state = engine.apply_action(state, gather_action, gather_action)

    player_energy = new_state.player.get_active_pet().current_energy
    opponent_energy = new_state.opponent.get_active_pet().current_energy

    print(f"聚能后 - 玩家能量: {player_energy}, 对手能量: {opponent_energy}")

    # 验证能量增加了3点，但不超过上限10
    assert player_energy == 5, f"玩家能量应为5，实际为{player_energy}"
    assert opponent_energy == 10, f"对手能量应为10（上限），实际为{opponent_energy}"

    print("[PASS] 扩展引擎聚能测试通过\n")


def test_gather_energy_cap():
    """测试聚能的能量上限"""
    print("=== 测试聚能能量上限 ===")

    data_loader = DataLoader()
    engine = BattleEngine(data_loader)

    # 创建能量接近上限的精灵
    player_pet = create_test_pet("火神", 100, 8)
    opponent_pet = create_test_pet("水神", 100, 10)

    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0),
        opponent=PlayerState(team=[opponent_pet], active_index=0)
    )

    print(f"初始状态 - 玩家能量: {player_pet.current_energy}, 对手能量: {opponent_pet.current_energy}")

    # 聚能
    gather_action = Action(type=ActionType.GATHER_ENERGY)
    new_state = engine.apply_action(state, gather_action, gather_action)

    player_energy = new_state.player.get_active_pet().current_energy
    opponent_energy = new_state.opponent.get_active_pet().current_energy

    print(f"聚能后 - 玩家能量: {player_energy}, 对手能量: {opponent_energy}")

    # 验证能量不会超过上限10
    assert player_energy == 10, f"玩家能量应为10（上限），实际为{player_energy}"
    assert opponent_energy == 10, f"对手能量应保持10（已满），实际为{opponent_energy}"

    print("[PASS] 聚能能量上限测试通过\n")


if __name__ == "__main__":
    try:
        test_basic_engine_gather_energy()
        test_extended_engine_gather_energy()
        test_gather_energy_cap()
        print("=" * 50)
        print("所有聚能测试通过！")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
    except Exception as e:
        print(f"\n[ERROR] 运行错误: {e}")
        import traceback
        traceback.print_exc()
