from __future__ import annotations

from ..core.events import BattleEvent, BattleSide, EventType
from ..core.observation import (
    BenchResourceEvidence,
    CopySkillEvidence,
    DamageInferenceEvidence,
    ObservationState,
    QuickEffectEvidence,
    SkillInferenceEvidence,
    SpeedEvidence,
)


class EvidenceCollector:
    """Extracts higher-information evidence objects from raw battle events."""

    def collect(self, obs: ObservationState, event: BattleEvent) -> None:
        if event.event_type in {EventType.OPPONENT_ACTION_OBSERVED, EventType.SKILL_USED}:
            self._collect_skill_evidence(obs, event)
            self._collect_copy_skill_evidence(obs, event)
            self._collect_quick_effect_evidence(obs, event)
            self._collect_speed_evidence(obs, event)
            return

        if event.event_type == EventType.DAMAGE_OBSERVED:
            self._collect_damage_evidence(obs, event)
            return

        if event.event_type in {EventType.HP_PERCENT_UPDATED, EventType.ENERGY_UPDATED}:
            self._collect_bench_resource_evidence(obs, event)
            return

        if event.event_type == EventType.STATE_CORRECTED:
            self._collect_correction_side_effects(obs, event)

    def _collect_skill_evidence(self, obs: ObservationState, event: BattleEvent) -> None:
        pet_name = event.payload.get("pet_name")
        skill_name = event.payload.get("skill_name")
        if not pet_name or not skill_name:
            return
        source = "opponent_action" if event.event_type == EventType.OPPONENT_ACTION_OBSERVED else "skill_used"
        obs.skill_evidence.append(
            SkillInferenceEvidence(
                turn=event.turn,
                pet_name=pet_name,
                observed_skill_name=skill_name,
                source=source,
            )
        )

    def _collect_copy_skill_evidence(self, obs: ObservationState, event: BattleEvent) -> None:
        copied_skill_name = event.payload.get("copied_skill_name")
        if not copied_skill_name:
            return
        obs.copy_skill_evidence.append(
            CopySkillEvidence(
                turn=event.turn,
                actor_pet=event.payload.get("pet_name", ""),
                copied_skill_name=copied_skill_name,
                copied_from_pet=event.payload.get("copied_from_pet"),
                energy_discount=int(event.payload.get("energy_discount", 0)),
                notes=list(event.payload.get("copy_notes", [])),
            )
        )

    def _collect_quick_effect_evidence(self, obs: ObservationState, event: BattleEvent) -> None:
        if not event.payload.get("quick_effect_active") and event.payload.get("priority_bonus") is None:
            return
        side = event.actor_side or event.payload.get("side")
        if side is None:
            return
        obs.quick_effect_evidence.append(
            QuickEffectEvidence(
                turn=event.turn,
                side=BattleSide(side),
                pet_name=event.payload.get("pet_name", ""),
                source_skill=event.payload.get("skill_name"),
                source_trait=event.payload.get("source_trait"),
                priority_bonus=event.payload.get("priority_bonus"),
                notes=list(event.payload.get("quick_notes", [])),
            )
        )

    def _collect_speed_evidence(self, obs: ObservationState, event: BattleEvent) -> None:
        if "moved_first" not in event.payload and "my_moved_first" not in event.payload:
            return
        my_pet = obs.my_side.active_pet or event.payload.get("my_pet")
        opponent_pet = obs.opponent_side.active_pet or event.payload.get("opponent_pet")
        if not my_pet or not opponent_pet:
            return
        my_moved_first = event.payload.get("my_moved_first")
        if my_moved_first is None and "moved_first" in event.payload:
            my_moved_first = bool(event.payload["moved_first"]) if event.payload.get("actor_side") == "my" else not bool(event.payload["moved_first"])
        obs.speed_evidence.append(
            SpeedEvidence(
                turn=event.turn,
                my_pet=my_pet,
                opponent_pet=opponent_pet,
                my_action=event.payload.get("my_action"),
                opponent_action=event.payload.get("opponent_action"),
                my_priority=event.payload.get("my_priority"),
                opponent_priority=event.payload.get("opponent_priority"),
                my_moved_first=my_moved_first,
                quick_effect_active=bool(event.payload.get("quick_effect_active", False)),
                notes=list(event.payload.get("speed_notes", [])),
            )
        )

    def _collect_damage_evidence(self, obs: ObservationState, event: BattleEvent) -> None:
        source_side = event.payload.get("source_side")
        target_side = event.payload.get("target_side")
        attacker = event.payload.get("attacker")
        defender = event.payload.get("defender")
        skill_name = event.payload.get("skill_name")
        if not source_side or not target_side or not attacker or not defender or not skill_name:
            return
        obs.damage_evidence.append(
            DamageInferenceEvidence(
                turn=event.turn,
                attacker=attacker,
                defender=defender,
                skill_name=skill_name,
                source_side=BattleSide(source_side),
                target_side=BattleSide(target_side),
                observed_damage=event.payload.get("observed_damage"),
                observed_hp_drop_percent=event.payload.get("observed_hp_drop_percent"),
                target_hp_percent_after=event.payload.get("target_hp_percent"),
                target_is_active=bool(event.payload.get("target_is_active", True)),
                notes=list(event.payload.get("damage_notes", [])),
            )
        )

    def _collect_bench_resource_evidence(self, obs: ObservationState, event: BattleEvent) -> None:
        side = event.payload.get("side")
        pet_name = event.payload.get("pet_name")
        if not side or not pet_name:
            return
        side_enum = BattleSide(side)
        side_state = obs.my_side if side_enum == BattleSide.MY else obs.opponent_side
        is_active = side_state.active_pet == pet_name
        if event.payload.get("target_is_active") is False:
            is_active = False
        if is_active:
            return
        hp_percent = event.payload.get("hp_percent") if event.event_type == EventType.HP_PERCENT_UPDATED else None
        energy = event.payload.get("energy") if event.event_type == EventType.ENERGY_UPDATED else None
        if hp_percent is None and energy is None:
            return
        obs.bench_resource_evidence.append(
            BenchResourceEvidence(
                turn=event.turn,
                side=side_enum,
                pet_name=pet_name,
                hp_percent=float(hp_percent) if hp_percent is not None else None,
                energy=int(energy) if energy is not None else None,
                source_trait=event.payload.get("source_trait"),
                source_skill=event.payload.get("source_skill"),
                notes=list(event.payload.get("bench_notes", [])),
            )
        )
        if hp_percent is not None:
            side_state.bench_hp_percent[pet_name] = float(hp_percent)
        if energy is not None:
            side_state.bench_energy[pet_name] = int(energy)

    def _collect_correction_side_effects(self, obs: ObservationState, event: BattleEvent) -> None:
        correction_type = event.payload.get("correction_type")
        if correction_type == "pet_hp":
            self._collect_bench_resource_evidence(
                obs,
                BattleEvent(
                    event_id=event.event_id,
                    session_id=event.session_id,
                    turn=event.turn,
                    phase=event.phase,
                    event_type=EventType.HP_PERCENT_UPDATED,
                    timestamp=event.timestamp,
                    payload=event.payload,
                    actor_side=event.actor_side,
                    source=event.source,
                    note=event.note,
                ),
            )
        elif correction_type == "pet_energy":
            self._collect_bench_resource_evidence(
                obs,
                BattleEvent(
                    event_id=event.event_id,
                    session_id=event.session_id,
                    turn=event.turn,
                    phase=event.phase,
                    event_type=EventType.ENERGY_UPDATED,
                    timestamp=event.timestamp,
                    payload=event.payload,
                    actor_side=event.actor_side,
                    source=event.source,
                    note=event.note,
                ),
            )

