from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..core.observation import ObservationState, ObservedPetState
from .opponent_model import OpponentModel


@dataclass(slots=True)
class InferredBattleState:
    battle_state: object | None
    assumptions: list[str] = field(default_factory=list)
    skill_probability: float = 0.0
    skill_signature: tuple[str, ...] = field(default_factory=tuple)
    profile_probability: float = 1.0
    profile_label: str = "center"

    @property
    def confidence(self) -> float:
        return self.belief_weight

    @property
    def belief_weight(self) -> float:
        return max(0.0, float(self.skill_probability)) * max(0.0, float(self.profile_probability))


@dataclass(slots=True)
class PetAssemblyPreview:
    pet_name: str
    source_side: str
    hp_strategy: str
    skill_strategy: str
    unresolved_fields: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AssemblyPlan:
    turn_strategy: str
    weather_strategy: str
    hearts_strategy: str
    field_mark_strategy: str
    my_pet_previews: list[PetAssemblyPreview] = field(default_factory=list)
    opponent_pet_previews: list[PetAssemblyPreview] = field(default_factory=list)
    unresolved_global_fields: list[str] = field(default_factory=list)


class StateAssembler:
    """Assembles minimal BattleState candidates from ObservationState."""

    POSITIVE_MARKS = {
        "charge_mark",
        "蓄电印记",
        "momentum_mark",
        "蓄势印记",
        "attack_mark",
        "攻击印记",
        "wind_mark",
        "风起印记",
        "dragon_bite_mark",
        "龙噬印记",
        "moist_mark",
        "湿润印记",
        "photosynthesis_mark",
        "光合印记",
    }

    NEGATIVE_MARKS = {
        "star_fall_mark",
        "星陨印记",
        "descent_mark",
        "降灵印记",
        "thorn",
        "棘刺",
        "frost_mark",
        "凝霜印记",
        "slow_mark",
        "迟缓印记",
    }

    STATUS_NAME_MAP = {
        "poison": "POISON",
        "中毒": "POISON",
        "poison_mark": "POISON_MARK",
        "中毒印记": "POISON_MARK",
        "burn": "BURN",
        "灼烧": "BURN",
        "freeze": "FREEZE",
        "冻结": "FREEZE",
        "parasite": "PARASITE",
        "寄生": "PARASITE",
        "star_fall_mark": "STAR_FALL_MARK",
        "星陨印记": "STAR_FALL_MARK",
        "descent_mark": "DESCENT_MARK",
        "降灵印记": "DESCENT_MARK",
        "thorn": "THORN",
        "棘刺": "THORN",
        "frost_mark": "FROST_MARK",
        "凝霜印记": "FROST_MARK",
        "photosynthesis_mark": "PHOTOSYNTHESIS_MARK",
        "光合印记": "PHOTOSYNTHESIS_MARK",
        "charge_mark": "CHARGE_MARK",
        "蓄电印记": "CHARGE_MARK",
        "momentum_mark": "MOMENTUM_MARK",
        "蓄势印记": "MOMENTUM_MARK",
        "attack_mark": "ATTACK_MARK",
        "攻击印记": "ATTACK_MARK",
        "wind_mark": "WIND_MARK",
        "风起印记": "WIND_MARK",
        "dragon_bite_mark": "DRAGON_BITE_MARK",
        "龙噬印记": "DRAGON_BITE_MARK",
        "moist_mark": "MOIST_MARK",
        "湿润印记": "MOIST_MARK",
        "slow_mark": "SLOW_MARK",
        "迟缓印记": "SLOW_MARK",
    }

    def __init__(self, data_loader=None, data_dir: str | None = None) -> None:
        self._data_loader = data_loader
        self._data_dir = data_dir
        self._opponent_model = OpponentModel(data_loader=data_loader, data_dir=data_dir)

    def describe_plan(self, observation: ObservationState) -> AssemblyPlan:
        return AssemblyPlan(
            turn_strategy="直接使用 ObservationState.turn；若缺失则回退到 1",
            weather_strategy="直接使用 ObservationState.weather",
            hearts_strategy="优先使用 side.hearts；若缺失则回退到 BattleState 默认值",
            field_mark_strategy="当前仅把当前出战宠可观测 marks 映射到 BattleState 单正单负槽位",
            my_pet_previews=[
                self._preview_pet(pet_name, "my", pet)
                for pet_name, pet in observation.my_side.pets.items()
            ],
            opponent_pet_previews=[
                self._preview_pet(pet_name, "opponent", pet)
                for pet_name, pet in observation.opponent_side.pets.items()
            ],
            unresolved_global_fields=[
                "场下精灵的细粒度状态还原仍为简化策略",
                "属性范围推断当前按区间中心值写回，不是完整概率分布",
            ],
        )

    def build_candidates(self, observation: ObservationState) -> list[InferredBattleState]:
        plan = self.describe_plan(observation)
        data_loader = self._ensure_data_loader()
        if data_loader is None:
            return [
                InferredBattleState(
                    battle_state=None,
                    assumptions=["DataLoader 加载失败，无法装配 BattleState"],
                    skill_probability=0.0,
                    profile_probability=0.0,
                )
            ]

        try:
            from core.models import BattleState, FieldMark, PlayerState, StatModifier
            from core.status_effects import StatusEffectType
        except ImportError:
            return [
                InferredBattleState(
                    battle_state=None,
                    assumptions=["未能导入 core.models / core.status_effects"],
                    skill_probability=0.0,
                    profile_probability=0.0,
                )
            ]

        my_ordered_names = self._ordered_pet_names(
            observation.my_side.active_pet,
            observation.my_side.pets.keys(),
        )
        opp_ordered_names = self._ordered_pet_names(
            observation.opponent_side.active_pet,
            observation.opponent_side.pets.keys(),
        )

        if not my_ordered_names or not opp_ordered_names:
            assumptions = list(plan.unresolved_global_fields)
            if not my_ordered_names:
                assumptions.append("我方未记录任何已观测精灵")
            if not opp_ordered_names:
                assumptions.append("对手未记录任何已观测精灵")
            return [
                InferredBattleState(
                    battle_state=None,
                    assumptions=assumptions,
                    skill_probability=0.0,
                    profile_probability=0.0,
                )
            ]

        missing_pet_names = [
            name for name in list(my_ordered_names) + list(opp_ordered_names)
            if name not in data_loader.pets
        ]
        if missing_pet_names:
            assumptions = list(plan.unresolved_global_fields)
            assumptions.append(f"数据中不存在以下精灵，无法装配: {', '.join(missing_pet_names)}")
            return [
                InferredBattleState(
                    battle_state=None,
                    assumptions=assumptions,
                    skill_probability=0.0,
                    profile_probability=0.0,
                )
            ]

        my_team = [
            self._assemble_pet_instance(
                pet_name=name,
                observed_pet=observation.my_side.pets[name],
                side_state=observation.my_side,
                fallback_skills=[],
                default_to_learnable=True,
                data_loader=data_loader,
                StatusEffectType=StatusEffectType,
                StatModifier=StatModifier,
            )
            for name in my_ordered_names
            if name in observation.my_side.pets
        ]

        active_opp_name = observation.opponent_side.active_pet or opp_ordered_names[0]
        active_opp_pet = observation.opponent_side.pets[active_opp_name]
        skill_candidates = self._opponent_model.infer_skill_sets(
            pet_name=active_opp_name,
            observed_skills=list(active_opp_pet.observed_skills),
            observation=observation,
            top_k=3,
        )

        inferred_states: list[InferredBattleState] = []
        for skill_candidate in skill_candidates:
            stat_profiles = self._build_stat_profiles(observation.opponent_side.pets.get(active_opp_name))
            profile_weights = self._profile_weights(stat_profiles)
            for profile, profile_weight in zip(stat_profiles, profile_weights):
                opp_team: list[object] = []
                assumptions = list(plan.unresolved_global_fields)
                assumptions.extend([f"对手当前出战技能候选: {', '.join(skill_candidate.skills) or '无'}"])
                assumptions.extend(skill_candidate.rationale)
                assumptions.append(f"对手属性剖面: {profile['label']}")

                for name in opp_ordered_names:
                    if name not in observation.opponent_side.pets:
                        continue
                    observed_pet = observation.opponent_side.pets[name]
                    fallback_skills = skill_candidate.skills if name == active_opp_name else list(
                        observed_pet.observed_skills or observed_pet.inferred_skills
                    )
                    pet_profile = profile if name == active_opp_name else None
                    pet_instance = self._assemble_pet_instance(
                        pet_name=name,
                        observed_pet=observed_pet,
                        side_state=observation.opponent_side,
                        fallback_skills=fallback_skills,
                        default_to_learnable=True,
                        data_loader=data_loader,
                        StatusEffectType=StatusEffectType,
                        StatModifier=StatModifier,
                        stat_profile=pet_profile,
                    )
                    opp_team.append(pet_instance)

                battle_state = BattleState(
                    player=PlayerState(team=my_team, active_index=0),
                    opponent=PlayerState(team=opp_team, active_index=0),
                    turn=max(1, observation.turn or 1),
                    weather=observation.weather,
                    field_effects=dict(observation.field_marks),
                )
                battle_state.player_hearts = observation.my_side.hearts or battle_state.player_hearts
                battle_state.opponent_hearts = (
                    observation.opponent_side.hearts or battle_state.opponent_hearts
                )
                self._apply_team_resources(battle_state.player.team_state, observation.my_side.team_resources)
                self._apply_team_resources(battle_state.opponent.team_state, observation.opponent_side.team_resources)

                self._apply_active_marks(
                    battle_state=battle_state,
                    observed_pet=observation.my_side.pets.get(observation.my_side.active_pet or my_ordered_names[0]),
                    is_player=True,
                    FieldMark=FieldMark,
                )
                self._apply_active_marks(
                    battle_state=battle_state,
                    observed_pet=observation.opponent_side.pets.get(active_opp_name),
                    is_player=False,
                    FieldMark=FieldMark,
                )

                inferred_states.append(
                    InferredBattleState(
                        battle_state=battle_state,
                        assumptions=assumptions,
                        skill_probability=min(0.97, max(0.03, float(skill_candidate.probability))),
                        skill_signature=tuple(skill_candidate.skills),
                        profile_probability=min(0.97, max(0.03, float(profile_weight))),
                        profile_label=str(profile["label"]),
                    )
                )

        return inferred_states or [
            InferredBattleState(
                battle_state=None,
                assumptions=["未生成任何候选 BattleState"],
                skill_probability=0.0,
                profile_probability=0.0,
            )
        ]

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
        self._opponent_model = OpponentModel(data_loader=loader, data_dir=data_dir)
        return self._data_loader

    def _ordered_pet_names(self, active_pet: str | None, names) -> list[str]:
        ordered = []
        names_list = list(names)
        if active_pet and active_pet in names_list:
            ordered.append(active_pet)
        for name in names_list:
            if name != active_pet:
                ordered.append(name)
        return ordered

    def _assemble_pet_instance(
        self,
        *,
        pet_name: str,
        observed_pet: ObservedPetState,
        side_state,
        fallback_skills: list[str],
        default_to_learnable: bool,
        data_loader,
        StatusEffectType,
        StatModifier,
        stat_profile: dict | None = None,
    ):
        from core.models import PetInstance

        template = data_loader.pets[pet_name]
        stats = self._assemble_stats(template.stats.copy(), observed_pet, stat_profile=stat_profile)
        max_hp = int(stats.get("生命", 100))
        hp_percent = self._resolve_hp_percent(observed_pet, side_state)
        current_hp = max(0, min(max_hp, int(max_hp * hp_percent / 100.0)))
        energy = self._resolve_energy(observed_pet, side_state)

        skill_names = self._choose_skill_names(
            observed_pet=observed_pet,
            fallback_skills=fallback_skills,
            learnable_skills=(
                self._normalize_skill_names(template.learnable_skills)
                if default_to_learnable else []
            ),
        )
        skills = [
            data_loader.skills[skill_name]
            for skill_name in skill_names
            if skill_name in data_loader.skills
        ]

        pet = PetInstance(
            template=template,
            current_hp=current_hp,
            max_hp=max_hp,
            stats=stats,
            skills=skills,
            current_energy=max(0, energy),
            stat_modifiers=StatModifier(),
            skill_cooldowns={},
            is_alive=(not observed_pet.fainted and current_hp > 0),
        )
        pet.just_entered = False
        pet.status_effects = self._map_status_effects(observed_pet, StatusEffectType)
        pet.freeze_stacks = int(pet.status_effects.get(StatusEffectType.FREEZE, 0))
        pet.priority_bonus = self._resolve_priority_bonus(observed_pet)
        return pet

    def _choose_skill_names(
        self,
        *,
        observed_pet: ObservedPetState,
        fallback_skills: list[str],
        learnable_skills: list[str],
    ) -> list[str]:
        chosen: list[str] = []
        for skill_name in observed_pet.observed_skills + observed_pet.inferred_skills + fallback_skills:
            if skill_name and skill_name not in chosen:
                chosen.append(skill_name)
            if len(chosen) >= 4:
                return chosen[:4]
        for skill_name in learnable_skills:
            if skill_name and skill_name not in chosen:
                chosen.append(skill_name)
            if len(chosen) >= 4:
                break
        return chosen[:4]

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

    def _assemble_stats(self, base_stats: dict, observed_pet: ObservedPetState, stat_profile: dict | None = None) -> dict:
        stats = dict(base_stats)
        if stat_profile and stat_profile.get("stats"):
            stats.update(stat_profile["stats"])
            return stats
        for stat_name, stat_range in observed_pet.stat_ranges.items():
            if stat_range.min_value is None or stat_range.max_value is None:
                continue
            stats[stat_name] = int(round((stat_range.min_value + stat_range.max_value) / 2))
        return stats

    def _resolve_hp_percent(self, observed_pet: ObservedPetState, side_state) -> float:
        if observed_pet.hp_percent is not None:
            return float(observed_pet.hp_percent)
        if observed_pet.pet_name in side_state.bench_hp_percent:
            return float(side_state.bench_hp_percent[observed_pet.pet_name])
        return 100.0

    def _resolve_energy(self, observed_pet: ObservedPetState, side_state) -> int:
        if observed_pet.energy is not None:
            return int(observed_pet.energy)
        if observed_pet.pet_name in side_state.bench_energy:
            return int(side_state.bench_energy[observed_pet.pet_name])
        return 10

    def _resolve_priority_bonus(self, observed_pet: ObservedPetState) -> int:
        quick_score = max(
            observed_pet.inferred_trait_flags.get("存在迅捷/优先效果", 0.0),
            observed_pet.inferred_trait_flags.get("迅捷来源未消耗完", 0.0),
        )
        if quick_score >= 0.7:
            return 1
        return 0

    def _apply_team_resources(self, team_state, resources: dict[str, int]) -> None:
        if not resources:
            return
        field_map = {
            "leader_evolution_uses": "leader_evolution_uses",
            "willpower_strike_uses": "willpower_strike_uses",
            "devotion_poison": "devotion_poison",
            "devotion_lifesteal": "devotion_lifesteal",
            "devotion_combo": "devotion_combo",
            "devotion_power": "devotion_power",
            "devotion_energy": "devotion_energy",
            "earth_skill_count": "earth_skill_count",
            "ice_skill_count": "ice_skill_count",
            "fire_skill_count": "fire_skill_count",
            "water_skill_count": "water_skill_count",
            "status_skill_count": "status_skill_count",
            "counter_success_count": "counter_success_count",
            "defense_skill_count": "defense_skill_count",
            "gather_energy_count": "gather_energy_count",
            "switch_count": "switch_count",
        }
        for source_key, target_key in field_map.items():
            if source_key in resources and hasattr(team_state, target_key):
                setattr(team_state, target_key, int(resources[source_key]))

    def _build_stat_profiles(self, observed_pet: ObservedPetState | None) -> list[dict]:
        if observed_pet is None:
            return [{"label": "center", "stats": {}}]

        center_stats = self._stat_profile_from_ranges(observed_pet, mode="center")
        profiles = [{"label": "center", "stats": center_stats}]

        has_signal = any(
            stat_range.confidence >= 0.25
            for stat_range in observed_pet.stat_ranges.values()
        )
        if not has_signal:
            return profiles

        threat_stats = self._stat_profile_from_ranges(observed_pet, mode="threat_high")
        if threat_stats != center_stats:
            profiles.append({"label": "threat_high", "stats": threat_stats})
        return profiles

    def _stat_profile_from_ranges(self, observed_pet: ObservedPetState, mode: str) -> dict[str, int]:
        stats: dict[str, int] = {}
        for stat_name, stat_range in observed_pet.stat_ranges.items():
            if stat_range.min_value is None or stat_range.max_value is None:
                continue
            low = float(stat_range.min_value)
            high = float(stat_range.max_value)
            if mode == "center":
                value = (low + high) / 2
            elif mode == "threat_high":
                if stat_name in {"速度", "物攻", "魔攻", "生命", "物防", "魔防"}:
                    value = high
                else:
                    value = (low + high) / 2
            else:
                value = (low + high) / 2
            stats[stat_name] = int(round(value))
        return stats

    def _profile_weights(self, profiles: list[dict]) -> list[float]:
        if len(profiles) <= 1:
            return [1.0]
        if len(profiles) == 2:
            return [0.7, 0.3]
        uniform = 1.0 / len(profiles)
        return [uniform] * len(profiles)

    def _map_status_effects(self, observed_pet: ObservedPetState, StatusEffectType) -> dict:
        mapped: dict = {}
        for raw_name, stacks in observed_pet.status_effects.items():
            normalized = self.STATUS_NAME_MAP.get(raw_name, raw_name)
            if hasattr(StatusEffectType, normalized):
                mapped[getattr(StatusEffectType, normalized)] = int(stacks)
        for raw_name, stacks in observed_pet.marks.items():
            normalized = self.STATUS_NAME_MAP.get(raw_name, raw_name)
            if hasattr(StatusEffectType, normalized):
                mapped[getattr(StatusEffectType, normalized)] = int(stacks)
        return mapped

    def _apply_active_marks(self, *, battle_state, observed_pet: ObservedPetState | None, is_player: bool, FieldMark) -> None:
        if observed_pet is None:
            return
        positive = None
        negative = None
        for mark_name, stacks in observed_pet.marks.items():
            if positive is None and mark_name in self.POSITIVE_MARKS:
                positive = FieldMark(
                    type_key=self._status_value(mark_name),
                    stacks=int(stacks),
                    is_positive=True,
                )
            elif negative is None and mark_name in self.NEGATIVE_MARKS:
                negative = FieldMark(
                    type_key=self._status_value(mark_name),
                    stacks=int(stacks),
                    is_positive=False,
                )
        if positive is not None:
            battle_state.set_mark(is_player, positive)
        if negative is not None:
            battle_state.set_mark(is_player, negative)

    def _status_value(self, raw_name: str) -> str:
        normalized = self.STATUS_NAME_MAP.get(raw_name, raw_name)
        normalized_lower = normalized.lower()
        return normalized_lower

    def _preview_pet(self, pet_name: str, side: str, pet: ObservedPetState) -> PetAssemblyPreview:
        hp_strategy = "按 hp_percent * 模板生命值装配 current_hp"
        skill_strategy = (
            "我方优先使用 observed_skills/inferred_skills，不足时回退 learnable_skills"
            if side == "my"
            else "对手优先 observed_skills，当前出战由 OpponentModel 补全，不足时回退 learnable_skills"
        )
        unresolved_fields: list[str] = []
        if pet.energy is None:
            unresolved_fields.append("energy 未知，将回退为默认 10")
        if side == "opponent" and not pet.observed_skills:
            unresolved_fields.append("尚无已观测技能")
        if pet.hp_percent is None:
            unresolved_fields.append("hp_percent 未知，将回退为 100%")
        if pet.marks:
            unresolved_fields.append("marks 仅精确映射当前出战宠的单正单负槽位")
        return PetAssemblyPreview(
            pet_name=pet_name,
            source_side=side,
            hp_strategy=hp_strategy,
            skill_strategy=skill_strategy,
            unresolved_fields=unresolved_fields,
        )
