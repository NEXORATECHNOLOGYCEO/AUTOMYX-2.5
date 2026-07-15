"""
AUTOMYX BANNER v2.0
===================
Banner rediseñado con el sistema terminal.py.
Logo AUTOMYX grande, árbol de capacidades, tabla de estado.
"""
from __future__ import annotations

import time
import os
from typing import Optional

try:
    from .terminal import (
        banner as _banner,
        banner_compact,
        success as _success,
        info as _info,
        warn as _warn,
        error as _error,
        step as _step,
        panel as _panel,
        tree as _tree,
        table as _table,
        BRAND_CYAN, BRAND_YELLOW, BRAND_GREEN, BRAND_MAGENTA, BRAND_GRAY,
        ASCII_LOGO, ASCII_LOGO_COMPACT, ASCII_LOGO_MINI,
        RICH_AVAILABLE, console,
    )
except ImportError:
    from core.terminal import (
        banner as _banner, banner_compact, success as _success, info as _info,
        warn as _warn, error as _error, step as _step, panel as _panel, tree as _tree,
        table as _table, BRAND_CYAN, BRAND_YELLOW, BRAND_GREEN, BRAND_MAGENTA, BRAND_GRAY,
        ASCII_LOGO, ASCII_LOGO_COMPACT, ASCII_LOGO_MINI, RICH_AVAILABLE, console,
    )


