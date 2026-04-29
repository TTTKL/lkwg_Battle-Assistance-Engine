"""
命令行接口
提供简单的命令行工具用于测试和演示
"""
import argparse
from game_analysis_engine import GameAnalysisEngine


def main():
    parser = argparse.ArgumentParser(description='洛克王国游戏分析引擎')
    parser.add_argument('--depth', type=int, default=2, help='搜索深度（默认2）')

    args = parser.parse_args()

    # 初始化引擎
    print("正在加载游戏数据...")
    engine = GameAnalysisEngine()
    print(f"已加载 {len(engine.data_loader.pets)} 只精灵")
    print(f"已加载 {len(engine.data_loader.skills)} 个技能")
    print()

    # 创建示例对战
    print("创建示例对战...")

    # 玩家队伍：火神
    player_pet = engine.create_pet_instance(
        pet_name="火神",
        skill_names=["猛烈撞击", "火焰喷射"],
        hp_percent=0.8,
        energy=7
    )

    # 对手队伍：水蓝蓝
    opponent_pet = engine.create_pet_instance(
        pet_name="水蓝蓝",
        skill_names=["猛烈撞击", "水枪"],
        hp_percent=1.0,
        energy=10
    )

    if not player_pet or not opponent_pet:
        print("错误：无法创建精灵实例")
        return

    # 创建对战状态
    state = engine.create_battle_state(
        player_team=[player_pet],
        opponent_team=[opponent_pet]
    )

    print(f"玩家: {player_pet.template.name} (HP: {player_pet.current_hp}/{player_pet.max_hp}, 能量: {player_pet.current_energy})")
    print(f"对手: {opponent_pet.template.name} (HP: {opponent_pet.current_hp}/{opponent_pet.max_hp}, 能量: {opponent_pet.current_energy})")
    print()

    # 分析状态
    print(f"正在分析（搜索深度={args.depth}）...")
    result = engine.analyze_state(state, depth=args.depth)

    print(f"\n搜索了 {result['nodes_searched']} 个节点")
    print(f"局面评分: {result['evaluation']:.1f}")

    if result['best_action']:
        print(f"\n最佳行动: {result['best_action']}")

    print(f"\n所有可能的行动 ({len(result['all_actions'])} 个):")
    for i, action in enumerate(result['all_actions'], 1):
        print(f"  {i}. {action}")


if __name__ == '__main__':
    main()
