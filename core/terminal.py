"""
AUTOMYX TERMINAL UI v2.0
========================
Wrapper sobre Rich que da a TODO el output del agente un look profesional.
Refactored to consume the shared design system in `core.ui.py` (electric blue
glassmorphism). Public API preserved for backward compatibility — but new
code should import colors and helpers directly from `core.ui`.

Provides:
- Banners animados
- Spinners con contexto
- Paneles con borde electric-blue
- Trees jerárquicos
- Tablas con resaltado
- Progress bars
- Syntax highlighting para JSON/Python/YAML
- Markdown render
- Logging estructurado con timestamps
- Auto-detección de TTY (no rompe cuando se redirige a archivo)
"""
from __future__ import annotations

import os
import sys
import time
import json
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Iterable

# Reuse the brand palette and shared console from core.ui
try:
    from core.ui import (
        NAVY, DEEP_BLUE, BLUE, ELECTRIC, CYAN, GLOW, WHITE, GRAY, DIM,
        WARN, OK, ERR, PURPLE, RICH_AVAILABLE, console as _shared_console,
    )
except Exception:
    RICH_AVAILABLE = False
    _shared_console = None
    NAVY = DEEP_BLUE = BLUE = ELECTRIC = CYAN = GLOW = WHITE = GRAY = DIM = ""
    WARN = OK = ERR = PURPLE = ""

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.tree import Tree
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.spinner import Spinner
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.box import ROUNDED, DOUBLE, HEAVY, SIMPLE, MINIMAL
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align
    from rich import box as rich_box
    from rich.markup import escape as _rich_escape
    RICH_AVAILABLE = RICH_AVAILABLE or True
except ImportError:
    RICH_AVAILABLE = False

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=False)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


# Backward-compat alias mapping — old BRAND_* constants now point to the new
# electric-blue palette. Existing code (core.agent, core.onboard_pro, etc.)
# continues to import these names; visual identity is consistent with `core.ui`.
BRAND_CYAN    = CYAN
BRAND_MAGENTA = PURPLE
BRAND_YELLOW  = WARN
BRAND_GREEN   = OK
BRAND_RED     = ERR
BRAND_GRAY    = GRAY
BRAND_BLUE    = BLUE

ASCII_LOGO = """
    █████╗ ██╗   ██╗████████╗ ██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗
   ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗████╗ ████║╚██╗ ██╔╝╚██╗██╔╝
   ███████║██║   ██║   ██║   ██║   ██║██╔████╔██║ ╚████╔╝  ╚███╔╝
   ██╔══██║███╗██║   ██║   ██║   ██║██║╚██╔╝██║  ╚██╔╝   ██╔██╗
   ██║  ██║  ████║   ██║   ╚██████╔╝██║ ╚═╝ ██║   ██║   ██╔╝ ██╗
   ╚═╝  ╚═╝   ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝   ╚═╝   ╚═╝  ╚═╝
"""

ASCII_LOGO_COMPACT = """
  ╔═╗ ╦ ╦ ╦ ╔═╗ ╔═╗ ╦ ╦ ╦ ╦╔═╗ ╦ ╦
  ║═╬╗║ ║ ║ ╠═╣ ║   ╠═╣ ╠═╣╠╣
  ╚═╝╚╚═╝ ╩ ╩ ╩ ╚═╝ ╩ ╩ ╩ ╩╩  ╩ ╩
   v 2 . 5    ·   N E X O R A
"""

ASCII_LOGO_MINI = "  ⚡ AUTOMYX 2.5 ⚡  "


# ---------------------------------------------------------------------------
# Consola singleton
# ---------------------------------------------------------------------------
def _detect_console() -> "Console":
    if not RICH_AVAILABLE:
        return None
    is_tty = sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False
    force_terminal = os.environ.get("AUTOMYX_FORCE_TERMINAL", "1") == "1"
    # Detectar Windows Terminal o PowerShell moderno → soporta Unicode
    is_modern = "WT_SESSION" in os.environ or os.environ.get("TERM_PROGRAM") == "vscode"
    if os.name == "nt" and not is_modern:
        # Forzar ASCII para evitar problemas con cp1252
        os.environ["PYTHONIOENCODING"] = "utf-8"
        return Console(
            force_terminal=False,
            file=open(os.devnull, "w") if "AUTOMYX_NO_OUTPUT" in os.environ else sys.stdout,
            legacy_windows=True,
            safe_box=True,
        )
    return Console(
        force_terminal=force_terminal and is_tty,
        width=None,
        color_system="truecolor" if os.environ.get("TERM", "").endswith("256color") or is_modern else "auto",
        legacy_windows=False,
        safe_box=False,
        highlight=False,
    )


