from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.events import BattleEvent, BattleSide, EventType, EventValidationResult

if TYPE_CHECKING:
    from .session_manager import BattleSession


class EventValidator:
    """Validates normalized events against basic structural and session rules."""

    def validate(self, session: BattleSession, event: BattleEvent) -> EventValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if event.session_id != session.session_id:
            errors.append("event.session_id 与当前会话不一致")

        if event.turn < 0:
            errors.append("turn 不能为负数")

        if session.observation_state is not None and event.turn < session.observation_state.turn:
            if event.event_type != EventType.STATE_CORRECTED:
                errors.append("非修正事件的 turn 不允许倒退")

        payload = event.payload
        required_keys = self._required_payload_keys(event.event_type)
        for key in required_keys:
            if key not in payload:
                errors.append(f"{event.event_type.value} 缺少字段: {key}")

        if event.event_type in {EventType.HP_PERCENT_UPDATED, EventType.STATE_CORRECTED}:
            hp_percent = payload.get("hp_percent")
            if hp_percent is not None and not (0 <= float(hp_percent) <= 100):
                errors.append("hp_percent 必须在 0~100 之间")

        if event.event_type in {EventType.ENERGY_UPDATED, EventType.STATE_CORRECTED}:
            energy = payload.get("energy")
            if energy is not None and int(energy) < 0:
                errors.append("energy 不能小于 0")

        if event.event_type in {
            EventType.PET_SWITCHED,
            EventType.HP_PERCENT_UPDATED,
            EventType.ENERGY_UPDATED,
            EventType.PET_FAINTED,
            EventType.HEARTS_UPDATED,
        }:
            side = payload.get("side")
            if side is not None:
                try:
                    BattleSide(side)
                except ValueError:
                    errors.append(f"非法 side: {side}")

        if event.event_type == EventType.PET_SWITCHED:
            if payload.get("old_pet") and payload.get("old_pet") == payload.get("new_pet"):
                warnings.append("switch 事件中的 old_pet 与 new_pet 相同")

        return EventValidationResult(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
        )

    def _required_payload_keys(self, event_type: EventType) -> set[str]:
        mapping: dict[EventType, set[str]] = {
            EventType.BATTLE_STARTED: set(),
            EventType.TURN_STARTED: set(),
            EventType.MY_ACTION_DECLARED: {"pet_name", "action_type"},
            EventType.OPPONENT_ACTION_OBSERVED: {"pet_name", "action_type"},
            EventType.PET_SWITCHED: {"side", "new_pet"},
            EventType.SKILL_USED: {"side", "pet_name", "skill_name"},
            EventType.DAMAGE_OBSERVED: {"source_side", "target_side"},
            EventType.HP_PERCENT_UPDATED: {"side", "pet_name", "hp_percent"},
            EventType.ENERGY_UPDATED: {"side", "pet_name", "energy"},
            EventType.STATUS_APPLIED: {"side", "pet_name", "status_name"},
            EventType.STATUS_REMOVED: {"side", "pet_name", "status_name"},
            EventType.MARK_UPDATED: {"side", "target_type", "mark_name"},
            EventType.PET_FAINTED: {"side", "pet_name"},
            EventType.HEARTS_UPDATED: {"side", "hearts"},
            EventType.TURN_ENDED: set(),
            EventType.STATE_CORRECTED: {"correction_type"},
        }
        return mapping.get(event_type, set())
