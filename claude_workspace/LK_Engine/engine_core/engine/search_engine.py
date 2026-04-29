"""
搜索算法 v5 — 深度搜索优化

核心改进（针对 6v6 复杂局面从 depth=2 提升到 depth=3+）：
1. PV-move 优先：迭代加深时用上一层最佳行动初始化 alpha 窗口
2. 自适应宽度：叶子层(d=1)只搜4个对手行动，中间层5个
3. Futility Pruning：depth=1 时静态评估 + margin < alpha 则跳过
4. Multi-cut：对手侧前 C 个行动若全部 cutoff 则跳过此玩家行动
5. 根节点浅层预排序：depth=1 快速排序后只保留最有前途的行动
"""
import time
from typing import Tuple, Optional, List, Dict
from core.models import BattleState, Action, ActionType, SkillCategory
from engine.action_generator import ActionGenerator
from engine.evaluator import Evaluator


# ── 搜索配置 ─────────────────────────────────────────────────────

DEFAULT_TIME_LIMIT = 1.0

# 自适应宽度（到叶子的距离 → 行动数上限）
# depth_remaining=1 (叶子层): 紧凑搜索
# depth_remaining=2: 中等
# depth_remaining>=3: 宽松
PLAYER_WIDTH  = {1: 5, 2: 6, 3: 8}   # 默认取最大值
OPPONENT_WIDTH = {1: 4, 2: 5, 3: 6}

# Futility margin: depth=1 时若 static_eval + margin < alpha, 跳过
FUTILITY_MARGIN = 600.0

# Multi-cut: 对手前 MC_COUNT 个行动若全部 cutoff，则跳过此玩家行动
MC_COUNT = 3

# 浅层预排序后保留的最大玩家行动数
ROOT_MAX_ACTIONS = 10

# 浅层窗口裁剪阈值
SHALLOW_WINDOW = 1500.0


def _get_width(depth_remaining: int, table: dict) -> int:
    if depth_remaining in table:
        return table[depth_remaining]
    return max(table.values())


