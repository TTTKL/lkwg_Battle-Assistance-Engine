"""
REST API接口
提供HTTP接口用于游戏状态分析

可作为独立 Flask 服务运行（python api.py），
也可被 Calculator/server.py 导入蓝图 (engine_bp) 嵌入到统一服务中。
"""
import copy
import logging
from flask import Flask, Blueprint, request, jsonify, render_template
from typing import Dict, List, Optional
from agent_runtime.core.events import EventSource, EventType
from agent_runtime.engine.recommendation_service import RecommendationService
from agent_runtime.tracker.session_manager import BattleSessionConfig, BattleSessionManager
from game_analysis_engine import GameAnalysisEngine
from core.models import BattleState, Action, ActionType, TeamState
from engine.slot_effects import SlotEffectsProcessor
from engine.energy_costs import compute_effective_skill_energy_cost, can_pay_skill_energy_cost


# ---- 引擎单例 (导入时初始化一次) ----
engine = GameAnalysisEngine()
runtime_session_manager = BattleSessionManager()
runtime_recommendation_service = RecommendationService()
logger = logging.getLogger(__name__)

HIDDEN_IV_BASE_PROFILE = {
    'min': 0,
    'max': 10,
    'expected': 7.6,
    'low_chance': 0.22,
}

HIDDEN_IV_STAT_KEYS = {
    '速度': ('speedIvMin', 'speedIvMax'),
    '物攻': ('atkIvMin', 'atkIvMax'),
    '魔攻': ('matkIvMin', 'matkIvMax'),
    '物防': ('defIvMin', 'defIvMax'),
    '魔防': ('mdefIvMin', 'mdefIvMax'),
}


# ---- Blueprint: 所有引擎路由 ----
engine_bp = Blueprint(
    'engine', __name__,
    template_folder='templates',
    static_folder='static',
)


@engine_bp.errorhandler(400)
def _handle_bad_request(e):
    """捕获 Flask/Werkzeug 在解析请求体时抛出的 400 BadRequest。"""
    return jsonify({
        'error': f'请求格式错误: {e.description}',
        'hint': '请检查 JSON 请求体是否完整、格式是否正确',
    }), 400


def _safe_runtime_recommendation(session_id: str, depth: Optional[int] = None):
    try:
        session = runtime_session_manager.get_session(session_id)
        actual_depth = depth if depth is not None else session.config.search_depth
        recommendation = runtime_recommendation_service.recommend(session, depth=actual_depth)
        return {
            'best_action': recommendation.best_action,
            'score': recommendation.score,
            'confidence': recommendation.confidence,
            'analysis_depth': actual_depth,
            'inference_mode': session.config.inference_mode,
            'confidence_breakdown': recommendation.confidence_breakdown,
            'alternatives': recommendation.alternatives,
            'risk_notes': recommendation.risk_notes,
            'assumptions': recommendation.based_on_assumptions,
        }
    except Exception:
        return None


@engine_bp.route('/runtime-console', methods=['GET'])
def runtime_console():
    """极简实时对战控制台。"""
    return render_template('runtime_console.html')


@engine_bp.route('/api/analyze', methods=['POST'])
def analyze_state():
    """
    分析当前状态，返回最佳行动

    请求体:
    {
        "player_team": [
            {
                "name": "火神",
                "skills": ["火焰喷射", "猛烈撞击"],
                "hp_percent": 0.8,
                "energy": 7
            }
        ],
        "opponent_team": [...],
        "player_active_index": 0,
        "opponent_active_index": 0,
        "depth": 2
    }

    返回:
    {
        "best_action": {
            "type": "use_skill",
            "skill_name": "火焰喷射"
        },
        "evaluation": 150.5,
        "all_actions": [...],
        "nodes_searched": 1234
    }
    """
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': '无法解析请求 JSON，请检查请求体格式'}), 400

        # 创建玩家队伍 / 对手队伍
        player_team, opponent_team, hidden_meta = _build_request_teams(data)

        # 解析队伍状态（首领化/愿力冲击选择）
        player_team_state = _parse_team_state(data.get('player_team_state'))
        opponent_team_state = _parse_team_state(data.get('opponent_team_state'))

        # 创建对战状态
        state = engine.create_battle_state(
            player_team=player_team,
            opponent_team=opponent_team,
            player_active_index=data.get('player_active_index', 0),
            opponent_active_index=data.get('opponent_active_index', 0),
            player_team_state=player_team_state,
            opponent_team_state=opponent_team_state,
        )
        state.turn = max(1, int(data.get('turn', state.turn)))
        state.turn_prepared = bool(data.get('turn_prepared', False))

        # 分析状态
        depth = data.get('depth', 2)
        result = engine.analyze_state(state, depth)
        display_state, display_player_actions, display_opponent_actions = _build_display_state_and_actions(state)
        action_panels = _build_action_panels(display_state, display_player_actions, display_opponent_actions)

        # 格式化返回结果
        best_action = result['best_action']
        response = {
            'best_action': _format_action(best_action) if best_action else None,
            'evaluation': result['evaluation'],
            'win_rate': result.get('win_rate', 0.5),
            'action_scores': [
                {
                    'action': _format_action(item['action']),
                    'score': item['score'],
                    'win_rate': item['win_rate'],
                }
                for item in result.get('action_scores', [])
            ],
            'all_actions': [_format_action(a) for a in display_player_actions],
            'opponent_all_actions': [_format_action(a) for a in display_opponent_actions],
            'action_panels': action_panels,
            'nodes_searched': result['nodes_searched'],
            'state': _format_state(display_state),
        }
        if hidden_meta is not None:
            response['hidden_analysis'] = hidden_meta

        return jsonify(response)

    except Exception as e:
        import traceback
        logger.warning('[analyze] 400 error: %s\n%s', e, traceback.format_exc())
        return jsonify({'error': str(e)}), 400


def _parse_action_payload(action_data: Dict, state: BattleState, is_player: bool) -> Action:
    """将前端 action payload 解析为引擎 Action。"""
    if not action_data or 'type' not in action_data:
        raise ValueError('缺少行动信息')

    action_type = action_data['type']
    pet_state = state.player if is_player else state.opponent
    active_pet = pet_state.get_active_pet()
    send_out_index = action_data.get('send_out_index')
    selected_pet = active_pet
    if send_out_index is not None:
        send_out_index = int(send_out_index)
        if 0 <= send_out_index < len(pet_state.team):
            selected_pet = pet_state.team[send_out_index]

    if action_type == 'use_skill':
        skill_name = action_data.get('skill_name')
        if not skill_name:
            raise ValueError('技能行动缺少 skill_name')
        for skill in selected_pet.skills:
            if skill.name == skill_name:
                return Action(ActionType.USE_SKILL, skill=skill, send_out_index=send_out_index)
        raise ValueError(f'当前精灵不存在技能: {skill_name}')

    if action_type == 'switch_pet':
        target_index = action_data.get('target_index')
        if target_index is None:
            raise ValueError('换宠行动缺少 target_index')
        return Action(ActionType.SWITCH_PET, target_index=int(target_index))

    if action_type == 'leader_evolution':
        return Action(ActionType.LEADER_EVOLUTION, send_out_index=send_out_index)

    if action_type == 'willpower_strike':
        skill_name = action_data.get('skill_name')
        if not skill_name:
            raise ValueError('愿力冲击缺少 skill_name')
        for skill in selected_pet.skills:
            if skill.name == skill_name:
                return Action(ActionType.WILLPOWER_STRIKE, skill=skill, send_out_index=send_out_index)
        raise ValueError(f'当前精灵不存在愿力技能: {skill_name}')

    if action_type == 'gather_energy':
        return Action(ActionType.GATHER_ENERGY, send_out_index=send_out_index)

    raise ValueError(f'未知行动类型: {action_type}')


