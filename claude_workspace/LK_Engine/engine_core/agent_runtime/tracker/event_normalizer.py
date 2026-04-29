from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from uuid import uuid4

from ..core.events import (
    BattleEvent,
    BattleSide,
    EventPhase,
    EventSource,
    EventType,
)


class EventNormalizer:
    """Converts loose user/api input into normalized BattleEvent objects."""

    DEFAULT_PHASE_BY_TYPE: dict[EventType, EventPhase] = {
        EventType.BATTLE_STARTED: EventPhase.BATTLE,
        EventType.TURN_STARTED: EventPhase.TURN_START,
        EventType.MY_ACTION_DECLARED: EventPhase.ACTION,
        EventType.OPPONENT_ACTION_OBSERVED: EventPhase.ACTION,
        EventType.PET_SWITCHED: EventPhase.RESOLUTION,
        EventType.SKILL_USED: EventPhase.RESOLUTION,
        EventType.DAMAGE_OBSERVED: EventPhase.RESOLUTION,
        EventType.HP_PERCENT_UPDATED: EventPhase.SYNC,
        EventType.ENERGY_UPDATED: EventPhase.SYNC,
        EventType.STATUS_APPLIED: EventPhase.RESOLUTION,
        EventType.STATUS_REMOVED: EventPhase.RESOLUTION,
        EventType.MARK_UPDATED: EventPhase.RESOLUTION,
        EventType.PET_FAINTED: EventPhase.RESOLUTION,
        EventType.HEARTS_UPDATED: EventPhase.SYNC,
        EventType.TURN_ENDED: EventPhase.TURN_END,
        EventType.STATE_CORRECTED: EventPhase.CORRECTION,
    }

    def normalize(
        self,
        *,
        session_id: str,
        event_type: EventType | str,
        turn: int,
        payload: dict | None = None,
        actor_side: BattleSide | str | None = None,
        phase: EventPhase | str | None = None,
        source: EventSource | str = EventSource.USER,
        note: str = "",
        event_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> BattleEvent:
        normalized_type = event_type if isinstance(event_type, EventType) else EventType(event_type)
        normalized_side = None
        if actor_side is not None:
            normalized_side = actor_side if isinstance(actor_side, BattleSide) else BattleSide(actor_side)
        normalized_phase = (
            phase if isinstance(phase, EventPhase) else EventPhase(phase)
        ) if phase is not None else self.DEFAULT_PHASE_BY_TYPE[normalized_type]
        normalized_source = source if isinstance(source, EventSource) else EventSource(source)

        return BattleEvent(
            event_id=event_id or uuid4().hex,
            session_id=session_id,
            turn=turn,
            phase=normalized_phase,
            event_type=normalized_type,
            timestamp=timestamp or datetime.now(),
            payload=deepcopy(payload or {}),
            actor_side=normalized_side,
            source=normalized_source,
            note=note,
        )

