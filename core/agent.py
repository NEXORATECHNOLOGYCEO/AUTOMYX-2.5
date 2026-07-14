import json
import logging
import re
import sys
import threading
import time
import requests
import subprocess
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from core.audit import get_audit
    _AUDIT_AVAILABLE = True
except Exception:
    _AUDIT_AVAILABLE = False
    get_audit = None

try:
    from core.token_tracker import get_tracker
    _TRACKER_AVAILABLE = True
except Exception:
    _TRACKER_AVAILABLE = False
    get_tracker = None

try:
    from core.workspace import get_workspace_manager
    _WORKSPACE_AVAILABLE = True
except Exception:
    _WORKSPACE_AVAILABLE = False
    get_workspace_manager = None

# Estado thread-local para el frontend - evita race conditions en tareas paralelas
_agent_status_local = threading.local()

def get_agent_status() -> dict:
    """Obtiene el estado del thread actual, creando uno nuevo si no existe."""
    if not hasattr(_agent_status_local, 'status'):
        _agent_status_local.status = {
            "is_active": False,
            "phase": "idle",
            "current_action": "Esperando tu solicitud...",
            "reasoning": "",
            "user_request": "",
            "step": 0,
            "total_steps": 0,
            "tool_name": "",
            "tool_args_summary": "",
            "tool_result_summary": "",
            "tool_result_ok": None,
            "error_message": "",
            "started_at": None,
            "last_update": None,
            "plan": None,
            "flow_phases": [],
        }
    return _agent_status_local.status

# Alias de compatibilidad - redirige al thread-local
def agent_status():
    return get_agent_status()

# Forzar codificación UTF-8 para evitar errores en Windows con emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from typing import List, Dict, Any, Callable, Optional
from openai import OpenAI
from colorama import Fore, Style
from core.hardware_detector import hw_config
from core.skills import SKILLS_REGISTRY

# Sistemas de precisión y auto-aprendizaje de errores
try:
    from tools.error_learning import ErrorLearningSystem
except Exception:
    ErrorLearningSystem = None
try:
    from tools.aumformbring import aumformbring_system
except Exception:
    aumformbring_system = None
try:
    from tools.auto_learning_orchestrator import AutoLearningOrchestrator
except Exception:
    AutoLearningOrchestrator = None
# TaskCoordinator REMOVIDO: el modelo coordina nativamente
TaskCoordinator = None

# Núcleo nuevo: parser JSON blindado y terminal Rich
try:
    from core.json_protocol import parse_response, ParseResult, ToolCall, make_tool_call
    JSON_PROTOCOL_AVAILABLE = True
except Exception:
    JSON_PROTOCOL_AVAILABLE = False
    ParseResult = None
    ToolCall = None
    parse_response = None
    make_tool_call = None

try:
    from core import terminal as term
    TERMINAL_AVAILABLE = True
except Exception:
    TERMINAL_AVAILABLE = False
    term = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Agent")


# ---------------------------------------------------------------------------
# Helpers de estado: el frontend ve transiciones claras de fase
# ---------------------------------------------------------------------------
_state_lock = threading.RLock() if 'threading' in dir() else __import__('threading').RLock()
_progress_callback: Optional[Callable] = None


def set_progress_callback(cb: Optional[Callable]) -> None:
    """Registra un callback global de progreso (para streaming multi-tarea)."""
    global _progress_callback
    _progress_callback = cb


def _set_phase(phase: str, action: str = "", **extras: Any) -> None:
    """Actualiza el estado thread-local de forma atómica y notifica."""
    with _state_lock:
        get_agent_status()["phase"] = phase
        if action:
            get_agent_status()["current_action"] = action
        get_agent_status()["last_update"] = datetime.now().isoformat()
        for k, v in extras.items():
            get_agent_status()[k] = v
    # Log interno
    logger.debug(f"[phase={phase}] {action} | extras={extras}")
    # Callback de progreso (multi-tarea)
    if _progress_callback is not None:
        try:
            _progress_callback(phase, action, **extras)
        except Exception:
            pass


def _truncate_args(args: Dict[str, Any], max_len: int = 80) -> str:
    """Resumen corto de args para mostrar en UI."""
    if not args:
        return "(sin args)"
    parts = []
    for k, v in args.items():
        sv = str(v)
        if len(sv) > 30:
            sv = sv[:27] + "..."
        parts.append(f"{k}={sv}")
    s = ", ".join(parts)
    if len(s) > max_len:
        s = s[:max_len - 3] + "..."
    return s


def _summarize_result(result: Any) -> str:
    """Resumen amigable de un resultado de tool."""
    if result is None:
        return "(sin resultado)"
    if isinstance(result, dict):
        if "ok" in result:
            ok = result["ok"]
            err = result.get("error", "")
            return f"ok={ok}" + (f" err={err[:60]}" if err else "")
        if "error" in result:
            return f"error: {str(result['error'])[:60]}"
        if "count" in result:
            return f"{result['count']} items"
        if "output" in result:
            return f"output: {str(result['output'])[:60]}"
        # Resumen genérico
        keys = list(result.keys())[:3]
        return "{" + ", ".join(keys) + ("..." if len(result) > 3 else "") + "}"
    if isinstance(result, str):
        return result[:80] + ("..." if len(result) > 80 else "")
    if isinstance(result, list):
        return f"list[{len(result)}]"
    return str(type(result).__name__)


class OllamaManager:
    """Gestor para modelos de Ollama (local y cloud)"""
    
    @staticmethod
    def is_ollama_installed() -> bool:
        """Verifica si Ollama está instalado"""
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            return True
        except:
            return False
    
    @staticmethod
    def list_models() -> List[Dict[str, Any]]:
        """Lista los modelos Ollama instalados localmente"""
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                # Parsear la salida de ollama list
                lines = result.stdout.strip().split('\n')
                models = []
                for line in lines[1:]:  # Saltar la primera línea (cabecera)
                    parts = line.split()
                    if parts:
                        models.append({
                            "name": parts[0],
                            "size": parts[1] if len(parts) > 1 else None,
                            "id": parts[2] if len(parts) > 2 else None
                        })
                return models
            return []
        except Exception as e:
            logger.error(f"Error listando modelos Ollama: {e}")
            return []
    
    @staticmethod
    def pull_model(model_name: str) -> bool:
        """Descarga un modelo de Ollama"""
        try:
            logger.info(f"Descargando modelo: {model_name}...")
            subprocess.run(["ollama", "pull", model_name], check=True)
            logger.info(f"Modelo {model_name} descargado exitosamente!")
            return True
        except Exception as e:
            logger.error(f"Error descargando modelo {model_name}: {e}")
            return False
    
    @staticmethod
    def is_model_available(model_name: str) -> bool:
        """Verifica si un modelo está disponible localmente"""
        models = OllamaManager.list_models()
        return any(m["name"] == model_name for m in models)
    
    @staticmethod
    def launch_automyx(model_name: str = "llama3.1:8b", location: str = "local"):
        """Lanza Automyx con un modelo específico de Ollama"""
        
        # Construir el nombre completo del modelo
        full_model_name = ""
        if location == "local":
            full_model_name = f"ollama/{model_name}"
        elif location == "cloud":
            full_model_name = f"cloud/{model_name}"
        
        # Verificar si el modelo está disponible localmente
        if location == "local" and not OllamaManager.is_model_available(model_name):
            print(f"⚠️ El modelo {model_name} no está instalado localmente.")
            respuesta = input(f"¿Deseas descargarlo? (s/n): ").strip().lower()
            if respuesta == "s":
                if not OllamaManager.pull_model(model_name):
                    print("❌ No se pudo descargar el modelo. Saliendo...")
                    return
            else:
                print("Cancelando...")
                return
        
        # Establecer la variable de entorno
        os.environ["AUTOMYX_MODEL"] = full_model_name
        os.environ["AUTOMYX_LOCATION"] = location
        
        # Ejecutar Automyx
        # Encontrar la ruta correcta del script principal
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(script_dir, "automix.py")
        
        if not os.path.exists(script_path):
            print("❌ No se encontró automix.py!")
            return
        
        subprocess.run([sys.executable, script_path, "gateway"], cwd=script_dir)



# ---------------------------------------------------------------------------
# Wrapper de compatibilidad OpenAI para Anthropic SDK
# Permite usar client.chat.completions.create() con modelos Claude
# ---------------------------------------------------------------------------
class _AnthrChunk:
    class _Delta:
        def __init__(self, text):
            self.content = text
            self.reasoning_content = None
    class _Choice:
        def __init__(self, text):
            self.delta = _AnthrChunk._Delta(text)
    def __init__(self, text):
        self.choices = [self._Choice(text)]


class _AnthrMessage:
    class _MsgObj:
        def __init__(self, content):
            self.content = content
            self.tool_calls = None
    class _Choice:
        def __init__(self, content):
            self.message = _AnthrMessage._MsgObj(content)
    class _Usage:
        def __init__(self, prompt=0, completion=0):
            self.prompt_tokens = prompt
            self.completion_tokens = completion
    def __init__(self, content, usage=None):
        self.choices = [self._Choice(content)]
        _u = usage or {}
        self.usage = self._Usage(
            prompt=_u.get("input_tokens", 0),
            completion=_u.get("output_tokens", 0),
        )


def _build_anthropic_schemas(tools: dict) -> list:
    """Genera Anthropic tool schemas (max 64 tools, nombres sanitizados)."""
    import inspect as _inspect
    import re as _re

    # Anthropic: nombre válido = ^[a-zA-Z0-9_-]{1,64}$
    def _safe_name(n: str) -> str:
        n = _re.sub(r'[^a-zA-Z0-9_\-]', '_', n)
        return n[:64]

    # Priorizar tools más usadas (limitar a 64 para evitar payloads gigantes)
    _PRIORITY = [
        "write_file", "read_file", "create_directory", "list_directory",
        "execute_cmd", "delete_file", "copy_file", "move_file",
        "web_search", "web_fetch", "open_browser", "open_program",
        "open_vscode", "use_terminal_window", "remember_fact", "recall_facts",
        "glob_file", "search_in_file", "append_to_file", "replace_in_file",
        "download_file", "compress_files", "extract_zip", "get_clipboard",
        "set_clipboard", "take_screenshot", "notion_create_page",
        "github_create_repo", "send_telegram_message", "send_discord_message",
    ]
    _ordered = [t for t in _PRIORITY if t in tools]
    _ordered += [t for t in tools if t not in set(_ordered)]
    _ordered = _ordered[:64]

    schemas = []
    for name in _ordered:
        func = tools[name]
        safe = _safe_name(name)
        try:
            sig = _inspect.signature(func)
            props = {}
            required = []
            for pname, param in sig.parameters.items():
                if pname in ("self", "kwargs", "args"):
                    continue
                ann = param.annotation
                if ann == int:
                    ptype = "integer"
                elif ann == bool:
                    ptype = "boolean"
                elif ann in (list,):
                    ptype = "array"
                else:
                    ptype = "string"
                props[_safe_name(pname)] = {"type": ptype, "description": pname}
                if param.default is _inspect.Parameter.empty:
                    required.append(_safe_name(pname))
        except Exception:
            props = {}
            required = []
        doc = ((func.__doc__ or "").strip().split("\n")[0])[:200] or f"Tool: {name}"
        schemas.append({
            "name": safe,
            "description": doc[:200],
            "input_schema": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        })
    return schemas


