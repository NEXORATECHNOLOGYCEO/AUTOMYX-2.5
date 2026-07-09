"""
AUTOMYX REPL v6.0 - Claude Code Style Terminal Interface
========================================================
Professional terminal interface inspired by Claude Code with:
- Quiet mode by default (no noisy INFO: messages)
- Streaming output like Claude Code
- Beautiful welcome screen with glassmorphism
- Side-by-side onboarding
- Real-time activity indicators
- Task progress without clutter
"""
from __future__ import annotations

import os
import sys
import json
import time
import signal
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

# Load .env early — before any Automyx module reads os.environ
def _load_dotenv_repl():
    try:
        _env = Path(__file__).parent.parent / ".env"
        if _env.exists():
            for _line in _env.read_text(encoding="utf-8", errors="replace").splitlines():
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip()
                if _k and _k not in os.environ:
                    os.environ[_k] = _v
    except Exception:
        pass

_load_dotenv_repl()

# Suppress noisy logs BEFORE importing Automyx modules
from core import quiet as _quiet_module
_quiet_module.quiet()

# Rich imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.box import ROUNDED, DOUBLE, SIMPLE
    from rich.align import Align
    from rich.rule import Rule
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

# Automyx imports (after quiet is enabled)
try:
    from core.agent import AutomyxAgent
    from core.context import ProjectContext
    from core.permissions import PermissionManager
    from core.session import SessionManager
    from core.ui import (
        console as shared_console,
        ELECTRIC, CYAN, GLOW, WHITE, GRAY, DIM,
        OK, WARN, ERR, BLUE, NAVY, PURPLE,
        show_banner, glass_panel, section, info, ok, warn, err
    )
except ImportError as e:
    print(f"Error importing Automyx modules: {e}")
    sys.exit(1)


# ============================================================================
# AVAILABLE MODELS (curated, popular, free)
# ============================================================================
POPULAR_MODELS = {
    "NVIDIA (free)": [
        ("openai/gpt-oss-120b",              "GPT-OSS 120B  — coding, open-weights"),
        ("minimaxai/minimax-m3",             "MiniMax M3    — multimodal, ultra-fast"),
        ("minimaxai/minimax-m2.7",           "MiniMax M2.7  — balanceado"),
        ("moonshotai/kimi-k2.6",             "Kimi K2.6     — 256K contexto"),
        ("z-ai/glm-5.1",                     "GLM 5.1       — bilingüe"),
        ("meta/llama-3.3-70b-instruct",      "Llama 3.3 70B — propósito general"),
        ("mistralai/mistral-large-2-instruct","Mistral Large 2 — multilingüe"),
    ],
    "Anthropic": [
        ("claude-opus-4-5",           "Claude Opus 4.5   — el más potente"),
        ("claude-sonnet-4-5",         "Claude Sonnet 4.5 — mejor balance ★"),
        ("claude-haiku-4-5",          "Claude Haiku 4.5  — rápido y barato"),
        ("claude-3-5-sonnet-20241022","Claude 3.5 Sonnet — probado"),
        ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku  — veloz"),
        ("claude-3-opus-20240229",    "Claude 3 Opus     — máxima capacidad"),
    ],
    "OpenAI": [
        ("gpt-4o",       "GPT-4o       — multimodal ★"),
        ("gpt-4o-mini",  "GPT-4o Mini  — rápido y barato"),
        ("gpt-4.1",      "GPT-4.1      — sucesor de 4-turbo"),
        ("gpt-4.1-mini", "GPT-4.1 Mini — costo/rendimiento"),
        ("o3",           "o3           — razonamiento avanzado"),
        ("o4-mini",      "o4-mini      — razonamiento rápido"),
        ("o1-mini",      "o1-mini      — razonamiento clásico"),
    ],
    "Ollama (local)": [
        ("llama3.1:8b",     "Llama 3.1 8B  — rápido, 5GB RAM"),
        ("llama3.1:70b",    "Llama 3.1 70B — potente, 40GB RAM"),
        ("mistral:latest",  "Mistral 7B    — equilibrado"),
        ("codellama:latest","CodeLlama     — código"),
    ],
}


# ============================================================================
# BRANDING
# ============================================================================
AUTOMYX_VERSION = "2.5.0"
AUTOMYX_TAGLINE = "The Autonomous AI Agent"


# ============================================================================
# BEAUTIFUL WELCOME SCREEN
# ============================================================================
def print_welcome(console, model: str):
    """Print the AUTOMYX welcome screen like Claude Code."""
    console.clear()

    # Header bar
    header = Text()
    header.append("  AUTOMYX  ", style=f"bold {ELECTRIC}")
    header.append(f"v{AUTOMYX_VERSION}", style=WARN)
    header.append("  ", style=DIM)
    header.append(AUTOMYX_TAGLINE, style=GRAY)
    console.print(Rule(style=ELECTRIC))
    console.print(header)
    console.print(Rule(style=ELECTRIC))
    console.print()

    # Two-column layout: model + tips
    # Left column: current model + project info
    left = Text()
    left.append("\n")
    left.append("  Current Model\n", style=f"bold {CYAN}")
    left.append(f"  {model}\n", style=ELECTRIC)
    left.append("\n")
    left.append("  Project\n", style=f"bold {CYAN}")
    left.append(f"  {Path.cwd()}\n\n", style=GRAY)
    left.append("  Effort Level\n", style=f"bold {CYAN}")
    left.append("  high", style=OK)
    left.append("  (use ", style=DIM)
    left.append("/effort", style=f"bold {WHITE}")
    left.append(" to change)\n", style=DIM)
    left.append("\n")

    # Right column: tips
    right = Text()
    right.append("  Tips for getting started\n", style=f"bold {CYAN}")
    right.append("  > Just ask anything in natural language\n", style=DIM)
    right.append("  > Use ", style=DIM)
    right.append("/help", style=f"bold {WHITE}")
    right.append(" for commands\n", style=DIM)
    right.append("  > Use ", style=DIM)
    right.append("/init", style=f"bold {WHITE}")
    right.append(" to create AUTOMYX.md\n", style=DIM)
    right.append("\n")
    right.append("  Popular tasks\n", style=f"bold {CYAN}")
    right.append("  * Edit a file: ", style=DIM)
    right.append("edit app.py to add dark mode", style=WHITE)
    right.append("\n", style=DIM)
    right.append("  * Create a project: ", style=DIM)
    right.append("build me a portfolio site", style=WHITE)
    right.append("\n", style=DIM)
    right.append("  * Run a command: ", style=DIM)
    right.append("!npm install", style=WHITE)
    right.append("\n", style=DIM)
    right.append("  * Auto-mode: ", style=DIM)
    right.append("/auto create a video", style=WHITE)
    right.append("\n", style=DIM)
    right.append("\n")
    right.append("  Press ", style=DIM)
    right.append("?", style=f"bold {WHITE}")
    right.append(" for help, or start typing...", style=DIM)
    right.append("\n", style=DIM)

    # Render side-by-side
    console.print(Columns([left, right], equal=True, expand=True))
    console.print()


def print_model_badge(console, model: str):
    """Print a compact model badge in the bottom bar."""
    badge = Text()
    badge.append("  ", style=DIM)
    badge.append("●", style=OK)
    badge.append(f"  {model}", style=CYAN)
    badge.append("  ", style=DIM)
    console.print(badge)


# ============================================================================
# AUTONOMY HELPERS
# ============================================================================
BUILTIN_COMMANDS = {
    "/help":       "Mostrar ayuda",
    "/clear":      "Limpiar pantalla",
    "/history":    "Ver comandos recientes",
    "/model":      "Cambiar el modelo de IA",
    "/memory":     "Ver/gestionar memoria persistente",
    "/context":    "Ver contexto del proyecto",
    "/tools":      "Listar herramientas disponibles",
    "/skills":     "Listar habilidades disponibles",
    "/auto":       "Modo totalmente autonomo",
    "/parallel":   "Ejecucion multi-agente paralela",
    "/skill":      "Forjar nueva habilidad",
    "/design":     "Capacidades de diseno",
    "/effort":     "Nivel de esfuerzo (low/medium/high)",
    "/init":       "Crear AUTOMYX.md en este directorio",
    "/speed":      "Reporte de metricas de velocidad",
    "/cache":      "Limpiar cache de herramientas",
    "/dashboard":  "Panel de estado del sistema en tiempo real",
    "/tasks":      "Ver historial de tareas completadas",
    "/export":     "Exportar conversacion a archivo markdown",
    "/tokens":     "Tokens y costo de la sesion actual",
    "/audit":      "Ultimas acciones del audit log",
    "/workspace":  "Gestionar workspaces (list|create|switch)",
    "/scan":       "Escanear seguridad de archivo o directorio",
    "/github":     "Integracion GitHub (repos|prs|issues|diff)",
    "/rag":        "Base de conocimiento (index|search|stats|clear)",
    "/api":        "Servidor REST API local (start|stop|status)",
    "/schedule":   "Tareas programadas (list|add|remove|run)",
    "/review":     "Code review de archivo o diff",
    "/docs":       "Generar documentacion (readme|mermaid|changelog)",
    "/db":         "Agente de base de datos (connect|query|schema)",
    "/vision":     "Analizar imagen o screenshot",
    "/pair":       "Live pair agent (start|stop|status)",
    "/mcp":        "Conectar servidores MCP (connect|tools|list)",
    "/enterprise": "Gestion multi-usuario (setup|login|users)",
    "/marketplace":"Marketplace de skills (search|install|list)",
    "/onboard":    "Volver al wizard de configuracion (modelo, APIs, integraciones)",
    "/exit":       "Salir",
}


