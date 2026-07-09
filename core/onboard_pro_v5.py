from __future__ import annotations

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    from rich.rule import Rule
    from rich.columns import Columns
    from rich.syntax import Syntax
    from rich.live import Live
    from rich.spinner import Spinner
    from rich import box as _rbox
    RICH = True
except ImportError:
    RICH = False

try:
    from core.ui import console as _shared_console
except Exception:
    _shared_console = None

O  = "#00D4AA"
B  = "#00AAFF"
G  = "#5EE6A8"
R  = "#FF4444"
DM = "#4A6A8A"
W  = "#F0F6FF"
PU = "#A855F7"
YL = "#FFD700"

_STATE_FILE = Path("state") / "onboard_v5.json"

PROVIDERS: List[Dict[str, Any]] = [
    {
        "id":       "anthropic",
        "name":     "Anthropic / Claude",
        "tag":      "PAID",
        "desc":     "Claude Opus/Sonnet/Haiku 2026 · el más inteligente",
        "url":      "https://console.anthropic.com/settings/keys",
        "env_var":  "ANTHROPIC_API_KEY",
        "hint":     "console.anthropic.com → Settings → API Keys → Create Key",
        "models": [
            ("claude-opus-4-8",           "Claude Opus 4.8   · flagship 2026 · máximo poder"),
            ("claude-sonnet-4-6",         "Claude Sonnet 4.6 · mejor balance 2026 ★"),
            ("claude-haiku-4-5",          "Claude Haiku 4.5  · ultra-rápido y barato"),
            ("claude-opus-4-5",           "Claude Opus 4.5   · generación anterior"),
            ("claude-sonnet-4-5",         "Claude Sonnet 4.5 · probado y confiable"),
            ("claude-3-5-sonnet-20241022","Claude 3.5 Sonnet · clásico estable"),
        ],
        "default":  "claude-sonnet-4-6",
        "base_url": None,
        "has_free_key": False,
    },
    {
        "id":       "openai",
        "name":     "OpenAI",
        "tag":      "PAID",
        "desc":     "GPT-4.1 / o3 / o4-mini · 1M contexto",
        "url":      "https://platform.openai.com/api-keys",
        "env_var":  "OPENAI_API_KEY",
        "hint":     "platform.openai.com → API Keys → Create new secret key",
        "models": [
            ("gpt-4.1",       "GPT-4.1      · flagship 2026 · 1M ctx ★"),
            ("gpt-4.1-mini",  "GPT-4.1 Mini · rápido y económico"),
            ("gpt-4.1-nano",  "GPT-4.1 Nano · ultra-barato"),
            ("gpt-4o",        "GPT-4o       · multimodal, muy capaz"),
            ("gpt-4o-mini",   "GPT-4o Mini  · rápido"),
            ("o3",            "o3           · razonamiento avanzado"),
            ("o4-mini",       "o4-mini      · razonamiento rápido"),
        ],
        "default":  "gpt-4.1",
        "base_url": "https://api.openai.com/v1",
        "has_free_key": False,
    },
    {
        "id":       "google",
        "name":     "Google Gemini",
        "tag":      "PAID",
        "desc":     "Gemini 2.5 Pro/Flash · 1M contexto · muy barato",
        "url":      "https://aistudio.google.com/app/apikey",
        "env_var":  "GOOGLE_API_KEY",
        "hint":     "aistudio.google.com → Get API Key → Create API key",
        "models": [
            ("gemini-2.5-pro",      "Gemini 2.5 Pro      · flagship · 1M ctx ★"),
            ("gemini-2.5-flash",    "Gemini 2.5 Flash    · ultra-rápido · 1M ctx"),
            ("gemini-2.5-flash-8b", "Gemini 2.5 Flash-8B · ultra-barato"),
            ("gemini-2.0-flash",    "Gemini 2.0 Flash    · generación anterior"),
        ],
        "default":  "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "has_free_key": False,
    },
    {
        "id":       "xai",
        "name":     "xAI / Grok",
        "tag":      "PAID",
        "desc":     "Grok-3 · 131K contexto · muy potente",
        "url":      "https://console.x.ai/",
        "env_var":  "XAI_API_KEY",
        "hint":     "console.x.ai → API Keys → Create API Key",
        "models": [
            ("grok-3",            "Grok-3       · flagship xAI 2026 ★"),
            ("grok-3-mini",       "Grok-3 Mini  · razonamiento rápido y barato"),
            ("grok-2-vision-1212","Grok-2 Vision · multimodal, generación anterior"),
        ],
        "default":  "grok-3",
        "base_url": "https://api.x.ai/v1",
        "has_free_key": False,
    },
    {
        "id":       "mistral",
        "name":     "Mistral AI",
        "tag":      "PAID",
        "desc":     "Mistral Large/Medium/Small · europeo · multilingüe",
        "url":      "https://console.mistral.ai/api-keys",
        "env_var":  "MISTRAL_API_KEY",
        "hint":     "console.mistral.ai → Workspace → API Keys",
        "models": [
            ("mistral-large-latest",  "Mistral Large   · flagship · multilingüe ★"),
            ("mistral-medium-latest", "Mistral Medium  · balance perfecto"),
            ("mistral-small-latest",  "Mistral Small   · ultra-rápido y barato"),
            ("codestral-latest",      "Codestral       · especialista en código"),
        ],
        "default":  "mistral-large-latest",
        "base_url": "https://api.mistral.ai/v1",
        "has_free_key": False,
    },
    {
        "id":       "deepseek",
        "name":     "DeepSeek",
        "tag":      "PAID",
        "desc":     "DeepSeek V3/R2 · el más barato del mercado",
        "url":      "https://platform.deepseek.com/api_keys",
        "env_var":  "DEEPSEEK_API_KEY",
        "hint":     "platform.deepseek.com → API keys → Create new API key",
        "models": [
            ("deepseek-chat",     "DeepSeek V3 (chat)    · mejor valor ★ · $0.27/1M"),
            ("deepseek-reasoner", "DeepSeek R2 (reasoner)· razonamiento · $0.55/1M"),
        ],
        "default":  "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "has_free_key": False,
    },
    {
        "id":       "nvidia",
        "name":     "NVIDIA NIM",
        "tag":      "FREE",
        "desc":     "120B+ open-weights · gratis · sin tarjeta",
        "url":      "https://build.nvidia.com/",
        "env_var":  "NVIDIA_API_KEY",
        "models": [
            ("openai/gpt-oss-120b",                "GPT-OSS 120B       · open-weights · coding ★"),
            ("nvidia/nemotron-3-super-120b-a12b",  "Nemotron Super 120B· thinking mode · razonamiento ★"),
            ("minimaxai/minimax-m3",               "MiniMax M3         · multimodal · fast"),
            ("meta/llama-4-scout",                 "Llama 4 Scout      · Meta 2026 · multimodal"),
            ("moonshotai/kimi-k2.6",               "Kimi K2.6          · 256K context"),
            ("meta/llama-3.3-70b-instruct",        "Llama 3.3 70B      · general"),
            ("nvidia/llama-3.1-nemotron-70b-instruct", "Nemotron 70B   · razonamiento"),
            ("mistralai/mistral-large-2-instruct", "Mistral Large 2    · via NVIDIA"),
        ],
        "default":  "openai/gpt-oss-120b",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "has_free_key": True,
        "free_key": "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",
    },
    {
        "id":       "ollama",
        "name":     "Ollama (Local)",
        "tag":      "FREE",
        "desc":     "100% local · sin internet · privado",
        "url":      "https://ollama.com/",
        "env_var":  None,
        "models": [
            ("llama3.3:70b",    "Llama 3.3 70B · potente · 40GB RAM ★"),
            ("qwen3:32b",       "Qwen3 32B     · Alibaba · razonamiento"),
            ("qwen3:8b",        "Qwen3 8B      · ligero · muy bueno"),
            ("llama3.1:8b",     "Llama 3.1 8B  · rápido · 5GB RAM"),
            ("gemma3:9b",       "Gemma 3 9B    · Google · vision local"),
            ("codellama:latest","CodeLlama     · código"),
        ],
        "default":  "qwen3:8b",
        "base_url": "http://localhost:11434/v1",
        "has_free_key": False,
        "no_key_needed": True,
    },
]

