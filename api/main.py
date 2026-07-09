"""
Automyx API v2.0 - Gateway Profesional
Inspirado en OpenClaw
- WebSocket para control en tiempo real
- Multi-canal (WhatsApp, Telegram, etc.)
- Health checks
- Sistema de configuración profesional
"""
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from pydantic import BaseModel
import sys
import os

# Forzar codificación UTF-8 para evitar errores en Windows con emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import logging
logger = logging.getLogger("automyx.api")

import json
import sqlite3
import requests
import threading
import time
import base64
from pathlib import Path
from typing import Optional

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import AutomyxAgent, get_agent_status, OllamaManager
from core.gateway import create_gateway_app
from core.config import config
from tools.pc_tools import PCTools
from tools.social_tools import SocialTools
from tools.web_tools import WebTools
from tools.video_tools import VideoTools
from tools.cyber_tools import CyberTools
from tools.extra_tools import ExtraTools
from tools.three_d_tools import ThreeDTools
from tools.cron_tools import CronTools
from tools.data_tools import DataTools
from tools.devops_tools import DevOpsTools
from tools.email_tools import EmailTools
from tools.hr_tools import HRTools
from tools.skill_tools import SkillTools
from tools.audio_tools import AudioTools
from tools.blender_tools import BlenderTools
from tools.photo_editor_tools import PhotoEditorTools
from tools.project_autopilot import ProjectAutopilot
from tools.universal_app_control import UniversalAppControl
from tools.aumformbring import aumformbring_system
from tools.nexus_core import nexus_core
from tools.automation_pro import WorkflowManager, ScriptEditorPro, AdvancedMemory, APIIntegrationPro, ChainOfThought
from tools.elite_skills import GitHubTools, CloudDevOpsTools, DataScienceTools, SmartHomeTools, CreativeTools, UniqueAutomyxTools

# === NUEVAS SKILLS Ã‰LITE 2026 ===
from tools.academic_tools import AcademicTools
from tools.accountant_tools import AccountantTools
from tools.livestream_tools import LivestreamTools
from tools.swarm_tools import SwarmOrchestrator
from tools.skill_forger import SkillForger
from tools.stealth_browser_tools import StealthBrowserTools
from tools.rag_memory_tools import RAGMemoryTools
from tools.task_coordinator import TaskCoordinator
from tools.error_learning import ErrorLearningSystem

# === SKILLS NUEVAS 2026 - BESTIA PROFESIONAL ===
import tools.json_tools as json_tools
from tools.document_intelligence import DocumentIntelligenceTools
from tools.opencode_tools import OpenCodeTools
from tools.notion_tools import NotionTools
from tools.obsidian_tools import ObsidianTools
from tools.github_pro_tools import GitHubProTools
from tools.calendar_tools import CalendarTools
from tools.crypto_tools import CryptoTools
from tools.database_tools import DatabaseTools
from tools.translation_tools import TranslationTools
from tools.code_review_tools import CodeReviewTools
from tools.test_runner_tools import TestRunnerTools
from tools.deployment_tools import DeploymentTools
from tools.pdf_pro_tools import PDFProTools
from tools.video_pro_tools import VideoProTools


async def verify_gateway_token(x_gateway_token: Optional[str] = Header(None)):
    """Verifica el token de gateway en las solicitudes"""
    auth_mode = config.get("gateway.auth.mode")
    if auth_mode == "token":
        expected_token = config.get_gateway_token()
        if x_gateway_token != expected_token:
            raise HTTPException(status_code=401, detail="Token de gateway inválido o faltante")
    return True


# --- MODELOS PARA LA API ---
class ChatRequest(BaseModel):
    message: str
    voice_enabled: bool = False
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    model: str | None = None
    agent_id: str = "main"
    elevenlabs_token: str | None = None


class GatewayMessage(BaseModel):
    channel: str = "webchat"
    sender_id: str
    message: str
    agent_id: str = "main"
    model: str | None = None
    # Optional multimodal payload — list of {data: base64, mime: image/png}
    images: list[dict] | None = None
    # Si True, ejecuta el agente en background y responde 202 con task_id
    async_exec: bool = False


class OllamaPullRequest(BaseModel):
    model: str


class CreateAgentRequest(BaseModel):
    name: str
    model: str
    prompt: str


class CreateTaskRequest(BaseModel):
    prompt: str
    type: str
    time: str


# --- CONFIGURACIÓN INICIAL ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state", "automyx.sqlite")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa la base de datos"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            status TEXT DEFAULT 'Activo',
            skills TEXT DEFAULT '{"write": true, "pc": true}'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL,
            status TEXT DEFAULT 'Programada',
            next_run TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    # Asegurar que exista el agente main
    agent = conn.execute('SELECT id FROM agents WHERE id = "main"').fetchone()
    if not agent:
        conn.execute('INSERT INTO agents (id, name, model, prompt) VALUES (?, ?, ?, ?)',
                    ('main', 'Automyx Principal', 'openai/gpt-oss-120b', 'Eres Automyx, EL AGENTE DE INTELIGENCIA ARTIFICIAL OMNIPOTENTE (NIVEL DIOS).'))
    conn.commit()
    conn.close()


