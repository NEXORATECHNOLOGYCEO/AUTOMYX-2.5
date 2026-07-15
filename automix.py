#!/usr/bin/env python3
"""
Automyx 2.5 — Punto de entrada unificado
"""
from __future__ import annotations

import os
# CRÍTICO: debe fijarse ANTES de que numpy/scipy carguen libifcoremd.dll (runtime
# Intel Fortran de Anaconda). Ese runtime instala su propio handler de Ctrl+C que
# ABORTA el proceso ("forrtl: error (200)") saltándose el handler de Python — era
# lo que sacaba al usuario de Automyx al presionar Ctrl+C.
os.environ.setdefault("FOR_DISABLE_CONSOLE_CTRL_HANDLER", "1")

import argparse
import sys
import json
import shutil
import subprocess
import webbrowser
from pathlib import Path

# ── repo root en path ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── carga .env antes de cualquier import ─────────────────────────────────────
def _load_dotenv() -> None:
    p = Path(os.path.dirname(os.path.abspath(__file__))) / ".env"
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
    from rich.columns import Columns
    from rich.align import Align
    from rich import box as _rbox
    RICH = True
except ImportError:
    RICH = False

# ── paleta hacker (misma que onboard_pro_v5 y automyx_cli_v5) ────────────────
O  = "#FF8C00"
B  = "#00AAFF"
G  = "#5EE6A8"
R  = "#FF4444"
DM = "#4A6A8A"
W  = "#F0F6FF"
PU = "#A855F7"
YL = "#FFD700"

VERSION  = "2.5.0"
CODENAME = "Intent-Aware Terminal"

# ── consola compartida ────────────────────────────────────────────────────────
try:
    from core.ui import console as _shared_console
    console = _shared_console
except Exception:
    console = Console() if RICH else None

try:
    from core.config import config as _cfg
except Exception:
    _cfg = None


# ─────────────────────────────────────────────────────────────────────────────
# Diseño unificado
# ─────────────────────────────────────────────────────────────────────────────

def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")

def _banner() -> None:
    """Banner ASCII con ballena azul."""
    if not console:
        print(f"AUTOMYX v{VERSION}")
        return
    _clear()

    # ── Logo bicolor ─────────────────────────────────────────────────────────
    art = Text()
    art.append("\n")
    art.append("  ▄█████╗  ██╗   ██╗████████╗  ██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗\n", style=f"bold {O}")
    art.append("  ██╔══██╗ ██║   ██║╚══██╔══╝ ██╔═══██╗████╗ ████║╚██╗ ██╔╝╚██╗██╔╝\n", style=f"bold {O}")
    art.append("  ███████║ ██║   ██║   ██║    ██║   ██║██╔████╔██║ ╚████╔╝  ╚███╔╝ \n", style=f"bold {B}")
    art.append("  ██╔══██║ ██║   ██║   ██║    ██║   ██║██║╚██╔╝██║  ╚██╔╝   ██╔██╗ \n", style=f"bold {B}")
    art.append("  ██║  ██║ ╚██████╔╝   ██║    ╚██████╔╝██║ ╚═╝ ██║   ██║   ██╔╝ ██╗\n", style=f"bold {O}")
    art.append("  ╚═╝  ╚═╝  ╚═════╝    ╚═╝     ╚═════╝ ╚═╝     ╚═╝   ╚═╝   ╚═╝  ╚═╝\n", style=f"dim {O}")
    art.append("\n")
    console.print(art)

    # ── Ballena azul ─────────────────────────────────────────────────────────
    whale = Text()
    whale.append("                         .-'\n",                            style=f"bold {B}")
    whale.append("                    '---( ()  ~  ∿  ∿  ∿\n",              style=f"bold {B}")
    whale.append("                        '-.\"  ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿~\n",  style=f"bold {B}")
    whale.append("                   ~~~∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿~~~\n",style=f"dim {B}")
    whale.append(f"   🐋  autonomous ai agent  ·  v{VERSION}  ·  {CODENAME.lower()}",
                 style=f"dim {DM}")
    console.print(Panel(whale, border_style=B, box=_rbox.HEAVY, padding=(0, 2)))
    console.print()

def _rule(title: str = "", color: str = "") -> None:
    if console:
        console.print(Rule(f"[bold {color or B}]{title}[/]", style=f"dim {color or B}"))

def _p(text: str = "") -> None:
    if console:
        console.print(text)
    else:
        print(text)

