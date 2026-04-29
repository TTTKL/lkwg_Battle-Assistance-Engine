from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventPhase(str, Enum):
    BATTLE = "battle"
    TURN_START = "turn_start"
    ACTION = "action"
    RESOLUTION = "resolution"
    SYNC = "sync"
    TURN_END = "turn_end"
    CORRECTION = "correction"


class EventType(str, Enum):
    BATTLE_STARTED = "BATTLE_STARTED"
    TURN_STARTED = "TURN_STARTED"
    MY_ACTION_DECLARED = "MY_ACTION_DECLARED"
    OPPONENT_ACTION_OBSERVED = "OPPONENT_ACTION_OBSERVED"
    PET_SWITCHED = "PET_SWITCHED"
    SKILL_USED = "SKILL_USED"
    DAMAGE_OBSERVED = "DAMAGE_OBSERVED"
    HP_PERCENT_UPDATED = "HP_PERCENT_UPDATED"
    ENERGY_UPDATED = "ENERGY_UPDATED"
    STATUS_APPLIED = "STATUS_APPLIED"
    STATUS_REMOVED = "STATUS_REMOVED"
    MARK_UPDATED = "MARK_UPDATED"
    PET_FAINTED = "PET_FAINTED"
    HEARTS_UPDATED = "HEARTS_UPDATED"
    TURN_ENDED = "TURN_ENDED"
    STATE_CORRECTED = "STATE_CORRECTED"


class EventSource(str, Enum):
    USER = "user"
    API = "api"
    REPLAY = "replay"
    AUTO_INFER = "auto_infer"


class BattleSide(str, Enum):
    MY = "my"
    OPPONENT = "opponent"


@dataclass(slots=True)
class BattleEvent:
    event_id: str
    session_id: str
    turn: int
    phase: EventPhase
    event_type: EventType
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    actor_side: BattleSide | None = None
    source: EventSource = EventSource.USER
    note: str = ""


@dataclass(slots=True)
class EventValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

