"""
Automyx 2.5 — Interactive Onboarding Wizard
============================================
Glassmorphism blue-themed TUI with a 6-step setup:
  1. Welcome + security disclaimer
  2. Pick an LLM model (local + cloud)
  3. Pick a messaging channel (or skip)
  4. Multi-select skills from the 86-skill marketplace
  5. Pick integrations (Notion, GitHub, etc.) and paste tokens
  6. Confirm + save to .env / SQLite

All visuals come from `core.ui` (electric blue glassmorphism design system).
"""
from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path

# Reuse the shared design system
from core.ui import (
    NAVY, DEEP_BLUE, BLUE, ELECTRIC, CYAN, GLOW, WHITE, GRAY,
    WARN, OK, ERR, PURPLE,
    RICH_AVAILABLE, QUESTIONARY_AVAILABLE, console,
    show_banner, show_step_header, glass_panel, ok, info, warn, err, section,
    automyx_style, skill_table, save_to_env,
    AUTOMYX_VERSION, AUTOMYX_CODENAME,
)

# Rich + questionary (after ui.py)
if RICH_AVAILABLE:
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import box as rich_box
    from rich.align import Align

if QUESTIONARY_AVAILABLE:
    import questionary
    from questionary import Choice, Separator

try:
    from core.config import config
except Exception:
    config = None


