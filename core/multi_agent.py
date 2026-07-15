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

# Tope duro de agentes paralelos (selector del /auto llega hasta aquí)
MAX_AGENTS = 100


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

    # ── LLM directo (sin Soul.md ni tools — solo para planificar) ─────────────
    def _llm(self, prompt: str, max_tokens: int = 900) -> str:
        from core.agent import ModelProvider
        client = ModelProvider.get_client(self.model)
        r = client.chat.completions.create(
            model=ModelProvider.get_display_name(self.model),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens, temperature=0.2, timeout=90)
        return r.choices[0].message.content or ""

    # ── Descomposición ────────────────────────────────────────────────────────
    def decompose_task(self, task: str, num_agents: int = 4) -> List[str]:
        """Usa el LLM para dividir la tarea en subtareas paralelas."""
        prompt = (
            f"Descompón en exactamente {num_agents} subtareas independientes que puedan ejecutarse "
            f"en paralelo:\n\nTarea: {task}\n\n"
            f"Responde SOLO con JSON array de {num_agents} strings cortos y concretos.\n"
            f"Ejemplo: [\"subtarea 1\", \"subtarea 2\"]"
        )
        try:
            resp = self._llm(prompt, max_tokens=min(4096, 300 + 35 * num_agents))
            import re
            m = re.search(r'\[.*?\]', resp, re.DOTALL)
            if m:
                sub = json.loads(m.group())
                if isinstance(sub, list) and len(sub) == num_agents:
                    return [str(s) for s in sub]
        except Exception:
            pass
        return [f"{task} — parte {i+1}" for i in range(num_agents)]

    # ── Plan de proyecto compartido (fix "cada agente crea su carpeta") ───────
    def plan_project(self, task: str, num_agents: int = 4) -> Optional[Dict[str, Any]]:
        """Arquitectura común ANTES de lanzar agentes: UNA carpeta, plan de
        archivos con dueño único por archivo, y notas de integración."""
        prompt = f"""Eres el arquitecto de un equipo de {num_agents} agentes que van a construir EN PARALELO un único entregable coherente.

Tarea: {task}

IMPORTANTE: si la tarea NO es construir archivos/software nuevo (p.ej. diagnosticar
o arreglar un servidor remoto, investigar un problema, monitorear, administrar
sistemas), responde SOLO: {{"es_proyecto": false}}

Si SÍ es construir algo, diseña el plan. Responde SOLO con este JSON:
{{
  "project_dir": "nombre-corto-kebab",
  "files": [{{"path": "index.html", "purpose": "que hace"}}],
  "subtasks": [{{"label": "rol-corto", "task": "instruccion concreta y completa", "files": ["archivos que ESTE agente crea"]}}],
  "integration_notes": "como se conectan los archivos (orden de script tags, objetos globales, convenciones de nombres)"
}}

Reglas ESTRICTAS:
- exactamente {num_agents} subtasks
- cada archivo tiene UN solo dueño (aparece en el "files" de UN solo subtask)
- todos los archivos viven en project_dir (subcarpetas relativas ok: css/, js/, assets/)
- las subtasks deben cubrir TODO lo necesario para que el entregable funcione al abrirlo
- si es una web/juego, index.html debe quedar funcional y enlazar el resto"""
        try:
            resp = self._llm(prompt, max_tokens=min(4096, 800 + 140 * num_agents))
            import re
            m = re.search(r'\{.*\}', resp, re.DOTALL)
            if not m:
                return None
            spec = json.loads(m.group())
            if spec.get("es_proyecto") is False:
                return {"es_proyecto": False}
            subs = spec.get("subtasks") or []
            if not spec.get("project_dir") or not subs:
                return None
            return spec
        except Exception:
            return None

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

            brief = (context or {}).get("_shared_brief")
            extra_ctx = {k: v for k, v in (context or {}).items() if k != "_shared_brief"}
            if brief:
                full_task = f"{brief}\n\nTU SUBTAREA (haz SOLO esto):\n{ag.description}"
            else:
                full_task = ag.description
            if extra_ctx:
                full_task += "\n\nContexto:\n" + "\n".join(f"  · {k}: {v}" for k, v in extra_ctx.items())

            # Acción visible en vivo: tool en curso o preview del texto del modelo
            def _progress(phase, action="", **extras):
                txt = ""
                if phase == "tool_executing":
                    tn = extras.get("tool_name") or str(action)
                    args = (extras.get("tool_args_summary") or "").replace("\n", " ")[:40]
                    txt = f"⚒ {tn}({args})" if args else f"⚒ {tn}"
                elif phase == "streaming" and str(action).strip():
                    t = str(action).replace("\n", " ").strip()
                    ji = t.find('{"')
                    if ji > 0:
                        t = t[:ji].strip()
                    elif ji == 0:
                        t = ""
                    txt = t[-80:] if t else ""
                if txt:
                    with self._lock:
                        ag.action = txt[:80]

            result = agent.run(full_task, progress_callback=_progress)
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

    # ── Proyecto coherente: plan compartido → paralelo → integración ─────────
    def run_project(self, task: str, num_agents: int = 4) -> str:
        """Flujo completo para construir UN entregable: arquitectura común
        (una carpeta, dueño único por archivo), agentes en paralelo con el
        mismo brief, y un agente integrador final que verifica y repara."""
        num_agents = max(1, min(int(num_agents), MAX_AGENTS))
        self.max_workers = max(self.max_workers, num_agents)
        if self.console:
            self.console.print(f"  [dim {_D}]Diseñando arquitectura del proyecto ({num_agents} agentes)…[/dim {_D}]")
        spec = self.plan_project(task, num_agents=num_agents)

        if spec and spec.get("es_proyecto") is False:
            # tarea OPERATIVA (diagnóstico/arreglo/investigación): sin carpeta
            # de proyecto ni integrador de archivos — agentes investigan en
            # paralelo aspectos distintos y se consolidan los hallazgos
            if self.console:
                self.console.print(f"  [dim {_D}]Tarea operativa — {num_agents} agentes investigan en paralelo (sin carpeta de proyecto)[/dim {_D}]")
            subtasks = self.decompose_task(task, num_agents=num_agents)
            plan = self.create_plan(task, subtasks)
            brief = (f"TAREA OPERATIVA EN EQUIPO: {task}\n"
                     f"Trabajas en PARALELO con otros agentes que revisan otros aspectos. "
                     f"NO crees carpetas ni archivos de proyecto. Si hay credenciales SSH "
                     f"en la tarea usa la tool ssh_exec (nunca ssh interactivo). Ejecuta, "
                     f"diagnostica y si puedes ARREGLA; termina con hallazgos concretos.")
            plan = self.execute_parallel(plan, context={"_shared_brief": brief})
            return self.aggregate_results(plan)

        if not spec:
            # sin plan estructurado: flujo clásico (mejor que fallar)
            subtasks = self.decompose_task(task, num_agents=num_agents)
            plan = self.create_plan(task, subtasks)
            plan = self.execute_parallel(plan)
            return self.aggregate_results(plan)

        project_dir = os.path.abspath(os.path.join(os.getcwd(), str(spec["project_dir"]).strip("/\\ ")))
        os.makedirs(project_dir, exist_ok=True)
        file_plan = "\n".join(f"  - {f.get('path')}: {f.get('purpose','')}"
                              for f in (spec.get("files") or []))
        notes = spec.get("integration_notes", "")

        brief = f"""PROYECTO EN EQUIPO ({num_agents} agentes en paralelo) — REGLAS OBLIGATORIAS:
- Carpeta ÚNICA del proyecto: {project_dir}
- NO crees ninguna otra carpeta de proyecto. Todos los archivos van DENTRO de esa carpeta (subcarpetas relativas del plan ok).
- Plan de archivos completo del equipo:
{file_plan}
- Crea SOLO los archivos asignados a tu subtarea; los demás los hacen otros agentes EN ESTE MISMO MOMENTO — no los toques ni los esperes, asume que existirán según el plan.
- Convenciones de integración: {notes}
- Escribe código COMPLETO y funcional (nada de TODOs ni placeholders).

Tarea global del equipo: {task}"""

        if self.console:
            self.console.print(f"  [dim {_D}]Proyecto: {project_dir}[/dim {_D}]")

        subs, labels = [], []
        for st in spec["subtasks"]:
            files = ", ".join(st.get("files") or [])
            desc = st.get("task", "")
            if files:
                desc += f"\nArchivos que TÚ creas: {files}"
            subs.append(desc)
            labels.append(str(st.get("label") or f"agent-{len(labels)+1}")[:18])

        plan = self.create_plan(task, subs, labels=labels)
        plan = self.execute_parallel(plan, context={"_shared_brief": brief})

        integration = self.integrate_project(task, project_dir, file_plan, notes)

        fails = "\n".join(f"  ✗ {a.label}: {a.error}" for a in plan.agents
                          if a.status == AgentStatus.FAILED)
        report = (
            f"# Proyecto creado: {project_dir}\n\n"
            f"**Tarea:** {task}\n"
            f"**Agentes:** {plan.n_done}/{len(plan.agents)} exitosos · {plan.elapsed:.1f}s\n"
            + (f"\n**Fallos:**\n{fails}\n" if fails else "")
            + f"\n## Integración final\n\n{integration}"
        )
        return report

    def integrate_project(self, task: str, project_dir: str,
                          file_plan: str, notes: str) -> str:
        """Agente integrador: revisa lo que dejaron los paralelos y lo hace funcionar."""
        if self.console:
            self.console.print()
            self.console.print(f"  [bold {_B}]●[/bold {_B}] [bold {_W}]Integrando y verificando el proyecto…[/bold {_W}]")
        agent = AutomyxAgent(model_name=self.model)
        try:
            from core.tool_registry import register_all_tools
            register_all_tools(agent)
        except Exception:
            pass
        itask = f"""Eres el INTEGRADOR final de un proyecto construido por varios agentes en paralelo.

Tarea original: {task}
Carpeta del proyecto: {project_dir}
Plan de archivos esperado:
{file_plan}
Convenciones: {notes}

Haz esto, en orden:
1. Lista el contenido real de {project_dir} (recursivo).
2. Compara con el plan: si falta un archivo del plan, CRÉALO completo tú mismo.
3. Lee los archivos clave y corrige inconsistencias reales: referencias rotas (script src, link href, imports, rutas), nombres que no coinciden entre archivos, código duplicado o placeholders.
4. Asegúrate de que el punto de entrada (p. ej. index.html) enlace todo y funcione al abrirlo.
5. Termina con un resumen breve: qué archivos quedaron, qué corregiste y cómo ejecutar/abrir el resultado."""
        try:
            result = agent.run(itask)
        except Exception as e:
            result = f"Integración falló: {e}"
        if self.console:
            self.console.print(f"  [bold {_G}]✓[/bold {_G}] [dim {_G}]Integración terminada[/dim {_G}]")
        return result or ""

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
