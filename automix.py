#!/usr/bin/env python3
"""
Automyx 2.5 — Command-Line Interface
=====================================
24+ commands for power users, automation, and CI/CD pipelines.

Visual: Electric blue glassmorphism via `core.ui`.
"""
from __future__ import annotations

import argparse
import sys
import os
import json
import time
import subprocess
import webbrowser
from pathlib import Path

# Make repo root importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ui import (
    NAVY, DEEP_BLUE, BLUE, ELECTRIC, CYAN, GLOW, WHITE, GRAY,
    WARN, OK, ERR, PURPLE, console,
    show_banner, show_step_header, glass_panel, ok, info, warn, err, section,
    automyx_style, AUTOMYX_VERSION, AUTOMYX_CODENAME, save_to_env,
    RICH_AVAILABLE, QUESTIONARY_AVAILABLE,
)
try:
    from core.config import config
except Exception:
    config = None


# ============================================================================
# Helpers
# ============================================================================
def _rich_table(title: str, columns: list, rows: list, styles: list = None):
    if not RICH_AVAILABLE or console is None:
        print(f"\n=== {title} ===")
        for row in rows:
            print("  " + " · ".join(str(c) for c in row))
        return
    from rich.table import Table
    from rich import box as rich_box
    t = Table(title=f"[bold {CYAN}]{title}[/]",
              box=rich_box.ROUNDED, border_style=BLUE,
              header_style=f"bold {CYAN}")
    styles = styles or [CYAN] * len(columns)
    for col, st in zip(columns, styles):
        t.add_column(col, style=st, no_wrap=False)
    for row in rows:
        t.add_row(*[str(c) for c in row])
    console.print(t)


def _kv_table(title: str, rows: list):
    _rich_table(title, ["Key", "Value"], rows, styles=[CYAN, WHITE])


# ============================================================================
# Command handlers
# ============================================================================
def cmd_version(args):
    show_banner(subtitle=f"v{AUTOMYX_VERSION} · {AUTOMYX_CODENAME}")
    body = (
        f"[{CYAN}]Version[/]        {AUTOMYX_VERSION}\n"
        f"[{CYAN}]Codename[/]       {AUTOMYX_CODENAME}\n"
        f"[{CYAN}]Channel[/]        {os.environ.get('AUTOMYX_CHANNEL', 'stable')}\n"
        f"[{CYAN}]Python[/]         {sys.version.split()[0]}\n"
        f"[{CYAN}]Platform[/]       {sys.platform}\n"
        f"[{CYAN}]Author[/]         Nexora Technology LLC\n"
        f"[{CYAN}]Repo[/]           https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5"
    )
    glass_panel("ℹ  About", body, accent=BLUE)


def cmd_gateway(args):
    from api.main import app, gateway
    show_banner(subtitle=f"Starting gateway on {args.host}:{args.port}")
    gateway.start(host=args.host, port=args.port)


def cmd_onboard(args):
    show_banner(subtitle="Interactive Setup Wizard · 6 steps")
    try:
        from core.onboard import run_onboarding
        run_onboarding()
    except KeyboardInterrupt:
        warn("Cancelled by user.")


def cmd_chat(args):
    show_banner(subtitle="Repl Mode · type 'exit' to leave")
    from core.agent import AutomyxAgent
    from core.ui import glass_panel
    agent = AutomyxAgent()
    if args.system:
        agent.system_prompt = args.system
    info(f"Model: {args.model or 'default'} · stream={not args.no_stream}")
    info("Tip: try 'ahorita metele a youtube reproducción de bad bunny'")
    while True:
        try:
            user = console.input(f"\n[{CYAN}]you[/{CYAN}] ❯ ") if RICH_AVAILABLE else input("\nyou ❯ ")
        except (EOFError, KeyboardInterrupt):
            print()
            warn("Bye.")
            return
        if user.strip().lower() in {"exit", "quit", "q", "salir"}:
            warn("Bye.")
            return
        if not user.strip():
            continue
        with console.status(f"[{ELECTRIC}]thinking...[/]", spinner="dots") if RICH_AVAILABLE else _nullctx():
            try:
                response = agent.run(user, model=args.model or None)
            except Exception as e:
                response = f"[ERR] {e}"
        if RICH_AVAILABLE and console is not None:
            glass_panel("AUTOMYX", response, accent=ELECTRIC)
        else:
            print(f"\nAUTOMYX → {response}\n")