# ============================================================================
# REPL CLASS
# ============================================================================
class AutomyxREPL:
    """
    Professional, quiet REPL inspired by Claude Code.
    """

    def __init__(self, model: Optional[str] = None, verbose: bool = False):
        if verbose:
            _quiet_module.verbose()
        else:
            _quiet_module.quiet()

        self.console = shared_console or (Console() if Console else None)
        if not self.console:
            print("Error: rich library not available")
            sys.exit(1)

        self.model = model or os.environ.get('AUTOMYX_MODEL', 'openai/gpt-oss-120b')
        self.verbose = verbose
        self.agent: Optional[AutomyxAgent] = None
        self.context = ProjectContext()
        self.permissions = PermissionManager()
        self.session = SessionManager()
        self.history: List[str] = []
        self.running = False
        self.effort = "high"
        self.autonomy = None

        self._pt_session    = None
        self._cmd_completer = None
        self._init_prompt_toolkit()

        try:
            from core.memory import MemoryManager
            self.memory = MemoryManager()
        except Exception:
            self.memory = None

        self.session.load()

    def _init_prompt_toolkit(self):
        """Inicializa prompt_toolkit para autocomplete de / y historial con flechas."""
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.completion import Completer, Completion
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.styles import Style

            history_path = Path.home() / ".automyx" / "prompt_history.txt"
            history_path.parent.mkdir(parents=True, exist_ok=True)

            class _CmdCompleter(Completer):
                def __init__(self_, commands):
                    self_._cmds = list(commands.items())

                def get_completions(self_, document, complete_event):
                    text = document.text_before_cursor
                    if not text.startswith("/"):
                        return
                    for cmd, desc in self_._cmds:
                        if cmd.startswith(text):
                            yield Completion(
                                cmd,
                                start_position=-len(text),
                                display=cmd,
                                display_meta=desc,
                            )

            self._cmd_completer = _CmdCompleter(BUILTIN_COMMANDS)

            pt_style = Style.from_dict({
                "completion-menu":                        "bg:#0d1f35 #aac4e0",
                "completion-menu.completion":             "bg:#0d1f35 #8aafcc",
                "completion-menu.completion.current":     "bg:#00D4AA #000000 bold",
                "completion-menu.meta.completion":        "bg:#081525 #556677",
                "completion-menu.meta.completion.current":"bg:#cc6a00 #000000",
                "scrollbar.background":                   "bg:#0d1f35",
                "scrollbar.button":                       "bg:#1a4080",
            })

            self._pt_session = PromptSession(
                history=FileHistory(str(history_path)),
                style=pt_style,
                mouse_support=False,
            )
        except Exception:
            self._pt_session    = None
            self._cmd_completer = None

    def start(self):
        """Start the REPL loop."""
        self.running = True
        signal.signal(signal.SIGINT, self._handle_interrupt)

        # Inicializar agente y mostrar conteo de tools antes del primer prompt
        self._ensure_agent()
        self.console.print()

        while self.running:
            try:
                user_input = self._get_input()
                if not user_input:
                    continue
                    
                # Handle Autocomplete commands when user types "/"
                if user_input == "/":
                    self.console.print()
                    self.console.print("[bold #00D4AA]Comandos disponibles:[/]")
                    for cmd, desc in BUILTIN_COMMANDS.items():
                        if cmd.startswith("/"):
                            self.console.print(f"  [bold #00AAFF]{cmd:<12}[/] [dim]{desc}[/]")
                    self.console.print()
                    continue
                    
                if user_input in ('?', '/?'):
                    self._cmd_help()
                    continue
                # Soporte !comando (shell directo, como Claude Code)
                if user_input.startswith('!'):
                    self._run_shell_direct(user_input[1:].strip())
                    continue
                if user_input.startswith('/'):
                    if self._handle_command(user_input):
                        continue
                # Detección de paste largo
                user_input = self._handle_long_paste(user_input)
                if user_input is None:
                    continue
                # Regular input
                self.history.append(user_input)
                self.session.add_to_history(user_input)
                self._process_input(user_input)
            except KeyboardInterrupt:
                self.console.print()
                self.console.print(f"[{DIM}]Interrupted. Use /exit to quit.[/{DIM}]")
                continue
            except EOFError:
                self._exit()
                break

    def _get_input(self) -> str:
        """Cuadro de input con borde naranja/azul + autocomplete / en tiempo real."""
        import os as _os
        from pathlib import Path as _Path

        O  = "\033[38;2;0;212;170m"   # teal-green brand
        B  = "\033[38;2;0;170;255m"   # blue
        R  = "\033[38;2;0;212;170m"   # teal (was red — unified palette)
        D  = "\033[38;2;40;80;115m"   # dim blue-grey
        BD = "\033[1m"
        RS = "\033[0m"

        try:
            cols = _os.get_terminal_size().columns
        except Exception:
            cols = 88

        model_short = (self.model or "").split("/")[-1]
        if len(model_short) > 22:
            model_short = model_short[:20] + "..."
        dir_name = _Path.cwd().name
        if len(dir_name) > 20:
            dir_name = dir_name[:18] + "..."

        left_tag   = f" {model_short} "
        right_tag  = f" {dir_name} "
        inner      = cols - 4
        mid_dashes = max(2, inner - len(left_tag) - len(right_tag))

        top = (
            f"\n{D}╭─{RS}"
            f"{BD}{O}{left_tag}{RS}"
            f"{D}{chr(9472) * mid_dashes}{RS}"
            f"{BD}{B}{right_tag}{RS}"
            f"{D}─╮{RS}"
        )
        bottom = f"{D}╰{chr(9472) * (inner + 2)}╯{RS}"

        print(top)

        if self._pt_session is not None:
            try:
                from prompt_toolkit.formatted_text import ANSI as PT_ANSI
                pt_prompt = PT_ANSI(
                    f"{D}│{RS}  {BD}{O}>{RS}{BD}{R}>{RS}{BD}{B}>{RS}  "
                )
                user_input = self._pt_session.prompt(
                    pt_prompt,
                    completer=self._cmd_completer,
                    complete_while_typing=True,
                    enable_history_search=True,
                    reserve_space_for_menu=10,
                )
                print(bottom)
                return user_input.strip()
            except KeyboardInterrupt:
                print(bottom)
                raise
            except EOFError:
                print(bottom)
                return ""
            except Exception:
                pass

        print(f"{D}│{RS}  {BD}{O}>{RS}{BD}{R}>{RS}{BD}{B}>{RS}  ", end="", flush=True)
        try:
            user_input = input()
        except EOFError:
            user_input = ""
        print(bottom)
        return user_input.strip()

    def _handle_long_paste(self, text: str):
        """Detecta texto largo y ofrece guardarlo con Ctrl+G antes de procesar."""
        if len(text) < 400 and text.count('\n') < 6:
            return text

        lines = text.splitlines()
        preview = '\n'.join(lines[:3])
        if len(lines) > 3:
            preview += f'\n... ({len(lines)} líneas, {len(text)} caracteres)'

        O  = "#00D4AA"
        B  = "#00AAFF"
        G  = "#5EE6A8"
        DM = "#4A6A8A"
        W  = "#F0F6FF"

        from rich.panel import Panel as _Panel
        from rich import box as _rbox

        self.console.print()
        self.console.print(_Panel(
            f"[{W}]{preview}[/{W}]",
            title=f"[bold {O}]Texto largo detectado — {len(text)} caracteres[/]",
            border_style=f"{O}",
            box=_rbox.ROUNDED,
            padding=(1, 3),
        ))
        self.console.print(
            f"  [{DM}]Pega el texto de nuevo y presiona[/{DM}] "
            f"[bold {O}]Ctrl+G[/] [{DM}]para guardarlo en notas y procesarlo,[/{DM}]\n"
            f"  [{DM}]o simplemente presiona[/{DM}] [bold {B}]Enter[/] [{DM}]para enviarlo directo.[/{DM}]"
        )
        self.console.print()

        saved_path = None

        try:
            from prompt_toolkit import PromptSession as _PS
            from prompt_toolkit.formatted_text import ANSI as _ANSI
            from prompt_toolkit.key_binding import KeyBindings as _KB
            import datetime

            _kb = _KB()
            _captured = {"text": "", "save": False}

            @_kb.add("c-g")
            def _ctrl_g(event):
                _captured["save"] = True
                _captured["text"] = event.app.current_buffer.text
                event.app.exit(result=_captured["text"])

            _session = _PS(key_bindings=_kb)
            O_ansi  = "\033[38;2;255;140;0m"
            B_ansi  = "\033[38;2;0;170;255m"
            BD      = "\033[1m"
            RS      = "\033[0m"
            pt_prompt = _ANSI(f"{BD}{O_ansi}paste ❯{RS}  ")
            try:
                new_text = _session.prompt(pt_prompt, multiline=False)
                if _captured["save"] or new_text is None:
                    new_text = _captured["text"] or text
                    _captured["save"] = True
            except KeyboardInterrupt:
                self.console.print(f"  [{DM}]Cancelado.[/{DM}]")
                return None
            except Exception:
                new_text = text
                _captured["save"] = False

            if _captured["save"]:
                notes_dir = Path.home() / ".automyx" / "notes"
                notes_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                note_file = notes_dir / f"paste_{ts}.md"
                note_file.write_text(new_text or text, encoding="utf-8")
                saved_path = str(note_file)
                self.console.print(
                    f"  [{G}]✓[/{G}] [{DM}]Guardado en[/{DM}] [{B}]{note_file.name}[/{B}]"
                )

            return new_text or text

        except ImportError:
            import datetime
            raw = input(f"  paste ❯  ").strip()
            final = raw or text
            notes_dir = Path.home() / ".automyx" / "notes"
            notes_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            note_file = notes_dir / f"paste_{ts}.md"
            note_file.write_text(final, encoding="utf-8")
            self.console.print(f"  Guardado en {note_file}")
            return final

    def _handle_command(self, command: str) -> bool:
        """Handle builtin commands. Returns True if handled."""
        cmd = command.split()[0].lower()
        args = command.split()[1:] if len(command.split()) > 1 else []

        dispatch = {
            '?':          self._cmd_help,
            '/?':         self._cmd_help,
            '/help':      self._cmd_help,
            '/clear':     self._cmd_clear,
            '/history':   self._cmd_history,
            '/model':     self._cmd_model,
            '/memory':    self._cmd_memory,
            '/context':   self._cmd_context,
            '/tools':     self._cmd_tools,
            '/skills':    self._cmd_skills,
            '/auto':      self._cmd_auto,
            '/parallel':  self._cmd_parallel,
            '/skill':     self._cmd_skill,
            '/design':    self._cmd_design,
            '/effort':    self._cmd_effort,
            '/init':      self._cmd_init,
            '/speed':     self._cmd_speed,
            '/cache':     self._cmd_cache,
            '/dashboard': self._cmd_dashboard,
            '/tasks':     self._cmd_tasks,
            '/export':    self._cmd_export,
            '/tokens':    self._cmd_tokens,
            '/audit':     self._cmd_audit,
            '/workspace': self._cmd_workspace,
            '/scan':       self._cmd_scan,
            '/github':     self._cmd_github,
            '/rag':        self._cmd_rag,
            '/api':        self._cmd_api,
            '/schedule':   self._cmd_schedule,
            '/review':     self._cmd_review,
            '/docs':       self._cmd_docs,
            '/db':         self._cmd_db,
            '/vision':     self._cmd_vision,
            '/pair':       self._cmd_pair,
            '/mcp':        self._cmd_mcp,
            '/enterprise': self._cmd_enterprise,
            '/marketplace':self._cmd_marketplace,
            '/onboard':    self._cmd_onboard,
            '/exit':       self._cmd_exit,
        }

        handler = dispatch.get(cmd)
        if not handler:
            self.console.print(f"[{ERR}]Comando desconocido:[/] {cmd}")
            self.console.print(f"[{DIM}]Escribe / y Tab para ver comandos disponibles[/{DIM}]")
            return True
        try:
            handler(args)
        except Exception as e:
            self.console.print(f"[{ERR}]Error:[/] {e}")
        return True

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_help(self, args=None):
        self.console.clear()
        self.console.print(Rule(f"[bold {CYAN}]AUTOMYX v{AUTOMYX_VERSION}[/]", style=ELECTRIC))
        self.console.print()

        # Three-column help
        cmds = list(BUILTIN_COMMANDS.items())
        col_size = (len(cmds) + 2) // 3
        cols = [cmds[i:i+col_size] for i in range(0, len(cmds), col_size)]

        col_texts = []
        for col in cols:
            t = Text()
            t.append("Commands\n\n", style=f"bold {CYAN}")
            for name, desc in col:
                t.append(f"  {name:<14}", style=ELECTRIC)
                t.append(f"  {desc}\n", style=DIM)
            col_texts.append(t)
        self.console.print(Columns(col_texts, equal=True, expand=True))
        self.console.print()
        self.console.print(Rule(style=DIM))
        self.console.print(
            f"[{DIM}]Just type a task in natural language to begin.[/{DIM}]"
        )
        self.console.print()

    def _cmd_clear(self, args=None):
        self.console.clear()

    def _cmd_history(self, args=None):
        if not self.history:
            self.console.print(f"[{DIM}]Sin historial todavia[/{DIM}]")
            return
        self.console.print(f"\n[bold {CYAN}]Comandos recientes[/]\n")
        for i, cmd in enumerate(self.history[-15:], 1):
            self.console.print(f"  [{GRAY}]{i:>3}[/{GRAY}]  {cmd}")
        self.console.print()

    def _cmd_memory(self, args=None):
        """Ver y gestionar la memoria persistente de Automyx."""
        if not self.memory:
            self.console.print(f"  [{ERR}]Sistema de memoria no disponible.[/{ERR}]")
            return

        args = args or []
        subcmd = args[0].lower() if args else ""

        if subcmd == "clear":
            self.memory.clear_facts()
            self.memory.clear_history()
            if self.agent:
                self.agent.clear_memory()
            self.console.print(f"\n  [{OK}]Memoria borrada completamente.[/{OK}]\n")
            return

        if subcmd == "forget" and len(args) > 1:
            try:
                fid = int(args[1])
                msg = self.memory.forget(fid)
                self.console.print(f"\n  [{OK}]{msg}[/{OK}]\n")
            except ValueError:
                self.console.print(f"\n  [{ERR}]Uso: /memory forget <id>[/{ERR}]\n")
            return

        ORANGE = "#00D4AA"
        BLUE   = "#00AAFF"

        s = self.memory.summary()
        self.console.print()
        self.console.print(f"[bold {ORANGE}]  Memoria de Automyx[/bold {ORANGE}]")
        self.console.print(f"  [{DIM}]{s['dir']}[/{DIM}]")
        self.console.print()

        if self.memory.facts:
            self.console.print(f"  [bold {BLUE}]Facts ({len(self.memory.facts)})[/bold {BLUE}]")
            self.console.print()
            for f in self.memory.facts:
                fid  = f.get("id", "?")
                cat  = f.get("category", "general")
                fact = f.get("fact", "")
                at   = f.get("at", "")[:10]
                self.console.print(
                    f"  [{DIM}]#{fid:<3}[/{DIM}] [{ORANGE}]{cat:<12}[/{ORANGE}]  {fact}  [{DIM}]{at}[/{DIM}]"
                )
            self.console.print()
        else:
            self.console.print(f"  [{DIM}]Sin facts guardados. El agente puede usar remember_fact() para guardar.[/{DIM}]")
            self.console.print()

        if self.memory.notes:
            self.console.print(f"  [bold {BLUE}]Notas de sesion ({len(self.memory.notes)})[/bold {BLUE}]")
            for n in self.memory.notes[-5:]:
                self.console.print(f"  [{DIM}]{n.get('at','')}[/{DIM}]  {n.get('note','')[:80]}")
            self.console.print()

        self.console.print(f"  [{DIM}]Historial LLM guardado: {s['hist_msgs']} mensajes[/{DIM}]")
        self.console.print()
        self.console.print(f"  [{DIM}]Subcomandos:[/{DIM}]  "
                           f"[{BLUE}]/memory clear[/{BLUE}]  "
                           f"[{BLUE}]/memory forget <id>[/{BLUE}]")
        self.console.print()

    def _cmd_model(self, args=None):
        """Menú de selección de modelo con tabla de precios y gestión de API keys."""
        from rich.table import Table
        from rich import box as _rbox
        from pathlib import Path as _Path

        O_ = "#00D4AA"; B_ = "#00AAFF"; G_ = "#5EE6A8"
        PU_= "#A855F7"; W_ = "#F0F6FF"; DM_= "#4A6A8A"
        YL_= "#FFD700"; R_ = "#FF4444"

        try:
            from core.model_config import PROVIDERS_ORDER
        except ImportError:
            self.console.print(f"[{R_}]Error: model_config no disponible[/]")
            return

        ENV_VARS = {
            "anthropic": ("ANTHROPIC_API_KEY", "https://console.anthropic.com/settings/keys"),
            "openai":    ("OPENAI_API_KEY",    "https://platform.openai.com/api-keys"),
            "google":    ("GOOGLE_API_KEY",    "https://aistudio.google.com/app/apikey"),
            "xai":       ("XAI_API_KEY",       "https://console.x.ai/"),
            "mistral":   ("MISTRAL_API_KEY",   "https://console.mistral.ai/api-keys"),
            "deepseek":  ("DEEPSEEK_API_KEY",  "https://platform.deepseek.com/api_keys"),
            "nvidia":    ("NVIDIA_API_KEY",    "https://build.nvidia.com/"),
            "ollama":    (None,                "https://ollama.com/"),
        }

        def _has_key(provider_id: str) -> bool:
            env, _ = ENV_VARS.get(provider_id, (None, ""))
            if env is None:
                return True
            return bool(os.environ.get(env, "").strip())

        def _save_key(provider_id: str, key: str):
            env, _ = ENV_VARS.get(provider_id, (None, ""))
            if not env:
                return
            key = key.strip()
            os.environ[env] = key
            env_path = _Path(__file__).parent.parent / ".env"
            lines = []
            if env_path.exists():
                for ln in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not ln.startswith(f"{env}="):
                        lines.append(ln)
            lines.append(f"{env}={key}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        def _badge_style(badge: str) -> str:
            return {
                "FREE":  f"bold {G_}",
                "PAID":  f"bold {YL_}",
                "LOCAL": f"bold {B_}",
            }.get(badge, W_)

        def _cost_str(cin: float, cout: float) -> str:
            if cin == 0.0 and cout == 0.0:
                return f"[{G_}]GRATIS[/{G_}]"
            return f"[{YL_}]${cin:.2f}[/{YL_}] / [{R_}]${cout:.2f}[/{R_}]"

        def _test_api_key(provider_id: str, key: str):
            """Verifica la API key haciendo una llamada mínima. Retorna (ok, msg)."""
            import urllib.request as _ur, urllib.error as _ue, json as _j2
            _auth = {"Authorization": f"Bearer {key}"}
            _tests = {
                "anthropic": ("POST", "https://api.anthropic.com/v1/messages",
                    {"x-api-key": key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
                    {"model": "claude-haiku-4-5", "max_tokens": 1,
                     "messages": [{"role": "user", "content": "hi"}]}),
                "openai":   ("GET",  "https://api.openai.com/v1/models",  _auth, None),
                "google":   ("GET",  f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", {}, None),
                "xai":      ("GET",  "https://api.x.ai/v1/models",        _auth, None),
                "mistral":  ("GET",  "https://api.mistral.ai/v1/models",  _auth, None),
                "deepseek": ("GET",  "https://api.deepseek.com/v1/models", _auth, None),
                "nvidia":   ("GET",  "https://integrate.api.nvidia.com/v1/models", _auth, None),
            }
            if provider_id not in _tests:
                return True, "sin verificación"
            method, url, headers, body = _tests[provider_id]
            try:
                data = _j2.dumps(body).encode() if body else None
                req = _ur.Request(url, data=data, headers=headers, method=method)
                with _ur.urlopen(req, timeout=12) as resp:
                    return resp.status in (200, 201), f"HTTP {resp.status}"
            except _ue.HTTPError as e:
                # Anthropic 400/422 = key válida pero parámetros menores mal
                if e.code in (400, 422) and provider_id == "anthropic":
                    return True, "key válida"
                if e.code == 401:
                    return False, "key rechazada (401 Unauthorized)"
                if e.code == 403:
                    return False, "acceso denegado (403 Forbidden)"
                if e.code == 429:
                    return True, "key válida (rate limit 429)"
                return False, f"error HTTP {e.code}"
            except Exception as exc:
                return False, f"sin conexión: {str(exc)[:50]}"

        def _enter_api_key(provider_id: str) -> bool:
            """Panel bonito para ingresar y validar una API key. Retorna True si se guardó."""
            from rich.panel import Panel as _Panel
            from rich.align import Align as _Align

            env_var, key_url = ENV_VARS.get(provider_id, (None, ""))
            if not env_var:
                return True  # Ollama no necesita key

            _PNAMES = {
                "anthropic": "Anthropic / Claude", "openai": "OpenAI",
                "google": "Google Gemini",          "xai": "xAI / Grok",
                "mistral": "Mistral AI",            "deepseek": "DeepSeek",
                "nvidia": "NVIDIA NIM",
            }
            _PREFIXES = {
                "anthropic": ("sk-ant-", "Las keys de Anthropic empiezan con  sk-ant-"),
                "openai":    ("sk-",     "Las keys de OpenAI empiezan con  sk-"),
                "google":    ("AIza",    "Las keys de Google empiezan con  AIza"),
                "xai":       ("xai-",   "Las keys de xAI empiezan con  xai-"),
                "mistral":   ("",        ""),
                "deepseek":  ("sk-",    "Las keys de DeepSeek empiezan con  sk-"),
                "nvidia":    ("nvapi-", "Las keys de NVIDIA empiezan con  nvapi-"),
            }
            pname  = _PNAMES.get(provider_id, provider_id.title())
            prefix, prefix_hint = _PREFIXES.get(provider_id, ("", ""))

            self.console.print()
            self.console.print(_Panel(
                f"[bold {W_}]{pname}[/bold {W_}]\n\n"
                f"[{DM_}]Obtén tu API key en:[/{DM_}]\n"
                f"[bold {B_}]{key_url}[/bold {B_}]"
                + (f"\n\n[{DM_}]{prefix_hint}[/{DM_}]" if prefix_hint else ""),
                title=f"[bold {O_}]  API KEY — {pname.upper()}  [/bold {O_}]",
                border_style=O_,
                padding=(1, 4),
                expand=False,
            ))

            for attempt in range(3):
                self.console.print()
                try:
                    raw = Prompt.ask(
                        f"  [{O_}]▸ Pega tu key[/{O_}]  [{DM_}](Enter para cancelar)[/{DM_}]",
                        password=True, default=""
                    )
                except (KeyboardInterrupt, EOFError):
                    break
                raw = raw.strip()
                if not raw:
                    break

                # Validación de formato
                if prefix and not raw.startswith(prefix):
                    self.console.print(_Panel(
                        f"[bold {YL_}]Formato incorrecto[/bold {YL_}]\n"
                        f"[{DM_}]{prefix_hint}[/{DM_}]\n"
                        f"[{DM_}]Tu key empieza con:[/{DM_}] [{R_}]{raw[:10]}…[/{R_}]",
                        border_style=YL_,
                        padding=(0, 4),
                        expand=False,
                    ))
                    continue

                # Preview enmascarada
                masked = raw[:10] + "···" + raw[-4:] if len(raw) > 14 else raw[:6] + "···"
                self.console.print(f"  [{DM_}]Key recibida:[/{DM_}]  [{W_}]{masked}[/{W_}]")

                # Test en vivo con spinner
                test_ok = False; test_msg = ""
                with self.console.status(
                    f"  [{DM_}]Verificando con {pname}...[/{DM_}]",
                    spinner="dots2", spinner_style=O_
                ):
                    import time as _t2; _t2.sleep(0.3)
                    test_ok, test_msg = _test_api_key(provider_id, raw)

                if test_ok:
                    _save_key(provider_id, raw)
                    self.console.print(_Panel(
                        f"[bold {G_}]  KEY VÁLIDA Y GUARDADA  [/bold {G_}]\n\n"
                        f"[{DM_}]{masked}[/{DM_}]\n\n"
                        f"[{G_}]{pname} está listo para usar.[/{G_}]",
                        border_style=G_,
                        padding=(1, 4),
                        expand=False,
                    ))
                    import time as _t2; _t2.sleep(0.8)
                    return True
                else:
                    intentos_left = 2 - attempt
                    self.console.print(_Panel(
                        f"[bold {R_}]  KEY INVÁLIDA  [/bold {R_}]\n\n"
                        f"[{DM_}]{test_msg}[/{DM_}]\n\n"
                        + (f"[{YL_}]Intentos restantes: {intentos_left}[/{YL_}]"
                           if intentos_left > 0 else f"[{R_}]Sin más intentos.[/{R_}]"),
                        border_style=R_,
                        padding=(1, 4),
                        expand=False,
                    ))
                    if intentos_left == 0:
                        break

            return False

        while True:
            self.console.clear()

            # ── Banner ──
            self.console.print()
            self.console.print(
                f"  [bold {O_}]▸ SELECCIÓN DE MODELO[/bold {O_}]"
                f"  [dim {DM_}]precio = USD / 1M tokens  (entrada / salida)[/dim {DM_}]"
            )
            self.console.print(Rule(style=DM_))
            self.console.print()

            all_entries = []
            section_map = {}
            global_idx  = 1

            for provider_name, provider_id, models_dict, label in PROVIDERS_ORDER:
                has_k  = _has_key(provider_id)
                k_icon = f"[{G_}]●[/{G_}]" if has_k else f"[{R_}]○[/{R_}]"
                env_var, url = ENV_VARS.get(provider_id, (None, ""))

                # Cabecera de sección
                self.console.print(
                    f"  {k_icon} [bold {W_}]{provider_name}[/bold {W_}]"
                    f"  [dim {DM_}]{label}[/dim {DM_}]"
                )
                if not has_k and env_var:
                    self.console.print(
                        f"    [dim {DM_}]→ Necesita API key  ({url})[/dim {DM_}]"
                    )

                # Tabla de modelos
                tbl = Table(
                    show_header=True, box=_rbox.SIMPLE_HEAD,
                    header_style=f"dim {DM_}",
                    border_style=DM_, padding=(0, 1),
                )
                tbl.add_column("#",       style=DM_,             width=4,  justify="right")
                tbl.add_column("Modelo",  style=f"bold {W_}",    min_width=32)
                tbl.add_column("Ctx",     style=DM_,             width=6,  justify="right")
                tbl.add_column("Visión",  style=DM_,             width=6,  justify="center")
                tbl.add_column("Entrada", style=YL_,             width=10, justify="right")
                tbl.add_column("Salida",  style=R_,              width=10, justify="right")
                tbl.add_column("Info",    style=f"dim {DM_}",    min_width=28)

                section_start = global_idx
                for model_id, cfg in models_dict.items():
                    is_current = (model_id == self.model)
                    badge = cfg.get("badge", "")
                    cin   = cfg.get("cost_in",  0.0)
                    cout  = cfg.get("cost_out", 0.0)
                    ctx_k = cfg.get("ctx_k", 0)
                    vis   = "✓" if cfg.get("vision") else "·"
                    # Indicador de thinking/reasoning mode
                    think_tag = " [THINK]" if cfg.get("thinking") else ""

                    num_str = f"[bold {O_}]{global_idx}[/bold {O_}]" if is_current else str(global_idx)
                    mdl_str = (f"[bold {O_}]▶ {model_id}[/bold {O_}]"
                               if is_current else f"[{W_}]{model_id}[/{W_}]")
                    ctx_str = f"{ctx_k}K"
                    cin_str = f"GRATIS" if cin == 0.0 else f"${cin:.2f}"
                    cout_str= f"GRATIS" if cout == 0.0 else f"${cout:.2f}"
                    info    = cfg.get("description", "") + think_tag

                    tbl.add_row(num_str, mdl_str, ctx_str, vis, cin_str, cout_str, info)
                    all_entries.append((model_id, provider_id))
                    section_map[global_idx] = (model_id, provider_id)
                    global_idx += 1

                self.console.print(tbl)

                # Opción de configurar key si falta
                if not has_k and env_var:
                    self.console.print(
                        f"    [dim]→ escribe [{YL_}]k{provider_id[0]}[/{YL_}] para ingresar la API key[/dim]"
                    )
                self.console.print()

            # Leyenda
            self.console.print(
                f"  [dim {DM_}]●=key configurada  ○=key faltante"
                f"  ▶=modelo actual  Ctx=contexto  Visión=✓/·[/dim {DM_}]"
            )
            self.console.print(
                f"  [dim {DM_}]Número = seleccionar  ·  "
                f"[{YL_}]ka[/{YL_}]=Anthropic  "
                f"[{YL_}]ko[/{YL_}]=OpenAI  "
                f"[{YL_}]kg[/{YL_}]=Google  "
                f"[{YL_}]kx[/{YL_}]=xAI  "
                f"[{YL_}]km[/{YL_}]=Mistral  "
                f"[{YL_}]kd[/{YL_}]=DeepSeek  "
                f"[{YL_}]kn[/{YL_}]=NVIDIA  "
                f"· 0=cancelar[/dim {DM_}]"
            )
            self.console.print()

            try:
                choice = Prompt.ask(f"  [{O_}]▸ Selección[/{O_}]", default="0")
            except (KeyboardInterrupt, EOFError):
                break

            choice = choice.strip().lower()

            # ── Gestión de API keys ──
            if choice in ("ka", "kanthropic"):
                choice = "ka"
            key_map = {
                "ka": "anthropic", "ko": "openai", "kg": "google",
                "kx": "xai",       "km": "mistral", "kd": "deepseek",
                "kn": "nvidia",
            }
            if choice in key_map:
                pid = key_map[choice]
                _enter_api_key(pid)
                continue

            # ── Cancelar ──
            if choice == "0" or choice == "":
                break

            # ── Modelo personalizado ──
            if choice == "c" or choice == "custom":
                try:
                    custom = Prompt.ask(f"  [{O_}]Nombre del modelo[/{O_}]")
                except (KeyboardInterrupt, EOFError):
                    continue
                if custom.strip():
                    self.model = custom.strip()
                    self._apply_model_change()
                break

            # ── Selección numérica ──
            try:
                num = int(choice)
            except ValueError:
                self.console.print(f"  [{R_}]Opción inválida — escribe un número o 0 para salir[/{R_}]")
                import time as _t; _t.sleep(1.2)
                continue

            if num not in section_map:
                self.console.print(f"  [{R_}]Número fuera de rango[/{R_}]")
                import time as _t; _t.sleep(1.0)
                continue

            selected_model, selected_provider = section_map[num]

            # Si el proveedor necesita key y no la tiene, pedirla ahora
            if not _has_key(selected_provider):
                env_var, _ = ENV_VARS.get(selected_provider, (None, ""))
                if env_var:
                    saved = _enter_api_key(selected_provider)
                    if not saved:
                        self.console.print(
                            f"  [{R_}]Sin key válida — elige un modelo FREE o Ollama[/{R_}]"
                        )
                        import time as _t; _t.sleep(1.2)
                        continue

            self.model = selected_model
            self._apply_model_change()
            break

    def _apply_model_change(self):
        """Aplica el cambio de modelo al agente activo."""
        O_ = "#00D4AA"; G_ = "#5EE6A8"
        self.agent    = None
        self.autonomy = None
        self._ensure_agent()
        self.console.print(
            f"\n  [{G_}]✓[/{G_}] Modelo activo: [bold {O_}]{self.model}[/bold {O_}]\n"
        )
        # Persistir en .env
        try:
            from pathlib import Path as _P
            env_path = _P(__file__).parent.parent / ".env"
            lines = []
            if env_path.exists():
                for ln in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not ln.startswith("AUTOMYX_MODEL="):
                        lines.append(ln)
            lines.append(f"AUTOMYX_MODEL={self.model}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    def _cmd_context(self, args=None):
        """Show current project context."""
        self.console.print(f"\n[bold {CYAN}]Project Context[/]\n")
        self.console.print(f"  [{GRAY}]Directory[/{GRAY}]  {Path.cwd()}")
        self.console.print(f"  [{GRAY}]Type[/{GRAY}]       {self.context.project_type or 'unknown'}")
        if self.context.has_git:
            self.console.print(f"  [{GRAY}]Branch[/{GRAY}]     {self.context.git_branch}")
        if self.context.tools:
            self.console.print(f"  [{GRAY}]Tools[/{GRAY}]      {', '.join(self.context.tools[:5])}")
        self.console.print()

    def _cmd_tools(self, args=None):
        """List tool count."""
        self._ensure_agent()
        n = len(self.agent.tools) if self.agent else 0
        self.console.print(f"\n  [{CYAN}]{n}[/{CYAN}] tools available")
        self.console.print()

    def _cmd_skills(self, args=None):
        """List skill count."""
        self._ensure_agent()
        n = len(self.agent.skills) if self.agent else 0
        self.console.print(f"\n  [{CYAN}]{n}[/{CYAN}] skills loaded")
        self.console.print()

    def _cmd_effort(self, args=None):
        if not args:
            self.console.print(f"  Current effort: [{CYAN}]{self.effort}[/{CYAN}]")
            self.console.print(f"  [{DIM}]Usage: /effort low|medium|high[/{DIM}]")
            return
        level = args[0].lower()
        if level in ['low', 'medium', 'high']:
            self.effort = level
            self.console.print(f"[{OK}][OK][/] Effort: [bold {CYAN}]{level}[/bold {CYAN}]")
        else:
            self.console.print(f"[{ERR}]Invalid effort level. Use low, medium, or high.[/]")

    def _cmd_init(self, args=None):
        """Create AUTOMYX.md."""
        content = """# AUTOMYX Project Instructions

## Project Overview
Describe your project here.

## Code Style
- Follow language-specific best practices
- Use clear, descriptive names
- Keep functions small and focused

## Testing
- Run tests before committing
- Add tests for new features

## Common Commands
- `npm run dev` - Start dev server
- `npm run build` - Build for production
- `npm test` - Run tests
"""
        try:
            Path("AUTOMYX.md").write_text(content, encoding="utf-8")
            self.console.print(f"[{OK}][OK][/] Created [bold {CYAN}]AUTOMYX.md[/bold {CYAN}]")
        except Exception as e:
            self.console.print(f"[{ERR}]Failed: {e}[/]")

    def _cmd_speed(self, args=None):
        """Show speed metrics report."""
        try:
            from core.speed import print_speed_report
            self.console.print()
            self.console.print(f"[bold {CYAN}]Speed Metrics[/]")
            self.console.print()
            self.console.print(print_speed_report())
            self.console.print()
        except Exception as e:
            self.console.print(f"[{ERR}]Error: {e}[/]")

    def _cmd_cache(self, args=None):
        """Clear the tool result cache."""
        try:
            from core.speed import clear_tool_cache
            clear_tool_cache()
            self.console.print(f"[{OK}][OK][/] Tool cache cleared")
        except Exception as e:
            self.console.print(f"[{ERR}]Error: {e}[/]")

    def _cmd_dashboard(self, args=None):
        """Panel de estado del sistema en tiempo real."""
        ORANGE = "#00D4AA"
        BLUE   = "#00AAFF"
        GREEN  = "#5EE6A8"
        DIM_   = "#5A7090"
        WHITE_ = "#F0F6FF"

        self.console.print()
        self.console.print(Rule(f"[bold {ORANGE}]* AUTOMYX DASHBOARD[/bold {ORANGE}]", style=BLUE))
        self.console.print()

        tbl = Table(box=DOUBLE, border_style=BLUE, show_header=False, padding=(0, 2))
        tbl.add_column(style=f"bold {ORANGE}", no_wrap=True)
        tbl.add_column(style=WHITE_)

        # Modelo
        model_short = self.model.split("/")[-1] if self.model and "/" in self.model else (self.model or "—")
        tbl.add_row("Modelo", model_short)

        # Directorio
        cwd = str(Path.cwd())
        if len(cwd) > 48: cwd = "…" + cwd[-46:]
        tbl.add_row("Directorio", cwd)

        # Esfuerzo
        tbl.add_row("Effort", getattr(self, "effort", "medium"))

        # Tools
        n_tools = len(self.agent.tools) if self.agent else 0
        tbl.add_row("Herramientas", str(n_tools))

        # Skills
        n_skills = len(self.agent.skills) if self.agent else 0
        tbl.add_row("Skills cargadas", str(n_skills))

        # Memoria
        if self.memory:
            try:
                s = self.memory.summary()
                tbl.add_row("Memoria — facts", str(s.get("facts", 0)))
                tbl.add_row("Memoria — tareas", str(s.get("tasks", 0)))
                tbl.add_row("Memoria — historial", f"{s.get('hist_msgs', 0)} msgs")
                tbl.add_row("Memoria dir", s.get("dir", "—"))
            except Exception:
                tbl.add_row("Memoria", "no disponible")
        else:
            tbl.add_row("Memoria", "no inicializada")

        try:
            from core.workspace import get_workspace_manager
            _wm = get_workspace_manager()
            tbl.add_row("Workspace", _wm.current_name)
            tbl.add_row("Workspace dir", _wm.current_config.get("directory", "?")[:48])
        except Exception:
            pass

        try:
            from core.token_tracker import get_tracker
            _sess = get_tracker().get_session_stats()
            tbl.add_row("Tokens sesión", f"{_sess.get('total_tokens', 0):,}")
            tbl.add_row("Costo sesión", f"${_sess.get('cost_usd', 0.0):.4f} USD")
        except Exception:
            pass

        hist_len = len(self.agent.history) if self.agent else 0
        tbl.add_row("Historial sesión", f"{hist_len} msgs")

        self.console.print(tbl)

        # Últimas 3 tareas
        if self.memory:
            try:
                recent = self.memory.get_recent_tasks(3)
                if recent:
                    self.console.print()
                    self.console.print(f"  [bold {BLUE}]Últimas tareas:[/bold {BLUE}]")
                    for t in reversed(recent):
                        skill_tag = f"  [dim]skill→ {t['skill']}[/dim]" if t.get("skill") else ""
                        self.console.print(
                            f"  [{DIM_}]{t['at']}[/{DIM_}]  "
                            f"[{WHITE_}]{t['task'][:60]}[/{WHITE_}]"
                            f"  [dim]{t['tools']} tools[/dim]{skill_tag}"
                        )
            except Exception:
                pass

        self.console.print()
        self.console.print(Rule(style=BLUE))
        self.console.print()

    def _cmd_tasks(self, args=None):
        """Ver historial de tareas completadas."""
        ORANGE = "#00D4AA"
        BLUE   = "#00AAFF"
        GREEN  = "#5EE6A8"
        DIM_   = "#5A7090"
        WHITE_ = "#F0F6FF"

        if not self.memory:
            self.console.print(f"  [{ERR}]Memoria no disponible[/{ERR}]")
            return

        try:
            n = int(args[0]) if args else 15
        except Exception:
            n = 15

        try:
            tasks = self.memory.get_recent_tasks(n)
        except Exception as e:
            self.console.print(f"  [{ERR}]Error: {e}[/{ERR}]")
            return

        if not tasks:
            self.console.print(f"  [{DIM_}]Sin tareas registradas.[/{DIM_}]")
            return

        self.console.print()
        tbl = Table(box=ROUNDED, border_style=BLUE, show_header=True, header_style=f"bold {ORANGE}")
        tbl.add_column("Fecha",   style=DIM_,   no_wrap=True, width=16)
        tbl.add_column("Tarea",   style=WHITE_,  max_width=52)
        tbl.add_column("Tools",   style=f"bold {BLUE}", justify="right", width=6)
        tbl.add_column("Skill",   style=GREEN,   max_width=22)

        for t in reversed(tasks):
            tbl.add_row(
                t.get("at", ""),
                t.get("task", "")[:50],
                str(t.get("tools", 0)),
                t.get("skill") or "—",
            )

        self.console.print(tbl)
        self.console.print()

    def _cmd_export(self, args=None):
        """Exportar conversación a archivo markdown."""
        ORANGE = "#00D4AA"
        GREEN  = "#5EE6A8"

        if not self.agent or not self.agent.history:
            self.console.print(f"  [dim]Sin conversación activa para exportar.[/dim]")
            return

        filename = args[0] if args else f"automyx_export_{int(time.time())}.md"
        if not filename.endswith(".md"):
            filename += ".md"

        try:
            from datetime import datetime as _dt
            lines = [f"# Automyx Conversación — {_dt.now().strftime('%Y-%m-%d %H:%M')}\n\n"]
            for msg in self.agent.history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "system":
                    continue
                if isinstance(content, list):
                    content = " ".join(str(c) for c in content)
                label = "**Usuario**" if role == "user" else "**Automyx**"
                lines.append(f"### {label}\n\n{str(content).strip()}\n\n---\n\n")

            Path(filename).write_text("".join(lines), encoding="utf-8")
            self.console.print(f"  [{GREEN}]Exportado →[/{GREEN}] [bold]{filename}[/bold]  ({len(lines)//4} msgs)")
        except Exception as e:
            self.console.print(f"  [{ERR}]Error al exportar: {e}[/{ERR}]")
        self.console.print()

    def _cmd_design(self, args=None):
        """Show design capabilities."""
        self.console.clear()
        self.console.print(Rule(f"[bold {CYAN}]AUTOMYX Design Suite[/]", style=ELECTRIC))
        self.console.print()

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style=CYAN, no_wrap=True)
        grid.add_column(style=WHITE)

        rows = [
            ("UI/UX", "Create stunning user interfaces"),
            ("Graphics", "Logos, banners, illustrations"),
            ("Web", "Modern, responsive websites"),
            ("3D", "Blender-powered 3D scenes"),
            ("Video", "Professional video editing"),
            ("Brand", "Identity and visual systems"),
            ("Photo", "15+ photo editing tools"),
            ("Audio", "Mastering, TTS, voice cloning"),
        ]
        for cat, desc in rows:
            grid.add_row(f"  {cat}", desc)
        self.console.print(Panel(grid, border_style=ELECTRIC, box=ROUNDED, padding=(1, 2)))
        self.console.print()

    def _cmd_auto(self, args=None):
        if not args:
            self.console.print(f"  [{DIM}]Usage: /auto <task>[/{DIM}]")
            return
        task = ' '.join(args)
        self._process_input(task, use_autonomy=True)

    def _cmd_parallel(self, args=None):
        if not args:
            self.console.print(
                f"  [dim]Uso: /parallel <tarea> [--agents N][/dim]\n"
                f"  [dim]Ej:  /parallel investiga las mejores librerías de Python para ML --agents 4[/dim]"
            )
            return
        num_agents = 4
        clean_args = []
        i = 0
        while i < len(args):
            if args[i] in ('--agents', '-n') and i + 1 < len(args):
                try:
                    num_agents = max(2, min(8, int(args[i + 1])))
                    i += 2
                    continue
                except ValueError:
                    pass
            clean_args.append(args[i])
            i += 1
        task = ' '.join(clean_args)
        try:
            from core.multi_agent import run_parallel
            from rich.markdown import Markdown
            report = run_parallel(
                task=task,
                num_agents=num_agents,
                model=self.model,
                console=self.console,
            )
            self.console.print()
            self.console.print(Panel(
                Markdown(report),
                title=f"[bold #00D4AA]Resultado multi-agente[/]",
                border_style="#00AAFF",
                box=ROUNDED,
                padding=(1, 2),
            ))
        except Exception as e:
            self.console.print(f"[{ERR}]Error: {e}[/]")

    def _cmd_skill(self, args=None):
        if not args:
            self.console.print(f"  [{DIM}]Usage: /skill <task>[/{DIM}]")
            return
        task = ' '.join(args)
        try:
            from core.auto_skill import AutoSkillCreator
            creator = AutoSkillCreator(model=self.model, console=self.console)
            skill_name = creator.auto_create_for_task(task)
            if skill_name:
                self.console.print(f"[{OK}][OK][/] Skill created: [bold {CYAN}]{skill_name}[/bold {CYAN}]")
            else:
                self.console.print(f"[{WARN}]Could not auto-detect skill type. Try a more specific task.[/]")
        except Exception as e:
            self.console.print(f"[{ERR}]Error: {e}[/]")

    def _cmd_tokens(self, args=None):
        ORANGE = "#00D4AA"
        BLUE   = "#00AAFF"
        GREEN  = "#5EE6A8"
        DIM_   = "#5A7090"
        try:
            from core.token_tracker import get_tracker
            tracker = get_tracker()
        except Exception as e:
            self.console.print(f"  [{ERR}]Token tracker no disponible: {e}[/{ERR}]")
            return

        sess = tracker.get_session_stats()
        hist = tracker.get_all_time_stats()

        self.console.print()
        self.console.print(Rule(f"[bold {ORANGE}]Tokens & Costo[/bold {ORANGE}]", style=BLUE))
        self.console.print()

        tbl = Table(box=ROUNDED, border_style=BLUE, show_header=False, padding=(0, 2))
        tbl.add_column(style=f"bold {ORANGE}", no_wrap=True)
        tbl.add_column(style=f"#F0F6FF")

        tbl.add_row("Modelo", sess.get("model", "—"))
        tbl.add_row("Calls esta sesión", str(sess.get("calls", 0)))
        tbl.add_row("Tokens entrada", f"{sess.get('total_input', 0):,}")
        tbl.add_row("Tokens salida", f"{sess.get('total_output', 0):,}")
        tbl.add_row("Total tokens", f"{sess.get('total_tokens', 0):,}")
        tbl.add_row("Costo sesión (USD)", f"${sess.get('cost_usd', 0.0):.6f}")
        self.console.print(tbl)

        if hist.get("sessions", 0):
            self.console.print()
            self.console.print(f"  [bold {BLUE}]Histórico acumulado[/bold {BLUE}]")
            self.console.print(f"  [{DIM_}]Sesiones totales:[/{DIM_}]  {hist.get('sessions', 0)}")
            self.console.print(f"  [{DIM_}]Tokens totales:  [{DIM_}]  {hist.get('total_input', 0) + hist.get('total_output', 0):,}")
            self.console.print(f"  [{DIM_}]Costo total:     [{DIM_}]  ${hist.get('total_cost_usd', 0.0):.4f} USD")

        self.console.print()

    def _cmd_audit(self, args=None):
        ORANGE = "#00D4AA"
        BLUE   = "#00AAFF"
        GREEN  = "#5EE6A8"
        RED_   = "#FF4444"
        DIM_   = "#5A7090"
        WHITE_ = "#F0F6FF"

        try:
            from core.audit import get_audit
            audit = get_audit()
        except Exception as e:
            self.console.print(f"  [{ERR}]Audit log no disponible: {e}[/{ERR}]")
            return

        try:
            n = int(args[0]) if args else 20
        except Exception:
            n = 20

        entries = audit.get_recent(n=n)
        if not entries:
            self.console.print(f"\n  [{DIM_}]Sin entradas en el audit log aún.[/{DIM_}]\n")
            return

        stats = audit.get_stats()
        self.console.print()
        self.console.print(Rule(f"[bold {ORANGE}]Audit Log[/bold {ORANGE}]", style=BLUE))
        self.console.print(
            f"  [{DIM_}]Total acciones: {stats['total_actions']} | "
            f"Éxito: {stats['success_rate']*100:.1f}% | "
            f"Sesiones hoy: {stats['sessions_today']}[/{DIM_}]"
        )
        self.console.print()

        tbl = Table(box=ROUNDED, border_style=BLUE, show_header=True, header_style=f"bold {ORANGE}")
        tbl.add_column("Hora",       style=DIM_,   no_wrap=True, width=8)
        tbl.add_column("Acción",     style=f"bold {BLUE}", max_width=22)
        tbl.add_column("OK",         justify="center", width=4)
        tbl.add_column("ms",         justify="right", width=6, style=DIM_)
        tbl.add_column("Preview",    style=WHITE_, max_width=40)

        for e in reversed(entries):
            ts    = e.get("ts", "")[-8:]
            act   = e.get("action", "?")
            ok    = e.get("result_ok", True)
            dur   = str(e.get("duration_ms", ""))
            prev  = str(e.get("result_preview", ""))[:38]
            ok_s  = f"[{GREEN}]✓[/{GREEN}]" if ok else f"[{RED_}]✗[/{RED_}]"
            tbl.add_row(ts, act, ok_s, dur, prev)

        self.console.print(tbl)

        if stats.get("top_tools"):
            self.console.print()
            self.console.print(f"  [bold {BLUE}]Top herramientas[/bold {BLUE}]")
            for t in stats["top_tools"]:
                self.console.print(f"  [{DIM_}]{t['count']:>4}×[/{DIM_}]  {t['tool']}")

        self.console.print()
        self.console.print(
            f"  [{DIM_}]/audit <N>  para ver las últimas N entradas[/{DIM_}]"
        )
        self.console.print()

    def _cmd_workspace(self, args=None):
        ORANGE = "#00D4AA"
        BLUE   = "#00AAFF"
        GREEN  = "#5EE6A8"
        DIM_   = "#5A7090"
        WHITE_ = "#F0F6FF"

        try:
            from core.workspace import get_workspace_manager
            wm = get_workspace_manager()
        except Exception as e:
            self.console.print(f"  [{ERR}]Workspace manager no disponible: {e}[/{ERR}]")
            return

        subcmd = (args[0].lower() if args else "list")

        if subcmd == "list" or not subcmd:
            workspaces = wm.list_all()
            self.console.print()
            self.console.print(Rule(f"[bold {ORANGE}]Workspaces[/bold {ORANGE}]", style=BLUE))
            self.console.print()
            tbl = Table(box=ROUNDED, border_style=BLUE, show_header=True, header_style=f"bold {ORANGE}")
            tbl.add_column("Nombre",      style=f"bold {BLUE}", no_wrap=True)
            tbl.add_column("Directorio",  style=DIM_,   max_width=40)
            tbl.add_column("Modelo",      style=WHITE_,  width=18)
            tbl.add_column("Facts",       justify="right", width=6, style=DIM_)
            tbl.add_column("Tareas",      justify="right", width=7, style=DIM_)
            for ws in workspaces:
                marker = " ●" if ws.get("name") == wm.current_name else ""
                tbl.add_row(
                    ws.get("name", "?") + marker,
                    ws.get("directory", "?"),
                    ws.get("model", "default"),
                    str(ws.get("_stats", {}).get("facts", 0)),
                    str(ws.get("_stats", {}).get("tasks", 0)),
                )
            self.console.print(tbl)
            self.console.print(
                f"\n  [{DIM_}]Actual: [/{DIM_}][bold {ORANGE}]{wm.current_name}[/bold {ORANGE}]  "
                f"[{DIM_}]— /workspace create <nombre> | /workspace switch <nombre>[/{DIM_}]\n"
            )

        elif subcmd == "create":
            name = args[1] if len(args) > 1 else None
            if not name:
                self.console.print(f"  [{ERR}]Uso: /workspace create <nombre>[/{ERR}]")
                return
            directory = args[2] if len(args) > 2 else None
            try:
                cfg = wm.create(name, directory=directory)
                self.console.print(
                    f"\n  [{GREEN}]Workspace '[bold]{name}[/bold]' creado.[/{GREEN}]  "
                    f"[{DIM_}]Dir: {cfg.get('directory')}[/{DIM_}]\n"
                )
            except Exception as e:
                self.console.print(f"  [{ERR}]Error: {e}[/{ERR}]")

        elif subcmd == "switch":
            name = args[1] if len(args) > 1 else None
            if not name:
                self.console.print(f"  [{ERR}]Uso: /workspace switch <nombre>[/{ERR}]")
                return
            try:
                cfg = wm.switch(name)
                self.console.print(
                    f"\n  [{GREEN}]Workspace activo: [bold]{name}[/bold][/{GREEN}]  "
                    f"[{DIM_}]{cfg.get('directory')}[/{DIM_}]\n"
                )
                if self.agent:
                    prev_hist = wm.load_current_state()
                    if prev_hist:
                        self.agent.load_conversation_history(prev_hist)
                        self.console.print(
                            f"  [{DIM_}]* {len(prev_hist)} mensajes restaurados del workspace[/{DIM_}]"
                        )
            except FileNotFoundError:
                self.console.print(
                    f"  [{ERR}]Workspace '{name}' no existe. Usa /workspace create {name}[/{ERR}]"
                )
            except Exception as e:
                self.console.print(f"  [{ERR}]Error: {e}[/{ERR}]")

        else:
            self.console.print(
                f"  [{ERR}]Subcomando desconocido: {subcmd}. Usa list | create | switch[/{ERR}]"
            )

    def _cmd_scan(self, args=None):
        ORANGE = "#00D4AA"
        BLUE   = "#00AAFF"
        GREEN  = "#5EE6A8"
        RED_   = "#FF4444"
        YELLOW = "#FFD700"
        DIM_   = "#5A7090"

        try:
            from core.security_scanner import get_security_scanner
            scanner = get_security_scanner()
        except Exception as e:
            self.console.print(f"  [{ERR}]Security scanner no disponible: {e}[/{ERR}]")
            return

        target = args[0] if args else str(Path.cwd())

        self.console.print()
        self.console.print(Rule(f"[bold {ORANGE}]Security Scan[/bold {ORANGE}]", style=BLUE))
        self.console.print(f"  [{DIM_}]Escaneando: {target}[/{DIM_}]")
        self.console.print()

        try:
            p = Path(target)
            if p.is_file():
                findings = scanner.scan_file(str(p))
            else:
                findings = scanner.scan_directory(str(p))
        except Exception as e:
            self.console.print(f"  [{ERR}]Error al escanear: {e}[/{ERR}]")
            return

        risk = scanner.get_risk_level(findings)
        risk_color = {
            "CRITICAL": RED_,
            "HIGH":     RED_,
            "MEDIUM":   YELLOW,
            "LOW":      BLUE,
            "CLEAN":    GREEN,
        }.get(risk, BLUE)

        self.console.print(f"  Nivel de riesgo: [bold {risk_color}]{risk}[/bold {risk_color}]")
        self.console.print(f"  Hallazgos: [{ORANGE}]{len(findings)}[/{ORANGE}]")
        self.console.print()

        if findings:
            from collections import Counter as _Counter
            by_sev: dict = {}
            for f in findings:
                by_sev.setdefault(f["severity"], []).append(f)

            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                items = by_sev.get(sev, [])
                if not items:
                    continue
                s_color = RED_ if sev in ("CRITICAL", "HIGH") else (YELLOW if sev == "MEDIUM" else BLUE)
                self.console.print(f"  [bold {s_color}]{sev}[/bold {s_color}] ({len(items)})")
                for item in items[:8]:
                    fname = Path(item.get("file", "?")).name
                    self.console.print(
                        f"    [{DIM_}]L{item['line_number']:<4}[/{DIM_}]  "
                        f"[{ORANGE}]{item['rule']}[/{ORANGE}]  "
                        f"[{DIM_}]{fname}[/{DIM_}]"
                    )
                    self.console.print(
                        f"         [{DIM_}]{item['line_content'].strip()[:70]}[/{DIM_}]"
                    )
                if len(items) > 8:
                    self.console.print(f"    [{DIM_}]... y {len(items)-8} más[/{DIM_}]")
                self.console.print()
        else:
            self.console.print(f"  [{GREEN}]Sin problemas detectados.[/{GREEN}]\n")

        self.console.print(
            f"  [{DIM_}]Uso: /scan [ruta_archivo_o_directorio][/{DIM_}]\n"
        )

    # ── GitHub ─────────────────────────────────────────────────────────────
    def _cmd_github(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "help"
        try:
            from core.github_agent import get_github
            gh = get_github()
        except Exception as e:
            self.console.print(f"  [{ERR}]GitHub no disponible: {e}[/{ERR}]")
            return
        self.console.print()
        if sub == "repos":
            repos = gh.list_repos()
            for r in repos[:15]:
                self.console.print(f"  [{BLUE}]{r.get('full_name','')}[/{BLUE}]  [{DIM_}]{r.get('description','')[:60]}[/{DIM_}]")
        elif sub == "prs" and len(args) >= 2:
            prs = gh.list_prs(args[1])
            for p in prs:
                self.console.print(f"  [{ORANGE}]#{p['number']}[/{ORANGE}]  {p['title'][:60]}  [{DIM_}]{p['state']}[/{DIM_}]")
        elif sub == "issues" and len(args) >= 2:
            issues = gh.list_issues(args[1])
            for i in issues[:10]:
                self.console.print(f"  [{GREEN}]#{i['number']}[/{GREEN}]  {i['title'][:60]}")
        elif sub == "diff" and len(args) >= 3:
            diff = gh.get_pr_diff(args[1], int(args[2]))
            self.console.print(Syntax(diff[:3000], "diff", theme="monokai"))
        elif sub == "token" and len(args) >= 2:
            gh.set_token(args[1])
            self.console.print(f"  [{GREEN}]Token guardado.[/{GREEN}]")
        else:
            self.console.print(f"  [{DIM_}]Uso: /github repos | prs <owner/repo> | issues <owner/repo> | diff <owner/repo> <pr#> | token <TOKEN>[/{DIM_}]")
        self.console.print()

    # ── RAG ────────────────────────────────────────────────────────────────
    def _cmd_rag(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "stats"
        try:
            from core.rag import get_rag
            rag = get_rag()
        except Exception as e:
            self.console.print(f"  [{ERR}]RAG no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "index":
            path = args[1] if len(args) > 1 else "."
            self.console.print(f"  [{BLUE}]Indexando {path}...[/{BLUE}]")
            rag.index_directory(path)
            rag.save_index()
            s = rag.get_stats()
            self.console.print(f"  [{GREEN}]Indexado:[/{GREEN}] {s['total_files']} archivos, {s['total_chunks']} chunks")
        elif sub == "search" and len(args) > 1:
            q = " ".join(args[1:])
            results = rag.search(q, k=5)
            for r in results:
                self.console.print(f"  [{ORANGE}]{r['path']}:{r.get('line_start',0)}[/{ORANGE}]  score={r['score']:.3f}")
                self.console.print(f"    [{DIM_}]{r['content'][:120].strip()}[/{DIM_}]")
                self.console.print()
        elif sub == "clear":
            rag.clear_index()
            self.console.print(f"  [{GREEN}]Índice RAG limpiado.[/{GREEN}]")
        else:
            s = rag.get_stats()
            self.console.print(f"  Chunks: [{BLUE}]{s.get('total_chunks',0)}[/{BLUE}]  Archivos: {s.get('total_files',0)}  Última indexación: [{DIM_}]{s.get('last_indexed','nunca')}[/{DIM_}]")
            self.console.print(f"  [{DIM_}]Uso: /rag index [ruta] | search <query> | clear | stats[/{DIM_}]")
        self.console.print()

    # ── API ─────────────────────────────────────────────────────────────────
    def _cmd_api(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "status"
        try:
            from core.api_server import get_api_server
            srv = get_api_server(agent_getter=lambda: self.agent)
        except Exception as e:
            self.console.print(f"  [{ERR}]API server no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "start":
            port = int(args[1]) if len(args) > 1 else 7799
            srv.port = port
            srv.start(background=True)
            self.console.print(f"  [{GREEN}]API iniciada en {srv.get_url()}[/{GREEN}]")
        elif sub == "stop":
            srv.stop()
            self.console.print(f"  [{ORANGE}]API detenida.[/{ORANGE}]")
        else:
            running = srv.is_running
            status_color = GREEN if running else DIM_
            self.console.print(f"  Estado: [{status_color}]{'activa' if running else 'inactiva'}[/{status_color}]")
            if running:
                self.console.print(f"  URL: [{BLUE}]{srv.get_url()}[/{BLUE}]")
            self.console.print(f"  [{DIM_}]Uso: /api start [puerto] | /api stop | /api status[/{DIM_}]")
        self.console.print()

    # ── Scheduler ──────────────────────────────────────────────────────────
    def _cmd_schedule(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "list"
        try:
            from core.scheduler import get_scheduler
            sch = get_scheduler(agent_runner=lambda t, w: (self._ensure_agent(), self.agent.run(t)) and "ok")
            if not sch._running:
                sch.start_background()
        except Exception as e:
            self.console.print(f"  [{ERR}]Scheduler no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "list":
            schedules = sch.list_all()
            if not schedules:
                self.console.print(f"  [{DIM_}]Sin tareas programadas. Usa /schedule add \"cron\" \"tarea\"[/{DIM_}]")
            else:
                tbl = Table(box=ROUNDED, border_style=BLUE, show_header=True, header_style=f"bold {ORANGE}")
                tbl.add_column("ID", style=DIM_, width=10); tbl.add_column("Cron", style=BLUE, width=14)
                tbl.add_column("Tarea", style="#F0F6FF", max_width=40); tbl.add_column("Estado", width=10)
                for s in schedules:
                    tbl.add_row(s['id'][:8], s['cron'], s['task'][:38], GREEN+"✓" if s['enabled'] else DIM_+"⏸")
                self.console.print(tbl)
        elif sub == "add" and len(args) >= 3:
            sid = sch.add(args[1], " ".join(args[2:]))
            self.console.print(f"  [{GREEN}]Tarea programada. ID: {sid[:8]}[/{GREEN}]")
        elif sub == "remove" and len(args) >= 2:
            sch.remove(args[1])
            self.console.print(f"  [{GREEN}]Tarea eliminada.[/{GREEN}]")
        elif sub == "run" and len(args) >= 2:
            sch.run_now(args[1])
            self.console.print(f"  [{BLUE}]Ejecutando en background...[/{BLUE}]")
        else:
            self.console.print(f"  [{DIM_}]Uso: /schedule list | add \"0 9 * * 1\" \"tarea\" | remove <id> | run <id>[/{DIM_}]")
        self.console.print()

    # ── Code Review ────────────────────────────────────────────────────────
    def _cmd_review(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        if not args:
            self.console.print(f"  [{DIM_}]Uso: /review <archivo_o_diff>[/{DIM_}]"); return
        self._ensure_agent()
        try:
            from core.code_review import get_code_reviewer
            def _llm(messages):
                self.agent.history.append({"role": "user", "content": messages[-1]["content"]})
                return self.agent.run(messages[-1]["content"])
            reviewer = get_code_reviewer(_llm)
        except Exception as e:
            self.console.print(f"  [{ERR}]Code review no disponible: {e}[/{ERR}]"); return
        path = " ".join(args)
        self.console.print(f"\n  [{BLUE}]Analizando {path}...[/{BLUE}]\n")
        try:
            result = reviewer.review_file(path)
            self.console.print(Markdown(result.formatted))
        except Exception as e:
            self.console.print(f"  [{ERR}]Error: {e}[/{ERR}]")
        self.console.print()

    # ── Auto-docs ──────────────────────────────────────────────────────────
    def _cmd_docs(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "help"
        self._ensure_agent()
        try:
            from core.auto_docs import AutoDocGenerator
            def _llm(msgs): return self.agent.run(msgs[-1]["content"])
            gen = AutoDocGenerator(_llm)
        except Exception as e:
            self.console.print(f"  [{ERR}]Auto-docs no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "readme":
            path = args[1] if len(args) > 1 else "."
            self.console.print(f"  [{BLUE}]Generando README para {path}...[/{BLUE}]")
            content = gen.generate_readme(path)
            out = Path("README.md"); out.write_text(content, encoding="utf-8")
            self.console.print(f"  [{GREEN}]README.md generado ({len(content)} chars)[/{GREEN}]")
        elif sub == "mermaid":
            path = args[1] if len(args) > 1 else "."
            diagram = gen.generate_mermaid_diagram(path)
            self.console.print(Syntax(diagram, "markdown", theme="monokai"))
        elif sub == "changelog":
            import subprocess
            git_log = subprocess.run(["git", "log", "--oneline", "-50"], capture_output=True, text=True).stdout
            content = gen.generate_changelog(git_log)
            Path("CHANGELOG.md").write_text(content, encoding="utf-8")
            self.console.print(f"  [{GREEN}]CHANGELOG.md generado.[/{GREEN}]")
        elif sub == "docstrings" and len(args) > 1:
            content = gen.generate_docstrings(args[1])
            self.console.print(Syntax(content[:2000], "python", theme="monokai"))
        else:
            self.console.print(f"  [{DIM_}]Uso: /docs readme [dir] | mermaid [dir] | changelog | docstrings <archivo.py>[/{DIM_}]")
        self.console.print()

    # ── Database Agent ─────────────────────────────────────────────────────
    def _cmd_db(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "help"
        try:
            from core.database_agent import get_db_agent
            db = get_db_agent()
        except Exception as e:
            self.console.print(f"  [{ERR}]DB agent no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "connect" and len(args) > 1:
            db.connect(args[1])
            self.console.print(f"  [{GREEN}]Conectado: {db.connection_info}[/{GREEN}]")
        elif sub == "schema":
            schema = db.get_schema()
            for tbl in schema:
                self.console.print(f"  [{ORANGE}]{tbl['table']}[/{ORANGE}]")
                for col in tbl.get('columns', []):
                    self.console.print(f"    [{DIM_}]{col['name']}  {col['type']}[/{DIM_}]")
        elif sub == "query" and len(args) > 1:
            sql = " ".join(args[1:])
            result = db.execute_query(sql)
            if result.get("rows"):
                tbl = Table(box=SIMPLE, show_header=True, header_style=f"bold {BLUE}")
                for col in result["columns"]: tbl.add_column(col)
                for row in result["rows"][:20]: tbl.add_row(*[str(v) for v in row])
                self.console.print(tbl)
                self.console.print(f"  [{DIM_}]{result['row_count']} filas  {result['duration_ms']}ms[/{DIM_}]")
        elif sub == "ask" and len(args) > 1:
            self._ensure_agent()
            def _llm(msgs): return self.agent.run(msgs[-1]["content"])
            q = " ".join(args[1:])
            result = db.natural_language_query(q, _llm)
            self.console.print(Syntax(result.get("sql",""), "sql", theme="monokai"))
            if result.get("rows"):
                tbl = Table(box=SIMPLE, show_header=True, header_style=f"bold {BLUE}")
                for col in result.get("columns",[]): tbl.add_column(col)
                for row in result.get("rows",[])[:15]: tbl.add_row(*[str(v) for v in row])
                self.console.print(tbl)
        else:
            self.console.print(f"  [{DIM_}]Uso: /db connect <url> | schema | query <SQL> | ask <pregunta en lenguaje natural>[/{DIM_}]")
        self.console.print()

    # ── Vision Agent ───────────────────────────────────────────────────────
    def _cmd_vision(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        self._ensure_agent()
        try:
            from core.vision_agent import get_vision_agent
            def _llm(msgs): return self.agent.run(msgs[-1]["content"])
            va = get_vision_agent(_llm)
        except Exception as e:
            self.console.print(f"  [{ERR}]Vision agent no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if not args:
            self.console.print(f"  [{BLUE}]Tomando screenshot y analizando...[/{BLUE}]")
            result = va.take_and_analyze()
            self.console.print(Markdown(str(result)))
        elif len(args) == 1 and Path(args[0]).exists():
            info = va.get_image_info(args[0])
            self.console.print(f"  [{ORANGE}]{args[0]}[/{ORANGE}]  {info.get('width')}x{info.get('height')}  {info.get('format')}  {info.get('size_kb',0):.1f}KB")
            result = va.analyze_screenshot(args[0])
            self.console.print(Markdown(str(result)))
        elif len(args) >= 2 and args[0] == "compare":
            result = va.compare_images(args[1], args[2] if len(args)>2 else args[1])
            self.console.print(f"  Similitud: [{GREEN}]{result.get('similarity_pct',0):.1f}%[/{GREEN}]")
            self.console.print(f"  [{DIM_}]{result.get('summary','')}[/{DIM_}]")
        else:
            self.console.print(f"  [{DIM_}]Uso: /vision | /vision <imagen.png> | /vision compare <img1> <img2>[/{DIM_}]")
        self.console.print()

    # ── Pair Agent ─────────────────────────────────────────────────────────
    def _cmd_pair(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "status"
        self._ensure_agent()
        try:
            from core.pair_agent import get_pair_agent
            def _llm(msgs): return self.agent.run(msgs[-1]["content"])
            def _notify(suggestion, file):
                self.console.print(f"\n  [{ORANGE}]* Pair:[/{ORANGE}] [{DIM_}]{file}[/{DIM_}]")
                self.console.print(f"  {suggestion[:200]}\n")
            pa = get_pair_agent(_llm, callback=_notify)
        except Exception as e:
            self.console.print(f"  [{ERR}]Pair agent no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "start":
            directory = args[1] if len(args) > 1 else "."
            pa.start_watching(directory)
            self.console.print(f"  [{GREEN}]Pair agent activo en {directory}[/{GREEN}]")
        elif sub == "stop":
            pa.stop_watching()
            self.console.print(f"  [{ORANGE}]Pair agent detenido.[/{ORANGE}]")
        elif sub == "sensitivity" and len(args) > 1:
            pa.set_sensitivity(args[1])
            self.console.print(f"  [{GREEN}]Sensibilidad: {args[1]}[/{GREEN}]")
        else:
            watching = pa.is_watching
            color = GREEN if watching else DIM_
            self.console.print(f"  Estado: [{color}]{'activo' if watching else 'inactivo'}[/{color}]")
            history = pa.get_history()
            if history:
                self.console.print(f"  Sugerencias dadas: [{BLUE}]{len(history)}[/{BLUE}]")
            self.console.print(f"  [{DIM_}]Uso: /pair start [dir] | stop | sensitivity low|medium|high[/{DIM_}]")
        self.console.print()

    # ── MCP ────────────────────────────────────────────────────────────────
    def _cmd_mcp(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "list"
        try:
            from core.mcp_client import get_mcp_client
            mcp = get_mcp_client()
        except Exception as e:
            self.console.print(f"  [{ERR}]MCP no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "connect" and len(args) >= 2:
            if args[1].startswith("http"):
                mcp.connect_http(args[1])
            else:
                mcp.connect_stdio(args[1], args[2:])
            self.console.print(f"  [{GREEN}]Servidor MCP conectado.[/{GREEN}]")
            if self.agent:
                tools = mcp.get_all_tools_as_automyx()
                for name, fn in tools.items():
                    self.agent.register_tool(name, fn)
                self.console.print(f"  [{BLUE}]{len(tools)} herramientas MCP registradas.[/{BLUE}]")
        elif sub == "tools":
            server_id = args[1] if len(args) > 1 else None
            tools = mcp.list_tools(server_id)
            for t in tools:
                self.console.print(f"  [{ORANGE}]{t.get('name','')}[/{ORANGE}]  [{DIM_}]{t.get('description','')[:60]}[/{DIM_}]")
        else:
            servers = mcp.list_servers()
            if servers:
                for s in servers:
                    self.console.print(f"  [{BLUE}]{s}[/{BLUE}]")
            else:
                self.console.print(f"  [{DIM_}]Sin servidores MCP conectados.[/{DIM_}]")
            self.console.print(f"  [{DIM_}]Uso: /mcp connect <comando|url> | tools [server] | list[/{DIM_}]")
        self.console.print()

    # ── Enterprise ─────────────────────────────────────────────────────────
    def _cmd_enterprise(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "status"
        try:
            from core.enterprise import get_enterprise
            em = get_enterprise()
        except Exception as e:
            self.console.print(f"  [{ERR}]Enterprise no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "setup" and len(args) >= 4:
            em.setup(args[1], args[2], args[3])
            self.console.print(f"  [{GREEN}]Modo enterprise activado. Org: {args[1]}[/{GREEN}]")
        elif sub == "login" and len(args) >= 3:
            result = em.authenticate(args[1], args[2])
            if result.get("ok"):
                self.console.print(f"  [{GREEN}]Sesión iniciada. Rol: {result['role']}[/{GREEN}]")
            else:
                self.console.print(f"  [{ERR}]{result.get('error','Auth fallida')}[/{ERR}]")
        elif sub == "users":
            users = em.list_users()
            for u in users:
                self.console.print(f"  [{BLUE}]{u['username']}[/{BLUE}]  [{DIM_}]{u['role']}  activo={u.get('active',True)}[/{DIM_}]")
        elif sub == "adduser" and len(args) >= 4:
            em.create_user(args[1], args[2], args[3])
            self.console.print(f"  [{GREEN}]Usuario {args[1]} creado con rol {args[3]}[/{GREEN}]")
        elif sub == "history":
            for entry in em.get_team_history(10):
                self.console.print(f"  [{DIM_}]{entry.get('at','')}[/{DIM_}]  [{ORANGE}]{entry.get('user','')}[/{ORANGE}]  {str(entry.get('task',''))[:50]}")
        else:
            enabled = em.is_enabled
            self.console.print(f"  Enterprise: [{GREEN if enabled else DIM_}]{'activo' if enabled else 'inactivo'}[/{GREEN if enabled else DIM_}]")
            self.console.print(f"  [{DIM_}]Uso: /enterprise setup <org> <admin> <pass> | login <user> <pass> | users | adduser <u> <p> <rol> | history[/{DIM_}]")
        self.console.print()

    # ── Marketplace ────────────────────────────────────────────────────────
    def _cmd_marketplace(self, args=None):
        ORANGE = "#00D4AA"; BLUE = "#00AAFF"; GREEN = "#5EE6A8"; DIM_ = "#5A7090"
        sub = args[0].lower() if args else "list"
        try:
            skills_dir = Path(__file__).parent.parent / "skills"
            from core.skill_marketplace import get_marketplace
            mp = get_marketplace(str(skills_dir))
        except Exception as e:
            self.console.print(f"  [{ERR}]Marketplace no disponible: {e}[/{ERR}]"); return
        self.console.print()
        if sub == "search" and len(args) > 1:
            q = " ".join(args[1:])
            results = mp.search(q)
            for r in results[:10]:
                self.console.print(f"  [{ORANGE}]{r.get('name','')}[/{ORANGE}]  [{DIM_}]{r.get('description','')[:60]}[/{DIM_}]")
        elif sub == "install" and len(args) > 1:
            ok = mp.install(args[1])
            self.console.print(f"  [{GREEN if ok else ERR}]{'Skill instalada: '+args[1] if ok else 'Error instalando '+args[1]}[/{GREEN if ok else ERR}]")
        elif sub == "uninstall" and len(args) > 1:
            mp.uninstall(args[1])
            self.console.print(f"  [{GREEN}]Skill {args[1]} eliminada.[/{GREEN}]")
        elif sub == "update":
            mp.update_all()
            self.console.print(f"  [{GREEN}]Skills actualizadas.[/{GREEN}]")
        elif sub == "refresh":
            mp.refresh_cache()
            self.console.print(f"  [{GREEN}]Cache del marketplace actualizado.[/{GREEN}]")
        else:
            installed = mp.list_installed()
            if installed:
                tbl = Table(box=SIMPLE, show_header=True, header_style=f"bold {ORANGE}")
                tbl.add_column("Skill", style=BLUE); tbl.add_column("Descripción", style=DIM_, max_width=50)
                for s in installed:
                    tbl.add_row(s.get("name",""), s.get("description","")[:48])
                self.console.print(tbl)
            else:
                self.console.print(f"  [{DIM_}]Sin skills instaladas.[/{DIM_}]")
            self.console.print(f"  [{DIM_}]Uso: /marketplace search <q> | install <nombre> | uninstall <nombre> | update | refresh[/{DIM_}]")
        self.console.print()

    def _cmd_onboard(self, args=None):
        try:
            from core.onboard_pro_v5 import run_onboarding
            run_onboarding()
            new_model = os.environ.get("AUTOMYX_MODEL", "").strip()
            if new_model and new_model != self.model:
                self.model = new_model
                self.console.print(f"\n  [{OK}]✓[/{OK}] Modelo actualizado a [{WARN}]{new_model}[/]")
                if self.agent:
                    try:
                        self.agent.update_model(new_model)
                    except Exception:
                        self.agent = None
            self.console.print(f"  [{DIM}]Configura tus APIs en /onboard cuando quieras.[/{DIM}]\n")
        except KeyboardInterrupt:
            self.console.print(f"\n  [{DIM}]Onboard cancelado.[/{DIM}]\n")
        except Exception as e:
            self.console.print(f"  [{ERR}]Error en onboard: {e}[/{ERR}]")

    def _cmd_exit(self, args=None):
        self._exit()

    # ------------------------------------------------------------------
    # Agent execution
    # ------------------------------------------------------------------
    def _register_core_tools(self):
        """Registra herramientas esenciales en Python puro — siempre disponibles."""
        import os, subprocess, shutil, urllib.parse, urllib.request, json as _json

        existing = set(self.agent.tools.keys())

        def _read_file(file_path: str) -> str:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            except Exception as e:
                return f"ERROR leyendo {file_path}: {e}"

        def _write_file(file_path: str, content: str = "") -> dict:
            try:
                parent = os.path.dirname(os.path.abspath(file_path))
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
                return {"ok": True, "path": file_path, "bytes": len(str(content))}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _list_directory(path: str = ".") -> list:
            try:
                items = []
                for name in sorted(os.listdir(path)):
                    fp = os.path.join(path, name)
                    items.append({
                        "name": name,
                        "type": "directory" if os.path.isdir(fp) else "file",
                        "size": os.path.getsize(fp) if os.path.isfile(fp) else 0,
                    })
                return items
            except Exception as e:
                return [{"error": str(e)}]

        def _execute_cmd(command: str, background: bool = False) -> dict:
            try:
                if background:
                    subprocess.Popen(command, shell=True)
                    return {"ok": True, "output": f"Proceso iniciado en background: {command}"}
                r = subprocess.run(
                    command, shell=True, capture_output=True, text=True,
                    timeout=120, encoding='utf-8', errors='replace'
                )
                out = (r.stdout or "") + (r.stderr or "")
                return {"ok": r.returncode == 0, "output": out[:4000], "returncode": r.returncode}
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": "Comando agotó el tiempo (120s)"}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _create_directory(dir_path: str) -> dict:
            try:
                os.makedirs(dir_path, exist_ok=True)
                return {"ok": True, "path": dir_path}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _delete_file(path: str) -> dict:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                return {"ok": True, "deleted": path}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _copy_file(source: str, destination: str) -> dict:
            try:
                shutil.copy2(source, destination)
                return {"ok": True, "copied": f"{source} → {destination}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _move_file(source: str, destination: str) -> dict:
            try:
                shutil.move(source, destination)
                return {"ok": True, "moved": f"{source} → {destination}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _web_search(query: str) -> list:
            try:
                encoded = urllib.parse.quote(query)
                url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
                req = urllib.request.Request(url, headers={"User-Agent": "Automyx/2.5"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = _json.loads(r.read().decode('utf-8'))
                results = []
                if data.get("AbstractText"):
                    results.append({"title": data.get("Heading", query), "snippet": data["AbstractText"][:500], "url": data.get("AbstractURL", "")})
                for t in data.get("RelatedTopics", [])[:6]:
                    if isinstance(t, dict) and t.get("Text"):
                        results.append({"title": t.get("Text", "")[:80], "snippet": t.get("Text", ""), "url": t.get("FirstURL", "")})
                return results or [{"title": "Sin resultados", "snippet": f"No se encontraron resultados para: {query}"}]
            except Exception as e:
                return [{"error": str(e), "query": query}]

        def _open_program(program_name: str = "", executable: str = "") -> dict:
            name = executable or program_name
            try:
                subprocess.Popen(name, shell=True)
                return {"ok": True, "launched": name}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _open_website(url: str) -> dict:
            try:
                import webbrowser
                webbrowser.open(url)
                return {"ok": True, "url": url}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _screenshot() -> dict:
            try:
                import mss, os
                from datetime import datetime
                with mss.mss() as sct:
                    path = os.path.join(os.path.expanduser("~"), "Downloads",
                                        f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    sct.shot(output=path)
                return {"ok": True, "path": path}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _remember_fact(fact: str = "", category: str = "general") -> dict:
            try:
                from core.memory import MemoryManager
                mm = MemoryManager()
                msg = mm.remember(fact, category)
                return {"ok": True, "message": msg}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _scan_security(path: str = ".") -> dict:
            try:
                from core.security_scanner import get_security_scanner
                sc = get_security_scanner()
                p = Path(path)
                findings = sc.scan_file(str(p)) if p.is_file() else sc.scan_directory(str(p))
                return {
                    "ok": True,
                    "risk_level": sc.get_risk_level(findings),
                    "findings_count": len(findings),
                    "report": sc.generate_report(findings),
                }
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _github_list_repos(user: str = "") -> dict:
            try:
                from core.github_agent import get_github
                gh = get_github()
                return {"ok": True, "repos": gh.list_repos(user=user or None)}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _github_list_prs(repo: str, state: str = "open") -> dict:
            try:
                from core.github_agent import get_github
                return {"ok": True, "prs": get_github().list_prs(repo, state=state)}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _github_get_pr_diff(repo: str, pr_number: int) -> dict:
            try:
                from core.github_agent import get_github
                diff = get_github().get_pr_diff(repo, int(pr_number))
                return {"ok": True, "diff": diff[:8000]}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _github_create_issue(repo: str, title: str, body: str = "", labels: str = "") -> dict:
            try:
                from core.github_agent import get_github
                lbs = [l.strip() for l in labels.split(",") if l.strip()] if labels else None
                return {"ok": True, **get_github().create_issue(repo, title, body, labels=lbs)}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _github_get_commits(repo: str, n: int = 10) -> dict:
            try:
                from core.github_agent import get_github
                return {"ok": True, "commits": get_github().get_commits(repo, n=int(n))}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def _switch_workspace(name: str) -> dict:
            try:
                from core.workspace import get_workspace_manager
                cfg = get_workspace_manager().switch(name)
                return {"ok": True, "workspace": cfg.get("name"), "directory": cfg.get("directory")}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        fallbacks = {
            "read_file":          _read_file,
            "write_file":         _write_file,
            "list_directory":     _list_directory,
            "execute_cmd":        _execute_cmd,
            "create_directory":   _create_directory,
            "delete_file":        _delete_file,
            "copy_file":          _copy_file,
            "move_file":          _move_file,
            "web_search":         _web_search,
            "open_program":       _open_program,
            "open_website":       _open_website,
            "screenshot":         _screenshot,
            "remember_fact":      _remember_fact,
            "scan_security":      _scan_security,
            "github_list_repos":  _github_list_repos,
            "github_list_prs":    _github_list_prs,
            "github_get_pr_diff": _github_get_pr_diff,
            "github_create_issue":_github_create_issue,
            "github_get_commits": _github_get_commits,
            "switch_workspace":   _switch_workspace,
        }

        added = 0
        for name, func in fallbacks.items():
            if name not in existing:
                self.agent.register_tool(name, func)
                added += 1
        return added

    def _ensure_agent(self):
        if not self.agent:
            self.agent = AutomyxAgent(model_name=self.model)
            fallback_count = self._register_core_tools()
            try:
                from core.tool_registry import register_all_tools
                register_all_tools(self.agent)
            except Exception as reg_err:
                self.console.print(
                    f"  [{WARN}]Tool registry: {str(reg_err)[:80]}[/]\n"
                    f"  [{DIM}]  Usando {fallback_count} herramientas basicas.[/{DIM}]"
                )
            try:
                from core.onboard_pro_v5 import inject_notion_into_agent
                _n_notion = inject_notion_into_agent(self.agent)
                if _n_notion:
                    self.console.print(f"  [{DIM}]* {_n_notion} tools de Notion cargadas[/{DIM}]")
            except Exception:
                pass
            total = len(self.agent.tools)
            self.console.print(f"  [{DIM}]* {total} herramientas cargadas[/{DIM}]")

            if self.memory:
                try:
                    prev_hist = self.memory.load_agent_history()
                    if prev_hist:
                        self.agent.load_conversation_history(prev_hist)
                        self.console.print(
                            f"  [{DIM}]* {len(prev_hist)} mensajes de historial restaurados[/{DIM}]"
                        )
                    facts_ctx = self.memory.get_facts_context()
                    if facts_ctx:
                        self.agent.inject_memory_context(facts_ctx)
                        self.console.print(
                            f"  [{DIM}]* {len(self.memory.facts)} facts de memoria cargados[/{DIM}]"
                        )
                except Exception:
                    pass

    def _ensure_autonomy(self):
        if not self.autonomy:
            try:
                from core.autonomy import AutonomyCore
                self.autonomy = AutonomyCore(model=self.model, console=self.console)
            except Exception:
                self.autonomy = None

    def _make_3d_panel(self, message: str, style: str = "orange", step_info: str = ""):
        """Panel 3D con doble borde y sombra inferior — diseño elite."""
        from rich.console import Group
        from rich.box import DOUBLE, HEAVY
        from rich.panel import Panel
        from rich.spinner import Spinner
        from rich.text import Text

        TEAL   = "#00D4AA"
        BLUE   = "#00AAFF"
        RED    = "#FF4444"
        GREEN  = "#5EE6A8"
        ORANGE = "#00D4AA"

        palette = {
            "orange": (TEAL,   BLUE),
            "blue":   (BLUE,   TEAL),
            "green":  (GREEN,  BLUE),
            "red":    (RED,    "#FF8888"),
        }
        fg, border = palette.get(style, (TEAL, BLUE))

        title = f"[bold {TEAL}]* AUTOMYX[/bold {TEAL}]"
        if step_info:
            title += f"  [dim]{step_info}[/dim]"

        panel = Panel(
            Spinner("dots", text=Text(f"  {message}", style=f"bold {fg}")),
            box=DOUBLE,
            title=title,
            border_style=border,
            padding=(0, 3),
            expand=False,
        )

        try:
            cols = os.get_terminal_size().columns
        except Exception:
            cols = 88
        shadow_w = min(cols - 10, 66)
        shadow = Text("  " + chr(9604) * shadow_w, style="dim #050d18")

        return Group(panel, shadow)

    def _auto_save_inline_token(self, text: str) -> bool:
        """Detecta tokens de integraciones pegados directamente en el chat y los guarda."""
        import re
        stripped = text.strip()
        saved = False

        # Notion: ntn_XXX o secret_XXX (mínimo 40 chars)
        notion_match = re.match(r'^(ntn_[A-Za-z0-9]{30,}|secret_[A-Za-z0-9]{30,})$', stripped)
        if notion_match and not os.environ.get("NOTION_API_KEY", ""):
            try:
                from tools.notion_tools import set_token as _nt_save
                _nt_save(stripped)
                self.console.print(
                    f"  [#5EE6A8]Token Notion detectado y guardado automáticamente.[/#5EE6A8]"
                )
                saved = True
            except Exception:
                pass

        # GitHub: ghp_XXX o github_pat_XXX
        gh_match = re.match(r'^(ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})$', stripped)
        if gh_match and not os.environ.get("GITHUB_TOKEN", ""):
            try:
                env_path = Path(__file__).parent.parent / ".env"
                os.environ["GITHUB_TOKEN"] = stripped
                lines = []
                if env_path.exists():
                    for ln in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                        if not ln.startswith("GITHUB_TOKEN="):
                            lines.append(ln)
                lines.append(f"GITHUB_TOKEN={stripped}")
                env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                self.console.print(f"  [#5EE6A8]Token GitHub detectado y guardado.[/#5EE6A8]")
                saved = True
            except Exception:
                pass

        return saved

    def _process_input(self, user_input: str, use_autonomy: bool = False):
        """Execution pipeline 3D — SmartRetry + streaming + panel elite."""
        self._ensure_agent()
        self._ensure_autonomy()
        self._reset_progress_state()
        self._auto_save_inline_token(user_input)

        self.console.print()

        from rich.live import Live
        from rich.text import Text
        from rich.rule import Rule
        from rich.console import Group as _RGroup
        from rich.spinner import Spinner as _RSpinner

        TEAL   = "#00D4AA"
        BLUE   = "#00AAFF"
        RED    = "#FF4444"
        GREEN  = "#5EE6A8"
        ORANGE = "#00D4AA"
        DIM_C  = "#3a5a80"

        _live_active    = [True]
        _tool_count     = [0]
        _last_tool      = [""]
        _last_tool_args = [""]     # args preview del tool activo
        _tool_rows      = []       # Text rows de tools completados/errores (permanentes)
        _active_tool_sp = [None]   # Spinner animado del tool en curso
        _stream_buf     = [""]     # texto acumulado de la iteración actual
        _header_printed = [False]  # ya se imprimió ">> Automyx"
        _final_ok       = [False]  # esta iteración termina como respuesta final
        # Modo compacto para planes grandes (>6 pasos): una sola fila de progreso
        _compact_mode   = [False]
        _compact_total  = [0]
        _compact_done   = [0]
        _compact_fail   = [0]
        _compact_row_idx = [-1]    # índice en _tool_rows de la fila de progreso compacta

        def _make_live_display(status_msg="Procesando...", style="blue"):
            parts = list(_tool_rows)
            # Preview del texto del modelo — solo texto humano, nunca JSON
            cur = _stream_buf[0].strip()
            if cur and not _final_ok[0]:
                # Recortar hasta el primer JSON
                for _marker in ('{"action"', '{"tool"', '\n{"', '```json'):
                    _ji = cur.find(_marker)
                    if _ji == 0:
                        cur = ""; break
                    elif _ji > 0:
                        cur = cur[:_ji].strip(); break
                # Descartar si parece fragmento de JSON (sin texto antes)
                _is_json_frag = (
                    cur.startswith("{") or cur.startswith('"action"') or
                    cur.endswith("}}") or cur.endswith('"}') or
                    '"args"' in cur or '"action"' in cur
                )
                if _is_json_frag:
                    cur = ""
                if cur:
                    preview = cur[-80:] if len(cur) > 80 else cur
                    st = Text()
                    st.append("  ", style="")
                    st.append(preview, style="dim italic #506070")
                    parts.append(st)
            if _active_tool_sp[0] is not None:
                parts.append(_active_tool_sp[0])
            parts.append(self._make_3d_panel(status_msg, style=style))
            return _RGroup(*parts)

        live = Live(
            _make_live_display("Analizando solicitud...", style="blue"),
            console=self.console,
            refresh_per_second=16,
            transient=False,  # tool rows quedan visibles cuando Live para
        )
        live.start()

        def _stop_live_once():
            if _live_active[0]:
                _live_active[0] = False
                try:
                    # Mostrar solo las filas de tools antes de congelar (sin panel de status)
                    final_display = _RGroup(*_tool_rows) if _tool_rows else Text("")
                    live.update(final_display)
                    live.stop()
                except Exception:
                    pass

        def _flush_stream_buf():
            """Imprime el buffer acumulado de la respuesta final al terminal."""
            text = _stream_buf[0].strip()
            if not text:
                return
            _stop_live_once()
            _T  = "\033[38;2;0;212;170m"   # teal #00D4AA
            _BD = "\033[1m"
            _RS = "\033[0m"
            if not _header_printed[0]:
                _header_printed[0] = True
                sys.stdout.write(f"\n  {_BD}{_T}>> Automyx{_RS}\n\n")
                sys.stdout.write(text)
            else:
                # header ya impreso → sólo añadir salto + texto
                sys.stdout.write(f"\n{text}")
            sys.stdout.flush()

        def progress_cb(phase, action, **extras):
            # ── Thinking: nueva iteración LLM ──
            if phase == "thinking":
                _stream_buf[0] = ""
                _final_ok[0]   = False
                if _live_active[0]:
                    live.update(_make_live_display("Pensando...", style="blue"))
                return

            # ── Streaming: acumular + actualizar preview en Live ──
            if phase == "streaming":
                _stream_buf[0] = action or ""
                if _live_active[0]:
                    live.update(_make_live_display("Generando...", style="blue"))
                return

            # ── Responding: iteración final confirmada ──
            if phase == "responding":
                _final_ok[0] = True
                if _live_active[0]:
                    live.update(_make_live_display("Escribiendo respuesta...", style="green"))
                return

            # ── Tool ejecutándose: guardar narración + spinner animado ──
            if phase == "tool_executing":
                # Guardar texto de narración del modelo antes de limpiar
                # Recortar cualquier JSON del texto de narración
                narration = _stream_buf[0].strip()
                if narration:
                    for _m in ('{"action"', '{"tool"', '\n{"', '```json'):
                        _ji = narration.find(_m)
                        if _ji == 0:
                            narration = ""; break
                        elif _ji > 0:
                            narration = narration[:_ji].strip(); break
                    # Descartar si sigue siendo JSON o fragmento
                    if narration and (
                        narration.startswith("{") or '"action"' in narration
                        or '"args"' in narration or narration.endswith("}}")
                    ):
                        narration = ""
                if narration:
                    narr_row = Text()
                    narr_row.append("  ", style="")
                    narr_row.append(narration[:120], style="dim italic #6888A8")
                    _tool_rows.append(narr_row)
                _stream_buf[0] = ""
                _final_ok[0]   = False

                tool_name = extras.get("tool_name", action or "tool")
                args_sum  = (extras.get("tool_args_summary", "") or "").replace("\n", " ")[:62]
                rationale = (extras.get("rationale", "") or "")[:80]

                _tool_count[0]  += 1
                _last_tool[0]    = tool_name
                _last_tool_args[0] = args_sum

                # En modo compacto (planes grandes) no mostramos spinner por tool
                if not _compact_mode[0]:
                    inner = Text()
                    inner.append(f"  {tool_name}", style="bold white")
                    if args_sum:
                        inner.append(f"  {args_sum}", style="dim")
                    if rationale:
                        inner.append(f"\n    {rationale}", style="dim italic")
                    _active_tool_sp[0] = _RSpinner("dots", text=inner)

                if _live_active[0]:
                    status = f"Ejecutando {_compact_done[0]}/{_compact_total[0]}..." if _compact_mode[0] else f"{tool_name}..."
                    live.update(_make_live_display(status, style="blue"))
                return

            # ── Tool completado: reemplazar spinner por fila ✓ ──
            if phase == "tool_executed":
                dur     = extras.get("duration_ms", 0)
                step    = extras.get("step")
                total_e = extras.get("total")
                _active_tool_sp[0] = None

                if _compact_mode[0]:
                    # Modo compacto: actualizar la fila de progreso en lugar de añadir nuevas
                    _compact_done[0] += 1
                    done_n   = _compact_done[0]
                    total_n  = _compact_total[0]
                    fail_n   = _compact_fail[0]
                    pct      = int(done_n / total_n * 100) if total_n else 0
                    filled   = int(done_n / total_n * 22) if total_n else 0
                    upd = Text()
                    upd.append("  ✓  ", style=f"bold {GREEN}")
                    upd.append("━" * filled, style=TEAL)
                    upd.append("─" * (22 - filled), style="dim")
                    upd.append(f"  {done_n}/{total_n}", style=f"bold {TEAL}")
                    if fail_n:
                        upd.append(f"  ({fail_n} errores)", style=f"dim {RED}")
                    idx = _compact_row_idx[0]
                    if 0 <= idx < len(_tool_rows):
                        _tool_rows[idx] = upd
                    if _live_active[0]:
                        live.update(_make_live_display("Procesando...", style="blue"))
                    return

                # Usar tool_name de extras (thread-safe) con fallback a _last_tool
                done_tool = extras.get("tool_name") or _last_tool[0]
                done_args = _last_tool_args[0] if extras.get("tool_name") == _last_tool[0] else ""

                done = Text()
                done.append("  ✓  ", style=f"bold {GREEN}")
                done.append(done_tool, style="bold white")
                if done_args:
                    done.append(f"  {done_args}", style="dim")
                if dur:
                    t_str = f"{dur / 1000:.1f}s" if dur >= 1000 else f"{dur}ms"
                    done.append(f"  ({t_str})", style=f"dim {GREEN}")
                _tool_rows.append(done)

                # Barra de progreso cuando hay múltiples pasos
                if step and total_e and int(total_e) > 1:
                    pct    = int((int(step) / int(total_e)) * 100)
                    filled = int((int(step) / int(total_e)) * 26)
                    bar    = Text()
                    bar.append("  " + "━" * filled, style=TEAL)
                    bar.append("─" * (26 - filled), style="dim")
                    bar.append(f"  {pct}%  ({step}/{total_e})", style=f"bold {TEAL}")
                    _tool_rows.append(bar)

                if _live_active[0]:
                    live.update(_make_live_display("Procesando...", style="blue"))
                return

            if phase in ("analyzing",):
                if _live_active[0]:
                    live.update(_make_live_display("Analizando...", style="blue"))
                return

            if phase == "error":
                _active_tool_sp[0] = None
                if _compact_mode[0]:
                    _compact_fail[0] += 1
                    if _live_active[0]:
                        live.update(_make_live_display("Reintentando...", style="red"))
                    return
                err_row = Text()
                err_row.append("  ✗  ", style=f"bold {RED}")
                err_row.append(str(action)[:110], style="dim")
                _tool_rows.append(err_row)
                if _live_active[0]:
                    live.update(_make_live_display("Reintentando...", style="red"))
                return

            if phase == "plan_created":
                # Resetear modo compacto del plan anterior
                _compact_mode[0] = False
                _compact_done[0] = 0
                _compact_fail[0] = 0
                _compact_row_idx[0] = -1
                n = len(extras.get("plan", []) or [])
                if n > 0:
                    plan_row = Text()
                    plan_row.append("  ≡  ", style=f"bold {TEAL}")
                    plan_row.append(f"Plan: {n} pasos", style=f"dim {TEAL}")
                    _tool_rows.append(plan_row)
                    if n > 6:
                        _compact_mode[0]  = True
                        _compact_total[0] = n
                        # Reservar fila de progreso compacta (mutable via índice)
                        prog_row = Text()
                        prog_row.append(f"  ⠋  0/{n} completados", style=f"dim {TEAL}")
                        _tool_rows.append(prog_row)
                        _compact_row_idx[0] = len(_tool_rows) - 1
                return

            if phase == "learning":
                if _live_active[0]:
                    live.update(_make_live_display("Aprendiendo...", style="blue"))
                return

            if phase == "installing":
                pkg = extras.get("tool_name", action or "pkg")
                _active_tool_sp[0] = None
                inst_row = Text()
                inst_row.append("  ⬇  ", style=f"bold {BLUE}")
                inst_row.append(f"pip install {pkg}", style="dim italic")
                _tool_rows.append(inst_row)
                if _live_active[0]:
                    live.update(_make_live_display(f"Instalando {pkg}...", style="blue"))
                return

            if phase == "skill_saved":
                skill_nm = extras.get("tool_name", action or "skill")
                sk_row = Text()
                sk_row.append("  ★  ", style=f"bold {TEAL}")
                sk_row.append("skill guardada", style=f"bold {GREEN}")
                sk_row.append(f"  {skill_nm}", style="dim")
                _tool_rows.append(sk_row)
                return

        try:
            from core.agent import set_progress_callback
            set_progress_callback(progress_cb)
        except Exception:
            pass

        response    = ""
        duration    = 0.0
        agent_error = None
        try:
            start = time.time()
            if self.autonomy and use_autonomy:
                result   = self.autonomy.execute_autonomously(user_input)
                response = result.get("ejecucion", result.get("execution", "Done."))
            else:
                response = self.agent.run(user_input, progress_callback=progress_cb)
            duration = time.time() - start
        except Exception as e:
            duration    = time.time() - start
            agent_error = e
        finally:
            _stop_live_once()
            try:
                from core.agent import set_progress_callback
                set_progress_callback(None)
            except Exception:
                pass

        if agent_error is not None:
            self.console.print(f"\n  [{ERR}]! Error:[/] {agent_error}")
            return

        # Si el stream terminó con una respuesta final (sin tool calls),
        # imprimirla desde el buffer acumulado.
        # Si el buffer está vacío o la respuesta final vino por _display_response,
        # usar el texto retornado por agent.run().
        buf = _stream_buf[0].strip()
        if buf and _final_ok[0]:
            # Respuesta llegó por streaming — vaciar buffer al terminal
            _flush_stream_buf()
            sys.stdout.write("\n")
            sys.stdout.flush()
        elif response and response.strip():
            # Sin streaming limpio: mostrar con _display_response
            self.console.print()
            self._display_response(response)
        elif _tool_count[0] > 0:
            # Tools ejecutaron pero LLM no dio texto — mostrar resumen breve
            self.console.print()
            _sr = Text()
            _sr.append("  ✓ ", style="bold #00D4AA")
            _sr.append(f"{_tool_count[0]} acción{'es' if _tool_count[0] > 1 else ''} completadas.", style="dim white")
            self.console.print(_sr)

        if self.memory and self.agent:
            try:
                self.memory.save_agent_history(self.agent.history)
            except Exception:
                pass

        self.console.print()
        chars = len(response) if response else 0
        mins  = int(duration // 60)
        secs_r = duration % 60
        secs  = int(secs_r)
        ms    = int((secs_r - secs) * 1000)
        if mins > 0:
            duration_str = f"{mins}m {secs}s"
        elif secs >= 2:
            duration_str = f"{secs}s"
        else:
            duration_str = f"{secs}.{ms // 100}s"

        try:
            _cols = os.get_terminal_size().columns
        except Exception:
            _cols = 88
        _sep = chr(9472) * min(30, _cols - 20)

        footer = Text()
        footer.append("  ✓ ", style="bold #00D4AA")
        footer.append(duration_str, style="bold #00AAFF")
        if _tool_count[0]:
            footer.append(f"  ·  {_tool_count[0]} tools", style="dim #5A8090")
        footer.append(f"  ·  {chars:,} chars", style="dim #5A8090")
        footer.append(f"  {_sep}", style="dim #1a3050")
        self.console.print(footer)
        self.console.print()

    def _run_shell_direct(self, command: str):
        """Ejecuta un comando shell directo (prefijo !) y muestra el output en tiempo real."""
        if not command:
            return
        import subprocess
        self.console.print(f"\n  [{DIM}]$ {command}[/{DIM}]")
        try:
            proc = subprocess.run(
                command, shell=True, text=True, encoding='utf-8', errors='replace',
                capture_output=False, timeout=300
            )
            if proc.returncode != 0:
                self.console.print(f"  [{ERR}]Exit {proc.returncode}[/{ERR}]")
        except subprocess.TimeoutExpired:
            self.console.print(f"  [{ERR}]Timeout (300s)[/{ERR}]")
        except Exception as e:
            self.console.print(f"  [{ERR}]Error: {e}[/{ERR}]")
        self.console.print()

    def _reset_progress_state(self):
        """Reset progress tracking state for new input."""
        pass

    def _display_response(self, response: str):
        """Muestra la respuesta con syntax highlighting y diseño elite."""
        if not response:
            return

        from rich.syntax import Syntax
        from rich.text import Text

        TEAL   = "#00D4AA"
        BLUE   = "#00AAFF"
        GREEN  = "#5EE6A8"

        try:
            cols = os.get_terminal_size().columns
        except Exception:
            cols = 88

        label = Text()
        label.append("  >> Automyx", style=f"bold {TEAL}")
        label.append("  " + chr(9472) * min(40, cols - 16), style="dim #1a3050")
        self.console.print(label)
        self.console.print()

        text  = response.strip()
        lines = text.splitlines()

        has_code_block = "```" in text
        has_markdown   = has_code_block or any(
            text.startswith(md) for md in ("# ", "## ", "### ", "- ", "* ", "1.", "> ")
        )

        if has_code_block:
            import re as _re
            parts = _re.split(r"(```\w*\n[\s\S]*?```)", text)
            for part in parts:
                if part.startswith("```"):
                    lang_match = _re.match(r"```(\w*)\n([\s\S]*?)```", part)
                    if lang_match:
                        lang    = lang_match.group(1) or "text"
                        code    = lang_match.group(2)
                        try:
                            self.console.print(Syntax(
                                code, lang,
                                theme="monokai",
                                line_numbers=len(code.splitlines()) > 5,
                                background_color="#0d1520",
                            ))
                        except Exception:
                            self.console.print(f"  [dim]{code}[/dim]")
                    else:
                        self.console.print(part)
                else:
                    stripped = part.strip()
                    if stripped:
                        try:
                            self.console.print(Markdown(stripped))
                        except Exception:
                            self.console.print(f"  {stripped}")
        elif len(lines) <= 3 and not has_markdown:
            for line in lines:
                self.console.print(f"  {line}")
        else:
            try:
                self.console.print(Markdown(text))
            except Exception:
                self.console.print(text)

        self.console.print()

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    def _handle_interrupt(self, signum, frame):
        self.console.print()
        self.console.print(f"[{WARN}]Interrupted. Use /exit to quit.[/]")

    def _exit(self):
        self.running = False
        self.session.save()

        try:
            from core.token_tracker import get_tracker
            get_tracker().save_session()
        except Exception:
            pass

        try:
            from core.workspace import get_workspace_manager
            if self.agent:
                get_workspace_manager().save_current_state(self.agent.history)
        except Exception:
            pass

        self.console.print()
        self.console.print(f"[{DIM}]Session saved. Goodbye![/{DIM}]")
        sys.exit(0)


# ============================================================================
# Entry point
# ============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='AUTOMYX REPL')
    parser.add_argument('--model', '-m', help='Model to use')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    repl = AutomyxREPL(model=args.model, verbose=args.verbose)
    repl.start()


if __name__ == '__main__':
    main()