def _ok(msg: str)   -> None: _p(f"  [{G}]✓[/{G}]  {msg}")
def _warn(msg: str) -> None: _p(f"  [{YL}]⚠[/{YL}]  [{DM}]{msg}[/{DM}]")
def _err(msg: str)  -> None: _p(f"  [{R}]✗[/{R}]  [{R}]{msg}[/{R}]")
def _info(msg: str) -> None: _p(f"  [{DM}]{msg}[/{DM}]")

def _kv_table(title: str, rows: list) -> None:
    if not console:
        print(f"\n{title}")
        for r in rows:
            print(f"  {r[0]:<28} {r[1]}")
        return
    tbl = Table(
        box=_rbox.SIMPLE_HEAD, border_style=f"dim {B}",
        show_header=True, header_style=f"bold {O}", padding=(0, 2),
    )
    tbl.add_column("Clave",  style=f"bold {B}", width=28)
    tbl.add_column("Valor",  style=W,            max_width=54)
    for k, v in rows:
        tbl.add_row(str(k), str(v))
    _p(f"\n  [{O}]{title}[/{O}]")
    console.print(tbl)


# ─────────────────────────────────────────────────────────────────────────────
# Comandos
# ─────────────────────────────────────────────────────────────────────────────

def _start_telegram_direct(model: str = "") -> None:
    """Bot de Telegram directo (sin Gateway). Corre en su propio thread."""
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application, CommandHandler, MessageHandler,
            CallbackQueryHandler, filters, ContextTypes,
        )
    except ImportError:
        print("[Telegram] ⚠  python-telegram-bot no instalado: pip install python-telegram-bot")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return

    import threading
    import asyncio

    _agents: dict = {}
    _agents_lock  = threading.Lock()
    _user_models: dict = {}

    def _get_agent(chat_id: str, model_name: str = ""):
        with _agents_lock:
            if chat_id not in _agents:
                from core.agent import AutomyxAgent
                a = AutomyxAgent(model_name=model_name or model or "")
                try:
                    from core.tool_registry import register_all_tools
                    register_all_tools(a)
                except Exception:
                    pass
                _agents[chat_id] = a
            return _agents[chat_id]

    async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *¡Hola! Soy Automyx.*\n\n"
            "Puedo ejecutar tareas en tu PC: abrir programas, buscar en internet, "
            "crear archivos, desplegar proyectos, correr código y mucho más.\n\n"
            "Solo escríbeme lo que necesitas. ¿En qué te ayudo?",
            parse_mode="Markdown",
        )

    async def _cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
        kb = [
            [InlineKeyboardButton("⚡ GPT-OSS-120b (NVIDIA)",  callback_data="m:openai/gpt-oss-120b")],
            [InlineKeyboardButton("🌐 GLM-5.1 (NVIDIA)",       callback_data="m:z-ai/glm-5.1")],
            [InlineKeyboardButton("🔮 Kimi K2.6 (NVIDIA)",     callback_data="m:moonshotai/kimi-k2.6")],
            [InlineKeyboardButton("🧠 Claude Sonnet 4.5",      callback_data="m:claude-sonnet-4-5")],
            [InlineKeyboardButton("🤖 GPT-4o",                 callback_data="m:gpt-4o")],
        ]
        await update.message.reply_text(
            "Elige el modelo para esta sesión:",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    async def _btn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        if q.data.startswith("m:"):
            m = q.data[2:]
            uid = str(q.from_user.id)
            _user_models[uid] = m
            chat_id = str(q.message.chat_id)
            with _agents_lock:
                _agents.pop(chat_id, None)  # reinicia agente con el nuevo modelo
            await q.edit_message_text(f"✅ Modelo cambiado a `{m}`", parse_mode="Markdown")

    async def _handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = (update.message.text or "").strip()
        if not msg:
            return
        chat_id   = str(update.message.chat_id)
        user_name = update.effective_user.first_name or "?"
        uid       = str(update.effective_user.id)
        sel_model = _user_models.get(uid, model or "")

        print(f"[Telegram] {user_name}: {msg[:100]}")

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
        except Exception:
            pass

        agent = _get_agent(chat_id, sel_model)
        loop  = asyncio.get_event_loop()

        # Mantener "typing" mientras el agente trabaja
        _done = asyncio.Event()

        async def _keep_typing():
            while not _done.is_set():
                try:
                    await context.bot.send_chat_action(
                        chat_id=update.effective_chat.id, action="typing"
                    )
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(_done.wait(), timeout=4.5)
                except asyncio.TimeoutError:
                    pass

        typing_task = asyncio.ensure_future(_keep_typing())
        try:
            reply = await loop.run_in_executor(None, lambda: agent.run(msg))
        except Exception as e:
            reply = f"❌ Error: {e}"
        finally:
            _done.set()
            try:
                typing_task.cancel()
            except Exception:
                pass

        reply = (reply or "").strip() or "✅ Tarea completada."

        # Telegram limita a 4096 chars por mensaje
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])

        print(f"[Telegram] ✓ Respondido a {user_name} ({len(reply)} chars)")

    async def _handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.caption:
            update.message.text = "Describe esta imagen"
        else:
            update.message.text = update.message.caption
        await _handle_msg(update, context)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",  _cmd_start))
    app.add_handler(CommandHandler("model",  _cmd_model))
    app.add_handler(CallbackQueryHandler(_btn_callback))
    app.add_handler(MessageHandler(filters.PHOTO, _handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_msg))

    print(f"[Telegram] ✅ Bot iniciado (modo directo)")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"[Telegram] Error: {e}")