# ============================================================================
# Persistent state
# ============================================================================
def _state_path() -> Path:
    p = Path("state") / "onboard_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_state(state: dict):
    p = _state_path()
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        import sqlite3
        db_path = Path("state") / "automyx.sqlite"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS onboard_state ("
                "  id INTEGER PRIMARY KEY,"
                "  state_json TEXT NOT NULL,"
                "  updated_at TEXT DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
            conn.execute(
                "INSERT INTO onboard_state (state_json) VALUES (?)",
                (json.dumps(state),),
            )
            conn.commit()
    except Exception as e:
        warn(f"No se pudo persistir en SQLite: {e}")


def load_state() -> dict:
    p = _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


# ============================================================================
# Skill catalog loader
# ============================================================================
def _load_skill_catalog() -> list:
    out = []
    try:
        from core.intent_engine import SKILLS_CATALOG
        if isinstance(SKILLS_CATALOG, dict):
            for cat_name, skills_in_cat in SKILLS_CATALOG.items():
                if not isinstance(skills_in_cat, list):
                    continue
                cat_icon = skills_in_cat[0].get("icon", "🧩") if skills_in_cat else "🧩"
                for skill in skills_in_cat:
                    out.append({
                        "name": skill.get("name", "?"),
                        "description": skill.get("desc", skill.get("description", "")),
                        "category": cat_name,
                        "icon": skill.get("icon", cat_icon),
                        "tools": skill.get("tools", ""),
                    })
            if out:
                return out
        elif isinstance(SKILLS_CATALOG, list):
            for cat in SKILLS_CATALOG:
                cat_name = cat.get("name", "Otros")
                cat_icon = cat.get("icon", "📦")
                for skill in cat.get("skills", []):
                    out.append({
                        "name": skill.get("name", "?"),
                        "description": skill.get("description", ""),
                        "category": cat_name,
                        "icon": cat_icon,
                        "tools": skill.get("tools", []),
                    })
            if out:
                return out
    except Exception:
        pass

    skills_dir = Path("skills")
    if skills_dir.is_dir():
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                name = d.name
                desc = ""
                try:
                    text = (d / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
                    for line in text.splitlines():
                        if line.strip().startswith("#"):
                            continue
                        if line.strip():
                            desc = line.strip()[:120]
                            break
                except Exception:
                    pass
                out.append({"name": name, "description": desc, "category": "General", "icon": "🧩", "tools": ""})
    return out


def show_skill_grid(preselected: list[str] = None):
    skills = _load_skill_catalog()
    if not skills:
        warn("No se pudo cargar el catálogo de skills.")
        return

    by_cat = {}
    for s in skills:
        by_cat.setdefault(s["category"], []).append(s)

    rows = []
    for cat, items in sorted(by_cat.items()):
        names = ", ".join(s["name"] for s in items[:5])
        if len(items) > 5:
            names += f" … [+{len(items)-5}]"
        n_tools = sum(len(s.get("tools", [])) for s in items)
        icon = items[0].get("icon", "🧩")
        rows.append((f"{icon} {cat}", names, n_tools))

    skill_table(
        rows,
        title=f"🧩 Skill Marketplace · {len(skills)} skills · {len(by_cat)} categories",
    )
    if RICH_AVAILABLE and console is not None:
        console.print("")


# ============================================================================
# STEP 1 — Welcome + Security
# ============================================================================
def step1_welcome() -> bool:
    show_banner(subtitle=f"Core {AUTOMYX_VERSION} · {AUTOMYX_CODENAME} · The Intent-Aware Engine")

    sec_text = (
        "Automyx can run shell commands, read/write files, control your mouse & keyboard, "
        "browse the web, send messages, and operate any desktop app on your behalf.\n\n"
        "It uses an Intent Engine that understands slang and typos in 30+ languages, "
        "and a Multi-Task Dispatcher that runs 6 requests in parallel.\n\n"
        "If you're new, start with [bold]sandbox mode[/] + the least skills you need. "
        "You can always enable more from the dashboard later.\n\n"
        f"[{GRAY}]Docs: https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5[/]"
    )
    glass_panel("🛡  Security · Please Read", sec_text, accent=WARN)

    if not QUESTIONARY_AVAILABLE:
        warn("questionary not installed — running in non-interactive mode")
        return True

    ok_continue = questionary.confirm(
        "I understand this is powerful and inherently risky. Continue?",
        default=True,
        style=automyx_style(),
    ).ask()
    if not ok_continue:
        warn("Setup aborted by user.")
        sys.exit(0)
    return True


# ============================================================================
# STEP 2 — Pick LLM
# ============================================================================
def step2_pick_llm() -> str:
    show_step_header(2, 6, "Pick your AI model", "Local = private · Cloud = faster · Switch anytime")

    local_choices = []
    try:
        from core.agent import OllamaManager
        models = OllamaManager.list_models() or []
        for m in models:
            name = m.get("name", "unknown")
            local_choices.append(Choice(f"🦙 {name} · LOCAL · $0", f"ollama/{name}"))
    except Exception:
        pass

    choices = [
        Separator(f"[{BLUE}]── Cloud (high-performance) ──[/]"),
        Choice("⚡ GPT-OSS-120b · NVIDIA API · default", "openai/gpt-oss-120b"),
        Choice("🧠 GLM-5.1 · NVIDIA API", "z-ai/glm-5.1"),
        Choice("🌐 MiniMax-m2.7 · NVIDIA API", "minimaxai/minimax-m2.7"),
        Choice("🔮 Kimi K2.6 · NVIDIA API", "moonshotai/kimi-k2.6"),
        Separator(f"[{BLUE}]── Commercial APIs ──[/]"),
        Choice("🅞 OpenAI · GPT-4o / o1", "openai/gpt-4o"),
        Choice("🅐 Anthropic · Claude 3.5 Sonnet", "anthropic/claude-3-5-sonnet-20240620"),
        Choice("🅖 Google · Gemini 1.5 Pro", "google/gemini-1.5-pro"),
        Choice("🅖 Groq · LPU inference", "groq"),
        Choice("🅜 Mistral AI", "mistral"),
    ]
    if local_choices:
        choices.insert(0, Separator(f"[{BLUE}]── Local (Ollama detected) ──[/]"))
        for c in local_choices:
            choices.insert(1, c)

    return questionary.select(
        "Model/auth provider:",
        choices=choices,
        style=automyx_style(),
        use_indicator=True,
        pointer="◆",
    ).ask() or "openai/gpt-oss-120b"


# ============================================================================
# STEP 3 — Pick channel
# ============================================================================
def step3_pick_channel() -> str:
    show_step_header(3, 6, "Pick a chat channel", "Optional — you can add more later from the dashboard")

    choices = [
        Separator(f"[{BLUE}]── Top messaging ──[/]"),
        Choice("✈  Telegram (Bot API)", "telegram"),
        Choice("🟢 WhatsApp (QR · Playwright)", "whatsapp"),
        Choice("💬 Discord (Bot API)", "discord"),
        Choice("🔷 Slack (Socket Mode)", "slack"),
        Choice("🟦 Microsoft Teams", "teams"),
        Separator(f"[{BLUE}]── Knowledge & PM ──[/]"),
        Choice("📚 Notion (Bot · API v1)", "notion"),
        Choice("📓 Obsidian (Local Vault)", "obsidian"),
        Choice("🗂  Trello / Asana / Jira / Linear", "pm_tools"),
        Separator(f"[{BLUE}]── Social ──[/]"),
        Choice("𝕏  X / Twitter", "twitter"),
        Choice("📷 Instagram (Graph API)", "instagram"),
        Choice("📘 Facebook Messenger", "messenger"),
        Choice("💼 LinkedIn", "linkedin"),
        Choice("📌 Reddit", "reddit"),
        Choice("🎵 TikTok (Desktop)", "tiktok"),
        Choice("▶  YouTube (Content API)", "youtube"),
        Choice("🎮 Twitch", "twitch"),
        Separator(f"[{BLUE}]── Regional ──[/]"),
        Choice("🇪🇸 iMessage · LINE · WeChat · KakaoTalk · Viber · VK", "regional"),
        Separator(f"[{BLUE}]── Skip for now ──[/]"),
        Choice("⏭  Skip · I'll use the Web dashboard only", "skip"),
    ]
    return questionary.select(
        "Primary channel:",
        choices=choices,
        style=automyx_style(),
        use_indicator=True,
        pointer="◆",
    ).ask() or "skip"


# ============================================================================
# Skill-to-Channel mapping: each skill recommends specific channels
# ============================================================================
SKILL_CHANNEL_MAP = {
    "telegram-bot": ["telegram"],
    "discord-bot": ["discord"],
    "whatsapp-bot": ["whatsapp"],
    "instagram-automation": ["instagram"],
    "social-media-manager": ["telegram", "discord", "instagram", "twitter"],
    "notion-integration": ["notion"],
    "github-automation": ["github"],
    "content-factory": ["telegram", "discord", "tiktok", "youtube"],
    "email-manager": ["email"],
    "slack-bot": ["slack"],
    "youtube-automation": ["youtube"],
    "tiktok-automation": ["tiktok"],
    "twitter-automation": ["twitter"],
    "twitch-bot": ["twitch"],
    "obsidian-integration": ["obsidian"],
    "pm-tools": ["pm_tools"],
}


def _get_recommended_channels(skills: list[str]) -> list[str]:
    """Returns recommended channels based on selected skills."""
    channels = set()
    for skill_name in skills:
        sname = skill_name.lower().replace(" ", "-")
        for key, chs in SKILL_CHANNEL_MAP.items():
            if key in sname or sname in key:
                channels.update(chs)
            # Also check partial match
            for word in sname.split("-"):
                if word in key or key in word:
                    channels.update(chs)
    return list(channels)


def _step3_5_skill_channels(skills: list[str], current_channel: str) -> str:
    """After skills are selected, recommend and let user pick a channel."""
    recommended = _get_recommended_channels(skills)
    if not recommended:
        return current_channel

    if not QUESTIONARY_AVAILABLE:
        info(f"Canales recomendados para tus skills: {', '.join(recommended)}")
        return current_channel

    show_step_header(3, 6, "Vincula tus skills a un canal",
                     "Skills y canales trabajan juntos. Elige el canal principal.")

    choices = []
    for ch in recommended:
        ch_names = {
            "telegram": "✈ Telegram Bot", "discord": "💬 Discord Bot",
            "whatsapp": "🟢 WhatsApp", "instagram": "📷 Instagram",
            "twitter": "𝕏 Twitter", "tiktok": "🎵 TikTok",
            "youtube": "▶ YouTube", "notion": "📚 Notion",
            "github": "🐙 GitHub", "email": "📧 Email",
            "slack": "🔷 Slack", "obsidian": "📓 Obsidian",
            "pm_tools": "🗂 PM Tools", "twitch": "🎮 Twitch",
        }
        label = ch_names.get(ch, f"🔌 {ch}")
        default = "✔ " if ch == current_channel else "  "
        choices.append(Choice(f"{default} {label}", ch))

    if current_channel and current_channel not in recommended:
        ch_names = {
            "telegram": "✈ Telegram Bot", "discord": "💬 Discord Bot",
            "whatsapp": "🟢 WhatsApp", "instagram": "📷 Instagram",
            "twitter": "𝕏 Twitter", "tiktok": "🎵 TikTok",
            "youtube": "▶ YouTube", "notion": "📚 Notion",
            "github": "🐙 GitHub", "email": "📧 Email",
            "slack": "🔷 Slack", "obsidian": "📓 Obsidian",
            "pm_tools": "🗂 PM Tools", "twitch": "🎮 Twitch",
            "skip": "⏭ Web Dashboard (sin canal externo)",
        }
        label = ch_names.get(current_channel, current_channel)
        choices.append(Choice(f"✔ {label} (actual)", current_channel))

    result = questionary.select(
        "¿Qué canal usarás con tus skills?",
        choices=choices,
        style=automyx_style(),
        use_indicator=True,
        pointer="◆",
    ).ask()

    return result or current_channel


# ============================================================================
# STEP 4 — Multi-select skills
# ============================================================================
STARTER_KIT = {
    "ai-ml-engineer", "prompt-engineer", "fullstack-developer",
    "memory-rag-vector", "skill-forger", "data-scientist",
    "content-factory", "copywriter", "seo-expert",
    "browser-stealth-rpa", "pdf-professional-creator",
}


def step4_pick_skills() -> list[str]:
    show_step_header(4, 6, "Pick the skills you want",
                     "Space to toggle · Enter to confirm · recommended: start small")

    skills = _load_skill_catalog()
    if not skills:
        warn("No se pudo cargar el catálogo de skills.")
        return []

    show_skill_grid()

    by_cat: dict[str, list] = {}
    for s in skills:
        by_cat.setdefault(s["category"], []).append(s)

    choices = []
    for cat, items in sorted(by_cat.items()):
        icon = items[0].get("icon", "🧩")
        choices.append(Separator(f"[{BLUE}]── {icon} {cat} ({len(items)} skills) ──[/]"))
        for s in items:
            checked = s["name"] in STARTER_KIT
            mark = "★" if checked else " "
            desc = s.get("description", "")[:55]
            label = f"{mark} {s['name']:<28}  {GRAY}{desc}[/]"
            choices.append(Choice(title=label, value=s["name"], checked=checked))

    choices.insert(0, Separator(f"[{BLUE}]── Tips ──[/]"))
    choices.insert(
        1,
        Choice(
            title=f"[{GLOW}]💡 Starter kit preselected (★). Space to toggle, Enter to confirm.[/]",
            value="__tip__",
            disabled=True,
        ),
    )

    selected = questionary.checkbox(
        "Toggle the skills you want enabled:",
        choices=choices,
        style=automyx_style(),
        validate=lambda sel: True,
    ).ask() or []

    return [s for s in selected if not s.startswith("__")]


# ============================================================================
# STEP 5 — Integrations
# ============================================================================
INTEGRATIONS = [
    {"id": "notion",     "name": "📚 Notion",
     "env": "NOTION_API_KEY",     "ask": "Paste your Notion Internal Integration Secret (ntn_... or secret_...):",
     "help_url": "https://www.notion.so/my-integrations"},
    {"id": "github",     "name": "🐙 GitHub",
     "env": "GITHUB_TOKEN",       "ask": "Paste a GitHub Personal Access Token (ghp_...):",
     "help_url": "https://github.com/settings/tokens"},
    {"id": "elevenlabs", "name": "🗣  ElevenLabs (TTS)",
     "env": "ELEVENLABS_API_KEY", "ask": "Paste your ElevenLabs API key:",
     "help_url": "https://elevenlabs.io/app/settings/api-keys"},
    {"id": "openai",     "name": "🅞 OpenAI (optional)",
     "env": "OPENAI_API_KEY",     "ask": "Paste your OpenAI API key (sk-...):",
     "help_url": "https://platform.openai.com/api-keys"},
    {"id": "anthropic",  "name": "🅐 Anthropic (optional)",
     "env": "ANTHROPIC_API_KEY",  "ask": "Paste your Anthropic API key (sk-ant-...):",
     "help_url": "https://console.anthropic.com/settings/keys"},
    {"id": "tavily",     "name": "🔍 Tavily (web search)",
     "env": "TAVILY_API_KEY",     "ask": "Paste your Tavily API key:",
     "help_url": "https://tavily.com"},
]


def step5_integrations() -> dict:
    show_step_header(5, 6, "Integrations & API keys",
                     "Optional — paste only the ones you use. Stored locally in .env")

    picked = questionary.checkbox(
        "Which integrations do you want to enable?",
        choices=[Choice(i["name"], value=i["id"]) for i in INTEGRATIONS],
        style=automyx_style(),
    ).ask() or []

    secrets = {}
    for integ in INTEGRATIONS:
        if integ["id"] not in picked:
            continue
        if RICH_AVAILABLE and console is not None:
            console.print(
                f"\n  [{CYAN}]{integ['name']}[/{CYAN}]  [{GRAY}]{integ['help_url']}[/{GRAY}]"
            )
        token = questionary.password(integ["ask"], style=automyx_style()).ask()
        if token and token.strip():
            secrets[integ["id"]] = {"env_var": integ["env"], "value": token.strip()}
            os.environ[integ["env"]] = token.strip()
            save_to_env(integ["env"], token.strip())
            ok(f"{integ['env']} saved.")
    return secrets


# ============================================================================
# STEP 6 — Confirm
# ============================================================================
def step6_confirm(state: dict) -> bool:
    show_step_header(6, 6, "Review & launch", "Confirm your selection · you can change it later from the dashboard")

    skills_str = ", ".join(state["skills"][:8])
    if len(state["skills"]) > 8:
        skills_str += f" … (+{len(state['skills'])-8})"
    if not skills_str:
        skills_str = f"[{WARN}]none selected (use only the base toolset)[/]"

    integ_str = ", ".join(state["integrations"].keys()) or f"[{GRAY}]none[/]"

    summary = (
        f"[{CYAN}]LLM model[/]            {state['model']}\n"
        f"[{CYAN}]Channel[/]              {state['channel']}\n"
        f"[{CYAN}]Skills enabled[/]       {len(state['skills'])} → {skills_str}\n"
        f"[{CYAN}]Integrations[/]         {integ_str}\n"
        f"[{CYAN}]Gateway port[/]         {config.get('gateway.port', 3500) if config else 3500}\n"
        f"[{CYAN}]Persistence[/]          state/onboard_state.json + state/automyx.sqlite"
    )
    glass_panel("📋  Configuration Summary", summary, accent=CYAN)

    return questionary.confirm("Save & finish?", default=True, style=automyx_style()).ask() or False


# ============================================================================
# Main
# ============================================================================
def run_onboarding():
    if not step1_welcome():
        return
    show_skill_grid()

    # Step 2
    model = step2_pick_llm()
    os.environ["AUTOMYX_MODEL"] = model
    save_to_env("AUTOMYX_MODEL", model)
    if model.startswith("openai/gpt-4") or model == "openai/gpt-4o":
        k = questionary.password("Enter OpenAI API Key (sk-...):", style=automyx_style()).ask()
        if k:
            os.environ["OPENAI_API_KEY"] = k
            save_to_env("OPENAI_API_KEY", k)
    elif model.startswith("anthropic/"):
        k = questionary.password("Enter Anthropic API Key (sk-ant-...):", style=automyx_style()).ask()
        if k:
            os.environ["ANTHROPIC_API_KEY"] = k
            save_to_env("ANTHROPIC_API_KEY", k)
    elif model.startswith("google/"):
        k = questionary.password("Enter Google Gemini API Key:", style=automyx_style()).ask()
        if k:
            os.environ["GEMINI_API_KEY"] = k
            save_to_env("GEMINI_API_KEY", k)

    # Step 3
    channel = step3_pick_channel()
    if channel == "telegram":
        k = questionary.password("Enter Telegram Bot Token:", style=automyx_style()).ask()
        if k:
            os.environ["TELEGRAM_BOT_TOKEN"] = k
            save_to_env("TELEGRAM_BOT_TOKEN", k)

    # Step 4
    skills = step4_pick_skills()
    ok(f"{len(skills)} skill(s) selected.")

    # Step 3.5 — Link skills to channels
    channel = _step3_5_skill_channels(skills, channel)

    # Step 5
    integrations = step5_integrations()

    # Step 6
    state = {
        "model": model,
        "channel": channel,
        "skills": skills,
        "integrations": integrations,
        "version": AUTOMYX_VERSION,
        "wizard_run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if not step6_confirm(state):
        warn("Setup cancelled. Re-run with: python automix.py onboard")
        return

    save_state(state)

    closing = (
        f"✅ Automyx is configured.\n\n"
        f"  • Model:    {model}\n"
        f"  • Channel:  {channel}\n"
        f"  • Skills:   {len(skills)} enabled\n"
        f"  • Tokens:   {len(integrations)} integration(s)\n\n"
        f"Run [bold {CYAN}]python automix.py gateway[/] to start the dashboard at "
        f"[bold]http://localhost:3500[/]"
    )
    glass_panel("🚀  Automyx is ready", closing, accent=OK)

    if questionary.confirm("Start the gateway + Telegram bot now?",
                            default=True, style=automyx_style()).ask():
        import subprocess
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        subprocess.Popen([sys.executable, "api/main.py"], creationflags=creationflags)
        if os.environ.get("TELEGRAM_BOT_TOKEN"):
            subprocess.Popen([sys.executable, "telegram_bot.py"], creationflags=creationflags)
        ok("Gateway + Telegram booted.")
        info("Close this window and open http://localhost:3500")
    else:
        info("Start later with:  python automix.py gateway")


# ============================================================================
# Backwards-compat exports
# ============================================================================
def show_skills_catalog():
    show_skill_grid()


def show_capabilities_summary():
    skills = _load_skill_catalog()
    by_cat = {}
    for s in skills:
        by_cat.setdefault(s["category"], []).append(s)
    if not RICH_AVAILABLE or console is None:
        print(f"Skill categories: {len(by_cat)}")
        print(f"Skills in catalog: {len(skills)}")
        return
    t = Table(title="[bold]Capabilities Summary[/]",
              box=rich_box.SIMPLE, border_style=BLUE,
              header_style=f"bold {CYAN}")
    t.add_column("Capability", style=CYAN)
    t.add_column("Count", style=GLOW, justify="right")
    t.add_row("Skill categories", str(len(by_cat)))
    t.add_row("Skills in catalog", str(len(skills)))
    t.add_row("Intents recognized", "30+")
    t.add_row("Tool aliases", "12,606")
    t.add_row("Multi-task workers", "6")
    console.print(t)


if __name__ == "__main__":
    run_onboarding()
