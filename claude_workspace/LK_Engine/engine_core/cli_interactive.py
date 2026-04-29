"""
交互式命令行接口
基于 agent_runtime 的事件驱动实时对战辅助 CLI。
"""
from __future__ import annotations

import argparse
import shlex
from typing import Iterable

from agent_runtime.core.events import EventSource, EventType
from agent_runtime.engine.recommendation_service import RecommendationService
from agent_runtime.tracker.session_manager import BattleSessionConfig, BattleSessionManager


HELP_TEXT = """
可用命令：
  start <my_pet1,my_pet2,...> <opp_pet1,opp_pet2,...> [mode]
  switch my|opponent <new_pet>
  hp my|opponent <pet_name> <percent>
  energy my|opponent <pet_name> <value>
  skill my|opponent <pet_name> <skill_name>
  status add my|opponent <pet_name> <status_name> [stacks]
  status remove my|opponent <pet_name> <status_name>
  mark pet my|opponent <pet_name> <mark_name> <stacks>
  mark field my|opponent <mark_name> <stacks>
  hearts my|opponent <value>
  import opponent <pet_name> <hp_percent> <energy>
  recommend [depth]
  report
  imports
  imports <import_batch_id>
  undo
  replay
  rollback-import <import_batch_id>
  clear-events
  clear-events CONFIRM
  correct hp my|opponent <pet_name> <percent>
  correct energy my|opponent <pet_name> <value>
  correct active my|opponent <pet_name>
  events
  help
  exit
"""