def cmd_default(args):
    """Sin subcomando → arranca el CLI hacker completo + Telegram si hay token."""
    # ── Telegram en background si TELEGRAM_BOT_TOKEN está en .env ──────────
    _tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if _tg_token:
        import threading
        _tg_thread = threading.Thread(
            target=_start_telegram_direct,
            args=(getattr(args, "model", "") or "",),
            daemon=True,
            name="automyx-telegram",
        )
        _tg_thread.start()
        if console:
            console.print(f"  [{G}]✓[/{G}]  [{DM}]Telegram bot iniciado en segundo plano[/{DM}]")

    try:
        from core.automyx_cli_v5 import AutomyxCLI
        AutomyxCLI(
            model=getattr(args, "model", "") or "",
            verbose=getattr(args, "verbose", False),
        ).start()
    except KeyboardInterrupt:
        pass


def cmd_onboard(args):
    try:
        from core.onboard_pro_v5 import run_onboarding
        run_onboarding()
    except KeyboardInterrupt:
        _warn("Cancelado.")


def cmd_version(args):
    _banner()
    _rule("SOBRE AUTOMYX", O)
    rows = [
        ("Versión",    VERSION),
        ("Codename",   CODENAME),
        ("Canal",      os.environ.get("AUTOMYX_CHANNEL", "stable")),
        ("Python",     sys.version.split()[0]),
        ("Plataforma", sys.platform),
        ("Autor",      "Nexora Technology LLC"),
        ("Repo",       "https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5"),
    ]
    _kv_table("Información", rows)
    _p()