def _build_illegal_action_error(
    state: BattleState,
    desired_action: Action,
    is_player: bool,
) -> Optional[Dict]:
    """
    在真正结算前，按引擎当前回合开始阶段的合法行动集校验一次。
    用于识别“网页端仍在提交旧槽位技能”的情况，并返回显式错误。
    """
    validation_state = state.copy()
    legal_actions = engine.action_generator.generate_actions(validation_state, is_player)

    desired_key = _format_action(desired_action)
    legal_keys = [_format_action(action) for action in legal_actions]
    if desired_key in legal_keys:
        return None

    active_pet = (validation_state.player if is_player else validation_state.opponent).get_active_pet()
    side_label = 'player' if is_player else 'opponent'
    current_skill_order = [skill.name for skill in active_pet.skills] if active_pet else []
    legal_skill_names = [
        action.skill.name
        for action in legal_actions
        if action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE) and action.skill
    ]

    action_name = None
    if desired_action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE) and desired_action.skill:
        action_name = desired_action.skill.name

    return {
        'error': '提交的行动在当前回合开始阶段不合法，可能是前端仍在提交旧槽位技能。',
        'error_code': 'ILLEGAL_ACTION_FOR_CURRENT_TURN_STATE',
        'side': side_label,
        'submitted_action': desired_key,
        'submitted_skill_name': action_name,
        'current_skill_order': current_skill_order,
        'legal_actions': legal_keys,
        'legal_skill_names': legal_skill_names,
    }


def _log_illegal_action(error_payload: Dict, state: BattleState, request_data: Optional[Dict] = None) -> None:
    try:
        logger.warning(
            "Illegal action rejected: side=%s submitted=%s current_order=%s legal_skills=%s turn=%s request_actions=%s",
            error_payload.get('side'),
            error_payload.get('submitted_action'),
            error_payload.get('current_skill_order'),
            error_payload.get('legal_skill_names'),
            state.turn,
            {
                'player_action': (request_data or {}).get('player_action'),
                'opponent_action': (request_data or {}).get('opponent_action'),
            },
        )
    except Exception:
        logger.exception("Failed to write illegal action log")


def _build_display_state_and_actions(state: BattleState):
    """
    生成用于前端展示/选招的状态。
    对会在回合开始改变槽位的机制，前端应看到“下一拍真正可选”的顺序，
    因此这里基于拷贝先跑一遍行动生成以触发 turn-start prepare。
    """
    display_state = state.copy()
    player_actions = engine.action_generator.generate_actions(display_state, True)
    opponent_actions = engine.action_generator.generate_actions(display_state, False)
    return display_state, player_actions, opponent_actions


def _build_action_panels(state: BattleState, player_actions: List[Action], opponent_actions: List[Action]) -> Dict:
    """为前端返回结构化行动面板，减少网页端本地规则计算。"""
    return {
        'player': _build_action_panel(state, True, player_actions),
        'opponent': _build_action_panel(state, False, opponent_actions),
    }


def _normalize_skill_names(raw_skills) -> List[str]:
    normalized: List[str] = []
    for item in raw_skills or []:
        skill_name = None
        if isinstance(item, str):
            skill_name = item
        elif isinstance(item, dict):
            skill_name = item.get('name')
        if skill_name and skill_name not in normalized:
            normalized.append(skill_name)
    return normalized


def _build_hidden_observation_map(observations: Optional[List[Dict]]) -> Dict[str, Dict]:
    observation_map: Dict[str, Dict] = {}
    for entry in observations or []:
        if not isinstance(entry, dict):
            continue
        keys = []
        pet_name = entry.get('pet_name')
        if pet_name:
            keys.append(f'name:{pet_name}')
        team_slot = entry.get('team_slot')
        if team_slot is not None:
            try:
                keys.append(f'slot:{int(team_slot)}')
            except (TypeError, ValueError):
                pass
        for key in keys:
            observation_map[key] = entry
    return observation_map


def _pick_hidden_observation(observation_map: Dict[str, Dict], pet_name: str, team_slot: int) -> Optional[Dict]:
    return (
        observation_map.get(f'slot:{team_slot}')
        or observation_map.get(f'name:{pet_name}')
    )


def _score_hidden_candidate_skill(skill_name: str, pet_types: List[str], active_energy: Optional[int]) -> float:
    skill = engine.data_loader.skills.get(skill_name)
    if skill is None:
        return -1e9

    score = 0.0
    damage_type = getattr(skill, 'damage_type', None)
    category = getattr(skill, 'category', None)
    category_value = category.value if hasattr(category, 'value') else str(category or '')

    if damage_type is not None:
        score += float(getattr(skill, 'base_power', 0) or 0)
    if category_value == 'status':
        score += 35.0
    elif category_value == 'defense':
        score += 20.0
    if getattr(skill, 'element', None) in (pet_types or []):
        score += 8.0
    if active_energy is not None:
        if skill.energy_cost <= active_energy:
            score += 12.0
        elif skill.energy_cost <= active_energy + 2:
            score += 4.0
    score -= float(getattr(skill, 'energy_cost', 0) or 0) * 6.0
    return score


def _build_hidden_skill_payloads(
    pet_name: str,
    observed_skills: List[str],
    active_energy: Optional[int],
) -> List[Dict]:
    template = engine.data_loader.pets.get(pet_name)
    if template is None:
        return [{'name': skill_name} for skill_name in observed_skills[:4]]

    learnable_skills = _normalize_skill_names(getattr(template, 'learnable_skills', []))
    pet_types = list(getattr(template, 'types', []) or [])
    chosen: List[str] = []

    for skill_name in observed_skills:
        if skill_name and skill_name not in chosen:
            chosen.append(skill_name)
        if len(chosen) >= 4:
            return [{'name': skill_name} for skill_name in chosen[:4]]

    ranked = sorted(
        [skill_name for skill_name in learnable_skills if skill_name not in chosen],
        key=lambda skill_name: _score_hidden_candidate_skill(skill_name, pet_types, active_energy),
        reverse=True,
    )
    for skill_name in ranked:
        chosen.append(skill_name)
        if len(chosen) >= 4:
            break
    return [{'name': skill_name} for skill_name in chosen[:4]]


def _resolve_hidden_iv_projection(iv_constraints: Optional[Dict]) -> Dict:
    constraints = iv_constraints if isinstance(iv_constraints, dict) else {}
    profile_min = HIDDEN_IV_BASE_PROFILE['min']
    profile_max = HIDDEN_IV_BASE_PROFILE['max']

    for min_key, max_key in HIDDEN_IV_STAT_KEYS.values():
        lower = constraints.get(min_key)
        upper = constraints.get(max_key)
        if lower is None or upper is None:
            continue
        try:
            lower_value = max(0, min(10, int(lower)))
            upper_value = max(0, min(10, int(upper)))
        except (TypeError, ValueError):
            continue
        if lower_value > upper_value:
            lower_value, upper_value = upper_value, lower_value
        profile_min = max(profile_min, lower_value)
        profile_max = min(profile_max, upper_value)

    if profile_min > profile_max:
        profile_min = HIDDEN_IV_BASE_PROFILE['min']
        profile_max = HIDDEN_IV_BASE_PROFILE['max']

    iv_map = {'生命': int(round((profile_min + profile_max) / 2))}
    for stat_name, (min_key, max_key) in HIDDEN_IV_STAT_KEYS.items():
        lower = constraints.get(min_key)
        upper = constraints.get(max_key)
        try:
            lower_value = max(profile_min, int(lower)) if lower is not None else profile_min
            upper_value = min(profile_max, int(upper)) if upper is not None else profile_max
        except (TypeError, ValueError):
            lower_value = profile_min
            upper_value = profile_max
        if lower_value > upper_value:
            lower_value, upper_value = profile_min, profile_max
        iv_map[stat_name] = int(round((lower_value + upper_value) / 2))

    if profile_min >= 8:
        low_chance = 0.0
    elif profile_max <= 7:
        low_chance = 1.0
    else:
        low_chance = min(
            HIDDEN_IV_BASE_PROFILE['low_chance'],
            (7 - profile_min + 1) / max(1, profile_max - profile_min + 1),
        )

    return {
        'iv_map': iv_map,
        'profile': {
            'min': profile_min,
            'max': profile_max,
            'expected': round((profile_min + profile_max) / 2, 2),
            'low_chance': round(low_chance, 4),
        },
        'iv_constraints': constraints,
    }