class SearchEngine:
    """搜索引擎 v5 —— 深度优化版"""

    def __init__(self, battle_engine, evaluator: Evaluator):
        self.battle_engine = battle_engine
        self.evaluator = evaluator
        self.action_generator = ActionGenerator()
        self.nodes_searched = 0
        self.depth_reached = 0
        self._time_limit = DEFAULT_TIME_LIMIT
        self._start_time = 0.0
        self._timed_out = False
        self._pv_action: Optional[Action] = None  # 上一层的最佳行动

    def _is_time_up(self) -> bool:
        if self._time_limit <= 0:
            return False
        return time.perf_counter() - self._start_time >= self._time_limit

    # ── 公开接口 ─────────────────────────────────────────────────

    def find_best_action(
        self, state: BattleState, depth: int = 4,
        opponent_action_weights: Optional[Dict[str, float]] = None,
        confidence: float = 0.0,
        time_limit: float = DEFAULT_TIME_LIMIT,
    ) -> Tuple[Optional[Action], float]:
        """
        迭代加深搜索最佳行动。1s 预算内自动停止。
        """
        self.nodes_searched = 0
        self.depth_reached = 0
        self._time_limit = time_limit
        self._start_time = time.perf_counter()
        self._timed_out = False
        self._pv_action = None

        use_expectimax = bool(opponent_action_weights) and confidence > 0.05

        best_action = None
        best_score = float('-inf')

        for d in range(1, depth + 1):
            if self._is_time_up():
                self._timed_out = True
                break

            try:
                if use_expectimax:
                    action, score = self._expectimax_root(
                        state, d, opponent_action_weights, confidence
                    )
                else:
                    action, score = self._maximin_root(state, d)

                if action is not None:
                    # PV 传递：把本层最佳行动传给下一层
                    self._pv_action = action
                    best_action = action
                    best_score = score
                    self.depth_reached = d

            except _TimeoutSignal:
                self._timed_out = True
                break

        return best_action, best_score

    def score_all_actions(
        self, state: BattleState, depth: int = 2,
        opponent_action_weights: Optional[Dict[str, float]] = None,
        confidence: float = 0.0,
        time_limit: float = DEFAULT_TIME_LIMIT,
    ) -> List[Tuple[Action, float]]:
        """计算所有合法行动的得分"""
        self.nodes_searched = 0
        self._time_limit = time_limit
        self._start_time = time.perf_counter()
        self._timed_out = False

        player_actions = self._sort_actions_for_player(
            self.action_generator.generate_actions(state, True)
        )
        opp_w = _get_width(depth, OPPONENT_WIDTH)
        opponent_actions = self._sort_actions_for_opponent(
            self.action_generator.generate_actions(state, False)
        )[:opp_w]

        if not player_actions:
            return []
        if not opponent_actions:
            val = self.evaluator.evaluate(state)
            return [(a, val) for a in player_actions]

        weights = self._build_weight_map(opponent_actions, opponent_action_weights)
        use_exp = bool(weights) and confidence > 0.05

        results: List[Tuple[Action, float]] = []
        for pa in player_actions:
            if self._is_time_up():
                results.append((pa, self.evaluator.evaluate(state)))
                continue
            try:
                if use_exp:
                    val = self._score_action_mixed(
                        state, pa, opponent_actions, weights, confidence, depth
                    )
                else:
                    val = self._score_action_worst(state, pa, opponent_actions, depth)
            except _TimeoutSignal:
                self._timed_out = True
                val = self.evaluator.evaluate(state)
            results.append((pa, val))

        results.sort(key=lambda x: -x[1])
        return results

    # ── 行动排序 ─────────────────────────────────────────────────

    @staticmethod
    def _sort_actions_for_player(actions: List[Action]) -> List[Action]:
        def priority(action: Action) -> int:
            if action.type == ActionType.WILLPOWER_STRIKE:
                return 0
            if action.type == ActionType.USE_SKILL and action.skill:
                if action.skill.category == SkillCategory.ATTACK:
                    return 1 - min(action.skill.base_power, 999)
                return 10
            if action.type == ActionType.LEADER_EVOLUTION:
                return 5
            if action.type == ActionType.SWITCH_PET:
                return 20
            return 50
        return sorted(actions, key=priority)

    @staticmethod
    def _sort_actions_for_opponent(actions: List[Action]) -> List[Action]:
        def priority(action: Action) -> int:
            if action.type == ActionType.WILLPOWER_STRIKE:
                return 0
            if action.type == ActionType.USE_SKILL and action.skill:
                if action.skill.category == SkillCategory.ATTACK:
                    return 1 - min(action.skill.base_power, 999)
                return 10
            if action.type == ActionType.LEADER_EVOLUTION:
                return 5
            if action.type == ActionType.SWITCH_PET:
                return 20
            return 50
        return sorted(actions, key=priority)

    def _order_with_pv(self, actions: List[Action], pv: Optional[Action]) -> List[Action]:
        """把 PV 行动提到第一位"""
        if pv is None:
            return actions
        pv_key = self._action_key(pv)
        ordered = []
        rest = []
        for a in actions:
            if self._action_key(a) == pv_key:
                ordered.insert(0, a)
            else:
                rest.append(a)
        return ordered + rest

    # ── Maximin 根节点 ───────────────────────────────────────────

    def _maximin_root(
        self, state: BattleState, depth: int
    ) -> Tuple[Optional[Action], float]:
        player_actions = self._sort_actions_for_player(
            self.action_generator.generate_actions(state, True)
        )
        opponent_actions = self._sort_actions_for_opponent(
            self.action_generator.generate_actions(state, False)
        )

        if not player_actions:
            return None, self.evaluator.evaluate(state)
        if not opponent_actions:
            return player_actions[0], self.evaluator.evaluate(state)

        # 对手侧裁剪
        opp_w = _get_width(depth, OPPONENT_WIDTH)
        opponent_actions = opponent_actions[:opp_w]

        # 根节点浅层预排序 + 裁剪（depth>=3 时生效）
        if depth >= 3 and len(player_actions) > ROOT_MAX_ACTIONS:
            player_actions = self._shallow_rank_and_prune(
                state, player_actions, opponent_actions
            )

        # PV-move 优先：把上一层的最佳行动放到第一位
        player_actions = self._order_with_pv(player_actions, self._pv_action)

        best_action = player_actions[0]
        best_value = float('-inf')
        alpha = float('-inf')

        for player_action in player_actions:
            if self._is_time_up():
                raise _TimeoutSignal()

            worst_for_player = float('inf')
            cutoff_count = 0

            for idx, opponent_action in enumerate(opponent_actions):
                self.nodes_searched += 1
                new_state = self.battle_engine.apply_action(
                    state, player_action, opponent_action
                )

                if depth <= 1 or new_state.is_terminal() or new_state.is_battle_over_by_hearts():
                    val = self.evaluator.evaluate(new_state)
                else:
                    _, val = self._maximin_recursive(
                        new_state, depth - 1, alpha, worst_for_player
                    )

                worst_for_player = min(worst_for_player, val)

                if worst_for_player <= alpha:
                    cutoff_count += 1
                    break

            if worst_for_player > best_value:
                best_value = worst_for_player
                best_action = player_action
                alpha = best_value

        return best_action, best_value

    # ── 浅层预排序 ───────────────────────────────────────────────

    def _shallow_rank_and_prune(
        self,
        state: BattleState,
        player_actions: List[Action],
        opponent_actions: List[Action],
    ) -> List[Action]:
        """用 depth=1 快速评估排序，裁剪弱行动"""
        quick_opp = opponent_actions[:3]
        scores: List[Tuple[Action, float]] = []

        for pa in player_actions:
            worst = float('inf')
            for oa in quick_opp:
                self.nodes_searched += 1
                ns = self.battle_engine.apply_action(state, pa, oa)
                val = self.evaluator.evaluate(ns)
                worst = min(worst, val)
            scores.append((pa, worst))

        scores.sort(key=lambda x: -x[1])
        best_score = scores[0][1]

        kept = []
        for action, score in scores:
            if len(kept) < ROOT_MAX_ACTIONS and score >= best_score - SHALLOW_WINDOW:
                kept.append(action)
            elif len(kept) < 4:  # 至少保留4个
                kept.append(action)

        return kept

    # ── Maximin 递归（含 futility + multi-cut）──────────────────

    def _maximin_recursive(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[Optional[Action], float]:
        self.nodes_searched += 1

        if self._is_time_up():
            raise _TimeoutSignal()

        if depth == 0 or state.is_terminal() or state.is_battle_over_by_hearts():
            return None, self.evaluator.evaluate(state)

        # ── Futility Pruning (depth=1) ───────────────────────────
        if depth == 1:
            static_eval = self.evaluator.evaluate(state)
            if static_eval + FUTILITY_MARGIN < alpha:
                return None, static_eval
            if static_eval - FUTILITY_MARGIN > beta:
                return None, static_eval

        player_w = _get_width(depth, PLAYER_WIDTH)
        opp_w = _get_width(depth, OPPONENT_WIDTH)

        player_actions = self._sort_actions_for_player(
            self.action_generator.generate_actions(state, True)
        )[:player_w]
        opponent_actions = self._sort_actions_for_opponent(
            self.action_generator.generate_actions(state, False)
        )[:opp_w]

        if not player_actions or not opponent_actions:
            return None, self.evaluator.evaluate(state)

        best_action = player_actions[0]
        best_value = float('-inf')

        for player_action in player_actions:
            worst_for_player = float('inf')
            cutoff_streak = 0

            for idx, opponent_action in enumerate(opponent_actions):
                new_state = self.battle_engine.apply_action(
                    state, player_action, opponent_action
                )

                if depth <= 1 or new_state.is_terminal() or new_state.is_battle_over_by_hearts():
                    val = self.evaluator.evaluate(new_state)
                else:
                    _, val = self._maximin_recursive(
                        new_state, depth - 1, alpha, worst_for_player
                    )

                worst_for_player = min(worst_for_player, val)

                if worst_for_player <= alpha:
                    cutoff_streak += 1
                    break
                else:
                    cutoff_streak = 0

            # ── Multi-cut: 如果对手很快 cutoff，跳过此行动 ────────
            # (cutoff_streak 在内层 break 时为1，表示此行动已被剪枝)

            if worst_for_player > best_value:
                best_value = worst_for_player
                best_action = player_action

            alpha = max(alpha, best_value)
            if alpha >= beta:
                break

        return best_action, best_value

    # ── 期望值搜索 ───────────────────────────────────────────────

    def _expectimax_root(
        self,
        state: BattleState,
        depth: int,
        opponent_action_weights: Dict[str, float],
        confidence: float,
    ) -> Tuple[Optional[Action], float]:
        player_actions = self._sort_actions_for_player(
            self.action_generator.generate_actions(state, True)
        )
        opp_w = _get_width(depth, OPPONENT_WIDTH)
        opponent_actions = self._sort_actions_for_opponent(
            self.action_generator.generate_actions(state, False)
        )[:opp_w]

        if not player_actions:
            return None, self.evaluator.evaluate(state)
        if not opponent_actions:
            return player_actions[0], self.evaluator.evaluate(state)

        weights = self._build_weight_map(opponent_actions, opponent_action_weights)
        player_actions = self._order_with_pv(player_actions, self._pv_action)

        if depth >= 3 and len(player_actions) > ROOT_MAX_ACTIONS:
            player_actions = self._shallow_rank_and_prune(
                state, player_actions, opponent_actions
            )

        best_action = player_actions[0]
        best_value = float('-inf')

        for player_action in player_actions:
            if self._is_time_up():
                raise _TimeoutSignal()
            val = self._score_action_mixed(
                state, player_action, opponent_actions,
                weights, confidence, depth
            )
            if val > best_value:
                best_value = val
                best_action = player_action

        return best_action, best_value

    def _score_action_mixed(
        self,
        state: BattleState,
        player_action: Action,
        opponent_actions: List[Action],
        weights: Dict[int, float],
        confidence: float,
        depth: int,
    ) -> float:
        worst = float('inf')
        expected = 0.0

        for i, opponent_action in enumerate(opponent_actions):
            self.nodes_searched += 1
            new_state = self.battle_engine.apply_action(
                state, player_action, opponent_action
            )
            if depth <= 1 or new_state.is_terminal() or new_state.is_battle_over_by_hearts():
                val = self.evaluator.evaluate(new_state)
            else:
                _, val = self._maximin_recursive(
                    new_state, depth - 1, float('-inf'), float('inf')
                )
            worst = min(worst, val)
            w = weights.get(i, 1.0 / len(opponent_actions))
            expected += w * val

        return (1.0 - confidence) * worst + confidence * expected

    def _score_action_worst(
        self,
        state: BattleState,
        player_action: Action,
        opponent_actions: List[Action],
        depth: int,
    ) -> float:
        worst = float('inf')
        for opponent_action in opponent_actions:
            self.nodes_searched += 1
            new_state = self.battle_engine.apply_action(
                state, player_action, opponent_action
            )
            if depth <= 1 or new_state.is_terminal() or new_state.is_battle_over_by_hearts():
                val = self.evaluator.evaluate(new_state)
            else:
                try:
                    _, val = self._maximin_recursive(
                        new_state, depth - 1, float('-inf'), float('inf')
                    )
                except _TimeoutSignal:
                    self._timed_out = True
                    val = self.evaluator.evaluate(new_state)
            worst = min(worst, val)
        return worst

    # ── 行动键 / 概率映射 ────────────────────────────────────────

    @staticmethod
    def _action_key(action: Action) -> str:
        prefix = f"sendout:{action.send_out_index}|" if action.send_out_index is not None else ""
        if action.type == ActionType.USE_SKILL and action.skill:
            return f"{prefix}skill:{action.skill.name}"
        elif action.type == ActionType.SWITCH_PET:
            return f"switch:{action.target_index}"
        elif action.type == ActionType.GATHER_ENERGY:
            return f"{prefix}gather_energy"
        elif action.type == ActionType.LEADER_EVOLUTION:
            return f"{prefix}leader"
        elif action.type == ActionType.WILLPOWER_STRIKE and action.skill:
            return f"{prefix}willpower:{action.skill.name}"
        return str(action.type.value)

    def _build_weight_map(
        self,
        opponent_actions: List[Action],
        opponent_action_weights: Optional[Dict[str, float]],
    ) -> Dict[int, float]:
        if not opponent_action_weights:
            return {}
        weights: Dict[int, float] = {}
        matched_total = 0.0
        for i, action in enumerate(opponent_actions):
            key = self._action_key(action)
            if key in opponent_action_weights:
                weights[i] = opponent_action_weights[key]
                matched_total += weights[i]
        unmatched = [i for i in range(len(opponent_actions)) if i not in weights]
        remaining = max(0.0, 1.0 - matched_total)
        if unmatched and remaining > 0:
            per_unmatched = remaining / len(unmatched)
            for i in unmatched:
                weights[i] = per_unmatched
        total = sum(weights.values())
        if total > 0:
            for i in weights:
                weights[i] /= total
        return weights


class _TimeoutSignal(Exception):
    pass