def cmd_doctor(args):
    _banner()
    _rule("DIAGNÓSTICO DEL SISTEMA", B)
    _p()

    # ── sistema ───────────────────────────────────────────────────────────
    rows = [
        ("Python",            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("Plataforma",        sys.platform),
        ("Directorio actual", os.getcwd()),
        ("AUTOMYX_MODEL",     os.environ.get("AUTOMYX_MODEL", "(no configurado)")),
        ("AUTOMYX_PROVIDER",  os.environ.get("AUTOMYX_PROVIDER", "(no configurado)")),
    ]
    _kv_table("Sistema", rows)
    _p()

    # ── integraciones ─────────────────────────────────────────────────────
    intg_rows = []
    intg_map = {
        "NVIDIA_API_KEY":     "NVIDIA NIM",
        "ANTHROPIC_API_KEY":  "Anthropic",
        "OPENAI_API_KEY":     "OpenAI",
        "NOTION_API_KEY":     "Notion",
        "GITHUB_TOKEN":       "GitHub",
        "TELEGRAM_BOT_TOKEN": "Telegram",
        "DISCORD_BOT_TOKEN":  "Discord",
        "ELEVENLABS_API_KEY": "ElevenLabs",
        "OPENWEATHER_API_KEY":"OpenWeather",
    }
    for env, label in intg_map.items():
        val = os.environ.get(env, "")
        if val:
            masked = val[:6] + "···" + val[-4:] if len(val) > 12 else "···"
            intg_rows.append((label, f"[{G}]✓  configurado[/{G}]  [{DM}]({masked})[/{DM}]"))
        else:
            intg_rows.append((label, f"[{DM}]✗  no configurado[/{DM}]"))
    _kv_table("Integraciones", intg_rows)
    _p()

    # ── herramientas del sistema ──────────────────────────────────────────
    tools = [("python", "Runtime"), ("git", "Control versiones"),
             ("ffmpeg", "Video/audio"), ("node", "Node.js")]
    tool_rows = []
    for t, desc in tools:
        found = shutil.which(t)
        if found:
            try:
                ver = subprocess.check_output(
                    [t, "--version"], stderr=subprocess.STDOUT,
                    timeout=3, text=True, errors="replace"
                ).splitlines()[0][:30]
            except Exception:
                ver = "?"
            tool_rows.append((f"{t}  ({desc})", f"[{G}]✓[/{G}]  {ver}"))
        else:
            tool_rows.append((f"{t}  ({desc})", f"[{DM}]✗  no encontrado[/{DM}]"))
    _kv_table("Herramientas del sistema", tool_rows)
    _p()

    # ── módulos Python ────────────────────────────────────────────────────
    mods = [
        ("rich", "UI terminal"), ("requests", "HTTP"),
        ("fastapi", "Gateway API"), ("uvicorn", "Servidor ASGI"),
        ("anthropic", "SDK Anthropic"), ("openai", "SDK OpenAI"),
        ("telegram", "Bot Telegram"), ("discord", "Bot Discord"),
    ]
    mod_rows = []
    for mod, desc in mods:
        try:
            __import__(mod)
            mod_rows.append((f"{mod}  ({desc})", f"[{G}]✓  instalado[/{G}]"))
        except ImportError:
            mod_rows.append((f"{mod}  ({desc})", f"[{DM}]✗  pip install {mod}[/{DM}]"))
    _kv_table("Módulos Python", mod_rows)
    _p()
    _ok("Doctor terminado.")
    _p()


def cmd_chat(args):
    """REPL básico sin la UI hacker completa (modo debug/CI)."""
    _banner()
    _rule("MODO CHAT — REPL DIRECTO", B)
    _p()

    from core.agent import AutomyxAgent
    agent = AutomyxAgent(model_name=getattr(args, "model", "") or "")
    try:
        from core.tool_registry import register_all_tools
        n = register_all_tools(agent)
        _info(f"{n} herramientas cargadas")
    except Exception as e:
        _warn(f"Tool registry: {e}")
    if getattr(args, "system", None):
        agent.system_prompt = args.system
    _info("Escribe 'exit' para salir.")
    _p()

    while True:
        try:
            if console:
                user = console.input(f"  [{B}]tú ❯[/{B}] ")
            else:
                user = input("  tú ❯ ")
        except (EOFError, KeyboardInterrupt):
            _p()
            _warn("Sesión cerrada.")
            return
        if user.strip().lower() in {"exit", "quit", "q", "salir"}:
            _warn("Sesión cerrada.")
            return
        if not user.strip():
            continue
        try:
            if console:
                with console.status(f"[{B}]pensando...[/]", spinner="dots"):
                    resp = agent.run(user, model=getattr(args, "model", None) or None)
            else:
                resp = agent.run(user)
        except Exception as e:
            resp = f"Error: {e}"
        if console:
            console.print(Panel(
                resp,
                title=f"[bold {O}]Automyx[/]",
                border_style=f"dim {B}",
                box=_rbox.ROUNDED,
                padding=(1, 3),
            ))
        else:
            print(f"\n  Automyx → {resp}\n")


def cmd_agent(args):
    """Invocación one-shot del agente."""
    _banner()
    _rule("AGENTE ONE-SHOT", O)
    _p()
    from core.agent import AutomyxAgent
    agent = AutomyxAgent()
    try:
        from core.tool_registry import register_all_tools
        register_all_tools(agent)
    except Exception:
        pass
    resp = agent.run(args.message)
    if console:
        console.print(Panel(
            resp,
            title=f"[bold {O}]Automyx[/]",
            border_style=f"dim {B}",
            box=_rbox.ROUNDED,
            padding=(1, 3),
        ))
    else:
        print(resp)


def cmd_intent(args):
    _banner()
    _rule("MOTOR DE INTENCIONES", B)
    _p()
    if not args.text:
        args.text = (console.input(f"  [{B}]❯ frase[/{B}] ") if console else input("  ❯ frase: "))
    if not args.text.strip():
        _err("Texto vacío.")
        return
    from core.intent_engine import understand
    result = understand(args.text)
    rows = [
        ("Intención",   result.get("intent", "?")),
        ("Confianza",   f"{result.get('intent_confidence', 0):.2f}"),
        ("Normalizado", result.get("normalized", "")),
        ("Match",       result.get("matched_keyword", "")),
    ]
    for k, v in (result.get("entities") or {}).items():
        rows.append((f"Entidad.{k}", str(v)[:60]))
    _kv_table("Análisis de intención", rows)
    if args.run:
        _p()
        _info("Ejecutando...")
        from core.agent import AutomyxAgent
        agent = AutomyxAgent()
        try:
            from core.tool_registry import register_all_tools
            register_all_tools(agent)
        except Exception:
            pass
        resp = agent.run(args.text)
        if console:
            console.print(Panel(resp, title=f"[bold {O}]Automyx[/]",
                                border_style=f"dim {B}", box=_rbox.ROUNDED, padding=(1, 3)))
        else:
            print(resp)


def cmd_multitask(args):
    _banner()
    _rule("MULTITAREA — 6 WORKERS PARALELOS", PU)
    _p()
    from core.multi_task import MultiTaskDispatcher
    dp = MultiTaskDispatcher()

    if args.action == "submit":
        from core.agent import AutomyxAgent
        agent = AutomyxAgent()
        try:
            from core.tool_registry import register_all_tools
            register_all_tools(agent)
        except Exception:
            pass
        tasks = args.tasks or []
        if not tasks:
            raw = (console.input(f"  [{B}]Tareas (una por línea, Enter vacío para terminar)[/{B}]\n")
                   if console else input("  Tareas:\n"))
            tasks = [l.strip() for l in raw.splitlines() if l.strip()]
        for t in tasks:
            tid = dp.submit(t, agent=agent)
            _ok(f"[{DM}]{tid}[/{DM}]  {t[:60]}")
        if args.wait:
            _info("Esperando finalización...")
            dp.wait_all(timeout=args.timeout)
        return

    if args.action == "list":
        tasks = dp.list_tasks()
        if not tasks:
            _warn("Sin tareas activas.")
            return
        tbl = Table(box=_rbox.SIMPLE_HEAD, border_style=f"dim {B}",
                    header_style=f"bold {O}", padding=(0, 2))
        tbl.add_column("ID",       style=f"bold {B}", width=20)
        tbl.add_column("Estado",   style=W,            width=14)
        tbl.add_column("Acción",   style=DM,           max_width=40)
        tbl.add_column("%",        justify="right",    width=6)
        for t in tasks[:50]:
            st   = t.status.value if hasattr(t.status, "value") else str(t.status)
            act  = getattr(t, "current_action", "") or ""
            prog = getattr(t, "progress", 0.0)
            tbl.add_row(t.task_id[:18], st, act[:40], f"{int(prog*100)}%")
        if console:
            console.print(tbl)
        return

    if args.action == "stats":
        s = dp.stats()
        rows = [
            ("Total enviadas",  s.get("total", 0)),
            ("Completadas",     s.get("completed", 0)),
            ("Fallidas",        s.get("failed", 0)),
            ("Workers activos", s.get("active_workers", 0)),
            ("Max workers",     s.get("max_workers", 0)),
        ]
        _kv_table("Estadísticas del dispatcher", rows)
        return

    if args.action == "cancel":
        _ok(f"Cancelada: {dp.cancel(args.task_id)}")


def cmd_skill(args):
    _banner()
    _rule("SKILLS — MARKETPLACE", PU)
    _p()
    from core.onboard import _load_skill_catalog
    skills = _load_skill_catalog()

    if args.action == "list":
        if not skills:
            _err("No se encontraron skills.")
            return
        from collections import defaultdict
        by_cat: dict = defaultdict(list)
        for s in skills:
            by_cat[s["category"]].append(s["name"])
        tbl = Table(box=_rbox.SIMPLE_HEAD, border_style=f"dim {B}",
                    header_style=f"bold {O}", padding=(0, 2))
        tbl.add_column("Categoría", style=f"bold {B}",  width=22)
        tbl.add_column("Skills",    style=DM,            width=6)
        tbl.add_column("Nombres",   style=W,             max_width=52)
        for cat, names in sorted(by_cat.items()):
            tbl.add_row(cat, str(len(names)),
                        ", ".join(names[:6]) + ("…" if len(names) > 6 else ""))
        if console:
            console.print(tbl)
        _p(f"  [{DM}]Total: {len(skills)} skills en {len(by_cat)} categorías.[/{DM}]")
        return

    if args.action == "show":
        match = [s for s in skills if s["name"] == args.name]
        if not match:
            _err(f"Skill no encontrado: {args.name}")
            return
        s = match[0]
        rows = [
            ("Nombre",      s["name"]),
            ("Categoría",   s["category"]),
            ("Descripción", s["description"]),
            ("Tools",       s.get("tools", "")),
        ]
        _kv_table(f"{s.get('icon', '·')}  {s['name']}", rows)
        sp = Path("skills") / s["name"] / "SKILL.md"
        if sp.exists() and console:
            from rich.markdown import Markdown
            console.print(Markdown(sp.read_text(encoding="utf-8", errors="ignore")[:1500]))
        return

    if args.action == "create":
        target = Path("skills") / args.name
        target.mkdir(parents=True, exist_ok=True)
        md = target / "SKILL.md"
        if not md.exists():
            md.write_text(
                f"# {args.name}\n\n## Descripción\n{args.description or 'TODO'}\n\n"
                f"## Tools\n- `mi_tool(arg)`: descripción\n\n## Ejemplos\n```\n"
                f"> user: 'haz algo'\n  → llama mi_tool(...)\n```\n",
                encoding="utf-8",
            )
        (target / "tools").mkdir(exist_ok=True)
        tf = target / "tools" / f"{args.name}.py"
        if not tf.exists():
            tf.write_text(
                f'def run(**kwargs):\n    return {{"ok": True, "skill": "{args.name}"}}\n',
                encoding="utf-8",
            )
        _ok(f"Skill creado en {target}")


def cmd_memory(args):
    _banner()
    _rule("MEMORIA Y RAG", B)
    _p()
    if args.action == "search":
        try:
            from core.memory import search
            results = search(args.query, limit=args.limit)
            if not results:
                _warn("Sin resultados.")
                return
            for r in results[:args.limit]:
                _p(f"  [{B}]·[/{B}] {r}")
        except Exception as e:
            _err(str(e))
        return
    if args.action == "stats":
        try:
            from core.memory import stats
            s = stats()
            _kv_table("Estadísticas de memoria", [(k, str(v)) for k, v in s.items()])
        except Exception as e:
            _err(str(e))


def cmd_ollama(args):
    _banner()
    _rule("OLLAMA — MODELOS LOCALES", G)
    _p()
    from core.agent import OllamaManager
    if args.ollama_command == "list":
        models = OllamaManager.list_models() or []
        if not models:
            _warn("Sin modelos Ollama locales. Instala: https://ollama.com")
            return
        tbl = Table(box=_rbox.SIMPLE_HEAD, border_style=f"dim {B}",
                    header_style=f"bold {O}", padding=(0, 2))
        tbl.add_column("Modelo", style=f"bold {W}", width=30)
        tbl.add_column("Tamaño", style=DM,           width=10)
        for m in models:
            tbl.add_row(m.get("name", "?"),
                        f"{(m.get('size', 0) or 0) // (1024**3)} GB")
        if console:
            console.print(tbl)
        return
    if args.ollama_command == "pull":
        if console:
            with console.status(f"[{B}]descargando {args.model}...[/]", spinner="dots"):
                result = OllamaManager.pull_model(args.model)
        else:
            result = OllamaManager.pull_model(args.model)
        (_ok if result else _err)(f"{'Descargado' if result else 'Error'}: {args.model}")
        return
    if args.ollama_command == "launch":
        OllamaManager.launch_automyx(args.model, args.location)


def cmd_gateway(args):
    _banner()
    _rule(f"GATEWAY — {args.host}:{args.port}", B)
    _p()
    from api.main import app, gateway
    gateway.start(host=args.host, port=args.port)


def cmd_dashboard(args):
    _banner()
    port = _cfg.get("gateway.port", 3500) if _cfg else 3500
    url  = f"http://localhost:{port}"
    _info(f"Abriendo dashboard en {url}")
    webbrowser.open(url)


def cmd_config(args):
    _banner()
    _rule("CONFIGURACIÓN", B)
    _p()
    if not _cfg:
        _err("Módulo config no disponible.")
        return
    if args.config_command == "list":
        _kv_table("Valores", [(k, str(v) if not isinstance(v, dict) else "(anidado)")
                               for k, v in _cfg.config.items()])
    elif args.config_command == "get":
        _ok(f"{args.key} = {_cfg.get(args.key)}")
    elif args.config_command == "set":
        _cfg.set(args.key, args.value)
        _ok(f"{args.key} = {args.value}")


def cmd_catalog(args):
    _banner()
    _rule("CATÁLOGO DE HERRAMIENTAS", O)
    _p()
    if args.what == "tools":
        try:
            from tools.mega_tools import get_tool_catalog
            cat = get_tool_catalog()
            rows = [[k, str(v)] for k, v in list(cat.items())[:60]]
            _kv_table(f"Herramientas (primeras 60 de {len(cat)})", rows)
        except Exception as e:
            _err(str(e))
        return
    if args.what == "aliases":
        try:
            from tools.mega_tools import get_aliases
            aliases = get_aliases()
            _info(f"Total aliases: {len(aliases)}")
            _kv_table("Aliases (muestra)", [[k, v] for k, v in list(aliases.items())[:40]])
        except Exception as e:
            _err(str(e))
        return
    if args.what == "intents":
        try:
            from core.intent_engine import get_intent_catalog
            cat = get_intent_catalog()
            rows = [[n, str(len(cat[n])), ", ".join(cat[n][:5])] for n in cat]
            if console:
                tbl = Table(box=_rbox.SIMPLE_HEAD, border_style=f"dim {B}",
                            header_style=f"bold {O}", padding=(0, 2))
                tbl.add_column("Intención",  style=f"bold {B}", width=22)
                tbl.add_column("Keywords",   style=DM,           width=8)
                tbl.add_column("Ejemplos",   style=W,            max_width=48)
                for r in rows:
                    tbl.add_row(*r)
                console.print(tbl)
        except Exception as e:
            _err(str(e))


def _run_install(platform_name):
    scripts = Path("installers")
    mapping = {
        "windows":   "windows_install.bat",
        "macos":     "macos_install.sh",
        "linux":     "linux_install.sh",
        "raspberry": "raspberry_install.sh",
        "termux":    "termux_install.sh",
        "docker":    "docker_install.sh",
    }
    if platform_name:
        script = mapping.get(platform_name, "linux_install.sh")
    elif os.name == "nt":
        script = "windows_install.bat"
    elif os.path.exists("/data/data/com.termux"):
        script = "termux_install.sh"
    elif sys.platform == "darwin":
        script = "macos_install.sh"
    else:
        script = "linux_install.sh"
    p = scripts / script
    if not p.exists():
        _err(f"Instalador no encontrado: {p}")
        return
    _info(f"Ejecutando {p} ...")
    subprocess.run([str(p)], shell=(os.name == "nt"))


def _run_update(args):
    _info("Descargando última versión de origin/main ...")
    subprocess.run(["git", "pull", "--rebase", "origin", "main"])


# ─────────────────────────────────────────────────────────────────────────────
# Argparse
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="automyx",
        description="Automyx 2.5 — Autonomous AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Uso rápido
──────────
  python automyx.py                  Arranca el agente (modo hacker)
  python automyx.py onboard          Wizard de configuración
  python automyx.py doctor           Diagnóstico del sistema
  python automyx.py version          Ver versión y autor
  python automyx.py chat             REPL directo sin UI
  python automyx.py agent -m "..."   One-shot
  python automyx.py multitask submit -t "tarea"
  python automyx.py skill list
  python automyx.py ollama list
        """,
    )
    parser.add_argument("--model",   "-m", default="", help="Modelo a usar al arrancar")
    parser.add_argument("--verbose", "-v", action="store_true")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("onboard",   help="Wizard de configuración (6 pasos, diseño hacker)")
    cr = sub.add_parser("cron", help="Ejecutar una tarea programada (headless, usado por el Programador de Windows)")
    cr.add_argument("schedule_id", help="ID de la tarea programada")
    sub.add_parser("version",   help="Ver versión, codename y autor")
    sub.add_parser("doctor",    help="Diagnóstico: sistema, integraciones, módulos")
    sub.add_parser("dashboard", help="Abrir dashboard web en el navegador")
    sub.add_parser("update",    help="Actualizar desde GitHub")

    # chat
    c = sub.add_parser("chat", help="REPL directo (modo debug/CI)")
    c.add_argument("--model",     default=None)
    c.add_argument("--system",    default=None)
    c.add_argument("--no-stream", action="store_true")

    # agent one-shot
    a = sub.add_parser("agent", help="Invocación one-shot del agente")
    a.add_argument("-m", "--message", required=True)

    # intent
    i = sub.add_parser("intent", help="Analizar intención de una frase")
    i.add_argument("text", nargs="?", default=None)
    i.add_argument("--run", action="store_true")

    # multitask
    mt = sub.add_parser("multitask", help="Enviar / listar / cancelar tareas paralelas")
    mt_sub = mt.add_subparsers(dest="action", required=True)
    ms = mt_sub.add_parser("submit")
    ms.add_argument("-t", "--tasks", action="append", default=[])
    ms.add_argument("--wait", action="store_true")
    ms.add_argument("--timeout", type=float, default=120.0)
    mt_sub.add_parser("list")
    mt_sub.add_parser("stats")
    mc = mt_sub.add_parser("cancel")
    mc.add_argument("task_id")

    # skill
    sk = sub.add_parser("skill", help="Marketplace de skills")
    sk_sub = sk.add_subparsers(dest="action", required=True)
    sk_sub.add_parser("list")
    ss = sk_sub.add_parser("show")
    ss.add_argument("name")
    sc = sk_sub.add_parser("create")
    sc.add_argument("name")
    sc.add_argument("--description", default="")
    sub.add_parser("skills", help="Alias de 'skill list'")

    # catalog
    cat = sub.add_parser("catalog", help="Catálogo de tools, aliases, intents")
    cat_sub = cat.add_subparsers(dest="what", required=True)
    cat_sub.add_parser("tools")
    cat_sub.add_parser("aliases")
    cat_sub.add_parser("intents")

    # memory
    mem = sub.add_parser("memory", help="Buscar en memoria RAG")
    mem_sub = mem.add_subparsers(dest="action", required=True)
    ms2 = mem_sub.add_parser("search")
    ms2.add_argument("query")
    ms2.add_argument("--limit", type=int, default=10)
    mem_sub.add_parser("stats")

    # ollama
    ol = sub.add_parser("ollama", help="Gestionar modelos Ollama locales")
    ol_sub = ol.add_subparsers(dest="ollama_command", required=True)
    ol_sub.add_parser("list")
    op = ol_sub.add_parser("pull")
    op.add_argument("model")
    ola = ol_sub.add_parser("launch")
    ola.add_argument("--model", default="llama3.1:8b")
    ola.add_argument("--location", default="local", choices=["local", "cloud"])

    # gateway
    gw = sub.add_parser("gateway", help="Iniciar gateway HTTP/WebSocket")
    gw.add_argument("--host", default="0.0.0.0")
    gw.add_argument("--port", type=int, default=3500)
    gw.add_argument("--verbose", action="store_true")

    # config
    cf = sub.add_parser("config", help="Leer / escribir configuración")
    cf_sub = cf.add_subparsers(dest="config_command", required=True)
    cf_sub.add_parser("list")
    cg = cf_sub.add_parser("get")
    cg.add_argument("key")
    cs = cf_sub.add_parser("set")
    cs.add_argument("key")
    cs.add_argument("value")

    # install
    inst = sub.add_parser("install", help="Instalador one-click")
    inst.add_argument("--platform", default=None,
                      choices=["windows", "macos", "linux", "raspberry", "termux", "docker"])

    return parser


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = _build_parser()
    args   = parser.parse_args()

    dispatch = {
        "onboard":   cmd_onboard,
        "cron":      lambda a: sys.exit(__import__("core.scheduler", fromlist=["run_headless"]).run_headless(a.schedule_id)),
        "version":   cmd_version,
        "doctor":    cmd_doctor,
        "chat":      cmd_chat,
        "dashboard": cmd_dashboard,
        "agent":     cmd_agent,
        "intent":    cmd_intent,
        "multitask": cmd_multitask,
        "skill":     cmd_skill,
        "skills":    lambda a: cmd_skill(argparse.Namespace(action="list")),
        "catalog":   cmd_catalog,
        "memory":    cmd_memory,
        "ollama":    cmd_ollama,
        "gateway":   cmd_gateway,
        "config":    cmd_config,
        "install":   lambda a: _run_install(getattr(a, "platform", None)),
        "update":    _run_update,
    }

    if not args.command:
        # sin subcomando → CLI hacker completo
        cmd_default(args)
        return 0

    handler = dispatch.get(args.command)
    if not handler:
        _banner()
        _err(f"Comando desconocido: {args.command}")
        _p()
        _info("Usa  python automyx.py --help  para ver todos los comandos.")
        return 1

    try:
        handler(args)
    except KeyboardInterrupt:
        _p()
        _warn("Interrumpido.")
        return 130
    except Exception as e:
        _err(f"{type(e).__name__}: {e}")
        if os.environ.get("AUTOMYX_DEBUG") == "1":
            raise
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