class _AnthrCompletions:
    def __init__(self, ac):
        self._ac = ac
        self._schemas = None  # set by agent before calling

    def _clean_messages(self, messages):
        """Convierte history de Automyx al formato Anthropic."""
        system_parts = []
        conv = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c)
                    for c in content
                )
            if role == "system":
                system_parts.append(content)
            elif role in ("user", "assistant"):
                conv.append({"role": role, "content": content or " "})

        # Anthropic requiere roles alternados empezando con user
        cleaned = []
        last_role = None
        for m in conv:
            if m["role"] == last_role:
                cleaned[-1]["content"] += "\n" + m["content"]
            else:
                cleaned.append({"role": m["role"], "content": m["content"]})
                last_role = m["role"]
        if not cleaned or cleaned[0]["role"] != "user":
            cleaned.insert(0, {"role": "user", "content": "Continúa."})

        # Anthropic rechaza assistant content con trailing whitespace
        for msg in cleaned:
            if msg["role"] == "assistant":
                msg["content"] = (msg["content"] or "").rstrip() or "OK"

        return system_parts, cleaned

    def create(self, model, messages, stream=False, max_tokens=4096,
               temperature=0.7, top_p=0.95, timeout=120, **kw):

        system_parts, cleaned = self._clean_messages(messages)

        kwargs = {
            "model": model,
            "messages": cleaned,
            "max_tokens": max(max_tokens, 1),
            "temperature": min(max(float(temperature), 0.0), 1.0),
        }
        if system_parts:
            kwargs["system"] = "\n".join(system_parts)

        # ── Native tool_use (previene planes JSON) ───────────────────────
        schemas = self._schemas
        if schemas:
            kwargs["tools"] = schemas
            kwargs["tool_choice"] = {"type": "auto"}

        if stream:
            resp = self._ac.messages.create(stream=True, **kwargs)

            def _gen():
                try:
                    _pending_tool = {}  # {id: {name, buf}}
                    _active_id = [None]
                    for chunk in resp:
                        t = getattr(chunk, "type", "")

                        if t == "content_block_start":
                            blk = getattr(chunk, "content_block", None)
                            if blk and getattr(blk, "type", "") == "tool_use":
                                bid = getattr(blk, "id", "") or "t0"
                                _pending_tool[bid] = {"name": getattr(blk, "name", ""), "buf": ""}
                                _active_id[0] = bid

                        elif t == "content_block_delta":
                            delta = getattr(chunk, "delta", None)
                            if not delta:
                                continue
                            dtype = getattr(delta, "type", "")
                            if dtype == "text_delta":
                                text = getattr(delta, "text", "") or ""
                                if text:
                                    yield _AnthrChunk(text)
                            elif dtype == "input_json_delta":
                                bid = _active_id[0]
                                if bid and bid in _pending_tool:
                                    _pending_tool[bid]["buf"] += getattr(delta, "partial_json", "") or ""

                        elif t == "content_block_stop":
                            bid = _active_id[0]
                            if bid and bid in _pending_tool:
                                tc = _pending_tool.pop(bid)
                                if tc["name"]:
                                    try:
                                        args = json.loads(tc["buf"]) if tc["buf"] else {}
                                    except Exception:
                                        args = {}
                                    tool_json = json.dumps({"action": tc["name"], "args": args})
                                    yield _AnthrChunk(f"\n{tool_json}")
                                _active_id[0] = None
                except Exception:
                    pass
            return _gen()
        else:
            resp = self._ac.messages.create(**kwargs)
            parts = []
            for blk in getattr(resp, "content", []) or []:
                btype = getattr(blk, "type", "")
                if btype == "text":
                    text = getattr(blk, "text", "") or ""
                    if text:
                        parts.append(text)
                elif btype == "tool_use":
                    args = getattr(blk, "input", {}) or {}
                    tool_json = json.dumps({"action": blk.name, "args": args})
                    parts.append(f"\n{tool_json}")
            # Propagar usage real para token tracking
            _usage = getattr(resp, "usage", None)
            usage_dict = {}
            if _usage:
                usage_dict = {
                    "input_tokens":  getattr(_usage, "input_tokens",  0),
                    "output_tokens": getattr(_usage, "output_tokens", 0),
                }
            return _AnthrMessage("\n".join(parts), usage=usage_dict)


class _AnthrCompatClient:
    """Cliente compatible con OpenAI API para modelos Anthropic."""
    def __init__(self, api_key: str):
        import anthropic as _anth
        _ac = _anth.Anthropic(api_key=api_key)
        self.chat = type("_C", (), {})()
        self.chat.completions = _AnthrCompletions(_ac)

    def set_tool_schemas(self, tools: dict):
        """Registra los schemas de tools para usar native tool_use."""
        try:
            self.chat.completions._schemas = _build_anthropic_schemas(tools)
        except Exception:
            pass


class ModelProvider:
    """Gestiona diferentes proveedores de modelos."""
    OLLAMA_LOCAL = "ollama_local"
    OLLAMA_CLOUD = "ollama_cloud"
    NVIDIA      = "nvidia"
    OPENAI      = "openai"
    ANTHROPIC   = "anthropic"
    GOOGLE      = "google"
    XAI         = "xai"
    MISTRAL_AI  = "mistral"
    DEEPSEEK    = "deepseek"
    VYREX       = "vyrex"

    @staticmethod
    def get_provider(model_name: str) -> str:
        ml = model_name.lower()
        # Vyrex (modelo propio via API Vyrex) — detectar ANTES que ollama/qwen
        if ml.startswith("vyrex"):
            return ModelProvider.VYREX
        # Prefijos explícitos Ollama
        if model_name.startswith("ollama/"):
            return ModelProvider.OLLAMA_LOCAL
        if model_name.startswith("cloud/"):
            return ModelProvider.OLLAMA_CLOUD
        # Modelos locales Ollama (sin prefijo)
        if ":" in model_name and not "/" in model_name:
            return ModelProvider.OLLAMA_LOCAL
        # NVIDIA NIM (prefijos de sus rutas)
        if (model_name.startswith("nvidia/") or model_name.startswith("openai/")
                or model_name.startswith("z-ai/") or model_name.startswith("minimaxai/")
                or model_name.startswith("moonshotai/") or model_name.startswith("meta/")
                or model_name.startswith("mistralai/") or "gpt-oss" in ml):
            return ModelProvider.NVIDIA
        # Anthropic
        if ml.startswith("claude"):
            return ModelProvider.ANTHROPIC
        # OpenAI
        if ml.startswith("gpt-") or ml.startswith("o1") or ml.startswith("o3") or ml.startswith("o4"):
            return ModelProvider.OPENAI
        # Google Gemini
        if ml.startswith("gemini"):
            return ModelProvider.GOOGLE
        # xAI
        if ml.startswith("grok"):
            return ModelProvider.XAI
        # Mistral (directo, no via NVIDIA)
        if ml.startswith("mistral-") or ml.startswith("codestral"):
            return ModelProvider.MISTRAL_AI
        # DeepSeek
        if ml.startswith("deepseek"):
            return ModelProvider.DEEPSEEK
        # Ollama (nombres sin prefijo ni slash)
        if any(x in ml for x in ("llama", "phi", "qwen", "gemma", "codellama")):
            return ModelProvider.OLLAMA_LOCAL
        # Fallback: NVIDIA
        return ModelProvider.NVIDIA

    @staticmethod
    def get_client(model_name: str, provider: str = None):
        if provider is None:
            provider = ModelProvider.get_provider(model_name)

        if provider == ModelProvider.OLLAMA_LOCAL:
            return OpenAI(base_url="http://localhost:11434/v1", api_key="local-ollama")

        if provider == ModelProvider.OLLAMA_CLOUD:
            return OpenAI(
                base_url="https://ollama.com/v1",
                api_key=os.getenv("OLLAMA_API_KEY", "ollama-cloud-key"),
            )

        if provider == ModelProvider.ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY no configurada")
            try:
                return _AnthrCompatClient(api_key)
            except ImportError:
                logger.warning("anthropic SDK no instalado, usando NVIDIA como fallback")

        if provider == ModelProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                logger.warning("OPENAI_API_KEY no configurada")
            return OpenAI(api_key=api_key or "missing-key")

        if provider == ModelProvider.GOOGLE:
            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key:
                logger.warning("GOOGLE_API_KEY no configurada")
            return OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=api_key or "missing-key",
            )

        if provider == ModelProvider.XAI:
            api_key = os.getenv("XAI_API_KEY", "")
            if not api_key:
                logger.warning("XAI_API_KEY no configurada")
            return OpenAI(base_url="https://api.x.ai/v1", api_key=api_key or "missing-key")

        if provider == ModelProvider.MISTRAL_AI:
            api_key = os.getenv("MISTRAL_API_KEY", "")
            if not api_key:
                logger.warning("MISTRAL_API_KEY no configurada")
            return OpenAI(base_url="https://api.mistral.ai/v1", api_key=api_key or "missing-key")

        if provider == ModelProvider.DEEPSEEK:
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key:
                logger.warning("DEEPSEEK_API_KEY no configurada")
            return OpenAI(base_url="https://api.deepseek.com/v1", api_key=api_key or "missing-key")

        if provider == ModelProvider.VYREX:
            api_key = os.getenv("VYREX_API_KEY", "")
            if not api_key:
                logger.warning("VYREX_API_KEY no configurada (ponla en el .env: VYREX_API_KEY=vyx_...)")
            return OpenAI(base_url="https://vyrexstudio.com/v1", api_key=api_key or "missing-key")

        if provider == ModelProvider.NVIDIA:
            api_key = os.getenv("NVIDIA_API_KEY", "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")
            try:
                from core.speed import get_optimized_http_client
                http_client = get_optimized_http_client("https://integrate.api.nvidia.com/v1", api_key)
                if http_client is not None:
                    return OpenAI(
                        base_url="https://integrate.api.nvidia.com/v1",
                        api_key=api_key,
                        http_client=http_client,
                    )
            except Exception:
                pass
            return OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)

        # Fallback NVIDIA
        api_key = os.getenv("NVIDIA_API_KEY", "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")
        return OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)

    @staticmethod
    def get_display_name(model_name: str) -> str:
        if model_name.startswith("ollama/"):
            return model_name.replace("ollama/", "")
        if model_name.startswith("cloud/"):
            return model_name.replace("cloud/", "")
        # NVIDIA: mantener prefijo (la API lo requiere)
        if (model_name.startswith("nvidia/") or model_name.startswith("openai/")
                or model_name.startswith("z-ai/") or model_name.startswith("minimaxai/")
                or model_name.startswith("moonshotai/") or model_name.startswith("meta/")
                or model_name.startswith("mistralai/")):
            return model_name
        return model_name


