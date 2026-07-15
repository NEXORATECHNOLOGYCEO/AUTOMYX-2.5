"""
AUTONOMY v6.0 - Complete Autonomy System
=========================================
The most autonomous AI agent ever created.

Features:
- Master Orchestrator that decides everything automatically
- Auto-creation of agents on demand
- Auto-creation of skills on demand
- Auto-navigation of filesystem
- Self-improvement through learning
- No need for Claude Code, OpenClaw, or any other external AI
"""
from __future__ import annotations

import os
import sys
import json
import time
import uuid
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.box import ROUNDED, DOUBLE
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

try:
    from core.agent import AutomyxAgent
    from core.multi_agent import MultiAgentOrchestrator
except ImportError:
    AutomyxAgent = None
    MultiAgentOrchestrator = None


class TaskComplexity(Enum):
    """Complexity levels for tasks."""
    TRIVIAL = "trivial"           # Single tool, no planning needed
    SIMPLE = "simple"             # Few tools, basic plan
    MODERATE = "moderate"         # Multiple tools, structured plan
    COMPLEX = "complex"           # Many tools, parallel execution needed
    MASSIVE = "massive"           # Multi-agent, multi-phase


@dataclass
class TaskAnalysis:
    """Analysis of a task's requirements."""
    complexity: TaskComplexity
    needs_agents: bool
    num_agents_needed: int
    needs_skills: bool
    skills_needed: List[str]
    needs_filesystem: bool
    files_involved: List[str]
    estimated_duration: float
    reasoning: str