def _build_hidden_stat_projection(pet_name: str, iv_projection: Dict) -> Dict:
    template = engine.data_loader.pets.get(pet_name)
    if template is None:
        return {'estimated_stats': {}, 'stat_ranges': {}}

    base_stats = getattr(template, 'stats', {}) or {}
    profile = iv_projection['profile']
    estimated_stats = {}
    stat_ranges = {}
    for stat_name in ['生命', '物攻', '魔攻', '物防', '魔防', '速度']:
        min_iv = profile['min']
        max_iv = profile['max']
        if stat_name in HIDDEN_IV_STAT_KEYS:
            min_key, max_key = HIDDEN_IV_STAT_KEYS[stat_name]
            raw_min = iv_projection['iv_constraints'].get(min_key)
            raw_max = iv_projection['iv_constraints'].get(max_key)
            if raw_min is not None:
                min_iv = raw_min
            if raw_max is not None:
                max_iv = raw_max
        min_iv = max(profile['min'], min(10, int(min_iv)))
        max_iv = max(profile['min'], min(10, int(max_iv)))
        if min_iv > max_iv:
            min_iv, max_iv = profile['min'], profile['max']
        estimated_iv = iv_projection['iv_map'].get(stat_name, int(round((min_iv + max_iv) / 2)))
        estimated_stats[stat_name] = engine.data_loader.calc_actual_stats(
            base_stats.copy(),
            ivs={stat_name: estimated_iv},
            nature_name=None,
        ).get(stat_name, base_stats.get(stat_name, 0))
        stat_ranges[stat_name] = {
            'min': engine.data_loader.calc_actual_stats(
                base_stats.copy(),
                ivs={stat_name: min_iv},
                nature_name=None,
            ).get(stat_name, base_stats.get(stat_name, 0)),
            'max': engine.data_loader.calc_actual_stats(
                base_stats.copy(),
                ivs={stat_name: max_iv},
                nature_name=None,
            ).get(stat_name, base_stats.get(stat_name, 0)),
        }
    return {
        'estimated_stats': estimated_stats,
        'stat_ranges': stat_ranges,
    }


def _project_hidden_pet_payload(
    pet_data: Dict,
    observation_entry: Optional[Dict],
) -> tuple[Dict, Dict]:
    projected = copy.deepcopy(pet_data)
    observed_skills = _normalize_skill_names((observation_entry or {}).get('observed_skills', []))
    projected_skills = _build_hidden_skill_payloads(
        pet_name=projected['name'],
        observed_skills=observed_skills,
        active_energy=projected.get('energy'),
    )
    projected['skills'] = projected_skills
    projected.pop('nature', None)

    iv_projection = _resolve_hidden_iv_projection((observation_entry or {}).get('iv_constraints'))
    projected['iv'] = iv_projection['iv_map']
    stat_projection = _build_hidden_stat_projection(projected['name'], iv_projection)

    hidden_meta = {
        'pet_name': projected['name'],
        'observed_skill_count': len(observed_skills),
        'predicted_skill_count': max(0, len(projected_skills) - len(observed_skills)),
        'skills': [
            {
                'name': skill_payload['name'],
                'prediction_source': 'observed' if skill_payload['name'] in observed_skills else 'predicted',
            }
            for skill_payload in projected_skills
        ],
        'iv_profile': iv_projection['profile'],
        'iv_constraints': iv_projection['iv_constraints'],
        'estimated_stats': stat_projection['estimated_stats'],
        'stat_ranges': stat_projection['stat_ranges'],
        'notes': list(((observation_entry or {}).get('iv_constraints') or {}).get('notes', [])[-3:]),
    }
    return projected, hidden_meta


def _build_request_teams(data: Dict) -> tuple[List, List, Optional[Dict]]:
    if 'player_team' not in data or 'opponent_team' not in data:
        raise ValueError(
            f'请求缺少必要字段: '
            f'{"player_team " if "player_team" not in data else ""}'
            f'{"opponent_team" if "opponent_team" not in data else ""}'.strip()
        )
    player_team_data = copy.deepcopy(data['player_team'])
    opponent_team_data = copy.deepcopy(data['opponent_team'])
    hidden_meta = None

    if data.get('engine_mode') == 'hidden':
        observation_map = _build_hidden_observation_map(data.get('opponent_observations'))
        projected_opponent_team = []
        per_pet_meta = []
        for team_slot, pet_data in enumerate(opponent_team_data):
            observation_entry = _pick_hidden_observation(
                observation_map,
                pet_data.get('name', ''),
                team_slot,
            )
            projected_pet, pet_meta = _project_hidden_pet_payload(pet_data, observation_entry)
            projected_opponent_team.append(projected_pet)
            per_pet_meta.append(pet_meta)
        opponent_team_data = projected_opponent_team
        active_index = max(0, int(data.get('opponent_active_index', 0)))
        active_meta = per_pet_meta[active_index] if active_index < len(per_pet_meta) else None
        hidden_meta = {
            'mode': 'hidden',
            'opponent': {
                'active_index': active_index,
                'pets': per_pet_meta,
                'active_summary': active_meta,
            },
        }

    player_team = _build_team(player_team_data)
    opponent_team = _build_team(opponent_team_data)
    return player_team, opponent_team, hidden_meta


@engine_bp.route('/api/resolve', methods=['POST'])
def resolve_turn():
    """
    直接按双方指定行动推进一回合，返回引擎结算后的下一状态。
    请求体格式同 /api/analyze，额外包含:
    {
        "player_action": {...},
        "opponent_action": {...}
    }
    """
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': '无法解析请求 JSON，请检查请求体格式'}), 400

        player_team, opponent_team, hidden_meta = _build_request_teams(data)

        state = engine.create_battle_state(
            player_team=player_team,
            opponent_team=opponent_team,
            player_active_index=data.get('player_active_index', 0),
            opponent_active_index=data.get('opponent_active_index', 0),
            player_team_state=_parse_team_state(data.get('player_team_state')),
            opponent_team_state=_parse_team_state(data.get('opponent_team_state')),
        )
        state.turn = max(1, int(data.get('turn', state.turn)))
        state.turn_prepared = bool(data.get('turn_prepared', False))

        player_action = _parse_action_payload(data.get('player_action'), state, True)
        opponent_action = _parse_action_payload(data.get('opponent_action'), state, False)

        player_error = _build_illegal_action_error(state, player_action, True)
        if player_error is not None:
            _log_illegal_action(player_error, state, data)
            return jsonify(player_error), 400

        opponent_error = _build_illegal_action_error(state, opponent_action, False)
        if opponent_error is not None:
            _log_illegal_action(opponent_error, state, data)
            return jsonify(opponent_error), 400

        request_event_session_id = data.get('event_session_id') or 'engine-authority-preview'

        new_state = engine.battle_engine.apply_action(state, player_action, opponent_action)
        before_state_payload = _format_state(state)
        display_state, next_player_actions, next_opponent_actions = _build_display_state_and_actions(new_state)
        display_state_payload = _format_state(display_state)
        action_panels = _build_action_panels(display_state, next_player_actions, next_opponent_actions)
        turn_record = _build_turn_record(
            before_state_payload,
            display_state_payload,
            player_action,
            opponent_action,
            session_id=request_event_session_id,
        )

        response = {
            'player_action': _format_action(player_action),
            'opponent_action': _format_action(opponent_action),
            'all_actions': [_format_action(a) for a in next_player_actions],
            'opponent_all_actions': [_format_action(a) for a in next_opponent_actions],
            'action_panels': action_panels,
            'state': display_state_payload,
            'turn_record': turn_record,
        }
        if hidden_meta is not None:
            response['hidden_analysis'] = hidden_meta
        return jsonify(response)

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 400


