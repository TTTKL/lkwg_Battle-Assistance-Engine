from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from core.models import BattleState, FieldMark, PetInstance
from core.status_effects import StatusEffectType
from engine.energy_costs import compute_effective_skill_energy_cost


@dataclass
class StrategyMechanicContext:
    state: BattleState
    is_player: bool
    active_pet: Optional[PetInstance]
    enemy_active_pet: Optional[PetInstance]


@dataclass
class StrategyMechanicResult:
    score: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)
    pending: List[str] = field(default_factory=list)

    def add(self, key: str, value: float) -> None:
        if value == 0:
            return
        self.breakdown[key] = self.breakdown.get(key, 0.0) + value
        self.score += value

    def extend(self, other: "StrategyMechanicResult") -> None:
        self.score += other.score
        for key, value in other.breakdown.items():
            self.breakdown[key] = self.breakdown.get(key, 0.0) + value
        self.pending.extend(other.pending)


MarkHook = Callable[[StrategyMechanicContext, FieldMark, bool], StrategyMechanicResult]
TraitHook = Callable[[StrategyMechanicContext, PetInstance, bool], StrategyMechanicResult]


MARK_HOOKS: Dict[str, MarkHook] = {}
TRAIT_HOOKS: Dict[str, TraitHook] = {}


PENDING_MARK_NOTES = {
    StatusEffectType.MOMENTUM_MARK.value: "legacy_rule_needs_confirmation",
    StatusEffectType.PHOTOSYNTHESIS_MARK.value: "stacked_energy_restore_not_fully_verified",
    StatusEffectType.FROST_MARK.value: "fixed_speed_penalty_vs_stack_rule_needs_confirmation",
}

PENDING_TRAIT_NOTES = {
    "不朽": "delayed_revive_rule_not_fully_modeled",
    "先知": "condition_gate_not_fully_modeled",
    "预警": "condition_gate_not_fully_modeled",
    "哨兵": "forced_switch_exit_rule_not_fully_modeled",
    "威慑": "counter_timing_dependency_needs_refinement",
    "吟游之风": "requires_multi_mark_state_model",
}


def register_mark_hook(mark_key: str, hook: MarkHook) -> None:
    MARK_HOOKS[mark_key] = hook


def register_trait_hook(trait_name: str, hook: TraitHook) -> None:
    TRAIT_HOOKS[trait_name] = hook


def evaluate_strategy_mechanics(ctx: StrategyMechanicContext) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    pos_mark, neg_mark = ctx.state.get_marks(ctx.is_player)
    if pos_mark:
        result.extend(_evaluate_mark(ctx, pos_mark, True))
    if neg_mark:
        result.extend(_evaluate_mark(ctx, neg_mark, False))

    if ctx.active_pet is not None and ctx.active_pet.is_alive:
        result.extend(_evaluate_traits(ctx, ctx.active_pet, True))
    if ctx.enemy_active_pet is not None and ctx.enemy_active_pet.is_alive:
        enemy_result = _evaluate_traits(ctx, ctx.enemy_active_pet, False)
        enemy_result.score *= -1
        enemy_result.breakdown = {
            f"enemy::{key}": -value for key, value in enemy_result.breakdown.items()
        }
        result.extend(enemy_result)

    return result


def _evaluate_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    hook = MARK_HOOKS.get(mark.type_key)
    if hook is not None:
        result = hook(ctx, mark, is_positive)
    else:
        result = StrategyMechanicResult()
        direction = 1.0 if is_positive else -1.0
        result.add(f"mark::{mark.type_key}", direction * mark.stacks * 50.0)

    pending_note = PENDING_MARK_NOTES.get(mark.type_key)
    if pending_note:
        result.pending.append(f"mark::{mark.type_key}::{pending_note}")
    return result


