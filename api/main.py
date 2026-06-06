"""
Automyx API v2.0 - Gateway Profesional
Inspirado en OpenClaw
- WebSocket para control en tiempo real
- Multi-canal (WhatsApp, Telegram, etc.)
- Health checks
- Sistema de configuración profesional
"""
from fastapi import FastAPI, Request, WebSocket, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os

# Forzar codificación UTF-8 para evitar errores en Windows con emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

from core.agent import AutomyxAgent, agent_status, OllamaManager
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

# Registrar herramientas
agent.register_tool("execute_cmd", PCTools.execute_cmd)
agent.register_tool("use_terminal_window", PCTools.use_terminal_window)
agent.register_tool("list_directory", PCTools.list_directory)
agent.register_tool("read_file", PCTools.read_file)
agent.register_tool("write_file", PCTools.write_file)
agent.register_tool("create_directory", PCTools.create_directory)
agent.register_tool("copy_file", PCTools.copy_file)
agent.register_tool("move_file", PCTools.move_file)
agent.register_tool("delete_file", PCTools.delete_file)
agent.register_tool("open_vscode", PCTools.open_vscode)
agent.register_tool("open_program", PCTools.open_program)
agent.register_tool("wait_seconds", PCTools.wait_seconds)
agent.register_tool("press_key", PCTools.press_key)
agent.register_tool("mouse_click", PCTools.mouse_click)
agent.register_tool("find_and_click_image", PCTools.find_and_click_image)
agent.register_tool("type_text", PCTools.type_text)
agent.register_tool("screenshot", PCTools.screenshot)
agent.register_tool("play_tiktok_desktop_video", PCTools.play_tiktok_desktop_video)
agent.register_tool("generate_vyrex_video", PCTools.generate_vyrex_video)
agent.register_tool("generate_gemini_image", PCTools.generate_gemini_image)
agent.register_tool("generate_gemini_video", PCTools.generate_gemini_video)
agent.register_tool("web_search", WebTools.web_search)
agent.register_tool("open_website", WebTools.open_website)
agent.register_tool("deep_web_scrape", WebTools.deep_web_scrape)
agent.register_tool("ai_form_filler", WebTools.ai_form_filler)
agent.register_tool("play_youtube_video", WebTools.play_youtube_video)
agent.register_tool("create_web_preview", WebTools.create_web_preview)
agent.register_tool("analyze_browser_screen", WebTools.analyze_browser_screen)
agent.register_tool("get_current_browser_url", WebTools.get_current_browser_url)
agent.register_tool("send_whatsapp", SocialTools.send_whatsapp)
agent.register_tool("upload_tiktok", SocialTools.upload_tiktok)
agent.register_tool("post_facebook", SocialTools.post_facebook)
agent.register_tool("send_telegram", SocialTools.send_telegram)
agent.register_tool("trim_video", VideoTools.trim_video)
agent.register_tool("professional_color_grading", VideoTools.professional_color_grading)
agent.register_tool("advanced_transition", VideoTools.advanced_transition)
agent.register_tool("professional_audio_mastering", VideoTools.professional_audio_mastering)
agent.register_tool("add_intro_outro", VideoTools.add_intro_outro)
agent.register_tool("composite_movie_sequence", VideoTools.composite_movie_sequence)
agent.register_tool("add_music_to_video", VideoTools.add_music_to_video)
agent.register_tool("apply_visual_effect", VideoTools.apply_visual_effect)
agent.register_tool("auto_subtitles", VideoTools.auto_subtitles)
agent.register_tool("create_tiktok_edit", VideoTools.create_tiktok_edit)
agent.register_tool("add_dynamic_zoom", VideoTools.add_dynamic_zoom)
agent.register_tool("advanced_video_editor", VideoTools.advanced_video_editor)
agent.register_tool("analyze_video_content", VideoTools.analyze_video_content)
agent.register_tool("smart_auto_edit", VideoTools.smart_auto_edit)
agent.register_tool("port_scan", CyberTools.port_scan)
agent.register_tool("run_nmap_scan", CyberTools.run_nmap_scan)
agent.register_tool("osint_search", CyberTools.osint_search)
agent.register_tool("apply_autotune", AudioTools.apply_autotune)
agent.register_tool("mix_music", AudioTools.mix_music)
agent.register_tool("master_audio", AudioTools.master_audio)
agent.register_tool("extract_text_from_image", ExtraTools.extract_text_from_image)
agent.register_tool("text_to_speech", ExtraTools.text_to_speech)
agent.register_tool("download_video", ExtraTools.download_video)
agent.register_tool("generate_3d_model", ThreeDTools.generate_3d_model)
agent.register_tool("run_blender_script", ThreeDTools.run_blender_script)
agent.register_tool("execute_blender_python_code", ThreeDTools.execute_blender_python_code)
agent.register_tool("generate_professional_3d_video", ThreeDTools.generate_professional_3d_video)
agent.register_tool("generate_cinematic_environment", ThreeDTools.generate_cinematic_environment)
agent.register_tool("simulate_advanced_physics", ThreeDTools.simulate_advanced_physics)
agent.register_tool("composite_movie_sequence", ThreeDTools.composite_movie_sequence)
agent.register_tool("update_live_canvas", WebTools.update_live_canvas)
agent.register_tool("schedule_task", CronTools.schedule_task)
agent.register_tool("list_scheduled_tasks", CronTools.list_scheduled_tasks)
agent.register_tool("cancel_task", CronTools.cancel_task)
agent.register_tool("analyze_csv_data", DataTools.analyze_csv_data)
agent.register_tool("generate_data_chart", DataTools.generate_data_chart)
agent.register_tool("check_system_resources", DevOpsTools.check_system_resources)
agent.register_tool("manage_docker_container", DevOpsTools.manage_docker_container)
agent.register_tool("read_recent_emails", EmailTools.read_recent_emails)
agent.register_tool("create_email_draft", EmailTools.create_email_draft)
agent.register_tool("read_pdf_text", HRTools.read_pdf_text)
agent.register_tool("read_all_cvs_in_folder", HRTools.read_all_cvs_in_folder)
agent.register_tool("export_to_excel", HRTools.export_to_excel)
agent.register_tool("create_skill", SkillTools.create_skill)
agent.register_tool("list_skills", SkillTools.list_skills)
agent.register_tool("read_skill", SkillTools.read_skill)