INTEGRATIONS: List[Dict[str, Any]] = [
    {
        "id":      "notion",
        "name":    "Notion",
        "icon":    "📓",
        "desc":    "Leer/escribir páginas, bases de datos, notas",
        "env_var": "NOTION_API_KEY",
        "url":     "https://www.notion.so/my-integrations",
        "hint":    "Crea una integration en notion.so → Settings → Connections → Develop integrations",
        "prefix":  "secret_",
        "tools":   ["notion_search", "notion_create_page", "notion_append_block", "notion_get_db"],
    },
    {
        "id":      "github",
        "name":    "GitHub",
        "icon":    "🐙",
        "desc":    "PRs, issues, commits, repos, diff de código",
        "env_var": "GITHUB_TOKEN",
        "url":     "https://github.com/settings/tokens/new",
        "hint":    "Genera un Personal Access Token con permisos repo + workflow",
        "prefix":  "ghp_",
        "tools":   ["github_list_repos", "github_list_prs", "github_create_issue", "github_get_commits"],
    },
    {
        "id":      "telegram",
        "name":    "Telegram Bot",
        "icon":    "✈️",
        "desc":    "Controla Automyx desde Telegram",
        "env_var": "TELEGRAM_BOT_TOKEN",
        "url":     "https://t.me/BotFather",
        "hint":    "Habla con @BotFather → /newbot → copia el token",
        "prefix":  "",
        "tools":   [],
    },
    {
        "id":      "discord",
        "name":    "Discord Bot",
        "icon":    "🎮",
        "desc":    "Automyx en tu servidor de Discord",
        "env_var": "DISCORD_BOT_TOKEN",
        "url":     "https://discord.com/developers/applications",
        "hint":    "Crea una App → Bot → Reset Token → copia el token",
        "prefix":  "",
        "tools":   [],
    },
    {
        "id":      "elevenlabs",
        "name":    "ElevenLabs",
        "icon":    "🔊",
        "desc":    "TTS ultra-realista y voice cloning",
        "env_var": "ELEVENLABS_API_KEY",
        "url":     "https://elevenlabs.io/app/api-key",
        "hint":    "Dashboard → API Keys → Create API Key",
        "prefix":  "",
        "tools":   [],
    },
    {
        "id":      "openweather",
        "name":    "OpenWeather",
        "icon":    "🌤️",
        "desc":    "Clima en tiempo real para cualquier ciudad",
        "env_var": "OPENWEATHER_API_KEY",
        "url":     "https://home.openweathermap.org/api_keys",
        "hint":    "Gratis hasta 60 calls/min — crea una cuenta y copia tu key",
        "prefix":  "",
        "tools":   [],
    },
]

SYS_TOOLS = [
    ("python",  "Runtime Python"),
    ("git",     "Control de versiones"),
    ("ffmpeg",  "Edición de video/audio"),
    ("node",    "Node.js / npm"),
]


