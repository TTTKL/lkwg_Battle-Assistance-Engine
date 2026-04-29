from core.models import BattleState


def process_end_turn(
    state: BattleState,
    status_processor,
    trait_processor,
    deduct_hearts,
    apply_mirror_reflect_transformation,
    self_reenter_active_pet,
    get_end_of_turn_trigger_count,
):
    player_pet = state.player.get_active_pet()
    opponent_pet = state.opponent.get_active_pet()
    trigger_count = get_end_of_turn_trigger_count(state)

    if state.weather == '暴风雪':
        for pet in [player_pet, opponent_pet]:
            if pet and pet.is_alive:
                pet.freeze_stacks += 1

    for _ in range(trigger_count):
        for pet, opponent, is_player in [
            (player_pet, opponent_pet, True),
            (opponent_pet, player_pet, False),
        ]:
            if not pet or not pet.is_alive:
                continue
            was_alive = pet.is_alive
            hp_before = pet.current_hp
            status_processor.process_end_of_turn_effects(pet, opponent, is_player, state)
            if pet.current_hp < hp_before:
                pet.set_runtime_flag('_took_any_damage_this_turn', True)
            if was_alive and not pet.is_alive:
                deduct_hearts(pet, is_player, state)

    for _ in range(trigger_count):
        for pet, opponent, is_player in [
            (player_pet, opponent_pet, True),
            (opponent_pet, player_pet, False),
        ]:
            if pet and pet.is_alive:
                trait_processor.trigger_end_of_turn(pet, opponent, is_player, state)

    for pet in [state.player.get_active_pet(), state.opponent.get_active_pet()]:
        if pet and pet.is_alive:
            apply_mirror_reflect_transformation(pet)

    for is_player, pet in [(True, state.player.get_active_pet()), (False, state.opponent.get_active_pet())]:
        if pet and pet.is_alive and pet.get_runtime_flag('_self_reenter_at_end_turn', False):
            pet.pop_runtime_flag('_self_reenter_at_end_turn', None)
            self_reenter_active_pet(state, is_player)

    for ps in [state.player, state.opponent]:
        pet = ps.get_active_pet()
        if pet:
            for sk in list(pet.skill_cooldowns):
                pet.skill_cooldowns[sk] -= 1
                if pet.skill_cooldowns[sk] <= 0:
                    del pet.skill_cooldowns[sk]

    for ps in [state.player, state.opponent]:
        pet = ps.get_active_pet()
        if pet and pet.is_alive:
            for sk in pet.skills:
                if sk.name == '水波术':
                    sk.base_power += 20

    for ps in [state.player, state.opponent]:
        pet = ps.get_active_pet()
        if pet:
            if pet.burst_turns_remaining > 0:
                pet.burst_turns_remaining -= 1
            pet.priority_bonus = 0
            pet.set_runtime_flag(
                '_took_any_damage_last_turn',
                pet.get_runtime_flag('_took_any_damage_this_turn', False)
            )
            pet.set_runtime_flag('_took_any_damage_this_turn', False)
