"""
AUTOMYX — Multi-Agent Parallel Execution (Claude Code Style)
=============================================================
Display estilo Claude Code:

  ⠙ agent-1  Buscando en la web: "react hooks tutorial"
  ⠹ agent-2  Leyendo archivo src/components/App.tsx
  ✓ agent-3  Completado — 3 archivos analizados (4.2s)
  ✗ agent-4  Error: timeout al conectar

Cada agente es una fila viva con spinner individual.
"""
from __future__ import annotations

import os
import sys
import json
import time
import uuid
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rich.console import Console
    from rich.live import Live
    from rich.text import Text
    from rich.panel import Panel
    from rich.table import Table
    from rich.rule import Rule
    from rich import box as _rbox
    RICH = True
except ImportError:
    RICH = False
    Console = None

try:
    from core.agent import AutomyxAgent
    from core.ui import console as shared_console
except ImportError:
    shared_console = None


# ── Paleta ────────────────────────────────────────────────────────────────────
_B  = "#00AAFF"
_G  = "#5EE6A8"
_O  = "#FF8C00"
_R  = "#FF4444"
_D  = "#4A6A8A"
_W  = "#F0F6FF"
_PU = "#A855F7"

# ── Frames del spinner (mismo que Claude Code) ─────────────────────────────────
_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class AgentStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


@dataclass
class AgentTask:
    agent_id:    str
    label:       str                    # nombre corto p.ej. "researcher-1"
    description: str                    # descripción completa de la subtarea
    status:      AgentStatus = AgentStatus.PENDING
    result:      Optional[str] = None
    error:       Optional[str] = None
    action:      str = ""               # acción actual visible en pantalla
    start_time:  Optional[float] = None
    end_time:    Optional[float] = None
    _frame_idx:  int = 0               # para animar el spinner

    @property
    def elapsed(self) -> float:
        if not self.start_time:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def tick(self):
        self._frame_idx = (self._frame_idx + 1) % len(_FRAMES)


@dataclass
class MultiAgentPlan:
    plan_id:    str
    main_task:  str
    agents:     List[AgentTask] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time:   Optional[float] = None

    @property
    def elapsed(self) -> float:
        if not self.start_time:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def n_done(self) -> int:
        return sum(1 for a in self.agents if a.status == AgentStatus.COMPLETED)

    @property
    def n_failed(self) -> int:
        return sum(1 for a in self.agents if a.status == AgentStatus.FAILED)

    @property
    def n_running(self) -> int:
        return sum(1 for a in self.agents if a.status == AgentStatus.RUNNING)


