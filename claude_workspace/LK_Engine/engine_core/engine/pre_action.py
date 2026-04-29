from core.models import Action, ActionType
from engine.slot_effects import SlotEffectsProcessor


def prepare_actions_for_turn(
    state,
    player_action,
    opponent_action,
    process_turn_start_skill_position_changes,
    force_send_out_if_needed,
    expire_turn_limited_flags,
    switch_pet,
    gather_energy,
    apply_leader_evolution,
    apply_willpower_strike,
):
    SlotEffectsProcessor.prepare_state_for_turn(state)
    process_turn_start_skill_position_changes(state)

    if player_action.send_out_index is not None:
        force_send_out_if_needed(state, True, player_action.send_out_index)
    if opponent_action.send_out_index is not None:
        force_send_out_if_needed(state, False, opponent_action.send_out_index)

    p_pet = state.player.get_active_pet()
    o_pet = state.opponent.get_active_pet()
    if p_pet:
        p_pet.just_entered = False
        p_pet.pop_runtime_flag('_selected_skill_name', None)
    if o_pet:
        o_pet.just_entered = False
        o_pet.pop_runtime_flag('_selected_skill_name', None)
    state.player.team_state.switched_this_turn = False
    state.opponent.team_state.switched_this_turn = False

    if p_pet and player_action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE) and player_action.skill:
        p_pet.set_runtime_flag('_selected_skill_name', player_action.skill.name)
    if o_pet and opponent_action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE) and opponent_action.skill:
        o_pet.set_runtime_flag('_selected_skill_name', opponent_action.skill.name)
    if p_pet:
        expire_turn_limited_flags(p_pet, state.turn)
        if p_pet.get_runtime_flag('_next_skill_priority_bonus', 0) > 0:
            p_pet.set_runtime_flag('_next_skill_priority_armed', True)
    if o_pet:
        expire_turn_limited_flags(o_pet, state.turn)
        if o_pet.get_runtime_flag('_next_skill_priority_bonus', 0) > 0:
            o_pet.set_runtime_flag('_next_skill_priority_armed', True)

    if p_pet and p_pet.stun_turns > 0:
        if player_action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE):
            player_action = Action(type=ActionType.GATHER_ENERGY)
        p_pet.stun_turns -= 1
    if o_pet and o_pet.stun_turns > 0:
        if opponent_action.type in (ActionType.USE_SKILL, ActionType.WILLPOWER_STRIKE):
            opponent_action = Action(type=ActionType.GATHER_ENERGY)
        o_pet.stun_turns -= 1

    if player_action.type == ActionType.SWITCH_PET:
        switch_pet(state, True, player_action.target_index)
        state.player.team_state.switched_this_turn = True
    if opponent_action.type == ActionType.SWITCH_PET:
        switch_pet(state, False, opponent_action.target_index)
        state.opponent.team_state.switched_this_turn = True

    if player_action.type == ActionType.GATHER_ENERGY:
        gather_energy(state.player)
    if opponent_action.type == ActionType.GATHER_ENERGY:
        gather_energy(state.opponent)

    if player_action.type == ActionType.LEADER_EVOLUTION:
        apply_leader_evolution(state, True)
    if opponent_action.type == ActionType.LEADER_EVOLUTION:
        apply_leader_evolution(state, False)
    if player_action.type == ActionType.WILLPOWER_STRIKE:
        apply_willpower_strike(state, True, player_action.skill)
    if opponent_action.type == ActionType.WILLPOWER_STRIKE:
        apply_willpower_strike(state, False, opponent_action.skill)

    return player_action, opponent_action