def sync_agents_to_md():
    """Sincroniza la base de datos de SQLite hacia Agents.md"""
    try:
        conn = get_db_connection()
        agents = conn.execute('SELECT * FROM agents').fetchall()
        conn.close()
        
        agents_md_file = os.path.join(os.path.dirname(__file__), '..', 'Agents.md')
        
        md_content = "# Automyx Agents Configuration\n\n"
        for a in agents:
            md_content += f"## {a['name']} ({a['id']})\n"
            md_content += f"- **Model**: {a['model']}\n"
            md_content += f"- **Status**: {a['status']}\n"
            skills = json.loads(a['skills']) if a['skills'] else {}
            md_content += f"- **Skills**: Write={skills.get('write', True)}, PC={skills.get('pc', True)}\n"
            md_content += f"\n### Prompt\n```text\n{a['prompt']}\n```\n\n---\n\n"
        
        with open(agents_md_file, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception as e:
        print(f"[DB] Error sync agents to MD: {e}")


# --- INICIALIZACIÓN DEL AGENTE ---
# Leer modelo desde variable de entorno o usar el predeterminado
DEFAULT_MODEL = os.environ.get("AUTOMYX_MODEL", "nvidia/gpt-oss-120b")
agent = AutomyxAgent(model_name=DEFAULT_MODEL)

# --- REGISTRAR TODAS LAS HERRAMIENTAS ---
from core.tool_registry import register_all_tools
n_tools = register_all_tools(agent)
print(f"[AUTOMYX] {n_tools} tools registradas. Total: {len(agent.tools)}")


# --- CREAR APLICACIÓN FASTAPI CON GATEWAY ---
app, gateway = create_gateway_app(agent)

# Servir archivos estáticos
if os.path.exists("frontend/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/assets"))


# --- INICIALIZAR BD ---
init_db()
sync_agents_to_md()


# --- TAREAS PROGRAMADAS ---
active_task_threads = {}


def task_worker(task_id: str, agent_id: str, prompt: str, interval_minutes: int):
    """Hilo trabajador para tareas programadas"""
    import time
    while task_id in active_task_threads:
        try:
            print(f"⏰ [AUTOMATIZACIÓN] Ejecutando tarea {task_id}: {prompt}")
            agent.run(prompt)
            if interval_minutes > 0:
                time.sleep(interval_minutes * 60)
            else:
                break
        except Exception as e:
            print(f"❌ Error en tarea {task_id}: {e}")
            break


def load_all_tasks():
    """Carga tareas desde la BD al iniciar"""
    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM tasks WHERE status = "Programada"').fetchall()
        conn.close()
        for r in rows:
            thread = threading.Thread(target=task_worker, args=(r["id"], r["agent_id"], r["prompt"], r["interval_minutes"]), daemon=True)
            active_task_threads[r["id"]] = thread
            thread.start()
    except Exception as e:
        print(f"[TASKS] Error cargando tareas: {e}")


load_all_tasks()


# --- ENDPOINTS PARA VISTAS BESTIA 2026 ---
@app.get("/api/sessions/list")
async def list_sessions_endpoint(limit: int = 50, _: bool = Depends(verify_gateway_token)):
    """Lista sesiones de chat recientes (sintetizadas desde aumformbring)."""
    try:
        mem = aumformbring_system.get_conversation_memory(limit=limit)
        items = mem if isinstance(mem, list) else (mem.get("items") if isinstance(mem, dict) else [])
        sessions = []
        for i, it in enumerate(items):
            md = it.get("metadata", {}) if isinstance(it, dict) else {}
            sessions.append({
                "id": (it.get("id") or it.get("conversation_id") or f"mem_{i}") if isinstance(it, dict) else f"mem_{i}",
                "started_at": (it.get("timestamp") or it.get("ts") or "") if isinstance(it, dict) else "",
                "duration_s": 0,
                "model": md.get("model", "unknown") if isinstance(md, dict) else "unknown",
                "messages": 1,
                "tools": 0,
                "status": "ok",
            })
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        return {"sessions": [], "error": str(e)}


@app.get("/api/usage")
async def get_usage_endpoint(period: str = "week", _: bool = Depends(verify_gateway_token)):
    """Estadísticas de uso (tokens, requests, costos) por período."""
    try:
        stats = aumformbring_system.get_stats() if hasattr(aumformbring_system, "get_stats") else {}
        if isinstance(stats, dict):
            total_conv = stats.get("total_conversations", 0) or 0
            tokens_in = stats.get("total_input_tokens", 0) or 0
            tokens_out = stats.get("total_output_tokens", 0) or 0
        else:
            total_conv, tokens_in, tokens_out = 0, 0, 0
        # Estimación de costo (tarifas promedio USD/1k tokens)
        cost = round((tokens_in * 0.000003) + (tokens_out * 0.000015), 4)
        return {
            "period": period,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "requests": total_conv,
            "cost": cost,
            "by_model": {},
            "by_tool": {},
        }
    except Exception as e:
        return {"period": period, "tokens_in": 0, "tokens_out": 0, "requests": 0, "cost": 0, "by_model": {}, "by_tool": {}, "error": str(e)}


@app.get("/api/error_learn/get_lessons")
async def get_lessons_endpoint(limit: int = 50, _: bool = Depends(verify_gateway_token)):
    """Lista lecciones de error aprendidas."""
    try:
        lessons = ErrorLearningSystem.get_all_lessons(limit=limit)
        if isinstance(lessons, dict):
            items = lessons.get("lessons", lessons.get("items", []))
        elif isinstance(lessons, list):
            items = lessons
        else:
            items = []
        return {"lessons": items, "count": len(items)}
    except Exception as e:
        return {"lessons": [], "count": 0, "error": str(e)}


