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


# ── Auto-encendido: Programador de tareas de Windows ─────────────────────────
# Crea una tarea de Windows que lanza `python automyx.py cron <id>` a la hora
# programada — Automyx se ENCIENDE SOLO aunque el REPL esté cerrado.

REPORTS_DIR = Path.home() / ".automyx" / "schedule_reports"


def _task_name(schedule_id: str) -> str:
    return f"Automyx_{schedule_id}"


def _automyx_entry() -> tuple:
    import sys
    root = Path(__file__).resolve().parent.parent
    return sys.executable, str(root / "automyx.py")


def create_windows_task(schedule_id: str, cron_expr: str) -> str:
    """Traduce crons simples a schtasks. Soporta: 'M H * * *' (diario HH:MM),
    '*/N * * * *' (cada N min), 'M H * * D' (semanal). Devuelve descripción."""
    import subprocess
    py, entry = _automyx_entry()
    tr = f'"{py}" "{entry}" cron {schedule_id}'
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError("cron inválido")
    minute, hour, day, month, weekday = parts

    base = ["schtasks", "/Create", "/TN", _task_name(schedule_id), "/TR", tr, "/F"]
    if minute.startswith("*/") and hour == "*":
        n = int(minute[2:])
        cmd = base + ["/SC", "MINUTE", "/MO", str(n)]
        desc = f"cada {n} min"
    elif minute.isdigit() and hour.isdigit() and weekday != "*" and weekday.isdigit():
        dias = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        st = f"{int(hour):02d}:{int(minute):02d}"
        cmd = base + ["/SC", "WEEKLY", "/D", dias[int(weekday) % 7], "/ST", st]
        desc = f"semanal {dias[int(weekday) % 7]} {st}"
    elif minute.isdigit() and hour.isdigit():
        st = f"{int(hour):02d}:{int(minute):02d}"
        cmd = base + ["/SC", "DAILY", "/ST", st]
        desc = f"diario a las {st}"
    else:
        raise ValueError("cron demasiado complejo para el Programador de Windows "
                         "(usa HH:MM, cada Nm, o día semanal)")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "schtasks falló").strip()[:200])
    return desc


def delete_windows_task(schedule_id: str) -> bool:
    import subprocess
    r = subprocess.run(["schtasks", "/Delete", "/TN", _task_name(schedule_id), "/F"],
                       capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def run_headless(schedule_id: str) -> int:
    """Runner del Programador de Windows: carga el agente completo, ejecuta la
    tarea programada de forma autónoma y guarda el reporte en markdown."""
    schedules = _load_schedules()
    sched = next((s for s in schedules if s["id"] == schedule_id
                  or s["id"].startswith(schedule_id)), None)
    if not sched:
        print(f"tarea programada no encontrada: {schedule_id}")
        return 1
    if not sched.get("enabled", True):
        print(f"tarea {schedule_id} deshabilitada — no se ejecuta")
        return 0

    started = datetime.now()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{sched['id']}_{started.strftime('%Y%m%d_%H%M')}.md"

    task = (
        f"{sched['task']}\n\n"
        f"[TAREA PROGRAMADA — MODO AUTÓNOMO] Nadie está mirando la terminal: no "
        f"preguntes nada, toma decisiones tú mismo y ejecuta hasta terminar. Si "
        f"diagnosticas un problema, ARRÉGLALO y verifica el arreglo. Termina "
        f"SIEMPRE con un reporte claro: estado encontrado, qué hiciste, y "
        f"recomendaciones."
    )
    result, error = "", ""
    try:
        from core.agent import AutomyxAgent
        from core.tool_registry import register_all_tools
        agent = AutomyxAgent()
        try:
            register_all_tools(agent)
        except Exception:
            pass
        result = agent.run(task) or "(sin respuesta)"
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    finished = datetime.now()
    dur = (finished - started).total_seconds()
    report = (
        f"# Reporte Automyx — tarea programada `{sched['id']}`\n\n"
        f"- **Tarea:** {sched['task']}\n"
        f"- **Inicio:** {started.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- **Duración:** {dur:.0f}s\n"
        f"- **Estado:** {'❌ ERROR' if error else '✅ completada'}\n\n"
        f"---\n\n"
        + (f"## Error\n\n```\n{error}\n```\n" if error else f"## Resultado\n\n{result}\n")
    )
    report_path.write_text(report, encoding="utf-8")

    sched["last_run"] = finished.isoformat()
    _save_schedules(schedules)
    _append_run({
        "schedule_id": sched["id"], "task": sched["task"],
        "started_at": started.isoformat(), "finished_at": finished.isoformat(),
        "result": (result or error)[:500], "error": error,
        "report": str(report_path), "headless": True,
    })
    print(f"reporte: {report_path}")
    return 1 if error else 0