# Herramientas profesionales de Blender para 3D
agent.register_tool("blender_open", BlenderTools.open_blender)
agent.register_tool("blender_create_cube", BlenderTools.create_cube)
agent.register_tool("blender_create_sphere", BlenderTools.create_sphere)
agent.register_tool("blender_create_torus", BlenderTools.create_torus)
agent.register_tool("blender_create_cylinder", BlenderTools.create_cylinder)
agent.register_tool("blender_create_cone", BlenderTools.create_cone)
agent.register_tool("blender_apply_material", BlenderTools.apply_material)
agent.register_tool("blender_set_location", BlenderTools.set_object_location)
agent.register_tool("blender_set_rotation", BlenderTools.set_object_rotation)
agent.register_tool("blender_set_scale", BlenderTools.set_object_scale)
agent.register_tool("blender_delete_object", BlenderTools.delete_object)
agent.register_tool("blender_clear_scene", BlenderTools.clear_scene)
agent.register_tool("blender_save_scene", BlenderTools.save_scene)
agent.register_tool("blender_render_image", BlenderTools.render_image)
agent.register_tool("blender_create_animation", BlenderTools.create_animation)
agent.register_tool("blender_render_animation", BlenderTools.render_animation)
agent.register_tool("blender_import_model", BlenderTools.import_model)
agent.register_tool("blender_export_model", BlenderTools.export_model)
agent.register_tool("blender_list_objects", BlenderTools.list_objects)