@app.post("/api/error_learn/clear")
async def clear_lessons_endpoint(_: bool = Depends(verify_gateway_token)):
    """Limpia todas las lecciones de error."""
    try:
        ErrorLearningSystem.clear_lessons()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- ENDPOINTS EXISTENTES (COMPATIBILIDAD HACIA ATRÁS) ---
import time as _time
_STARTUP_TS = _time.time()


@app.get("/api/agent/status")
async def get_agent_status_endpoint(_: bool = Depends(verify_gateway_token)):
    return get_agent_status()


@app.get("/api/health")
async def health_endpoint():
    """Health check para bots y orquestadores. NO requiere auth.

    Devuelve estado del agente, GPU, memoria, uptime.
    Útil para que los bots (Telegram/Discord/Instagram) sepan si deben
    reintentar, esperar, o reportar al usuario.
    """
    import time as _t
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0)
        mem = psutil.virtual_memory()
    except Exception:
        cpu, mem = None, None
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
    except Exception:
        gpu_available, gpu_name = False, None
    return {
        "status": "ok",
        "agent_running": get_agent_status().get("is_active", True),
        "model": getattr(agent, "model_name", "?"),
        "provider": getattr(agent, "provider", "?"),
        "phase": get_agent_status().get("phase", "idle"),
        "uptime_s": _t.time() - _STARTUP_TS,
        "cpu_percent": cpu,
        "memory_percent": mem.percent if mem else None,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "version": "2.5.0",
    }


@app.get("/api/tasks")
async def get_tasks_endpoint(_: bool = Depends(verify_gateway_token)):
    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM tasks').fetchall()
        conn.close()
        return {"tasks": [dict(row) for row in rows]}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/tasks")
async def create_task_endpoint(req: CreateTaskRequest, _: bool = Depends(verify_gateway_token)):
    try:
        new_id = f"task_{int(time.time())}"
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO tasks (id, name, agent_id, prompt, interval_minutes, status, next_run) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (new_id, "Tarea programada", req.agent_id or "main", req.prompt, 0, "Programada", None)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "task": {"id": new_id}}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/tasks/{task_id}")
async def delete_task_endpoint(task_id: str, _: bool = Depends(verify_gateway_token)):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
        if task_id in active_task_threads:
            del active_task_threads[task_id]
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/gateway/inbound")
async def universal_gateway_inbound(data: GatewayMessage, _: bool = Depends(verify_gateway_token)):
    """Endpoint universal para todos los canales.

    Modos:
      - `async_exec=true` → ejecuta el agente en background y responde 202 con
        un `task_id`. El bot debe hacer polling a `/api/gateway/result/{task_id}`
        o conectarse al WebSocket para recibir el resultado. Esto evita que
        Telegram cierre la conexión por timeout.
      - `async_exec=false` (default) → ejecuta síncrono y devuelve la respuesta.
    """
    async_exec = bool(getattr(data, "async_exec", False))
    try:
        if data.model and data.model != agent.model_name:
            agent.update_model(data.model)
        if async_exec:
            return await _async_inbound(data)
        result = agent.run(data.message, images=data.images)
        try:
            from core.intent_engine import understand
            u = understand(data.message)
            intent_name = u.get("intent", "unknown")
            intent_confidence = u.get("intent_confidence", 0.0)
        except Exception:
            intent_name, intent_confidence = "unknown", 0.0
        return {
            "reply": result,
            "channel": data.channel,
            "agent_used": data.agent_id,
            "has_images": bool(data.images),
            "intent": intent_name,
            "intent_confidence": intent_confidence,
        }
    except Exception as e:
        return {"error": str(e)}


# Task store for async mode
_ASYNC_TASKS: dict = {}


async def _async_inbound(data: "GatewayMessage"):
    """Ejecuta el agente en background y devuelve 202 con task_id."""
    import uuid
    task_id = uuid.uuid4().hex[:12]
    _ASYNC_TASKS[task_id] = {
        "status": "running",
        "started_at": __import__("time").time(),
        "channel": data.channel,
        "sender_id": data.sender_id,
        "message": data.message,
    }

    async def _run():
        try:
            from core.intent_engine import understand
            u = understand(data.message)
            _ASYNC_TASKS[task_id]["intent"] = u.get("intent", "unknown")
            _ASYNC_TASKS[task_id]["intent_confidence"] = u.get("intent_confidence", 0.0)
        except Exception:
            _ASYNC_TASKS[task_id]["intent"] = "unknown"
            _ASYNC_TASKS[task_id]["intent_confidence"] = 0.0
        try:
            loop = asyncio.get_event_loop()
            # Run blocking agent.run() in a thread so the event loop stays free
            result = await loop.run_in_executor(
                None, lambda: agent.run(data.message, images=data.images)
            )
            # Ensure result is a non-empty string
            if result is None:
                result = ""
            result_str = str(result).strip()
            if not result_str:
                result_str = "✅ Tarea completada (sin respuesta textual)."
            _ASYNC_TASKS[task_id].update({
                "status": "done",
                "reply": result_str,
                "finished_at": __import__("time").time(),
            })
        except Exception as e:
            _ASYNC_TASKS[task_id].update({
                "status": "error",
                "error": str(e),
                "finished_at": __import__("time").time(),
            })

    asyncio.ensure_future(_run())
    return {
        "status": "accepted",
        "task_id": task_id,
        "channel": data.channel,
        "poll_url": f"/api/gateway/result/{task_id}",
    }