def _evaluate_traits(
    ctx: StrategyMechanicContext,
    pet: PetInstance,
    is_own_side: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    for trait in getattr(pet.template, "traits", []):
        hook = TRAIT_HOOKS.get(trait.name)
        if hook is not None:
            result.extend(hook(ctx, pet, is_own_side))
        pending_note = PENDING_TRAIT_NOTES.get(trait.name)
        if pending_note:
            result.pending.append(f"trait::{trait.name}::{pending_note}")
    return result


def _active_attack_skill_count(ctx: StrategyMechanicContext) -> int:
    if ctx.active_pet is None:
        return 0
    return sum(
        1
        for skill in ctx.active_pet.skills
        if getattr(skill, "base_power", 0) > 0 and getattr(skill, "damage_type", None)
    )


def _hook_moist_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    active = ctx.active_pet
    if active is None:
        return result
    discounted_skills = 0
    for skill in active.skills:
        base_cost = int(getattr(skill, "energy_cost", 0) or 0)
        current_cost = compute_effective_skill_energy_cost(ctx.state, ctx.is_player, active, skill)
        if current_cost < base_cost:
            discounted_skills += 1
    base_value = 35.0 * mark.stacks + 12.0 * discounted_skills
    result.add("mark::moist_mark", base_value if is_positive else -base_value)
    return result


def _hook_dragon_bite_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    active = ctx.active_pet
    if active is None:
        return result
    five_cost_attacks = sum(
        1
        for skill in active.skills
        if getattr(skill, "energy_cost", 0) == 5
        and getattr(skill, "base_power", 0) > 0
        and getattr(skill, "damage_type", None)
    )
    base_value = 45.0 * five_cost_attacks * max(1, mark.stacks)
    result.add("mark::dragon_bite_mark", base_value if is_positive else -base_value)
    return result


def _hook_wind_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    if ctx.active_pet is None or ctx.enemy_active_pet is None:
        return result
    speed_gap = ctx.active_pet.get_effective_stat("速度") - ctx.enemy_active_pet.get_effective_stat("速度")
    speed_factor = 1.3 if speed_gap >= 0 else 0.7
    base_value = 30.0 * mark.stacks * speed_factor
    result.add("mark::wind_mark", base_value if is_positive else -base_value)
    return result


def _hook_slow_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    if ctx.active_pet is None or ctx.enemy_active_pet is None:
        return result
    speed_gap = ctx.active_pet.get_effective_stat("速度") - ctx.enemy_active_pet.get_effective_stat("速度")
    speed_factor = 1.3 if speed_gap <= 0 else 0.7
    base_value = 28.0 * mark.stacks * speed_factor
    result.add("mark::slow_mark", base_value if is_positive else -base_value)
    return result


def _hook_charge_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    attack_count = _active_attack_skill_count(ctx)
    base_value = 16.0 * max(1, attack_count) * max(1, mark.stacks)
    result.add("mark::charge_mark", base_value if is_positive else -base_value)
    return result


def _hook_photosynthesis_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    active = ctx.active_pet
    if active is None:
        return result
    low_energy_factor = 1.4 if active.current_energy <= 3 else 1.0
    base_value = 22.0 * max(1, mark.stacks) * low_energy_factor
    result.add("mark::photosynthesis_mark", base_value if is_positive else -base_value)
    return result


def _hook_frost_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    if ctx.active_pet is None or ctx.enemy_active_pet is None:
        return result
    speed_gap = ctx.active_pet.get_effective_stat("速度") - ctx.enemy_active_pet.get_effective_stat("速度")
    speed_factor = 1.5 if speed_gap <= 0 else 1.0
    base_value = 20.0 * max(1, mark.stacks) * speed_factor
    result.add("mark::frost_mark", base_value if is_positive else -base_value)
    return result


def _hook_descent_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    base_value = 18.0 * max(1, mark.stacks)
    result.add("mark::descent_mark", base_value if is_positive else -base_value)
    return result


def _hook_thorn_mark(
    ctx: StrategyMechanicContext,
    mark: FieldMark,
    is_positive: bool,
) -> StrategyMechanicResult:
    result = StrategyMechanicResult()
    base_value = 24.0 * max(1, mark.stacks)
    result.add("mark::thorn", base_value if is_positive else -base_value)
    return result


def _hook_incomplete_trait(
    trait_name: str,
    conservative_score: float,
) -> TraitHook:
    def _hook(
        ctx: StrategyMechanicContext,
        pet: PetInstance,
        is_own_side: bool,
    ) -> StrategyMechanicResult:
        result = StrategyMechanicResult()
        if pet is not ctx.active_pet:
            return result
        result.add(f"trait::{trait_name}", conservative_score if is_own_side else -conservative_score)
        return result
    return _hook


register_mark_hook(StatusEffectType.MOIST_MARK.value, _hook_moist_mark)
register_mark_hook(StatusEffectType.DRAGON_BITE_MARK.value, _hook_dragon_bite_mark)
register_mark_hook(StatusEffectType.WIND_MARK.value, _hook_wind_mark)
register_mark_hook(StatusEffectType.SLOW_MARK.value, _hook_slow_mark)
register_mark_hook(StatusEffectType.CHARGE_MARK.value, _hook_charge_mark)
register_mark_hook(StatusEffectType.PHOTOSYNTHESIS_MARK.value, _hook_photosynthesis_mark)
register_mark_hook(StatusEffectType.FROST_MARK.value, _hook_frost_mark)
register_mark_hook(StatusEffectType.DESCENT_MARK.value, _hook_descent_mark)
register_mark_hook(StatusEffectType.THORN.value, _hook_thorn_mark)

register_trait_hook("不朽", _hook_incomplete_trait("不朽", 35.0))
register_trait_hook("先知", _hook_incomplete_trait("先知", 18.0))
register_trait_hook("预警", _hook_incomplete_trait("预警", 18.0))
register_trait_hook("哨兵", _hook_incomplete_trait("哨兵", 12.0))
register_trait_hook("威慑", _hook_incomplete_trait("威慑", 10.0))
register_trait_hook("吟游之风", _hook_incomplete_trait("吟游之风", 8.0))