class InteractiveCLI:
    def __init__(self, session_id: str = "interactive") -> None:
        self.session_id = session_id
        self.manager = BattleSessionManager()
        self.recommendation_service = RecommendationService()
        self.current_turn = 1
        self.started = False
        self._pending_clear_confirmation = False

    def run(self) -> None:
        print("实时对战辅助 CLI")
        print("输入 help 查看命令。")

        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue

            try:
                if not self._handle_line(line):
                    break
            except Exception as exc:
                print(f"[error] {exc}")

    def _handle_line(self, line: str) -> bool:
        parts = shlex.split(line)
        command = parts[0].lower()

        if command == "help":
            print(HELP_TEXT.strip())
            return True
        if command in {"exit", "quit"}:
            return False

        if command == "start":
            self._cmd_start(parts[1:])
        elif command == "switch":
            self._cmd_switch(parts[1:])
        elif command == "hp":
            self._cmd_hp(parts[1:])
        elif command == "energy":
            self._cmd_energy(parts[1:])
        elif command == "skill":
            self._cmd_skill(parts[1:])
        elif command == "status":
            self._cmd_status(parts[1:])
        elif command == "mark":
            self._cmd_mark(parts[1:])
        elif command == "hearts":
            self._cmd_hearts(parts[1:])
        elif command == "import":
            self._cmd_import(parts[1:])
        elif command == "recommend":
            self._cmd_recommend(parts[1:])
        elif command == "report":
            self._cmd_report()
        elif command == "imports":
            self._cmd_imports(parts[1:])
        elif command == "undo":
            self._cmd_undo()
        elif command == "replay":
            self._cmd_replay()
        elif command == "rollback-import":
            self._cmd_rollback_import(parts[1:])
        elif command == "clear-events":
            self._cmd_clear_events(parts[1:])
        elif command == "correct":
            self._cmd_correct(parts[1:])
        elif command == "events":
            self._cmd_events()
        else:
            print(f"[error] 未知命令: {command}")
        return True

    def _cmd_start(self, args: list[str]) -> None:
        if len(args) < 2:
            raise ValueError("start <my_pet1,my_pet2,...> <opp_pet1,opp_pet2,...> [mode]")
        my_team = self._split_csv(args[0])
        opp_team = self._split_csv(args[1])
        inference_mode = args[2] if len(args) > 2 else "hybrid"

        self.manager.create_session(
            self.session_id,
            BattleSessionConfig(
                my_team=my_team,
                opponent_team_candidates=opp_team,
                inference_mode=inference_mode,
            ),
        )
        event = self.manager.normalize_event(
            session_id=self.session_id,
            event_type=EventType.BATTLE_STARTED,
            turn=0,
            payload={"my_team": my_team, "opponent_team": opp_team},
        )
        self.manager.append_event(event)
        self.current_turn = 1
        self.started = True
        print(f"[ok] 已开始对局。my={my_team} opp={opp_team} mode={inference_mode}")

    def _cmd_switch(self, args: list[str]) -> None:
        side, new_pet = self._require_args(args, 2, "switch my|opponent <new_pet>")
        self._append(
            EventType.PET_SWITCHED,
            {"side": side, "new_pet": new_pet},
        )
        print(f"[ok] {side} 切换到 {new_pet}")

    def _cmd_hp(self, args: list[str]) -> None:
        side, pet_name, percent = self._require_args(args, 3, "hp my|opponent <pet_name> <percent>")
        self._append(
            EventType.HP_PERCENT_UPDATED,
            {"side": side, "pet_name": pet_name, "hp_percent": float(percent)},
        )
        print(f"[ok] {side} {pet_name} HP={percent}%")

    def _cmd_energy(self, args: list[str]) -> None:
        side, pet_name, value = self._require_args(args, 3, "energy my|opponent <pet_name> <value>")
        self._append(
            EventType.ENERGY_UPDATED,
            {"side": side, "pet_name": pet_name, "energy": int(value)},
        )
        print(f"[ok] {side} {pet_name} energy={value}")

    def _cmd_skill(self, args: list[str]) -> None:
        side, pet_name, skill_name = self._require_args(args, 3, "skill my|opponent <pet_name> <skill_name>")
        event_type = EventType.SKILL_USED if side == "my" else EventType.OPPONENT_ACTION_OBSERVED
        self._append(
            event_type,
            {"side": side, "pet_name": pet_name, "skill_name": skill_name, "action_type": "USE_SKILL"},
            actor_side=side if side == "opponent" else None,
        )
        print(f"[ok] {side} {pet_name} 使用 {skill_name}")

    def _cmd_status(self, args: list[str]) -> None:
        if len(args) < 4:
            raise ValueError("status add/remove my|opponent <pet_name> <status_name> [stacks]")
        op = args[0]
        side = args[1]
        pet_name = args[2]
        status_name = args[3]
        if op == "add":
            stacks = int(args[4]) if len(args) > 4 else 1
            self._append(
                EventType.STATUS_APPLIED,
                {"side": side, "pet_name": pet_name, "status_name": status_name, "stacks": stacks},
            )
            print(f"[ok] {side} {pet_name} 添加状态 {status_name} x{stacks}")
            return
        if op == "remove":
            self._append(
                EventType.STATUS_REMOVED,
                {"side": side, "pet_name": pet_name, "status_name": status_name},
            )
            print(f"[ok] {side} {pet_name} 移除状态 {status_name}")
            return
        raise ValueError("status 仅支持 add/remove")

    def _cmd_mark(self, args: list[str]) -> None:
        if len(args) < 4:
            raise ValueError("mark pet my|opponent <pet_name> <mark_name> <stacks> | mark field my|opponent <mark_name> <stacks>")
        target_type = args[0]
        side = args[1]
        if target_type == "pet":
            if len(args) < 5:
                raise ValueError("mark pet my|opponent <pet_name> <mark_name> <stacks>")
            pet_name, mark_name, stacks = args[2], args[3], int(args[4])
            payload = {
                "side": side,
                "target_type": "pet",
                "pet_name": pet_name,
                "mark_name": mark_name,
                "stacks": stacks,
            }
            self._append(EventType.MARK_UPDATED, payload)
            print(f"[ok] {side} {pet_name} 印记 {mark_name}={stacks}")
            return
        if target_type == "field":
            if len(args) < 4:
                raise ValueError("mark field my|opponent <mark_name> <stacks>")
            mark_name, stacks = args[2], int(args[3])
            payload = {
                "side": side,
                "target_type": "field",
                "mark_name": mark_name,
                "stacks": stacks,
            }
            self._append(EventType.MARK_UPDATED, payload)
            print(f"[ok] field {side} 印记 {mark_name}={stacks}")
            return
        raise ValueError("mark 仅支持 pet/field")

    def _cmd_hearts(self, args: list[str]) -> None:
        side, value = self._require_args(args, 2, "hearts my|opponent <value>")
        self._append(
            EventType.HEARTS_UPDATED,
            {"side": side, "hearts": int(value)},
        )
        print(f"[ok] {side} hearts={value}")

    def _cmd_import(self, args: list[str]) -> None:
        self._require_started()
        side, pet_name, hp_percent, energy = self._require_args(
            args,
            4,
            "import opponent <pet_name> <hp_percent> <energy>",
        )
        if side != "opponent":
            raise ValueError("import 当前仅支持 opponent")
        _, import_batch_id, created_events = self.manager.apply_import_snapshot(
            session_id=self.session_id,
            turn=self.current_turn,
            side=side,
            active_pet_name=pet_name,
            pets=[{
                "pet_name": pet_name,
                "hp_percent": float(hp_percent),
                "energy": int(energy),
            }],
            note="CLI import opponent state",
            source=EventSource.USER,
        )
        print(
            f"[ok] 已导入敌方战况 batch={import_batch_id} "
            f"pet={pet_name} hp={hp_percent}% energy={energy} events={len(created_events)}"
        )

    def _cmd_recommend(self, args: list[str]) -> None:
        self._require_started()
        depth = int(args[0]) if args else 2
        rec = self.recommendation_service.recommend(
            self.manager.get_session(self.session_id),
            depth=depth,
        )
        print(f"[recommend] confidence={rec.confidence:.2f} score={rec.score:.1f}")
        print(f"[recommend] action={rec.best_action}")
        self._print_confidence_breakdown(rec.confidence_breakdown)
        for note in rec.risk_notes:
            print(f"[risk] {note}")
        self._print_alternatives(rec.alternatives)
        self._print_assumptions(rec.based_on_assumptions)

    def _cmd_report(self) -> None:
        self._require_started()
        report = self.manager.get_session_report(self.session_id)
        print(
            "[report] turn={turn} events={events} my_active={my_active} "
            "opp_active={opp_active} my_hearts={my_hearts} opp_hearts={opp_hearts}".format(
                turn=report.get("turn"),
                events=report.get("event_count"),
                my_active=report.get("my_active_pet"),
                opp_active=report.get("opponent_active_pet"),
                my_hearts=report.get("my_hearts"),
                opp_hearts=report.get("opponent_hearts"),
            )
        )
        if report.get("last_import_batch_id"):
            print(
                "[report] last_import batch={batch} turn={turn} at={at} note={note}".format(
                    batch=report.get("last_import_batch_id"),
                    turn=report.get("last_import_turn"),
                    at=report.get("last_import_at"),
                    note=report.get("last_import_note") or "",
                )
            )
        print("[report] evidence_counts:")
        for key, value in report.get("evidence_counts", {}).items():
            print(f"  {key}: {value}")
        self._print_pet_summary("my", report.get("my_active_summary"))
        self._print_pet_summary("opponent", report.get("opponent_active_summary"))
        recent_imports = report.get("recent_import_batches") or []
        if recent_imports:
            print("[report] recent_import_batches:")
            for row in recent_imports:
                print(
                    "  batch={batch} turn={turn} events={count} note={note}".format(
                        batch=row.get("import_batch_id"),
                        turn=row.get("turn"),
                        count=row.get("event_count"),
                        note=row.get("note") or "",
                    )
                )

    def _cmd_imports(self, args: list[str]) -> None:
        self._require_started()
        if not args:
            imports = self.manager.list_import_batches(self.session_id)
            if not imports:
                print("[imports] 当前没有导入批次")
                return
            for row in imports:
                print(
                    "[imports] batch={batch} turn={turn} events={count} at={at} note={note}".format(
                        batch=row.get("import_batch_id"),
                        turn=row.get("turn"),
                        count=row.get("event_count"),
                        at=row.get("timestamp"),
                        note=row.get("note") or "",
                    )
                )
            return
        import_batch_id, = self._require_args(args, 1, "imports [import_batch_id]")
        events = self.manager.get_import_batch_events(self.session_id, import_batch_id)
        if not events:
            print(f"[imports] 未找到导入批次 {import_batch_id}")
            return
        print(f"[imports] batch={import_batch_id} events={len(events)}")
        for event in events:
            correction_type = event.payload.get("correction_type")
            pet_name = event.payload.get("pet_name")
            print(
                f"  {event.event_id} turn={event.turn} correction={correction_type} "
                f"pet={pet_name} payload={event.payload}"
            )

    def _cmd_undo(self) -> None:
        self._require_started()
        event = self.manager.undo_last_event(self.session_id)
        if event is None:
            print("[ok] 没有可撤销事件")
            return
        print(f"[ok] 已撤销 {event.event_type.value} ({event.event_id})")

    def _cmd_replay(self) -> None:
        self._require_started()
        self.manager.replay_session(self.session_id)
        print("[ok] 已从日志重放当前会话")

    def _cmd_rollback_import(self, args: list[str]) -> None:
        self._require_started()
        import_batch_id, = self._require_args(args, 1, "rollback-import <import_batch_id>")
        _, removed_events = self.manager.rollback_import_batch(
            self.session_id,
            import_batch_id=import_batch_id,
        )
        print(
            f"[ok] 已撤回导入批次 {import_batch_id}，"
            f"共移除 {len(removed_events)} 条事件"
        )

    def _cmd_clear_events(self, args: list[str]) -> None:
        self._require_started()
        if args and args[0] == "CONFIRM":
            _, removed_count = self.manager.clear_events(self.session_id)
            self._pending_clear_confirmation = False
            print(f"[ok] 已清空事件信息，共移除 {removed_count} 条事件，保留会话配置")
            return
        self._pending_clear_confirmation = True
        print("此操作会清空当前对局累计的事件、修正和推断结果，但保留会话配置。")
        print("如确认，请输入：clear-events CONFIRM")

    def _cmd_correct(self, args: list[str]) -> None:
        if len(args) < 1:
            raise ValueError("correct hp/energy/active ...")
        self._require_started()
        correction = args[0]
        if correction == "hp":
            side, pet_name, percent = self._require_args(args[1:], 3, "correct hp my|opponent <pet_name> <percent>")
            self.manager.apply_correction(
                self.session_id,
                turn=self.current_turn,
                correction_type="pet_hp",
                payload={"side": side, "pet_name": pet_name, "hp_percent": float(percent)},
            )
            print(f"[ok] corrected hp {side} {pet_name}={percent}")
            return
        if correction == "energy":
            side, pet_name, value = self._require_args(args[1:], 3, "correct energy my|opponent <pet_name> <value>")
            self.manager.apply_correction(
                self.session_id,
                turn=self.current_turn,
                correction_type="pet_energy",
                payload={"side": side, "pet_name": pet_name, "energy": int(value)},
            )
            print(f"[ok] corrected energy {side} {pet_name}={value}")
            return
        if correction == "active":
            side, pet_name = self._require_args(args[1:], 2, "correct active my|opponent <pet_name>")
            self.manager.apply_correction(
                self.session_id,
                turn=self.current_turn,
                correction_type="active_pet",
                payload={"side": side, "pet_name": pet_name},
            )
            print(f"[ok] corrected active {side}={pet_name}")
            return
        raise ValueError("correct 仅支持 hp/energy/active")

    def _cmd_events(self) -> None:
        self._require_started()
        session = self.manager.get_session(self.session_id)
        for event in session.event_log.list_events():
            batch_id = event.payload.get("import_batch_id")
            batch_text = f" batch={batch_id}" if batch_id else ""
            print(
                f"{event.event_id} turn={event.turn} {event.event_type.value}"
                f"{batch_text} payload={event.payload}"
            )

    def _append(self, event_type: EventType, payload: dict, actor_side: str | None = None) -> None:
        self._require_started()
        event = self.manager.normalize_event(
            session_id=self.session_id,
            event_type=event_type,
            turn=self.current_turn,
            payload=payload,
            actor_side=actor_side,
        )
        self.manager.append_event(event)

    def _require_started(self) -> None:
        if not self.started:
            raise ValueError("请先使用 start 命令创建对局")

    def _split_csv(self, text: str) -> list[str]:
        return [item.strip() for item in text.split(",") if item.strip()]

    def _require_args(self, args: list[str], count: int, usage: str):
        if len(args) < count:
            raise ValueError(usage)
        return args[:count]

    def _print_confidence_breakdown(self, breakdown: dict) -> None:
        if not breakdown:
            return
        belief_weight = breakdown.get("belief_weight")
        skill_probability = breakdown.get("skill_probability")
        profile_probability = breakdown.get("profile_probability")
        profile_label = breakdown.get("profile_label")
        action_support = breakdown.get("action_support")
        score_span = breakdown.get("score_span")
        skill_signature = breakdown.get("skill_signature") or []

        header_parts: list[str] = []
        if belief_weight is not None:
            header_parts.append(f"belief={belief_weight:.3f}")
        if skill_probability is not None:
            header_parts.append(f"skill_prob={skill_probability:.3f}")
        if profile_probability is not None:
            header_parts.append(f"profile_prob={profile_probability:.3f}")
        if action_support is not None:
            header_parts.append(f"support={action_support:.3f}")
        if score_span is not None:
            header_parts.append(f"score_span={float(score_span):.1f}")
        if profile_label:
            header_parts.append(f"profile={profile_label}")
        print(f"[confidence] {' '.join(header_parts)}")

        if skill_signature:
            print(f"[confidence] skill_signature={', '.join(skill_signature)}")

        dominant_skill_sets = breakdown.get("dominant_skill_sets") or []
        for row in dominant_skill_sets[:3]:
            skills = ", ".join(row.get("skills", []))
            print(f"[belief-skill] weight={row.get('belief_weight', 0):.3f} skills={skills}")

        dominant_profiles = breakdown.get("dominant_profiles") or []
        for row in dominant_profiles[:3]:
            print(f"[belief-profile] weight={row.get('belief_weight', 0):.3f} label={row.get('label')}")

    def _print_alternatives(self, alternatives: list[dict]) -> None:
        if not alternatives:
            return
        for index, item in enumerate(alternatives[:3], start=1):
            action = item.get("action", {})
            label = action.get("display") or action
            print(
                "[alt-{idx}] support={support:.3f} conf={conf:.3f} "
                "selected={selected:.1f} expected={expected:.1f} worst={worst:.1f} action={action}".format(
                    idx=index,
                    support=float(item.get("action_support", 0.0)),
                    conf=float(item.get("confidence", 0.0)),
                    selected=float(item.get("selected_score", 0.0)),
                    expected=float(item.get("expected_score", 0.0)),
                    worst=float(item.get("worst_score", 0.0)),
                    action=label,
                )
            )

    def _print_assumptions(self, assumptions: list[str]) -> None:
        if not assumptions:
            return
        for item in assumptions[:5]:
            print(f"[assumption] {item}")

    def _print_pet_summary(self, side: str, summary: dict | None) -> None:
        if not summary:
            print(f"[report] {side}_active_summary: None")
            return
        print(
            "[report] {side}_active pet={pet} hp={hp} energy={energy} observed_skills={skills}".format(
                side=side,
                pet=summary.get("pet_name"),
                hp=summary.get("hp_percent"),
                energy=summary.get("energy"),
                skills=",".join(summary.get("observed_skills", [])),
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="事件驱动实时对战辅助 CLI")
    parser.add_argument("--session-id", default="interactive", help="会话 ID")
    args = parser.parse_args()

    cli = InteractiveCLI(session_id=args.session_id)
    cli.run()


if __name__ == "__main__":
    main()