class HackerOnboarding:
    def __init__(self) -> None:
        self.console: Console = _shared_console or (Console() if RICH else None)
        self.cfg: Dict[str, Any] = self._load_state()
        self.provider: Dict[str, Any] = {}
        self.model:    str = ""
        self.api_key:  str = ""

    def _load_state(self) -> Dict[str, Any]:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _STATE_FILE.exists():
            try:
                return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_state(self) -> None:
        _STATE_FILE.write_text(json.dumps(self.cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_env(self, key: str, value: str) -> None:
        os.environ[key] = value
        env_path = Path(".env")
        lines: List[str] = []
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if not line.startswith(f"{key}="):
                    lines.append(line)
        lines.append(f"{key}={value}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _p(self, text: str = "") -> None:
        if self.console:
            self.console.print(text)
        else:
            print(text)

    def _rule(self, title: str = "", color: str = "") -> None:
        c = color or B
        if self.console:
            self.console.print(Rule(f"[bold {c}]{title}[/]", style=f"dim {c}"))

    def _banner(self) -> None:
        if not self.console:
            print("=== AUTOMYX 2.5 — SETUP ===")
            return
        self.console.clear()

        # ── Ballena azul ASCII ──────────────────────────────────────────────
        whale = (
            "                         .-'                              \n"
            "                    '---( ()  ~  ∿  ∿  ∿                 \n"
            "                        '-..\"  ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿~    \n"
            "                   ~~~∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿~~~  \n"
        )

        # ── Logo AUTOMYX ────────────────────────────────────────────────────
        logo = Text()
        logo.append("\n")
        logo.append("  ▄████████╗ ██╗   ██╗████████╗  ██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗\n", style=f"bold {O}")
        logo.append("  ██╔══════╝ ██║   ██║╚══██╔══╝ ██╔═══██╗████╗ ████║╚██╗ ██╔╝╚██╗██╔╝\n", style=f"bold {O}")
        logo.append("  ███████╗   ██║   ██║   ██║    ██║   ██║██╔████╔██║ ╚████╔╝  ╚███╔╝ \n", style=f"bold {B}")
        logo.append("  ██╔════╝   ██║   ██║   ██║    ██║   ██║██║╚██╔╝██║  ╚██╔╝   ██╔██╗ \n", style=f"bold {B}")
        logo.append("  ███████╗   ╚██████╔╝   ██║    ╚██████╔╝██║ ╚═╝ ██║   ██║   ██╔╝ ██╗\n", style=f"bold {O}")
        logo.append("  ╚══════╝    ╚═════╝    ╚═╝     ╚═════╝ ╚═╝     ╚═╝   ╚═╝   ╚═╝  ╚═╝\n", style=f"dim {O}")
        logo.append("\n")

        self.console.print(logo)

        # ── Panel ballena + tagline ──────────────────────────────────────────
        from rich.panel import Panel as _Panel
        whale_panel = _Panel(
            Text.from_markup(
                f"[bold {B}]{whale}[/bold {B}]"
                f"[dim {DM}]  🐋  autonomous ai agent  ·  v2.5  ·  powered by nvidia, anthropic & more[/dim {DM}]"
            ),
            border_style=B,
            box=_rbox.HEAVY,
            padding=(0, 2),
        )
        self.console.print(whale_panel)
        self.console.print()

    def _setup_overview(self, completed: Optional[List[str]] = None) -> None:
        """Muestra el mapa de pasos al estilo Claude Code."""
        from rich.panel import Panel as _Panel
        completed = completed or []
        steps = [
            ("provider",     "1", "Proveedor de IA"),
            ("model",        "2", "Modelo"),
            ("api_key",      "3", "API Key / Credenciales"),
            ("integrations", "4", "Integraciones opcionales"),
            ("sys_check",    "5", "Herramientas del sistema"),
        ]
        t = Text()
        t.append("\n")
        for key, num, label in steps:
            if key in completed:
                t.append(f"  ✔ [{num}] {label}\n", style=f"bold {G}")
            elif key == (completed[-1] if completed else "") + "_next":
                t.append(f"  ● [{num}] {label}\n", style=f"bold {O}")
            else:
                t.append(f"  ○ [{num}] {label}\n", style=f"dim {DM}")
        t.append("\n")
        self.console.print(_Panel(
            t,
            title=f"[bold {O}]  SETUP WIZARD  [/bold {O}]",
            border_style=f"dim {DM}",
            box=_rbox.ROUNDED,
            padding=(0, 4),
            expand=False,
        ))
        self.console.print()

    def run(self) -> None:
        self._banner()
        if self.console:
            self._setup_overview()
        self._step_provider()
        self._step_model()
        self._step_api_key()
        self._step_integrations()
        self._step_sys_check()
        self._step_notion()
        self._step_complete()

    def _badge(self, text: str, color: str) -> Text:
        t = Text()
        t.append(f" {text} ", style=f"bold reverse {color}")
        return t

    def _step_provider(self) -> None:
        self._p()
        self._rule("PASO 1 / 6  ·  PROVEEDOR DE IA", O)
        self._p()
        self._p(f"  [{DM}]Elige el motor de IA que usará Automyx.[/{DM}]")
        self._p()

        if not self.console:
            for i, pv in enumerate(PROVIDERS, 1):
                print(f"  {i}. {pv['name']}  [{pv['tag']}]  — {pv['desc']}")
            raw = input("\n  Opción [1]: ").strip() or "1"
            self.provider = PROVIDERS[int(raw) - 1]
            return

        tbl = Table(
            box=_rbox.SIMPLE_HEAD,
            border_style=f"dim {B}",
            show_header=True,
            header_style=f"bold {O}",
            padding=(0, 2),
        )
        tbl.add_column("#",       style=f"bold {O}",  width=3,  justify="right")
        tbl.add_column("Provider",style=f"bold {W}",  width=22)
        tbl.add_column("Tag",     width=8,  justify="center")
        tbl.add_column("Descripción", style=DM, max_width=46)

        tag_colors = {"FREE": G, "PAID": YL}
        for i, pv in enumerate(PROVIDERS, 1):
            tc = tag_colors.get(pv["tag"], W)
            tag_text = Text(f"[{pv['tag']}]", style=f"bold {tc}")
            existing = os.environ.get(pv["env_var"] or "", "") if pv.get("env_var") else ""
            name_text = Text(pv["name"])
            if existing:
                name_text.append("  ✓", style=f"bold {G}")
            tbl.add_row(str(i), name_text, tag_text, pv["desc"])

        self.console.print(tbl)
        self._p()

        raw = Prompt.ask(
            f"  [{O}]Opción[/{O}]",
            choices=[str(i) for i in range(1, len(PROVIDERS) + 1)],
            default="1",
        )
        self.provider = PROVIDERS[int(raw) - 1]
        self._p()
        sel = Text()
        sel.append("  ✓ ", style=f"bold {G}")
        sel.append("Provider: ", style=DM)
        sel.append(self.provider["name"], style=f"bold {W}")
        self._p(sel)

    def _step_model(self) -> None:
        self._p()
        self._rule(f"PASO 2 / 6  ·  MODELO — {self.provider['name'].upper()}", B)
        self._p()
        self._p(f"  [{DM}]precio = USD / 1M tokens  ·  entrada / salida[/{DM}]")
        self._p()

        pv_id = self.provider["id"]

        # Intentar obtener datos detallados de model_config
        rich_models: List[Tuple[str, Dict]] = []
        try:
            from core.model_config import (
                NVIDIA_MODELS, ANTHROPIC_MODELS, OPENAI_MODELS, OLLAMA_MODELS,
                GOOGLE_MODELS, XAI_MODELS, MISTRAL_MODELS, DEEPSEEK_MODELS,
            )
            _map = {
                "nvidia":    NVIDIA_MODELS,
                "anthropic": ANTHROPIC_MODELS,
                "openai":    OPENAI_MODELS,
                "google":    GOOGLE_MODELS,
                "xai":       XAI_MODELS,
                "mistral":   MISTRAL_MODELS,
                "deepseek":  DEEPSEEK_MODELS,
                "ollama":    OLLAMA_MODELS,
            }
            src = _map.get(pv_id, {})
            rich_models = list(src.items())
        except Exception:
            pass

        # Fallback a lista simple del PROVIDERS si no hay datos ricos
        if not rich_models:
            simple_models = self.provider["models"]
            if not self.console:
                for i, (mid, mdesc) in enumerate(simple_models, 1):
                    print(f"  {i}. {mid}  — {mdesc}")
                raw = input(f"\n  Opción [1]: ").strip() or "1"
                self.model = simple_models[int(raw) - 1][0]
                self.cfg["model"] = self.model
                self.cfg["provider"] = pv_id
                self._save_state()
                return
            rich_models = [(mid, {"description": mdesc, "cost_in": 0.0, "cost_out": 0.0,
                                   "ctx_k": 0, "vision": False, "badge": "FREE"})
                           for mid, mdesc in simple_models]

        if not self.console:
            for i, (mid, cfg) in enumerate(rich_models, 1):
                cin  = cfg.get("cost_in",  0.0)
                cout = cfg.get("cost_out", 0.0)
                cost = "GRATIS" if (cin == 0.0 and cout == 0.0) else f"${cin:.2f}/${cout:.2f}"
                print(f"  {i}. {mid:<42}  {cost:>14}  — {cfg.get('description','')}")
            raw = input(f"\n  Opción [1]: ").strip() or "1"
            self.model = rich_models[int(raw) - 1][0]
            self.cfg["model"] = self.model
            self.cfg["provider"] = pv_id
            self._save_state()
            return

        tbl = Table(
            box=_rbox.SIMPLE_HEAD,
            border_style=f"dim {B}",
            show_header=True,
            header_style=f"bold {B}",
            padding=(0, 1),
        )
        tbl.add_column("#",        style=f"bold {O}", width=3,  justify="right")
        tbl.add_column("Modelo",   style=f"bold {W}", min_width=32)
        tbl.add_column("Ctx",      style=DM,          width=6,  justify="right")
        tbl.add_column("Vision",   style=DM,          width=6,  justify="center")
        tbl.add_column("Entrada",  style=YL,          width=10, justify="right")
        tbl.add_column("Salida",   style=R,           width=10, justify="right")
        tbl.add_column("Info",     style=DM,          min_width=28)

        default_idx = "1"
        for i, (mid, cfg) in enumerate(rich_models, 1):
            cin   = cfg.get("cost_in",  0.0)
            cout  = cfg.get("cost_out", 0.0)
            ctx_k = cfg.get("ctx_k", 0)
            vis   = "✓" if cfg.get("vision") else "·"
            desc  = cfg.get("description", "")
            is_star = "★" in desc or cfg.get("is_default")

            cin_s  = "GRATIS" if cin  == 0.0 else f"${cin:.2f}"
            cout_s = "GRATIS" if cout == 0.0 else f"${cout:.2f}"
            ctx_s  = f"{ctx_k}K" if ctx_k else "·"
            m_text = Text(mid, style=f"bold {O}" if is_star else W)
            if is_star:
                default_idx = str(i)

            tbl.add_row(str(i), m_text, ctx_s, vis, cin_s, cout_s, desc.replace(" ★", ""))

        self.console.print(tbl)
        self._p(f"  [{DM}]Entrada = costo por 1M tokens de entrada  ·  Salida = costo por 1M tokens de salida[/{DM}]")
        self._p()

        raw = Prompt.ask(
            f"  [{O}]Opción[/{O}]",
            choices=[str(i) for i in range(1, len(rich_models) + 1)],
            default=default_idx,
        )
        self.model = rich_models[int(raw) - 1][0]
        self.cfg["model"]    = self.model
        self.cfg["provider"] = pv_id
        self._save_state()

        self._p()
        sel = Text()
        sel.append("  ✓ ", style=f"bold {G}")
        sel.append("Modelo: ", style=DM)
        sel.append(self.model, style=f"bold {O}")
        # Mostrar costo si aplica
        chosen_cfg = rich_models[int(raw) - 1][1]
        cin_v  = chosen_cfg.get("cost_in",  0.0)
        cout_v = chosen_cfg.get("cost_out", 0.0)
        if cin_v > 0.0 or cout_v > 0.0:
            sel.append(f"  (${cin_v:.2f} entrada / ${cout_v:.2f} salida por 1M tokens)", style=f"dim {DM}")
        else:
            sel.append("  (GRATIS)", style=f"bold {G}")
        self._p(sel)

    def _step_api_key(self) -> None:
        self._p()
        self._rule("PASO 3 / 6  ·  API KEY", O)
        self._p()

        pv = self.provider

        if pv.get("no_key_needed"):
            self._p(f"  [{G}]✓[/{G}] [{W}]Ollama no necesita API key — corre 100% local.[/{W}]")
            self._p(f"  [{DM}]Asegúrate de tener Ollama corriendo: ollama serve[/{DM}]")
            self._p(f"  [{DM}]Descarga un modelo: ollama pull {self.model}[/{DM}]")
            self._configure_agent()
            return

        env_var = pv["env_var"]
        existing = os.environ.get(env_var, "").strip()

        if existing:
            self._p(f"  [{G}]✓[/{G}] [{DM}]{env_var}[/{DM}] ya está configurado.")
            if self.console:
                keep = Confirm.ask(f"  [{O}]¿Usar el existente?[/{O}]", default=True)
            else:
                keep = (input("  ¿Usar el existente? [S/n]: ").strip().lower() or "s") == "s"
            if keep:
                self.api_key = existing
                self._configure_agent()
                return

        # Prefijos válidos por proveedor
        _KEY_PREFIXES = {
            "anthropic": ("sk-ant-", "Las keys de Anthropic empiezan con  sk-ant-"),
            "openai":    ("sk-",     "Las keys de OpenAI empiezan con  sk-"),
            "google":    ("AIza",    "Las keys de Google empiezan con  AIza"),
            "xai":       ("xai-",   "Las keys de xAI empiezan con  xai-"),
            "mistral":   ("",        ""),
            "deepseek":  ("sk-",    "Las keys de DeepSeek empiezan con  sk-"),
            "nvidia":    ("nvapi-", "Las keys de NVIDIA empiezan con  nvapi-"),
        }
        prefix, prefix_hint = _KEY_PREFIXES.get(pv["id"], ("", ""))

        self._p()
        if self.console:
            self.console.print(Panel(
                f"[bold {W}]{pv['name']}[/bold {W}]\n\n"
                f"[{DM}]Obtén tu API key en:[/{DM}]\n"
                f"[bold {B}]{pv['url']}[/bold {B}]"
                + (f"\n\n[{DM}]{pv.get('hint','')}[/{DM}]" if pv.get("hint") else "")
                + (f"\n\n[{DM}]{prefix_hint}[/{DM}]" if prefix_hint else ""),
                title=f"[bold {O}]  API KEY — {pv['name'].upper()}  [/bold {O}]",
                border_style=O,
                box=_rbox.ROUNDED,
                padding=(1, 4),
                expand=False,
            ))
            self._p()

        if pv.get("has_free_key"):
            self._p(f"  [{G}]ℹ[/{G}]  [{DM}]NVIDIA tiene una key gratuita incluida. Puedes usar la tuya propia para mayor rate-limit.[/{DM}]")
            self._p()
            if self.console:
                use_free = Confirm.ask(f"  [{O}]¿Usar la key gratuita de Automyx?[/{O}]", default=True)
            else:
                use_free = (input("  ¿Usar key gratuita? [S/n]: ").strip().lower() or "s") == "s"
            if use_free:
                self.api_key = pv["free_key"]
                self._save_env(env_var, self.api_key)
                self._p(f"  [{G}]✓[/{G}] Key gratuita aplicada.")
                self._configure_agent()
                return

        # Bucle de entrada con hasta 3 intentos
        for attempt in range(3):
            self._p()
            if self.console:
                try:
                    raw = Prompt.ask(
                        f"  [{O}]▸ Pega tu {env_var}[/{O}]  [{DM}](Enter para omitir)[/{DM}]",
                        password=True, default=""
                    )
                except (KeyboardInterrupt, EOFError):
                    break
            else:
                raw = input(f"  Pega tu {env_var}: ").strip()

            raw = raw.strip()
            if not raw:
                break

            # Validación de formato
            if prefix and not raw.startswith(prefix):
                if self.console:
                    self.console.print(Panel(
                        f"[bold {YL}]Formato incorrecto[/bold {YL}]\n"
                        f"[{DM}]{prefix_hint}[/{DM}]\n"
                        f"[{DM}]Tu key empieza con:[/{DM}] [{R}]{raw[:10]}…[/{R}]",
                        border_style=YL,
                        padding=(0, 4),
                        expand=False,
                    ))
                else:
                    print(f"  ⚠ Formato incorrecto. {prefix_hint}")
                continue

            masked = raw[:10] + "···" + raw[-4:] if len(raw) > 14 else raw[:6] + "···"
            self._p(f"  [{DM}]Key recibida:[/{DM}] [{W}]{masked}[/{W}]")

            # Verificación en vivo
            if self.console:
                with self.console.status(
                    f"  [{DM}]Verificando con {pv['name']}...[/{DM}]",
                    spinner="dots2", spinner_style=O
                ):
                    import time as _t3; _t3.sleep(0.3)
                    valid, msg = self._validate_key(pv, raw)
            else:
                print(f"  Verificando...")
                valid, msg = self._validate_key(pv, raw)

            if valid:
                self.api_key = raw
                self._save_env(env_var, raw)
                if self.console:
                    self.console.print(Panel(
                        f"[bold {G}]  KEY VÁLIDA Y GUARDADA  [/bold {G}]\n\n"
                        f"[{DM}]{masked}[/{DM}]\n\n"
                        f"[{G}]{pv['name']} está listo para usar.[/{G}]",
                        border_style=G,
                        padding=(1, 4),
                        expand=False,
                    ))
                    import time as _t3; _t3.sleep(0.8)
                else:
                    print(f"  ✓ Key válida — {msg}")
                self._configure_agent()
                return
            else:
                intentos_left = 2 - attempt
                if self.console:
                    self.console.print(Panel(
                        f"[bold {R}]  KEY INVÁLIDA  [/bold {R}]\n\n"
                        f"[{DM}]{msg}[/{DM}]\n\n"
                        + (f"[{YL}]Intentos restantes: {intentos_left}[/{YL}]"
                           if intentos_left > 0 else f"[{R}]Sin más intentos.[/{R}]"),
                        border_style=R,
                        padding=(1, 4),
                        expand=False,
                    ))
                else:
                    print(f"  ✗ Key inválida: {msg}")
                if intentos_left == 0:
                    break

        self._p(f"  [{YL}]⚠[/{YL}] Continuando sin key válida.")
        self._configure_agent()

    def _validate_key(self, pv: Dict[str, Any], key: str) -> Tuple[bool, str]:
        import urllib.request as _ur, urllib.error as _ue
        pid = pv["id"]
        _auth = {"Authorization": f"Bearer {key}"}
        _endpoints = {
            "nvidia":   ("GET", "https://integrate.api.nvidia.com/v1/models",  _auth, None),
            "openai":   ("GET", "https://api.openai.com/v1/models",            _auth, None),
            "google":   ("GET", f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", {}, None),
            "xai":      ("GET", "https://api.x.ai/v1/models",                 _auth, None),
            "mistral":  ("GET", "https://api.mistral.ai/v1/models",           _auth, None),
            "deepseek": ("GET", "https://api.deepseek.com/v1/models",         _auth, None),
            "anthropic":("POST","https://api.anthropic.com/v1/messages",
                         {"x-api-key": key, "anthropic-version": "2023-06-01",
                          "Content-Type": "application/json"},
                         {"model": "claude-haiku-4-5", "max_tokens": 1,
                          "messages": [{"role": "user", "content": "hi"}]}),
        }
        if pid not in _endpoints:
            return True, "sin verificación"
        method, url, headers, body = _endpoints[pid]
        try:
            import json as _j2
            data = _j2.dumps(body).encode() if body else None
            req = _ur.Request(url, data=data, headers=headers, method=method)
            with _ur.urlopen(req, timeout=12) as r:
                result = json.loads(r.read())
                n = len(result.get("data", result.get("models", [])))
                return True, f"{n} modelos disponibles" if n else "key válida"
        except _ue.HTTPError as e:
            if e.code in (400, 422) and pid == "anthropic":
                return True, "key válida"
            if e.code == 429:
                return True, "key válida (rate limit)"
            if e.code == 401:
                return False, "key rechazada (401 Unauthorized)"
            if e.code == 403:
                return False, "acceso denegado (403 Forbidden)"
            return False, f"error HTTP {e.code}"
        except Exception as exc:
            return False, str(exc)[:80]

    def _configure_agent(self) -> None:
        pv = self.provider
        self._save_env("AUTOMYX_MODEL", self.model)
        self._save_env("AUTOMYX_PROVIDER", pv["id"])
        if pv.get("base_url"):
            self._save_env("AUTOMYX_BASE_URL", pv["base_url"])
        self.cfg["model"]    = self.model
        self.cfg["provider"] = pv["id"]
        self._save_state()
        self._patch_model_config()

    def _patch_model_config(self) -> None:
        pv = self.provider
        try:
            from core.agent import ModelProvider
            os.environ["AUTOMYX_MODEL"]    = self.model
            os.environ["AUTOMYX_PROVIDER"] = pv["id"]
        except Exception:
            pass

        if pv["id"] == "anthropic" and self.api_key:
            try:
                import anthropic as _ant
                os.environ["ANTHROPIC_API_KEY"] = self.api_key
            except ImportError:
                pass

        if pv["id"] == "openai" and self.api_key:
            os.environ["OPENAI_API_KEY"] = self.api_key

    def _step_integrations(self) -> None:
        self._p()
        self._rule("PASO 4 / 6  ·  INTEGRACIONES OPCIONALES", PU)
        self._p()
        self._p(f"  [{DM}]Conecta servicios externos para ampliar las capacidades de Automyx.[/{DM}]")
        self._p(f"  [{DM}]Pulsa Enter para omitir cualquier integración.[/{DM}]")
        self._p()

        skip_notion = True

        for intg in INTEGRATIONS:
            env_var = intg["env_var"]
            existing = os.environ.get(env_var, "").strip()
            already  = "  " + ("[dim green]✓ ya configurado[/dim green]" if existing else f"[dim]{intg['desc']}[/dim]")

            if not self.console:
                print(f"\n  {intg['icon']}  {intg['name']}  —  {intg['desc']}")
                if existing:
                    print("    (ya configurado)")
                else:
                    val = input(f"    {env_var} (Enter para omitir): ").strip()
                    if val:
                        self._save_env(env_var, val)
                        print(f"    ✓ {intg['name']} configurado")
                        if intg["id"] == "notion":
                            skip_notion = False
                continue

            name_t = Text()
            name_t.append(f"  {intg['icon']}  ", style="")
            name_t.append(intg["name"], style=f"bold {W}")
            self._p(name_t)
            self._p(f"     [{DM}]{intg['desc']}[/{DM}]")
            if existing:
                self._p(f"     [{G}]✓[/{G}] [{DM}]ya configurado[/{DM}]")
                if intg["id"] == "notion" and existing:
                    skip_notion = False
                self._p()
                continue

            self._p(f"     [{DM}]→ {intg['hint']}[/{DM}]")
            self._p(f"     [{DM}]URL: [{B}]{intg['url']}[/{B}][/{DM}]")
            val = Prompt.ask(f"     [{O}]{env_var}[/{O}] [{DM}](Enter = omitir)[/{DM}]", default="")
            if val.strip():
                self._save_env(env_var, val.strip())
                self._p(f"     [{G}]✓[/{G}] {intg['name']} configurado")
                if intg["id"] == "notion":
                    skip_notion = False
            self._p()

        self.cfg["skip_notion"] = skip_notion
        self._save_state()

    def _step_sys_check(self) -> None:
        self._p()
        self._rule("PASO 5 / 6  ·  HERRAMIENTAS DEL SISTEMA", B)
        self._p()

        if not self.console:
            for tool, desc in SYS_TOOLS:
                found = shutil.which(tool)
                status = "OK" if found else "FALTA"
                print(f"  {status:<6} {tool:<12} {desc}")
            return

        tbl = Table(
            box=_rbox.SIMPLE_HEAD,
            border_style=f"dim {B}",
            show_header=True,
            header_style=f"bold {B}",
            padding=(0, 2),
        )
        tbl.add_column("Herramienta", style=f"bold {W}", width=14)
        tbl.add_column("Propósito",   style=DM,          width=26)
        tbl.add_column("Estado",      justify="center",   width=14)
        tbl.add_column("Versión",     style=DM,           width=14)

        for tool, desc in SYS_TOOLS:
            found = shutil.which(tool)
            if found:
                try:
                    out = subprocess.check_output(
                        [tool, "--version"], stderr=subprocess.STDOUT,
                        timeout=3, text=True, errors="replace"
                    ).splitlines()[0][:20]
                except Exception:
                    out = "?"
                status_t = Text("✓  instalado", style=f"bold {G}")
            else:
                out     = "—"
                status_t = Text("✗  falta",    style=f"dim {R}")

            tbl.add_row(tool, desc, status_t, out)

        self.console.print(tbl)
        self._p()

    def _step_notion(self) -> None:
        notion_key = os.environ.get("NOTION_API_KEY", "").strip()
        if not notion_key:
            return

        self._p()
        self._rule("NOTION — CONFIGURACIÓN AVANZADA", PU)
        self._p()
        self._p(f"  [{G}]✓[/{G}] Notion conectado. Registrando tools del agente...")
        self._p()

        try:
            self._register_notion_tools()
            self._p(f"  [{G}]✓[/{G}] Tools de Notion registradas: notion_search, notion_create_page,")
            self._p(f"      notion_append_block, notion_get_database")
        except Exception as e:
            self._p(f"  [{YL}]⚠[/{YL}] No se pudo registrar tools de Notion: {e}")

    def _register_notion_tools(self) -> None:
        import urllib.request, urllib.error, urllib.parse

        notion_key = os.environ.get("NOTION_API_KEY", "")

        def _notion_req(method: str, endpoint: str, body: Optional[Dict] = None) -> Dict:
            url = f"https://api.notion.com/v1/{endpoint}"
            data = json.dumps(body or {}).encode() if body else None
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Authorization":  f"Bearer {notion_key}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type":   "application/json",
                },
                method=method,
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())

        def notion_search(query: str = "", filter_type: str = "") -> Dict:
            body: Dict[str, Any] = {}
            if query:
                body["query"] = query
            if filter_type in ("page", "database"):
                body["filter"] = {"value": filter_type, "property": "object"}
            result = _notion_req("POST", "search", body)
            results = result.get("results", [])
            return {
                "ok":    True,
                "count": len(results),
                "items": [
                    {
                        "id":    r.get("id"),
                        "type":  r.get("object"),
                        "title": _notion_title(r),
                        "url":   r.get("url"),
                    }
                    for r in results[:20]
                ],
            }

        def _notion_title(obj: Dict) -> str:
            try:
                props = obj.get("properties", {})
                for k in ("Name", "Title", "title"):
                    p = props.get(k, {})
                    tv = p.get("title") or p.get("rich_text") or []
                    if tv:
                        return "".join(t.get("plain_text", "") for t in tv)
                return obj.get("id", "?")
            except Exception:
                return "?"

        def notion_create_page(
            parent_id: str,
            title: str,
            content: str = "",
            icon: str = "",
        ) -> Dict:
            body: Dict[str, Any] = {
                "parent": {"page_id": parent_id},
                "properties": {
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                },
            }
            if icon:
                body["icon"] = {"type": "emoji", "emoji": icon}
            if content:
                body["children"] = [
                    {
                        "object": "block",
                        "type":   "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                        },
                    }
                ]
            result = _notion_req("POST", "pages", body)
            return {"ok": True, "id": result.get("id"), "url": result.get("url")}

        def notion_append_block(page_id: str, content: str, block_type: str = "paragraph") -> Dict:
            valid_types = {"paragraph", "heading_1", "heading_2", "heading_3",
                           "bulleted_list_item", "numbered_list_item", "code", "quote"}
            if block_type not in valid_types:
                block_type = "paragraph"
            key = "rich_text" if block_type != "code" else "rich_text"
            block: Dict[str, Any] = {
                "object": "block",
                "type":   block_type,
                block_type: {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                },
            }
            if block_type == "code":
                block[block_type]["language"] = "plain text"
            result = _notion_req("PATCH", f"blocks/{page_id}/children", {"children": [block]})
            return {"ok": True, "results_count": len(result.get("results", []))}

        def notion_get_database(database_id: str, filter_json: str = "") -> Dict:
            body: Dict[str, Any] = {"page_size": 50}
            if filter_json:
                try:
                    body["filter"] = json.loads(filter_json)
                except Exception:
                    pass
            result = _notion_req("POST", f"databases/{database_id}/query", body)
            rows = result.get("results", [])
            return {
                "ok":    True,
                "count": len(rows),
                "rows": [
                    {
                        "id":    r.get("id"),
                        "url":   r.get("url"),
                        "props": {
                            k: _notion_title({"properties": {k: v}})
                            for k, v in r.get("properties", {}).items()
                        },
                    }
                    for r in rows[:30]
                ],
            }

        self.cfg["notion_tools"] = {
            "notion_search":       True,
            "notion_create_page":  True,
            "notion_append_block": True,
            "notion_get_database": True,
        }
        self._save_state()

        try:
            from core.tool_registry import _NOTION_TOOLS
            _NOTION_TOOLS.update({
                "notion_search":       notion_search,
                "notion_create_page":  notion_create_page,
                "notion_append_block": notion_append_block,
                "notion_get_database": notion_get_database,
            })
        except Exception:
            pass

        _GLOBAL_NOTION_TOOLS["notion_search"]       = notion_search
        _GLOBAL_NOTION_TOOLS["notion_create_page"]  = notion_create_page
        _GLOBAL_NOTION_TOOLS["notion_append_block"] = notion_append_block
        _GLOBAL_NOTION_TOOLS["notion_get_database"] = notion_get_database

    def _step_complete(self) -> None:
        self._p()
        self._rule("LISTO", G)
        self._p()

        if not self.console:
            print(f"\n  ✓ Automyx configurado.")
            print(f"  Modelo: {self.model}")
            print(f"  Provider: {self.provider['name']}")
            return

        summary = Text()
        summary.append(f"\n  {'─' * 52}\n", style=f"dim {B}")
        summary.append("  ✓ ", style=f"bold {G}")
        summary.append("Automyx 2.5 configurado y listo.\n\n", style=f"bold {W}")
        summary.append("  Modelo:    ", style=DM)
        summary.append(f"{self.model}\n",        style=f"bold {O}")
        summary.append("  Provider:  ", style=DM)
        summary.append(f"{self.provider['name']}\n", style=f"bold {W}")

        intgs_on = [
            i["name"] for i in INTEGRATIONS
            if os.environ.get(i["env_var"] or "", "").strip()
        ]
        if intgs_on:
            summary.append("  Conectado: ", style=DM)
            summary.append(", ".join(intgs_on) + "\n", style=f"bold {PU}")

        summary.append(f"\n  {'─' * 52}\n", style=f"dim {B}")
        summary.append("  Comandos rápidos:\n", style=f"bold {B}")
        summary.append("  python automix.py        ", style=DM)
        summary.append("→ REPL principal\n",      style=W)
        summary.append("  /help                    ", style=DM)
        summary.append("→ ver todos los comandos\n", style=W)
        summary.append("  /workspace create <name> ", style=DM)
        summary.append("→ nuevo workspace\n",      style=W)
        summary.append("  /tokens                  ", style=DM)
        summary.append("→ costo de la sesión\n",   style=W)
        summary.append("  /scan                    ", style=DM)
        summary.append("→ escaneo de seguridad\n", style=W)

        self.console.print(Panel(
            summary,
            border_style=f"{G}",
            box=_rbox.DOUBLE,
            padding=(0, 1),
        ))
        self._p()

        self.cfg["completed"] = True
        self._save_state()


_GLOBAL_NOTION_TOOLS: Dict[str, Any] = {}


def get_notion_tools() -> Dict[str, Any]:
    return _GLOBAL_NOTION_TOOLS.copy()


def inject_notion_into_agent(agent: Any) -> int:
    notion_key = os.environ.get("NOTION_API_KEY", "").strip()
    if not notion_key:
        return 0

    ob = HackerOnboarding()
    try:
        ob._register_notion_tools()
    except Exception:
        return 0

    added = 0
    for name, fn in _GLOBAL_NOTION_TOOLS.items():
        if name not in agent.tools:
            agent.register_tool(name, fn)
            added += 1
    return added


def is_first_run() -> bool:
    if not _STATE_FILE.exists():
        return True
    try:
        return not json.loads(_STATE_FILE.read_text(encoding="utf-8")).get("completed", False)
    except Exception:
        return True


def run_onboarding() -> None:
    ob = HackerOnboarding()
    ob.run()


if __name__ == "__main__":
    run_onboarding()
