"""
Automyx 2.5 — Shared UI Design System
======================================
Glassmorphism electric-blue palette + helpers used everywhere
(`core.onboard`, `core.terminal`, `core.onboard_pro`, `automix.py`).

Brand colors are owned by Automyx — do not copy from other projects.
"""
from __future__ import annotations

import os
import sys

# Lazy import for Rich (avoid hard crash in headless envs)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.tree import Tree
    from rich.layout import Layout
    from rich import box as rich_box
    from rich.align import Align
    from rich.columns import Columns
    from rich.rule import Rule
    from rich.padding import Padding
    from rich.status import Status
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn, TextColumn,
        TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn,
    )
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = Panel = Text = Table = Tree = Layout = None
    rich_box = None
    Align = Columns = Rule = Padding = Status = None
    Progress = SpinnerColumn = BarColumn = TextColumn = None
    TimeElapsedColumn = TimeRemainingColumn = MofNCompleteColumn = None

# Lazy import for questionary
try:
    import questionary
    from questionary import Choice, Separator
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False
    questionary = None
    Choice = Separator = None

# Lazy import for colorama (used in plain text fallback)
try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    Fore = Style = None
    def _colorama_init(*a, **k): pass


# ============================================================================
# Brand Palette — Electric Blue Glassmorphism
# ============================================================================
# This is Automyx's own visual identity. Deep navy backgrounds, electric
# blue panels, cyan accents, soft glow text. NOT a copy of OpenClaw or any
# other project.

NAVY         = "#0A1A2F"
DEEP_BLUE    = "#0B2545"
BLUE         = "#1E5FBE"
ELECTRIC     = "#00AAFF"
CYAN         = "#00E5FF"
GLOW         = "#7BD5FF"
WHITE        = "#E6F2FF"
GRAY         = "#6A89B5"
DIM          = "#3A5070"
WARN         = "#FFB347"
OK           = "#5EE6A8"
ERR          = "#FF6B7A"
PURPLE       = "#9B6BFF"

# Materialized console (shared by every UI surface)
console: "Console | None" = Console() if RICH_AVAILABLE else None


# ============================================================================
# Banner
# ============================================================================
AUTOMYX_BANNER = """\
[bold {e}]    ▄▄▄       █    ██ ▄▄▄█████▓ ▒█████   ███▄    █  ██▓▓█████  ▒██   ██▒[/]
[bold {e}]   ▒████▄     ██  ▓██▒▓  ██▒ ▓▒▒██▒  ██▒ ██ ▀█   █ ▓██▒▓█   ▀  ▒▒ █ █ ▒░[/]
[bold {e}]   ▒██  ▀█▄  ▓██  ▒██░▒ ▓██░ ▒░▒██░  ██▒▓██  ▀█ ██▒▒██░▒███    ░░  █   ░[/]
[bold {e}]   ░██▄▄▄▄██ ▓▓█  ░██░░ ▓██▓ ░ ▒██   ██░▓██▒  ▐▌██▒▒██░▒▓█  ▄   ░ █ █ ▒[/]
[bold {e}]    ▓█   ▓██▒▒▒█████▓   ▒██▒ ░ ░ ████▓▒░▒██░   ▓██░░██████▒▒ ▒██▒ ▒██▒[/]
[bold {e}]    ▒▒   ▓▒█░░▒▓▒ ▒ ▒   ▒ ░░   ░ ▒░▒░▒░ ░ ▒░   ▒ ▒ ░ ▒░▓  ░  ▒▒ ░ ░▓ ░[/]"""


def show_banner(subtitle: str = "Core 2.5 · The Intent-Aware Engine", clear: bool = True):
    """Print the Automyx banner + brand subtitle. Clears the screen first."""
    if clear and RICH_AVAILABLE and console is not None:
        os.system("cls" if os.name == "nt" else "clear")
    if RICH_AVAILABLE and console is not None:
        console.print(AUTOMYX_BANNER.format(e=ELECTRIC))
        # NOTE: Use Text() objects to avoid Rich's closing-tag mismatch with
        # hex colors in the form [bold #00AAFF]... [/#00AAFF].
        from rich.text import Text as _T
        line = _T()
        line.append("· ", style=f"bold {ELECTRIC}")
        line.append(subtitle, style=GLOW)
        line.append("  ·  Powered by Nexora Technology LLC", style=GRAY)
        console.print(Align.center(line))
        console.print("")
    else:
        print("AUTOMYX 2.5  ·  Core 2.5  ·  The Intent-Aware Engine")


# ============================================================================
# Step header & progress bar
# ============================================================================
def show_step_header(step: int, total: int, title: str, subtitle: str = ""):
    """Render a glassmorphism step header with progress bar."""
    if not RICH_AVAILABLE or console is None:
        print(f"\n--- STEP {step}/{total}: {title} ---")
        if subtitle:
            print(f"    {subtitle}")
        return
    bar_len = 30
    filled = int(bar_len * step / total)
    bar_char = "█"
    empty_char = "░"
    bar = bar_char * filled + empty_char * (bar_len - filled)
    console.print(
        f"\n[{ELECTRIC}]┌─ STEP {step}/{total} ─────────────────────────────────────────────┐[/{ELECTRIC}]"
    )
    console.print(
        f"[{ELECTRIC}]│[/{ELECTRIC}]  [{WHITE}]{bar}[/{WHITE}]  "
        f"[bold {CYAN}]{title}[/bold {CYAN}]"
    )
    if subtitle:
        console.print(
            f"[{ELECTRIC}]│[/{ELECTRIC}]  [{GRAY}]{subtitle}[/{GRAY}]"
        )
    console.print(
        f"[{ELECTRIC}]└──────────────────────────────────────────────────────────────────┘[/{ELECTRIC}]\n"
    )