class AutomyxAgent:
    def __init__(self, model_name: str = "", provider: str = None):
        if not model_name:
            model_name = os.environ.get("AUTOMYX_MODEL", "openai/gpt-oss-120b")
        self.model_name = model_name
        self.provider = provider or ModelProvider.get_provider(model_name)
        self.hw = hw_config
        
        logger.info(f"Iniciando AutomyxAgent en {self.hw.os_name} ({self.hw.arch})")
        logger.info(f"Hardware detectado: GPU={self.hw.gpu_vendor}, Backend={self.hw.acceleration_backend}")
        
        self.client = ModelProvider.get_client(model_name, self.provider)
        logger.info(f"Proveedor: {self.provider} | Modelo: {ModelProvider.get_display_name(model_name)}")
        
        # Cargar el Soul base desde Soul.md (OPTIMIZADO: solo una vez, cacheado)
        try:
            soul_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Soul.md")
            with open(soul_path, "r", encoding="utf-8") as f:
                soul_text = f.read()
        except Exception as e:
            logger.warning(f"No se pudo cargar Soul.md, usando prompt por defecto. Error: {e}")
            soul_text = "Eres Automyx. Debes usar JSON para las herramientas."

        # OPTIMIZACION: prompt compacto para fast_mode (modelos M3/M2.7)
        # Reduce el system prompt de ~13K tokens a ~2K para velocidad maxima
        try:
            from core.model_config import get_model_config
            _mc = get_model_config(model_name)
            self._fast_mode = _mc.get("fast_mode", False)
        except Exception:
            self._fast_mode = False

        if self._fast_mode:
            self.system_prompt = (
                "Eres Automyx, agente IA autonomo local. Responde SIEMPRE en espanol.\n\n"
                "REGLA #1 — HERRAMIENTAS (CRITICA, SIN EXCEPCIONES):\n"
                "Cuando necesites hacer algo concreto (crear archivo, ejecutar comando, leer, escribir, buscar):\n"
                "- Responde UNICAMENTE con el JSON, NADA MAS. Cero texto antes ni despues.\n"
                "- Formato exacto: {\"action\": \"nombre_tool\", \"args\": {\"param\": \"valor\"}}\n"
                "- Si necesitas escribir un archivo con contenido largo, pon TODO el contenido en args.content.\n"
                "- NO escribas 'Voy a...', 'Claro!', 'Te lo dejo...' ni ningun texto antes del JSON.\n"
                "- El JSON debe estar SOLO en tu respuesta, sin ningun otro caracter.\n\n"
                "REGLA #2 — RESPUESTA FINAL:\n"
                "Solo DESPUES de ejecutar TODAS las herramientas necesarias, escribe texto plano resumiendo lo hecho.\n"
                "Esa respuesta final NO debe contener JSON.\n\n"
                "REGLA #3 — SIN BUCLES:\n"
                "Maximo 3-4 herramientas por tarea. Cuando hayas escrito todos los archivos, da la respuesta final.\n\n"
                "REGLA #4 — CONTENIDO COMPLETO:\n"
                "Cuando escribas HTML/CSS/JS, el contenido debe ser COMPLETO y profesional en args.content.\n"
                "Nunca pongas placeholders ni '...' en el contenido real de archivos.\n\n"
                "REGLA #5 — execute_cmd CON SERVIDORES:\n"
                "Para node server.js, python app.py, npm start, flask run, uvicorn: SIEMPRE agrega 'background': true.\n"
                "NUNCA encadenes npm install && node server.js: hazlo en 2 llamadas separadas.\n"
                "NUNCA digas 'inicia el servidor manualmente' — TU lo inicias con background:true.\n\n"
                "Tools: read_file, write_file, list_directory, execute_cmd, create_directory, web_search, remember_fact."
            )
        else:
            # Prompt completo para modelos grandes
            self.system_prompt = soul_text
            # Append enhanced communication rules for 100% task completion
            try:
                from core.model_config import ENHANCED_SYSTEM_PROMPT_ADDITION
                self.system_prompt = self.system_prompt + "\n" + ENHANCED_SYSTEM_PROMPT_ADDITION
            except Exception as e:
                logger.debug(f"Could not append enhanced system prompt: {e}")

        self.history = [{"role": "system", "content": self.system_prompt}]
        self.tools: Dict[str, Callable] = {}
        self._tool_requires: Dict[str, list] = {}
        self._alias_tool_names: set = set()
        self._conversation_count = 0

        # OPTIMIZACION: pre-warm de recursos en background
        try:
            from core.speed import init_speed_optimizations
            init_speed_optimizations(model_name)
        except Exception:
            pass

    def update_model(self, model_name: str):
        """Actualiza el modelo, proveedor y cliente en caliente."""
        if self.model_name != model_name:
            self.model_name = model_name
            self.provider = ModelProvider.get_provider(model_name)
            self.client = ModelProvider.get_client(model_name, self.provider)
            logger.info(f"Modelo actualizado a: {self.provider} | {ModelProvider.get_display_name(model_name)}")

    def clear_memory(self):
        """Reinicia el historial de conversación, conservando solo el prompt base."""
        self.history = [{"role": "system", "content": self.system_prompt}]
        return "Memoria borrada."

    def load_conversation_history(self, messages: list):
        """Restaura el historial LLM previo despues del system prompt."""
        if not messages:
            return
        system_msg = self.history[0] if self.history else {"role": "system", "content": self.system_prompt}
        self.history = [system_msg]
        for msg in messages:
            if msg.get("role") in ("user", "assistant"):
                self.history.append(msg)

    def inject_memory_context(self, facts_context: str):
        """Inyecta el contexto de memoria en el system prompt existente."""
        if not facts_context or not self.history:
            return
        if self.history[0]["role"] == "system":
            base = self.history[0]["content"]
            if "[MEMORIA PERSISTENTE" not in base:
                self.history[0]["content"] = base + f"\n\n{facts_context}"

    def register_tool(self, name: str, func: Callable, requires: Optional[list] = None):
        """Register a tool. Optionally declare pip deps via `requires=['whisper', 'torch']`.

        When a tool is registered with deps, Automyx checks they're importable
        (and silently installs missing ones) on first invocation. This avoids
        the "first run crashes" problem for fresh installs.
        """
        self.tools[name] = func
        if requires:
            self._tool_requires[name] = list(requires)

    def _parse_tool_calls(self, response_text: str) -> list:
        """
        Parsea tool calls usando el parser blindado de core/json_protocol.py.
        5 capas: markdown fence -> balanced braces -> repair -> regex -> schema validation.
        Ademas detecta planes JSON (plan_id + steps) y los convierte a tool calls.
        Retorna lista de dicts {action, args} compatible con el codigo existente.
        """
        # === CAPA 0: Detectar plan JSON con steps y convertirlo ===
        # Soporta JSON válido, JSON malformado, y extracción de pasos individuales
        try:
            _plan_steps = None

            # 0a. Buscar en code fences primero (más confiable)
            for fence_m in re.finditer(r'```(?:json)?\s*([\s\S]*?)```', response_text, re.IGNORECASE):
                candidate = fence_m.group(1).strip()
                if '"steps"' not in candidate and '"plan_id"' not in candidate:
                    continue
                try:
                    candidate_clean = re.sub(r',\s*([\]}])', r'\1', candidate)
                    _p = json.loads(candidate_clean)
                    if isinstance(_p, dict) and "steps" in _p and isinstance(_p["steps"], list):
                        _plan_steps = _p["steps"]
                        break
                except json.JSONDecodeError:
                    pass

            # 0b. Intentar balanced-brace parse (JSON sin fence)
            if _plan_steps is None and ('"plan_id"' in response_text or '"steps"' in response_text):
                _depth = 0; _start = -1
                for _i, _c in enumerate(response_text):
                    if _c == '{':
                        if _depth == 0: _start = _i
                        _depth += 1
                    elif _c == '}':
                        _depth -= 1
                        if _depth == 0 and _start != -1:
                            json_str = re.sub(r',\s*([\]}])', r'\1', response_text[_start:_i+1])
                            try:
                                _p = json.loads(json_str)
                                if isinstance(_p, dict) and "steps" in _p and isinstance(_p["steps"], list):
                                    _plan_steps = _p["steps"]
                                    break
                            except json.JSONDecodeError:
                                pass
                            _start = -1

            # 0c. Fallback: extraer pasos individuales con regex
            # Soporta JSON truncado / malformado con contenido embebido grande
            if _plan_steps is None and '"tool"' in response_text and '"args"' in response_text:
                _plan_steps = []
                # Buscar patrones "tool": "name", "args": {…}
                for step_m in re.finditer(
                    r'"tool"\s*:\s*"([^"]+)"[^}]{0,200}"args"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})',
                    response_text, re.DOTALL
                ):
                    tool_nm = step_m.group(1)
                    args_raw = re.sub(r',\s*([\]}])', r'\1', step_m.group(2))
                    try:
                        args_obj = json.loads(args_raw)
                    except json.JSONDecodeError:
                        args_obj = {}
                    _plan_steps.append({"tool": tool_nm, "args": args_obj})

            if _plan_steps:
                tool_calls_from_plan = []
                for _step in _plan_steps:
                    action = _step.get("tool") or _step.get("action", "")
                    if action:
                        tool_calls_from_plan.append({
                            "action": action,
                            "args": _step.get("args", {}),
                            "rationale": _step.get("rationale", ""),
                        })
                if tool_calls_from_plan:
                    logger.info(f"[plan] Plan detectado: {len(tool_calls_from_plan)} pasos")
                    return tool_calls_from_plan
        except Exception:
            pass

        # === CAPA 1: Parser blindado json_protocol ===
        if JSON_PROTOCOL_AVAILABLE and parse_response is not None:
            try:
                result: ParseResult = parse_response(response_text)
                if result.repairs_applied if hasattr(result, 'repairs_applied') else False:
                    logger.info(f"[json_protocol] repairs: {getattr(result, 'repairs_applied', [])}")
                if result.warnings:
                    for w in result.warnings[:3]:
                        logger.warning(f"[json_protocol] {w}")
                
                # Check if json_protocol parsed a single plan object instead of multiple tools
                parsed_tools = [tc.to_dict() for tc in result.tool_calls]
                if len(parsed_tools) == 1 and "plan_id" in parsed_tools[0].get("args", {}):
                    # It parsed the whole plan as one tool call with args containing the steps
                    args = parsed_tools[0].get("args", {})
                    if "steps" in args and isinstance(args["steps"], list):
                        tool_calls_from_plan = []
                        for _step in args["steps"]:
                            tc = {
                                "action": _step.get("tool") or _step.get("action", ""),
                                "args": _step.get("args", {}),
                                "rationale": _step.get("rationale", ""),
                            }
                            if tc["action"]:
                                tool_calls_from_plan.append(tc)
                        if tool_calls_from_plan:
                            return tool_calls_from_plan
                            
                return parsed_tools
            except Exception as e:
                logger.error(f"[json_protocol] error, fallback a parser legacy: {e}")

        # === CAPA 2: FALLBACK legacy ===
        tool_calls = []
        matches = re.finditer(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                json_str = match.group(1)
                json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
                parsed = json.loads(json_str)
                # Ensure we handle plan inside fallback
                if isinstance(parsed, dict) and "steps" in parsed and "plan_id" in parsed:
                    for _step in parsed["steps"]:
                        tc = {
                            "action": _step.get("tool") or _step.get("action", ""),
                            "args": _step.get("args", {}),
                            "rationale": _step.get("rationale", ""),
                        }
                        if tc["action"]:
                            tool_calls.append(tc)
                else:
                    tool_calls.append(parsed)
            except json.JSONDecodeError:
                pass
        if tool_calls:
            return tool_calls
        depth = 0
        start_idx = -1
        for i, char in enumerate(response_text):
            if char == '{':
                if depth == 0:
                    start_idx = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start_idx != -1:
                    json_str = response_text[start_idx:i+1]
                    if '"action"' in json_str or '"tool"' in json_str or '"plan_id"' in json_str:
                        try:
                            json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
                            parsed = json.loads(json_str)
                            if isinstance(parsed, dict) and "steps" in parsed and "plan_id" in parsed:
                                for _step in parsed["steps"]:
                                    tc = {
                                        "action": _step.get("tool") or _step.get("action", ""),
                                        "args": _step.get("args", {}),
                                        "rationale": _step.get("rationale", ""),
                                    }
                                    if tc["action"]:
                                        tool_calls.append(tc)
                            else:
                                tool_calls.append(parsed)
                        except json.JSONDecodeError:
                            pass
                    start_idx = -1
        return tool_calls

    def _validate_tool_call(self, action: str, args: Dict[str, Any]) -> Optional[str]:
        """
        Valida un tool call antes de ejecutarlo. Retorna mensaje de error o None si OK.
        """
        if not action or not isinstance(action, str):
            return f"Acción inválida (tipo {type(action).__name__})"
        if action not in self.tools:
            # Buscar tools similares (fuzzy)
            from difflib import get_close_matches
            similar = get_close_matches(action, list(self.tools.keys()), n=3, cutoff=0.5)
            hint = f" Â¿Sabias usar {similar[0]}?" if similar else ""
            return f"Herramienta '{action}' no existe. Disponibles: {len(self.tools)} tools. {hint}"
        if not isinstance(args, dict):
            return f"args debe ser dict, recibido {type(args).__name__}"

        # Detectar tools que requieren argumentos pero recibieron args vacíos.
        # Esto cubre el caso del regex_fallback_used: el LLM alucinó la action
        # sin proporcionar 'args' (queda {} y la tool falla por falta de campos).
        try:
            import inspect
            sig = inspect.signature(self.tools[action])
            required_params = [
                p.name for p in sig.parameters.values()
                if p.default is inspect.Parameter.empty
                and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
                and p.name not in ("args", "kwargs")
            ]
            if required_params and not any(args.get(k) for k in required_params):
                return (
                    f"Faltan argumentos requeridos para '{action}': {required_params}. "
                    f"Reintenta con el JSON completo, p.ej. "
                    f'{{"action": "{action}", "args": {{"{required_params[0]}": "..."}}}}.'
                )
        except (TypeError, ValueError):
            pass

        # Pre-flight: ensure pip deps for this tool are installed (silent install).
        deps = self._tool_requires.get(action)
        if deps:
            try:
                from core.auto_install import ensure_packages
                if not ensure_packages(deps, verbose=False):
                    return (
                        f"No pude instalar dependencias para '{action}': {deps}. "
                        f"Intenta: pip install {' '.join(deps)}"
                    )
            except Exception:
                pass
        return None

    def _guided_setup(self, integration_id: str, understanding: dict = None) -> str:
        """Guided setup flow for an integration. Returns a user-facing message
        that asks for the token, validates it, and saves it to .env.

        This is designed to work identically from terminal, Telegram, Discord,
        Instagram, and the web frontend. The next user message that looks like
        a token is auto-detected and applied to the pending integration.
        """
        from core.intent_engine import INTEGRATION_REGISTRY, validate_integration_token
        info = INTEGRATION_REGISTRY.get(integration_id)
        if not info:
            return f"❌ Integración desconocida: {integration_id}"

        # Persist the pending integration so the next turn can pick it up
        try:
            from pathlib import Path
            import json
            state_path = Path("state") / "pending_setup.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"integration_id": integration_id, "started_at": time.time()}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

        name = info["name"]
        icon = info["icon"]
        env_var = info["env_var"] or "(no requiere token)"
        help_url = info["help_url"]
        hint = info["format_hint"]

        # If env var is already set, confirm and offer to test/rotate
        existing = os.environ.get(env_var) if env_var and env_var != "(no requiere token)" else None
        if existing:
            return (
                f"{icon} **{name}** ya está configurado.\n\n"
                f"Variable de entorno: `{env_var}`\n"
                f"Estado: ✅ token presente\n\n"
                f"Para rotar el token, di **'rotar {integration_id}'**.\n"
                f"Para validar de nuevo, di **'validar {integration_id}'**."
            )

        return (
            f"{icon} **Configurar {name}**\n\n"
            f"Para vincular tu cuenta, necesito tu **{hint}**.\n\n"
            f"🔗 Dónde obtenerlo: {help_url}\n\n"
            f"Pégalo aquí en tu próximo mensaje. Lo guardaré cifrado en `.env` "
            f"bajo la variable `{env_var}` y validaré que funcione.\n\n"
            f"_Tip: en el dashboard puedes pegarlo en el campo de la integración._"
        )

    def _complete_pending_setup(self, text: str) -> Optional[str]:
        """If there's a pending setup waiting for a token, validate `text` as
        the token, save it, and return the confirmation. Returns None if no
        pending setup or if `text` doesn't look like a token."""
        from pathlib import Path
        import json
        state_path = Path("state") / "pending_setup.json"
        if not state_path.exists():
            return None
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        integration_id = data.get("integration_id")
        if not integration_id:
            return None

        from core.intent_engine import INTEGRATION_REGISTRY, validate_integration_token
        info = INTEGRATION_REGISTRY.get(integration_id)
        if not info or not info.get("env_var"):
            state_path.unlink(missing_ok=True)
            return None

        token = text.strip()
        # Quick sanity check: token-shaped strings are 20+ chars, may have _, ., -, alnum
        if len(token) < 20 or any(c.isspace() for c in token):
            return None  # doesn't look like a token — not a setup continuation

        # Validate (best effort)
        validation = validate_integration_token(integration_id, token)
        # Save regardless (user explicitly pasted it)
        env_var = info["env_var"]
        os.environ[env_var] = token
        try:
            from core.ui import save_to_env
            save_to_env(env_var, token)
        except Exception:
            # Fallback: write .env manually
            try:
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
            except Exception:
                pass

        # Clear pending state
        state_path.unlink(missing_ok=True)

        if validation.get("ok"):
            return (
                f"{info['icon']} **{info['name']}** configurado correctamente.\n\n"
                f"Variable `{env_var}` guardada en `.env`.\n"
                f"Validación: ✅ {validation.get('detail', 'OK')}\n\n"
                f"Listo para usar. Puedes invocarlo con skills o herramientas que "
                f"usen {info['name']}."
            )
        else:
            return (
                f"{info['icon']} **{info['name']}** guardado (pero no se pudo validar).\n\n"
                f"Variable `{env_var}` en `.env`.\n"
                f"Detalle: ⚠️ {validation.get('detail', '?')}\n\n"
                f"Verifica el token en {info['help_url']} y vuelve a pegarlo si falla."
            )

    def _communicate_user_request(self, user_input: str) -> None:
        """Muestra al usuario QUÉ entendió el agente de su solicitud."""
        if not TERMINAL_AVAILABLE or term is None:
            return
        term.info(f"Solicitud recibida: \"{user_input[:120]}{'...' if len(user_input) > 120 else ''}\"")

    # Tools que NO se pueden paralelizar (efectos secundarios)
    SERIAL_TOOLS: set = {
        "write_file", "create_directory", "delete_file", "move_file",
        "copy_file", "open_program", "use_terminal_window", "execute_cmd",
        "open_website", "create_web_preview",
        "ui_click_image", "mouse_click", "press_key", "type_text", "press_hotkey",
        "send_whatsapp_message", "send_email",
    }

    # ---- PLAN EXECUTOR PARALELO (MODEL-NATIVE) ----
    def _analyze_parallel_groups(self, steps: list) -> list:
        """Analiza dependencias entre pasos y agrupa los independientes para paralelizar.
        Retorna lista de grupos: [{"steps": [...], "parallel": True/False}]
        Cada grupo con `parallel=True` ejecuta todos sus pasos en paralelo.
        """
        if not steps:
            return []

        # Tools de solo lectura (se pueden paralelizar sin riesgo)
        READ_TOOLS = {"read_file", "list_directory", "glob_file", "web_search",
                       "deep_web_scrape", "screenshot", "check_system_resources"}

        groups = []
        current_group = []

        for i, step in enumerate(steps):
            tool = step.get("tool", "")
            # Serial tools siempre van solas en su grupo
            if tool in self.SERIAL_TOOLS:
                if current_group:
                    groups.append({"steps": list(current_group), "parallel": len(current_group) > 1})
                    current_group = []
                groups.append({"steps": [step], "parallel": False})
                continue

            # Si hay dependencia de datos entre este paso y el anterior, crear nuevo grupo
            if current_group:
                prev_step = current_group[-1]
                prev_tool = prev_step.get("tool", "")
                prev_args = prev_step.get("args", {})
                curr_args = step.get("args", {})
                # Detectar si curr_args referencia output de prev_step
                has_dep = False
                for k, v in curr_args.items():
                    if isinstance(v, str):
                        for pk, pv in prev_args.items():
                            if isinstance(pv, str) and pv in v:
                                has_dep = True
                                break
                if has_dep:
                    groups.append({"steps": list(current_group), "parallel": len(current_group) > 1})
                    current_group = [step]
                    continue

            current_group.append(step)

        if current_group:
            groups.append({"steps": list(current_group), "parallel": len(current_group) > 1})

        return groups

    TOOL_ALTERNATIVES: dict = {
        "read_file":        ["read_text_file", "get_file", "open_file", "cat_file"],
        "write_file":       ["save_file", "create_file", "write_text", "put_file"],
        "list_directory":   ["list_files", "list_dir", "ls", "dir_list"],
        "execute_cmd":      ["run_command", "shell_exec", "bash_cmd", "run_shell"],
        "web_search":       ["search_web", "search", "google_search", "brave_search"],
        "create_directory": ["mkdir", "make_dir", "create_dir"],
        "delete_file":      ["remove_file", "rm_file", "unlink_file"],
        "copy_file":        ["cp_file", "duplicate_file", "file_copy"],
        "move_file":        ["mv_file", "rename_file", "file_move"],
        "screenshot":       ["take_screenshot", "capture_screen", "screen_capture"],
    }

    def _try_run_tool(self, tool_name: str, resolved_args: dict):
        """Intenta ejecutar una herramienta con SmartRetry de 3 niveles."""
        import os as _os

        # Nivel 1: herramienta exacta
        if tool_name in self.tools:
            return self.tools[tool_name](**resolved_args), tool_name

        # Nivel 2: alternativas por nombre
        for alt in self.TOOL_ALTERNATIVES.get(tool_name, []):
            if alt in self.tools:
                try:
                    return self.tools[alt](**resolved_args), alt
                except Exception:
                    pass

        # Nivel 3: fallback via execute_cmd para ops de archivo/directorio
        if "execute_cmd" in self.tools:
            path = resolved_args.get("path", resolved_args.get("file_path", "."))
            if tool_name == "list_directory":
                cmd = f'dir "{path}"' if _os.name == "nt" else f'ls -la "{path}"'
                result = self.tools["execute_cmd"](command=cmd)
                return result, "execute_cmd[list_directory]"
            if tool_name == "read_file":
                cmd = f'type "{path}"' if _os.name == "nt" else f'cat "{path}"'
                result = self.tools["execute_cmd"](command=cmd)
                return result, "execute_cmd[read_file]"

        _alias_names = getattr(self, "_alias_tool_names", set())
        available = sorted(n for n in self.tools.keys() if n not in _alias_names)[:10]
        raise ValueError(
            f"Tool '{tool_name}' no disponible. "
            f"Tools registradas ({len(self.tools)}): {available}"
        )

    def _execute_step(self, step: dict, step_num: int, total: int,
                       plan: dict, progress_callback=None) -> dict:
        """Ejecuta un paso con SmartRetry de 3 niveles. Usado por workers paralelos."""
        tool_name = step.get("tool") or step.get("action", "")
        args = step.get("args", {})
        rationale = step.get("rationale", "")

        step_msg = f"[Paso {step_num}/{total}] {rationale or tool_name}"
        _set_phase("tool_executing", step_msg, tool_name=tool_name,
                   rationale=rationale, tool_args_summary=str(args)[:80],
                   step=step_num, total=total)

        resolved_args = self._resolve_step_args(args, plan)
        t0 = time.time()

        try:
            result, used_tool = self._try_run_tool(tool_name, resolved_args)
            duration = int((time.time() - t0) * 1000)
            _set_phase("tool_executed", f"OK ({duration}ms)",
                       step=step_num, total=total, tool_name=used_tool, duration_ms=duration)
            return {"step": step_num, "tool": used_tool, "ok": True,
                    "result": result, "duration_ms": duration}
        except Exception as e:
            duration = int((time.time() - t0) * 1000)
            err = f"Error en paso {step_num} ({tool_name}): {e}"
            _set_phase("error", err, step=step_num, total=total, tool_name=tool_name)
            return {"step": step_num, "tool": tool_name, "ok": False,
                    "error": str(e), "duration_ms": duration}

    def _execute_plan_parallel(self, plan: dict, progress_callback=None) -> Optional[str]:
        """Ejecuta un plan con paralelizacion inteligente de pasos independientes."""
        if not plan or not plan.get("steps"):
            return None

        steps = plan["steps"]
        total = len(steps)

        # 1. Analizar grupos de paralelizacion
        groups = self._analyze_parallel_groups(steps)

        results = []
        global_step_counter = [0]

        try:
            # 2. Ejecutar grupos secuencialmente, pasos dentro de grupo en paralelo
            for g_idx, group in enumerate(groups):
                g_steps = group["steps"]
                is_parallel = group["parallel"]
    
                if is_parallel:
                    # Ejecutar todos los pasos del grupo en paralelo
                    step_futures = {}
                    with ThreadPoolExecutor(max_workers=min(len(g_steps), 8)) as executor:
                        for step in g_steps:
                            global_step_counter[0] += 1
                            sn = global_step_counter[0]
                            future = executor.submit(
                                self._execute_step, step, sn, total, plan, progress_callback
                            )
                            step_futures[future] = step
    
                        for future in as_completed(step_futures):
                            try:
                                result = future.result(timeout=300)
                                results.append(result)
                            except Exception as e:
                                results.append({
                                    "step": global_step_counter[0],
                                    "tool": step_futures[future].get("tool", "?"),
                                    "ok": False, "error": f"Thread error: {e}"
                                })
                else:
                    # Ejecutar pasos secuencialmente (1 por grupo)
                    for step in g_steps:
                        global_step_counter[0] += 1
                        sn = global_step_counter[0]
                        result = self._execute_step(step, sn, total, plan, progress_callback)
                        results.append(result)
        finally:
            pass

        # 3. Verificar outputs
        missing = []
        if plan.get("verification"):
            for v in plan["verification"]:
                if v.get("check") == "output_file_exists":
                    p = v["path"]
                    if not os.path.exists(p):
                        missing.append(p)

        # 4. Ordenar resultados por numero de paso
        results.sort(key=lambda r: r.get("step", 0))

        # 5. Construir respuesta final
        n_ok = sum(1 for r in results if r["ok"])
        n_fail = sum(1 for r in results if not r["ok"])
        total_duration = sum(r.get("duration_ms", 0) for r in results)
        summary = f"Plan completado: {n_ok} OK, {n_fail} fallos ({total_duration}ms total)"
        if results:
            summary += "\n\nDetalle:\n"
            for r in results:
                status = "OK" if r["ok"] else "FAIL"
                dur = r.get("duration_ms", 0)
                summary += f"  [{status}] Paso {r['step']}: {r['tool']} ({dur}ms)"
                if not r["ok"]:
                    summary += f" -> {r.get('error', '?')}"
                else:
                    res_content = str(r.get("result", "") or "").strip()
                    if res_content:
                        summary += f"\n    Resultado: {res_content[:600]}"
                summary += "\n"

        if missing:
            summary += f"\nArchivos no generados: {', '.join(missing)}"

        self.history.append({"role": "assistant", "content": summary})
        return summary

    def _resolve_step_args(self, args: dict, plan: dict) -> dict:
        """Resuelve placeholders como <PRIMER_VIDEO_ENCONTRADO> con archivos reales."""
        if not args:
            return args
        resolved = {}
        candidates = plan.get("candidate_files", [])
        first_video = candidates[0]["path"] if candidates else None
        folder = plan.get("preconditions", [{}])[0].get("path") if plan.get("preconditions") else None

        for k, v in args.items():
            if isinstance(v, str):
                if v == "<PRIMER_VIDEO_ENCONTRADO>" and first_video:
                    resolved[k] = first_video
                elif v == "<CARPETA_DESTINO>" and folder:
                    resolved[k] = folder
                elif v == "<EXTRAER_DEL_TEXTO>":
                    resolved[k] = v  # El LLM lo inferirá
                else:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved

    def run(self, user_input: str, custom_system_prompt: str = None, agent_skills: dict = None,
            agent_id: str = "main", progress_callback=None, images: list = None) -> str:
        """Bucle principal del agente con fases claras y comunicación rica.

        `images` (opcional): lista de dicts {"data": base64, "mime": "image/png"}.
        Se guardan a disco y se referencian en el contexto para modelos con visión.
        """
        # --- Save incoming images to disk for downstream tools / vision models ---
        if images:
            try:
                import base64
                from pathlib import Path
                import time as _t
                img_dir = Path("state") / "incoming_images"
                img_dir.mkdir(parents=True, exist_ok=True)
                saved_paths = []
                for idx, img in enumerate(images):
                    b64 = img.get("data", "")
                    mime = img.get("mime", "image/png")
                    ext = mime.split("/")[-1] if "/" in mime else "png"
                    if "," in b64:
                        b64 = b64.split(",", 1)[1]
                    fname = f"img_{int(_t.time()*1000)}_{idx}.{ext}"
                    (img_dir / fname).write_bytes(base64.b64decode(b64))
                    saved_paths.append(str(img_dir / fname))
                user_input = f"{user_input}\n\n[Imágenes adjuntas: {len(saved_paths)} archivo(s) en {', '.join(saved_paths)}]"
            except Exception:
                pass

        # --- PENDING SETUP CHECK (if user is mid-setup, treat input as a token) ---
        try:
            setup_response = self._complete_pending_setup(user_input)
            if setup_response:
                self.history.append({"role": "user", "content": user_input})
                self.history.append({"role": "assistant", "content": setup_response})
                _set_phase("idle", "Integración configurada")
                return setup_response
        except Exception:
            pass

        # ---- FASE 1: ANALYZING (comprender qué pidió el usuario) ----
        get_agent_status()["is_active"] = True
        get_agent_status()["user_request"] = user_input
        get_agent_status()["started_at"] = datetime.now().isoformat()
        get_agent_status()["step"] = 0
        get_agent_status()["total_steps"] = 0
        get_agent_status()["error_message"] = ""
        get_agent_status()["tool_name"] = ""
        get_agent_status()["tool_args_summary"] = ""
        get_agent_status()["tool_result_summary"] = ""
        get_agent_status()["tool_result_ok"] = None
        get_agent_status()["plan"] = None
        get_agent_status()["flow_phases"] = []
        
        # Omit analyzing print as we already echo the user input in the REPL
        _set_phase("analyzing", f"Analizando solicitud...")
        if progress_callback:
            try: progress_callback("analyzing", f"Analizando solicitud...")
            except Exception: pass
        
        # ContextProbe: leer AUTOMYX.md del directorio actual si existe
        import os as _os
        _project_ctx = ""
        for _ctx_file in ["AUTOMYX.md", "CLAUDE.md", "README.md"]:
            _ctx_path = _os.path.join(_os.getcwd(), _ctx_file)
            if _os.path.exists(_ctx_path):
                try:
                    with open(_ctx_path, "r", encoding="utf-8", errors="replace") as _f:
                        _content = _f.read()[:3000]
                    _project_ctx = f"\n\n[CONTEXTO DEL PROYECTO - {_ctx_file}]\n{_content}"
                    break
                except Exception:
                    pass

        # Lista dinamica de tools disponibles (para que el LLM use nombres exactos)
        # Integraciones prioritarias van primero para que el LLM siempre las vea
        _PRIORITY_PREFIXES = (
            "notion_", "github_", "gh_", "telegram_", "discord_",
            "elevenlabs_", "weather_", "obsidian_", "calendar_", "crypto_",
        )
        # Excluir los ~8000 aliases coloquiales de mega_tools (haz_/hazme_/do_/make_/
        # run_/ejecuta_X, etc.) de la lista visible: alfabéticamente ahogaban a tools
        # reales (execute_cmd, write_file, generate_vyrex_video nunca aparecían en los
        # primeros 200). Los aliases siguen registrados y funcionan si el LLM los usa,
        # solo no se listan explícitamente en el prompt.
        _alias_names = getattr(self, "_alias_tool_names", set())
        _all_tool_names = sorted(n for n in self.tools.keys() if n not in _alias_names)
        _priority = [t for t in _all_tool_names if any(t.startswith(p) for p in _PRIORITY_PREFIXES)]
        _rest     = [t for t in _all_tool_names if t not in set(_priority)]
        _tool_names = _priority + _rest
        # Sin aliases, las tools reales son ~400 (~2000 tokens listadas completas) -- barato
        # frente al costo de que el LLM no sepa que una tool existe. Tope holgado en 600.
        _tool_cap = 600
        _tool_list  = ", ".join(_tool_names[:_tool_cap])
        if len(_tool_names) > _tool_cap:
            _tool_list += f" ... ({len(_tool_names)} total, +{len(_alias_names)} aliases coloquiales ocultos)"

        _workspace_ctx = ""
        if _WORKSPACE_AVAILABLE and get_workspace_manager is not None:
            try:
                _workspace_ctx = "\n" + get_workspace_manager().get_context_string()
            except Exception:
                pass

        # Integraciones activas (tokens configurados)
        _active_integrations = []
        if _os.environ.get("NOTION_API_KEY", "").strip():
            _active_integrations.append("Notion (notion_create_page, notion_search, notion_append_blocks, notion_get_database, notion_set_token)")
        if _os.environ.get("GITHUB_TOKEN", "").strip():
            _active_integrations.append("GitHub (gh_list_repos, gh_create_pr, github_create_pr ...)")
        if _os.environ.get("TELEGRAM_BOT_TOKEN", "").strip():
            _active_integrations.append("Telegram (send_telegram)")
        if _os.environ.get("ELEVENLABS_API_KEY", "").strip():
            _active_integrations.append("ElevenLabs TTS")
        if _os.environ.get("OPENWEATHER_API_KEY", "").strip():
            _active_integrations.append("OpenWeather")
        _integrations_line = (
            f"\nINTEGRACIONES ACTIVAS (tokens configurados, ÚSALAS SIN DUDAR): "
            + ", ".join(_active_integrations)
            if _active_integrations else ""
        )

        _os_name_lower = str(self.hw.os_name).lower()
        _is_windows = "win" in _os_name_lower
        _shell_hint = (
            "SHELL: Windows CMD. USA SOLO comandos CMD/PowerShell. "
            "PROHIBIDO usar bash/linux: grep→findstr, cat→type, ls→dir, tail→nada (usa 'type' o PowerShell Get-Content -Tail N), "
            "head→PowerShell Get-Content -TotalCount N, touch→echo.>, rm→del, mv→move, cp→copy. "
            "Para git, python, pip, node: funcionan igual en CMD."
        ) if _is_windows else (
            "SHELL: Linux/macOS bash. Puedes usar grep, cat, ls, tail, head, rm, mv, cp normalmente."
        )

        hw_context = (
            f"\n\n[CONTEXTO DEL SISTEMA — LEER ANTES DE RESPONDER]\n"
            f"OS: {self.hw.os_name} | Arch: {self.hw.arch} | "
            f"Dir: {_os.getcwd()} | GPU: {self.hw.gpu_vendor}\n"
            f"{_shell_hint}\n"
            f"IDENTIDAD CRITICA: Eres un agente que corre 100% LOCAL en el PC del usuario. "
            f"NO eres una IA en la nube. TIENES acceso directo al sistema de archivos, "
            f"puedes ejecutar comandos, leer/escribir archivos y operar el PC sin restricciones. "
            f"NUNCA digas 'no puedo ejecutar en tu PC', 'soy una IA en la nube' ni 'no tengo acceso'. "
            f"Si el usuario pide ejecutar algo → USA UNA HERRAMIENTA AHORA MISMO, no expliques.\n"
            f"HERRAMIENTAS DISPONIBLES (usa EXACTAMENTE estos nombres): {_tool_list}"
            f"{_integrations_line}"
            f"{_project_ctx}"
            f"{_workspace_ctx}"
        )

        if self.history and self.history[0]["role"] == "system":
            if custom_system_prompt:
                base = custom_system_prompt
            else:
                base = self.system_prompt

            # Aplicar filtros de permisos si los hay (sin destruir el prompt)
            if agent_skills:
                if not agent_skills.get("write", True):
                    for tool in ["write_file", "create_directory", "delete_file", "ai_form_filler"]:
                        base = base.replace(f'"{tool}"', f'"[BLOQUEADO:{tool}]"')
                if not agent_skills.get("pc", True):
                    for tool in ["execute_cmd", "execute_shell", "control_pc", "press_key", "type_text"]:
                        base = base.replace(f'"{tool}"', f'"[BLOQUEADO:{tool}]"')

            self.history[0]["content"] = base + hw_context

        self.history.append({"role": "user", "content": user_input})

        # Inyectar contexto de auto-aprendizaje (conversaciones similares + lecciones)
        context_parts = []
        if aumformbring_system is not None:
            try:
                ctx = aumformbring_system.inject_context(user_input)
                if ctx:
                    context_parts.append(ctx)
            except Exception:
                pass
        if ErrorLearningSystem is not None:
            try:
                warnings = ErrorLearningSystem.get_warnings_for_request(user_input)
                if warnings:
                    context_parts.append(warnings)
            except Exception:
                pass
        if context_parts:
            self.history.append({"role": "system", "content": "\n".join(context_parts)})

        # ── Native tool_use para Anthropic (previene planes JSON) ──────────
        if hasattr(self.client, "set_tool_schemas"):
            try:
                self.client.set_tool_schemas(self.tools)
            except Exception:
                pass

        final_answer = ""
        recent_actions: List[str] = []  # anti-loop
        consecutive_errors: int = 0     # anti-confusion
        recent_exact: set = set()       # detección de duplicado exacto
        tools_used_in_task: list = []   # para auto-skill-save

        # ---- BUCLE PRINCIPAL ----
        # Safety net: ajustar segun el modelo. Modelos rapidos (M3) toleran
        # mas iteraciones; modelos lentos (GPT-OSS 120B) necesitan menos.
        try:
            from core.model_config import get_model_config
            _mc = get_model_config(self.model_name)
            if _mc.get("fast_mode"):
                max_iterations = 12  # M3/M2.7: rapido, podemos permitirnos
            elif "120b" in self.model_name.lower() or "340b" in self.model_name.lower():
                max_iterations = 8   # modelos grandes: minimizar iteraciones
            else:
                max_iterations = 10
        except Exception:
            max_iterations = 10
        for iteration in range(max_iterations):
            get_agent_status()["step"] = iteration + 1

            # Recordatorio de tarea cada 3 iteraciones → previene confusión del LLM
            if iteration > 0 and iteration % 3 == 0:
                _remaining = max_iterations - iteration
                self.history.append({"role": "system", "content": (
                    f"[RECORDATORIO SISTEMA — iteración {iteration+1}/{max_iterations}] "
                    f"Tarea original: '{user_input[:200]}'. "
                    f"{'URGENTE: FINALIZA YA con lo que tienes, resume resultados.' if _remaining <= 2 else 'Continúa con foco. No repitas herramientas ya ejecutadas.'}"
                )})

            # OPTIMIZACION: truncar historial agresivamente para fast_mode
            # Cada llamada envia todo el historial, asi que menos historial = mas rapido
            _max_hist = 10 if self._fast_mode else 20
            if len(self.history) > _max_hist + 1:
                # Mantener system prompt (index 0) y los ultimos N mensajes
                self.history = [self.history[0]] + self.history[-(_max_hist):]

            # OPTIMIZACION: comprimir mensajes antiguos del historial
            # (en vez de descartar, resume para preservar contexto)
            try:
                from core.speed import compress_history_messages
                self.history = compress_history_messages(self.history, max_chars_per_msg=400)
            except Exception:
                pass

            # ---- FASE 2: THINKING (llamar al LLM) ----
            _set_phase("thinking", f"Pensando cómo responder (paso {iteration+1})...")
            if TERMINAL_AVAILABLE and term:
                term.llm_thinking()

            ai_message = ""
            reasoning_accumulated = ""
            actual_model = ModelProvider.get_display_name(self.model_name)
            api_error: Optional[str] = None

            try:
                # Use model_config for proper parameters per model
                from core.model_config import get_model_config, supports_streaming
                model_config = get_model_config(actual_model)
                # OPTIMIZACION: en iteraciones internas (tool calls), limitamos
                # max_tokens drasticamente. Solo la respuesta final (sin tools)
                # tiene el budget completo.
                _max_tokens = model_config.get("max_tokens", 4096)
                if self._fast_mode:
                    # Fast mode: maximo 1024 tokens para tool calls
                    _max_tokens = min(_max_tokens, 1024)
                else:
                    # 4096 da margen para respuestas largas. El plan-cap (8 tool calls)
                    # evita que el modelo genere 30+ pasos aunque haya tokens disponibles.
                    _max_tokens = min(_max_tokens, 4096)
                # Timeout generoso para NVIDIA API (puede tardar 90-120s en cold start)
                _timeout = 120
                # OPTIMIZACION: session headers para affinity con NVIDIA
                # (no usar en streaming porque el cliente openai lo maneja)
                _call_kwargs = {
                    "model": actual_model,
                    "messages": self.history,
                    "temperature": model_config.get("temperature", 0.7),
                    "top_p": model_config.get("top_p", 0.95),
                    "max_tokens": _max_tokens,
                    "stream": supports_streaming(actual_model),
                    "timeout": _timeout,
                }
                # extra_body para modelos con thinking mode (Nemotron Super, etc.)
                if model_config.get("thinking"):
                    _reasoning_budget = model_config.get("reasoning_budget", 8192)
                    _call_kwargs["extra_body"] = {
                        "chat_template_kwargs": {"enable_thinking": True},
                        "reasoning_budget": _reasoning_budget,
                    }
                # Anhadir session headers solo si no es streaming (compatibilidad)
                if not _call_kwargs["stream"]:
                    try:
                        from core.speed import get_session_headers
                        _call_kwargs["extra_headers"] = get_session_headers()
                    except Exception:
                        pass
                
                completion = self.client.chat.completions.create(**_call_kwargs)
                if _call_kwargs["stream"]:
                    if TERMINAL_AVAILABLE and term:
                        term.llm_response_stream("")  # marca inicio de stream
                    _last_stream_update = 0.0
                    _STREAM_UPDATE_INTERVAL = 0.12  # max ~8 display updates/seg
                    for chunk in completion:
                        if not getattr(chunk, "choices", None) or len(chunk.choices) == 0:
                            continue
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            reasoning_accumulated += delta.reasoning_content
                            get_agent_status()["reasoning"] = reasoning_accumulated
                            if TERMINAL_AVAILABLE and term and hasattr(term, 'live_reasoning'):
                                try: term.live_reasoning(reasoning_accumulated)
                                except Exception: pass
                        if getattr(delta, "content", None) is not None:
                            ai_message += delta.content
                            # Throttle: actualizar display máximo cada 120ms
                            _now = time.time()
                            if TERMINAL_AVAILABLE and term and (_now - _last_stream_update) >= _STREAM_UPDATE_INTERVAL:
                                _set_phase("streaming", ai_message)
                                _last_stream_update = _now
                else:
                    if hasattr(completion, "choices") and len(completion.choices) > 0:
                        ai_message = completion.choices[0].message.content or ""
                
                if TERMINAL_AVAILABLE and term:
                    term.llm_response_done()

                if _TRACKER_AVAILABLE and get_tracker is not None:
                    try:
                        _usage = getattr(completion, "usage", None)
                        if _usage is not None:
                            get_tracker().track(
                                actual_model,
                                getattr(_usage, "prompt_tokens", 0),
                                getattr(_usage, "completion_tokens", 0),
                            )
                    except Exception:
                        pass

            except Exception as api_err:
                api_error = str(api_err)
                logger.warning(f"[run] API error: {api_err}")

                # 429 rate-limit: esperar antes de reintentar
                _is_429 = "429" in api_error or "Too Many Requests" in api_error
                if _is_429:
                    _set_phase("error", f"Rate limit ({self.model_name}), esperando 8s...")
                    import time as _t429
                    _t429.sleep(8)
                else:
                    _set_phase("error", f"Error con {self.model_name}, reintentando...")

                # Fallback inteligente según provider:
                # - Anthropic → reintentar mismo modelo SIN tool schemas (modo texto)
                # - Otros     → usar cliente NVIDIA con modelo ligero
                _fb_client = None
                _fb_model  = actual_model
                try:
                    if self.provider == ModelProvider.ANTHROPIC:
                        # Deshabilitar tool_use y reintentar con el mismo modelo
                        _fb_client = self.client
                        if hasattr(_fb_client, "chat") and hasattr(_fb_client.chat, "completions"):
                            _fb_client.chat.completions._schemas = None
                    else:
                        from core.model_config import get_fallback_model
                        _fb_model  = get_fallback_model()
                        _fb_client = ModelProvider.get_client(_fb_model)
                except Exception:
                    pass

                if _fb_client is None:
                    _fb_client = self.client

                if TERMINAL_AVAILABLE and term:
                    term.warn(f"Reintentando con {_fb_model} (sin tool_use)..." )
                try:
                    completion = _fb_client.chat.completions.create(
                        model=_fb_model,
                        messages=self.history,
                        temperature=0.3,
                        top_p=0.95,
                        max_tokens=4096,
                        stream=False,
                        timeout=90,
                    )
                    ai_message = completion.choices[0].message.content or ""
                except Exception as e2:
                    msg = f"Error: {e2}"
                    _set_phase("error", msg, error_message=msg)
                    if TERMINAL_AVAILABLE and term:
                        term.error(msg)
                    get_agent_status()["is_active"] = False
                    return msg

            self.history.append({"role": "assistant", "content": ai_message})

            # ---- FASE 3: PARSE TOOL CALLS ----
            tool_calls = self._parse_tool_calls(ai_message)
            if not tool_calls:
                # Anti-refusal: detectar si el LLM está rechazando ejecutar sin razón válida
                _ai_low = ai_message.lower()
                _refusal_phrases = [
                    "soy una ia en la nube",
                    "soy una ia de la nube",
                    "no tengo acceso a tu",
                    "no puedo ejecutar comandos en tu",
                    "no puedo acceder a tu",
                    "no puedo interactuar con tu",
                    "i'm a cloud ai",
                    "i can't access your",
                    "no puedo ejecutar directamente",
                    "no tengo capacidad de ejecutar",
                ]
                _is_refusal = any(p in _ai_low for p in _refusal_phrases)
                _has_action_word = any(w in user_input.lower() for w in [
                    "ejecuta", "ejecutar", "corre", "correr", "lanza", "lanzar",
                    "abre", "abrir", "hazlo", "haz", "arranca", "inicia", "iniciar",
                    "run", "start", "do it", "do this",
                ])

                if _is_refusal and _has_action_word and iteration < max_iterations - 1:
                    _set_phase("error", "Refusal detectado — forzando ejecución con herramientas")
                    self.history.append({"role": "system", "content": (
                        "CORRECCIÓN CRÍTICA: Acabas de decir que no puedes ejecutar, pero ESO ES FALSO. "
                        "Eres un agente LOCAL con acceso total al PC del usuario. "
                        f"Herramientas disponibles ahora mismo: {_tool_list[:300]}. "
                        "USA UNA HERRAMIENTA INMEDIATAMENTE. La tarea del usuario es: "
                        f"'{user_input[:200]}'. "
                        "Responde SOLO con el JSON de la herramienta, sin texto adicional."
                    )})
                    continue  # Forzar otra iteración

                # Detectar "promesas sin acción": modelo anuncia qué va a hacer pero no llama herramientas
                _promise_patterns = [
                    "voy a leer", "voy a crear", "voy a escribir", "voy a modificar",
                    "voy a actualizar", "voy a ejecutar", "voy a proceder", "voy a revisar",
                    "voy a analizar", "voy a cambiar", "voy a reemplazar", "voy a generar",
                    "voy a hacer", "voy a empezar", "voy a comenzar", "voy a arreglar",
                    "procederé a", "a continuación voy", "luego voy a", "después voy a",
                    "ahora voy a", "primero voy a", "comenzaré", "empezaré a",
                    "el siguiente paso", "paso siguiente", "haré lo siguiente",
                    "i will now", "let me now", "i'll now", "now i'll",
                ]
                _is_promise = any(p in _ai_low for p in _promise_patterns)

                if _is_promise and iteration < max_iterations - 1:
                    _set_phase("error", "Promesa sin acción — ejecutando herramienta directamente")
                    self.history.append({"role": "system", "content": (
                        "⚠️ ERROR: Acabas de ANUNCIAR lo que ibas a hacer sin ejecutar ninguna herramienta. "
                        "Esto está PROHIBIDO. NUNCA anuncies — actúa de inmediato. "
                        "EJECUTA AHORA la acción pendiente usando una herramienta. "
                        f"Tarea: '{user_input[:200]}'. "
                        "Responde ÚNICAMENTE con el JSON de la herramienta. Sin texto. Sin explicaciones."
                    )})
                    continue  # Forzar ejecución real

                # No hay refusal ni promesa → es respuesta final legítima
                _set_phase("responding", "Generando respuesta final...")
                if progress_callback:
                    try: progress_callback("responding", "Generando respuesta final", progress=0.95)
                    except Exception: pass
                if TERMINAL_AVAILABLE and term:
                    term.success("Tarea completada, preparando respuesta final.")
                final_answer = ai_message
                break

            # ---- FASE 3.5: PLAN NATIVO + EJECUCION PARALELA ----
            # Si hay multiples tool calls, ejecutar en paralelo con plan visual
            if len(tool_calls) >= 2:
                # Cap: si el modelo genera demasiadas llamadas del mismo tool (ej: 36 web_search),
                # recortamos a un máximo razonable para evitar planes interminables.
                _MAX_SAME_TOOL = 8
                _tc_actions = [tc.get("action", "") for tc in tool_calls]
                if len(tool_calls) > _MAX_SAME_TOOL:
                    _unique_actions = set(_tc_actions)
                    if len(_unique_actions) <= 2:
                        # Casi todos son el mismo tool → recortar
                        tool_calls = tool_calls[:_MAX_SAME_TOOL]

                plan_steps = []
                for idx, tc in enumerate(tool_calls, 1):
                    action = tc.get("action", "?")
                    args = tc.get("args", {})
                    try:
                        from core.intent_engine import resolve_tool_alias
                        resolved = resolve_tool_alias(action)
                        if resolved != action and resolved in self.tools:
                            action = resolved
                    except Exception:
                        pass
                    plan_steps.append({
                        "n": idx,
                        "tool": action,
                        "args": args,
                        "rationale": tc.get("rationale", action),
                    })
                get_agent_status()["plan"] = {"steps": plan_steps, "total": len(plan_steps), "completed": 0}
                if progress_callback:
                    try: progress_callback("plan_created", f"Plan de {len(plan_steps)} pasos en paralelo", plan=plan_steps)
                    except Exception: pass
                _plan_obj = {"plan_id": f"plan_{int(time.time())}", "steps": plan_steps}
                _plan_result = self._execute_plan_parallel(_plan_obj, progress_callback=progress_callback)
                if _plan_result:
                    all_results_msg = _plan_result
                else:
                    all_results_msg = "Error ejecutando plan en paralelo."

                # Si todos los pasos fallaron, instruir al LLM que NO afirme éxito
                n_ok_check = all_results_msg.count("[OK]") if "[OK]" in all_results_msg else (
                    int(all_results_msg.split("OK,")[0].split(":")[-1].strip()) if "OK," in all_results_msg else -1
                )
                all_failed = ("0 OK" in all_results_msg or n_ok_check == 0)
                if all_failed and ("fallos" in all_results_msg or "FAIL" in all_results_msg):
                    all_results_msg += (
                        "\n\n⚠️ INSTRUCCIÓN CRÍTICA: Ningún paso se ejecutó exitosamente. "
                        "NO afirmes que completaste la tarea. "
                        "Informa al usuario del error específico y qué necesita corregirse."
                    )

                # Skip the sequential execution since we already ran them in parallel
                get_agent_status()["tool_result_ok"] = not all_failed
                self.history.append({"role": "user", "content": f"Resultados de herramientas (paralelo):\n{all_results_msg}"})
                _set_phase("learning", "Resultados recolectados", tool_result_summary=all_results_msg)
                if progress_callback:
                    try: progress_callback("learning", "Resultados recolectados")
                    except Exception: pass
                continue
            else:
                get_agent_status()["plan"] = None
                get_agent_status()["flow_phases"] = []

            # ---- FASE 4: EJECUTAR TOOL CALL UNICO (cuando no hay plan multi-paso) ----
            # Claude Code style: Only set phase, avoid double printing
            all_results_msg = ""
            loop_detected = False

            for idx, tool_call in enumerate(tool_calls, 1):
                if "action" not in tool_call:
                    msg = f"[Tool {idx}] No se encontró 'action' en tool_call. Ignorando."
                    if TERMINAL_AVAILABLE and term:
                        term.warn(msg)
                    all_results_msg += msg + "\n"
                    continue

                action = tool_call["action"]
                args = tool_call.get("args", {}) or {}

                # 4.0: Resolver aliases coloquiales (ej: "guardar_archivo" → "write_file")
                try:
                    from core.intent_engine import resolve_tool_alias
                    resolved = resolve_tool_alias(action)
                    if resolved != action and resolved in self.tools:
                        if TERMINAL_AVAILABLE and term:
                            term.debug(f"alias: {action} → {resolved}")
                        action = resolved
                except Exception:
                    pass

                # 4.1: Validar el tool call
                validation_error = self._validate_tool_call(action, args)
                if validation_error:
                    _set_phase("error", f"Validación falló: {validation_error[:80]}", error_message=validation_error)
                    if TERMINAL_AVAILABLE and term:
                        term.error(f"Validación: {validation_error}")
                    all_results_msg += f"[Tool {idx}] {validation_error}\n"
                    continue

                # 4.2: Detección de duplicado EXACTO (misma acción + mismos args = 100% atascado)
                # NOTA: la detección por "mismo tool N veces" se eliminó porque bloqueaba
                # tool calls legítimas (ej: 5 execute_cmd con comandos distintos).
                # Solo bloqueamos cuando los args son EXACTAMENTE iguales.
                try:
                    import json as _j_dedup
                    _exact_key = f"{action}|{_j_dedup.dumps(args, sort_keys=True, default=str)[:200]}"
                    if _exact_key in recent_exact:
                        all_results_msg += (
                            f"SISTEMA: Ya ejecutaste '{action}' con EXACTAMENTE los mismos argumentos. "
                            f"El resultado NO cambiará. CAMBIA DE ESTRATEGIA — usa otra herramienta o parámetros distintos.\n"
                        )
                        continue
                    recent_exact.add(_exact_key)
                except Exception:
                    pass
                recent_actions.append({"action": action, "args": args})
                if len(recent_actions) > 20:
                    recent_actions.pop(0)

                # Registrar tool para auto-skill-save al finalizar
                tools_used_in_task.append({
                    "tool": action,
                    "args": {k: str(v)[:60] for k, v in (args or {}).items()}
                })

                # Auto-web-search cuando hay 2+ errores consecutivos y web_search disponible
                if consecutive_errors >= 2 and "web_search" in self.tools and action != "web_search":
                    _err_query = f"{action} error {str(args.get('command', args.get('path', '')))[:50]}"
                    try:
                        _ws_result = self.tools["web_search"](query=_err_query[:120])
                        all_results_msg += f"\n[AUTO-BÚSQUEDA] Soluciones encontradas para '{action}':\n{str(_ws_result)[:400]}\n"
                    except Exception:
                        pass

                # 4.3: Comunicar QUÉ voy a hacer y por qué
                args_summary = _truncate_args(args)
                rationale = tool_call.get("rationale", "")
                narrative = f"[{idx}/{len(tool_calls)}] "
                if rationale:
                    narrative += f"{rationale} -> {action}({args_summary})"
                else:
                    narrative += f"Ejecutando {action}({args_summary})"
                get_agent_status()["tool_name"] = action
                get_agent_status()["tool_args_summary"] = args_summary
                get_agent_status()["reasoning"] = rationale
                
                _set_phase("tool_executing", narrative,
                          tool_name=action, tool_args_summary=args_summary, rationale=rationale,
                          step=idx, total=len(tool_calls))
                
                if TERMINAL_AVAILABLE and term:
                    # Note: term.tool_executing ya imprime la acción, evitamos imprimir cosas dobles
                    # Lo comentamos porque la UI ya lo muestra a través de _set_phase y repl.py
                    # term.tool_executing(action, args)
                    pass

                # 4.4: Ejecutar la tool con medición de tiempo y auto-healing
                t0 = time.time()
                tool_result: Any = None
                tool_exc: Optional[BaseException] = None

                # OPTIMIZACION: tool result caching - no re-ejecutar misma tool
                # con mismos args (ahorra tiempo en llamadas repetidas)
                try:
                    from core.speed import get_cached_tool_result, set_cached_tool_result
                    cached = get_cached_tool_result(action, args)
                    if cached is not None:
                        tool_result = cached
                        duration_ms = int((time.time() - t0) * 1000)
                        _set_phase("tool_executed", f"{action} (cache hit)",
                                   step=iteration+1, total=len(tool_calls),
                                   tool_name=action, duration_ms=duration_ms)
                        result_msg = f"Herramienta {action} ejecutada en {duration_ms}ms (cache). Resultado: {tool_result}"
                        all_results_msg += result_msg + "\n"
                        continue
                except Exception:
                    pass

                try:
                    tool_result = self.tools[action](**args)
                    # Guardar en cache para llamadas futuras
                    try:
                        from core.speed import set_cached_tool_result
                        set_cached_tool_result(action, args, tool_result)
                    except Exception:
                        pass
                except (ImportError, ModuleNotFoundError) as e:
                    # Auto-install attempt: detect missing module, pip install, retry once.
                    import re as _re
                    m = _re.search(r"no module named ['\"]?([\w\-]+)", str(e))
                    missing_mod = m.group(1) if m else None
                    if missing_mod and missing_mod not in {"automyx"}:  # don't install our own packages
                        try:
                            from core.auto_install import ensure_packages
                            _set_phase("installing",
                                       f"Instalando dependencia faltante: {missing_mod}",
                                       tool_name=action)
                            ok = ensure_packages([missing_mod], verbose=False)
                            if ok:
                                # Retry the tool once with a fresh import
                                try:
                                    tool_result = self.tools[action](**args)
                                except Exception as e2:
                                    tool_exc = e2
                            else:
                                tool_exc = RuntimeError(
                                    f"No pude instalar la dependencia '{missing_mod}' automáticamente. "
                                    f"Ejecuta manualmente: pip install {missing_mod}"
                                )
                        except Exception as e3:
                            tool_exc = e3
                    else:
                        tool_exc = e
                except Exception as e:
                    tool_exc = e

                # AUTO-HEALING: si la tool falló, intentar con código de healing
                if tool_exc is not None and ErrorLearningSystem is not None:
                    try:
                        healing_code = ErrorLearningSystem.get_healing_suggestions(str(tool_exc))
                        if healing_code and "Auto-healing" in healing_code:
                            _set_phase("healing", f"Auto-reparando: {str(tool_exc)[:60]}",
                                      error_message=str(tool_exc))
                            if TERMINAL_AVAILABLE and term:
                                term.info(f"Auto-healing para {action}...")
                            # Intentar ejecutar healing code
                            try:
                                exec(healing_code.replace("[RUTA_AQUI]", 
                                    next((v for v in args.values() if isinstance(v, str) and 
                                          ("\\" in v or "/" in v)), ".")))
                                # Retry the tool once
                                tool_result = self.tools[action](**args)
                                tool_exc = None  # healed
                                if TERMINAL_AVAILABLE and term:
                                    term.success(f"Auto-healing exitoso para {action}")
                            except Exception:
                                pass  # healing didn't work, keep original error
                    except Exception:
                        pass

                duration_ms = int((time.time() - t0) * 1000)

                if _AUDIT_AVAILABLE and get_audit is not None:
                    try:
                        _ws_name = "default"
                        if _WORKSPACE_AVAILABLE and get_workspace_manager is not None:
                            _ws_name = get_workspace_manager().current_name
                        get_audit().log(
                            action=action,
                            args=args,
                            result=tool_result if tool_exc is None else str(tool_exc),
                            ok=tool_exc is None,
                            duration_ms=duration_ms,
                            workspace=_ws_name,
                        )
                    except Exception:
                        pass

                # 4.5: Procesar resultado y comunicar
                if tool_exc is not None:
                    result_msg = f"Error ejecutando {action}: {tool_exc}"
                    ok = False
                    summary = f"exception: {str(tool_exc)[:60]}"
                    # Claude Code style prints errors immediately via the callback, so we keep this set_phase
                    _set_phase("error", f"{action} falló: {str(tool_exc)[:60]}",
                              error_message=str(tool_exc), tool_result_summary=summary, tool_result_ok=False)
                    # Eliminamos la impresion doble de tool_result_error aqui
                    # if TERMINAL_AVAILABLE and term:
                    #    term.tool_result(action, ok=False, summary=summary)
                    # Registrar para aprendizaje
                    if ErrorLearningSystem is not None:
                        try:
                            ErrorLearningSystem.log_error(action, args, str(tool_exc), context=user_input[:200])
                        except Exception:
                            pass
                else:
                    result_msg = f"Herramienta {action} ejecutada en {duration_ms}ms. Resultado: {tool_result}"

                    # read_file vacío → guiar al LLM a usar execute_cmd como fallback
                    if action in ("read_file", "read_text_file", "get_file") and not str(tool_result or "").strip():
                        _fp = args.get("file_path", args.get("path", args.get("filename", "")))
                        result_msg += (
                            f"\nNOTA SISTEMA: read_file devolvió vacío para '{_fp}'. "
                            f"El archivo existe pero la herramienta no pudo leerlo. "
                            f"Usa INMEDIATAMENTE: execute_cmd(command='type \"{_fp}\"') para leerlo en Windows."
                        )
                    # list_directory vacío → fallback con execute_cmd dir
                    elif action in ("list_directory", "list_files", "list_dir") and not tool_result:
                        _dp = args.get("directory", args.get("path", "."))
                        result_msg += (
                            f"\nNOTA SISTEMA: list_directory devolvió vacío para '{_dp}'. "
                            f"Usa: execute_cmd(command='dir \"{_dp}\"') como fallback."
                        )

                    if isinstance(tool_result, dict):
                        ok = bool(tool_result.get("ok", True)) and not tool_result.get("error")
                        if tool_result.get("error") and ErrorLearningSystem is not None:
                            try:
                                ErrorLearningSystem.log_error(action, args, str(tool_result["error"]), context=user_input[:200])
                            except Exception:
                                pass
                    elif isinstance(tool_result, str):
                        # Convención usada por ~190 tools del repo: strings de resultado
                        # empiezan con "❌"/"⚠️" en fallo y "✅" en éxito. Antes CUALQUIER
                        # string se marcaba ok=True sin mirar su contenido, lo que dejaba
                        # que el LLM narrara "éxito" sobre errores reales (ej. Blender con
                        # output_path vacío devolviendo "❌ Error..." se mostraba con ✓ y el
                        # modelo inventaba detalles de un video que nunca se creó).
                        _stripped = tool_result.strip()
                        ok = not (_stripped.startswith("❌") or _stripped.startswith("⚠️") or _stripped.lower().startswith("error"))
                        if not ok and ErrorLearningSystem is not None:
                            try:
                                ErrorLearningSystem.log_error(action, args, _stripped[:300], context=user_input[:200])
                            except Exception:
                                pass
                    else:
                        ok = True
                    summary = _summarize_result(tool_result)
                    _set_phase("tool_executed",
                              f"{action} completado en {duration_ms}ms: {summary}",
                              step=idx, total=len(tool_calls),
                              tool_name=action, duration_ms=duration_ms,
                              tool_result_summary=summary, tool_result_ok=ok)
                    # Eliminamos la impresion doble de tool_result aqui ya que progress_cb lo maneja y la UI lo muestra
                    # if TERMINAL_AVAILABLE and term:
                    #     term.tool_result(action, ok=ok, summary=f"{summary} ({duration_ms}ms)")

                all_results_msg += result_msg + "\n"

                # Rastreo de errores consecutivos → detectar confusión
                if tool_exc is not None:
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        all_results_msg += (
                            f"\n[SISTEMA CRITICO] {consecutive_errors} errores consecutivos detectados. "
                            f"CAMBIA COMPLETAMENTE de estrategia. "
                            f"Opciones: (1) usa 'execute_cmd' con comandos directos, "
                            f"(2) intenta una ruta alternativa, "
                            f"(3) resume lo que ya lograste y explícalo al usuario.\n"
                        )
                else:
                    consecutive_errors = 0

                # Actualizar progreso del plan
                if get_agent_status().get("plan"):
                    get_agent_status()["plan"]["completed"] = idx
                    if get_agent_status()["flow_phases"] and idx <= len(get_agent_status()["flow_phases"]):
                        current_flow_id = get_agent_status()["flow_phases"][idx - 1]["id"]
                        if TERMINAL_AVAILABLE and term and idx < len(tool_calls):
                            try:
                                next_id = get_agent_status()["flow_phases"][idx]["id"] if idx < len(get_agent_status()["flow_phases"]) else ""
                                term.render_flow_schema(get_agent_status()["flow_phases"],
                                                        current_phase=next_id,
                                                        title=f"Plan paso {idx+1}/{len(tool_calls)}")
                            except Exception:
                                pass

            # ---- FASE 5: FEEDBACK AL MODELO ----
            if loop_detected:
                all_results_msg += "\nâš ï¸ SISTEMA: Hubo un bucle. Cambia de estrategia o finaliza con lo que tengas."
            if all_results_msg.strip():
                all_results_msg += (
                    "\n\n[INSTRUCCION CRITICA] Tu PROXIMA respuesta DEBE ser texto en espanol "
                    "explicando que hiciste y el resultado. "
                    "NO ejecutes mas herramientas si la tarea ya esta completa. "
                    "Si falta algo, ejecuta UNA sola herramienta mas. "
                    "BASATE UNICAMENTE en el 'Resultado:' real de cada herramienta de arriba — "
                    "NUNCA inventes detalles (nombres de escenas, personajes, archivos, rutas) que no "
                    "esten literalmente en ese resultado. Si una herramienta devolvio '❌' o un error, "
                    "DEBES decirle al usuario que fallo y por que, NO describas un exito que no ocurrio."
                )
                self.history.append({"role": "user", "content": all_results_msg})
            else:
                final_answer = ai_message
                break
        else:
            # Safety net: limite de iteraciones
            if TERMINAL_AVAILABLE and term:
                term.warn(f"Limite de {max_iterations} iteraciones alcanzado.")
            # Si la ultima respuesta del modelo es JSON de herramientas, no la retornamos
            # como respuesta final — dejamos que el auto-resumen tome el control.
            _last_is_json = bool(ai_message and self._parse_tool_calls(ai_message))
            final_answer = ai_message if (ai_message and not _last_is_json) else ""

        # ---- Auto-resumen cuando LLM no dio respuesta final ----
        if not final_answer.strip() and tools_used_in_task:
            _n = len(tools_used_in_task)
            _tool_names = ", ".join(t["tool"] for t in tools_used_in_task[:6])
            final_answer = (
                f"Completado. {_n} accion{'es' if _n > 1 else ''}: {_tool_names}."
                + (f" (y {_n - 6} mas)" if _n > 6 else "")
            )
            _set_phase("responding", final_answer)
            if progress_callback:
                try:
                    progress_callback("responding", final_answer)
                except Exception:
                    pass

        # ---- FASE 6: CIERRE + AUTO-LEARNING ----

        # AUTO-SKILL-SAVE: tarea compleja (3+ tools) y exitosa → guardar habilidad
        if len(tools_used_in_task) >= 3 and final_answer and len(final_answer) > 40:
            try:
                from core.auto_skill import AutoSkillCreator
                import re as _re_sk
                _asc = AutoSkillCreator(model=self.model_name)
                _skill_cat = _asc.detect_needed_skill(user_input)
                _slug = _skill_cat or _re_sk.sub(r'[^a-z0-9]+', '_', user_input[:28].lower()).strip('_')
                _steps_md = "\n".join(
                    f"{i+1}. `{t['tool']}`"
                    + (f" — {list(t['args'].values())[0]}" if t.get('args') else "")
                    for i, t in enumerate(tools_used_in_task[:20])
                )
                _ok_skill = _asc.create_custom_skill(
                    name=_slug,
                    description=user_input[:100],
                    instructions=(
                        f"# Skill auto-generada\n\n"
                        f"## Tarea original\n{user_input[:300]}\n\n"
                        f"## Pasos ejecutados ({len(tools_used_in_task)} herramientas)\n{_steps_md}\n\n"
                        f"## Resultado\n{final_answer[:500]}\n"
                    ),
                )
                if _ok_skill and progress_callback:
                    try:
                        progress_callback("skill_saved", f"skill guardada: {_slug}", tool_name=_slug)
                    except Exception:
                        pass
                # Guardar resumen de tarea en memoria persistente
                try:
                    from core.memory import MemoryManager
                    _mm = MemoryManager()
                    _mm.save_task(
                        task=user_input[:200],
                        tools_count=len(tools_used_in_task),
                        skill_saved=_slug if _ok_skill else None,
                        result_preview=final_answer[:200],
                    )
                except Exception:
                    pass
            except Exception:
                pass

        _set_phase("idle", "Listo. Esperando tu siguiente solicitud.")
        get_agent_status()["is_active"] = False
        get_agent_status()["step"] = 0
        get_agent_status()["total_steps"] = 0
        # No imprimir nada al final para mantenerlo silencioso al estilo Claude Code
        # if TERMINAL_AVAILABLE and term:
        #    term.success(f"Respuesta final lista ({len(final_answer)} caracteres).")

        # Store conversation in Aumformbring for pattern learning
        if aumformbring_system is not None:
            try:
                aumformbring_system.store_conversation(user_input, final_answer)
            except Exception:
                pass

        # Track skill usage from tools used in this conversation
        if aumformbring_system is not None and final_answer:
            try:
                tools_used = re.findall(r'(?:action|tool)["\']?\s*:\s*["\'](\w+)["\']', final_answer)
                for t in tools_used[:5]:
                    aumformbring_system.track_skill_usage(t, success=True)
            except Exception:
                pass

        # Periodic auto-learning cycle with status feedback
        self._conversation_count += 1
        cycle_interval = 5
        if AutoLearningOrchestrator is not None and self._conversation_count % cycle_interval == 0:
            _set_phase("learning", "Ejecutando ciclo de auto-aprendizaje...")
            if TERMINAL_AVAILABLE and term:
                try: term.info("Ciclo de auto-aprendizaje automatico en progreso...")
                except Exception: pass
            try:
                report = AutoLearningOrchestrator.run_full_cycle()
                if report.get("skills_forged", 0) > 0 or report.get("skills_promoted", 0) > 0:
                    if TERMINAL_AVAILABLE and term:
                        try: term.success(f"Auto-evolución: {report['skills_forged']} forjadas, {report['skills_promoted']} promovidas")
                        except Exception: pass
            except Exception:
                pass

        _set_phase("idle", "Listo. Esperando tu siguiente solicitud.")
        return final_answer

    def get_speed_report(self) -> str:
        """Retorna un reporte de las metricas de velocidad."""
        try:
            from core.speed import print_speed_report
            return print_speed_report()
        except Exception:
            return "No speed metrics available"