# Prefer the shared console from `core.ui` so all surfaces draw with the same
# color_system and encoding. Fallback to a local one if Rich is missing.
console = _shared_console if (_shared_console is not None) else _detect_console()


# ---------------------------------------------------------------------------
# Helper anti-explosión: el LLM y los resultados de tools pueden traer
# markup de Rich malformado ([/dim] sin abrir, etc). Esta función escapa
# cualquier string "no confiable" antes de pasarlo a console.print().
# ---------------------------------------------------------------------------
def _safe_print(prefix_style: str, icon: str, msg: str, *, end: str = "\n") -> None:
    """
    Imprime `[prefix_style]icon[/] <msg-escaped>` de forma segura.
    Si Rich truena por markup residual, hace fallback a print plano.
    """
    if not RICH_AVAILABLE or console is None:
        _print_fallback(f"{icon}  {msg}", end=end)
        return
    try:
        safe_msg = _rich_escape(str(msg)) if msg else ""
        console.print(f"[{prefix_style}]{icon}[/] {safe_msg}", end=end)
    except Exception:
        # Último recurso: imprimir como literal
        try:
            console.print(str(msg), end=end, markup=False, highlight=False)
        except Exception:
            _print_fallback(f"{icon}  {msg}", end=end)


def _print_fallback(*args, **kwargs):
    """Fallback a print cuando Rich no está disponible."""
    try:
        msg = " ".join(str(a) for a in args)
        if COLORAMA_AVAILABLE:
            msg = f"{Style.RESET_ALL}{msg}{Style.RESET_ALL}"
        print(msg, **kwargs)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Banners
# ---------------------------------------------------------------------------
def banner(
    text: str = "",
    *,
    subtitle: str = "",
    style: str = BRAND_CYAN,
    box: Any = None,
    ascii_logo: bool = True,
    width: int = 90,
) -> None:
    """Imprime un banner con logo ASCII grande + subtítulo."""
    if RICH_AVAILABLE and console:
        content_parts = []
        if ascii_logo:
            content_parts.append(Text(ASCII_LOGO, style=style))
        if text:
            content_parts.append(Text(text, style=f"bold {style}"))
        if subtitle:
            content_parts.append(Text(subtitle, style="dim"))

        from rich.console import Group
        group = Group(*content_parts)
        panel = Panel(
            group,
            border_style=style,
            box=box or DOUBLE,
            padding=(1, 2),
            width=width,
        )
        console.print(panel)
    else:
        _print_fallback("\n" + (ASCII_LOGO if ascii_logo else "") + text + ("  " + subtitle if subtitle else ""))


def banner_compact(model: str = "", version: str = "2.5.0") -> None:
    """Banner compacto para el día a día."""
    if RICH_AVAILABLE and console:
        title = Text()
        title.append("AUTOMYX ", style=f"bold {BRAND_CYAN}")
        title.append(f"v{version}", style=BRAND_YELLOW)
        if model:
            title.append(f"  -  {model}", style=BRAND_GRAY)
        console.print(title)
    else:
        _print_fallback(f"AUTOMYX v{version}" + (f"  -  {model}" if model else ""))


def banner_skill(skill_name: str, description: str = "") -> None:
    """Banner de activación de skill."""
    if RICH_AVAILABLE and console:
        t = Text()
        t.append("⚡ ", style=BRAND_YELLOW)
        t.append(skill_name, style=f"bold {BRAND_CYAN}")
        if description:
            t.append(f"  ·  {description}", style=BRAND_GRAY)
        console.print(Panel(t, border_style=BRAND_CYAN, box=SIMPLE, padding=(0, 1)))
    else:
        _print_fallback(f"[SKILL] {skill_name}: {description}")


# ---------------------------------------------------------------------------
# Mensajes
# ---------------------------------------------------------------------------
def info(msg: str, *, icon: str = "[i]") -> None:
    _safe_print(BRAND_BLUE, icon, msg)