# Herramientas de Automatización Profesional (Estilo OpenClaw/Hermes)
agent.register_tool("create_workflow", WorkflowManager.create_workflow)
agent.register_tool("run_workflow", WorkflowManager.run_workflow)
agent.register_tool("create_and_run_script", ScriptEditorPro.create_and_run_script)
agent.register_tool("log_conversation", AdvancedMemory.log_conversation)
agent.register_tool("recall_conversation", AdvancedMemory.recall_conversation)
agent.register_tool("make_api_request", APIIntegrationPro.make_request)
agent.register_tool("create_plan", ChainOfThought.create_plan)

# Herramientas profesionales para edición de fotos y diseño gráfico
agent.register_tool("photo_open", PhotoEditorTools.open_image)
agent.register_tool("photo_resize", PhotoEditorTools.resize_image)
agent.register_tool("photo_crop", PhotoEditorTools.crop_image)
agent.register_tool("photo_brightness", PhotoEditorTools.adjust_brightness)
agent.register_tool("photo_contrast", PhotoEditorTools.adjust_contrast)
agent.register_tool("photo_saturation", PhotoEditorTools.adjust_saturation)
agent.register_tool("photo_filter", PhotoEditorTools.apply_filter)
agent.register_tool("photo_rotate", PhotoEditorTools.rotate_image)
agent.register_tool("photo_flip", PhotoEditorTools.flip_image)
agent.register_tool("photo_convert", PhotoEditorTools.convert_image_format)
agent.register_tool("photo_text_watermark", PhotoEditorTools.add_text_watermark)
agent.register_tool("photo_image_watermark", PhotoEditorTools.add_image_watermark)
agent.register_tool("photo_thumbnail", PhotoEditorTools.create_thumbnail)
agent.register_tool("photo_collage", PhotoEditorTools.create_collage)
agent.register_tool("photo_exposure", PhotoEditorTools.adjust_exposure)

# Project Autopilot - Característica única y ultra impactante
agent.register_tool("autopilot_analyze_project", ProjectAutopilot.analyze_project)
agent.register_tool("autopilot_detect_bugs", ProjectAutopilot.detect_bugs)
agent.register_tool("autopilot_fix_bugs", ProjectAutopilot.fix_bugs)
agent.register_tool("autopilot_generate_docs", ProjectAutopilot.generate_documentation)
agent.register_tool("autopilot_auto_improve", ProjectAutopilot.auto_improve_project)
agent.register_tool("autopilot_git_commit", ProjectAutopilot.git_commit)
agent.register_tool("autopilot_git_push", ProjectAutopilot.git_push)
agent.register_tool("autopilot_git_pull", ProjectAutopilot.git_pull)
agent.register_tool("autopilot_full_run", ProjectAutopilot.full_autopilot_run)

# Universal App Control - Control TOTAL de cualquier aplicación
agent.register_tool("app_get_windows", UniversalAppControl.get_open_windows)
agent.register_tool("app_activate_window", UniversalAppControl.activate_window)
agent.register_tool("app_move_window", UniversalAppControl.move_window)
agent.register_tool("app_close_window", UniversalAppControl.close_window)
agent.register_tool("app_minimize_window", UniversalAppControl.minimize_window)
agent.register_tool("app_maximize_window", UniversalAppControl.maximize_window)
agent.register_tool("ui_click", UniversalAppControl.ui_click)
agent.register_tool("ui_move", UniversalAppControl.ui_move)
agent.register_tool("ui_type", UniversalAppControl.ui_type)
agent.register_tool("ui_press", UniversalAppControl.ui_press)
agent.register_tool("ui_hotkey", UniversalAppControl.ui_hotkey)
agent.register_tool("ui_mouse_pos", UniversalAppControl.get_mouse_position)
agent.register_tool("ui_screen_size", UniversalAppControl.get_screen_size)
agent.register_tool("ui_screenshot_region", UniversalAppControl.screenshot_region)
agent.register_tool("ui_find_image", UniversalAppControl.find_image_on_screen)
agent.register_tool("ui_click_image", UniversalAppControl.click_image)
agent.register_tool("ui_scroll", UniversalAppControl.scroll)
agent.register_tool("ui_drag_to", UniversalAppControl.drag_to)
agent.register_tool("app_automate_sequence", UniversalAppControl.automate_app_sequence)

