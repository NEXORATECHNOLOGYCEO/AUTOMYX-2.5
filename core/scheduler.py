from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

SCHEDULES_FILE = Path.home() / ".automyx" / "schedules.json"
RUNS_FILE = Path.home() / ".automyx" / "schedule_runs.jsonl"

_scheduler_instance: Optional["AgentScheduler"] = None


def _ensure():
    SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_schedules() -> List[Dict[str, Any]]:
    if SCHEDULES_FILE.exists():
        try:
            return json.loads(SCHEDULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_schedules(schedules: List[Dict[str, Any]]):
    _ensure()
    SCHEDULES_FILE.write_text(json.dumps(schedules, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_run(run: Dict[str, Any]):
    _ensure()
    with open(RUNS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")


def _match_field(field: str, value: int) -> bool:
    if field == "*":
        return True
    if "," in field:
        return value in [int(x) for x in field.split(",")]
    if "-" in field:
        parts = field.split("-")
        return int(parts[0]) <= value <= int(parts[1])
    if "/" in field:
        parts = field.split("/")
        base = 0 if parts[0] == "*" else int(parts[0])
        step = int(parts[1])
        return (value - base) % step == 0
    try:
        return int(field) == value
    except ValueError:
        return False


def _parse_cron(cron_expr: str) -> bool:
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expresión cron inválida (necesita 5 campos): {cron_expr}")
    return True


def _should_run(cron_expr: str, last_run: Optional[str]) -> bool:
    now = datetime.now()
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return False

    minute, hour, day, month, weekday = parts

    if not _match_field(minute, now.minute):
        return False
    if not _match_field(hour, now.hour):
        return False
    if not _match_field(day, now.day):
        return False
    if not _match_field(month, now.month):
        return False
    if not _match_field(weekday, now.weekday()):
        return False

    if last_run is not None:
        try:
            last_dt = datetime.fromisoformat(last_run)
            if (now - last_dt).total_seconds() < 59:
                return False
        except Exception:
            pass

    return True


class AgentScheduler:
    def __init__(self, agent_runner: Optional[Callable[[str, str], str]] = None):
        self.agent_runner = agent_runner
        self._schedules: List[Dict[str, Any]] = _load_schedules()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def add(self, cron_expr: str, task: str, workspace: str = "default") -> str:
        _parse_cron(cron_expr)
        schedule_id = str(uuid.uuid4())[:8]
        entry = {
            "id": schedule_id,
            "cron": cron_expr,
            "task": task,
            "workspace": workspace,
            "last_run": None,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        self._schedules.append(entry)
        _save_schedules(self._schedules)
        return schedule_id

    def remove(self, schedule_id: str) -> bool:
        before = len(self._schedules)
        self._schedules = [s for s in self._schedules if s["id"] != schedule_id]
        if len(self._schedules) < before:
            _save_schedules(self._schedules)
            return True
        return False

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._schedules)

    def enable(self, schedule_id: str) -> bool:
        return self._set_enabled(schedule_id, True)

    def disable(self, schedule_id: str) -> bool:
        return self._set_enabled(schedule_id, False)

    def _set_enabled(self, schedule_id: str, enabled: bool) -> bool:
        for s in self._schedules:
            if s["id"] == schedule_id:
                s["enabled"] = enabled
                _save_schedules(self._schedules)
                return True
        return False

    def run_now(self, schedule_id: str):
        for s in self._schedules:
            if s["id"] == schedule_id:
                t = threading.Thread(
                    target=self._execute_schedule,
                    args=(s,),
                    daemon=True,
                    name=f"schedule-{schedule_id}",
                )
                t.start()
                return True
        return False

    def _execute_schedule(self, schedule: Dict[str, Any]):
        started = datetime.now().isoformat()
        result = ""
        error = ""
        try:
            if self.agent_runner:
                result = self.agent_runner(schedule["task"], schedule.get("workspace", "default"))
            else:
                result = "agent_runner no configurado"
        except Exception as e:
            error = str(e)

        schedule["last_run"] = datetime.now().isoformat()
        _save_schedules(self._schedules)

        run_record = {
            "schedule_id": schedule["id"],
            "task": schedule["task"],
            "workspace": schedule.get("workspace", "default"),
            "started_at": started,
            "finished_at": schedule["last_run"],
            "result": result[:500] if result else "",
            "error": error,
        }
        _append_run(run_record)

    def _loop(self):
        while not self._stop_event.is_set():
            now_str = datetime.now().isoformat()
            for s in list(self._schedules):
                if not s.get("enabled", True):
                    continue
                try:
                    if _should_run(s["cron"], s.get("last_run")):
                        t = threading.Thread(
                            target=self._execute_schedule,
                            args=(s,),
                            daemon=True,
                            name=f"schedule-{s['id']}",
                        )
                        t.start()
                except Exception:
                    pass
            self._stop_event.wait(60)

    def start_background(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="automyx-scheduler")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)


def get_scheduler(agent_runner: Optional[Callable] = None) -> AgentScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AgentScheduler(agent_runner=agent_runner)
    return _scheduler_instance