@engine_bp.route('/api/next_states', methods=['POST'])
def get_next_states():
    """
    获取所有可能的下一步状态

    请求体格式同 /api/analyze

    返回:
    {
        "next_states": [
            {
                "player_action": {...},
                "opponent_action": {...},
                "state": {...}
            }
        ]
    }
    """
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': '无法解析请求 JSON，请检查请求体格式'}), 400

        # 创建队伍和状态（同上）
        player_team, opponent_team, _ = _build_request_teams(data)

        state = engine.create_battle_state(
            player_team=player_team,
            opponent_team=opponent_team,
            player_active_index=data.get('player_active_index', 0),
            opponent_active_index=data.get('opponent_active_index', 0),
            player_team_state=_parse_team_state(data.get('player_team_state')),
            opponent_team_state=_parse_team_state(data.get('opponent_team_state')),
        )
        state.turn = max(1, int(data.get('turn', state.turn)))
        state.turn_prepared = bool(data.get('turn_prepared', False))

        # 获取所有下一步状态
        next_states = engine.get_all_next_states(state)

        # 格式化返回
        response = {
            'next_states': [
                {
                    'player_action': _format_action(player_action),
                    'opponent_action': _format_action(opponent_action),
                    'state': _format_state(new_state)
                }
                for player_action, opponent_action, new_state in next_states
            ]
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/eval', methods=['POST'])
def evaluate_state():
    """
    只评估当前局面，不进行搜索（速度更快）

    返回:
    {
        "evaluation": 150.5,
        "player_hearts": 4,
        "opponent_hearts": 4,
        "is_terminal": false,
        "winner": null
    }
    """
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': '无法解析请求 JSON，请检查请求体格式'}), 400
        player_team, opponent_team, _ = _build_request_teams(data)
        state = engine.create_battle_state(
            player_team=player_team,
            opponent_team=opponent_team,
            player_active_index=data.get('player_active_index', 0),
            opponent_active_index=data.get('opponent_active_index', 0),
            player_team_state=_parse_team_state(data.get('player_team_state')),
            opponent_team_state=_parse_team_state(data.get('opponent_team_state')),
        )
        state.turn = max(1, int(data.get('turn', state.turn)))
        state.turn_prepared = bool(data.get('turn_prepared', False))
        evaluation = engine.evaluator.evaluate(state)
        from engine.evaluator import Evaluator
        return jsonify({
            'evaluation': evaluation,
            'win_rate': Evaluator.evaluation_to_win_rate(evaluation),
            'player_hearts': state.player_hearts,
            'opponent_hearts': state.opponent_hearts,
            'is_terminal': state.is_terminal(),
            'winner': state.get_winner(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/simulate', methods=['POST'])
def simulate_battle():
    """
    模拟完整对战（双方AI自动选择最佳行动）

    请求体:
    {
        "player_team": [...],
        "opponent_team": [...],
        "depth": 2,
        "max_turns": 30,
        "num_games": 1          // 模拟局数（>1 时返回胜率统计）
    }

    返回:
    {
        "winner": "player" | "opponent" | "draw",
        "turns": 15,
        "final_state": {...},
        "history": [...],
        // 多局模拟时额外返回:
        "win_rate": {"player": 0.6, "opponent": 0.3, "draw": 0.1},
        "num_games": 10
    }
    """
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': '无法解析请求 JSON，请检查请求体格式'}), 400
        depth = data.get('depth', 2)
        max_turns = data.get('max_turns', 30)
        num_games = min(data.get('num_games', 1), 100)  # 上限100局

        from engine.action_generator import ActionGenerator
        gen = ActionGenerator()

        results = []
        last_history = []
        last_final_state = None

        for game_idx in range(num_games):
            player_team, opponent_team, _ = _build_request_teams(data)
            state = engine.create_battle_state(
                player_team=player_team,
                opponent_team=opponent_team,
                player_team_state=_parse_team_state(data.get('player_team_state')),
                opponent_team_state=_parse_team_state(data.get('opponent_team_state')),
            )

            history = []

            for _ in range(max_turns):
                if state.is_terminal() or state.is_battle_over_by_hearts():
                    break

                # 玩家搜索最优行动
                p_action, _ = engine.search_engine.find_best_action(state, depth)

                # 对手搜索最优行动：从对手视角做 maximin
                # 对手想最大化自己的分数 = 最小化 player 的分数
                o_action = _find_best_opponent_action(state, engine, gen, depth)

                if p_action is None:
                    p_actions = gen.generate_actions(state, True)
                    p_action = p_actions[0] if p_actions else None

                if p_action is None or o_action is None:
                    break

                new_state = engine.battle_engine.apply_action(state, p_action, o_action)
                history.append({
                    'turn': state.turn,
                    'player_action': _format_action(p_action),
                    'opponent_action': _format_action(o_action),
                    'state': _format_state(new_state),
                })
                state = new_state

            winner = state.get_winner_by_hearts() or state.get_winner() or "draw"
            results.append(winner)
            last_history = history
            last_final_state = state

        # 统计胜率
        if num_games > 1:
            win_count = {"player": 0, "opponent": 0, "draw": 0}
            for w in results:
                win_count[w] = win_count.get(w, 0) + 1
            win_rate = {k: round(v / num_games, 4) for k, v in win_count.items()}
            return jsonify({
                'winner': max(win_count, key=win_count.get),
                'turns': last_final_state.turn if last_final_state else 0,
                'final_state': _format_state(last_final_state) if last_final_state else None,
                'history': last_history,
                'win_rate': win_rate,
                'num_games': num_games,
            })

        return jsonify({
            'winner': results[0] if results else "draw",
            'turns': last_final_state.turn if last_final_state else 0,
            'final_state': _format_state(last_final_state) if last_final_state else None,
            'history': last_history,
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 400


def _find_best_opponent_action(state, engine, gen, depth):
    """
    对手视角搜索最佳行动。
    对手要最大化自己的收益 = 最小化 player 的评估分。
    对每个对手行动 b，计算 max_a V(a, b)（player 的最佳响应），
    选择 min_b max_a V(a, b)（最小化 player 的最优值）。
    """
    opponent_actions = engine.search_engine._sort_actions_for_opponent(
        gen.generate_actions(state, False)
    )
    player_actions = engine.search_engine._sort_actions_for_player(
        gen.generate_actions(state, True)
    )

    if not opponent_actions:
        return None
    if not player_actions:
        return opponent_actions[0]

    best_action = opponent_actions[0]
    best_value = float('inf')  # 对手想最小化 player 的分

    for opponent_action in opponent_actions:
        # player 对此 opponent_action 的最佳响应
        best_for_player = float('-inf')
        for player_action in player_actions:
            new_state = engine.battle_engine.apply_action(
                state, player_action, opponent_action
            )
            if depth <= 1 or new_state.is_terminal() or new_state.is_battle_over_by_hearts():
                val = engine.evaluator.evaluate(new_state)
            else:
                _, val = engine.search_engine._maximin_recursive(
                    new_state, depth - 1, float('-inf'), float('inf')
                )
            best_for_player = max(best_for_player, val)

        if best_for_player < best_value:
            best_value = best_for_player
            best_action = opponent_action

    return best_action


@engine_bp.route('/api/pets', methods=['GET'])
def list_pets():
    """列出所有精灵"""
    pets = []
    for name, tmpl in engine.data_loader.pets.items():
        pets.append({
            'name': name,
            'types': tmpl.types,
            'is_legendary': tmpl.is_legendary,
            'traits': [{'name': t.name, 'desc': t.desc} for t in tmpl.traits],
            'stats': tmpl.stats,
            'learnable_skills_count': len(tmpl.learnable_skills),
        })
    return jsonify({'pets': pets, 'total': len(pets)})


@engine_bp.route('/api/skills', methods=['GET'])
def list_skills():
    """列出所有技能（支持 ?element=火 过滤）"""
    element = request.args.get('element')
    category = request.args.get('category')
    skills = []
    for name, sk in engine.data_loader.skills.items():
        if element and sk.element != element:
            continue
        if category and sk.category.value != category:
            continue
        skills.append({
            'name': name,
            'element': sk.element,
            'category': sk.category.value,
            'base_power': sk.base_power,
            'energy_cost': sk.energy_cost,
            'hits': sk.hits,
            'priority': sk.priority,
        })
    return jsonify({'skills': skills, 'total': len(skills)})


@engine_bp.route('/api/battle/start', methods=['POST'])
def battle_start():
    """创建事件驱动会话。"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = {}
        session_id = data.get('session_id') or 'battle-session'
        my_team = data.get('my_team', [])
        opponent_team = data.get('opponent_team', [])
        search_depth = int(data.get('search_depth', 2))
        inference_mode = data.get('inference_mode', 'hybrid')

        runtime_session_manager.create_session(
            session_id,
            BattleSessionConfig(
                my_team=my_team,
                opponent_team_candidates=opponent_team,
                search_depth=search_depth,
                inference_mode=inference_mode,
            ),
        )
        event = runtime_session_manager.normalize_event(
            session_id=session_id,
            event_type=EventType.BATTLE_STARTED,
            turn=0,
            payload={
                'my_team': my_team,
                'opponent_team': opponent_team,
                'weather': data.get('weather'),
            },
            source=EventSource.API,
        )
        runtime_session_manager.append_event(event)
        return jsonify({
            'session_id': session_id,
            'report': runtime_session_manager.get_session_report(session_id),
            'recommendation': _safe_runtime_recommendation(session_id, search_depth),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/event', methods=['POST'])
def battle_event(session_id: str):
    """追加事件。"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = {}
        event = runtime_session_manager.normalize_event(
            session_id=session_id,
            event_type=data['event_type'],
            turn=int(data.get('turn', 0)),
            payload=data.get('payload', {}),
            actor_side=data.get('actor_side'),
            phase=data.get('phase'),
            source=EventSource.API,
            note=data.get('note', ''),
        )
        validation = runtime_session_manager.validate_event(session_id, event)
        if not validation.is_valid:
            return jsonify({
                'error': 'invalid_event',
                'errors': validation.errors,
                'warnings': validation.warnings,
            }), 400
        runtime_session_manager.append_event(event)
        recommendation = _safe_runtime_recommendation(session_id)
        return jsonify({
            'event': _format_runtime_event(event),
            'report': runtime_session_manager.get_session_report(session_id),
            'warnings': validation.warnings,
            'recommendation': recommendation,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/report', methods=['GET'])
def battle_report(session_id: str):
    """返回会话概览。"""
    try:
        return jsonify({
            'report': runtime_session_manager.get_session_report(session_id),
            'recommendation': _safe_runtime_recommendation(session_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@engine_bp.route('/api/battle/<session_id>/recommend', methods=['GET'])
def battle_recommend(session_id: str):
    """返回当前推荐。"""
    try:
        depth = int(request.args.get('depth', 2))
        recommendation = _safe_runtime_recommendation(session_id, depth)
        if recommendation is None:
            raise ValueError('recommendation_unavailable')
        return jsonify(recommendation)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/events', methods=['GET'])
def battle_events(session_id: str):
    """返回事件日志。"""
    try:
        session = runtime_session_manager.get_session(session_id)
        return jsonify({
            'session_id': session_id,
            'events': [_format_runtime_event(event) for event in session.event_log.list_events()],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@engine_bp.route('/api/battle/<session_id>/imports', methods=['GET'])
def battle_imports(session_id: str):
    """返回最近的导入批次。"""
    try:
        return jsonify({
            'session_id': session_id,
            'imports': runtime_session_manager.list_import_batches(session_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@engine_bp.route('/api/battle/<session_id>/imports/<import_batch_id>', methods=['GET'])
def battle_import_detail(session_id: str, import_batch_id: str):
    """返回某个导入批次对应的事件。"""
    try:
        events = runtime_session_manager.get_import_batch_events(session_id, import_batch_id)
        return jsonify({
            'session_id': session_id,
            'import_batch_id': import_batch_id,
            'events': [_format_runtime_event(event) for event in events],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@engine_bp.route('/api/battle/<session_id>/undo', methods=['POST'])
def battle_undo(session_id: str):
    """撤销最后一条事件。"""
    try:
        event = runtime_session_manager.undo_last_event(session_id)
        return jsonify({
            'removed_event': _format_runtime_event(event) if event else None,
            'report': runtime_session_manager.get_session_report(session_id),
            'recommendation': _safe_runtime_recommendation(session_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/replay', methods=['POST'])
def battle_replay(session_id: str):
    """从日志重放。"""
    try:
        runtime_session_manager.replay_session(session_id)
        return jsonify({
            'report': runtime_session_manager.get_session_report(session_id),
            'recommendation': _safe_runtime_recommendation(session_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/correct', methods=['POST'])
def battle_correct(session_id: str):
    """追加 correction 事件。"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = {}
        runtime_session_manager.apply_correction(
            session_id=session_id,
            turn=int(data.get('turn', 0)),
            correction_type=data['correction_type'],
            payload=data.get('payload', {}),
            note=data.get('note', ''),
        )
        return jsonify({
            'report': runtime_session_manager.get_session_report(session_id),
            'recommendation': _safe_runtime_recommendation(session_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/import_state', methods=['POST'])
def battle_import_state(session_id: str):
    """导入敌方当前战况快照，不清空既有事件证据。"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = {}
        turn = int(data.get('turn', 0))
        side = data.get('side', 'opponent')
        active_pet_name = data.get('active_pet_name')
        pets = data.get('pets', [])
        note = data.get('note', '')
        session, import_batch_id, created_events = runtime_session_manager.apply_import_snapshot(
            session_id=session_id,
            turn=turn,
            side=side,
            active_pet_name=active_pet_name,
            pets=pets,
            note=note,
            source=EventSource.API,
        )
        return jsonify({
            'ok': True,
            'session_id': session_id,
            'turn': turn,
            'import_batch_id': import_batch_id,
            'applied_events': [
                {
                    'event_id': event.event_id,
                    'correction_type': event.payload.get('correction_type'),
                    'pet_name': event.payload.get('pet_name'),
                }
                for event in created_events
            ],
            'report': runtime_session_manager.get_session_report(session_id),
            'recommendation': _safe_runtime_recommendation(
                session_id,
                session.config.search_depth,
            ),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/clear_events', methods=['POST'])
def battle_clear_events(session_id: str):
    """清空当前会话的事件信息，但保留会话配置。"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = {}
        if data.get('confirm_text') != 'CLEAR':
            return jsonify({
                'error': 'confirmation_required',
                'message': '清空事件信息需要提供 confirm_text=CLEAR',
            }), 400
        session, removed_count = runtime_session_manager.clear_events(session_id)
        return jsonify({
            'ok': True,
            'session_id': session_id,
            'cleared_event_count': removed_count,
            'preserved_config': {
                'my_team': session.config.my_team,
                'opponent_team_candidates': session.config.opponent_team_candidates,
                'search_depth': session.config.search_depth,
                'inference_mode': session.config.inference_mode,
            },
            'report': runtime_session_manager.get_session_report(session_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@engine_bp.route('/api/battle/<session_id>/rollback_import/<import_batch_id>', methods=['POST'])
def battle_rollback_import(session_id: str, import_batch_id: str):
    """撤回指定导入批次。"""
    try:
        _, removed_events = runtime_session_manager.rollback_import_batch(
            session_id=session_id,
            import_batch_id=import_batch_id,
        )
        return jsonify({
            'ok': True,
            'session_id': session_id,
            'import_batch_id': import_batch_id,
            'removed_events': [_format_runtime_event(event) for event in removed_events],
            'report': runtime_session_manager.get_session_report(session_id),
            'recommendation': _safe_runtime_recommendation(session_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


def _build_team(team_data: List[Dict]):
    """从请求数据构建队伍"""
    team = []
    for pet_data in team_data:
        skill_payloads = pet_data.get('skills', [])
        skill_names = [
            sk.get('name') if isinstance(sk, dict) else sk
            for sk in skill_payloads
            if (sk.get('name') if isinstance(sk, dict) else sk)
        ]
        pet = engine.create_pet_instance(
            pet_name=pet_data['name'],
            skill_names=skill_names,
            hp_percent=pet_data.get('hp_percent', 1.0),
            energy=pet_data.get('energy', 10),
            bloodline=pet_data.get('bloodline'),
            ivs=pet_data.get('iv'),
            nature=pet_data.get('nature'),
        )
        if pet:
            for idx, payload in enumerate(skill_payloads):
                if not isinstance(payload, dict) or idx >= len(pet.skills):
                    continue
                skill = pet.skills[idx]
                # 仅接受明确的运行时覆盖字段（energy_cost_override），
                # 忽略来自 my_teams.json 快照的 energy/energy_cost，
                # 避免旧快照数据覆盖 battle_data.json 的权威值。
                energy_cost = payload.get('energy_cost_override')
                if energy_cost is not None:
                    try:
                        skill.energy_cost = max(0, int(energy_cost))
                    except (TypeError, ValueError):
                        pass
                cooldown = payload.get('cooldown')
                if cooldown is not None:
                    try:
                        cooldown_value = max(0, int(cooldown))
                        if cooldown_value > 0:
                            pet.skill_cooldowns[skill.name] = cooldown_value
                        else:
                            pet.skill_cooldowns.pop(skill.name, None)
                    except (TypeError, ValueError):
                        pass
            team.append(pet)
    return team


def _parse_team_state(ts_data: Optional[Dict]) -> Optional[TeamState]:
    """从请求数据解析队伍状态（首领化/愿力冲击次数等）。

    返回 None 表示使用默认值。
    """
    if not ts_data or not isinstance(ts_data, dict):
        return None
    ts = TeamState()
    if 'leader_evolution_uses' in ts_data:
        try:
            ts.leader_evolution_uses = max(0, int(ts_data['leader_evolution_uses']))
        except (TypeError, ValueError):
            pass
    if 'willpower_strike_uses' in ts_data:
        try:
            ts.willpower_strike_uses = max(0, int(ts_data['willpower_strike_uses']))
        except (TypeError, ValueError):
            pass
    return ts


def _format_action(action: Action) -> Dict:
    """格式化行动为JSON"""
    if action.type == ActionType.USE_SKILL:
        payload = {
            'type': 'use_skill',
            'skill_name': action.skill.name if action.skill else None
        }
        if action.send_out_index is not None:
            payload['send_out_index'] = action.send_out_index
        return payload
    elif action.type == ActionType.SWITCH_PET:
        return {
            'type': 'switch_pet',
            'target_index': action.target_index
        }
    elif action.type == ActionType.LEADER_EVOLUTION:
        payload = {'type': 'leader_evolution'}
        if action.send_out_index is not None:
            payload['send_out_index'] = action.send_out_index
        return payload
    elif action.type == ActionType.WILLPOWER_STRIKE:
        payload = {
            'type': 'willpower_strike',
            'skill_name': action.skill.name if action.skill else None
        }
        if action.send_out_index is not None:
            payload['send_out_index'] = action.send_out_index
        return payload
    else:  # GATHER_ENERGY
        payload = {'type': 'gather_energy'}
        if action.send_out_index is not None:
            payload['send_out_index'] = action.send_out_index
        return payload


def _build_action_panel(state: BattleState, is_player: bool, legal_actions: List[Action]) -> Dict:
    """为前端构建当前行动面板，避免网页端重复推断技能合法性/能耗。"""
    player_state = state.player if is_player else state.opponent
    active_pet = player_state.get_active_pet()

    panel = {
        'side': 'player' if is_player else 'opponent',
        'active_index': player_state.active_index,
        'active_pet_name': active_pet.template.name if active_pet else None,
        'bloodline': getattr(active_pet.template, 'bloodline', 'unknown') if active_pet else None,
        'forced_switch_required': bool(active_pet and not active_pet.is_alive),
        'forced_switch_targets': [],
        'can_charge': False,
        'can_leader_evolution': False,
        'can_switch': False,
        'switch_targets': [],
        'skills': [],
    }

    if not active_pet:
        return panel

    legal_skill_names = set()
    legal_willpower_skill_names = set()
    for action in legal_actions:
        if action.send_out_index is not None:
            panel['forced_switch_targets'].append(action.send_out_index)
        if action.type == ActionType.USE_SKILL and action.skill:
            legal_skill_names.add(action.skill.name)
        elif action.type == ActionType.WILLPOWER_STRIKE and action.skill:
            legal_willpower_skill_names.add(action.skill.name)
        elif action.type == ActionType.GATHER_ENERGY:
            panel['can_charge'] = True
        elif action.type == ActionType.LEADER_EVOLUTION:
            panel['can_leader_evolution'] = True
        elif action.type == ActionType.SWITCH_PET and action.target_index is not None:
            panel['can_switch'] = True
            panel['switch_targets'].append(action.target_index)

    panel['forced_switch_targets'] = sorted(set(panel['forced_switch_targets']))

    allowed_slots = SlotEffectsProcessor.get_allowed_skill_slots(active_pet)
    for idx, skill in enumerate(active_pet.skills):
        slot_locked = allowed_slots is not None and idx not in allowed_slots
        current_energy_cost = compute_effective_skill_energy_cost(
            state, is_player, active_pet, skill
        )
        cooldown = active_pet.skill_cooldowns.get(skill.name, 0)
        is_attack = getattr(skill, 'base_power', 0) > 0 and skill.category.value in ('物攻', '魔攻')
        is_legal = skill.name in legal_skill_names
        can_willpower = skill.name in legal_willpower_skill_names
        disabled_reason = None
        if not is_legal:
            if active_pet.stun_turns > 0:
                disabled_reason = 'stunned'
            elif active_pet.charging_skill and active_pet.charging_skill != skill.name:
                disabled_reason = 'charging_locked'
            elif slot_locked:
                disabled_reason = 'slot_locked'
            elif cooldown > 0:
                disabled_reason = 'cooldown'
            elif not can_pay_skill_energy_cost(active_pet, current_energy_cost):
                disabled_reason = 'insufficient_energy'
            else:
                disabled_reason = 'engine_rule_blocked'

        panel['skills'].append({
            'index': idx,
            'name': skill.name,
            'element': skill.element,
            'category': skill.category.value,
            'base_power': skill.base_power,
            'current_energy_cost': current_energy_cost,
            'cooldown': cooldown,
            'slot_locked': slot_locked,
            'is_attack': is_attack,
            'is_legal': is_legal,
            'can_willpower': can_willpower,
            'disabled_reason': disabled_reason,
        })

    return panel


def _format_runtime_event(event) -> Dict:
    if event is None:
        return {}
    return {
        'event_id': event.event_id,
        'session_id': event.session_id,
        'turn': event.turn,
        'phase': event.phase.value,
        'event_type': event.event_type.value,
        'payload': event.payload,
        'actor_side': event.actor_side.value if event.actor_side else None,
        'source': event.source.value,
        'note': event.note,
        'import_batch_id': event.payload.get('import_batch_id'),
        'timestamp': event.timestamp.isoformat(),
    }


def _build_turn_record(
    before_state: Dict,
    after_state: Dict,
    player_action: Action,
    opponent_action: Action,
    session_id: str,
) -> Dict:
    turn = int(before_state.get('turn', 0))
    events: List[Dict] = []
    highlights: List[str] = []
    hp_changes: List[Dict] = []
    energy_changes: List[Dict] = []
    status_changes: List[Dict] = []
    heart_changes: List[Dict] = []
    switches: List[Dict] = []
    side_metrics = {
        'my': {'damage_dealt': 0, 'damage_taken': 0, 'healing_done': 0, 'healing_taken': 0, 'energy_spent': 0, 'energy_gained': 0},
        'opponent': {'damage_dealt': 0, 'damage_taken': 0, 'healing_done': 0, 'healing_taken': 0, 'energy_spent': 0, 'energy_gained': 0},
    }

    def append_event(
        event_type: EventType,
        payload: Dict,
        *,
        actor_side: Optional[str] = None,
        note: str = "",
    ) -> None:
        event = runtime_session_manager.normalize_event(
            session_id=session_id,
            event_type=event_type,
            turn=turn,
            payload=payload,
            actor_side=actor_side,
            source=EventSource.API,
            note=note,
        )
        events.append(_format_runtime_event(event))

    def action_label(action: Action) -> str:
        if action.type == ActionType.USE_SKILL and action.skill:
            return action.skill.name
        if action.type == ActionType.WILLPOWER_STRIKE and action.skill:
            return f"愿力冲击·{action.skill.name}"
        if action.type == ActionType.SWITCH_PET:
            return "换宠"
        if action.type == ActionType.GATHER_ENERGY:
            return "聚能"
        if action.type == ActionType.LEADER_EVOLUTION:
            return "首领化"
        return action.type.value

    def team_pet_map(team_payload: Dict) -> Dict[str, Dict]:
        return {
            pet.get('name'): pet
            for pet in (team_payload or {}).get('team', [])
            if pet.get('name')
        }

    def status_events_for_side(side_key: str, before_team: Dict, after_team: Dict) -> None:
        before_map = team_pet_map(before_team)
        after_map = team_pet_map(after_team)
        for pet_name, after_pet in after_map.items():
            before_pet = before_map.get(pet_name, {})
            before_status = before_pet.get('status_effects') or {}
            after_status = after_pet.get('status_effects') or {}
            for status_name in sorted(set(before_status.keys()) | set(after_status.keys())):
                old_value = int(before_status.get(status_name, 0) or 0)
                new_value = int(after_status.get(status_name, 0) or 0)
                if old_value == new_value:
                    continue
                if new_value <= 0:
                    status_changes.append({
                        'side': side_key,
                        'pet_name': pet_name,
                        'status_name': status_name,
                        'before_stacks': old_value,
                        'after_stacks': 0,
                        'change_type': 'removed',
                    })
                    append_event(
                        EventType.STATUS_REMOVED,
                        {
                            'side': side_key,
                            'pet_name': pet_name,
                            'status_name': status_name,
                        },
                    )
                    highlights.append(f"{('我方' if side_key == 'my' else '敌方')} {pet_name} 失去状态：{status_name}")
                    continue
                status_changes.append({
                    'side': side_key,
                    'pet_name': pet_name,
                    'status_name': status_name,
                    'before_stacks': old_value,
                    'after_stacks': new_value,
                    'change_type': 'applied' if old_value <= 0 else 'updated',
                })
                append_event(
                    EventType.STATUS_APPLIED,
                    {
                        'side': side_key,
                        'pet_name': pet_name,
                        'status_name': status_name,
                        'stacks': new_value,
                    },
                )
                highlights.append(f"{('我方' if side_key == 'my' else '敌方')} {pet_name} 状态变为 {status_name}×{new_value}")

    def hp_energy_events_for_side(
        side_key: str,
        before_team: Dict,
        after_team: Dict,
        enemy_active_name: Optional[str],
        enemy_action_name: Optional[str],
    ) -> None:
        before_map = team_pet_map(before_team)
        after_map = team_pet_map(after_team)
        for pet_name, after_pet in after_map.items():
            before_pet = before_map.get(pet_name)
            if before_pet is None:
                continue
            side_label = '我方' if side_key == 'my' else '敌方'
            before_hp = int(before_pet.get('hp', 0) or 0)
            after_hp = int(after_pet.get('hp', 0) or 0)
            if before_hp != after_hp:
                delta = after_hp - before_hp
                hp_change = {
                    'side': side_key,
                    'pet_name': pet_name,
                    'before_hp': before_hp,
                    'after_hp': after_hp,
                    'delta': delta,
                    'abs_delta': abs(delta),
                    'max_hp': int(after_pet.get('max_hp', before_pet.get('max_hp', 0)) or 0),
                    'hp_percent_after': after_pet.get('hp_percent', 0),
                    'change_type': 'heal' if delta > 0 else 'damage',
                    'source_pet': enemy_active_name or '',
                    'source_action': enemy_action_name or '',
                }
                hp_changes.append(hp_change)
                append_event(
                    EventType.HP_PERCENT_UPDATED,
                    {
                        'side': side_key,
                        'pet_name': pet_name,
                        'hp_percent': after_pet.get('hp_percent', 0),
                        'hp': after_hp,
                        'max_hp': after_pet.get('max_hp', 0),
                        'before_hp': before_hp,
                        'after_hp': after_hp,
                    },
                )
                if delta < 0:
                    side_metrics[side_key]['damage_taken'] += abs(delta)
                    side_metrics['opponent' if side_key == 'my' else 'my']['damage_dealt'] += abs(delta)
                    append_event(
                        EventType.DAMAGE_OBSERVED,
                        {
                            'attacker': enemy_active_name or '',
                            'defender': pet_name,
                            'skill_name': enemy_action_name or '',
                            'observed_damage': abs(delta),
                            'target_side': side_key,
                            'target_hp_percent': after_pet.get('hp_percent', 0),
                            'before_hp': before_hp,
                            'after_hp': after_hp,
                        },
                    )
                    highlights.append(f"{side_label} {pet_name} 生命 {before_hp}→{after_hp} (-{abs(delta)})")
                else:
                    side_metrics[side_key]['healing_taken'] += delta
                    side_metrics[side_key]['healing_done'] += delta
                    highlights.append(f"{side_label} {pet_name} 生命 {before_hp}→{after_hp} (+{delta})")
            before_energy = int(before_pet.get('energy', 0) or 0)
            after_energy = int(after_pet.get('energy', 0) or 0)
            if before_energy != after_energy:
                energy_delta = after_energy - before_energy
                energy_changes.append({
                    'side': side_key,
                    'pet_name': pet_name,
                    'before_energy': before_energy,
                    'after_energy': after_energy,
                    'delta': energy_delta,
                    'change_type': 'gain' if energy_delta > 0 else 'spend',
                })
                if energy_delta > 0:
                    side_metrics[side_key]['energy_gained'] += energy_delta
                else:
                    side_metrics[side_key]['energy_spent'] += abs(energy_delta)
                append_event(
                    EventType.ENERGY_UPDATED,
                    {
                        'side': side_key,
                        'pet_name': pet_name,
                        'energy': after_energy,
                        'before_energy': before_energy,
                        'after_energy': after_energy,
                    },
                )
                highlights.append(f"{side_label} {pet_name} 能量 {before_energy}→{after_energy}")
            if bool(before_pet.get('is_alive', True)) and not bool(after_pet.get('is_alive', True)):
                append_event(
                    EventType.PET_FAINTED,
                    {
                        'side': side_key,
                        'pet_name': pet_name,
                    },
                )
                highlights.append(f"{side_label} {pet_name} 倒下")

    before_player = before_state.get('player') or {}
    before_opponent = before_state.get('opponent') or {}
    after_player = after_state.get('player') or {}
    after_opponent = after_state.get('opponent') or {}

    before_player_active = ((before_player.get('team') or [{}])[before_player.get('active_index', 0)] or {}).get('name')
    before_opponent_active = ((before_opponent.get('team') or [{}])[before_opponent.get('active_index', 0)] or {}).get('name')
    after_player_active = ((after_player.get('team') or [{}])[after_player.get('active_index', 0)] or {}).get('name')
    after_opponent_active = ((after_opponent.get('team') or [{}])[after_opponent.get('active_index', 0)] or {}).get('name')

    player_action_payload = _format_action(player_action)
    opponent_action_payload = _format_action(opponent_action)
    player_action_name = action_label(player_action)
    opponent_action_name = action_label(opponent_action)

    append_event(
        EventType.TURN_STARTED,
        {
            'player_active_pet': before_player_active,
            'opponent_active_pet': before_opponent_active,
        },
    )
    append_event(
        EventType.MY_ACTION_DECLARED,
        {
            'pet_name': before_player_active,
            'action': player_action_payload,
            'action_name': player_action_name,
        },
        actor_side='my',
    )
    append_event(
        EventType.OPPONENT_ACTION_OBSERVED,
        {
            'pet_name': before_opponent_active,
            'action': opponent_action_payload,
            'action_name': opponent_action_name,
            'skill_name': opponent_action.skill.name if opponent_action.skill else None,
        },
        actor_side='opponent',
    )
    highlights.append(f"我方行动：{player_action_name}")
    highlights.append(f"敌方行动：{opponent_action_name}")

    if player_action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE) and player_action.skill:
        append_event(
            EventType.SKILL_USED,
            {
                'side': 'my',
                'pet_name': before_player_active,
                'skill_name': player_action.skill.name,
                'action_type': player_action.type.value,
            },
            actor_side='my',
        )
    if opponent_action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE) and opponent_action.skill:
        append_event(
            EventType.SKILL_USED,
            {
                'side': 'opponent',
                'pet_name': before_opponent_active,
                'skill_name': opponent_action.skill.name,
                'action_type': opponent_action.type.value,
            },
            actor_side='opponent',
        )

    if before_player_active != after_player_active and after_player_active:
        append_event(
            EventType.PET_SWITCHED,
            {
                'side': 'my',
                'old_pet': before_player_active,
                'new_pet': after_player_active,
            },
            actor_side='my',
        )
        switches.append({'side': 'my', 'old_pet': before_player_active, 'new_pet': after_player_active})
        highlights.append(f"我方换上 {after_player_active}")
    if before_opponent_active != after_opponent_active and after_opponent_active:
        append_event(
            EventType.PET_SWITCHED,
            {
                'side': 'opponent',
                'old_pet': before_opponent_active,
                'new_pet': after_opponent_active,
            },
            actor_side='opponent',
        )
        switches.append({'side': 'opponent', 'old_pet': before_opponent_active, 'new_pet': after_opponent_active})
        highlights.append(f"敌方换上 {after_opponent_active}")

    hp_energy_events_for_side('my', before_player, after_player, before_opponent_active, opponent_action_name)
    hp_energy_events_for_side('opponent', before_opponent, after_opponent, before_player_active, player_action_name)
    status_events_for_side('my', before_player, after_player)
    status_events_for_side('opponent', before_opponent, after_opponent)

    before_player_hearts = int(before_player.get('hearts', 0) or 0)
    after_player_hearts = int(after_player.get('hearts', 0) or 0)
    if before_player_hearts != after_player_hearts:
        heart_changes.append({
            'side': 'my',
            'before_hearts': before_player_hearts,
            'after_hearts': after_player_hearts,
            'delta': after_player_hearts - before_player_hearts,
        })
        append_event(
            EventType.HEARTS_UPDATED,
            {
                'side': 'my',
                'hearts': after_player_hearts,
                'before_hearts': before_player_hearts,
                'after_hearts': after_player_hearts,
            },
        )
        highlights.append(f"我方心数 {before_player_hearts}→{after_player_hearts}")

    before_opponent_hearts = int(before_opponent.get('hearts', 0) or 0)
    after_opponent_hearts = int(after_opponent.get('hearts', 0) or 0)
    if before_opponent_hearts != after_opponent_hearts:
        heart_changes.append({
            'side': 'opponent',
            'before_hearts': before_opponent_hearts,
            'after_hearts': after_opponent_hearts,
            'delta': after_opponent_hearts - before_opponent_hearts,
        })
        append_event(
            EventType.HEARTS_UPDATED,
            {
                'side': 'opponent',
                'hearts': after_opponent_hearts,
                'before_hearts': before_opponent_hearts,
                'after_hearts': after_opponent_hearts,
            },
        )
        highlights.append(f"敌方心数 {before_opponent_hearts}→{after_opponent_hearts}")

    append_event(
        EventType.TURN_ENDED,
        {
            'next_turn': after_state.get('turn'),
            'winner': after_state.get('winner'),
            'is_terminal': after_state.get('is_terminal'),
        },
    )

    summary = {
        'my': side_metrics['my'],
        'opponent': side_metrics['opponent'],
        'total_hp_changes': len(hp_changes),
        'total_energy_changes': len(energy_changes),
        'total_status_changes': len(status_changes),
        'total_switches': len(switches),
        'counts': {
            'hp_changes': len(hp_changes),
            'energy_changes': len(energy_changes),
            'status_changes': len(status_changes),
            'heart_changes': len(heart_changes),
            'switches': len(switches),
        },
    }

    return {
        'turn': turn,
        'player_action': player_action_payload,
        'opponent_action': opponent_action_payload,
        'player_action_name': player_action_name,
        'opponent_action_name': opponent_action_name,
        'state_before': before_state,
        'state_after': after_state,
        'highlights': highlights,
        'summary': summary,
        'hp_changes': hp_changes,
        'energy_changes': energy_changes,
        'status_changes': status_changes,
        'heart_changes': heart_changes,
        'switches': switches,
        'events': events,
    }


def _format_state(state: BattleState) -> Dict:
    """格式化状态为JSON"""
    def fmt_pet(pet):
        from core.status_effects import StatusEffectType
        energy_markers = []
        seen_energy_deltas = set()
        for skill in pet.skills:
            base_skill = engine.data_loader.skills.get(skill.name)
            if base_skill is None:
                continue
            try:
                base_energy = int(getattr(base_skill, 'energy_cost', 0) or 0)
                current_energy = int(getattr(skill, 'energy_cost', 0) or 0)
            except (TypeError, ValueError):
                continue
            delta = current_energy - base_energy
            if delta == 0 or delta in seen_energy_deltas:
                continue
            seen_energy_deltas.add(delta)
            energy_markers.append({
                'delta': delta,
                'text': f'消耗{delta:+d}',
                'type': 'cost_down' if delta < 0 else 'cost_up',
            })
        energy_markers.sort(key=lambda item: (0 if item['delta'] < 0 else 1, abs(item['delta'])))
        return {
            'name': pet.template.name,
            'bloodline': getattr(pet.template, 'bloodline', 'unknown'),
            'hp': pet.current_hp,
            'max_hp': pet.max_hp,
            'hp_percent': round(pet.current_hp / max(pet.max_hp, 1), 3),
            'energy': pet.current_energy,
            'is_alive': pet.is_alive,
            'stats': pet.stats,
            'effective_stats': {
                '生命': pet.max_hp,
                '物攻': pet.get_effective_stat('物攻'),
                '魔攻': pet.get_effective_stat('魔攻'),
                '物防': pet.get_effective_stat('物防'),
                '魔防': pet.get_effective_stat('魔防'),
                '速度': pet.get_effective_stat('速度'),
            },
            'buffs': {
                'physical_attack': pet.stat_modifiers.physical_attack,
                'magical_attack': pet.stat_modifiers.magical_attack,
                'physical_defense': pet.stat_modifiers.physical_defense,
                'magical_defense': pet.stat_modifiers.magical_defense,
                'speed': pet.stat_modifiers.speed,
            },
            'status_effects': {
                k.value: v for k, v in pet.status_effects.items()
            },
            'freeze_stacks': pet.freeze_stacks,
            'energy_cost_markers': energy_markers,
            'skills': [
                {
                    'name': skill.name,
                    'element': skill.element,
                    'category': skill.category.value,
                    'base_power': skill.base_power,
                    'energy_cost': skill.energy_cost,
                    'energy': skill.energy_cost,
                    'hits': skill.hits,
                    'priority': skill.priority,
                    'cooldown': pet.skill_cooldowns.get(skill.name, 0),
                    'desc': skill.desc,
                }
                for skill in pet.skills
            ],
        }

    def fmt_team(ps, is_player):
        pos_mark, neg_mark = state.get_marks(is_player)
        return {
            'active_index': ps.active_index,
            'hearts': state.player_hearts if is_player else state.opponent_hearts,
            'team_state': {
                'leader_evolution_uses': ps.team_state.leader_evolution_uses,
                'willpower_strike_uses': ps.team_state.willpower_strike_uses,
            },
            'positive_mark': {
                'type': pos_mark.type_key,
                'stacks': pos_mark.stacks
            } if pos_mark else None,
            'negative_mark': {
                'type': neg_mark.type_key,
                'stacks': neg_mark.stacks
            } if neg_mark else None,
            'team': [fmt_pet(pet) for pet in ps.team],
        }

    return {
        'turn': state.turn,
        'turn_prepared': state.turn_prepared,
        'weather': state.weather,
        'field_effects': state.field_effects,
        'player': fmt_team(state.player, True),
        'opponent': fmt_team(state.opponent, False),
        'is_terminal': state.is_terminal(),
        'is_battle_over': state.is_battle_over_by_hearts(),
        'winner': state.get_winner(),
        'winner_by_hearts': state.get_winner_by_hearts(),
    }


if __name__ == '__main__':
    app = Flask(__name__)
    app.register_blueprint(engine_bp)
    app.run(host='0.0.0.0', port=5000, debug=True)
