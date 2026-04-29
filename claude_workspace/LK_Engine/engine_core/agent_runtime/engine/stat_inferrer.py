from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ..core.observation import (
    BenchResourceEvidence,
    CopySkillEvidence,
    DamageInferenceEvidence,
    ObservationState,
    QuickEffectEvidence,
    SpeedEvidence,
    StatRange,
)


@dataclass(slots=True)
class InferenceRange:
    min_value: float | None = None
    max_value: float | None = None
    confidence: float = 0.0
    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PetInferenceSummary:
    pet_name: str
    speed_range: InferenceRange = field(default_factory=InferenceRange)
    physical_attack_range: InferenceRange = field(default_factory=InferenceRange)
    magical_attack_range: InferenceRange = field(default_factory=InferenceRange)
    physical_defense_range: InferenceRange = field(default_factory=InferenceRange)
    magical_defense_range: InferenceRange = field(default_factory=InferenceRange)
    hp_range: InferenceRange = field(default_factory=InferenceRange)
    likely_natures: dict[str, float] = field(default_factory=dict)
    likely_ev_spreads: dict[str, float] = field(default_factory=dict)
    likely_traits: dict[str, float] = field(default_factory=dict)
    likely_skill_synergies: dict[str, float] = field(default_factory=dict)


class StatInferrer:
    """Collects evidence and produces coarse stat/trait/skill inferences.

    这一层当前先做证据归档和接口设计，不强行给出复杂数值推断。
    后续应逐步接入：
    - 出手顺序反推速度/性格/加点
    - 伤害与剩余血量反推双攻/双防/生命
    - 复制技能、后排资源恢复、迅捷效果等特殊证据
    """

    def __init__(self, data_loader=None, data_dir: str | None = None) -> None:
        self._data_loader = data_loader
        self._data_dir = data_dir
        self._observation: ObservationState | None = None
        self._speed_evidence: dict[str, list[SpeedEvidence]] = {}
        self._damage_evidence: dict[str, list[DamageInferenceEvidence]] = {}
        self._copy_skill_evidence: dict[str, list[CopySkillEvidence]] = {}
        self._bench_resource_evidence: dict[str, list[BenchResourceEvidence]] = {}
        self._quick_effect_evidence: dict[str, list[QuickEffectEvidence]] = {}

    def record_speed_evidence(self, evidence: SpeedEvidence) -> None:
        self._speed_evidence.setdefault(evidence.opponent_pet, []).append(evidence)

    def record_damage_evidence(self, evidence: DamageInferenceEvidence) -> None:
        self._damage_evidence.setdefault(evidence.attacker, []).append(evidence)
        self._damage_evidence.setdefault(evidence.defender, []).append(evidence)

    def record_copy_skill_evidence(self, evidence: CopySkillEvidence) -> None:
        self._copy_skill_evidence.setdefault(evidence.actor_pet, []).append(evidence)

    def record_bench_resource_evidence(self, evidence: BenchResourceEvidence) -> None:
        self._bench_resource_evidence.setdefault(evidence.pet_name, []).append(evidence)

    def record_quick_effect_evidence(self, evidence: QuickEffectEvidence) -> None:
        self._quick_effect_evidence.setdefault(evidence.pet_name, []).append(evidence)

    def infer_pet(self, pet_name: str) -> PetInferenceSummary:
        summary = PetInferenceSummary(pet_name=pet_name)
        self._seed_ranges_from_template(pet_name, summary)
        self._infer_speed(pet_name, summary)
        self._infer_attack_defense(pet_name, summary)
        self._infer_special_signals(pet_name, summary)
        return summary

    def apply_to_observation(self, observation: ObservationState) -> None:
        self.refresh_from_observation(observation)
        for side_state in (observation.my_side, observation.opponent_side):
            for pet_name, pet in side_state.pets.items():
                summary = self.infer_pet(pet_name)
                pet.stat_ranges["速度"] = self._to_stat_range(summary.speed_range)
                pet.stat_ranges["物攻"] = self._to_stat_range(summary.physical_attack_range)
                pet.stat_ranges["魔攻"] = self._to_stat_range(summary.magical_attack_range)
                pet.stat_ranges["物防"] = self._to_stat_range(summary.physical_defense_range)
                pet.stat_ranges["魔防"] = self._to_stat_range(summary.magical_defense_range)
                pet.stat_ranges["生命"] = self._to_stat_range(summary.hp_range)
                pet.inferred_natures = dict(summary.likely_natures)
                pet.inferred_ev_spreads = dict(summary.likely_ev_spreads)
                pet.inferred_trait_flags = dict(summary.likely_traits)

    def refresh_from_observation(self, observation: ObservationState) -> None:
        self._observation = observation
        self._speed_evidence.clear()
        self._damage_evidence.clear()
        self._copy_skill_evidence.clear()
        self._bench_resource_evidence.clear()
        self._quick_effect_evidence.clear()

        for evidence in observation.speed_evidence:
            self.record_speed_evidence(evidence)
        for evidence in observation.damage_evidence:
            self.record_damage_evidence(evidence)
        for evidence in observation.copy_skill_evidence:
            self.record_copy_skill_evidence(evidence)
        for evidence in observation.bench_resource_evidence:
            self.record_bench_resource_evidence(evidence)
        for evidence in observation.quick_effect_evidence:
            self.record_quick_effect_evidence(evidence)

    def _infer_speed(self, pet_name: str, summary: PetInferenceSummary) -> None:
        evidences = self._speed_evidence.get(pet_name, [])
        if not evidences:
            return
        summary.speed_range.confidence = min(0.8, 0.2 + 0.1 * len(evidences))
        summary.speed_range.rationale.append(
            f"基于 {len(evidences)} 条出手顺序证据估计速度范围"
        )
        moved_first_count = sum(1 for e in evidences if e.my_moved_first is False)
        moved_last_count = sum(1 for e in evidences if e.my_moved_first is True)
        if any(e.quick_effect_active for e in evidences):
            summary.likely_traits["存在迅捷/优先效果"] = 0.6
            summary.speed_range.rationale.append("检测到迅捷或额外先手效果")
        if moved_first_count > moved_last_count:
            summary.likely_natures["速度强化性格"] = 0.55
            summary.likely_ev_spreads["速度投入"] = 0.6
            self._shrink_range(summary.speed_range, upper_bias=1.15, lower_bias=0.95)
        elif moved_last_count > moved_first_count:
            summary.likely_natures["非速度强化性格"] = 0.45
            self._shrink_range(summary.speed_range, upper_bias=1.05, lower_bias=0.85)

        anchored = self._infer_speed_against_my_pet(pet_name, evidences)
        if anchored is not None:
            self._merge_estimate(summary.speed_range, anchored * 0.92, anchored * 1.08)
            summary.speed_range.rationale.append(
                f"根据与我方当前速度锚点比较，估计速度中心约为 {anchored:.1f}"
            )

    def _infer_attack_defense(self, pet_name: str, summary: PetInferenceSummary) -> None:
        evidences = self._damage_evidence.get(pet_name, [])
        if not evidences:
            return
        attack_evidence = [e for e in evidences if e.attacker == pet_name]
        defend_evidence = [e for e in evidences if e.defender == pet_name]

        if attack_evidence:
            confidence = min(0.8, 0.15 + 0.08 * len(attack_evidence))
            physical_count = 0
            magical_count = 0
            for evidence in attack_evidence:
                category = self._get_damage_category(evidence.skill_name)
                if category == "physical":
                    physical_count += 1
                elif category == "magical":
                    magical_count += 1
            summary.physical_attack_range.confidence = confidence
            summary.magical_attack_range.confidence = confidence
            summary.physical_attack_range.rationale.append(
                f"基于 {len(attack_evidence)} 条主动造成伤害证据估计双攻"
            )
            if physical_count > magical_count:
                summary.likely_natures["物攻强化性格"] = 0.55
                summary.likely_ev_spreads["物攻投入"] = 0.6
                self._shrink_range(summary.physical_attack_range, upper_bias=1.18, lower_bias=0.95)
            elif magical_count > physical_count:
                summary.likely_natures["魔攻强化性格"] = 0.55
                summary.likely_ev_spreads["魔攻投入"] = 0.6
                self._shrink_range(summary.magical_attack_range, upper_bias=1.18, lower_bias=0.95)

            attack_estimates = self._estimate_attack_ranges(pet_name, attack_evidence)
            if attack_estimates["physical"]:
                lo, hi = self._combine_numeric_samples(attack_estimates["physical"])
                self._merge_estimate(summary.physical_attack_range, lo, hi)
                summary.physical_attack_range.rationale.append(
                    f"根据伤害公式反推物攻约在 {lo:.1f}~{hi:.1f}"
                )
            if attack_estimates["magical"]:
                lo, hi = self._combine_numeric_samples(attack_estimates["magical"])
                self._merge_estimate(summary.magical_attack_range, lo, hi)
                summary.magical_attack_range.rationale.append(
                    f"根据伤害公式反推魔攻约在 {lo:.1f}~{hi:.1f}"
                )

        if defend_evidence:
            confidence = min(0.75, 0.1 + 0.06 * len(defend_evidence))
            summary.hp_range.confidence = confidence
            summary.physical_defense_range.confidence = confidence
            summary.magical_defense_range.confidence = confidence
            summary.physical_defense_range.rationale.append(
                f"基于 {len(defend_evidence)} 条受伤害与剩余血量证据估计双防/生命"
            )
            if any(e.target_hp_percent_after is not None and e.target_hp_percent_after > 60 for e in defend_evidence):
                summary.likely_ev_spreads["生命/双防投入"] = 0.52
                self._shrink_range(summary.hp_range, upper_bias=1.2, lower_bias=0.95)
                self._shrink_range(summary.physical_defense_range, upper_bias=1.15, lower_bias=0.95)
                self._shrink_range(summary.magical_defense_range, upper_bias=1.15, lower_bias=0.95)

            defense_estimates, hp_estimates = self._estimate_defense_hp_ranges(pet_name, defend_evidence)
            if defense_estimates["physical"]:
                lo, hi = self._combine_numeric_samples(defense_estimates["physical"])
                self._merge_estimate(summary.physical_defense_range, lo, hi)
                summary.physical_defense_range.rationale.append(
                    f"根据受伤公式反推物防约在 {lo:.1f}~{hi:.1f}"
                )
            if defense_estimates["magical"]:
                lo, hi = self._combine_numeric_samples(defense_estimates["magical"])
                self._merge_estimate(summary.magical_defense_range, lo, hi)
                summary.magical_defense_range.rationale.append(
                    f"根据受伤公式反推魔防约在 {lo:.1f}~{hi:.1f}"
                )
            if hp_estimates:
                lo, hi = self._combine_numeric_samples(hp_estimates)
                self._merge_estimate(summary.hp_range, lo, hi)
                summary.hp_range.rationale.append(
                    f"根据伤害与剩余血量百分比反推生命约在 {lo:.1f}~{hi:.1f}"
                )

    def _infer_special_signals(self, pet_name: str, summary: PetInferenceSummary) -> None:
        copies = self._copy_skill_evidence.get(pet_name, [])
        if copies:
            summary.likely_skill_synergies["复制到的技能可能存在于敌方技能组"] = 0.75
            summary.physical_attack_range.rationale.append("复制技能事件可反向约束对手技能组")

        bench_events = self._bench_resource_evidence.get(pet_name, [])
        if bench_events:
            summary.likely_traits["后排资源恢复特性/效果"] = 0.7
            summary.hp_range.rationale.append("检测到后排血量/能量变化证据")

        quick_events = self._quick_effect_evidence.get(pet_name, [])
        if quick_events:
            summary.likely_traits["迅捷来源未消耗完"] = 0.65
            summary.speed_range.rationale.append("检测到迅捷相关证据")

    def _seed_ranges_from_template(self, pet_name: str, summary: PetInferenceSummary) -> None:
        loader = self._ensure_data_loader()
        if loader is None:
            return
        template = loader.pets.get(pet_name)
        if template is None:
            return
        stats = template.stats
        self._seed_range(summary.hp_range, stats.get("生命"))
        self._seed_range(summary.physical_attack_range, stats.get("物攻"))
        self._seed_range(summary.magical_attack_range, stats.get("魔攻"))
        self._seed_range(summary.physical_defense_range, stats.get("物防"))
        self._seed_range(summary.magical_defense_range, stats.get("魔防"))
        self._seed_range(summary.speed_range, stats.get("速度"))

    def _seed_range(self, target: InferenceRange, base_value) -> None:
        if base_value is None:
            return
        base = float(base_value)
        target.min_value = round(base * 0.8, 2)
        target.max_value = round(base * 1.2, 2)
        target.confidence = max(target.confidence, 0.15)
        target.rationale.append(f"以模板种族值 {base_value} 为初始估计中心")

    def _shrink_range(self, target: InferenceRange, *, upper_bias: float, lower_bias: float) -> None:
        if target.min_value is None or target.max_value is None:
            return
        center = (target.min_value + target.max_value) / 2
        target.min_value = round(center * lower_bias, 2)
        target.max_value = round(center * upper_bias, 2)

    def _merge_estimate(self, target: InferenceRange, new_min: float, new_max: float) -> None:
        if target.min_value is None or target.max_value is None:
            target.min_value = round(new_min, 2)
            target.max_value = round(new_max, 2)
            return
        merged_min = max(target.min_value, new_min)
        merged_max = min(target.max_value, new_max)
        if merged_min <= merged_max:
            target.min_value = round(merged_min, 2)
            target.max_value = round(merged_max, 2)
        else:
            center = (new_min + new_max) / 2
            span = abs(new_max - new_min) / 2
            target.min_value = round(center - span, 2)
            target.max_value = round(center + span, 2)

    def _infer_speed_against_my_pet(self, pet_name: str, evidences: list[SpeedEvidence]) -> float | None:
        loader = self._ensure_data_loader()
        if loader is None:
            return None
        estimates: list[float] = []
        for evidence in evidences:
            my_template = loader.pets.get(evidence.my_pet)
            if my_template is None:
                continue
            my_speed = float(my_template.stats.get("速度", 0))
            if my_speed <= 0:
                continue
            if evidence.quick_effect_active:
                continue
            if evidence.my_priority is not None and evidence.opponent_priority is not None:
                if evidence.my_priority != evidence.opponent_priority:
                    continue
            if evidence.my_moved_first is False:
                estimates.append(my_speed * 1.05)
            elif evidence.my_moved_first is True:
                estimates.append(my_speed * 0.95)
        if not estimates:
            return None
        return sum(estimates) / len(estimates)

    def _estimate_attack_ranges(
        self,
        pet_name: str,
        evidences: list[DamageInferenceEvidence],
    ) -> dict[str, list[float]]:
        results = {"physical": [], "magical": []}
        loader = self._ensure_data_loader()
        if loader is None:
            return results
        for evidence in evidences:
            skill = loader.skills.get(evidence.skill_name)
            defender = loader.pets.get(evidence.defender)
            if skill is None or defender is None or not evidence.observed_damage:
                continue
            category = self._get_damage_category(evidence.skill_name)
            if category == "physical":
                defense = float(defender.stats.get("物防", 1))
            elif category == "magical":
                defense = float(defender.stats.get("魔防", 1))
            else:
                continue

            multiplier = 0.9 * max(1, skill.base_power)
            multiplier *= self._estimate_stab(skill.element, pet_name)
            multiplier *= self._estimate_type_effectiveness(skill.element, evidence.defender)
            multiplier *= self._estimate_weather_bonus(skill.element)
            if multiplier <= 0:
                continue
            attack = evidence.observed_damage * max(1.0, defense) / multiplier
            results[category].append(float(attack))
        return results

    def _estimate_defense_hp_ranges(
        self,
        pet_name: str,
        evidences: list[DamageInferenceEvidence],
    ) -> tuple[dict[str, list[float]], list[float]]:
        loader = self._ensure_data_loader()
        defense_results = {"physical": [], "magical": []}
        hp_estimates: list[float] = []
        if loader is None:
            return defense_results, hp_estimates

        for evidence in evidences:
            skill = loader.skills.get(evidence.skill_name)
            attacker = loader.pets.get(evidence.attacker)
            if skill is None or attacker is None or not evidence.observed_damage:
                continue
            category = self._get_damage_category(evidence.skill_name)
            if category == "physical":
                attack = float(attacker.stats.get("物攻", 1))
            elif category == "magical":
                attack = float(attacker.stats.get("魔攻", 1))
            else:
                continue

            multiplier = 0.9 * max(1, skill.base_power)
            multiplier *= self._estimate_stab(skill.element, evidence.attacker)
            multiplier *= self._estimate_type_effectiveness(skill.element, pet_name)
            multiplier *= self._estimate_weather_bonus(skill.element)
            if evidence.observed_damage <= 0:
                continue
            defense = (attack * multiplier) / evidence.observed_damage
            defense_results[category].append(float(defense))

            if evidence.observed_hp_drop_percent:
                hp_value = evidence.observed_damage / (float(evidence.observed_hp_drop_percent) / 100.0)
                hp_estimates.append(float(hp_value))

        return defense_results, hp_estimates

    def _combine_numeric_samples(self, values: Iterable[float]) -> tuple[float, float]:
        samples = [float(v) for v in values if v is not None]
        if not samples:
            return 0.0, 0.0
        center = sum(samples) / len(samples)
        spread = max(3.0, center * 0.12)
        return center - spread, center + spread

    def _estimate_stab(self, skill_element: str, attacker_name: str) -> float:
        loader = self._ensure_data_loader()
        if loader is None:
            return 1.0
        pet = loader.pets.get(attacker_name)
        if pet is None:
            return 1.0
        return 1.5 if skill_element in pet.types else 1.0

    def _estimate_type_effectiveness(self, skill_element: str, defender_name: str) -> float:
        loader = self._ensure_data_loader()
        if loader is None:
            return 1.0
        defender = loader.pets.get(defender_name)
        if defender is None:
            return 1.0
        return loader.get_combined_type_effectiveness(skill_element, defender.types)

    def _estimate_weather_bonus(self, skill_element: str) -> float:
        if self._observation is None:
            return 1.0
        if self._observation.weather == "下雨" and skill_element == "水":
            return 1.5
        return 1.0

    def _get_damage_category(self, skill_name: str) -> str | None:
        loader = self._ensure_data_loader()
        if loader is None:
            return None
        skill = loader.skills.get(skill_name)
        if skill is None or skill.damage_type is None:
            return None
        return skill.damage_type.value

    def _to_stat_range(self, source: InferenceRange) -> StatRange:
        return StatRange(
            min_value=source.min_value,
            max_value=source.max_value,
            confidence=source.confidence,
        )

    def _ensure_data_loader(self):
        if self._data_loader is not None:
            return self._data_loader

        try:
            from data_loader import DataLoader
            from paths import get_default_data_dir
        except ImportError:
            return None

        data_dir = self._data_dir
        if data_dir is None:
            data_dir = str(get_default_data_dir())

        loader = DataLoader(data_dir=data_dir)
        loader.load_all()
        self._data_loader = loader
        return self._data_loader
