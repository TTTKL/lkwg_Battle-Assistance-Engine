from core.status_effects import StatusEffectType
from core.models import EffectType
from engine.mark_effects import MarkEffectsProcessor
from engine.slot_effects import SlotEffectsProcessor


def resolve_skill_damage(
    state,
    is_player,
    attacker,
    defender,
    skill,
    modified_power,
    ignore_external_modifiers,
    devotion_combo_bonus,
    devotion_lifesteal_bonus,
    devotion_poison_bonus,
    devotion_impact_count,
    trait_processor,
    status_processor,
    compute_total_hits_with_defender,
    calculate_damage_with_power,
    apply_heal_or_reversed_damage,
):
    total_damage = 0
    if not (skill.base_power > 0 and skill.damage_type):
        return total_damage

    total_hits = compute_total_hits_with_defender(skill, attacker, defender)
    total_hits += devotion_combo_bonus

    if attacker.get_runtime_flag('_crackle_first', False):
        attacker.set_runtime_flag('_crackle_first', False)
        total_hits += 1

    if attacker.get_runtime_flag('_takeoff_speed', False):
        attacker.set_runtime_flag('_takeoff_speed', False)
        attacker.priority_bonus += 1

    def _has_active_trait(ps, trait_name):
        pet_active = ps.get_active_pet()
        return pet_active and any(t.name == trait_name for t in pet_active.template.traits)

    if _has_active_trait(state.player, "无差别过滤") or _has_active_trait(state.opponent, "无差别过滤"):
        total_hits = 2

    opp_state = state.opponent if is_player else state.player
    opp_switched = opp_state.team_state.switched_this_turn
    is_first = attacker.get_runtime_flag('_is_first_attacker', False)

    if skill.name == '反击拳' and not is_first:
        total_hits = 3
    elif skill.name == '疾风刺' and is_first:
        total_hits = 3
    elif skill.name == '撕咬':
        if attacker.current_hp < attacker.max_hp * 0.5:
            total_hits += 2
    elif skill.name == '幼态延续':
        cute_stacks = getattr(attacker, 'cute_stacks', 0)
        if cute_stacks > 0:
            modified_power += 60
    elif skill.name == '坟场搏击':
        reduction = defender.current_energy * 0.1
        modified_power = max(1, int(modified_power * (1 - reduction)))
    elif skill.name == '燃尽':
        hp_lost_pct = (defender.max_hp - defender.current_hp) / max(1, defender.max_hp)
        lost_steps = int(hp_lost_pct / 0.05)
        modified_power = max(1, modified_power - lost_steps * 5)
    elif skill.name == '彗星':
        hp_lost_pct = (attacker.max_hp - attacker.current_hp) / max(1, attacker.max_hp)
        lost_steps = int(hp_lost_pct / 0.05)
        modified_power = max(1, modified_power - lost_steps * 10)
    elif skill.name == '埋伏' and opp_switched:
        total_hits += 3
    elif skill.name == '灵光' and opp_switched:
        total_hits = max(1, total_hits * 2)
    elif skill.name == '回旋踢' and opp_switched:
        modified_power = modified_power * 2
    elif skill.name == '绵里藏针':
        if not defender.get_runtime_flag('_took_any_damage_last_turn', False):
            modified_power += 20

    if skill.name == '月光合奏':
        total_hits += getattr(attacker, 'cute_stacks', 0) + getattr(defender, 'cute_stacks', 0)

    if skill.name == '虫鸣':
        own_state = state.player if is_player else state.opponent
        total_hits += sum(1 for pet in own_state.team for sk in pet.skills if sk.name == '虫鸣')

    for _ in range(total_hits):
        if not defender.is_alive:
            break
        damage = calculate_damage_with_power(
            attacker, defender, skill, state, modified_power,
            ignore_external_modifiers=ignore_external_modifiers
        )
        defender.current_hp = max(0, defender.current_hp - damage)
        total_damage += damage
        defender.set_runtime_flag('_took_any_damage_this_turn', True)

        if defender.charging_skill:
            charged_hit_power = max(
                defender.get_runtime_flag('_charged_hit_power', 0),
                int(modified_power * 3),
            )
            defender.set_runtime_flag('_charged_hit_power', charged_hit_power)

        trait_processor.trigger_on_attack(attacker, defender, damage, is_player, state)
        trait_processor.trigger_on_damaged(defender, attacker, damage, not is_player, state)

        if defender.current_hp == 0:
            defender.is_alive = False
            break

    if attacker.get_runtime_flag('_overload_burst', False) and total_damage > 0:
        for sk in defender.skills:
            SlotEffectsProcessor.apply_energy_cost_delta(defender, sk, 1)

    if skill.name == '针刺射击' and opp_switched and total_damage > 0:
        attacker.current_energy = min(10, attacker.current_energy + 7)

    for eff in skill.effects:
        if eff.type == EffectType.LIFESTEAL and total_damage > 0:
            heal = int(total_damage * eff.value)
            apply_heal_or_reversed_damage(attacker, heal)
    if devotion_lifesteal_bonus > 0 and total_damage > 0:
        heal = int(total_damage * devotion_lifesteal_bonus / 100)
        apply_heal_or_reversed_damage(attacker, heal)
    lifesteal_bonus = attacker.get_runtime_flag('_lifesteal_bonus', 0)
    if lifesteal_bonus > 0 and total_damage > 0:
        heal = int(total_damage * lifesteal_bonus / 100)
        apply_heal_or_reversed_damage(attacker, heal)

    if any(t.name == "守望星" for t in attacker.template.traits):
        star_stacks = defender.get_status_stacks(
            __import__('core.status_effects', fromlist=['StatusEffectType']).StatusEffectType.STAR_FALL_MARK
        )
        extra = status_processor.trigger_star_fall_mark(
            defender, attacker, skill.element, not is_player, state
        )
        if extra > 0:
            defender.add_status(StatusEffectType.STAR_FALL_MARK, star_stacks // 2)
    else:
        extra = status_processor.trigger_star_fall_mark(
            defender, attacker, skill.element, not is_player, state
        )
    if extra > 0:
        defender.current_hp = max(0, defender.current_hp - extra)

    status_processor.check_freeze_death(defender)

    if devotion_poison_bonus > 0 and defender.is_alive:
        defender.add_status(StatusEffectType.POISON, devotion_poison_bonus)

    if defender.current_hp == 0:
        defender.is_alive = False

    if skill.name == '啃咬' and devotion_impact_count > 0:
        current_skill_name = attacker.get_runtime_flag('_current_skill_name', '')
        for attacker_skill in attacker.skills:
            if attacker_skill.name == current_skill_name:
                SlotEffectsProcessor.apply_energy_cost_delta(attacker, attacker_skill, devotion_impact_count)
                break

    return total_damage
