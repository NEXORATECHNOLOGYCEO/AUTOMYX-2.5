#!/usr/bin/env python3
"""
AUTONOMY 2.5 - Terminal-First AI Agent
======================================
The most autonomous AI agent ever created.
Claude Code-style terminal interface with quiet mode by default.
"""
from __future__ import annotations

import os
import sys
import json

# Force UTF-8 encoding to avoid Windows cp1252 issues with Rich
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from pathlib import Path

# Make repo root importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Apply quiet mode BEFORE importing anything else
os.environ.setdefault("AUTOMYX_QUIET", "1")
os.environ.setdefault("AUTOMYX_VERBOSE", "0")

try:
    from core import quiet as _quiet_module
    _quiet_module.quiet()
except Exception:
    pass

# Rich imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.rule import Rule
    from rich.columns import Columns
    from rich.box import ROUNDED, DOUBLE, SIMPLE
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

try:
    from core.ui import (
        ELECTRIC, CYAN, GLOW, WHITE, GRAY, DIM,
        OK, WARN, ERR, BLUE, NAVY, PURPLE,
        AUTOMYX_VERSION as _V
    )
    AUTOMYX_VERSION = "2.5.0"
    AUTOMYX_CODENAME = "Intent-Aware"
except Exception:
    ELECTRIC = "#00AAFF"
    CYAN = "#00E5FF"
    GLOW = "#7BD5FF"
    WHITE = "#E6F2FF"
    GRAY = "#6A89B5"
    DIM = "#3A5070"
    OK = "#5EE6A8"
    WARN = "#FFB347"
    ERR = "#FF6B7A"
    PURPLE = "#9B6BFF"
    AUTOMYX_VERSION = "2.5.0"
    AUTOMYX_CODENAME = "Intent-Aware"


AUTOMYX_TAGLINE = "The Autonomous AI Agent"


# ============================================================================
# FIRST-TIME SETUP
# ============================================================================
def first_time_setup(console):
    config_file = Path(".automyx") / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                saved_model = config.get("model")
                if saved_model:
                    return saved_model
        except Exception:
            pass

    from core.model_selector import ModelSelector
    selector = ModelSelector(console=console)
    model = selector.ask()

    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump({
                "model": model,
                "version": AUTOMYX_VERSION,
                "first_run": False
            }, f, indent=2)
    except Exception:
        pass

    return model


# ============================================================================
# BEAUTIFUL WELCOME / ONBOARDING — Elite redesign
# ============================================================================
def print_welcome(console, model: str):
    """Onboarding espectacular estilo Claude Code con identidad Automyx."""
    console.clear()

    from rich.columns import Columns
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    from rich.rule import Rule
    from rich.table import Table
    from rich.box import ROUNDED, SIMPLE, MINIMAL

    ORANGE = "#FF8C00"
    RED    = "#FF3333"
    BLUE   = "#00AAFF"
    CYAN   = "#00E5FF"
    WHITE  = "#F0F6FF"
    DIM    = "#5A7090"
    GLOW   = "#7BD5FF"
    OK     = "#5EE6A8"

    # ── ASCII Logo ─────────────────────────────────────────────────────────
    logo_lines = [
        ("  ░█████╗░██╗░░░██╗████████╗░█████╗░███╗░░░███╗██╗░░░██╗██╗░░██╗", ORANGE),
        ("  ██╔══██╗██║░░░██║╚══██╔══╝██╔══██╗████╗░████║╚██╗░██╔╝╚██╗██╔╝", ORANGE),
        ("  ███████║██║░░░██║░░░██║░░░██║░░██║██╔████╔██║░╚████╔╝░░╚███╔╝░", RED),
        ("  ██╔══██║██║░░░██║░░░██║░░░██║░░██║██║╚██╔╝██║░░╚██╔╝░░░██╔██╗░", RED),
        ("  ██║░░██║╚██████╔╝░░░██║░░░╚█████╔╝██║░╚═╝░██║░░░██║░░░██╔╝╚██╗", BLUE),
        ("  ╚═╝░░╚═╝░╚═════╝░░░╚═╝░░░░╚════╝░╚═╝░░░░░╚═╝░░░╚═╝░░░╚═╝░░╚═╝", BLUE),
    ]

    logo_text = Text()
    logo_text.append("\n")
    for line, color in logo_lines:
        logo_text.append(f"{line}\n", style=f"bold {color}")

    subtitle = Text()
    subtitle.append(f"\n  v{AUTOMYX_VERSION}", style=f"bold {ORANGE}")
    subtitle.append(f"  {AUTOMYX_CODENAME}", style=DIM)
    subtitle.append(f"  ·  {AUTOMYX_TAGLINE}\n", style=DIM)

    console.print(Rule(style=BLUE))
    console.print(logo_text)
    console.print(subtitle)
    console.print(Rule(style=BLUE))
    console.print()

    # ── Two-column info + tips ─────────────────────────────────────────────
    left = Text()
    left.append("  Estado del sistema\n\n", style=f"bold {CYAN}")

    model_short = model.split("/")[-1] if "/" in model else model
    left.append("  Modelo     ", style=DIM)
    left.append(f"{model_short}\n", style=f"bold {WHITE}")

    left.append("  Versión    ", style=DIM)
    left.append(f"Automyx {AUTOMYX_VERSION}\n", style=WHITE)

    cwd = str(Path.cwd())
    if len(cwd) > 40:
        cwd = "…" + cwd[-38:]
    left.append("  Directorio ", style=DIM)
    left.append(f"{cwd}\n", style=WHITE)

    left.append("\n")
    left.append("  Capacidades\n\n", style=f"bold {CYAN}")
    caps = [
        ("⟩", "Ejecuta código, archivos, comandos"),
        ("⟩", "Busca en la web en tiempo real"),
        ("⟩", "Edición de video e imagen"),
        ("⟩", "Multi-agente con planes paralelos"),
        ("⟩", "Auto-aprendizaje y memoria"),
    ]
    for icon, cap in caps:
        left.append(f"  {icon} ", style=f"bold {ORANGE}")
        left.append(f"{cap}\n", style=DIM)

    right = Text()
    right.append("  Primeros pasos\n\n", style=f"bold {CYAN}")
    tips = [
        ("Escribe",    "cualquier tarea en lenguaje natural"),
        ("!comando",   "ejecuta un comando de shell directo"),
        ("/help",      "muestra todos los comandos"),
        ("/model",     "cambia el modelo de IA"),
        ("/auto",      "modo totalmente autónomo"),
        ("/parallel",  "ejecución multi-agente paralela"),
        ("/skill",     "forja una nueva habilidad"),
        ("/init",      "crea AUTOMYX.md en este directorio"),
    ]
    for cmd, desc in tips:
        right.append(f"  {cmd:<12}", style=f"bold {BLUE}")
        right.append(f" {desc}\n", style=DIM)

    right.append("\n")
    right.append("  Ejemplos rápidos\n\n", style=f"bold {CYAN}")
    examples = [
        "crea una carpeta 'proyectos' en el escritorio",
        "busca en Google las últimas noticias de IA",
        "lee el archivo config.py y explícame qué hace",
        "ejecuta pip install rich y dime el resultado",
    ]
    for ex in examples:
        right.append(f"  › ", style=f"bold {ORANGE}")
        right.append(f"{ex}\n", style=WHITE)

    console.print(Columns([left, right], equal=True, expand=True))
    console.print()
    console.print(Rule(style=DIM))
    console.print(
        f"  [{DIM}]Listo. Escribe una tarea o [/][bold {WHITE}]?[/][{DIM}] para ayuda.[/{DIM}]"
    )
    console.print()