class MultiAgentOrchestrator:
    """
    Orquesta varios agentes en paralelo con display estilo Claude Code.
    """

    def __init__(self, model: Optional[str] = None, max_workers: int = 4,
                 console: Optional[Any] = None):
        self.console     = console or shared_console or (Console() if Console else None)
        self.model       = model or os.environ.get("AUTOMYX_MODEL", "openai/gpt-oss-120b")
        self.max_workers = max_workers
        self.plans: Dict[str, MultiAgentPlan] = {}
        self._lock = threading.Lock()

    # ── Descomposición ────────────────────────────────────────────────────────
    def decompose_task(self, task: str, num_agents: int = 4) -> List[str]:
        """Usa el LLM para dividir la tarea en subtareas paralelas."""
        agent = AutomyxAgent(model_name=self.model)
        try:
            from core.tool_registry import register_all_tools
            register_all_tools(agent)
        except Exception:
            pass

        prompt = (
            f"Descompón en exactamente {num_agents} subtareas independientes que puedan ejecutarse "
            f"en paralelo:\n\nTarea: {task}\n\n"
            f"Responde SOLO con JSON array de {num_agents} strings cortos y concretos.\n"
            f"Ejemplo: [\"subtarea 1\", \"subtarea 2\"]"
        )
        try:
            resp = agent.run(prompt)
            import re
            m = re.search(r'\[.*?\]', resp, re.DOTALL)
            if m:
                sub = json.loads(m.group())
                if isinstance(sub, list) and len(sub) == num_agents:
                    return [str(s) for s in sub]
        except Exception:
            pass
        return [f"{task} — parte {i+1}" for i in range(num_agents)]

    def create_plan(self, main_task: str, subtasks: List[str],
                    labels: Optional[List[str]] = None) -> MultiAgentPlan:
        plan_id = str(uuid.uuid4())[:8]
        roles = labels or [f"agent-{i+1}" for i in range(len(subtasks))]
        agents = [
            AgentTask(
                agent_id=f"agt_{i}",
                label=roles[i] if i < len(roles) else f"agent-{i+1}",
                description=sub,
            )
            for i, sub in enumerate(subtasks)
        ]
        plan = MultiAgentPlan(plan_id=plan_id, main_task=main_task, agents=agents)
        self.plans[plan_id] = plan
        return plan

    # ── Render live (Claude Code style) ───────────────────────────────────────
    def _render(self, plan: MultiAgentPlan) -> Text:
        """Construye el Text del display en tiempo real."""
        lines = Text()

        # Header
        lines.append(f"\n  Agentes paralelos", style=f"bold {_W}")
        lines.append(f"  ·  {plan.main_task[:60]}", style=f"dim {_D}")
        if len(plan.main_task) > 60:
            lines.append("…", style=f"dim {_D}")
        lines.append("\n\n")

        label_w = max((len(a.label) for a in plan.agents), default=10) + 2

        for ag in plan.agents:
            if ag.status == AgentStatus.PENDING:
                spinner = " "
                name_style  = f"dim {_D}"
                action_text = "en espera…"
                action_style = f"dim {_D}"

            elif ag.status == AgentStatus.RUNNING:
                spinner = f"[bold {_B}]{_FRAMES[ag._frame_idx]}[/bold {_B}]"
                name_style  = f"bold {_B}"
                action_text = ag.action or "procesando…"
                action_style = _W

            elif ag.status == AgentStatus.COMPLETED:
                spinner = f"[bold {_G}]✓[/bold {_G}]"
                name_style  = f"bold {_G}"
                action_text = f"completado — {ag.elapsed:.1f}s"
                action_style = f"dim {_G}"

            else:  # FAILED
                spinner = f"[bold {_R}]✗[/bold {_R}]"
                name_style  = f"bold {_R}"
                action_text = f"error: {(ag.error or '?')[:50]}"
                action_style = f"dim {_R}"

            label_padded = ag.label.ljust(label_w)
            lines.append(f"  ")
            lines.append(f"{_FRAMES[ag._frame_idx] if ag.status == AgentStatus.RUNNING else ('✓' if ag.status == AgentStatus.COMPLETED else ('✗' if ag.status == AgentStatus.FAILED else ' '))} ",
                         style=f"bold {_B if ag.status == AgentStatus.RUNNING else (_G if ag.status == AgentStatus.COMPLETED else (_R if ag.status == AgentStatus.FAILED else _D))}")
            lines.append(label_padded, style=name_style)
            lines.append(action_text, style=action_style)
            lines.append("\n")

        # Footer
        total = len(plan.agents)
        done  = plan.n_done
        lines.append(f"\n  [{done}/{total}] ", style=f"dim {_D}")
        lines.append(f"{plan.elapsed:.1f}s", style=f"dim {_D}")
        if plan.n_running:
            lines.append(f"  ·  {plan.n_running} corriendo", style=f"dim {_B}")
        lines.append("\n")
        return lines

    # ── Ejecución de un solo agente ───────────────────────────────────────────
    def _run_agent(self, ag: AgentTask, context: Dict[str, Any]) -> AgentTask:
        ag.status     = AgentStatus.RUNNING
        ag.start_time = time.time()
        ag.action     = ag.description[:60]

        try:
            agent = AutomyxAgent(model_name=self.model)
            try:
                from core.tool_registry import register_all_tools
                register_all_tools(agent)
            except Exception:
                pass

            full_task = ag.description
            if context:
                ctx_str = "\n\nContexto:\n" + "\n".join(f"  · {k}: {v}" for k, v in context.items())
                full_task += ctx_str

            # Callback para actualizar la acción visible
            def _on_token(text: str):
                if text.strip():
                    with self._lock:
                        ag.action = text.strip()[:80]

            result = agent.run(full_task)
            ag.result = result
            ag.status = AgentStatus.COMPLETED

        except Exception as e:
            ag.error  = str(e)
            ag.status = AgentStatus.FAILED

        ag.end_time = time.time()
        return ag

    # ── Ejecución paralela con display live ───────────────────────────────────
    def execute_parallel(self, plan: MultiAgentPlan,
                         context: Optional[Dict[str, Any]] = None) -> MultiAgentPlan:
        plan.start_time = time.time()
        context = context or {}

        if not RICH or not self.console:
            return self._execute_plain(plan, context)

        # Header
        self.console.print()
        self.console.print(Rule(
            f"[bold {_B}]  ● Lanzando {len(plan.agents)} agentes en paralelo  [/bold {_B}]",
            style=f"dim {_D}"
        ))
        self.console.print()

        stop_event = threading.Event()

        def _ticker():
            while not stop_event.is_set():
                with self._lock:
                    for ag in plan.agents:
                        if ag.status == AgentStatus.RUNNING:
                            ag.tick()
                time.sleep(0.1)

        ticker = threading.Thread(target=_ticker, daemon=True)
        ticker.start()

        with Live(
            self._render(plan),
            console=self.console,
            refresh_per_second=10,
            transient=False,
        ) as live:
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(plan.agents))) as ex:
                futures = {ex.submit(self._run_agent, ag, context): ag for ag in plan.agents}
                for future in as_completed(futures):
                    ag = futures[future]
                    try:
                        result_ag = future.result()
                        with self._lock:
                            for i, a in enumerate(plan.agents):
                                if a.agent_id == result_ag.agent_id:
                                    plan.agents[i] = result_ag
                    except Exception as e:
                        with self._lock:
                            ag.error  = str(e)
                            ag.status = AgentStatus.FAILED
                    live.update(self._render(plan))

        stop_event.set()
        plan.end_time = time.time()
        self._print_summary(plan)
        return plan

    def _execute_plain(self, plan: MultiAgentPlan, context: Dict) -> MultiAgentPlan:
        """Fallback sin Rich."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {ex.submit(self._run_agent, ag, context): ag for ag in plan.agents}
            for future in as_completed(futures):
                try:
                    result_ag = future.result()
                    for i, a in enumerate(plan.agents):
                        if a.agent_id == result_ag.agent_id:
                            plan.agents[i] = result_ag
                except Exception as e:
                    ag = futures[future]
                    ag.error  = str(e)
                    ag.status = AgentStatus.FAILED
        plan.end_time = time.time()
        return plan

    def _print_summary(self, plan: MultiAgentPlan):
        if not self.console:
            return
        self.console.print()
        ok   = plan.n_done
        fail = plan.n_failed
        tot  = len(plan.agents)
        if fail == 0:
            self.console.print(
                f"  [bold {_G}]✓[/bold {_G}]  {ok}/{tot} agentes completados  "
                f"[dim {_D}]·  {plan.elapsed:.1f}s total[/dim {_D}]"
            )
        else:
            self.console.print(
                f"  [bold {_O}]⚠[/bold {_O}]  {ok}/{tot} exitosos  "
                f"[bold {_R}]{fail} fallidos[/bold {_R}]  "
                f"[dim {_D}]·  {plan.elapsed:.1f}s[/dim {_D}]"
            )
        self.console.print()

    # ── Agrupación de resultados ──────────────────────────────────────────────
    def aggregate_results(self, plan: MultiAgentPlan) -> str:
        parts = []
        for ag in plan.agents:
            if ag.status == AgentStatus.COMPLETED and ag.result:
                parts.append(f"### {ag.label}: {ag.description}\n\n{ag.result}")
            elif ag.status == AgentStatus.FAILED:
                parts.append(f"### {ag.label}: {ag.description}\n\n**Error:** {ag.error}")

        return (
            f"# Reporte Multi-Agente\n\n"
            f"**Tarea:** {plan.main_task}\n"
            f"**Duración:** {plan.elapsed:.1f}s\n"
            f"**Agentes:** {len(plan.agents)} total / {plan.n_done} exitosos / {plan.n_failed} fallidos\n\n"
            f"---\n\n"
            + "\n\n---\n\n".join(parts)
        )

    def get_plan(self, plan_id: str) -> Optional[MultiAgentPlan]:
        return self.plans.get(plan_id)

    def list_plans(self) -> List[MultiAgentPlan]:
        return list(self.plans.values())


# ── Helper público para usar desde el REPL ───────────────────────────────────
def run_parallel(
    task: str,
    subtasks: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    num_agents: int = 4,
    model: Optional[str] = None,
    console: Optional[Any] = None,
) -> str:
    """
    Lanza N agentes en paralelo y retorna el reporte agregado.

    Si `subtasks` es None, el LLM descompone `task` automáticamente.
    """
    orch = MultiAgentOrchestrator(model=model, max_workers=num_agents, console=console)

    if subtasks is None:
        if console:
            console.print(f"  [dim {_D}]Descomponiendo tarea en {num_agents} subtareas…[/dim {_D}]")
        subtasks = orch.decompose_task(task, num_agents=num_agents)

    plan = orch.create_plan(task, subtasks, labels=labels)
    plan = orch.execute_parallel(plan)
    return orch.aggregate_results(plan)
