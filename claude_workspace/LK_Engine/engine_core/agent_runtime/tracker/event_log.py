from __future__ import annotations

from dataclasses import dataclass, field

from ..core.events import BattleEvent


@dataclass
class BattleEventLog:
    events: list[BattleEvent] = field(default_factory=list)

    def append(self, event: BattleEvent) -> None:
        self.events.append(event)

    def copy_events(self) -> list[BattleEvent]:
        return list(self.events)

    def get_event_index(self, event_id: str) -> int | None:
        for index, event in enumerate(self.events):
            if event.event_id == event_id:
                return index
        return None

    def get_event(self, event_id: str) -> BattleEvent | None:
        index = self.get_event_index(event_id)
        if index is None:
            return None
        return self.events[index]

    def last_event(self) -> BattleEvent | None:
        if not self.events:
            return None
        return self.events[-1]

    def rollback_last(self) -> BattleEvent | None:
        if not self.events:
            return None
        return self.events.pop()

    def clear(self) -> int:
        removed_count = len(self.events)
        self.events.clear()
        return removed_count

    def rollback_to_index(self, index: int) -> None:
        self.events = self.events[:index]

    def rollback_to_event(self, event_id: str, inclusive: bool = True) -> bool:
        index = self.get_event_index(event_id)
        if index is None:
            return False
        end_index = index if inclusive else index + 1
        self.rollback_to_index(end_index)
        return True

    def list_turn_events(self, turn: int) -> list[BattleEvent]:
        return [event for event in self.events if event.turn == turn]

    def list_events(self) -> list[BattleEvent]:
        return list(self.events)
