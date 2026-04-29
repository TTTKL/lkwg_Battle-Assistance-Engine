import unittest
import uuid
from copy import deepcopy

from agent_runtime.core.events import EventType
from agent_runtime.engine.recommendation_service import RecommendationService
from agent_runtime.tracker.session_manager import BattleSessionConfig, BattleSessionManager


MY_PET = "火花"
OPPONENT_PET = "喵呜"


class AgentRuntimeFlowTest(unittest.TestCase):
    def setUp(self):
        self.manager = BattleSessionManager()
        self.recommendation_service = RecommendationService()
        self.session_id = f"agent-runtime-{uuid.uuid4().hex[:8]}"

    def test_runtime_recommendation_and_report(self):
        self._create_session()

        self._append(
            EventType.BATTLE_STARTED,
            turn=0,
            payload={
                "my_team": [MY_PET],
                "opponent_team": [OPPONENT_PET],
            },
        )
        self._append(
            EventType.PET_SWITCHED,
            turn=1,
            payload={
                "side": "my",
                "new_pet": MY_PET,
            },
        )
        self._append(
            EventType.PET_SWITCHED,
            turn=1,
            payload={
                "side": "opponent",
                "new_pet": OPPONENT_PET,
            },
        )
        self._append(
            EventType.SKILL_USED,
            turn=1,
            payload={
                "side": "my",
                "pet_name": MY_PET,
                "skill_name": "抓挠",
                "action_type": "USE_SKILL",
            },
        )
        self._append(
            EventType.OPPONENT_ACTION_OBSERVED,
            turn=1,
            payload={
                "pet_name": OPPONENT_PET,
                "skill_name": "叫声",
                "action_type": "USE_SKILL",
            },
            actor_side="opponent",
        )
        self._append(
            EventType.HP_PERCENT_UPDATED,
            turn=1,
            payload={
                "side": "my",
                "pet_name": MY_PET,
                "hp_percent": 88,
            },
        )
        self._append(
            EventType.HP_PERCENT_UPDATED,
            turn=1,
            payload={
                "side": "opponent",
                "pet_name": OPPONENT_PET,
                "hp_percent": 72,
            },
        )
        self._append(
            EventType.ENERGY_UPDATED,
            turn=1,
            payload={
                "side": "my",
                "pet_name": MY_PET,
                "energy": 7,
            },
        )

        session = self.manager.get_session(self.session_id)
        recommendation = self.recommendation_service.recommend(session, depth=1)
        self.assertIsInstance(recommendation.best_action, dict)
        self.assertIn("action_support", recommendation.confidence_breakdown)
        self.assertIn("dominant_skill_sets", recommendation.confidence_breakdown)
        self.assertIn("dominant_profiles", recommendation.confidence_breakdown)
        self.assertIn("score_span", recommendation.confidence_breakdown)
        self.assertTrue(recommendation.risk_notes)

        report = self.manager.get_session_report(self.session_id)
        self.assertEqual(report["my_active_pet"], MY_PET)
        self.assertIn("my_active_summary", report)
        self.assertIn("opponent_active_summary", report)
        self.assertIn("evidence_counts", report)
        self.assertIn("skill", report["evidence_counts"])
        self.assertEqual(report["my_active_summary"]["pet_name"], MY_PET)
        self.assertEqual(report["my_active_summary"]["energy"], 7)
        self.assertEqual(report["opponent_active_summary"]["pet_name"], OPPONENT_PET)

    def test_observed_opponent_action_sets_active_and_session_tools_work(self):
        self._create_session()

        self._append(
            EventType.BATTLE_STARTED,
            turn=0,
            payload={
                "my_team": [MY_PET],
                "opponent_team": [OPPONENT_PET],
            },
        )
        self._append(
            EventType.OPPONENT_ACTION_OBSERVED,
            turn=1,
            payload={
                "pet_name": OPPONENT_PET,
                "skill_name": "叫声",
                "action_type": "USE_SKILL",
            },
            actor_side="opponent",
        )

        report = self.manager.get_session_report(self.session_id)
        self.assertEqual(report["opponent_active_pet"], OPPONENT_PET)
        self.assertEqual(report["opponent_active_summary"]["pet_name"], OPPONENT_PET)

        self._append(
            EventType.HP_PERCENT_UPDATED,
            turn=1,
            payload={
                "side": "opponent",
                "pet_name": OPPONENT_PET,
                "hp_percent": 65,
            },
        )
        corrected = self.manager.apply_correction(
            self.session_id,
            turn=1,
            correction_type="pet_hp",
            payload={
                "side": "opponent",
                "pet_name": OPPONENT_PET,
                "hp_percent": 61,
            },
        )
        self.assertEqual(
            corrected.observation_state.opponent_side.pets[OPPONENT_PET].hp_percent,
            61.0,
        )

        removed = self.manager.undo_last_event(self.session_id)
        self.assertIsNotNone(removed)
        self.assertEqual(removed.event_type, EventType.STATE_CORRECTED)
        self.assertEqual(
            self.manager.get_session(self.session_id).observation_state.opponent_side.pets[OPPONENT_PET].hp_percent,
            65.0,
        )

        replayed = self.manager.replay_session(self.session_id)
        self.assertEqual(
            replayed.observation_state.opponent_side.pets[OPPONENT_PET].hp_percent,
            65.0,
        )

        recommendation = self.recommendation_service.recommend(
            self.manager.get_session(self.session_id),
            depth=1,
        )
        self.assertIsInstance(recommendation.best_action, dict)
        self.assertTrue(recommendation.risk_notes)

    def test_import_snapshot_preserves_evidence_and_clear_events_resets_runtime_state(self):
        self._create_session()

        self._append(
            EventType.BATTLE_STARTED,
            turn=0,
            payload={
                "my_team": [MY_PET],
                "opponent_team": [OPPONENT_PET],
            },
        )
        self._append(
            EventType.OPPONENT_ACTION_OBSERVED,
            turn=1,
            payload={
                "pet_name": OPPONENT_PET,
                "skill_name": "叫声",
                "action_type": "USE_SKILL",
            },
            actor_side="opponent",
        )

        session, import_batch_id, created_events = self.manager.apply_import_snapshot(
            session_id=self.session_id,
            turn=1,
            side="opponent",
            active_pet_name=OPPONENT_PET,
            pets=[{
                "pet_name": OPPONENT_PET,
                "hp_percent": 64,
                "energy": 5,
            }],
            note="test import",
        )

        opponent_pet = session.observation_state.opponent_side.pets[OPPONENT_PET]
        self.assertEqual(opponent_pet.hp_percent, 64.0)
        self.assertEqual(opponent_pet.energy, 5)
        self.assertIn("叫声", opponent_pet.observed_skills)
        self.assertTrue(import_batch_id.startswith("imp_"))
        self.assertEqual(len(created_events), 3)

        report = self.manager.get_session_report(self.session_id)
        self.assertEqual(report["last_import_batch_id"], import_batch_id)
        self.assertEqual(report["last_import_turn"], 1)
        self.assertEqual(report["last_import_note"], "test import")
        self.assertTrue(report["has_manual_corrections"])

        session_after_clear, cleared_count = self.manager.clear_events(self.session_id)
        self.assertGreaterEqual(cleared_count, 1)
        self.assertEqual(len(session_after_clear.event_log.events), 0)
        self.assertEqual(session_after_clear.observation_state.turn, 0)
        self.assertEqual(session_after_clear.observation_state.event_cursor, 0)
        self.assertIsNone(session_after_clear.last_import_batch_id)
        self.assertFalse(self.manager.get_session_report(self.session_id)["has_manual_corrections"])

    def test_rollback_import_batch_only_removes_import_events(self):
        self._create_session()

        self._append(
            EventType.BATTLE_STARTED,
            turn=0,
            payload={
                "my_team": [MY_PET],
                "opponent_team": [OPPONENT_PET],
            },
        )
        self._append(
            EventType.OPPONENT_ACTION_OBSERVED,
            turn=1,
            payload={
                "pet_name": OPPONENT_PET,
                "skill_name": "叫声",
                "action_type": "USE_SKILL",
            },
            actor_side="opponent",
        )
        self._append(
            EventType.HP_PERCENT_UPDATED,
            turn=1,
            payload={
                "side": "opponent",
                "pet_name": OPPONENT_PET,
                "hp_percent": 88,
            },
        )

        _, import_batch_id, created_events = self.manager.apply_import_snapshot(
            session_id=self.session_id,
            turn=1,
            side="opponent",
            active_pet_name=OPPONENT_PET,
            pets=[{
                "pet_name": OPPONENT_PET,
                "hp_percent": 64,
                "energy": 5,
            }],
            note="rollback import test",
        )
        self.assertEqual(len(created_events), 3)

        session, removed_events = self.manager.rollback_import_batch(
            self.session_id,
            import_batch_id=import_batch_id,
        )
        self.assertEqual(len(removed_events), 3)
        opponent_pet = session.observation_state.opponent_side.pets[OPPONENT_PET]
        self.assertEqual(opponent_pet.hp_percent, 88.0)
        self.assertIn("叫声", opponent_pet.observed_skills)
        report = self.manager.get_session_report(self.session_id)
        self.assertIsNone(report["last_import_batch_id"])
        self.assertEqual(report["recent_import_batches"], [])

    def test_import_batch_listing_and_detail(self):
        self._create_session()

        self._append(
            EventType.BATTLE_STARTED,
            turn=0,
            payload={
                "my_team": [MY_PET],
                "opponent_team": [OPPONENT_PET],
            },
        )

        _, import_batch_id, created_events = self.manager.apply_import_snapshot(
            session_id=self.session_id,
            turn=2,
            side="opponent",
            active_pet_name=OPPONENT_PET,
            pets=[{
                "pet_name": OPPONENT_PET,
                "hp_percent": 55,
                "energy": 4,
            }],
            note="list import test",
        )

        batches = self.manager.list_import_batches(self.session_id)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["import_batch_id"], import_batch_id)
        self.assertEqual(batches[0]["event_count"], len(created_events))

        batch_events = self.manager.get_import_batch_events(self.session_id, import_batch_id)
        self.assertEqual(len(batch_events), len(created_events))
        self.assertTrue(all(event.payload.get("import_batch_id") == import_batch_id for event in batch_events))

    def test_replay_session_matches_incremental_observation_state(self):
        self._create_session()

        self._append(
            EventType.BATTLE_STARTED,
            turn=0,
            payload={
                "my_team": [MY_PET],
                "opponent_team": [OPPONENT_PET],
            },
        )
        self._append(
            EventType.PET_SWITCHED,
            turn=1,
            payload={
                "side": "opponent",
                "new_pet": OPPONENT_PET,
            },
        )
        self._append(
            EventType.OPPONENT_ACTION_OBSERVED,
            turn=1,
            payload={
                "pet_name": OPPONENT_PET,
                "skill_name": "叫声",
                "action_type": "USE_SKILL",
            },
            actor_side="opponent",
        )
        self.manager.apply_import_snapshot(
            session_id=self.session_id,
            turn=1,
            side="opponent",
            active_pet_name=OPPONENT_PET,
            pets=[{
                "pet_name": OPPONENT_PET,
                "hp_percent": 64,
                "energy": 5,
            }],
            note="replay consistency",
        )

        before_replay = deepcopy(self.manager.get_session(self.session_id).observation_state)
        replayed_session = self.manager.replay_session(self.session_id)
        after_replay = replayed_session.observation_state

        self.assertEqual(before_replay.turn, after_replay.turn)
        self.assertEqual(before_replay.event_cursor, after_replay.event_cursor)
        self.assertEqual(before_replay.opponent_side.active_pet, after_replay.opponent_side.active_pet)
        self.assertEqual(
            before_replay.opponent_side.pets[OPPONENT_PET].hp_percent,
            after_replay.opponent_side.pets[OPPONENT_PET].hp_percent,
        )
        self.assertEqual(
            before_replay.opponent_side.pets[OPPONENT_PET].energy,
            after_replay.opponent_side.pets[OPPONENT_PET].energy,
        )
        self.assertEqual(
            before_replay.opponent_side.pets[OPPONENT_PET].observed_skills,
            after_replay.opponent_side.pets[OPPONENT_PET].observed_skills,
        )

    def _create_session(self):
        self.manager.create_session(
            self.session_id,
            BattleSessionConfig(
                my_team=[MY_PET],
                opponent_team_candidates=[OPPONENT_PET],
                search_depth=1,
                inference_mode="hybrid",
            ),
        )

    def _append(self, event_type, turn: int, payload: dict, actor_side: str | None = None):
        event = self.manager.normalize_event(
            session_id=self.session_id,
            event_type=event_type,
            turn=turn,
            payload=payload,
            actor_side=actor_side,
        )
        self.manager.append_event(event)


if __name__ == "__main__":
    unittest.main()
