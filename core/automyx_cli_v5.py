"""
AUTOMYX CLI v5.0 — Hacker Terminal
====================================
Entry-point alternativo al REPL.  Misma paleta visual que onboard_pro_v5.
Conecta Notion, GitHub, Telegram, Discord en el arranque y los expone al agente.
"""
from __future__ import annotations

import os
import sys
import json
import time
import signal
import shutil
import threading
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── carga .env antes de cualquier import de Automyx ─────────────────────────
def _load_dotenv() -> None:
    p = Path(__file__).parent.parent / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k and k not in os.environ:
            os.environ[k] = v

_load_dotenv()

# ── Rich ─────────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.rule import Rule
    from rich.prompt import Prompt, Confirm
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.columns import Columns
    from rich.markdown import Markdown
    from rich import box as _rbox
    RICH = True
except ImportError:
    RICH = False
    Console = None  # type: ignore

# ── paleta (idéntica a onboard_pro_v5) ───────────────────────────────────────
O  = "#00D4AA"   # teal-green (brand)
B  = "#00AAFF"   # azul
G  = "#5EE6A8"   # verde
R  = "#FF4444"   # rojo
DM = "#4A6A8A"   # gris azul
W  = "#F0F6FF"   # blanco cálido
PU = "#A855F7"   # púrpura
YL = "#FFD700"   # dorado

VERSION = "2.5.0"

# ── modelos disponibles (sincronizados con onboard_pro_v5) ───────────────────
MODELS: Dict[str, List[Tuple[str, str]]] = {
    "NVIDIA NIM  [FREE]": [
        ("openai/gpt-oss-120b",                "GPT-OSS 120B       · open-weights · coding ★"),
        ("nvidia/nemotron-3-super-120b-a12b",  "Nemotron Super 120B· thinking mode · razonamiento ★"),
        ("minimaxai/minimax-m3",               "MiniMax M3         · multimodal · fast"),
        ("minimaxai/minimax-m2.7",             "MiniMax M2.7       · ultra-fast"),
        ("moonshotai/kimi-k2.6",               "Kimi K2.6          · 256K context"),
        ("meta/llama-3.3-70b-instruct",        "Llama 3.3 70B      · general"),
        ("nvidia/llama-3.1-nemotron-70b-instruct", "Nemotron 70B   · razonamiento"),
        ("mistralai/mistral-large-2-instruct", "Mistral Large 2    · via NVIDIA"),
    ],
    "Anthropic   [PAID]": [
        ("claude-sonnet-4-5",          "Claude Sonnet 4.5  · best balance ★"),
        ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet  · proven"),
        ("claude-3-5-haiku-20241022",  "Claude 3.5 Haiku   · fast & cheap"),
        ("claude-3-opus-20240229",     "Claude 3 Opus      · most capable"),
    ],
    "OpenAI      [PAID]": [
        ("gpt-4o",      "GPT-4o       · multimodal ★"),
        ("gpt-4o-mini", "GPT-4o Mini  · fast & cheap"),
        ("o1-mini",     "o1-mini      · reasoning"),
        ("gpt-4-turbo", "GPT-4 Turbo"),
    ],
    "Ollama      [LOCAL]": [
        ("llama3.1:8b",      "Llama 3.1 8B  · 5GB RAM"),
        ("llama3.1:70b",     "Llama 3.1 70B · 40GB RAM"),
        ("mistral:latest",   "Mistral 7B"),
        ("codellama:latest", "CodeLlama"),
        ("phi3:latest",      "Phi-3  · ultra-ligero"),
    ],
}

# ── integraciones (misma lista que onboard_pro_v5) ───────────────────────────
INTEGRATIONS: Dict[str, Dict[str, str]] = {
    "notion":      {"env": "NOTION_API_KEY",      "icon": "📓", "label": "Notion"},
    "github":      {"env": "GITHUB_TOKEN",         "icon": "🐙", "label": "GitHub"},
    "telegram":    {"env": "TELEGRAM_BOT_TOKEN",   "icon": "✈️",  "label": "Telegram"},
    "discord":     {"env": "DISCORD_BOT_TOKEN",    "icon": "🎮", "label": "Discord"},
    "elevenlabs":  {"env": "ELEVENLABS_API_KEY",   "icon": "🔊", "label": "ElevenLabs"},
    "openweather": {"env": "OPENWEATHER_API_KEY",  "icon": "🌤️",  "label": "OpenWeather"},
}


# ─────────────────────────────────────────────────────────────────────────────
# Consola
# ─────────────────────────────────────────────────────────────────────────────
def _make_console() -> Optional[Console]:
    if not RICH:
        return None
    try:
        from core.ui import console as _shared
        if _shared is not None:
            return _shared
    except Exception:
        pass
    return Console()


# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────
def _banner(console: Console) -> None:
    console.clear()

    # ── Boot probes (identidad hacker, rapidos) ─────────────────────────────
    import platform as _plat
    import time as _time
    _T  = "#00D4AA"
    _GR = ["#00FFB2", "#00F2C8", "#00E0DC", "#00CCEE", "#00B8FF", "#3D9EFF"]
    console.print()
    for _n, _v in [
        ("sys",    f"{_plat.system().lower()} {_plat.release()}"),
        ("python", _plat.python_version()),
        ("engine", f"automyx core v{VERSION}"),
    ]:
        _bl = Text()
        _bl.append("  ▸ ", style=f"bold {_T}")
        _bl.append(f"{_n:<8}", style=f"dim {DM}")
        _bl.append(_v, style=W)
        _bl.append("  ✓", style=f"bold {G}")
        console.print(_bl)
        _time.sleep(0.04)
    console.print()

    # ── Logo AUTOMYX mini (SaaS-clean, 2 líneas, degradado) ─────────────────
    art = Text()
    art.append("\n")
    art.append("  ▄▀█ █░█ ▀█▀ █▀█ █▀▄▀█ █▄█ ▀▄▀", style=f"bold {_GR[0]}")
    art.append(f"   v{VERSION}\n", style=f"dim {DM}")
    art.append("  █▀█ █▄█ ░█░ █▄█ █░▀░█ ░█░ █░█", style=f"bold {_GR[4]}")
    art.append("   🐋 autonomous ai agent · nexora\n", style=f"dim {DM}")
    console.print(art)


def _rule(console: Console, title: str = "", color: str = "") -> None:
    c = color or B
    console.print(Rule(f"[bold {c}]{title}[/]", style=f"dim {c}"))


# ─────────────────────────────────────────────────────────────────────────────
# Pantalla de bienvenida (reemplaza la antigua roja)
# ─────────────────────────────────────────────────────────────────────────────
def print_welcome(console: Console, model: str, integrations_on: List[str]) -> None:
    _banner(console)

    cwd  = str(Path.cwd())
    if len(cwd) > 44:
        cwd = "…" + cwd[-43:]
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"

    ws_name = "default"
    try:
        from core.workspace import get_workspace_manager
        ws_name = get_workspace_manager().current_name
    except Exception:
        pass

    _T = "#00D4AA"
    card = Text()
    card.append("✻ ", style=f"bold {_T}")
    card.append(f"Bienvenido, {user}", style=f"bold {W}")
    card.append("\n\n")
    card.append("  modelo         ", style=f"dim {DM}")
    card.append(f"{model}\n", style=f"bold {_T}")
    card.append("  workspace      ", style=f"dim {DM}")
    card.append(f"{ws_name}\n", style=W)
    card.append("  integraciones  ", style=f"dim {DM}")
    if integrations_on:
        _parts = []
        for name in integrations_on:
            meta = INTEGRATIONS.get(name, {})
            _parts.append(f"{meta.get('icon','·')} {meta.get('label', name)}")
        card.append(" · ".join(_parts) + "\n", style=W)
    else:
        card.append("ninguna — usa /onboard\n", style=f"dim {DM}")
    card.append("  directorio     ", style=f"dim {DM}")
    card.append(cwd, style=W)

    console.print(Panel(card, border_style=f"dim {_T}", box=_rbox.ROUNDED,
                        padding=(1, 3), expand=False))

    tips = Text()
    tips.append("  /help", style=f"bold {_T}")
    tips.append(" comandos", style=f"dim {DM}")
    tips.append("   /model", style=f"bold {_T}")
    tips.append(" cambiar", style=f"dim {DM}")
    tips.append("   /tokens", style=f"bold {_T}")
    tips.append(" costos", style=f"dim {DM}")
    tips.append("   /onboard", style=f"bold {_T}")
    tips.append(" configurar", style=f"dim {DM}")
    tips.append("   !", style=f"bold {_T}")
    tips.append(" shell", style=f"dim {DM}")
    console.print(tips)
    console.print()


