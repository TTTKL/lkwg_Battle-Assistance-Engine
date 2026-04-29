from __future__ import annotations

from dataclasses import dataclass, field

from .events import BattleSide


@dataclass(slots=True)
class StatRange:
    min_value: float | None = None
    max_value: float | None = None
    confidence: float = 0.0


@dataclass(slots=True)
class DamageEvent:
    attacker: str
    defender: str
    skill_name: str
    observed_damage: int | None = None
    observed_hp_drop_percent: float | None = None
    category: str | None = None
    stab: bool | None = None
    type_effectiveness: float | None = None


@dataclass(slots=True)
class SpeedEvidence:
    turn: int
    my_pet: str
    opponent_pet: str
    my_action: str | None = None
    opponent_action: str | None = None
    my_priority: int | None = None
    opponent_priority: int | None = None
    my_moved_first: bool | None = None
    quick_effect_active: bool | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DamageInferenceEvidence:
    turn: int
    attacker: str
    defender: str
    skill_name: str
    source_side: BattleSide
    target_side: BattleSide
    observed_damage: int | None = None
    observed_hp_drop_percent: float | None = None
    target_hp_percent_after: float | None = None
    target_is_active: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SkillInferenceEvidence:
    turn: int
    pet_name: str
    observed_skill_name: str
    source: str
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CopySkillEvidence:
    turn: int
    actor_pet: str
    copied_skill_name: str
    copied_from_pet: str | None = None
    energy_discount: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BenchResourceEvidence:
    turn: int
    side: BattleSide
    pet_name: str
    hp_percent: float | None = None
    energy: int | None = None
    source_trait: str | None = None
    source_skill: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class QuickEffectEvidence:
    turn: int
    side: BattleSide
    pet_name: str
    source_skill: str | None = None
    source_trait: str | None = None
    priority_bonus: int | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ObservedPetState:
    pet_name: str
    side: BattleSide
    revealed: bool = False
    is_active: bool = False
    fainted: bool = False
    hp_percent: float | None = None
    energy: int | None = None
    status_effects: dict[str, int] = field(default_factory=dict)
    marks: dict[str, int] = field(default_factory=dict)
    buffs: dict[str, int] = field(default_factory=dict)
    debuffs: dict[str, int] = field(default_factory=dict)
    observed_skills: list[str] = field(default_factory=list)
    inferred_skills: list[str] = field(default_factory=list)
    stat_ranges: dict[str, StatRange] = field(default_factory=dict)
    inferred_natures: dict[str, float] = field(default_factory=dict)
    inferred_ev_spreads: dict[str, float] = field(default_factory=dict)
    inferred_trait_flags: dict[str, float] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass(slots=True)
class ObservedSideState:
    side: BattleSide
    active_pet: str | None = None
    hearts: int | None = None
    pets: dict[str, ObservedPetState] = field(default_factory=dict)
    team_resources: dict[str, int] = field(default_factory=dict)
    bench_hp_percent: dict[str, float] = field(default_factory=dict)
    bench_energy: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ObservationState:
    session_id: str
    turn: int = 0
    weather: str | None = None
    field_marks: dict[str, int] = field(default_factory=dict)
    my_side: ObservedSideState = field(
        default_factory=lambda: ObservedSideState(side=BattleSide.MY)
    )
    opponent_side: ObservedSideState = field(
        default_factory=lambda: ObservedSideState(side=BattleSide.OPPONENT)
    )
    damage_log: list[DamageEvent] = field(default_factory=list)
    speed_evidence: list[SpeedEvidence] = field(default_factory=list)
    damage_evidence: list[DamageInferenceEvidence] = field(default_factory=list)
    skill_evidence: list[SkillInferenceEvidence] = field(default_factory=list)
    copy_skill_evidence: list[CopySkillEvidence] = field(default_factory=list)
    bench_resource_evidence: list[BenchResourceEvidence] = field(default_factory=list)
    quick_effect_evidence: list[QuickEffectEvidence] = field(default_factory=list)
    uncertainty_notes: list[str] = field(default_factory=list)
    event_cursor: int = 0
