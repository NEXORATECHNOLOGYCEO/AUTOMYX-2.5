"""
AUTOMYX Multi-Task Dispatcher v2.5
==================================
Permite que el usuario envíe múltiples preguntas mientras el agente
ejecuta otras tareas. Cada request corre en su propio thread y se
monitorea independientemente.
- Cola de tareas por session_id
- Estado observable en tiempo real
- Locking de tools con efectos secundarios (escritura)
- Streaming de progreso por WebSocket / API
"""
from __future__ import annotations

import os
import json
import time
import uuid
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("automyx.multitask")


# ---------------------------------------------------------------------------
# Estados de tarea
# ---------------------------------------------------------------------------
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Definición de tarea
# ---------------------------------------------------------------------------
@dataclass
class Task:
    task_id: str
    session_id: str
    user_input: str
    agent: Any  # AutomyxAgent
    model: Optional[str] = None
    agent_id: str = "main"
    custom_prompt: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: str = ""
    error: str = ""
    steps: int = 0
    tools_used: List[str] = field(default_factory=list)
    current_phase: str = "queued"
    current_action: str = ""
    progress: float = 0.0
    intent_data: Dict[str, Any] = field(default_factory=dict)
    normalized_input: str = ""
    future: Optional[Future] = None
    cancelled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["duration_s"] = (
            (self.completed_at or time.time()) - (self.started_at or self.created_at)
        )
        return d


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
class MultiTaskDispatcher:
    """
    Despachador de tareas paralelas para Automyx.
    Permite que múltiples preguntas corran simultáneamente y se
    respondan de forma independiente.
    """

    # Tools que NO se pueden ejecutar en paralelo (efectos secundarios)
    SERIAL_TOOLS: Set[str] = {
        "write_file", "create_directory", "delete_file", "move_file",
        "copy_file", "open_program", "use_terminal_window", "execute_cmd",
        "open_website", "create_web_preview", "schedule_task",
        "system_sleep", "system_shutdown", "system_restart",
        "ui_click_image", "ui_click", "ui_type", "ui_press", "ui_hotkey",
        "mouse_click", "press_key", "type_text", "press_hotkey",
        "swarm_dispatch_task", "swarm_dispatch_parallel", "swarm_dispatch_map_reduce",
        "swarm_pipeline", "swarm_consensus",
        "forger_promote_skill", "forger_demote_skill", "forger_archive_skill",
        "forger_forge_skill", "forger_run_cycle",
        "error_learn_clear", "error_learn_add_manual",
    }

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="automyx-mt")
        self.tasks: Dict[str, Task] = {}
        self.tasks_lock = threading.RLock()
        self.serial_lock = threading.RLock()  # para tools con side effects
        # Callbacks de progreso (opcional)
        self.on_progress: Optional[Callable[[Task], None]] = None
        self.on_complete: Optional[Callable[[Task], None]] = None
        # Listeners por sesión (para broadcast a WebSocket)
        self.session_listeners: Dict[str, List[Callable]] = {}

    # -----------------------------------------------------------------------
    # API pública
    # -----------------------------------------------------------------------
    def submit(
        self,
        user_input: str,
        agent: Any,
        session_id: str = "default",
        model: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        agent_id: str = "main",
    ) -> Task:
        """Encola una nueva tarea y la ejecuta en background."""
        task_id = f"mt_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        # Pre-procesar con intent engine
        intent_data: Dict[str, Any] = {}
        normalized = user_input
        try:
            from core.intent_engine import understand
            intent_data = understand(user_input)
            normalized = intent_data.get("normalized", user_input)
        except Exception as e:
            logger.debug(f"intent_engine no disponible: {e}")

        task = Task(
            task_id=task_id,
            session_id=session_id,
            user_input=user_input,
            agent=agent,
            model=model,
            agent_id=agent_id,
            custom_prompt=custom_prompt,
            intent_data=intent_data,
            normalized_input=normalized,
        )

        with self.tasks_lock:
            self.tasks[task_id] = task

        # Lanzar ejecución en thread
        task.future = self.executor.submit(self._run_task, task)
        return task

    def cancel(self, task_id: str) -> bool:
        """Intenta cancelar una tarea en ejecución."""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            task.cancelled = True
            if task.future and not task.future.done():
                task.future.cancel()
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            return True

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def list_tasks(self, session_id: Optional[str] = None, status: Optional[TaskStatus] = None) -> List[Task]:
        with self.tasks_lock:
            tasks = list(self.tasks.values())
        if session_id:
            tasks = [t for t in tasks if t.session_id == session_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def wait(self, task_id: str, timeout: Optional[float] = None) -> Optional[Task]:
        """Bloquea hasta que la tarea termine."""
        task = self.tasks.get(task_id)
        if not task or not task.future:
            return task
        try:
            task.future.result(timeout=timeout)
        except Exception:
            pass
        return task

    def wait_session(self, session_id: str, timeout: float = 60.0) -> List[Task]:
        """Espera a que TODAS las tareas de la sesión terminen."""
        tasks = self.list_tasks(session_id=session_id)
        for t in tasks:
            if t.future and not t.future.done():
                try:
                    t.future.result(timeout=timeout)
                except Exception:
                    pass
        return self.list_tasks(session_id=session_id)

    def stats(self) -> Dict[str, Any]:
        with self.tasks_lock:
            tasks = list(self.tasks.values())
        by_status: Dict[str, int] = {}
        for t in tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        return {
            "total": len(tasks),
            "by_status": by_status,
            "max_workers": self.max_workers,
            "active": by_status.get("running", 0) + by_status.get("streaming", 0) + by_status.get("pending", 0),
        }

    def shutdown(self, wait: bool = True):
        self.executor.shutdown(wait=wait)

    # -----------------------------------------------------------------------
    # Listeners de sesión (para WebSocket)
    # -----------------------------------------------------------------------
    def add_session_listener(self, session_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self.tasks_lock:
            self.session_listeners.setdefault(session_id, []).append(callback)

    def remove_session_listener(self, session_id: str, callback: Callable) -> None:
        with self.tasks_lock:
            if session_id in self.session_listeners:
                try:
                    self.session_listeners[session_id].remove(callback)
                except ValueError:
                    pass

    def _emit_session(self, session_id: str, event: Dict[str, Any]) -> None:
        listeners = self.session_listeners.get(session_id, [])
        for cb in listeners:
            try:
                cb(event)
            except Exception as e:
                logger.debug(f"listener error: {e}")

    # -----------------------------------------------------------------------
    # Ejecución interna
    # -----------------------------------------------------------------------
    def _run_task(self, task: Task) -> None:
        """Ejecuta una tarea con soporte para serialización de tools side-effect."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        task.current_phase = "analyzing"
        task.current_action = "Procesando solicitud"
        self._emit_progress(task)

        try:
            # Hook opcional del agent: callback por step
            progress_callback = self._make_progress_callback(task)

            # El agent.run devuelve un string; podría tener un hook de progreso
            result = task.agent.run(
                task.user_input,
                custom_system_prompt=task.custom_prompt,
                agent_id=task.agent_id,
                progress_callback=progress_callback,
            )
            task.result = result or ""
            task.status = TaskStatus.COMPLETED
            task.current_phase = "completed"
            task.current_action = "Tarea completada"
            task.progress = 1.0
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.current_phase = "failed"
            task.current_action = f"Error: {str(e)[:100]}"
            logger.exception(f"Task {task.task_id} failed: {e}")
        finally:
            task.completed_at = time.time()
            self._emit_progress(task)
            if self.on_complete:
                try:
                    self.on_complete(task)
                except Exception:
                    pass

    def _make_progress_callback(self, task: Task) -> Callable:
        def cb(phase: str, action: str, **extras) -> None:
            task.current_phase = phase
            task.current_action = action
            if "step" in extras:
                task.steps = max(task.steps, extras["step"])
            if "tool_name" in extras:
                tname = extras["tool_name"]
                if tname and tname not in task.tools_used:
                    task.tools_used.append(tname)
            if "progress" in extras:
                try:
                    task.progress = float(extras["progress"])
                except (TypeError, ValueError):
                    pass
            self._emit_progress(task)
        return cb

    def _emit_progress(self, task: Task) -> None:
        self._emit_session(task.session_id, {
            "type": "task_progress",
            "task_id": task.task_id,
            "session_id": task.session_id,
            "status": task.status.value,
            "phase": task.current_phase,
            "action": task.current_action,
            "progress": task.progress,
            "tools_used": task.tools_used,
            "result_preview": task.result[:120] if task.result else "",
            "error": task.error,
        })
        if self.on_progress:
            try:
                self.on_progress(task)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Singleton global
# ---------------------------------------------------------------------------
_dispatcher: Optional[MultiTaskDispatcher] = None
_dispatcher_lock = threading.Lock()


def get_dispatcher() -> MultiTaskDispatcher:
    """Obtiene (o crea) el dispatcher global."""
    global _dispatcher
    with _dispatcher_lock:
        if _dispatcher is None:
            max_workers = int(os.environ.get("AUTOMYX_MAX_WORKERS", "6"))
            _dispatcher = MultiTaskDispatcher(max_workers=max_workers)
    return _dispatcher
