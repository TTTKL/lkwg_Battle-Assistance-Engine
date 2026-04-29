from core.models import BattleState, PetInstance, Skill, SkillCategory
from engine.mark_effects import MarkEffectsProcessor
from engine.slot_effects import SlotEffectsProcessor


def get_runtime_skill_energy_delta(pet: PetInstance, skill: Skill, current_turn: int) -> int:
    delta = pet.get_runtime_flag('_permanent_all_skill_energy_delta', 0)
    delta += pet.get_runtime_flag('_mental_disruption_energy_delta', 0)
    if skill.category == SkillCategory.ATTACK:
        delta += pet.get_runtime_flag('_permanent_attack_skill_energy_delta', 0)

    for rule in pet.get_runtime_flag('_temporary_energy_rules', []):
        if current_turn < rule.get('start_turn', 0) or current_turn > rule.get('end_turn', -1):
            continue
        kind = rule.get('kind')
        if kind == 'all_except_skill':
            if skill.name != rule.get('excluded_skill_name'):
                delta += int(rule.get('delta', 0))
        elif kind == 'skill_name':
            if skill.name == rule.get('skill_name'):
                delta += int(rule.get('delta', 0))
        elif kind == 'all_attack':
            if skill.category == SkillCategory.ATTACK:
                delta += int(rule.get('delta', 0))
        elif kind == 'all_skills':
            delta += int(rule.get('delta', 0))

    return delta


def compute_effective_skill_energy_cost(
    state: BattleState,
    is_player: bool,
    attacker: PetInstance,
    skill: Skill,
    *,
    counter_success: bool = False,
    extra_multiplier: int = 1,
    include_forced_runtime: bool = False,
) -> int:
    _, modified_energy = MarkEffectsProcessor.apply_mark_effects_to_skill(
        skill, attacker, is_player, counter_success, state
    )
    modified_energy = max(0, modified_energy + SlotEffectsProcessor.get_skill_energy_delta(attacker, skill))
    modified_energy = max(0, modified_energy + get_runtime_skill_energy_delta(attacker, skill, state.turn))

    if include_forced_runtime:
        modified_energy = max(0, modified_energy + int(attacker.get_runtime_flag('_forced_flat_energy_delta', 0)))

    if state.weather == '沙暴' and skill.element == '地':
        modified_energy = max(0, modified_energy - 2)

    next_energy_delta = SlotEffectsProcessor.get_next_skill_energy_delta(attacker)
    if next_energy_delta != 0:
        modified_energy = max(0, modified_energy + next_energy_delta)

    multiplier = extra_multiplier
    if include_forced_runtime:
        multiplier *= int(attacker.get_runtime_flag('_forced_energy_multiplier', 1))

    return max(0, modified_energy * multiplier)


def can_pay_skill_energy_cost(pet: PetInstance, required_energy: int) -> bool:
    if pet.current_energy >= required_energy:
        return True
    if any(trait.name == "石头大餐" for trait in getattr(pet.template, "traits", [])):
        shortfall = required_energy - pet.current_energy
        cost_hp = int(pet.max_hp * 0.05 * shortfall)
        return pet.current_hp > cost_hp
    return False