def print_automyx_banner(
    model_name: str = "automyx",
    show_details: bool = True,
    *,
    version: str = "2.5.0",
    provider: Optional[str] = None,
    agent_count: int = 1,
    skill_count: int = 18,
    tool_count: int = 275,
    channels: Optional[list] = None,
) -> None:
    """
    Imprime el banner principal de AUTOMYX.
    - Logo AUTOMYX grande
    - Subtítulo con versión + modelo
    - Si show_details: árbol de capacidades + tabla de inventario
    """
    import os as _os
    import time as _time
    try:
        from rich.text import Text
        from rich.panel import Panel
        from rich import box as _rbox

        _G  = ["#00FFB2", "#00F2C8", "#00E0DC", "#00CCEE", "#00B8FF", "#3D9EFF"]
        _DM = "#4A6A8A"
        _W  = "#F0F6FF"
        _T  = "#00D4AA"

        if not (RICH_AVAILABLE and console):
            print(ASCII_LOGO_MINI)
            print(f"AUTOMYX v{version} · {model_name}")
            return

        # ── 1) Boot probes ultrarrápidos (identidad hacker) ──
        import platform as _plat
        _probes = [
            ("sys",    f"{_plat.system().lower()} {_plat.release()}"),
            ("python", _plat.python_version()),
            ("engine", f"automyx core v{version}"),
        ]
        console.print()
        for _n, _v in _probes:
            _bl = Text()
            _bl.append("  ▸ ", style=f"bold {_T}")
            _bl.append(f"{_n:<8}", style=f"dim {_DM}")
            _bl.append(_v, style=_W)
            _bl.append("  ✓", style="bold #5EE6A8")
            console.print(_bl)
            _time.sleep(0.04)
        console.print()

        # ── 2) Logo AUTOMYX con degradado verde→cian ──
        _rows = [
            "  ▄████████╗ ██╗   ██╗████████╗  ██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗",
            "  ██╔══════╝ ██║   ██║╚══██╔══╝ ██╔═══██╗████╗ ████║╚██╗ ██╔╝╚██╗██╔╝",
            "  ███████╗   ██║   ██║   ██║    ██║   ██║██╔████╔██║ ╚████╔╝  ╚███╔╝ ",
            "  ██╔════╝   ██║   ██║   ██║    ██║   ██║██║╚██╔╝██║  ╚██╔╝   ██╔██╗ ",
            "  ███████╗   ╚██████╔╝   ██║    ╚██████╔╝██║ ╚═╝ ██║   ██║   ██╔╝ ██╗",
            "  ╚══════╝    ╚═════╝    ╚═╝     ╚═════╝ ╚═╝     ╚═╝   ╚═╝   ╚═╝  ╚═╝",
        ]
        _logo = Text()
        for _i, _r in enumerate(_rows):
            _logo.append(_r + "\n", style=f"bold {_G[_i]}")
        console.print(_logo)

        # ── 3) Welcome card estilo Claude Code ──
        _cwd = _os.getcwd()
        if len(_cwd) > 46:
            _cwd = "…" + _cwd[-45:]
        _card = Text()
        _card.append("✻ ", style=f"bold {_T}")
        _card.append(f"Bienvenido a AUTOMYX", style=f"bold {_W}")
        _card.append(f"  v{version}\n\n", style=f"dim {_DM}")
        _card.append("  modelo      ", style=f"dim {_DM}")
        _card.append(f"{model_name or 'sin configurar'}", style=f"bold {_T}")
        if provider:
            _card.append(f"  ({provider})", style=f"dim {_DM}")
        _card.append("\n")
        _card.append("  directorio  ", style=f"dim {_DM}")
        _card.append(f"{_cwd}\n", style=_W)
        _card.append("  arsenal     ", style=f"dim {_DM}")
        _card.append(f"{tool_count} tools", style=_W)
        _card.append(" · ", style=f"dim {_DM}")
        _card.append(f"{skill_count} skills", style=_W)
        _card.append(" · ", style=f"dim {_DM}")
        _card.append(f"{agent_count + 6} agentes", style=_W)
        if channels:
            _card.append("\n")
            _card.append("  canales     ", style=f"dim {_DM}")
            _card.append(" · ".join(channels), style=_W)
        console.print(Panel(_card, border_style=f"dim {_T}", box=_rbox.ROUNDED,
                            padding=(1, 3), expand=False))

        # ── 4) Tips de arranque (una sola línea, como Claude Code) ──
        _tips = Text()
        _tips.append("  /help", style=f"bold {_T}")
        _tips.append(" comandos", style=f"dim {_DM}")
        _tips.append("   /model", style=f"bold {_T}")
        _tips.append(" cambiar modelo", style=f"dim {_DM}")
        _tips.append("   /tasks", style=f"bold {_T}")
        _tips.append(" tareas", style=f"dim {_DM}")
        _tips.append("   !", style=f"bold {_T}")
        _tips.append(" shell directo", style=f"dim {_DM}")
        console.print(_tips)
        console.print()

        if not show_details:
            return

        # ── 5) Promo Vyrex GPT (compacta, identidad Nexora) ──
        _pm = Text()
        _pm.append("⚡ ", style="bold #FFD700")
        _pm.append("Vyrex GPT", style=f"bold {_T}")
        _pm.append(" — motor propio de Nexora · recarga en ", style=f"dim {_DM}")
        _pm.append("vyrexstudio.com", style=f"bold {_W}")
        _pm.append(" · precios ridículos vs Claude/GPT", style=f"dim {_DM}")
        console.print(_pm)
        console.print()

    except Exception as e:
        print(ASCII_LOGO)
        print(f"AUTOMYX v{version} - {model_name}")
        print(f"Tools: {tool_count} | Skills: {skill_count}")
        print(f"Error decorando banner: {e}")


def print_startup_sequence() -> None:
    """Secuencia de arranque rápida (boot)."""
    _banner_compact_fallback = lambda: print(f"{ASCII_LOGO_MINI}")
    if RICH_AVAILABLE and console:
        from rich.text import Text
        t = Text()
        t.append("AUTOMYX", style=f"bold {BRAND_CYAN}")
        t.append(" iniciando", style=BRAND_GRAY)
        console.print(t)
    else:
        print("AUTOMYX iniciando")


if __name__ == "__main__":
    print_automyx_banner(
        model_name="openai/gpt-oss-120b",
        show_details=True,
        version="2.5.0",
        provider="nvidia",
        agent_count=1,
        skill_count=18,
        tool_count=275,
        channels=["web", "telegram"],
    )