# ============================================================================
# Glassmorphism panel
# ============================================================================
def glass_panel(
    title: str,
    body: str,
    accent: str = ELECTRIC,
    subtitle: str = "",
    width: int | None = None,
):
    """A glassmorphism-styled panel with brand colors. Parses Rich markup in body."""
    if not RICH_AVAILABLE or console is None:
        print(f"\n=== {title} ===")
        print(body)
        return
    # Append subtitle as a separate paragraph (gray) — markup in body is parsed.
    if subtitle:
        body = f"{body}\n\n[{GRAY}]{subtitle}[/{GRAY}]"
    p = Panel(
        body,
        title=title,
        border_style=accent,
        box=rich_box.DOUBLE_EDGE if accent == ELECTRIC else rich_box.ROUNDED,
        padding=(1, 3),
        style=f"on {DEEP_BLUE}",
        width=width,
    )
    # The Panel's `renderable` can be a string; Rich will parse it for markup.
    console.print(p)


# ============================================================================
# Status helpers (OK, info, warn, error)
# ============================================================================
# NOTE: We use plain `print()` with colorama ANSI codes for the status helpers.
# This is the most robust approach — it works in all terminals, never tries to
# parse markup, and never crashes on messages that contain literal `[...]`
# sequences (which is a real risk for error messages from Rich/argparse).
def _safe_print(ansi_color: str, icon: str, msg: str):
    msg = str(msg) if msg is not None else ""
    if COLORAMA_AVAILABLE:
        try:
            print(f"{ansi_color}{icon} {msg}{Style.RESET_ALL}")
        except Exception:
            print(f"{icon} {msg}")
    else:
        try:
            print(f"{icon} {msg}")
        except Exception:
            pass


def ok(msg: str):
    _safe_print(Fore.GREEN if COLORAMA_AVAILABLE else "", "✓", msg)


def info(msg: str):
    _safe_print(Fore.CYAN if COLORAMA_AVAILABLE else "", "ℹ", msg)


def warn(msg: str):
    _safe_print(Fore.YELLOW if COLORAMA_AVAILABLE else "", "⚠", msg)


def err(msg: str):
    _safe_print(Fore.RED if COLORAMA_AVAILABLE else "", "✗", msg)


def section(title: str):
    """Horizontal rule with a title — section divider."""
    if RICH_AVAILABLE and console is not None:
        console.print(Rule(f"[bold {CYAN}]{title}[/]", style=ELECTRIC))
    else:
        print(f"\n=== {title} ===")


# ============================================================================
# questionary style (electric blue / cyan)
# ============================================================================
def automyx_style():
    """The questionary style object matching the brand."""
    if not QUESTIONARY_AVAILABLE:
        return None
    return questionary.Style([
        ("qmark",              f"fg:{ELECTRIC} bold"),
        ("question",           f"fg:{WHITE} bold"),
        ("answer",             f"fg:{CYAN} bold"),
        ("pointer",            f"fg:{CYAN} bold"),
        ("highlighted",        f"fg:{CYAN} bold"),
        ("selected",           f"fg:{ELECTRIC}"),
        ("separator",          f"fg:{BLUE} bold"),
        ("instruction",        f"fg:{GRAY}"),
        ("text",               f"fg:{WHITE}"),
        ("disabled",           f"fg:{GRAY} italic"),
        ("checkbox",           f"fg:{CYAN} bold"),
        ("checkbox-selected",  f"fg:{ELECTRIC} bold"),
    ])


# ============================================================================
# Tables
# ============================================================================
def skill_table(rows, title: str = None):
    """Render a table of skills (name, category, tools)."""
    if not RICH_AVAILABLE or console is None:
        for r in rows:
            print(r)
        return
    t = Table(
        title=title,
        box=rich_box.ROUNDED,
        border_style=BLUE,
        title_justify="left",
        header_style=f"bold {CYAN}",
    )
    t.add_column("Category", style=CYAN, no_wrap=True)
    t.add_column("Skills", style=WHITE)
    t.add_column("Tools", style=GLOW, justify="right")
    for cat, names, n_tools in rows:
        t.add_row(cat, names, str(n_tools))
    console.print(t)


# ============================================================================
# File save helpers (shared with onboard.py)
# ============================================================================
def save_to_env(key: str, value: str):
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    with open(env_path, "w", encoding="utf-8") as f:
        key_found = False
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                key_found = True
            else:
                f.write(line)
        if not key_found:
            f.write(f"{key}={value}\n")


# ============================================================================
# Version
# ============================================================================
AUTOMYX_VERSION = "2.5.0"
AUTOMYX_CODENAME = "Intent-Aware"