def select_model(console: Console, current: str = "") -> str:
    _banner(console)
    _rule(console, "SELECCIÓN DE MODELO", B)
    console.print()

    flat: List[Tuple[str, str, str]] = []   # (provider_label, model_id, notes)

    for prov_label, models in MODELS.items():
        tbl = Table(
            box=_rbox.SIMPLE_HEAD,
            border_style=f"dim {B}",
            show_header=True,
            header_style=f"bold {O}",
            padding=(0, 2),
        )
        tbl.add_column("#",       style=f"bold {O}", width=4, justify="right")
        tbl.add_column("Modelo",  style=f"bold {W}", width=40)
        tbl.add_column("Notas",   style=DM,           max_width=38)
        console.print(f"  [{B}]{prov_label}[/{B}]")
        for model_id, notes in models:
            n = len(flat) + 1
            is_cur = model_id == current
            star    = "★" in notes
            m_txt   = Text(model_id, style=f"bold {O}" if star else W)
            if is_cur:
                m_txt.append("  ← actual", style=f"dim {G}")
            tbl.add_row(str(n), m_txt, notes.replace(" ★", ""))
            flat.append((prov_label, model_id, notes))
        console.print(tbl)
        console.print()

    custom_n = len(flat) + 1
    console.print(f"  [{DM}]{custom_n}.[/{DM}] [{W}]Modelo personalizado[/{W}]")
    console.print(f"  [{DM}]0.[/{DM}]  [{DM}]Cancelar[/{DM}]")
    console.print()

    raw = Prompt.ask(
        f"  [{O}]Opción[/{O}] [{DM}](0 = cancelar)[/{DM}]",
        default="0",
    )
    try:
        idx = int(raw.strip())
    except ValueError:
        return current

    if idx == 0:
        return current
    if 1 <= idx <= len(flat):
        return flat[idx - 1][1]
    if idx == custom_n:
        return Prompt.ask(f"  [{O}]Nombre del modelo[/{O}]").strip() or current
    return current


# ─────────────────────────────────────────────────────────────────────────────
# Panel de integraciones (status en tiempo real)
# ─────────────────────────────────────────────────────────────────────────────
def _intg_status_table(console: Console) -> None:
    tbl = Table(
        box=_rbox.SIMPLE_HEAD,
        border_style=f"dim {B}",
        show_header=True,
        header_style=f"bold {O}",
        padding=(0, 2),
    )
    tbl.add_column("Integración", style=f"bold {W}", width=16)
    tbl.add_column("Variable",    style=DM,          width=26)
    tbl.add_column("Estado",      justify="center",  width=16)
    tbl.add_column("Herramientas registradas", style=DM, max_width=40)

    tool_map = {
        "notion":      "notion_search, notion_get_page, notion_create_page, notion_append_blocks",
        "github":      "github_list_repos, github_list_prs, github_create_issue, github_get_commits",
        "telegram":    "— (lanzar bot externo)",
        "discord":     "— (lanzar bot externo)",
        "elevenlabs":  "— (TTS via requests)",
        "openweather": "— (clima via requests)",
    }

    for key, meta in INTEGRATIONS.items():
        val = os.environ.get(meta["env"], "").strip()
        if val:
            st = Text("✓  activo", style=f"bold {G}")
        else:
            st = Text("✗  falta",  style=f"dim {DM}")
        tbl.add_row(
            f"{meta['icon']}  {meta['label']}",
            meta["env"],
            st,
            tool_map.get(key, ""),
        )

    console.print(tbl)


# ─────────────────────────────────────────────────────────────────────────────
# Wiring de integraciones → agente
# ─────────────────────────────────────────────────────────────────────────────

def _wire_notion(agent: Any) -> int:
    """Conecta tools de Notion al agente usando tools/notion_tools.py."""
    key = os.environ.get("NOTION_API_KEY", "").strip()
    if not key:
        return 0
    added = 0
    try:
        from tools.notion_tools import NotionTools as NT, search, get_page, get_page_content, \
            get_database, create_page, update_page, append_blocks, delete_page, md_to_blocks

        tool_defs: List[Tuple[str, Any]] = [
            ("notion_search",       search),
            ("notion_get_page",     get_page),
            ("notion_get_content",  get_page_content),
            ("notion_get_database", get_database),
            ("notion_create_page",  create_page),
            ("notion_update_page",  update_page),
            ("notion_append_md",    lambda **kw: append_blocks(
                kw.get("page_id") or kw.get("id") or "",
                md_to_blocks(kw.get("markdown") or kw.get("content") or kw.get("text") or "")
            )),
            ("notion_delete_page",  delete_page),
            ("notion_set_token",    NT.set_token),
        ]
        for name, fn in tool_defs:
            if name not in agent.tools:
                agent.register_tool(name, fn)
                added += 1
    except Exception:
        try:
            from core.onboard_pro_v5 import inject_notion_into_agent
            added = inject_notion_into_agent(agent)
        except Exception:
            pass
    return added


