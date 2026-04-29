from __future__ import annotations

from copy import deepcopy

from ..core.events import BattleEvent, BattleSide, EventType
from ..core.observation import DamageEvent, ObservationState, ObservedPetState
from .evidence_collector import EvidenceCollector


class ObservationReducer:
    """Applies battle events to an ObservationState.

    This reducer intentionally updates only observed facts. Inference outputs
    should be written by dedicated inference services, not mixed into raw event
    application.
    """

    def __init__(self) -> None:
        self._evidence_collector = EvidenceCollector()

    def apply(self, obs: ObservationState, event: BattleEvent) -> ObservationState:
        obs = deepcopy(obs)
        obs.event_cursor += 1
        obs.turn = max(obs.turn, event.turn)
        self._evidence_collector.collect(obs, event)

        if event.event_type == EventType.BATTLE_STARTED:
            self._apply_battle_started(obs, event)
            return obs

        if event.event_type == EventType.TURN_STARTED:
            obs.turn = event.turn
            return obs

        if event.event_type == EventType.HP_PERCENT_UPDATED:
            self._apply_hp_update(obs, event)
            return obs

        if event.event_type == EventType.ENERGY_UPDATED:
            self._apply_energy_update(obs, event)
            return obs

        if event.event_type == EventType.OPPONENT_ACTION_OBSERVED:
            self._apply_observed_skill(obs, event)
            return obs

        if event.event_type == EventType.SKILL_USED:
            self._apply_skill_used(obs, event)
            return obs

        if event.event_type == EventType.DAMAGE_OBSERVED:
            self._apply_damage_observed(obs, event)
            return obs

        if event.event_type == EventType.STATUS_APPLIED:
            self._apply_status_applied(obs, event)
            return obs

        if event.event_type == EventType.STATUS_REMOVED:
            self._apply_status_removed(obs, event)
            return obs

        if event.event_type == EventType.MARK_UPDATED:
            self._apply_mark_updated(obs, event)
            return obs

        if event.event_type == EventType.PET_SWITCHED:
            self._apply_switch(obs, event)
            return obs

        if event.event_type == EventType.PET_FAINTED:
            self._apply_fainted(obs, event)
            return obs

        if event.event_type == EventType.HEARTS_UPDATED:
            self._apply_hearts_updated(obs, event)
            return obs

        if event.event_type == EventType.STATE_CORRECTED:
            self._apply_state_corrected(obs, event)
            return obs

        return obs

    def _get_side_state(self, obs: ObservationState, side: BattleSide):
        return obs.my_side if side == BattleSide.MY else obs.opponent_side

    def _apply_battle_started(self, obs: ObservationState, event: BattleEvent) -> None:
        weather = event.payload.get("weather")
        if weather is not None:
            obs.weather = weather
        my_team = event.payload.get("my_team", [])
        opponent_team = event.payload.get("opponent_team", [])
        for pet_name in my_team:
            self._ensure_pet(obs, BattleSide.MY, pet_name)
        for pet_name in opponent_team:
            pet = self._ensure_pet(obs, BattleSide.OPPONENT, pet_name)
            pet.revealed = True

    def _ensure_pet(
        self, obs: ObservationState, side: BattleSide, pet_name: str
    ) -> ObservedPetState:
        side_state = self._get_side_state(obs, side)
        if pet_name not in side_state.pets:
            side_state.pets[pet_name] = ObservedPetState(
                pet_name=pet_name,
                side=side,
                revealed=True,
            )
        return side_state.pets[pet_name]

    def _apply_hp_update(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        pet = self._ensure_pet(obs, side, event.payload["pet_name"])
        pet.hp_percent = float(event.payload["hp_percent"])

    def _apply_energy_update(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        pet = self._ensure_pet(obs, side, event.payload["pet_name"])
        pet.energy = int(event.payload["energy"])

    def _apply_observed_skill(self, obs: ObservationState, event: BattleEvent) -> None:
        side = event.actor_side or BattleSide.OPPONENT
        pet = self._ensure_pet(obs, side, event.payload["pet_name"])
        self._set_active_pet(obs, side, pet.pet_name)
        skill_name = event.payload["skill_name"]
        if skill_name not in pet.observed_skills:
            pet.observed_skills.append(skill_name)

    def _apply_skill_used(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        pet = self._ensure_pet(obs, side, event.payload["pet_name"])
        self._set_active_pet(obs, side, pet.pet_name)
        skill_name = event.payload["skill_name"]
        if side == BattleSide.OPPONENT and skill_name not in pet.observed_skills:
            pet.observed_skills.append(skill_name)

    def _apply_damage_observed(self, obs: ObservationState, event: BattleEvent) -> None:
        damage_event = DamageEvent(
            attacker=event.payload.get("attacker", ""),
            defender=event.payload.get("defender", ""),
            skill_name=event.payload.get("skill_name", ""),
            observed_damage=event.payload.get("observed_damage"),
            observed_hp_drop_percent=event.payload.get("observed_hp_drop_percent"),
            category=event.payload.get("category"),
            stab=event.payload.get("stab"),
            type_effectiveness=event.payload.get("type_effectiveness"),
        )
        obs.damage_log.append(damage_event)

        target_side = event.payload.get("target_side")
        pet_name = event.payload.get("defender")
        hp_percent = event.payload.get("target_hp_percent")
        if target_side and pet_name and hp_percent is not None:
            pet = self._ensure_pet(obs, BattleSide(target_side), pet_name)
            pet.hp_percent = float(hp_percent)

    def _apply_status_applied(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        pet = self._ensure_pet(obs, side, event.payload["pet_name"])
        status_name = event.payload["status_name"]
        stacks = int(event.payload.get("stacks", 1))
        pet.status_effects[status_name] = stacks

    def _apply_status_removed(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        pet = self._ensure_pet(obs, side, event.payload["pet_name"])
        status_name = event.payload["status_name"]
        pet.status_effects.pop(status_name, None)

    def _apply_mark_updated(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        target_type = event.payload["target_type"]
        mark_name = event.payload["mark_name"]
        stacks = int(event.payload.get("stacks", 0))

        if target_type == "field":
            if stacks <= 0:
                obs.field_marks.pop(mark_name, None)
            else:
                obs.field_marks[mark_name] = stacks
            return

        if target_type == "pet":
            pet = self._ensure_pet(obs, side, event.payload["pet_name"])
            if stacks <= 0:
                pet.marks.pop(mark_name, None)
            else:
                pet.marks[mark_name] = stacks

    def _apply_hearts_updated(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        side_state = self._get_side_state(obs, side)
        side_state.hearts = int(event.payload["hearts"])

    def _apply_switch(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        old_pet = event.payload.get("old_pet")
        new_pet = event.payload["new_pet"]
        side_state = self._get_side_state(obs, side)
        if old_pet:
            old_state = self._ensure_pet(obs, side, old_pet)
            old_state.is_active = False
        new_state = self._ensure_pet(obs, side, new_pet)
        new_state.revealed = True
        self._set_active_pet(obs, side, new_pet)

    def _apply_fainted(self, obs: ObservationState, event: BattleEvent) -> None:
        side = BattleSide(event.payload["side"])
        pet = self._ensure_pet(obs, side, event.payload["pet_name"])
        pet.fainted = True
        pet.is_active = False
        pet.hp_percent = 0.0
        side_state = self._get_side_state(obs, side)
        if side_state.active_pet == pet.pet_name:
            side_state.active_pet = None

    def _apply_state_corrected(self, obs: ObservationState, event: BattleEvent) -> None:
        correction_type = event.payload["correction_type"]
        if correction_type == "pet_hp":
            side = BattleSide(event.payload["side"])
            pet = self._ensure_pet(obs, side, event.payload["pet_name"])
            pet.hp_percent = float(event.payload["hp_percent"])
            return

        if correction_type == "pet_energy":
            side = BattleSide(event.payload["side"])
            pet = self._ensure_pet(obs, side, event.payload["pet_name"])
            pet.energy = int(event.payload["energy"])
            return

        if correction_type == "hearts":
            side = BattleSide(event.payload["side"])
            self._get_side_state(obs, side).hearts = int(event.payload["hearts"])
            return

        if correction_type == "active_pet":
            side = BattleSide(event.payload["side"])
            pet_name = event.payload["pet_name"]
            pet = self._ensure_pet(obs, side, pet_name)
            pet.revealed = True
            self._set_active_pet(obs, side, pet_name)

    def _set_active_pet(self, obs: ObservationState, side: BattleSide, pet_name: str) -> None:
        side_state = self._get_side_state(obs, side)
        for pet in side_state.pets.values():
            pet.is_active = False
        active_pet = self._ensure_pet(obs, side, pet_name)
        active_pet.is_active = True
        active_pet.revealed = True
        side_state.active_pet = pet_name
