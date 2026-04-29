from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..core.observation import ObservationState, ObservedPetState


@dataclass(slots=True)
class SkillSetCandidate:
    skills: list[str]
    score: float
    probability: float = 0.0
    rationale: list[str] = field(default_factory=list)


class OpponentModel:
    """Produces data-backed skill-set candidates for unknown opponent pets."""

    def __init__(self, data_loader=None, data_dir: str | None = None) -> None:
        self._data_loader = data_loader
        self._data_dir = data_dir

    def infer_skill_sets(
        self,
        pet_name: str,
        observed_skills: list[str],
        observation: ObservationState,
        top_k: int = 3,
    ) -> list[SkillSetCandidate]:
        data_loader = self._ensure_data_loader()
        if data_loader is None:
            return [
                SkillSetCandidate(
                    skills=list(observed_skills),
                    score=0.2,
                    probability=1.0,
                    rationale=[
                        "未能加载 DataLoader，当前只保留已观测技能",
                    ],
                )
            ]

        pet_template = data_loader.pets.get(pet_name)
        if pet_template is None:
            return [
                SkillSetCandidate(
                    skills=list(observed_skills),
                    score=0.2,
                    probability=1.0,
                    rationale=[f"数据中未找到精灵: {pet_name}"],
                )
            ]

        learnable_skills = self.get_learnable_skills(pet_name)
        observed_pet = self._get_observed_pet(pet_name, observation)
        if len(observed_skills) >= 4:
            return [
                SkillSetCandidate(
                    skills=observed_skills[:4],
                    score=1.0,
                    probability=1.0,
                    rationale=["已观测技能已足够组成完整技能组"],
                )
            ][:top_k]

        inferred_observed = list(observed_pet.inferred_skills) if observed_pet else []
        for skill_name in inferred_observed:
            if skill_name not in observed_skills and skill_name not in learnable_skills:
                learnable_skills.append(skill_name)

        active_energy = self._get_observed_energy(pet_name, observation)
        ranked_skills = self._rank_learnable_skills(
            pet_name=pet_name,
            observed_skills=observed_skills,
            learnable_skills=learnable_skills,
            active_energy=active_energy,
            observation=observation,
            observed_pet=observed_pet,
        )

        balanced = self._build_balanced_candidate(observed_skills, ranked_skills)
        attack_first = self._build_attack_first_candidate(observed_skills, ranked_skills)
        utility_first = self._build_utility_first_candidate(observed_skills, ranked_skills)

        candidates = [balanced, attack_first, utility_first]
        deduped: list[SkillSetCandidate] = []
        seen: set[tuple[str, ...]] = set()
        for candidate in candidates:
            skill_key = tuple(candidate.skills)
            if skill_key in seen:
                continue
            seen.add(skill_key)
            deduped.append(candidate)
        trimmed = deduped[:top_k]
        self._normalize_candidate_probabilities(trimmed)
        return trimmed

    def get_learnable_skills(self, pet_name: str) -> list[str]:
        data_loader = self._ensure_data_loader()
        if data_loader is None or pet_name not in data_loader.pets:
            return []
        raw_skills = data_loader.pets[pet_name].learnable_skills
        return self._normalize_skill_names(raw_skills)

    def _ensure_data_loader(self):
        if self._data_loader is not None:
            return self._data_loader

        try:
            from data_loader import DataLoader
            from paths import get_default_data_dir
        except ImportError:
            return None

        default_data_dir = self._data_dir
        if default_data_dir is None:
            default_data_dir = str(get_default_data_dir())

        loader = DataLoader(data_dir=default_data_dir)
        loader.load_all()
        self._data_loader = loader
        return self._data_loader

    def _get_observed_energy(self, pet_name: str, observation: ObservationState) -> int | None:
        for pet in observation.opponent_side.pets.values():
            if pet.pet_name == pet_name:
                return pet.energy
        return None

    def _get_observed_pet(self, pet_name: str, observation: ObservationState) -> ObservedPetState | None:
        return observation.opponent_side.pets.get(pet_name)

    def _rank_learnable_skills(
        self,
        *,
        pet_name: str,
        observed_skills: list[str],
        learnable_skills: list[str],
        active_energy: int | None,
        observation: ObservationState,
        observed_pet: ObservedPetState | None,
    ) -> list[tuple[str, float, list[str]]]:
        data_loader = self._ensure_data_loader()
        if data_loader is None:
            return []

        pet_template = data_loader.pets.get(pet_name)
        pet_types = set(pet_template.types if pet_template else [])
        ranked: list[tuple[str, float, list[str]]] = []

        for skill_name in learnable_skills:
            if skill_name in observed_skills:
                continue
            skill = data_loader.skills.get(skill_name)
            if skill is None:
                continue

            score = 0.0
            rationale: list[str] = []

            if skill.element in pet_types:
                score += 3.0
                rationale.append("本系技能")

            if skill.category.value == "attack":
                score += 2.0
                rationale.append("攻击技能")
            elif skill.category.value == "defense":
                score += 1.0
                rationale.append("防御技能")
            else:
                score += 0.8
                rationale.append("状态技能")

            if active_energy is not None:
                if skill.energy_cost <= active_energy:
                    score += 1.0
                    rationale.append("当前能量可释放")
                elif skill.energy_cost <= active_energy + 2:
                    score += 0.3
                    rationale.append("短期内可释放")
                else:
                    score -= 0.5
                    rationale.append("当前能量偏紧")

            if getattr(skill, "priority", 0) > 0:
                score += 0.5
                rationale.append("有先手等级")

            if getattr(skill, "hits", 1) > 1:
                score += 0.3
                rationale.append("多段技能")

            score_ref = {"value": score}
            self._apply_inference_biases(
                pet_name=pet_name,
                skill_name=skill_name,
                score_ref=score_ref,
                rationale=rationale,
                observation=observation,
                observed_pet=observed_pet,
            )
            score = score_ref["value"]

            ranked.append((skill_name, score, rationale))

        ranked.sort(key=lambda item: (-item[1], item[0]))
        return ranked

    def _normalize_skill_names(self, raw_skills) -> list[str]:
        normalized: list[str] = []
        for item in raw_skills or []:
            skill_name = None
            if isinstance(item, str):
                skill_name = item
            elif isinstance(item, dict):
                skill_name = item.get("name")
            if skill_name and skill_name not in normalized:
                normalized.append(skill_name)
        return normalized

    def _build_balanced_candidate(
        self,
        observed_skills: list[str],
        ranked_skills: list[tuple[str, float, list[str]]],
    ) -> SkillSetCandidate:
        chosen = list(observed_skills)
        rationale = ["平衡型补全：优先使用综合评分最高的技能"]
        for skill_name, score, skill_rationale in ranked_skills:
            if len(chosen) >= 4:
                break
            chosen.append(skill_name)
            rationale.append(f"{skill_name}: score={score:.1f}, {'/'.join(skill_rationale)}")
        score = self._candidate_score(chosen, ranked_skills, bias=1.0)
        return SkillSetCandidate(
            skills=chosen[:4],
            score=score,
            rationale=rationale,
        )

    def _build_attack_first_candidate(
        self,
        observed_skills: list[str],
        ranked_skills: list[tuple[str, float, list[str]]],
    ) -> SkillSetCandidate:
        chosen = list(observed_skills)
        rationale = ["进攻型补全：优先挑选攻击技能"]
        attack_pool = [item for item in ranked_skills if "攻击技能" in item[2]]
        fallback_pool = [item for item in ranked_skills if item not in attack_pool]
        for pool in (attack_pool, fallback_pool):
            for skill_name, score, skill_rationale in pool:
                if len(chosen) >= 4:
                    break
                if skill_name in chosen:
                    continue
                chosen.append(skill_name)
                rationale.append(f"{skill_name}: score={score:.1f}, {'/'.join(skill_rationale)}")
        score = self._candidate_score(chosen, ranked_skills, bias=0.92)
        return SkillSetCandidate(
            skills=chosen[:4],
            score=score,
            rationale=rationale,
        )

    def _build_utility_first_candidate(
        self,
        observed_skills: list[str],
        ranked_skills: list[tuple[str, float, list[str]]],
    ) -> SkillSetCandidate:
        chosen = list(observed_skills)
        rationale = ["功能型补全：优先保留防御/状态技能以覆盖应对空间"]
        utility_pool = [
            item for item in ranked_skills
            if "防御技能" in item[2] or "状态技能" in item[2]
        ]
        fallback_pool = [item for item in ranked_skills if item not in utility_pool]
        for pool in (utility_pool, fallback_pool):
            for skill_name, score, skill_rationale in pool:
                if len(chosen) >= 4:
                    break
                if skill_name in chosen:
                    continue
                chosen.append(skill_name)
                rationale.append(f"{skill_name}: score={score:.1f}, {'/'.join(skill_rationale)}")
        score = self._candidate_score(chosen, ranked_skills, bias=0.88)
        return SkillSetCandidate(
            skills=chosen[:4],
            score=score,
            rationale=rationale,
        )

    def _candidate_score(
        self,
        chosen: list[str],
        ranked_skills: list[tuple[str, float, list[str]]],
        *,
        bias: float,
    ) -> float:
        rank_map = {skill_name: score for skill_name, score, _ in ranked_skills}
        base = sum(rank_map.get(skill_name, 1.0) for skill_name in chosen[:4])
        if not chosen:
            return 0.1
        return max(0.1, base * bias / max(1, len(chosen[:4])))

    def _normalize_candidate_probabilities(self, candidates: list[SkillSetCandidate]) -> None:
        if not candidates:
            return
        weights = [max(0.01, candidate.score) for candidate in candidates]
        total = sum(weights)
        if total <= 0:
            uniform = 1.0 / len(candidates)
            for candidate in candidates:
                candidate.probability = uniform
            return
        for candidate, weight in zip(candidates, weights):
            candidate.probability = weight / total
            candidate.rationale.append(f"candidate_probability={candidate.probability:.3f}")

    def _apply_inference_biases(
        self,
        *,
        pet_name: str,
        skill_name: str,
        score_ref: dict[str, float],
        rationale: list[str],
        observation: ObservationState,
        observed_pet: ObservedPetState | None,
    ) -> None:
        skill = self._ensure_data_loader().skills.get(skill_name)
        if skill is None:
            return

        if observed_pet is not None:
            if observed_pet.inferred_natures.get("物攻强化性格", 0) >= 0.5 and skill.damage_type and skill.damage_type.value == "physical":
                score_ref["value"] += 0.8
                rationale.append("物攻推断支持")
            if observed_pet.inferred_natures.get("魔攻强化性格", 0) >= 0.5 and skill.damage_type and skill.damage_type.value == "magical":
                score_ref["value"] += 0.8
                rationale.append("魔攻推断支持")
            if observed_pet.inferred_ev_spreads.get("速度投入", 0) >= 0.5 and getattr(skill, "priority", 0) > 0:
                score_ref["value"] += 0.4
                rationale.append("速度投入与先手技能相容")
            if observed_pet.inferred_trait_flags.get("存在迅捷/优先效果", 0) >= 0.5 and getattr(skill, "priority", 0) > 0:
                score_ref["value"] += 0.6
                rationale.append("迅捷证据支持先手技能")
            if observed_pet.inferred_trait_flags.get("后排资源恢复特性/效果", 0) >= 0.6 and skill.category.value in {"status", "defense"}:
                score_ref["value"] += 0.35
                rationale.append("后排资源恢复倾向配合功能技能")

        copied_names = {
            evidence.copied_skill_name
            for evidence in observation.copy_skill_evidence
            if evidence.copied_from_pet == pet_name or evidence.copied_from_pet is None
        }
        if skill_name in copied_names:
            score_ref["value"] += 2.5
            rationale.append("复制技能证据直接支持")

        quick_support = any(
            evidence.pet_name == pet_name and (evidence.priority_bonus or 0) > 0
            for evidence in observation.quick_effect_evidence
        )
        if quick_support and getattr(skill, "priority", 0) > 0:
            score_ref["value"] += 0.5
            rationale.append("迅捷证据增强先手技能概率")

        bench_support = any(
            evidence.pet_name == pet_name and evidence.energy is not None
            for evidence in observation.bench_resource_evidence
        )
        if bench_support and skill.energy_cost >= 3:
            score_ref["value"] += 0.25
            rationale.append("后排能量证据支持高能耗技能")