def _wire_github(agent: Any) -> int:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return 0
    added = 0
    try:
        from core.github_agent import get_github
        gh = get_github(token=token)
        tool_defs: List[Tuple[str, Any]] = [
            ("github_list_repos",    gh.list_repos),
            ("github_get_repo_info", gh.get_repo_info),
            ("github_list_prs",      gh.list_prs),
            ("github_get_pr_diff",   gh.get_pr_diff),
            ("github_create_pr",     gh.create_pr),
            ("github_add_pr_comment",gh.add_pr_comment),
            ("github_list_issues",   gh.list_issues),
            ("github_create_issue",  gh.create_issue),
            ("github_close_issue",   gh.close_issue),
            ("github_get_file",      gh.get_file_content),
            ("github_get_commits",   gh.get_commits),
        ]
        for name, fn in tool_defs:
            if name not in agent.tools:
                agent.register_tool(name, fn)
                added += 1
    except Exception:
        pass
    return added


def _wire_weather(agent: Any) -> int:
    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not key:
        return 0

    def get_weather(city: str, units: str = "metric") -> Dict[str, Any]:
        try:
            import urllib.request
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&units={units}&appid={key}&lang=es"
            )
            with urllib.request.urlopen(url, timeout=10) as r:
                d = json.loads(r.read())
            return {
                "ok":         True,
                "city":       d.get("name"),
                "temp":       d["main"]["temp"],
                "feels_like": d["main"]["feels_like"],
                "humidity":   d["main"]["humidity"],
                "description":d["weather"][0]["description"],
                "wind_kph":   round(d["wind"]["speed"] * 3.6, 1),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    added = 0
    if "get_weather" not in agent.tools:
        agent.register_tool("get_weather", get_weather)
        added = 1
    return added


def _wire_elevenlabs(agent: Any) -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        return 0

    def tts_speak(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL", output: str = "speech.mp3") -> Dict[str, Any]:
        try:
            import urllib.request
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            body = json.dumps({
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            }).encode()
            req = urllib.request.Request(
                url, data=body,
                headers={"xi-api-key": key, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                Path(output).write_bytes(r.read())
            return {"ok": True, "file": output}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    added = 0
    if "tts_speak" not in agent.tools:
        agent.register_tool("tts_speak", tts_speak)
        added = 1
    return added


def wire_all_integrations(agent: Any, console: Optional[Console] = None) -> Dict[str, int]:
    results: Dict[str, int] = {}

    def _add(name: str, fn: Any) -> None:
        n = fn(agent)
        results[name] = n
        if console and n:
            console.print(
                f"  [dim #3a5a80]⎿ [/][dim #6888A8]{INTEGRATIONS[name]['icon']} "
                f"{INTEGRATIONS[name]['label'].lower()} · {n} tools[/] [bold {G}]✓[/]"
            )

    _add("notion",      _wire_notion)
    _add("github",      _wire_github)
    _add("openweather", _wire_weather)
    _add("elevenlabs",  _wire_elevenlabs)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Pantalla de ayuda
# ─────────────────────────────────────────────────────────────────────────────
def print_help(console: Console) -> None:
    _banner(console)
    _rule(console, "AYUDA — COMANDOS", O)
    console.print()

    sections = [
        ("Agente", [
            ("/model",             "cambiar modelo de IA en caliente"),
            ("/tokens",            "ver tokens y costo de la sesión"),
            ("/audit",             "log de auditoría de herramientas"),
            ("/workspace [cmd]",   "create · switch · list · delete"),
            ("/scan [dir]",        "escaneo de seguridad estático"),
            ("/integrations",      "ver estado de todas las integraciones"),
        ]),
        ("Sesión", [
            ("/clear",             "limpiar historial de conversación"),
            ("/history",           "ver historial de la sesión"),
            ("/save [archivo]",    "guardar conversación a .md"),
            ("/onboard",           "volver al wizard de configuración"),
            ("/exit  · Ctrl+C",    "salir guardando sesión"),
        ]),
        ("Notion", [
            ("busca en notion ...",        "notion_search"),
            ("lee la página [ID]",         "notion_get_content"),
            ("crea página en [ID] ...",    "notion_create_page"),
            ("agrega a [ID] ...",          "notion_append_md"),
            ("consulta db [ID]",           "notion_get_database"),
        ]),
        ("GitHub", [
            ("lista mis repos",            "github_list_repos"),
            ("PRs del repo [owner/repo]",  "github_list_prs"),
            ("crea issue en ...",          "github_create_issue"),
            ("commits de ...",             "github_get_commits"),
            ("diff del PR #N en ...",      "github_get_pr_diff"),
        ]),
    ]

    for sec_title, cmds in sections:
        console.print(f"  [{O}]{sec_title}[/{O}]")
        tbl = Table(
            box=_rbox.SIMPLE_HEAD,
            border_style=f"dim {B}",
            show_header=False,
            padding=(0, 2),
        )
        tbl.add_column("Comando",      style=f"bold {B}", width=32)
        tbl.add_column("Descripción",  style=DM,          max_width=48)
        for cmd, desc in cmds:
            tbl.add_row(cmd, desc)
        console.print(tbl)
        console.print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI principal
# ─────────────────────────────────────────────────────────────────────────────
class AutomyxCLI:
    def __init__(self, model: str = "", verbose: bool = False) -> None:
        self.console: Optional[Console] = _make_console()
        self.verbose = verbose
        self.model   = (
            model
            or os.environ.get("AUTOMYX_MODEL", "")
            or "openai/gpt-oss-120b"
        )
        self._integrations_on: List[str] = [
            k for k, m in INTEGRATIONS.items()
            if os.environ.get(m["env"], "").strip()
        ]

    def _p(self, text: str = "") -> None:
        if self.console:
            self.console.print(text)
        else:
            print(text)

    def _rule(self, title: str = "", color: str = "") -> None:
        if self.console:
            _rule(self.console, title, color)
        else:
            print(f"\n── {title} ──")

    def start(self) -> None:
        if self.console:
            print_welcome(self.console, self.model, self._integrations_on)
        else:
            print(f"AUTOMYX v{VERSION}  ·  {self.model}")

        self._start_repl()

    def _start_repl(self) -> None:
        try:
            from core.repl import AutomyxREPL
        except ImportError as e:
            self._p(f"  [{R}]Error importando REPL: {e}[/{R}]")
            sys.exit(1)

        repl = AutomyxREPL(model=self.model, verbose=self.verbose)

        # ── wire integraciones al agente cuando esté listo ────────────────
        original_ensure = repl._ensure_agent

        def _patched_ensure() -> None:
            original_ensure()
            if repl.agent is not None:
                results = wire_all_integrations(repl.agent, self.console)
            repl._ensure_agent = original_ensure  # solo parchear una vez

        repl._ensure_agent = _patched_ensure

        repl.start()


# ─────────────────────────────────────────────────────────────────────────────
# CLI standalone: python automyx_cli.py [opciones]
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="automyx_cli",
        description=f"AUTOMYX v{VERSION} — Terminal-First AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python automyx_cli.py
  python automyx_cli.py --model openai/gpt-oss-120b
  python automyx_cli.py --model claude-3-5-sonnet-20241022 --verbose
  python automyx_cli.py --integrations        ver estado de integraciones
  python automyx_cli.py --select-model        elegir modelo interactivo
        """,
    )
    parser.add_argument("--model",          "-m", default="",       help="Modelo a usar")
    parser.add_argument("--verbose",        "-v", action="store_true")
    parser.add_argument("--integrations",   "-i", action="store_true", help="Mostrar estado de integraciones y salir")
    parser.add_argument("--select-model",   "-s", action="store_true", help="Abrir selector de modelo interactivo")
    args = parser.parse_args()

    console = _make_console()
    if not console:
        print(f"AUTOMYX v{VERSION} — rich no disponible, instala con: pip install rich")
        sys.exit(1)

    # ── modo: ver integraciones ───────────────────────────────────────────
    if args.integrations:
        _banner(console)
        _rule(console, "ESTADO DE INTEGRACIONES", PU)
        console.print()
        _intg_status_table(console)
        console.print()
        return

    # ── modo: seleccionar modelo ──────────────────────────────────────────
    current_model = (
        args.model
        or os.environ.get("AUTOMYX_MODEL", "")
        or "openai/gpt-oss-120b"
    )
    if args.select_model:
        chosen = select_model(console, current=current_model)
        if chosen and chosen != current_model:
            os.environ["AUTOMYX_MODEL"] = chosen
            # persistir en .env
            env_path = Path(__file__).parent.parent / ".env"
            lines = []
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if not line.startswith("AUTOMYX_MODEL="):
                        lines.append(line)
            lines.append(f"AUTOMYX_MODEL={chosen}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            current_model = chosen
            console.print(f"\n  [{G}]✓[/{G}] Modelo actualizado: [{O}]{chosen}[/{O}]\n")

    # ── modo normal: arrancar REPL ────────────────────────────────────────
    sys.path.insert(0, str(Path(__file__).parent.parent))
    cli = AutomyxCLI(model=current_model, verbose=args.verbose)
    cli.start()


if __name__ == "__main__":
    main()