@app.get("/api/gateway/result/{task_id}")
async def get_async_result(task_id: str, wait: int = 0, _: bool = Depends(verify_gateway_token)):
    """Recupera el resultado de una tarea async.

    `wait` = segundos máximos a esperar por la respuesta (max 50s).
    """
    import asyncio as _aio
    deadline = _aio.get_event_loop().time() + min(max(wait, 0), 50)
    while _aio.get_event_loop().time() < deadline:
        task = _ASYNC_TASKS.get(task_id)
        if task and task["status"] in ("done", "error"):
            return task
        await _aio.sleep(0.5)
    task = _ASYNC_TASKS.get(task_id)
    if task is None:
        return {"error": "task_not_found", "task_id": task_id}
    return {"status": task["status"], "task_id": task_id}


# NOTA: El endpoint WebSocket /ws ya está registrado por core/gateway.py
# dentro de create_gateway_app(agent). No duplicar aquí para evitar shadowing.


# =============================================================================
# ENDPOINTS v2.5: INTENTS, MULTI-TASK, CATÁLOGO
# =============================================================================

class IntentRequest(BaseModel):
    text: str


@app.post("/api/intent/analyze")
async def analyze_intent_endpoint(req: IntentRequest, _: bool = Depends(verify_gateway_token)):
    """Analiza el intent del usuario sin ejecutar nada (slang, typos, entidades)."""
    try:
        from core.intent_engine import understand, normalize_text, detect_intent
        u = understand(req.text)
        return {
            "original": req.text,
            "normalized": u["normalized"],
            "intent": u["intent"],
            "confidence": u["intent_confidence"],
            "matched_keyword": u["matched_keyword"],
            "entities": u["entities"],
            "interpretation": u["interpretation"],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/intent/keywords")
async def intent_keywords_endpoint(_: bool = Depends(verify_gateway_token)):
    """Lista todos los intents conocidos con sus keywords."""
    try:
        from core.intent_engine import INTENT_KEYWORDS
        return {"intents": INTENT_KEYWORDS, "count": len(INTENT_KEYWORDS)}
    except Exception as e:
        return {"error": str(e)}


class MultiTaskRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str | None = None
    agent_id: str = "main"


@app.post("/api/multitask/submit")
async def multitask_submit_endpoint(req: MultiTaskRequest, _: bool = Depends(verify_gateway_token)):
    """Envía una tarea al dispatcher multi-task. Devuelve task_id para polling."""
    try:
        from core.multi_task import get_dispatcher
        d = get_dispatcher()
        task = d.submit(
            user_input=req.message,
            agent=agent,
            session_id=req.session_id,
            model=req.model,
            agent_id=req.agent_id,
        )
        return {"status": "accepted", "task_id": task.task_id, "session_id": task.session_id}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/multitask/task/{task_id}")
async def multitask_task_endpoint(task_id: str, _: bool = Depends(verify_gateway_token)):
    """Obtiene el estado de una tarea multi-task."""
    try:
        from core.multi_task import get_dispatcher
        d = get_dispatcher()
        t = d.get_task(task_id)
        if not t:
            return {"error": f"Tarea {task_id} no encontrada"}
        return t.to_dict()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/multitask/list")
async def multitask_list_endpoint(
    session_id: Optional[str] = None,
    limit: int = 50,
    _: bool = Depends(verify_gateway_token)
):
    """Lista tareas recientes (todas o filtradas por sesión)."""
    try:
        from core.multi_task import get_dispatcher
        d = get_dispatcher()
        tasks = d.list_tasks(session_id=session_id)
        tasks = tasks[:limit]
        return {
            "tasks": [t.to_dict() for t in tasks],
            "count": len(tasks),
            "stats": d.stats(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/multitask/task/{task_id}")
async def multitask_cancel_endpoint(task_id: str, _: bool = Depends(verify_gateway_token)):
    """Cancela una tarea en ejecución."""
    try:
        from core.multi_task import get_dispatcher
        d = get_dispatcher()
        ok = d.cancel(task_id)
        return {"status": "cancelled" if ok else "not_found"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/multitask/stats")
async def multitask_stats_endpoint(_: bool = Depends(verify_gateway_token)):
    """Estadísticas del dispatcher multi-task."""
    try:
        from core.multi_task import get_dispatcher
        return get_dispatcher().stats()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/skills/catalog")
async def skills_catalog_endpoint(_: bool = Depends(verify_gateway_token)):
    """Catálogo COMPLETO de skills con categorías (82+ skills, 500+ tools)."""
    try:
        from core.intent_engine import SKILLS_CATALOG, count_skills, count_tools_in_catalog
        return {
            "categories": SKILLS_CATALOG,
            "total_skills": count_skills(),
            "total_tools_in_catalog": count_tools_in_catalog(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/state/channels")
async def channels_state_endpoint(_: bool = Depends(verify_gateway_token)):
    """Estado de los canales de comunicación (Telegram, Discord, Instagram, etc.)."""
    try:
        import shutil
        from pathlib import Path
        channels = []
        # Telegram
        has_tg = bool(os.environ.get("TELEGRAM_BOT_TOKEN")) or (Path(".env").exists() and "TELEGRAM_BOT_TOKEN=" in Path(".env").read_text(encoding="utf-8", errors="ignore"))
        channels.append({"id": "telegram",  "name": "Telegram",  "icon": "✈️", "configured": has_tg, "running": False})
        # Discord
        has_dc = bool(os.environ.get("DISCORD_BOT_TOKEN")) or (Path(".env").exists() and "DISCORD_BOT_TOKEN=" in Path(".env").read_text(encoding="utf-8", errors="ignore"))
        channels.append({"id": "discord",   "name": "Discord",   "icon": "💬", "configured": has_dc, "running": False})
        # Instagram
        has_ig = bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN")) or (Path(".env").exists() and "INSTAGRAM_ACCESS_TOKEN=" in Path(".env").read_text(encoding="utf-8", errors="ignore"))
        channels.append({"id": "instagram", "name": "Instagram", "icon": "📷", "configured": has_ig, "running": False})
        # WhatsApp
        has_wa = Path("state/whatsapp_session").exists() or Path("nexus_data/whatsapp").exists()
        channels.append({"id": "whatsapp",  "name": "WhatsApp",  "icon": "🟢", "configured": has_wa, "running": False})
        # Web dashboard
        channels.append({"id": "web",       "name": "Web Dashboard", "icon": "🌐", "configured": True, "running": True})
        # Detect running processes
        try:
            import psutil
            for proc in psutil.process_iter(["name", "cmdline"]):
                cmdline = " ".join(proc.info.get("cmdline") or [])
                for cid, fname in [("telegram", "telegram_bot.py"), ("discord", "discord_bot.py"), ("instagram", "instagram_bot.py")]:
                    if fname in cmdline and not next((c for c in channels if c["id"] == cid), {}).get("running"):
                        for c in channels:
                            if c["id"] == cid:
                                c["running"] = True
        except ImportError:
            pass
        # Notion integration
        has_notion = bool(os.environ.get("NOTION_API_KEY")) or (Path(".env").exists() and "NOTION_API_KEY=" in Path(".env").read_text(encoding="utf-8", errors="ignore"))
        integrations = [
            {"id": "notion",     "name": "Notion",     "icon": "📚", "configured": has_notion},
            {"id": "github",     "name": "GitHub",     "icon": "🐙", "configured": bool(os.environ.get("GITHUB_TOKEN"))},
            {"id": "elevenlabs", "name": "ElevenLabs", "icon": "🗣️", "configured": bool(os.environ.get("ELEVENLABS_API_KEY"))},
            {"id": "openai",     "name": "OpenAI",     "icon": "🅞", "configured": bool(os.environ.get("OPENAI_API_KEY"))},
            {"id": "anthropic",  "name": "Anthropic",  "icon": "🅐", "configured": bool(os.environ.get("ANTHROPIC_API_KEY"))},
            {"id": "tavily",     "name": "Tavily",     "icon": "🔍", "configured": bool(os.environ.get("TAVILY_API_KEY"))},
        ]
        return {"channels": channels, "integrations": integrations}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/state/skills")
async def active_skills_endpoint(_: bool = Depends(verify_gateway_token)):
    """Skills activas (las que el usuario seleccionó en el wizard o activó después)."""
    try:
        from pathlib import Path
        state_path = Path("state/onboard_state.json")
        active = []
        if state_path.exists():
            import json
            data = json.loads(state_path.read_text(encoding="utf-8"))
            active = data.get("skills", []) or []
        # También incluir el environment override
        env_skills = os.environ.get("AUTOMYX_ACTIVE_SKILLS", "")
        if env_skills:
            active = [s.strip() for s in env_skills.split(",") if s.strip()]
        return {
            "active": active,
            "count": len(active),
            "source": "onboard_state.json" if state_path.exists() else "env",
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/state/skills/toggle")
async def toggle_skill_endpoint(payload: dict, _: bool = Depends(verify_gateway_token)):
    """Activa o desactiva un skill en el estado persistido."""
    try:
        from pathlib import Path
        import json
        skill_name = payload.get("name")
        enabled = bool(payload.get("enabled", True))
        if not skill_name:
            return {"error": "Missing 'name' in payload"}
        state_path = Path("state/onboard_state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if state_path.exists():
            data = json.loads(state_path.read_text(encoding="utf-8"))
        active = set(data.get("skills", []) or [])
        if enabled:
            active.add(skill_name)
        else:
            active.discard(skill_name)
        data["skills"] = sorted(active)
        state_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "active": data["skills"], "count": len(active)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/state/terminal")
async def terminal_state_endpoint(_: bool = Depends(verify_gateway_token)):
    """Estado del terminal local (CLI ejecutándose, sesión activa, etc.)."""
    try:
        import platform
        import socket
        hostname = socket.gethostname()
        return {
            "platform": sys.platform,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "hostname": hostname,
            "cwd": os.getcwd(),
            "user": os.environ.get("USERNAME") or os.environ.get("USER", "?"),
            "pid": os.getpid(),
            "automyx_version": os.environ.get("AUTOMYX_VERSION", "2.5.0"),
            "model": os.environ.get("AUTOMYX_MODEL", "openai/gpt-oss-120b"),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/integrations/registry")
async def integrations_registry_endpoint(_: bool = Depends(verify_gateway_token)):
    """Listado de integraciones soportadas con su info de setup."""
    try:
        from core.intent_engine import INTEGRATION_REGISTRY
        from pathlib import Path
        env_text = Path(".env").read_text(encoding="utf-8", errors="ignore") if Path(".env").exists() else ""
        items = []
        for key, info in INTEGRATION_REGISTRY.items():
            env_var = info.get("env_var")
            configured = False
            if env_var:
                configured = bool(os.environ.get(env_var)) or f"{env_var}=" in env_text
            items.append({
                "id":            key,
                "name":          info["name"],
                "icon":          info["icon"],
                "env_var":       env_var,
                "help_url":      info["help_url"],
                "format_hint":   info["format_hint"],
                "configured":    configured,
                "has_validator": bool(info.get("validate")),
            })
        return {"integrations": items, "count": len(items)}
    except Exception as e:
        return {"error": str(e)}


class SaveTokenPayload(BaseModel):
    integration_id: str
    token: str


@app.post("/api/integrations/save_token")
async def save_integration_token(payload: SaveTokenPayload,
                                    _: bool = Depends(verify_gateway_token)):
    """Guarda un token de integración en .env y opcionalmente lo valida."""
    try:
        from core.intent_engine import INTEGRATION_REGISTRY, validate_integration_token
        info = INTEGRATION_REGISTRY.get(payload.integration_id)
        if not info:
            return {"error": f"Integración desconocida: {payload.integration_id}"}
        env_var = info.get("env_var")
        if not env_var:
            return {"error": f"{info['name']} no requiere token (escaneo QR o auth interactivo)"}
        token = payload.token.strip()
        if len(token) < 8:
            return {"error": "Token demasiado corto"}
        # Save
        os.environ[env_var] = token
        env_path = Path(".env")
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        found = False
        with open(env_path, "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith(f"{env_var}="):
                    f.write(f"{env_var}={token}\n")
                    found = True
                else:
                    f.write(line + "\n")
            if not found:
                f.write(f"{env_var}={token}\n")
        # Validate (best effort)
        validation = validate_integration_token(payload.integration_id, token)
        return {
            "ok": True,
            "env_var": env_var,
            "configured": True,
            "validation": validation,
        }
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/integrations/{integration_id}/token")
async def delete_integration_token(integration_id: str,
                                     _: bool = Depends(verify_gateway_token)):
    """Elimina el token de una integración (la deja 'no configurada')."""
    try:
        from core.intent_engine import INTEGRATION_REGISTRY
        info = INTEGRATION_REGISTRY.get(integration_id)
        if not info or not info.get("env_var"):
            return {"error": "Integración inválida o sin env_var"}
        env_var = info["env_var"]
        if env_var in os.environ:
            del os.environ[env_var]
        env_path = Path(".env")
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            with open(env_path, "w", encoding="utf-8") as f:
                for line in lines:
                    if not line.startswith(f"{env_var}="):
                        f.write(line + "\n")
        return {"ok": True, "env_var": env_var, "configured": False}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/tools/catalog")
async def tools_catalog_endpoint(category: Optional[str] = None, _: bool = Depends(verify_gateway_token)):
    """Catálogo de tools disponibles. Si category=sees, devuelve conteo por seed."""
    try:
        from tools.mega_tools import TOOL_SEEDS, count_aliases
        canonical_tools = sorted(agent.tools.keys())
        return {
            "total_registered": len(canonical_tools),
            "total_aliases_planned": count_aliases(max_per_seed=2),
            "total_seeds": len(TOOL_SEEDS),
            "categories": list(TOOL_SEEDS.keys())[:50],
            "tools": canonical_tools,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/subtitles/presets")
async def subtitle_presets_endpoint(_: bool = Depends(verify_gateway_token)):
    """Lista los presets de subtítulos disponibles para la UI."""
    try:
        from core.subtitle_presets import list_presets, categories
        return {"presets": list_presets(), "categories": categories()}
    except Exception as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/multitask/wait/{task_id}")
async def multitask_wait_endpoint(
    task_id: str,
    timeout: float = 30.0,
    _: bool = Depends(verify_gateway_token)
):
    """Bloquea hasta que la tarea termine (o timeout) y devuelve el resultado."""
    try:
        from core.multi_task import get_dispatcher
        d = get_dispatcher()
        t = d.wait(task_id, timeout=timeout)
        if not t:
            return {"error": f"Tarea {task_id} no encontrada"}
        return t.to_dict()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/ollama/models")
async def get_ollama_models_endpoint(_: bool = Depends(verify_gateway_token)):
    """Lista los modelos Ollama instalados localmente"""
    try:
        models = OllamaManager.list_models()
        return {"models": models}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/ollama/pull")
async def pull_ollama_model_endpoint(req: OllamaPullRequest, _: bool = Depends(verify_gateway_token)):
    """Descarga un modelo de Ollama"""
    try:
        success = OllamaManager.pull_model(req.model)
        if success:
            return {"status": "success", "model": req.model}
        else:
            return {"error": f"No se pudo descargar el modelo {req.model}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/agents")
async def get_agents_endpoint(_: bool = Depends(verify_gateway_token)):
    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM agents').fetchall()
        conn.close()
        agents_list = []
        for r in rows:
            agent_dict = dict(r)
            agent_dict["skills"] = json.loads(r["skills"]) if r["skills"] else {}
            agents_list.append(agent_dict)
        return {"agents": agents_list}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/agents")
async def create_agent_endpoint(req: CreateAgentRequest, _: bool = Depends(verify_gateway_token)):
    try:
        new_id = f"agent_{int(time.time())}"
        skills_json = json.dumps({"write": True, "pc": True})
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO agents (id, name, model, prompt, status, skills) VALUES (?, ?, ?, ?, ?, ?)',
            (new_id, req.name, req.model, req.prompt, "Activo", skills_json)
        )
        conn.commit()
        conn.close()
        sync_agents_to_md()
        return {"status": "success", "agent": {"id": new_id}}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/agents/{agent_id}")
async def delete_agent_endpoint(agent_id: str, _: bool = Depends(verify_gateway_token)):
    try:
        if agent_id == "main":
            return {"error": "No puedes eliminar el agente principal."}
        conn = get_db_connection()
        conn.execute('DELETE FROM agents WHERE id = ?', (agent_id,))
        conn.commit()
        conn.close()
        sync_agents_to_md()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/agents/{agent_id}/skills")
async def update_agent_skills_endpoint(agent_id: str, skills: dict, _: bool = Depends(verify_gateway_token)):
    try:
        skills_json = json.dumps({
            "write": skills.get("write", True),
            "pc": skills.get("pc", True)
        })
        conn = get_db_connection()
        conn.execute('UPDATE agents SET skills = ? WHERE id = ?', (skills_json, agent_id))
        conn.commit()
        conn.close()
        sync_agents_to_md()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


# --- NODOS CLÚSTER ---
@app.get("/api/nodos")
async def get_nodos_endpoint(_: bool = Depends(verify_gateway_token)):
    import psutil
    from core.hardware_detector import hw_config
    local_cpu = psutil.cpu_percent(interval=0.1)
    local_ram = psutil.virtual_memory().percent
    nodos = [
        {
            "id": "node_master",
            "name": f"Automyx Master ({hw_config.os_name} {hw_config.arch})",
            "ip": "127.0.0.1 (Localhost)",
            "status": "online",
            "cpu": local_cpu,
            "ram": local_ram,
            "uptime": "Activo",
            "icon": "fa-server",
            "gpu": hw_config.gpu_vendor.upper(),
            "backend": hw_config.acceleration_backend.upper()
        }
    ]
    return {"nodos": nodos}


# --- TERMINAL ---
class TerminalCommand(BaseModel):
    command: str


@app.post("/api/terminal/run")
async def run_terminal_command_endpoint(cmd: TerminalCommand, _: bool = Depends(verify_gateway_token)):
    try:
        output = PCTools.execute_cmd(cmd.command)
        return {"output": output}
    except Exception as e:
        return {"error": str(e)}


# --- VOZ ---
def generate_voice_response(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL", custom_api_key: str = None):
    api_key = custom_api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return None
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        data = {
            "text": text[:300],
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
        }
        res = requests.post(url, json=data, headers=headers, timeout=10)
        if res.status_code == 200:
            return base64.b64encode(res.content).decode('utf-8')
        return None
    except Exception:
        return None


class ConfigRequest(BaseModel):
    token: str = None
    api_key: str = None


@app.post("/api/config/elevenlabs")
async def set_elevenlabs_config(req: ConfigRequest, _: bool = Depends(verify_gateway_token)):
    if req.token:
        os.environ["ELEVENLABS_API_KEY"] = req.token
        return {"status": "success"}
    return {"status": "error", "message": "No token provided"}


@app.post("/api/config/telegram")
async def set_telegram_config(req: ConfigRequest, _: bool = Depends(verify_gateway_token)):
    if req.token:
        os.environ["TELEGRAM_BOT_TOKEN"] = req.token
        return {"status": "success"}
    return {"status": "error", "message": "No token provided"}


@app.get("/api/whatsapp/qr")
async def get_whatsapp_qr(_: bool = Depends(verify_gateway_token)):
    # Mock endpoint - in real implementation this would return actual QR
    return {"status": "pending", "message": "WhatsApp integration requires additional setup"}


@app.post("/api/clear_chat")
async def clear_chat_endpoint(_: bool = Depends(verify_gateway_token)):
    agent.clear_memory()
    return {"status": "success", "message": "Memoria reiniciada"}


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, request: Request, _: bool = Depends(verify_gateway_token)):
    from fastapi.responses import StreamingResponse
    import json
    
    user_agent = request.headers.get("user-agent", "").lower()
    if "edg" in user_agent:
        os.environ["AUTOMYX_BROWSER"] = "edge"
    elif "chrome" in user_agent:
        os.environ["AUTOMYX_BROWSER"] = "chrome"
    else:
        os.environ["AUTOMYX_BROWSER"] = "default"
    
    if req.voice_enabled:
        req.message += " [INSTRUCCIÓN INTERNA URGENTE: Estás en una llamada de voz en tiempo real. Responde INMEDIATAMENTE como un humano en la vida real. Máximo 10 a 15 palabras. Ve directo al grano, sin saludos formales, usa un tono súper conversacional y casual. NADA de markdown."
    
    custom_prompt = None
    agent_skills = None
    if req.agent_id and req.agent_id != "main":
        try:
            conn = get_db_connection()
            a = conn.execute('SELECT * FROM agents WHERE id = ?', (req.agent_id,)).fetchone()
            conn.close()
            if a:
                custom_prompt = a["prompt"]
                agent_skills = json.loads(a["skills"]) if a["skills"] else {}
                if not req.model or req.model.strip() == "":
                    req.model = a["model"]
        except Exception as e:
            print(f"[CHAT] Error cargando agente: {e}")
    
    # Convertir string vacío a None
    if req.model and req.model.strip() == "":
        req.model = None
    
    if req.model and req.model != agent.model_name:
        agent.update_model(req.model)
        
    # Lógica antigua para compatibilidad si no se solicita streaming en el request
    # Para simplificar y no romper el cliente, mantenemos la interfaz REST estándar 
    # pero el LLM por debajo ya está usando streaming real-time hacia la consola
    response = agent.run(req.message, custom_system_prompt=custom_prompt, agent_skills=agent_skills)

    # AUMFORMBRING: Almacenar la conversación automáticamente para aprendizaje
    aumformbring_system.store_conversation(
        user_input=req.message,
        agent_response=response,
        metadata={
            "voice_enabled": req.voice_enabled,
            "agent_id": req.agent_id,
            "model": req.model
        }
    )
    
    # NEXUS CORE: Actualizar perfil del usuario automáticamente
    nexus_core.update_user_profile(
        user_input=req.message,
        agent_response=response,
        tools_used=[]  # Se puede mejorar para registrar herramientas reales usadas
    )

    audio_base64 = None
    if req.voice_enabled:
        audio_base64 = generate_voice_response(response, req.voice_id, req.elevenlabs_token)

    return {"response": response, "audio": audio_base64}


# --- UI ---
@app.get("/preview", response_class=HTMLResponse)
async def serve_preview():
    try:
        with open("preview.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return """
        <div style="font-family: sans-serif; text-align: center; padding: 50px; color: #6b7280;">
            <h1 style="color: #374151;">No hay ninguna web generada aún</h1>
            <p>Pídale a Automyx que programe una página web (HTML/CSS/JS) y aparecerá aquí mágicamente.</p>
        </div>
        """


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    frontend_path = Path("frontend/index.html")
    if frontend_path.exists():
        with open(frontend_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Inyectar script para forzar cache busting en desarrollo
            cache_buster = f"<script>window.appVersion = '{time.time()}';</script>"
            return content.replace("</head>", f"{cache_buster}</head>")
    
    # Panel de control básico si no hay frontend
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automyx Gateway</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        header { display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; padding: 1.5rem 0; border-bottom: 1px solid #334155; }
        .logo { font-size: 2rem; font-weight: bold; background: linear-gradient(135deg, #8b5cf6, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .status { display: flex; gap: 0.5rem; align-items: center; margin-left: auto; }
        .status-dot { width: 12px; height: 12px; background: #22c55e; border-radius: 50%; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
        .card { background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }
        .card h2 { font-size: 1.25rem; margin-bottom: 1rem; color: #cbd5e1; }
        .info-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #334155; }
        .info-row:last-child { border-bottom: none; }
        .label { color: #94a3b8; }
        .value { font-weight: 600; }
        .btn { background: linear-gradient(135deg, #8b5cf6, #06b6d4); border: none; padding: 0.75rem 1.5rem; border-radius: 8px; color: white; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.9; }
        .chat-area { margin-top: 2rem; }
        .chat-input { width: 100%; padding: 1rem; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 1rem; }
        .chat-history { margin-top: 1rem; padding: 1rem; background: #1e293b; border-radius: 8px; border: 1px solid #334155; min-height: 200px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo"> AUTOMYX GATEWAY</div>
            <div class="status">
                <div class="status-dot"></div>
                <span>Online</span>
            </div>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>Estado del Sistema</h2>
                <div class="info-row">
                    <span class="label">Versión</span>
                    <span class="value">2.0.0</span>
                </div>
                <div class="info-row">
                    <span class="label">Gateway</span>
                    <span class="value" id="gatewayStatus">Online</span>
                </div>
                <div class="info-row">
                    <span class="label">WebSocket</span>
                    <span class="value" id="wsStatus">Desconectado</span>
                </div>
            </div>
            
            <div class="card">
                <h2>Configuración</h2>
                <div class="info-row">
                    <span class="label">Host</span>
                    <span class="value">0.0.0.0</span>
                </div>
                <div class="info-row">
                    <span class="label">Puerto</span>
                    <span class="value">3500</span>
                </div>
                <div class="info-row">
                    <span class="label">Auth</span>
                    <span class="value">Token</span>
                </div>
            </div>
        </div>
        
        <div class="chat-area card">
            <h2>Chat Rápido</h2>
            <input type="text" id="chatInput" class="chat-input" placeholder="Escribe un mensaje..." onkeypress="if(event.key==='Enter')sendMessage()">
            <div id="chatHistory" class="chat-history"></div>
        </div>
    </div>
    
    <script>
        let ws;
        function connectWS() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            ws.onopen = () => {
                document.getElementById('wsStatus').textContent = 'Conectado';
                document.getElementById('wsStatus').style.color = '#22c55e';
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'event' && data.event === 'agent') {
                    addMessage('Automyx', data.payload.content);
                }
            };
            ws.onclose = () => {
                document.getElementById('wsStatus').textContent = 'Desconectado';
                document.getElementById('wsStatus').style.color = '#ef4444';
                setTimeout(connectWS, 3000);
            };
        }
        
        function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage('Tú', message);
            input.value = '';
            
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            }).then(res => res.json()).then(data => {
                    addMessage('Automyx', data.response);
                });
        }
        
        function addMessage(sender, text) {
            const history = document.getElementById('chatHistory');
            const msg = document.createElement('div');
            msg.style.marginBottom = '0.5rem';
            msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
            history.appendChild(msg);
            history.scrollTop = history.scrollHeight;
        }
        
        connectWS();
    </script>
</body>
</html>
    """


# --- INICIAR GATEWAY ---
if __name__ == "__main__":
    gateway.start()