class AutonomyCore:
    """
    The core autonomy engine.
    
    This is the brain of AUTONOMY. It:
    - Analyzes any task and determines the best execution strategy
    - Auto-creates agents when needed
    - Auto-creates skills when needed
    - Auto-navigates the filesystem
    - Learns from every interaction
    """
    
    def __init__(self, model: Optional[str] = None, console: Optional[Console] = None):
        self.console = console or (Console() if Console else None)
        self.model = model or os.environ.get('AUTOMYX_MODEL', 'openai/gpt-oss-120b')
        self.master_agent = None
        self.created_agents: List[str] = []
        self.created_skills: List[str] = []
        self.learned_patterns: List[Dict[str, Any]] = []
        self.session_history: List[Dict[str, Any]] = []
        
    def _ensure_master_agent(self) -> Any:
        """Ensure the master agent is created with all tools."""
        if self.master_agent is None:
            if AutomyxAgent is None:
                raise ImportError("AutomyxAgent not available")
            self.master_agent = AutomyxAgent(model_name=self.model)
            try:
                from core.tool_registry import register_all_tools
                n = register_all_tools(self.master_agent)
                if self.console:
                    self.console.print(f"[dim]Master agent initialized with {n} tools[/dim]")
            except Exception as e:
                if self.console:
                    self.console.print(f"[yellow]Warning: {e}[/yellow]")
        return self.master_agent
    
    def analyze_task(self, task: str) -> TaskAnalysis:
        """
        Analyze a task and determine the best execution strategy.
        
        This uses the LLM to understand the task complexity.
        """
        analysis_prompt = f"""Analiza la siguiente tarea y determina su complejidad.

Tarea: {task}

Responde SOLO con un JSON con esta estructura:
{{
  "complexity": "trivial|simple|moderate|complex|massive",
  "needs_agents": true/false,
  "num_agents_needed": numero,
  "needs_skills": true/false,
  "skills_needed": ["skill1", "skill2"],
  "needs_filesystem": true/false,
  "files_involved": ["file1", "file2"],
  "estimated_duration": 60.0,
  "reasoning": "explicacion breve"
}}

Reglas:
- trivial: una sola herramienta
- simple: 2-3 herramientas, plan basico
- moderate: 4-10 herramientas, plan estructurado
- complex: 10+ herramientas, necesita ejecucion paralela
- massive: necesita multiples agentes especializados

JSON:"""
        
        try:
            # Llamada LLM directa y barata: sin Soul.md, sin tools, sin historial
            # (agent.run aqui quemaba ~40k tokens de system prompt solo para el JSON)
            # timeout corto SIN reintentos: si el modelo esta ocupado (np=1 en
            # ollama multimodal) caemos a heuristica en 45s, no en 92s
            from core.agent import ModelProvider
            client = ModelProvider.get_client(self.model).with_options(
                timeout=45.0, max_retries=0)
            r = client.chat.completions.create(
                model=ModelProvider.get_display_name(self.model),
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=500, temperature=0.2)
            response = r.choices[0].message.content or ""

            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return TaskAnalysis(
                    complexity=TaskComplexity(data.get('complexity', 'simple')),
                    needs_agents=data.get('needs_agents', False),
                    num_agents_needed=data.get('num_agents_needed', 1),
                    needs_skills=data.get('needs_skills', False),
                    skills_needed=data.get('skills_needed', []),
                    needs_filesystem=data.get('needs_filesystem', False),
                    files_involved=data.get('files_involved', []),
                    estimated_duration=data.get('estimated_duration', 60.0),
                    reasoning=data.get('reasoning', 'Auto-analysis')
                )
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]Auto-analysis failed: {e}, using heuristics[/yellow]")
        
        # Fallback: heuristic analysis
        return self._heuristic_analysis(task)
    
    def _heuristic_analysis(self, task: str) -> TaskAnalysis:
        """Heuristic-based task analysis as fallback."""
        task_lower = task.lower()
        word_count = len(task.split())
        
        # Determine complexity based on keywords
        massive_keywords = ['sistema completo', 'plataforma completa', 'aplicacion completa', 'proyecto completo']
        complex_keywords = ['crear una web', 'desarrollar aplicacion', 'sistema de', 'plataforma de']
        moderate_keywords = ['crear', 'desarrollar', 'implementar', 'configurar']
        
        if any(kw in task_lower for kw in massive_keywords):
            complexity = TaskComplexity.MASSIVE
            needs_agents = True
            num_agents = 4
        elif any(kw in task_lower for kw in complex_keywords):
            complexity = TaskComplexity.COMPLEX
            needs_agents = True
            num_agents = 3
        elif any(kw in task_lower for kw in moderate_keywords) and word_count > 5:
            complexity = TaskComplexity.MODERATE
            needs_agents = False
            num_agents = 1
        else:
            complexity = TaskComplexity.SIMPLE
            needs_agents = False
            num_agents = 1
        
        # Check if filesystem is needed
        filesystem_keywords = ['archivo', 'carpeta', 'crear', 'escribir', 'leer', 'descarga', 'guardar']
        needs_filesystem = any(kw in task_lower for kw in filesystem_keywords)
        
        # Check if skills might be needed
        skill_keywords = ['web', 'video', 'imagen', '3d', 'audio', 'pdf', 'ssh', 'docker']
        needs_skills = any(kw in task_lower for kw in skill_keywords)
        
        return TaskAnalysis(
            complexity=complexity,
            needs_agents=needs_agents,
            num_agents_needed=num_agents,
            needs_skills=needs_skills,
            skills_needed=[],
            needs_filesystem=needs_filesystem,
            files_involved=[],
            estimated_duration=60.0,
            reasoning="Heuristic analysis"
        )
    
    def auto_create_skill(self, skill_name: str, description: str = "", 
                          instrucciones: str = "") -> Optional[str]:
        """
        Auto-create a skill on demand.
        
        This is called when the agent needs a capability it doesn't have.
        """
        try:
            from tools.skill_tools import SkillTools
            result = SkillTools.create_skill(
                name=skill_name,
                description=description,
                instrucciones=instrucciones or f"# {skill_name}\n\nAuto-created skill by AUTONOMY."
            )
            self.created_skills.append(skill_name)
            if self.console:
                self.console.print(f"[green]Auto-created skill:[/] {skill_name}")
            return result
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Failed to create skill: {e}[/red]")
            return None
    
    def auto_create_agent(self, agent_name: str, role: str, 
                          task: str) -> Optional[Any]:
        """
        Auto-create a specialized agent for a specific task.
        """
        if AutomyxAgent is None:
            return None
        
        try:
            agent = AutomyxAgent(model_name=self.model)
            from core.tool_registry import register_all_tools
            register_all_tools(agent)
            
            self.created_agents.append(agent_name)
            if self.console:
                self.console.print(f"[green]Auto-created agent:[/] {agent_name} ({role})")
            return agent
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Failed to create agent: {e}[/red]")
            return None
    
    def auto_navigate_filesystem(self, path: str) -> Dict[str, Any]:
        """
        Auto-navigate the filesystem to understand the project structure.
        """
        try:
            path = Path(path).resolve()
            if not path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            result = {
                "path": str(path),
                "is_directory": path.is_dir(),
                "is_file": path.is_file(),
                "size": path.stat().st_size if path.is_file() else 0,
                "children": []
            }
            
            if path.is_dir():
                result["children"] = []
                for child in sorted(path.iterdir())[:50]:  # Limit to 50 items
                    result["children"].append({
                        "name": child.name,
                        "path": str(child),
                        "is_dir": child.is_dir(),
                        "size": child.stat().st_size if child.is_file() else 0
                    })
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    MAX_AGENTS = 100

    @staticmethod
    def needs_orchestrator(analysis: "TaskAnalysis") -> bool:
        """True solo si la tarea de verdad amerita agentes paralelos (2+)."""
        return bool(analysis and analysis.needs_agents
                    and analysis.num_agents_needed >= 2
                    and MultiAgentOrchestrator is not None)

    def analyze_only(self, task: str) -> Optional["TaskAnalysis"]:
        """Fase de análisis con su tabla — para correrla ANTES de abrir un Live."""
        if self.console:
            self.console.print(f"\n[bold cyan]AUTONOMY: Analizando tarea...[/bold cyan]")
            self.console.print(f"[dim]Tarea: {task[:80]}{'...' if len(task) > 80 else ''}[/dim]\n")
        analysis = self.analyze_task(task)
        analysis.num_agents_needed = max(1, min(int(analysis.num_agents_needed or 1),
                                                self.MAX_AGENTS))
        if self.console:
            self._display_analysis(analysis)
            modo = ("orquestador paralelo" if self.needs_orchestrator(analysis)
                    else "agente maestro (todas las tools)")
            self.console.print(f"\n[bold cyan]AUTONOMY: Ejecutando → {modo}[/bold cyan]")
        return analysis

    def execute_autonomously(self, task: str, agent: Any = None,
                             progress_callback: Any = None,
                             analysis: Optional["TaskAnalysis"] = None) -> Dict[str, Any]:
        """
        Execute a task completely autonomously.

        agent: agente ya vivo (el del REPL) para ejecutar con sus tools,
               historial y callbacks; si es None se usa el master agent propio.
        progress_callback: se pasa a agent.run para la UI en vivo del REPL.
        analysis: si ya se corrió analyze_only, se reutiliza (no re-analiza).

        OJO Live displays: el orquestador multi-agente abre su PROPIO rich.Live —
        el llamador debe cerrar cualquier Live activo antes si
        needs_orchestrator(analysis) es True (fix "Only one live display").
        """
        start_time = time.time()

        if analysis is None:
            analysis = self.analyze_only(task)

        result = {
            "task": task,
            "analysis": {
                "complexity": analysis.complexity.value,
                "needs_agents": analysis.needs_agents,
                "num_agents": analysis.num_agents_needed,
                "needs_filesystem": analysis.needs_filesystem
            },
            "execution": None,
            "duration": 0,
            "created_agents": [],
            "created_skills": []
        }

        try:
            if self.needs_orchestrator(analysis):
                orchestrator = MultiAgentOrchestrator(model=self.model,
                                                    max_workers=analysis.num_agents_needed)
                # run_project: carpeta única + plan de archivos con dueño por
                # agente + integrador final (antes cada agente inventaba su
                # propia carpeta y nadie ensamblaba el entregable)
                execution_result = orchestrator.run_project(
                    task, num_agents=analysis.num_agents_needed)
                result["execution"] = execution_result
            else:
                run_agent = agent if agent is not None else self._ensure_master_agent()
                execution_result = run_agent.run(task, progress_callback=progress_callback)
                result["execution"] = execution_result
        except Exception as e:
            result["execution"] = f"Error: {e}"
            if self.console:
                self.console.print(f"[red]Execution error: {e}[/red]")
        
        # Step 4: Learn from the result
        result["duration"] = time.time() - start_time
        result["created_agents"] = self.created_agents.copy()
        result["created_skills"] = self.created_skills.copy()
        
        # Store in session history
        self.session_history.append({
            "task": task,
            "complexity": analysis.complexity.value,
            "duration": result["duration"],
            "success": "Error" not in str(result["execution"])
        })
        
        return result
    
    def _display_analysis(self, analysis: TaskAnalysis):
        """Display task analysis."""
        table = Table(box=ROUNDED, border_style="blue")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Complexity", f"[bold]{analysis.complexity.value}[/bold]")
        table.add_row("Needs Agents", str(analysis.needs_agents))
        table.add_row("Num Agents", str(analysis.num_agents_needed))
        table.add_row("Needs Skills", str(analysis.needs_skills))
        if analysis.skills_needed:
            table.add_row("Skills Needed", ", ".join(analysis.skills_needed))
        table.add_row("Needs Filesystem", str(analysis.needs_filesystem))
        table.add_row("Est. Duration", f"{analysis.estimated_duration:.0f}s")
        table.add_row("Reasoning", analysis.reasoning)
        
        self.console.print(table)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get autonomy statistics."""
        return {
            "created_agents": len(self.created_agents),
            "created_skills": len(self.created_skills),
            "learned_patterns": len(self.learned_patterns),
            "session_tasks": len(self.session_history),
            "success_rate": sum(1 for h in self.session_history if h.get("success", False)) / max(len(self.session_history), 1) * 100
        }


def main():
    """Test the autonomy system."""
    console = Console() if Console else None
    autonomy = AutonomyCore(console=console)
    
    # Test task analysis
    task = "creame una pagina web profesional con edge-tts"
    result = autonomy.execute_autonomously(task)
    
    print("\n=== RESULT ===")
    print(f"Task: {result['task']}")
    print(f"Complexity: {result['analysis']['complexity']}")
    print(f"Duration: {result['duration']:.1f}s")
    print(f"Created Agents: {result['created_agents']}")
    print(f"Created Skills: {result['created_skills']}")


if __name__ == '__main__':
    main()