def _nullctx():
    from contextlib import contextmanager
    @contextmanager
    def _cm():
        yield
    return _cm()


def cmd_dashboard(args):
    port = config.get("gateway.port", 3500) if config else 3500
    url = f"http://localhost:{port}"
    info(f"Opening dashboard at {url}")
    webbrowser.open(url)


def cmd_doctor(args):
    show_banner(subtitle="Health check")
    section("System")
    rows = [
        ("Python",     f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("Platform",   sys.platform),
        ("CWD",        os.getcwd()),
        ("AUTOMYX_MODEL", os.environ.get("AUTOMYX_MODEL", "(not set)")),
        ("TELEGRAM_BOT_TOKEN", "set" if os.environ.get("TELEGRAM_BOT_TOKEN") else "missing"),
        ("NOTION_API_KEY",     "set" if os.environ.get("NOTION_API_KEY") else "missing"),
        ("GITHUB_TOKEN",       "set" if os.environ.get("GITHUB_TOKEN") else "missing"),
    ]
    _kv_table("Environment", rows)

    section("Modules")
    modules = [
        ("rich",          "rich"),
        ("questionary",   "questionary"),
        ("fastapi",       "fastapi"),
        ("uvicorn",       "uvicorn"),
        ("httpx",         "httpx"),
        ("playwright",    "playwright"),
        ("telegram",      "telegram"),
        ("discord",       "discord"),
        ("PIL",           "PIL"),
    ]
    rows = []
    for label, mod in modules:
        try:
            __import__(mod)
            rows.append((label, f"{OK}installed"))
        except ImportError as e:
            rows.append((label, f"{ERR}{e}"))
    _kv_table("Optional deps", rows)

    section("Disk")
    state_dir = Path("state")
    state_dir.mkdir(exist_ok=True)
    rows = [
        ("state/onboard_state.json", "exists" if (state_dir / "onboard_state.json").exists() else "missing"),
        ("state/automyx.sqlite",     "exists" if (state_dir / "automyx.sqlite").exists() else "missing"),
        ("skills/ (count)",          str(len([d for d in Path('skills').iterdir() if d.is_dir()]) if Path('skills').is_dir() else 0)),
    ]
    _kv_table("Local state", rows)
    ok("Doctor finished. Look for ❌ in the tables above.")


def cmd_intent(args):
    show_banner(subtitle="Intent Engine — analyze a phrase")
    text = args.text or (console.input(f"[{CYAN}]❯ phrase[/{CYAN}] ") if RICH_AVAILABLE else input("❯ phrase "))
    if not text.strip():
        err("Empty input.")
        return
    from core.intent_engine import understand
    result = understand(text)
    rows = [
        ("Intent",      result.get("intent", "?")),
        ("Confidence",  f"{result.get('intent_confidence', 0):.2f}"),
        ("Normalized",  result.get("normalized", "")),
        ("Match",       result.get("matched_keyword", "")),
    ]
    ents = result.get("entities", {}) or {}
    if ents:
        for k, v in ents.items():
            rows.append((f"Entity.{k}", str(v)[:60]))
    _kv_table("Intent analysis", rows)
    if args.run:
        info("Executing...")
        from core.agent import AutomyxAgent
        response = AutomyxAgent().run(text)
        glass_panel("AUTOMYX", response, accent=ELECTRIC)


def cmd_multitask(args):
    show_banner(subtitle="Multi-Task Dispatcher · 6 parallel workers")
    from core.multi_task import MultiTaskDispatcher
    dp = MultiTaskDispatcher()

    if args.action == "submit":
        from core.agent import AutomyxAgent
        agent = AutomyxAgent()
        tasks = args.tasks if args.tasks else console.input(
            f"[{CYAN}]tasks (one per line, end with EOF)[/{CYAN}]\n"
        ).splitlines() if RICH_AVAILABLE else input("tasks (one per line):\n").splitlines()
        ids = []
        for t in tasks:
            t = t.strip()
            if not t:
                continue
            tid = dp.submit(agent, t)
            ids.append(tid)
            ok(f"Submitted {tid}: {t[:60]}")
        if args.wait:
            info("Waiting for completion...")
            dp.wait_all(timeout=args.timeout)
        return

    if args.action == "list":
        tasks = dp.list_tasks()
        if not tasks:
            warn("No tasks yet. Run: automix multitask submit -t 'task1' -t 'task2'")
            return
        rows = []
        for t in tasks[:50]:
            rows.append([
                t.task_id[:18],
                t.status.value,
                t.phase[:18],
                t.action[:36],
                str(t.progress),
            ])
        _rich_table("Active tasks", ["ID", "Status", "Phase", "Action", "%"], rows)
        return

    if args.action == "stats":
        stats = dp.stats()
        rows = [
            ("Total submitted", stats.get("total", 0)),
            ("Completed",       stats.get("completed", 0)),
            ("Failed",          stats.get("failed", 0)),
            ("Active workers",  stats.get("active_workers", 0)),
            ("Max workers",     stats.get("max_workers", 0)),
        ]
        _kv_table("Dispatcher stats", rows)
        return

    if args.action == "cancel":
        ok(f"Cancelled {dp.cancel(args.task_id)}")
        return


def cmd_skill(args):
    show_banner(subtitle="Skill Marketplace · 86 skills · 24 categories")
    from core.onboard import _load_skill_catalog
    skills = _load_skill_catalog()
    if args.action == "list":
        if not skills:
            err("No skills found.")
            return
        from collections import defaultdict
        by_cat = defaultdict(list)
        for s in skills:
            by_cat[s["category"]].append(s["name"])
        rows = []
        for cat, names in sorted(by_cat.items()):
            rows.append([cat, str(len(names)), ", ".join(names[:6]) + ("…" if len(names) > 6 else "")])
        _rich_table("Skills", ["Category", "Count", "Names"], rows, styles=[CYAN, GLOW, WHITE])
        info(f"Total: {len(skills)} skills in {len(by_cat)} categories.")
        return

    if args.action == "show":
        match = [s for s in skills if s["name"] == args.name]
        if not match:
            err(f"Skill not found: {args.name}")
            return
        s = match[0]
        body = (
            f"[{CYAN}]Name[/]        {s['name']}\n"
            f"[{CYAN}]Category[/]    {s['category']}\n"
            f"[{CYAN}]Icon[/]        {s['icon']}\n"
            f"[{CYAN}]Description[/] {s['description']}\n"
            f"[{CYAN}]Tools[/]       {s.get('tools', '')}"
        )
        glass_panel(f"{s['icon']} {s['name']}", body, accent=CYAN)
        # Try to show SKILL.md
        skill_path = Path("skills") / s["name"] / "SKILL.md"
        if skill_path.exists():
            section("SKILL.md (excerpt)")
            text = skill_path.read_text(encoding="utf-8", errors="ignore")[:1500]
            if RICH_AVAILABLE and console is not None:
                from rich.markdown import Markdown
                console.print(Markdown(text))
            else:
                print(text)
        return

    if args.action == "create":
        target = Path("skills") / args.name
        target.mkdir(parents=True, exist_ok=True)
        md = target / "SKILL.md"
        if not md.exists():
            md.write_text(
                f"# {args.name}\n\n"
                f"## Description\n{args.description or 'TODO: describe the skill.'}\n\n"
                f"## Tools\n- `my_tool(arg1, arg2)`: short description\n\n"
                f"## Examples\n```\n> user: 'do the thing'\n"
                f"  → calls my_tool(...)\n```\n",
                encoding="utf-8",
            )
        tools_dir = target / "tools"
        tools_dir.mkdir(exist_ok=True)
        tool_file = tools_dir / f"{args.name}.py"
        if not tool_file.exists():
            tool_file.write_text(
                '"""\n' + args.name + ' tool — autogenerated by `automix skill create`.\n"""\n'
                'def run(**kwargs):\n    return {"ok": True, "skill": "' + args.name + '"}\n',
                encoding="utf-8",
            )
        ok(f"Skill scaffolded at {target}")


def cmd_catalog(args):
    show_banner(subtitle="Tool Catalog · 12,606 aliases")
    if args.what == "tools":
        try:
            from tools.mega_tools import get_tool_catalog
            catalog = get_tool_catalog()
            rows = [[k, str(v)] for k, v in list(catalog.items())[:60]]
            _rich_table("Tools (top 60)", ["Tool", "Aliases"], rows, styles=[CYAN, GLOW])
            info(f"Total: {len(catalog)} tool entries.")
        except Exception as e:
            err(f"{e}")
        return

    if args.what == "aliases":
        try:
            from tools.mega_tools import get_aliases
            aliases = get_aliases()
            info(f"Total aliases: {len(aliases)}")
            sample = list(aliases.items())[:40]
            rows = [[k, v] for k, v in sample]
            _rich_table("Aliases (sample)", ["Alias", "Canonical tool"], rows, styles=[GLOW, WHITE])
        except Exception as e:
            err(f"{e}")
        return

    if args.what == "intents":
        try:
            from core.intent_engine import get_intent_catalog
            catalog = get_intent_catalog()
            rows = [[name, str(len(catalog[name])), ", ".join(catalog[name][:5])] for name in catalog]
            _rich_table("Intents", ["Intent", "Keywords", "Examples"], rows)
        except Exception as e:
            err(f"{e}")


def cmd_memory(args):
    show_banner(subtitle="Memory & RAG")
    if args.action == "search":
        try:
            from core.memory import search
            results = search(args.query, limit=args.limit)
            if not results:
                warn("No matches.")
                return
            for r in results[: args.limit]:
                if RICH_AVAILABLE and console is not None:
                    console.print(f"  [{CYAN}]•[/{CYAN}] {r}")
                else:
                    print(f"  • {r}")
        except Exception as e:
            err(f"{e}")
        return

    if args.action == "stats":
        try:
            from core.memory import stats
            s = stats()
            rows = [[k, str(v)] for k, v in s.items()]
            _rich_table("Memory stats", ["Key", "Value"], rows)
        except Exception as e:
            err(f"{e}")


def cmd_ollama(args):
    show_banner(subtitle="Ollama Manager")
    from core.agent import OllamaManager
    if args.ollama_command == "list":
        models = OllamaManager.list_models() or []
        if not models:
            warn("No Ollama models found locally. Install: https://ollama.com")
            return
        rows = [[m.get("name", "?"), f"{(m.get('size', 0) or 0) // (1024**3)} GB"] for m in models]
        _rich_table("Ollama models", ["Name", "Size"], rows)
        return
    if args.ollama_command == "pull":
        with console.status(f"[{ELECTRIC}]pulling {args.model}...[/]", spinner="dots") if RICH_AVAILABLE else _nullctx():
            ok("done" if OllamaManager.pull_model(args.model) else "failed")
        return
    if args.ollama_command == "launch":
        OllamaManager.launch_automyx(args.model, args.location)


def cmd_agent(args):
    show_banner(subtitle="Single-shot agent")
    from core.agent import AutomyxAgent
    response = AutomyxAgent().run(args.message)
    glass_panel("AUTOMYX", response, accent=ELECTRIC)


def cmd_config(args):
    if not config:
        err("config module not available")
        return
    if args.config_command == "list":
        _kv_table("Config", [(k, str(v) if not isinstance(v, dict) else "(nested)")
                               for k, v in config.config.items()])
    elif args.config_command == "get":
        ok(f"{args.key} = {config.get(args.key)}")
    elif args.config_command == "set":
        config.set(args.key, args.value)
        ok(f"{args.key} = {args.value}")


# ============================================================================
# Argparse
# ============================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="automix",
        description="Automyx 2.5 — The Intent-Aware Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  automix gateway                   Start the gateway on :3500
  automix onboard                   6-step glassmorphism wizard
  automix chat                      Interactive REPL
  automix dashboard                 Open web dashboard
  automix intent "ahorita metele a youtube"
  automix multitask submit -t "task A" -t "task B" -t "task C"
  automix skill list                Browse 86 skills
  automix catalog tools             Tool catalog
  automix doctor                    Health check

Docs: https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # 1) version
    sub.add_parser("version", help="Show version & author info")

    # 2) gateway
    g = sub.add_parser("gateway", help="Start the HTTP/WebSocket gateway")
    g.add_argument("--host", default="0.0.0.0")
    g.add_argument("--port", type=int, default=3500)
    g.add_argument("--verbose", action="store_true")

    # 3) onboard
    sub.add_parser("onboard", help="6-step glassmorphism setup wizard")

    # 4) chat
    c = sub.add_parser("chat", help="Interactive REPL with the agent")
    c.add_argument("--model", default=None)
    c.add_argument("--system", default=None)
    c.add_argument("--no-stream", action="store_true")

    # 5) dashboard
    sub.add_parser("dashboard", help="Open the web dashboard in a browser")

    # 6) doctor
    sub.add_parser("doctor", help="Health check (env, modules, disk)")

    # 7) agent (one-shot)
    a = sub.add_parser("agent", help="Single-shot agent invocation")
    a.add_argument("-m", "--message", required=True)

    # 8) intent
    i = sub.add_parser("intent", help="Analyze the intent of a phrase")
    i.add_argument("text", nargs="?", default=None)
    i.add_argument("--run", action="store_true", help="Actually execute the agent")

    # 9) multitask
    m = sub.add_parser("multitask", help="Submit/list/cancel parallel tasks")
    m_sub = m.add_subparsers(dest="action", required=True)
    sm = m_sub.add_parser("submit", help="Submit one or more tasks")
    sm.add_argument("-t", "--tasks", action="append", default=[])
    sm.add_argument("--wait", action="store_true")
    sm.add_argument("--timeout", type=float, default=120.0)
    m_sub.add_parser("list", help="List active tasks")
    m_sub.add_parser("stats", help="Show dispatcher stats")
    cm = m_sub.add_parser("cancel", help="Cancel a task by id")
    cm.add_argument("task_id")

    # 10) skill
    s = sub.add_parser("skill", help="Browse, show, or create skills")
    s_sub = s.add_subparsers(dest="action", required=True)
    s_sub.add_parser("list", help="List all 86 skills")
    ss = s_sub.add_parser("show", help="Show one skill's details")
    ss.add_argument("name")
    sc = s_sub.add_parser("create", help="Scaffold a new skill")
    sc.add_argument("name")
    sc.add_argument("--description", default="")

    # 11) catalog
    cat = sub.add_parser("catalog", help="Browse tools, aliases, intents")
    cat_sub = cat.add_subparsers(dest="what", required=True)
    cat_sub.add_parser("tools", help="Tool catalog")
    cat_sub.add_parser("aliases", help="Alias explosion")
    cat_sub.add_parser("intents", help="Intent catalog")

    # 12) memory
    mem = sub.add_parser("memory", help="Query the RAG memory")
    mem_sub = mem.add_subparsers(dest="action", required=True)
    ms = mem_sub.add_parser("search", help="Semantic search")
    ms.add_argument("query")
    ms.add_argument("--limit", type=int, default=10)
    mem_sub.add_parser("stats", help="Memory statistics")

    # 13) ollama
    o = sub.add_parser("ollama", help="Manage local Ollama models")
    o_sub = o.add_subparsers(dest="ollama_command", required=True)
    o_sub.add_parser("list", help="List installed models")
    op = o_sub.add_parser("pull", help="Download a model")
    op.add_argument("model")
    ol = o_sub.add_parser("launch", help="Launch Automyx with an Ollama model")
    ol.add_argument("--model", default="llama3.1:8b")
    ol.add_argument("--location", default="local", choices=["local", "cloud"])

    # 14) config
    conf = sub.add_parser("config", help="Get/set config values")
    conf_sub = conf.add_subparsers(dest="config_command", required=True)
    conf_sub.add_parser("list", help="List all config")
    cg = conf_sub.add_parser("get", help="Get a value")
    cg.add_argument("key")
    cs = conf_sub.add_parser("set", help="Set a value")
    cs.add_argument("key")
    cs.add_argument("value")

    # 15) install (one-click installer shortcut)
    inst = sub.add_parser("install", help="Run the one-click installer")
    inst.add_argument("--platform", default=None,
                       choices=["windows", "macos", "linux", "raspberry", "termux", "docker"])

    # 16) update
    sub.add_parser("update", help="Pull the latest from GitHub")

    # 17) skills (alias of skill)
    sub.add_parser("skills", help="Alias for 'skill list'")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        show_banner(subtitle=f"v{AUTOMYX_VERSION} · {AUTOMYX_CODENAME}")
        parser.print_help()
        return 0

    dispatch = {
        "version":   cmd_version,
        "gateway":   cmd_gateway,
        "onboard":   cmd_onboard,
        "chat":      cmd_chat,
        "dashboard": cmd_dashboard,
        "doctor":    cmd_doctor,
        "agent":     cmd_agent,
        "intent":    cmd_intent,
        "multitask": cmd_multitask,
        "skill":     cmd_skill,
        "skills":    lambda a: cmd_skill(argparse.Namespace(action="list")),
        "catalog":   cmd_catalog,
        "memory":    cmd_memory,
        "ollama":    cmd_ollama,
        "config":    cmd_config,
        "install":   lambda a: _run_install(a.platform),
        "update":    _run_update,
    }
    handler = dispatch.get(args.command)
    if not handler:
        parser.print_help()
        return 1
    try:
        handler(args)
    except KeyboardInterrupt:
        warn("Interrupted.")
        return 130
    except Exception as e:
        err(f"{type(e).__name__}: {e}")
        if os.environ.get("AUTOMYX_DEBUG") == "1":
            raise
        return 1
    return 0


def _run_install(platform):
    scripts = Path("installers")
    mapping = {
        "windows":   "windows_install.bat",
        "macos":     "macos_install.sh",
        "linux":     "linux_install.sh",
        "raspberry": "raspberry_install.sh",
        "termux":    "termux_install.sh",
        "docker":    "docker_install.sh",
    }
    if platform:
        script = mapping[platform]
    else:
        # Auto-detect
        if os.name == "nt":
            script = "windows_install.bat"
        elif os.path.exists("/data/data/com.termux"):
            script = "termux_install.sh"
        elif os.uname().machine.startswith("arm") or os.uname().machine.startswith("aarch"):
            script = "raspberry_install.sh"
        elif sys.platform == "darwin":
            script = "macos_install.sh"
        else:
            script = "linux_install.sh"
    p = scripts / script
    if not p.exists():
        err(f"Installer not found: {p}")
        return
    info(f"Running {p} ...")
    subprocess.run([str(p)], shell=(os.name == "nt"))


def _run_update(args):
    info("Pulling latest from origin/main ...")
    subprocess.run(["git", "pull", "--rebase", "origin", "main"])


if __name__ == "__main__":
    sys.exit(main() or 0)