# AUMFORMBRING - Sistema de Auto-Aprendizaje y Auto-Mejo
agent.register_tool("aumformbring_store", aumformbring_system.store_conversation)
agent.register_tool("aumformbring_get_skills", aumformbring_system.get_learned_skills)
agent.register_tool("aumformbring_get_memory", aumformbring_system.get_conversation_memory)
agent.register_tool("aumformbring_get_patterns", aumformbring_system.get_useful_patterns)
agent.register_tool("aumformbring_recall", aumformbring_system.recall_similar_conversation)
agent.register_tool("aumformbring_auto_improve", aumformbring_system.auto_improve)
agent.register_tool("aumformbring_create_skill", aumformbring_system.create_custom_skill)
agent.register_tool("aumformbring_search", aumformbring_system.search_memory)
agent.register_tool("aumformbring_forget", aumformbring_system.forget_conversation)
agent.register_tool("aumformbring_clear", aumformbring_system.clear_all_memory)
agent.register_tool("aumformbring_stats", aumformbring_system.get_stats)

# AUTOMYX NEXUS CORE - Sistema avanzado (inspirado en Hermes)
agent.register_tool("nexus_store", nexus_core.store_and_compress)
agent.register_tool("nexus_search", nexus_core.search_memory)
agent.register_tool("nexus_profile", nexus_core.get_user_profile)
agent.register_tool("nexus_skill_stats", nexus_core.get_skill_stats)
agent.register_tool("nexus_all_skills", nexus_core.get_all_skills)
agent.register_tool("nexus_full_stats", nexus_core.get_full_stats)

# ELITE SKILLS - Expansión de Habilidades (Hermes, OpenClaw, y Exclusivas)
agent.register_tool("github_inspect_repo", GitHubTools.github_inspect_repo)
agent.register_tool("git_advanced_merge", GitHubTools.git_advanced_merge)
agent.register_tool("docker_deploy_stack", CloudDevOpsTools.docker_deploy_stack)
agent.register_tool("kubernetes_apply", CloudDevOpsTools.kubernetes_apply)
agent.register_tool("jupyter_live_kernel", DataScienceTools.jupyter_live_kernel)
agent.register_tool("sql_execute_query", DataScienceTools.sql_execute_query)
agent.register_tool("home_assistant_call", SmartHomeTools.home_assistant_call)
agent.register_tool("generate_mermaid_diagram", CreativeTools.generate_mermaid_diagram)
agent.register_tool("generate_ascii_art", CreativeTools.generate_ascii_art)
agent.register_tool("dark_web_breach_check", UniqueAutomyxTools.dark_web_breach_check)
agent.register_tool("blockchain_smart_contract_audit", UniqueAutomyxTools.blockchain_smart_contract_audit)
agent.register_tool("autonomous_codebase_healing", UniqueAutomyxTools.autonomous_codebase_healing)
agent.register_tool("predictive_market_analysis", UniqueAutomyxTools.predictive_market_analysis)


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


# --- ENDPOINTS EXISTENTES (COMPATIBILIDAD HACIA ATRÁS) ---
@app.get("/api/agent/status")
async def get_agent_status_endpoint(_: bool = Depends(verify_gateway_token)):
    return agent_status


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
    """Endpoint universal para todos los canales"""
    try:
        result = agent.run(data.message)
        return {"reply": result, "channel": data.channel, "agent_used": data.agent_id}
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
