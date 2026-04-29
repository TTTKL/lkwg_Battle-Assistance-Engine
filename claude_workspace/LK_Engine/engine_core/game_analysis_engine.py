"""
游戏分析引擎
提供输入状态、输出最佳行动的主接口
"""
from dataclasses import replace
from typing import Dict, List, Optional, Tuple
from core.models import (
    BattleState, Action, PetInstance, PlayerState,
    PetTemplate, Skill, StatModifier
)
from data_loader import DataLoader
from engine.extended_battle_engine import ExtendedBattleEngine
from engine.battle_engine import BattleEngine
from engine.evaluator import Evaluator
from engine.search_engine import SearchEngine
from engine.action_generator import ActionGenerator


class GameAnalysisEngine:
    """游戏分析引擎"""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_loader = DataLoader(data_dir)
        self.data_loader.load_all()

        # 使用扩展引擎（含状态效果、印记、特性、技能效果等完整机制）
        self.battle_engine = ExtendedBattleEngine(self.data_loader)
        self.evaluator = Evaluator(self.data_loader)
        self.search_engine = SearchEngine(self.battle_engine, self.evaluator)
        self.action_generator = ActionGenerator()

    def analyze_state(self, state: BattleState, depth: int = 4,
                      opponent_action_weights=None,
                      confidence: float = 0.0,
                      time_limit: float = 1.0) -> Dict:
        """
        分析当前状态，返回最佳行动、局面评估和全行动评分

        Args:
            state: 当前对战状态
            depth: 搜索深度（默认2）
            opponent_action_weights: 对手行为概率分布（暗箱模式）
            confidence: 对手预测置信度（0~1）

        Returns:
            {
                'best_action': 最佳行动,
                'evaluation': 局面评分,
                'win_rate': 胜率估算 (0.0~1.0),
                'all_actions': 所有可能的行动列表,
                'action_scores': 每个行动的详细分数 [{action, score, win_rate}, ...],
                'nodes_searched': 搜索的节点数
            }
        """
        # 获取所有可能的行动
        all_actions = self.action_generator.generate_actions(state, True)

        # 搜索最佳行动
        best_action, evaluation = self.search_engine.find_best_action(
            state, depth,
            opponent_action_weights=opponent_action_weights,
            confidence=confidence,
            time_limit=time_limit,
        )

        # 获取所有行动的详细评分
        scored_actions = self.search_engine.score_all_actions(
            state, max(1, depth - 1),  # 全行动评分用浅一层以节省时间
            opponent_action_weights=opponent_action_weights,
            confidence=confidence,
            time_limit=max(0.3, time_limit * 0.3),
        )

        # 转换为胜率
        from engine.evaluator import Evaluator
        win_rate = Evaluator.evaluation_to_win_rate(evaluation)

        action_scores = []
        for action, score in scored_actions:
            action_scores.append({
                'action': action,
                'score': score,
                'win_rate': Evaluator.evaluation_to_win_rate(score),
            })

        return {
            'best_action': best_action,
            'evaluation': evaluation,
            'win_rate': win_rate,
            'all_actions': all_actions,
            'action_scores': action_scores,
            'nodes_searched': self.search_engine.nodes_searched
        }

    def get_all_next_states(self, state: BattleState) -> List[Tuple[Action, Action, BattleState]]:
        """
        获取所有可能的下一步状态

        Args:
            state: 当前对战状态

        Returns:
            [(玩家行动, 对手行动, 新状态), ...]
        """
        player_actions = self.action_generator.generate_actions(state, True)
        opponent_actions = self.action_generator.generate_actions(state, False)

        next_states = []
        for player_action in player_actions:
            for opponent_action in opponent_actions:
                new_state = self.battle_engine.apply_action(
                    state, player_action, opponent_action
                )
                next_states.append((player_action, opponent_action, new_state))

        return next_states

    def create_pet_instance(self, pet_name: str, skill_names: List[str],
                           hp_percent: float = 1.0, energy: int = 10,
                           bloodline: Optional[str] = None,
                           ivs: Optional[Dict[str, int]] = None,
                           nature: Optional[str] = None) -> Optional[PetInstance]:
        """
        创建精灵实例

        Args:
            pet_name: 精灵名称
            skill_names: 技能名称列表（最多4个）
            hp_percent: HP百分比（0-1）
            energy: 当前能量

        Returns:
            精灵实例
        """
        if pet_name not in self.data_loader.pets:
            return None

        template = self.data_loader.pets[pet_name]
        if bloodline is not None:
            template = replace(
                template,
                bloodline=self.data_loader._normalize_bloodline(bloodline),
            )

        # 获取技能
        skills = []
        for skill_name in skill_names[:4]:
            if skill_name in self.data_loader.skills:
                skills.append(self.data_loader.skills[skill_name])

        # 计算实际属性：与前端 common.json 的个体/性格公式保持一致。
        stats = self.data_loader.calc_actual_stats(
            template.stats.copy(),
            ivs=ivs,
            nature_name=nature,
        )
        max_hp = stats.get('生命', 100)
        current_hp = int(max_hp * hp_percent)

        return PetInstance(
            template=template,
            current_hp=current_hp,
            max_hp=max_hp,
            stats=stats,
            skills=skills,
            current_energy=energy,
            stat_modifiers=StatModifier(),
            skill_cooldowns={},
            is_alive=current_hp > 0
        )

    def create_battle_state(self, player_team: List[PetInstance],
                           opponent_team: List[PetInstance],
                           player_active_index: int = 0,
                           opponent_active_index: int = 0,
                           player_team_state: 'TeamState | None' = None,
                           opponent_team_state: 'TeamState | None' = None) -> BattleState:
        """
        创建对战状态

        Args:
            player_team: 玩家队伍
            opponent_team: 对手队伍
            player_active_index: 玩家当前出战精灵索引
            opponent_active_index: 对手当前出战精灵索引
            player_team_state: 玩家队伍状态（首领化/愿力冲击次数等），None 时使用默认值
            opponent_team_state: 对手队伍状态，None 时使用默认值

        Returns:
            对战状态
        """
        player_state = PlayerState(team=player_team, active_index=player_active_index)
        opponent_state = PlayerState(team=opponent_team, active_index=opponent_active_index)

        if player_team_state is not None:
            player_state.team_state = player_team_state
        if opponent_team_state is not None:
            opponent_state.team_state = opponent_team_state

        return BattleState(
            player=player_state,
            opponent=opponent_state,
            turn=1,
            weather=None,
            field_effects={}
        )