def success(msg: str, *, icon: str = "[OK]") -> None:
    _safe_print(f"bold {BRAND_GREEN}", icon, msg)


def warn(msg: str, *, icon: str = "[!]") -> None:
    _safe_print(BRAND_YELLOW, icon, msg)


def error(msg: str, *, icon: str = "[X]") -> None:
    _safe_print(f"bold {BRAND_RED}", icon, msg)


def debug(msg: str) -> None:
    if os.environ.get("AUTOMYX_DEBUG") == "1":
        if RICH_AVAILABLE and console:
            console.print(f"[dim][DEBUG] {msg}[/dim]")


def step(n: int, total: int, msg: str) -> None:
    """Mensaje de paso numerado, estilo wizard."""
    if RICH_AVAILABLE and console:
        from rich.text import Text
        t = Text()
        t.append("  ")
        t.append("[", style=BRAND_CYAN)
        t.append(f"{n}/{total}", style=f"bold {BRAND_CYAN}")
        t.append("]  ", style=BRAND_CYAN)
        t.append(msg)
        console.print(t)
    else:
        _print_fallback(f"  [{n}/{total}] {msg}")


# ---------------------------------------------------------------------------
# Spinner / context managers
# ---------------------------------------------------------------------------
@contextmanager
def spinner(message: str, *, style: str = BRAND_CYAN, final_message: Optional[str] = None):
    """Spinner simple. Uso: with spinner('cargando'): do_thing()"""
    if RICH_AVAILABLE and console:
        with console.status(f"[{style}]{message}[/]", spinner="dots", spinner_style=style):
            yield
        if final_message:
            success(final_message)
    else:
        _print_fallback(f"... {message}")
        yield
        if final_message:
            _print_fallback(f"OK {final_message}")