# ============================================================================
# MAIN
# ============================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='AUTONOMY 2.5 - Fully Autonomous AI Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  automyx                          Start AUTONOMY REPL (first-time: model selection)
  automyx --model gpt-oss-120b    Use specific model
  automyx --verbose               Enable verbose output (show internal logs)
  automyx --reset                 Reset model selection
        """
    )
    parser.add_argument('--model', '-m', help='Model to use (skips first-time selection)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show internal logs')
    parser.add_argument('--version', '-V', action='store_true', help='Show version')
    parser.add_argument('--reset', action='store_true', help='Reset model selection')
    parser.add_argument('--show-models', action='store_true', help='Show model selection screen')
    args = parser.parse_args()

    if args.version:
        print(f"AUTONOMY {AUTOMYX_VERSION} ({AUTOMYX_CODENAME})")
        sys.exit(0)

    if not RICH_AVAILABLE or not Console:
        print("Error: rich library not available. Install with: pip install rich")
        sys.exit(1)

    console = Console(force_terminal=True, legacy_windows=False, safe_box=False)

    # Apply verbose flag if requested
    if args.verbose:
        os.environ["AUTOMYX_VERBOSE"] = "1"
        os.environ["AUTOMYX_QUIET"] = "0"
        _quiet_module.verbose()
    else:
        _quiet_module.quiet()

    # --show-models
    if args.show_models:
        from core.model_selector import ModelSelector
        selector = ModelSelector(console=console)
        selector.display()
        return

    # --reset
    if args.reset:
        config_file = Path(".automyx") / "config.json"
        if config_file.exists():
            config_file.unlink()
            console.print(f"[{OK}][OK][/] Model selection reset.")
        else:
            console.print(f"[{DIM}]No saved configuration to reset.[/{DIM}]")
        return

    # First-time setup
    if args.model:
        selected_model = args.model
    else:
        config_file = Path(".automyx") / "config.json"
        if config_file.exists() and not os.environ.get("AUTOMYX_FORCE_MODEL_SELECT"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    saved_model = config.get("model")
                    if saved_model:
                        selected_model = saved_model
                    else:
                        selected_model = first_time_setup(console)
            except Exception:
                selected_model = first_time_setup(console)
        else:
            selected_model = first_time_setup(console)

    os.environ['AUTOMYX_MODEL'] = selected_model

    # Print the beautiful welcome
    print_welcome(console, selected_model)

    # Start the REPL
    from core.repl import AutomyxREPL
    repl = AutomyxREPL(model=selected_model, verbose=args.verbose)
    repl.start()


if __name__ == '__main__':
    main()
