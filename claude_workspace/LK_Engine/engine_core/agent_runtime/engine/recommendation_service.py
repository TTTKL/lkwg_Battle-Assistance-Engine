from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..tracker.session_manager import BattleSession
from ..core.observation import ObservationState
from .behavior_predictor import BehaviorPredictor, PredictionResult
from .state_assembler import InferredBattleState, StateAssembler


@dataclass(slots=True)
class Recommendation:
    best_action: dict = field(default_factory=dict)
    score: float = 0.0
    confidence: float = 0.0
    confidence_breakdown: dict = field(default_factory=dict)
    alternatives: list[dict] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    based_on_assumptions: list[str] = field(default_factory=list)
    # 新增：预判相关
    opponent_prediction: dict = field(default_factory=dict)
    read_opportunities: list[dict] = field(default_factory=list)


class RecommendationService:
    def __init__(
        self,
        data_loader=None,
        data_dir: str | None = None,
        analysis_engine=None,
    ) -> None:
        self._data_loader = data_loader
        self._data_dir = data_dir
        self._analysis_engine = analysis_engine
        self._assembler = StateAssembler(data_loader=data_loader, data_dir=data_dir)
        self._behavior_predictor = BehaviorPredictor()

    def recommend(self, session: BattleSession, depth: int = 2) -> Recommendation:
        if session.observation_state is None:
            return Recommendation(risk_notes=["当前会话尚未建立 ObservationState"])

        candidates: list[InferredBattleState] = self._assembler.build_candidates(
            session.observation_state
        )
        if not candidates or candidates[0].battle_state is None:
            return Recommendation(
                confidence=0.0,
                risk_notes=["候选完整状态尚未装配完成，当前只能返回占位结果"],
                based_on_assumptions=candidates[0].assumptions if candidates else [],
            )

        # ── 对手行为预测 ─────────────────────────────────────────
        prediction = self._predict_opponent(session.observation_state)
        read_opportunities = self._behavior_predictor.analyze_reads(prediction)

        best_candidate = max(candidates, key=lambda item: item.belief_weight)
        mode = getattr(session.config, "inference_mode", "hybrid") or "hybrid"
        aggregated = self._aggregate_actions_across_candidates(
            candidates, depth, mode=mode, prediction=prediction,
        )
        if aggregated:
            best_choice = aggregated[0]
            dominant_beliefs = self._dominant_belief_summary(candidates)
            return Recommendation(
                best_action=best_choice["action"],
                score=float(best_choice["selected_score"]),
                confidence=max(0.2, min(0.98, best_choice["confidence"])),
                confidence_breakdown={
                    "belief_weight": best_candidate.belief_weight,
                    "skill_probability": best_candidate.skill_probability,
                    "skill_signature": list(best_candidate.skill_signature),
                    "profile_probability": best_candidate.profile_probability,
                    "profile_label": best_candidate.profile_label,
                    "action_support": best_choice["action_support"],
                    "score_span": best_choice["score_span"],
                    "dominant_skill_sets": dominant_beliefs["skill_sets"],
                    "dominant_profiles": dominant_beliefs["profiles"],
                },
                alternatives=[
                    {
                        "action": item["action"],
                        "mode": item["mode"],
                        "selected_score": item["selected_score"],
                        "worst_score": item["worst_score"],
                        "expected_score": item["expected_score"],
                        "average_score": item["average_score"],
                        "weighted_score": item["weighted_score"],
                        "confidence": item["confidence"],
                        "action_support": item["action_support"],
                        "score_span": item["score_span"],
                    }
                    for item in aggregated[:5]
                ],
                risk_notes=[
                    f"当前使用 {best_choice['mode']} 聚合策略",
                    f"已分析 {len(candidates)} 个候选 BattleState",
                    best_choice["belief_summary"],
                    best_choice["risk_summary"],
                ],
                based_on_assumptions=best_choice["assumptions"],
                opponent_prediction=self._format_prediction(prediction),
                read_opportunities=read_opportunities,
            )

        return Recommendation(
            confidence=best_candidate.belief_weight,
            confidence_breakdown={
                "belief_weight": best_candidate.belief_weight,
                "skill_probability": best_candidate.skill_probability,
                "skill_signature": list(best_candidate.skill_signature),
                "profile_probability": best_candidate.profile_probability,
                "profile_label": best_candidate.profile_label,
            },
            risk_notes=[
                "RecommendationService 尚未接入现有 SearchEngine",
                f"当前已装配 {len(candidates)} 个候选 BattleState",
            ],
            based_on_assumptions=best_candidate.assumptions,
        )

    def _aggregate_actions_across_candidates(
        self,
        candidates: list[InferredBattleState],
        depth: int,
        mode: str = "hybrid",
        prediction: PredictionResult | None = None,
    ) -> list[dict]:
        engine = self._ensure_analysis_engine()
        if engine is None:
            return []

        valid_candidates = [
            candidate for candidate in candidates if candidate.battle_state is not None
        ]
        if not valid_candidates:
            return []

        shared_actions = self._collect_shared_actions(engine, valid_candidates)
        if not shared_actions:
            return []

        aggregated: list[dict] = []
        weights = self._candidate_weights(valid_candidates)
        belief_summary = self._summarize_beliefs(valid_candidates)

        for action_key, action in shared_actions.items():
            scores: list[float] = []
            assumptions: list[str] = []
            per_candidate: list[dict[str, Any]] = []

            # 构建对手行为概率权重（如有预测数据）
            opp_weights = self._prediction_to_weights(prediction) if prediction else None
            pred_confidence = prediction.confidence if prediction else 0.0

            for index, candidate in enumerate(valid_candidates):
                score = self._score_fixed_action(
                    engine=engine,
                    state=candidate.battle_state,
                    action=action,
                    depth=depth,
                    opponent_action_weights=opp_weights,
                    prediction_confidence=pred_confidence,
                )
                scores.append(score)
                assumptions.extend(candidate.assumptions)
                per_candidate.append(
                    {
                        "candidate_index": index,
                        "score": score,
                        "belief_weight": candidate.belief_weight,
                        "skill_probability": candidate.skill_probability,
                        "skill_signature": list(candidate.skill_signature),
                        "profile_probability": candidate.profile_probability,
                        "profile_label": candidate.profile_label,
                    }
                )

            weighted_score = self._weighted_average(scores, weights)
            aggregated.append(
                {
                    "action_key": action_key,
                    "action": self._serialize_action(action),
                    "mode": mode,
                    "worst_score": min(scores),
                    "expected_score": weighted_score,
                    "average_score": sum(scores) / len(scores),
                    "weighted_score": weighted_score,
                    "belief_summary": belief_summary,
                    "assumptions": list(dict.fromkeys(assumptions)),
                    "per_candidate": per_candidate,
                }
            )

        best_by_candidate = self._best_scores_by_candidate(aggregated)
        for item in aggregated:
            item["action_support"] = self._action_support(
                item["per_candidate"],
                best_by_candidate,
                weights,
            )
            item["score_span"] = float(
                max(score["score"] for score in item["per_candidate"]) - item["worst_score"]
            )
            item["confidence"] = self._action_confidence(
                item["action_support"],
                item["score_span"],
            )
            item["risk_summary"] = self._summarize_action_risk(item)
            item["selected_score"] = self._select_score(item, mode)

        aggregated.sort(
            key=lambda item: (
                item["selected_score"],
                item["worst_score"],
                item["expected_score"],
            ),
            reverse=True,
        )
        return aggregated

    def _candidate_weights(self, candidates: list[InferredBattleState]) -> list[float]:
        raw = [max(0.01, float(candidate.belief_weight)) for candidate in candidates]
        total = sum(raw)
        if total <= 0:
            return [1.0 / len(candidates)] * len(candidates)
        return [value / total for value in raw]

    def _weighted_average(self, scores: list[float], weights: list[float]) -> float:
        if not scores:
            return 0.0
        return sum(score * weight for score, weight in zip(scores, weights))

    def _select_score(self, item: dict, mode: str) -> float:
        mode = (mode or "hybrid").lower()
        if mode == "pessimistic":
            return float(item["worst_score"])
        if mode == "expected":
            return float(item["expected_score"])
        return float(item["worst_score"]) * 0.7 + float(item["expected_score"]) * 0.3

    def _summarize_beliefs(self, candidates: list[InferredBattleState]) -> str:
        profile_mass: dict[str, float] = {}
        skill_mass = 0.0
        for candidate in candidates:
            profile_key = candidate.profile_label or "center"
            profile_mass[profile_key] = profile_mass.get(profile_key, 0.0) + candidate.belief_weight
            skill_mass = max(skill_mass, candidate.skill_probability)

        top_profile = (
            max(profile_mass.items(), key=lambda item: item[1])[0]
            if profile_mass else "center"
        )
        return (
            f"当前主要信念集中在技能组概率约 {skill_mass:.3f} "
            f"与属性侧面 {top_profile}"
        )

    def _dominant_belief_summary(
        self,
        candidates: list[InferredBattleState],
    ) -> dict[str, list[dict[str, float | str | list[str]]]]:
        profile_mass: dict[str, float] = {}
        skill_mass: dict[tuple[str, ...], float] = {}
        for candidate in candidates:
            profile_key = candidate.profile_label or "center"
            profile_mass[profile_key] = profile_mass.get(profile_key, 0.0) + candidate.belief_weight
            skill_key = candidate.skill_signature or ("<unknown>",)
            skill_mass[skill_key] = skill_mass.get(skill_key, 0.0) + candidate.belief_weight

        top_profiles = sorted(profile_mass.items(), key=lambda item: item[1], reverse=True)[:3]
        top_skill_sets = sorted(skill_mass.items(), key=lambda item: item[1], reverse=True)[:3]
        return {
            "profiles": [
                {"label": label, "belief_weight": round(weight, 4)}
                for label, weight in top_profiles
            ],
            "skill_sets": [
                {"skills": list(skills), "belief_weight": round(weight, 4)}
                for skills, weight in top_skill_sets
            ],
        }

    def _best_scores_by_candidate(self, aggregated: list[dict]) -> dict[int, float]:
        best: dict[int, float] = {}
        for item in aggregated:
            for row in item["per_candidate"]:
                index = int(row["candidate_index"])
                score = float(row["score"])
                if index not in best or score > best[index]:
                    best[index] = score
        return best

    def _action_support(
        self,
        per_candidate: list[dict[str, Any]],
        best_by_candidate: dict[int, float],
        weights: list[float],
        tolerance: float = 1e-6,
    ) -> float:
        support = 0.0
        for row in per_candidate:
            index = int(row["candidate_index"])
            score = float(row["score"])
            best_score = float(best_by_candidate.get(index, score))
            if score + tolerance >= best_score:
                support += weights[index]
        return min(1.0, max(0.0, support))

    def _action_confidence(self, action_support: float, score_span: float) -> float:
        span_penalty = min(0.45, max(0.0, float(score_span)) / 600.0)
        return max(0.15, min(0.98, float(action_support) - span_penalty))

    def _summarize_action_risk(self, item: dict) -> str:
        support = float(item.get("action_support", 0.0))
        span = float(item.get("score_span", 0.0))
        if support >= 0.8 and span <= 120:
            return "该推荐在主要候选状态下较为一致，不确定性风险较低"
        if support >= 0.5 and span <= 260:
            return "该推荐在部分候选状态下稳定，但仍受对手技能组或属性侧面影响"
        return "该推荐对候选状态假设较敏感，如有新观察信息建议重新请求推荐"

    def _collect_shared_actions(
        self,
        engine,
        candidates: list[InferredBattleState],
    ) -> dict[str, Any]:
        action_maps: list[dict[str, Any]] = []
        for candidate in candidates:
            actions = engine.action_generator.generate_actions(candidate.battle_state, True)
            action_map = {self._action_key(action): action for action in actions}
            action_maps.append(action_map)

        if not action_maps:
            return {}

        shared_keys = set(action_maps[0].keys())
        for action_map in action_maps[1:]:
            shared_keys &= set(action_map.keys())

        if shared_keys:
            return {key: action_maps[0][key] for key in shared_keys}

        return action_maps[0]

    def _score_fixed_action(
        self, engine, state, action, depth: int,
        opponent_action_weights: dict[str, float] | None = None,
        prediction_confidence: float = 0.0,
    ) -> float:
        opponent_actions = engine.search_engine._sort_actions_for_opponent(  # noqa: SLF001
            engine.action_generator.generate_actions(state, False),
        )
        if not opponent_actions:
            return float(engine.evaluator.evaluate(state))

        # 如果有预测权重，使用混合评估
        if opponent_action_weights and prediction_confidence > 0.05:
            weights = engine.search_engine._build_weight_map(  # noqa: SLF001
                opponent_actions, opponent_action_weights,
            )
            return engine.search_engine._score_action_mixed(  # noqa: SLF001
                state, action, opponent_actions,
                weights, prediction_confidence, depth,
            )

        # 否则使用纯 worst-case
        worst_for_player = float("inf")
        for opponent_action in opponent_actions:
            new_state = engine.battle_engine.apply_action(state, action, opponent_action)
            if depth <= 1:
                eval_score = engine.evaluator.evaluate(new_state)
            else:
                _, eval_score = engine.search_engine._maximin_recursive(  # noqa: SLF001
                    new_state,
                    depth - 1,
                    float("-inf"),
                    float("inf"),
                )
            worst_for_player = min(worst_for_player, float(eval_score))
        return worst_for_player

    def _ensure_analysis_engine(self):
        if self._analysis_engine is not None:
            return self._analysis_engine

        try:
            from game_analysis_engine import GameAnalysisEngine
            from paths import get_default_data_dir
        except ImportError:
            return None

        data_dir = self._data_dir
        if data_dir is None:
            data_dir = str(get_default_data_dir())

        self._analysis_engine = GameAnalysisEngine(data_dir=data_dir)
        return self._analysis_engine

    def _serialize_action(self, action) -> dict:
        if action is None:
            return {}

        payload = {"type": getattr(action.type, "value", str(action.type))}
        skill = getattr(action, "skill", None)
        if skill is not None:
            payload["skill_name"] = getattr(skill, "name", str(skill))
        target_index = getattr(action, "target_index", None)
        if target_index is not None:
            payload["target_index"] = target_index
        payload["display"] = str(action)
        return payload

    def _action_key(self, action) -> str:
        action_type = getattr(action.type, "value", str(action.type))
        skill = getattr(action, "skill", None)
        target_index = getattr(action, "target_index", None)
        skill_name = getattr(skill, "name", "")
        return f"{action_type}|{skill_name}|{target_index}"

    # ── 对手行为预测集成 ─────────────────────────────────────────

    @property
    def behavior_predictor(self) -> BehaviorPredictor:
        """暴露预测器实例，供外部录入历史行为"""
        return self._behavior_predictor

    def _predict_opponent(self, observation: ObservationState) -> PredictionResult:
        """基于当前观测状态进行对手行为预测"""
        opp = observation.opponent_side
        my = observation.my_side

        opponent_pet_name = opp.active_pet or ""
        my_pet_name = my.active_pet or ""

        # 收集对手当前精灵的信息
        opp_pet = opp.pets.get(opponent_pet_name)
        my_pet = my.pets.get(my_pet_name)

        opp_hp = opp_pet.hp_percent if opp_pet else None
        opp_energy = opp_pet.energy if opp_pet else None
        opp_skills = list(opp_pet.observed_skills) if opp_pet else []
        my_hp = my_pet.hp_percent if my_pet else None

        # 对手后备存活精灵
        bench = [
            name for name, pet in opp.pets.items()
            if name != opponent_pet_name and not pet.fainted
        ]

        return self._behavior_predictor.predict(
            observation=observation,
            opponent_pet_name=opponent_pet_name,
            my_pet_name=my_pet_name,
            opponent_hp_percent=opp_hp,
            opponent_energy=opp_energy,
            opponent_observed_skills=opp_skills,
            my_hp_percent=my_hp,
            opponent_alive_bench=bench,
        )

    @staticmethod
    def _prediction_to_weights(prediction: PredictionResult) -> dict[str, float]:
        """将预测结果转为搜索引擎需要的权重字典"""
        weights: dict[str, float] = {}
        for ap in prediction.action_distribution:
            if ap.action_type == "skill" and ap.skill_name:
                weights[f"skill:{ap.skill_name}"] = ap.probability
            elif ap.action_type == "switch" and ap.switch_target:
                # switch_target 是精灵名，搜索引擎用索引——这里传精灵名
                # _build_weight_map 会做 action_key 匹配
                weights[f"switch:{ap.switch_target}"] = ap.probability
            elif ap.action_type == "gather_energy":
                weights["gather_energy"] = ap.probability
            elif ap.action_type == "leader":
                weights["leader"] = ap.probability
            elif ap.action_type == "willpower":
                weights[f"willpower:{ap.skill_name}"] = ap.probability
        return weights

    @staticmethod
    def _format_prediction(prediction: PredictionResult) -> dict:
        """格式化预测结果为 JSON-safe dict"""
        return {
            "confidence": prediction.confidence,
            "most_likely": (
                {
                    "action_type": prediction.most_likely_action.action_type,
                    "detail": prediction.most_likely_action.skill_name
                              or prediction.most_likely_action.switch_target
                              or "",
                    "probability": round(prediction.most_likely_action.probability, 3),
                }
                if prediction.most_likely_action else None
            ),
            "distribution": [
                {
                    "action_type": ap.action_type,
                    "detail": ap.skill_name or ap.switch_target or "",
                    "probability": round(ap.probability, 3),
                    "rationale": ap.rationale,
                }
                for ap in prediction.action_distribution[:8]
            ],
            "notes": prediction.notes,
        }
