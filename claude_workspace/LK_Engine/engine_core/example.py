"""
示例：使用游戏分析引擎
"""
from game_analysis_engine import GameAnalysisEngine


def example_simple_battle():
    """简单的1v1对战示例"""
    print("=" * 60)
    print("示例1: 简单1v1对战")
    print("=" * 60)

    # 初始化引擎
    engine = GameAnalysisEngine()

    # 创建玩家精灵：火神
    player_pet = engine.create_pet_instance(
        pet_name="火神",
        skill_names=["猛烈撞击", "抓挠"],
        hp_percent=0.8,
        energy=7
    )

    # 创建对手精灵：水蓝蓝
    opponent_pet = engine.create_pet_instance(
        pet_name="水蓝蓝",
        skill_names=["猛烈撞击", "抓挠"],
        hp_percent=1.0,
        energy=10
    )

    if not player_pet or not opponent_pet:
        print("错误：无法创建精灵")
        return

    # 创建对战状态
    state = engine.create_battle_state(
        player_team=[player_pet],
        opponent_team=[opponent_pet]
    )

    print(f"\n玩家: {player_pet.template.name}")
    print(f"  属性: {', '.join(player_pet.template.types)}")
    print(f"  HP: {player_pet.current_hp}/{player_pet.max_hp}")
    print(f"  能量: {player_pet.current_energy}")
    print(f"  技能: {', '.join(s.name for s in player_pet.skills)}")

    print(f"\n对手: {opponent_pet.template.name}")
    print(f"  属性: {', '.join(opponent_pet.template.types)}")
    print(f"  HP: {opponent_pet.current_hp}/{opponent_pet.max_hp}")
    print(f"  能量: {opponent_pet.current_energy}")
    print(f"  技能: {', '.join(s.name for s in opponent_pet.skills)}")

    # 分析状态
    print("\n正在分析...")
    result = engine.analyze_state(state, depth=2)

    print(f"\n局面评分: {result['evaluation']:.1f}")
    print(f"搜索节点数: {result['nodes_searched']}")

    if result['best_action']:
        print(f"\n推荐行动: {result['best_action']}")

    print(f"\n所有可能的行动:")
    for i, action in enumerate(result['all_actions'], 1):
        print(f"  {i}. {action}")


def example_team_battle():
    """多精灵队伍对战示例"""
    print("\n" + "=" * 60)
    print("示例2: 多精灵队伍对战")
    print("=" * 60)

    engine = GameAnalysisEngine()

    # 创建玩家队伍
    player_team = []
    for pet_name in ["火神", "水蓝蓝"]:
        pet = engine.create_pet_instance(
            pet_name=pet_name,
            skill_names=["猛烈撞击", "抓挠"],
            hp_percent=1.0,
            energy=10
        )
        if pet:
            player_team.append(pet)

    # 创建对手队伍
    opponent_team = []
    for pet_name in ["喵喵", "迪莫"]:
        pet = engine.create_pet_instance(
            pet_name=pet_name,
            skill_names=["猛烈撞击", "抓挠"],
            hp_percent=1.0,
            energy=10
        )
        if pet:
            opponent_team.append(pet)

    if len(player_team) < 2 or len(opponent_team) < 2:
        print("错误：无法创建完整队伍")
        return

    # 创建对战状态
    state = engine.create_battle_state(
        player_team=player_team,
        opponent_team=opponent_team,
        player_active_index=0,
        opponent_active_index=0
    )

    print(f"\n玩家队伍:")
    for i, pet in enumerate(player_team):
        marker = "★" if i == 0 else " "
        print(f"  {marker} {pet.template.name} (HP: {pet.current_hp}/{pet.max_hp})")

    print(f"\n对手队伍:")
    for i, pet in enumerate(opponent_team):
        marker = "★" if i == 0 else " "
        print(f"  {marker} {pet.template.name} (HP: {pet.current_hp}/{pet.max_hp})")

    # 分析状态
    print("\n正在分析...")
    result = engine.analyze_state(state, depth=2)

    print(f"\n局面评分: {result['evaluation']:.1f}")
    print(f"推荐行动: {result['best_action']}")

    # 显示换精灵选项
    switch_actions = [a for a in result['all_actions'] if a.type.value == 'switch_pet']
    if switch_actions:
        print(f"\n可换精灵:")
        for action in switch_actions:
            target_pet = player_team[action.target_index]
            print(f"  - 换成 {target_pet.template.name}")


def example_next_states():
    """获取所有下一步状态示例"""
    print("\n" + "=" * 60)
    print("示例3: 获取所有可能的下一步状态")
    print("=" * 60)

    engine = GameAnalysisEngine()

    # 创建简单对战
    player_pet = engine.create_pet_instance(
        pet_name="火神",
        skill_names=["猛烈撞击"],
        hp_percent=1.0,
        energy=10
    )

    opponent_pet = engine.create_pet_instance(
        pet_name="水蓝蓝",
        skill_names=["猛烈撞击"],
        hp_percent=1.0,
        energy=10
    )

    if not player_pet or not opponent_pet:
        print("错误：无法创建精灵")
        return

    state = engine.create_battle_state(
        player_team=[player_pet],
        opponent_team=[opponent_pet]
    )

    # 获取所有下一步状态
    next_states = engine.get_all_next_states(state)

    print(f"\n共有 {len(next_states)} 种可能的下一步状态:\n")

    for i, (player_action, opponent_action, new_state) in enumerate(next_states[:5], 1):
        print(f"{i}. 玩家{player_action} vs 对手{opponent_action}")

        player_pet_new = new_state.player.get_active_pet()
        opponent_pet_new = new_state.opponent.get_active_pet()

        if player_pet_new and opponent_pet_new:
            print(f"   结果: 玩家HP={player_pet_new.current_hp}, 对手HP={opponent_pet_new.current_hp}")

        if new_state.is_terminal():
            print(f"   终局! 胜者: {new_state.get_winner()}")

        print()

    if len(next_states) > 5:
        print(f"... 还有 {len(next_states) - 5} 种状态")


if __name__ == '__main__':
    try:
        example_simple_battle()
        example_team_battle()
        example_next_states()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
