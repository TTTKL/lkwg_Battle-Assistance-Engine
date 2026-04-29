from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from ..core.events import BattleEvent, EventSource, EventType, EventValidationResult
from ..core.observation import ObservationState
from ..engine.stat_inferrer import StatInferrer
from .event_log import BattleEventLog
from .event_normalizer import EventNormalizer
from .event_validator import EventValidator
from .observation_reducer import ObservationReducer


@dataclass
class BattleSessionConfig:
    my_team: list[str] = field(default_factory=list)
    opponent_team_candidates: list[str] = field(default_factory=list)
    ruleset_version: str = "default"
    search_depth: int = 2
    inference_mode: str = "hybrid"


@dataclass
class BattleSession:
    session_id: str
    created_at: datetime
    updated_at: datetime
    status: str = "active"
    config: BattleSessionConfig = field(default_factory=BattleSessionConfig)
    event_log: BattleEventLog = field(default_factory=BattleEventLog)
    observation_state: ObservationState | None = None
    last_import_batch_id: str | None = None
    last_import_turn: int | None = None
    last_import_note: str = ""
    last_import_at: datetime | None = None


class BattleSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, BattleSession] = {}
        self._reducer = ObservationReducer()
        self._validator = EventValidator()
        self._normalizer = EventNormalizer()
        self._stat_inferrer = StatInferrer()

    def create_session(self, session_id: str, config: BattleSessionConfig) -> BattleSession:
        now = datetime.now()
        session = BattleSession(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            config=config,
            observation_state=ObservationState(session_id=session_id),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> BattleSession:
        return self._sessions[session_id]

    def append_event(self, event: BattleEvent) -> BattleSession:
        session = self.get_session(event.session_id)
        validation = self.validate_event(session.session_id, event)
        if not validation.is_valid:
            raise ValueError("; ".join(validation.errors))
        session.event_log.append(event)
        if session.observation_state is None:
            session.observation_state = ObservationState(session_id=session.session_id)
        session.observation_state = self._reducer.apply(session.observation_state, event)
        self._stat_inferrer.apply_to_observation(session.observation_state)
        session.updated_at = datetime.now()
        return session

    def replay_session(self, session_id: str) -> BattleSession:
        session = self.get_session(session_id)
        replayed = ObservationState(session_id=session.session_id)
        for event in session.event_log.list_events():
            replayed = self._reducer.apply(replayed, event)
        self._stat_inferrer.apply_to_observation(replayed)
        session.observation_state = replayed
        session.updated_at = datetime.now()
        return session

    def undo_last_event(self, session_id: str) -> BattleEvent | None:
        session = self.get_session(session_id)
        removed = session.event_log.rollback_last()
        self.replay_session(session_id)
        return removed

    def rollback_to_event(
        self,
        session_id: str,
        event_id: str,
        inclusive: bool = True,
    ) -> bool:
        session = self.get_session(session_id)
        ok = session.event_log.rollback_to_event(event_id, inclusive=inclusive)
        if not ok:
            return False
        self.replay_session(session_id)
        return True

    def apply_correction(
        self,
        session_id: str,
        turn: int,
        correction_type: str,
        payload: dict,
        note: str = "",
    ) -> BattleSession:
        correction_event = self.normalize_event(
            session_id=session_id,
            event_type=EventType.STATE_CORRECTED,
            turn=turn,
            payload={"correction_type": correction_type, **payload},
            source=EventSource.USER,
            note=note,
        )
        return self.append_event(correction_event)

    def apply_import_snapshot(
        self,
        session_id: str,
        turn: int,
        side: str,
        active_pet_name: str | None,
        pets: list[dict],
        note: str = "",
        source: EventSource = EventSource.USER,
    ) -> tuple[BattleSession, str, list[BattleEvent]]:
        if side != "opponent":
            raise ValueError("当前仅支持导入 opponent 战况")
        if not pets:
            raise ValueError("pets 不能为空")

        import_batch_id = f"imp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        created_events: list[BattleEvent] = []

        if active_pet_name:
            active_event = self.normalize_event(
                session_id=session_id,
                event_type=EventType.STATE_CORRECTED,
                turn=turn,
                payload={
                    "correction_type": "active_pet",
                    "side": side,
                    "pet_name": active_pet_name,
                    "import_batch_id": import_batch_id,
                    "created_reason": "snapshot_sync",
                },
                source=source,
                note=note,
            )
            self.append_event(active_event)
            created_events.append(active_event)

        for pet_state in pets:
            pet_name = pet_state.get("pet_name")
            if not pet_name:
                raise ValueError("导入宠物缺少 pet_name")
            hp_percent = pet_state.get("hp_percent")
            energy = pet_state.get("energy")
            if hp_percent is None and energy is None:
                raise ValueError(f"{pet_name} 至少需要提供 hp_percent 或 energy")

            if hp_percent is not None:
                hp_event = self.normalize_event(
                    session_id=session_id,
                    event_type=EventType.STATE_CORRECTED,
                    turn=turn,
                    payload={
                        "correction_type": "pet_hp",
                        "side": side,
                        "pet_name": pet_name,
                        "hp_percent": float(hp_percent),
                        "import_batch_id": import_batch_id,
                        "created_reason": "snapshot_sync",
                    },
                    source=source,
                    note=note,
                )
                self.append_event(hp_event)
                created_events.append(hp_event)

            if energy is not None:
                energy_event = self.normalize_event(
                    session_id=session_id,
                    event_type=EventType.STATE_CORRECTED,
                    turn=turn,
                    payload={
                        "correction_type": "pet_energy",
                        "side": side,
                        "pet_name": pet_name,
                        "energy": int(energy),
                        "import_batch_id": import_batch_id,
                        "created_reason": "snapshot_sync",
                    },
                    source=source,
                    note=note,
                )
                self.append_event(energy_event)
                created_events.append(energy_event)

        session = self.get_session(session_id)
        session.last_import_batch_id = import_batch_id
        session.last_import_turn = turn
        session.last_import_note = note
        session.last_import_at = datetime.now()
        return session, import_batch_id, created_events

    def clear_events(self, session_id: str) -> tuple[BattleSession, int]:
        session = self.get_session(session_id)
        removed_count = session.event_log.clear()
        session.observation_state = ObservationState(session_id=session.session_id)
        session.last_import_batch_id = None
        session.last_import_turn = None
        session.last_import_note = ""
        session.last_import_at = None
        session.updated_at = datetime.now()
        return session, removed_count

    def rollback_import_batch(
        self,
        session_id: str,
        import_batch_id: str,
    ) -> tuple[BattleSession, list[BattleEvent]]:
        session = self.get_session(session_id)
        kept_events: list[BattleEvent] = []
        removed_events: list[BattleEvent] = []
        for event in session.event_log.list_events():
            event_batch_id = event.payload.get("import_batch_id")
            if event_batch_id == import_batch_id:
                removed_events.append(event)
            else:
                kept_events.append(event)
        if not removed_events:
            raise ValueError(f"未找到导入批次: {import_batch_id}")

        session.event_log.events = kept_events
        self.replay_session(session_id)
        self._refresh_import_metadata(session)
        return session, removed_events

    def list_import_batches(self, session_id: str) -> list[dict]:
        session = self.get_session(session_id)
        return self._collect_recent_import_batches(session)

    def get_import_batch_events(
        self,
        session_id: str,
        import_batch_id: str,
    ) -> list[BattleEvent]:
        session = self.get_session(session_id)
        return [
            event
            for event in session.event_log.list_events()
            if event.payload.get("import_batch_id") == import_batch_id
        ]

    def get_session_report(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        obs = session.observation_state
        my_active = obs.my_side.pets.get(obs.my_side.active_pet) if obs and obs.my_side.active_pet else None
        opponent_active = (
            obs.opponent_side.pets.get(obs.opponent_side.active_pet)
            if obs and obs.opponent_side.active_pet else None
        )
        return {
            "session_id": session.session_id,
            "status": session.status,
            "inference_mode": session.config.inference_mode,
            "search_depth": session.config.search_depth,
            "event_count": len(session.event_log.events),
            "last_event_id": session.event_log.last_event().event_id if session.event_log.last_event() else None,
            "turn": obs.turn if obs else 0,
            "my_active_pet": obs.my_side.active_pet if obs else None,
            "opponent_active_pet": obs.opponent_side.active_pet if obs else None,
            "my_hearts": obs.my_side.hearts if obs else None,
            "opponent_hearts": obs.opponent_side.hearts if obs else None,
            "my_active_summary": self._pet_summary(my_active),
            "opponent_active_summary": self._pet_summary(opponent_active),
            "evidence_counts": {
                "speed": len(obs.speed_evidence) if obs else 0,
                "damage": len(obs.damage_evidence) if obs else 0,
                "skill": len(obs.skill_evidence) if obs else 0,
                "copy_skill": len(obs.copy_skill_evidence) if obs else 0,
                "bench_resource": len(obs.bench_resource_evidence) if obs else 0,
                "quick_effect": len(obs.quick_effect_evidence) if obs else 0,
            },
            "last_import_batch_id": session.last_import_batch_id,
            "last_import_turn": session.last_import_turn,
            "last_import_note": session.last_import_note,
            "last_import_at": session.last_import_at.isoformat() if session.last_import_at else None,
            "has_manual_corrections": any(
                event.event_type == EventType.STATE_CORRECTED
                for event in session.event_log.events
            ),
            "recent_import_batches": self._collect_recent_import_batches(session),
            "uncertainty_notes": list(obs.uncertainty_notes) if obs else [],
        }

    def _pet_summary(self, pet) -> dict | None:
        if pet is None:
            return None
        top_traits = sorted(
            pet.inferred_trait_flags.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        top_natures = sorted(
            pet.inferred_natures.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        top_spreads = sorted(
            pet.inferred_ev_spreads.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        stat_ranges = {
            name: {
                "min": value.min_value,
                "max": value.max_value,
                "confidence": value.confidence,
            }
            for name, value in pet.stat_ranges.items()
            if value.min_value is not None or value.max_value is not None
        }
        return {
            "pet_name": pet.pet_name,
            "hp_percent": pet.hp_percent,
            "energy": pet.energy,
            "observed_skills": list(pet.observed_skills),
            "inferred_skills": list(pet.inferred_skills),
            "top_trait_flags": [
                {"name": name, "score": round(score, 4)}
                for name, score in top_traits
                if score > 0
            ],
            "top_natures": [
                {"name": name, "score": round(score, 4)}
                for name, score in top_natures
                if score > 0
            ],
            "top_ev_spreads": [
                {"name": name, "score": round(score, 4)}
                for name, score in top_spreads
                if score > 0
            ],
            "stat_ranges": stat_ranges,
        }

    def normalize_event(self, **kwargs) -> BattleEvent:
        return self._normalizer.normalize(**kwargs)

    def validate_event(
        self, session_id: str, event: BattleEvent
    ) -> EventValidationResult:
        session = self.get_session(session_id)
        return self._validator.validate(session, event)

    def _refresh_import_metadata(self, session: BattleSession) -> None:
        latest_import = None
        for event in reversed(session.event_log.events):
            batch_id = event.payload.get("import_batch_id")
            if batch_id:
                latest_import = event
                break
        if latest_import is None:
            session.last_import_batch_id = None
            session.last_import_turn = None
            session.last_import_note = ""
            session.last_import_at = None
            return
        session.last_import_batch_id = latest_import.payload.get("import_batch_id")
        session.last_import_turn = latest_import.turn
        session.last_import_note = latest_import.note
        session.last_import_at = latest_import.timestamp

    def _collect_recent_import_batches(self, session: BattleSession) -> list[dict]:
        batches: dict[str, dict] = {}
        for event in session.event_log.events:
            batch_id = event.payload.get("import_batch_id")
            if not batch_id:
                continue
            row = batches.setdefault(batch_id, {
                "import_batch_id": batch_id,
                "turn": event.turn,
                "note": event.note,
                "event_count": 0,
                "timestamp": event.timestamp.isoformat(),
            })
            row["event_count"] += 1
        ordered = sorted(
            batches.values(),
            key=lambda item: (item["turn"], item["timestamp"]),
            reverse=True,
        )
        return ordered[:5]
