from core.models import ActionType


def resolve_skill_phase(
    state,
    player_action,
    opponent_action,
    check_counter,
    force_send_out_if_needed,
    execute_skill,
    determine_order,
    trigger_on_counter_success,
):
    if (player_action.type == ActionType.USE_SKILL and
            opponent_action.type == ActionType.USE_SKILL):

        p_skill = player_action.skill
        o_skill = opponent_action.skill

        player_counters = check_counter(p_skill, o_skill)
        opponent_counters = check_counter(o_skill, p_skill)

        if player_counters and not opponent_counters:
            force_send_out_if_needed(state, True, player_action.send_out_index)
            execute_skill(state, True, p_skill, counter_success=True)
            trigger_on_counter_success(
                state.player.get_active_pet(), state.opponent.get_active_pet(),
                True, state
            )
            if not state.is_terminal():
                force_send_out_if_needed(state, False, opponent_action.send_out_index)
                execute_skill(state, False, o_skill, counter_success=False)
            return

        if opponent_counters and not player_counters:
            force_send_out_if_needed(state, False, opponent_action.send_out_index)
            execute_skill(state, False, o_skill, counter_success=True)
            trigger_on_counter_success(
                state.opponent.get_active_pet(), state.player.get_active_pet(),
                False, state
            )
            if not state.is_terminal():
                force_send_out_if_needed(state, True, player_action.send_out_index)
                execute_skill(state, True, p_skill, counter_success=False)
            return

        first, _ = determine_order(
            state.player.get_active_pet(),
            state.opponent.get_active_pet(),
            p_skill, o_skill
        )
        if first == "player":
            p_pet = state.player.get_active_pet()
            o_pet = state.opponent.get_active_pet()
            if p_pet:
                p_pet.set_runtime_flag('_is_first_attacker', True)
            if o_pet:
                o_pet.set_runtime_flag('_is_first_attacker', False)
            force_send_out_if_needed(state, True, player_action.send_out_index)
            execute_skill(state, True, p_skill, False)
            if p_pet:
                p_pet.set_runtime_flag('_is_first_attacker', False)
            if not state.is_terminal():
                force_send_out_if_needed(state, False, opponent_action.send_out_index)
                execute_skill(state, False, o_skill, False)
            return

        p_pet = state.player.get_active_pet()
        o_pet = state.opponent.get_active_pet()
        if o_pet:
            o_pet.set_runtime_flag('_is_first_attacker', True)
        if p_pet:
            p_pet.set_runtime_flag('_is_first_attacker', False)
        force_send_out_if_needed(state, False, opponent_action.send_out_index)
        execute_skill(state, False, o_skill, False)
        if o_pet:
            o_pet.set_runtime_flag('_is_first_attacker', False)
        if not state.is_terminal():
            force_send_out_if_needed(state, True, player_action.send_out_index)
            execute_skill(state, True, p_skill, False)
        return

    if player_action.type == ActionType.USE_SKILL:
        force_send_out_if_needed(state, True, player_action.send_out_index)
        execute_skill(state, True, player_action.skill, False)
    if opponent_action.type == ActionType.USE_SKILL:
        force_send_out_if_needed(state, False, opponent_action.send_out_index)
        execute_skill(state, False, opponent_action.skill, False)