@contextmanager
def task(title: str, *, total: int = 100):
    """Progress bar con tareas. yield una función update(step, total_step, msg)."""
    if RICH_AVAILABLE and console:
        with Progress(
            SpinnerColumn(spinner_name="dots", style=BRAND_CYAN),
            TextColumn(f"[bold {BRAND_CYAN}]{title}[/]"),
            BarColumn(bar_width=30, style=BRAND_CYAN, complete_style=BRAND_GREEN, finished_style=BRAND_GREEN),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task(title, total=total)

            def update(advance: int = 1, msg: str = ""):
                progress.update(task_id, advance=advance)
                if msg:
                    progress.console.print(f"    {msg}")

            yield update
    else:
        _print_fallback(f"START  {title}")
        def update(advance=1, msg=""):
            if msg:
                _print_fallback(f"  -> {msg}")
        yield update
        _print_fallback(f"END  {title}")


# ---------------------------------------------------------------------------
# Paneles
# ---------------------------------------------------------------------------
def panel(
    content: Any,
    *,
    title: str = "",
    subtitle: str = "",
    style: str = BRAND_CYAN,
    box: Any = None,
    width: Optional[int] = None,
) -> None:
    if RICH_AVAILABLE and console:
        console.print(Panel(
            content,
            title=f"[bold {style}]{title}[/]" if title else None,
            subtitle=subtitle or None,
            border_style=style,
            box=box or ROUNDED,
            width=width,
            padding=(1, 2),
        ))
    else:
        _print_fallback(f"--- {title} ---" if title else "---")
        _print_fallback(content)
        _print_fallback("---")


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------
def table(
    title: str,
    columns: List[str],
    rows: List[List[str]],
    *,
    styles: Optional[List[str]] = None,
) -> None:
    """Imprime una tabla estilizada."""
    if RICH_AVAILABLE and console:
        t = Table(title=f"[bold {BRAND_CYAN}]{title}[/]", box=ROUNDED, border_style=BRAND_CYAN)
        styles = styles or [BRAND_CYAN] * len(columns)
        for col, style in zip(columns, styles):
            t.add_column(col, style=style, no_wrap=False)
        for row in rows:
            t.add_row(*[str(c) for c in row])
        console.print(t)
    else:
        _print_fallback(f"=== {title} ===")
        for row in rows:
            _print_fallback("  ".join(str(c) for c in row))


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------
def tree(title: str, structure: Dict[str, Any], *, style: str = BRAND_CYAN) -> None:
    """Imprime un árbol jerárquico desde un dict."""
    if RICH_AVAILABLE and console:
        tr = Tree(f"[bold {style}]{title}[/]", guide_style=style)
        _build_tree(tr, structure, style)
        console.print(tr)
    else:
        _print_fallback(f"--- {title} ---")
        for k, v in structure.items():
            _print_fallback(f"  {k}: {v}")


def _build_tree(node, structure, style):
    if isinstance(structure, dict):
        for k, v in structure.items():
            label = f"[{style}]{k}[/]"
            if isinstance(v, dict):
                child = node.add(label, style=style)
                _build_tree(child, v, style)
            elif isinstance(v, list):
                child = node.add(label, style=style)
                for item in v:
                    if isinstance(item, (dict, list)):
                        _build_tree(child, item, style)
                    else:
                        child.add(str(item), style=BRAND_GRAY)
            else:
                node.add(f"{label}  [dim]{v}[/dim]", style=style)
    elif isinstance(structure, list):
        for item in structure:
            _build_tree(node, item, style)


# ---------------------------------------------------------------------------
# JSON / Markdown / Syntax
# ---------------------------------------------------------------------------
def print_json(obj: Any, *, title: str = "") -> None:
    if RICH_AVAILABLE and console:
        try:
            txt = json.dumps(obj, indent=2, ensure_ascii=False)
            syn = Syntax(txt, "json", theme="monokai", line_numbers=False, word_wrap=True)
            if title:
                console.print(Panel(syn, title=f"[bold {BRAND_CYAN}]{title}[/]", border_style=BRAND_CYAN, box=SIMPLE))
            else:
                console.print(syn)
        except (TypeError, ValueError):
            console.print(str(obj))
    else:
        _print_fallback(json.dumps(obj, indent=2, ensure_ascii=False) if not isinstance(obj, str) else obj)


def print_markdown(md_text: str) -> None:
    if RICH_AVAILABLE and console:
        try:
            console.print(Markdown(md_text))
        except Exception:
            console.print(md_text)
    else:
        _print_fallback(md_text)


def print_code(code: str, language: str = "python", *, title: str = "") -> None:
    if RICH_AVAILABLE and console:
        syn = Syntax(code, language, theme="monokai", line_numbers=True, word_wrap=True)
        if title:
            console.print(Panel(syn, title=f"[bold {BRAND_CYAN}]{title}[/]", border_style=BRAND_CYAN, box=SIMPLE))
        else:
            console.print(syn)
    else:
        _print_fallback(code)


# ---------------------------------------------------------------------------
# Onboarding wizard
# ---------------------------------------------------------------------------
def onboarding_intro() -> None:
    """Intro animada del wizard de onboarding."""
    if RICH_AVAILABLE and console:
        # 1. Logo grande
        banner("", subtitle="Gateway · v2.5.0 · Nivel Élite", ascii_logo=True, width=110)

        # 2. Panel de bienvenida
        welcome = Text()
        welcome.append("Bienvenido a ", style="white")
        welcome.append("AUTOMYX", style=f"bold {BRAND_CYAN}")
        welcome.append(" — tu agente de IA omnipotente.", style="white")
        console.print(Panel(welcome, border_style=BRAND_MAGENTA, box=ROUNDED, padding=(1, 2)))

        # 3. Resumen de capacidades
        caps = Tree(f"[bold {BRAND_YELLOW}]Capacidades de fábrica[/]", guide_style=BRAND_YELLOW)
        for cat, items in [
            ("Productividad", ["Chat multi-modelo", "Búsqueda web profunda", "Generación de docs/PDF", "OCR y visión"]),
            ("Sistema", ["Ejecución de comandos", "Automatización PC/Mac", "Cron jobs", "Docker/K8s"]),
            ("Multimedia", ["Edición de video FFmpeg", "3D con Blender", "Audio mastering", "OBS livestreaming"]),
            ("Desarrollo", ["280+ herramientas", "Code review", "Test runner", "CI/CD"]),
            ("Conocimiento", ["RAG vector", "Búsqueda arXiv/PubMed", "OSINT/ciber", "OpenClaw bridge"]),
        ]:
            branch = caps.add(f"[bold {BRAND_CYAN}]{cat}[/]")
            for it in items:
                branch.add(f"[dim]{it}[/dim]")
        console.print(caps)
        console.print()
    else:
        _print_fallback(ASCII_LOGO)
        _print_fallback("Bienvenido a AUTOMYX v2.5.0")


def onboarding_step_complete(n: int, total: int, name: str) -> None:
    """Marca un paso del wizard como completado."""
    if RICH_AVAILABLE and console:
        console.print(f"  [{BRAND_GREEN}]✓[/]  Paso {n}/{total}  [bold]{name}[/bold]  [dim]listo[/dim]")
    else:
        _print_fallback(f"  OK  Paso {n}/{total} {name} listo")


def onboarding_summary(rows: List[Dict[str, str]]) -> None:
    """Tabla resumen al final del wizard."""
    if RICH_AVAILABLE and console:
        t = Table(title=f"[bold {BRAND_GREEN}]✓ AUTOMYX está listo[/]", box=DOUBLE, border_style=BRAND_GREEN)
        t.add_column("Configuración", style=BRAND_CYAN, no_wrap=False)
        t.add_column("Valor", style="white")
        for r in rows:
            t.add_row(r.get("key", ""), r.get("value", ""))
        console.print(t)
        console.print()
        console.print(Panel(
            Text("🚀 Dashboard: ", style="bold") + Text("http://localhost:3500", style=f"bold {BRAND_CYAN}"),
            border_style=BRAND_CYAN,
            box=ROUNDED,
        ))
    else:
        for r in rows:
            _print_fallback(f"  {r.get('key')}: {r.get('value')}")


# ---------------------------------------------------------------------------
# Tool execution renderer
# ---------------------------------------------------------------------------
def tool_executing(name: str, args: Dict[str, Any]) -> None:
    """Mensaje 'ejecutando tool' estilizado."""
    if RICH_AVAILABLE and console:
        try:
            safe_name = _rich_escape(str(name))
            safe_args_parts = []
            for k, v in (args or {}).items():
                safe_k = _rich_escape(str(k))
                safe_v = _rich_escape(repr(v)[:60])
                safe_args_parts.append(f"[dim]{safe_k}[/dim]=[{BRAND_YELLOW}]{safe_v}[/{BRAND_YELLOW}]")
            args_str = ", ".join(safe_args_parts)
            console.print(f"  [{BRAND_MAGENTA}]▶[/]  [bold]{safe_name}[/bold]({args_str})")
        except Exception:
            _print_fallback(f"  ▶ {name}({args})")
    else:
        _print_fallback(f"  ▶ {name}({args})")


def tool_result(name: str, ok: bool, summary: str = "") -> None:
    """Mensaje 'tool result' estilizado."""
    if RICH_AVAILABLE and console:
        icon = "✓" if ok else "✗"
        color = BRAND_GREEN if ok else BRAND_RED
        try:
            safe_name = _rich_escape(str(name))
            safe_summary = _rich_escape(str(summary)[:120]) if summary else ""
            msg = f"  [{color}]{icon}[/]  [bold]{safe_name}[/bold]"
            if safe_summary:
                msg += f"  [dim]→[/dim]  {safe_summary}"
            console.print(msg)
        except Exception:
            _print_fallback(f"  {'OK' if ok else 'FAIL'} {name} {summary}")
    else:
        _print_fallback(f"  {'OK' if ok else 'FAIL'} {name} {summary}")


def tool_loop_warning(action: str, count: int) -> None:
    """Aviso de bucle detectado."""
    if RICH_AVAILABLE and console:
        console.print(Panel(
            f"[bold {BRAND_RED}]⚠ Bucle detectado[/]  "
            f"La tool [bold]{action}[/] se ejecutó {count} veces con el mismo resultado. "
            f"Cambia de estrategia.",
            border_style=BRAND_RED,
            box=DOUBLE,
            padding=(0, 1),
        ))
    else:
        _print_fallback(f"!!! BUCLE: {action} x{count}")


def llm_thinking() -> None:
    """Indicador de 'pensando' mientras el LLM responde."""
    if RICH_AVAILABLE and console:
        try:
            console.print(f"  [{BRAND_MAGENTA}]◆ LLM pensando...[/]", end="\r")
        except Exception:
            _print_fallback("...", end="\r")
    else:
        _print_fallback("...", end="\r")


def llm_response_stream(text: str) -> None:
    """Render incremental de la respuesta LLM."""
    if RICH_AVAILABLE and console:
        try:
            # markup=False: el LLM puede traer corchetes que NO son Rich markup
            console.print(text, end="", markup=False, highlight=False)
        except Exception:
            _print_fallback(text, end="")
    else:
        _print_fallback(text, end="")
        sys.stdout.flush()


def llm_response_done() -> None:
    """Finaliza el streaming."""
    if RICH_AVAILABLE and console:
        console.print("")  # newline final
    else:
        print()


# ---------------------------------------------------------------------------
# Logging integration
# ---------------------------------------------------------------------------
class AutomixLogger:
    """Logger que formatea todo a través del terminal rico."""

    def __init__(self, name: str = "automyx"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

    def info(self, msg: str):
        self.logger.info(msg)
        info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)
        warn(msg)

    def error(self, msg: str):
        self.logger.error(msg)
        error(msg)

    def success(self, msg: str):
        self.logger.info(f"OK: {msg}")
        success(msg)


# Logger global
log = AutomixLogger("automyx")


# ---------------------------------------------------------------------------
# Multi-tarea: panel de progreso
# ---------------------------------------------------------------------------
def multitask_status(tasks: List[Dict[str, Any]]) -> None:
    """Muestra el estado de múltiples tareas en paralelo."""
    if not RICH_AVAILABLE or console is None or not tasks:
        return
    table = Table(
        title=f"[bold {BRAND_MAGENTA}]⚡ Tareas en paralelo ({len(tasks)})[/]",
        box=ROUNDED,
        border_style=BRAND_MAGENTA,
    )
    table.add_column("ID", style=BRAND_CYAN, no_wrap=True)
    table.add_column("Status", style=BRAND_YELLOW)
    table.add_column("Fase", style=BRAND_BLUE)
    table.add_column("Acción", style="white")
    table.add_column("Tools", style=BRAND_GREEN, justify="right")
    table.add_column("Progreso", style=BRAND_MAGENTA, justify="right")
    for t in tasks[:20]:
        status = t.get("status", "?")
        icon = {
            "pending": "○", "running": "▶", "streaming": "✦",
            "completed": "✓", "failed": "✗", "cancelled": "⊘",
        }.get(status, "•")
        color = {
            "pending": BRAND_GRAY, "running": BRAND_CYAN, "streaming": BRAND_MAGENTA,
            "completed": BRAND_GREEN, "failed": BRAND_RED, "cancelled": BRAND_YELLOW,
        }.get(status, "white")
        table.add_row(
            str(t.get("task_id", "?"))[:18],
            f"[{color}]{icon} {status}[/]",
            str(t.get("current_phase", ""))[:24],
            str(t.get("current_action", ""))[:36],
            str(len(t.get("tools_used", []))),
            f"{int(t.get('progress', 0) * 100)}%",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    banner_compact("gpt-oss-120b", "2.5.0")
    print()
    info("Mensaje informativo")
    success("Operación exitosa")
    warn("Advertencia importante")
    error("Algo falló")
    step(3, 7, "Configurando canales de comunicación")
    print()

    with spinner("Cargando dependencias..."):
        time.sleep(0.5)
    success("Dependencias cargadas")

    print()
    table(
        "Inventario de herramientas",
        ["Categoría", "Cantidad", "Estado"],
        [
            ["Productividad", "62", "✓"],
            ["Multimedia", "48", "✓"],
            ["Sistema", "54", "✓"],
            ["Conocimiento", "37", "✓"],
            ["TOTAL", "201", "READY"],
        ],
    )
    print()
    tree(
        "AUTOMYX 2.5",
        {
            "Core": {"Agent": "Llama 3.1 70B", "Memory": "RAG+SQLite"},
            "Tools": {
                "Productividad": 62,
                "Multimedia": 48,
                "Sistema": 54,
            },
            "Skills": {
                "Elite 2026": 7,
                "OpenClaw-style": 12,
            },
        },
    )
    print()
    print_json({"action": "create_file", "args": {"path": "test.txt"}}, title="Tool call")
    print()
    print_code("def hello():\n    print('AUTOMYX')", "python", title="Snippet")
    print()
    print_markdown("# Hola\n**AUTOMYX** es la *bestia*.")
    print()
    print("✓ terminal.py cargado y funcional")
