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

# Estado global para el frontend - enriquecido con fases claras
agent_status = {
    "is_active": False,
    "phase": "idle",  # idle | analyzing | thinking | tool_executing | tool_executed | responding | error
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
    "plan": None,        # Plan nativo del modelo: {"steps": [...], "total": 0, "completed": 0}
    "flow_phases": [],   # Fases del flow-schema visual
}

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

# Sistemas de precisiÃ³n y auto-aprendizaje de errores
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

# NÃºcleo nuevo: parser JSON blindado y terminal Rich
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
    """Actualiza el estado global de forma atómica y notifica."""
    global agent_status
    with _state_lock:
        agent_status["phase"] = phase
        if action:
            agent_status["current_action"] = action
        agent_status["last_update"] = datetime.now().isoformat()
        for k, v in extras.items():
            agent_status[k] = v
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
        # Resumen genÃ©rico
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



class ModelProvider:
    """Clase para gestionar diferentes proveedores de modelos"""
    OLLAMA_LOCAL = "ollama_local"
    OLLAMA_CLOUD = "ollama_cloud"
    NVIDIA = "nvidia"
    OPENAI = "openai"
    
    @staticmethod
    def get_provider(model_name: str) -> str:
        """Determina el proveedor basado en el nombre del modelo"""
        model_lower = model_name.lower()
        
        if model_name.startswith("ollama/"):
            return ModelProvider.OLLAMA_LOCAL
        elif model_name.startswith("cloud/"):
            return ModelProvider.OLLAMA_CLOUD
        elif model_name.startswith("nvidia/") or model_name.startswith("openai/") or model_name.startswith("z-ai/") or model_name.startswith("minimaxai/") or "gpt-oss" in model_lower:
            return ModelProvider.NVIDIA
        elif "llama" in model_lower or "mistral" in model_lower:
            return ModelProvider.OLLAMA_LOCAL
        
        # Por defecto, usar NVIDIA
        return ModelProvider.NVIDIA
    
    @staticmethod
    def get_client(model_name: str, provider: str = None):
        """Obtiene el cliente adecuado para el proveedor"""
        if provider is None:
            provider = ModelProvider.get_provider(model_name)
        
        if provider == ModelProvider.OLLAMA_LOCAL:
            logger.info("Usando motor de inferencia local (Ollama)")
            return OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="local-ollama"
            )
        elif provider == ModelProvider.OLLAMA_CLOUD:
            logger.info("Usando Ollama Cloud")
            return OpenAI(
                base_url="https://ollama.com/v1",
                api_key=os.getenv("OLLAMA_API_KEY", "ollama-cloud-key")
            )
        elif provider == ModelProvider.NVIDIA:
            logger.info("Usando NVIDIA API")
            api_key = os.getenv("NVIDIA_API_KEY", "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")
            return OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key
            )
        elif provider == ModelProvider.OPENAI:
            logger.info("Usando OpenAI API")
            return OpenAI(
                api_key="your-openai-api-key"
            )
        
        # Fallback
        api_key = os.getenv("NVIDIA_API_KEY", "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")
        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
    
    @staticmethod
    def get_display_name(model_name: str) -> str:
        """Obtiene el nombre del modelo sin el prefijo del proveedor (excepto para NVIDIA/openai)"""
        if model_name.startswith("ollama/"):
            return model_name.replace("ollama/", "")
        if model_name.startswith("cloud/"):
            return model_name.replace("cloud/", "")
        # Para NVIDIA, openai, z-ai, y minimaxai DEJAMOS el prefijo (API de NVIDIA lo requiere)
        if model_name.startswith("nvidia/") or model_name.startswith("openai/") or model_name.startswith("z-ai/") or model_name.startswith("minimaxai/"):
            return model_name
        return model_name


class AutomyxAgent:
    def __init__(self, model_name: str = "nvidia/gpt-oss-120b", provider: str = None):
        self.model_name = model_name
        self.provider = provider or ModelProvider.get_provider(model_name)
        self.hw = hw_config
        
        logger.info(f"Iniciando AutomyxAgent en {self.hw.os_name} ({self.hw.arch})")
        logger.info(f"Hardware detectado: GPU={self.hw.gpu_vendor}, Backend={self.hw.acceleration_backend}")
        
        self.client = ModelProvider.get_client(model_name, self.provider)
        logger.info(f"Proveedor: {self.provider} | Modelo: {ModelProvider.get_display_name(model_name)}")
        
        # Cargar el Soul base desde Soul.md
        try:
            import os
            soul_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Soul.md")
            with open(soul_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except Exception as e:
            logger.warning(f"No se pudo cargar Soul.md, usando prompt por defecto. Error: {e}")
            self.system_prompt = "Eres Automyx. Debes usar JSON para las herramientas."
            
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.tools: Dict[str, Callable] = {}
        self._tool_requires: Dict[str, list] = {}
        self._conversation_count = 0

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
        try:
            _detected_plan = None
            # Buscar cualquier JSON que tenga plan_id y steps
            for _maybe_json in re.finditer(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL | re.IGNORECASE):
                try:
                    _parsed = json.loads(_maybe_json.group(1))
                    if isinstance(_parsed, dict) and "steps" in _parsed and isinstance(_parsed["steps"], list):
                        _detected_plan = _parsed
                        break
                except json.JSONDecodeError:
                    pass
            if not _detected_plan:
                # Buscar sin fences tambien
                _depth = 0
                _start = -1
                for _i, _c in enumerate(response_text):
                    if _c == '{':
                        if _depth == 0: _start = _i
                        _depth += 1
                    elif _c == '}':
                        _depth -= 1
                        if _depth == 0 and _start != -1:
                            try:
                                _p = json.loads(response_text[_start:_i+1])
                                if isinstance(_p, dict) and "steps" in _p and isinstance(_p["steps"], list):
                                    _detected_plan = _p
                                    break
                            except json.JSONDecodeError:
                                pass
                            _start = -1
            if _detected_plan:
                tool_calls_from_plan = []
                for _step in _detected_plan["steps"]:
                    tc = {
                        "action": _step.get("tool") or _step.get("action", ""),
                        "args": _step.get("args", {}),
                        "rationale": _step.get("rationale", ""),
                    }
                    if tc["action"]:
                        tool_calls_from_plan.append(tc)
                if tool_calls_from_plan:
                    logger.info(f"[plan] Plan JSON detectado con {len(tool_calls_from_plan)} pasos")
                    # Guardar el plan original completo
                    _detected_plan["_from_llm"] = True
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
                return [tc.to_dict() for tc in result.tool_calls]
            except Exception as e:
                logger.error(f"[json_protocol] error, fallback a parser legacy: {e}")

        # === CAPA 2: FALLBACK legacy ===
        tool_calls = []
        matches = re.finditer(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                tool_calls.append(json.loads(match.group(1)))
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
                    if '"action"' in json_str:
                        try:
                            tool_calls.append(json.loads(json_str))
                        except json.JSONDecodeError:
                            pass
                    start_idx = -1
        return tool_calls

    def _validate_tool_call(self, action: str, args: Dict[str, Any]) -> Optional[str]:
        """
        Valida un tool call antes de ejecutarlo. Retorna mensaje de error o None si OK.
        """
        if not action or not isinstance(action, str):
            return f"AcciÃ³n invÃ¡lida (tipo {type(action).__name__})"
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
        # Mostrar siempre un resumen claro
        term.info(f"Solicitud recibida: \"{user_input[:120]}{'...' if len(user_input) > 120 else ''}\"")

        # 1) Intentar con el motor de intents v2.5 (slang, typos, frases coloquiales)
        intent_summary = None
        try:
            from core.intent_engine import understand
            understanding = understand(user_input)
            if understanding["intent"] != "unknown" and understanding["intent_confidence"] > 0.0:
                verb = understanding["intent"].replace("_", " ")
                conf = understanding["intent_confidence"]
                intent_summary = f"Interpretado como: {verb} (confianza {conf:.0%})"
                if understanding.get("entities", {}).get("folders"):
                    intent_summary += f" → {', '.join(understanding['entities']['folders'])}"
                if understanding.get("entities", {}).get("apps"):
                    intent_summary += f" → apps: {', '.join(understanding['entities']['apps'][:3])}"
        except Exception:
            understanding = None

        # 2) Intent summary from understanding (no TaskCoordinator needed)
        if not intent_summary and understanding:
            verb = understanding.get("intent", "procesar").replace("_", " ")
            entities = understanding.get("entities", {})
            intent_summary = f"🎯 {verb.capitalize()}"
            if entities.get("folders"):
                intent_summary += f" en {entities['folders'][0]}"
            if entities.get("apps"):
                intent_summary += f" → {entities['apps'][0]}"

        if intent_summary:
            term.info(intent_summary)

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

    def _execute_step(self, step: dict, step_num: int, total: int,
                       plan: dict, progress_callback=None) -> dict:
        """Ejecuta un paso individual del plan. Usado por workers paralelos."""
        tool_name = step.get("tool")
        args = step.get("args", {})
        rationale = step.get("rationale", "")

        step_msg = f"[Paso {step_num}/{total}] {rationale or tool_name}"
        _set_phase("tool_executing", step_msg, tool_name=tool_name)
        if progress_callback:
            try: progress_callback("tool_executing", step_msg, step=step_num, tool_name=tool_name)
            except Exception: pass

        resolved_args = self._resolve_step_args(args, plan)

        t0 = time.time()
        try:
            result = self.tools[tool_name](**resolved_args)
            duration = int((time.time() - t0) * 1000)
            if progress_callback:
                try: progress_callback("tool_executed", f"Paso {step_num} OK ({duration}ms)",
                                        step=step_num, tool_name=tool_name)
                except Exception: pass
            return {"step": step_num, "tool": tool_name, "ok": True, "result": result, "duration_ms": duration}
        except Exception as e:
            duration = int((time.time() - t0) * 1000)
            err = f"Error en paso {step_num} ({tool_name}): {e}"
            if progress_callback:
                try: progress_callback("error", err, step=step_num, tool_name=tool_name)
                except Exception: pass
            return {"step": step_num, "tool": tool_name, "ok": False, "error": str(e), "duration_ms": duration}

    def _execute_plan_parallel(self, plan: dict, progress_callback=None) -> Optional[str]:
        """Ejecuta un plan con paralelizacion inteligente de pasos independientes."""
        if not plan or not plan.get("steps"):
            return None

        steps = plan["steps"]
        total = len(steps)

        # 1. Analizar grupos de paralelizacion
        groups = self._analyze_parallel_groups(steps)

        if TERMINAL_AVAILABLE and term:
            n_parallel = sum(1 for g in groups if g["parallel"])
            plan_id = plan.get("plan_id", "plan")
            term.info(f"Plan {plan_id}: {total} pasos en {len(groups)} grupo(s) ({n_parallel} paralelos)")
            try:
                term.render_parallel_groups(groups, title=f"Plan {plan_id}")
            except Exception:
                pass

        results = []
        global_step_counter = [0]

        # 2. Ejecutar grupos secuencialmente, pasos dentro de grupo en paralelo
        for g_idx, group in enumerate(groups):
            g_steps = group["steps"]
            is_parallel = group["parallel"]

            group_label = f"Grupo {g_idx+1}/{len(groups)}"
            if is_parallel:
                if TERMINAL_AVAILABLE and term:
                    term.info(f"{group_label}: {len(g_steps)} pasos en PARALELO ⚡")
            else:
                pass  # secuencial, se muestra normal

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
                summary += "\n"

        if missing:
            summary += f"\nArchivos no generados: {', '.join(missing)}"

        if TERMINAL_AVAILABLE and term:
            if n_fail == 0:
                term.success(summary)
            else:
                term.warn(summary)

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

        # --- FAST PATH (saludos / confirmaciones cortas, sin gastar LLM) ---
        fast_responses = {
            "hola": "¡Hola! Estoy listo. ¿En qué te ayudo?",
            "estas ahi": "Sí, aquí estoy. Dime.",
            "estas ahí": "Sí, aquí estoy. Dime.",
            "estas ahi?": "Siempre activo. ¿Qué necesitas?",
            "gracias": "¡De nada! Aquí sigo si me necesitas.",
        }
        user_lower = user_input.strip().lower()
        if user_lower in fast_responses:
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": fast_responses[user_lower]})
            _set_phase("idle", "Esperando tu solicitud...")
            return fast_responses[user_lower]

        # --- INTENT-BASED FAST PATH (greetings, help, thanks, farewell, setup) ---
        # These intents are conversational — NEVER call tools. The previous
        # behavior of passing them to the LLM caused hallucinated tool calls
        # like "ey mano" → open_program.
        try:
            from core.intent_engine import understand as _understand, extract_integration_target
            _u = _understand(user_input)
            _intent = _u.get("intent", "unknown")
            if _intent in ("greeting", "thanks", "farewell"):
                _responses = {
                    "greeting": "¡Hola! Soy Automyx, tu agente de IA. ¿En qué te ayudo?",
                    "thanks":   "¡De nada! Aquí sigo para lo que necesites.",
                    "farewell": "¡Hasta luego! Si necesitas algo más, solo escríbeme.",
                }
                _resp = _responses[_intent]
                self.history.append({"role": "user", "content": user_input})
                self.history.append({"role": "assistant", "content": _resp})
                _set_phase("idle", "Conversación casual")
                return _resp
            if _intent == "help":
                _resp = (
                    "Puedo hacer mucho por ti:\n\n"
                    "🗣️  Conversar en lenguaje natural (con slang y typos)\n"
                    "🛠️  Ejecutar herramientas (archivos, código, web, PC, multimedia)\n"
                    "🧠  Analizar imágenes que me envíes\n"
                    "📚  Configurar integraciones (Notion, GitHub, Telegram, etc.)\n"
                    "⚡  Correr 6 tareas en paralelo\n"
                    "🔌  Conectar canales: Telegram, Discord, Instagram, Web\n\n"
                    "Dime qué necesitas o di 'configurar notion' para empezar."
                )
                self.history.append({"role": "user", "content": user_input})
                self.history.append({"role": "assistant", "content": _resp})
                _set_phase("idle", "Ayuda mostrada")
                return _resp
            if _intent == "setup_integration":
                # Detect which integration the user wants
                target = extract_integration_target(user_input)
                if target:
                    return self._guided_setup(target, _u)
                else:
                    _resp = (
                        "Puedo ayudarte a configurar estas integraciones:\n\n"
                        "📚 Notion\n🐙 GitHub\n✈️ Telegram\n💬 Discord\n📷 Instagram\n"
                        "🗣️ ElevenLabs\n🅞 OpenAI\n🅐 Anthropic\n🔍 Tavily\n\n"
                        "Di, por ejemplo: **configurar notion** o **conectar github**."
                    )
                    self.history.append({"role": "user", "content": user_input})
                    self.history.append({"role": "assistant", "content": _resp})
                    _set_phase("idle", "Menú de integraciones")
                    return _resp
        except Exception as _e:
            # If intent detection fails, fall through to LLM (better than crashing)
            pass

        # ---- FASE 1: ANALYZING (comprender quÃ© pidiÃ³ el usuario) ----
        global agent_status
        agent_status["is_active"] = True
        agent_status["user_request"] = user_input
        agent_status["started_at"] = datetime.now().isoformat()
        agent_status["step"] = 0
        agent_status["total_steps"] = 0
        agent_status["error_message"] = ""
        agent_status["tool_name"] = ""
        agent_status["tool_args_summary"] = ""
        agent_status["tool_result_summary"] = ""
        agent_status["tool_result_ok"] = None
        agent_status["plan"] = None
        agent_status["flow_phases"] = []
        _set_phase("analyzing", f"Analizando tu solicitud: \"{user_input[:60]}{'...' if len(user_input) > 60 else ''}\"")
        if progress_callback:
            try: progress_callback("analyzing", f"Analizando: {user_input[:60]}")
            except Exception: pass
        self._communicate_user_request(user_input)

        # Pre-procesar con intent engine v2.5: normaliza y resuelve tool concreta
        _intent_tool_hint = None
        try:
            from core.intent_engine import understand, resolve_tool_alias, TOOL_ALIASES
            understanding = understand(user_input)
            if understanding["intent"] != "unknown":
                intent_name = understanding["intent"]
                # Intentar resolver el intent a una tool concreta
                resolved_tool = resolve_tool_alias(intent_name)
                tool_hint = ""
                if resolved_tool != intent_name:
                    _intent_tool_hint = resolved_tool
                    tool_hint = f"\nLa herramienta correcta para '{intent_name}' es: '{resolved_tool}'. USA ESTA."
                elif intent_name in TOOL_ALIASES:
                    tool_hint = f"\nLa herramienta correcta para '{intent_name}' es: '{TOOL_ALIASES[intent_name]}'. USA ESTA."
                entities = understanding.get('entities', {})
                intent_block = (
                    f"\n[INTENT ENGINE v2.5]\n"
                    f"Detecte que quieres: {intent_name} "
                    f"(confianza {understanding['intent_confidence']:.0%})\n"
                    f"Texto normalizado: \"{understanding['normalized']}\"\n"
                    f"Palabra clave: \"{understanding.get('matched_keyword', '')}\"\n"
                    f"Entidades: {entities}\n"
                    f"INSTRUCCION: Usa este intent para decidir la PRIMERA herramienta.{tool_hint}"
                    f" Si el intent es claro, ejecuta directamente sin pedir aclaracion."
                )
                self.history.append({"role": "system", "content": intent_block})
        except Exception:
            pass

        # Construir el system prompt con filtros de permisos
        # Buscar la seccion de herramientas (puede ser "Herramientas:" o "Herramienta:")
        import re as _re_tool
        _tool_section_match = _re_tool.search(r'(Herramientas?:?\s*[\s\S]*)', self.system_prompt)
        tools_text = _tool_section_match.group(1) if _tool_section_match else ""
        if agent_skills:
            if not agent_skills.get("write", True):
                blocked_tools = ["write_file", "append_to_file", "create_directory", "delete_file",
                                 "ai_form_filler", "create_tiktok_edit", "add_dynamic_zoom",
                                 "open_app_by_uri", "control_pc"]
                for tool in blocked_tools:
                    tools_text = tools_text.replace(f"Herramienta: {tool}", f"Herramienta Bloqueada (Sin Permiso): {tool}")
            if not agent_skills.get("pc", True):
                blocked_tools = ["execute_shell", "open_app_by_uri", "control_pc", "press_hotkey",
                                 "type_text", "check_system_resources", "play_youtube_video",
                                 "play_tiktok_desktop_video", "generate_vyrex_video"]
                for tool in blocked_tools:
                    tools_text = tools_text.replace(f"Herramienta: {tool}", f"Herramienta Bloqueada (Sin Permiso): {tool}")

        hw_context = f"\n[INFO DEL SISTEMA]\nOS: {self.hw.os_name} | Arch: {self.hw.arch} | UserDir: {self.hw.user_home}\nHardware: {self.hw.gpu_vendor} | Backend: {self.hw.acceleration_backend}"

        if custom_system_prompt:
            if self.history and self.history[0]["role"] == "system":
                full_custom_prompt = f"{custom_system_prompt}\n\n[REGLAS DEL SISTEMA Y HERRAMIENTAS]\nDebes usar JSON para las herramientas.{hw_context}\nHerramienta{tools_text}"
                self.history[0]["content"] = full_custom_prompt
        else:
            if self.history and self.history[0]["role"] == "system":
                self.history[0]["content"] = self.system_prompt.split("Herramienta")[0] + f"Herramienta{hw_context}" + tools_text

        self.history.append({"role": "user", "content": user_input})

        # Inyectar lecciones aprendidas de errores previos (no alucinar)
        if ErrorLearningSystem is not None:
            try:
                warnings = ErrorLearningSystem.get_warnings_for_request(user_input)
                if warnings:
                    self.history.append({"role": "system", "content": warnings})
            except Exception:
                pass

        # Plan autogenerado (model-native) solo para tareas MULTI-PASO claras
        _needs_plan = any(kw in user_input.lower() for kw in
                          ["primer paso", "luego", "despues", "finalmente",
                           "paso a paso", "secuencia", "varios pasos",
                           "multiples pasos"])
        if _needs_plan:
            plan_prompt = (
                f"\n[GENERA PLAN ESTRUCTURADO - MULTI-STEP - PARALELO]\n"
                f"La tarea '{user_input[:80]}...' requiere multiples pasos.\n"
                f"Genera PRIMERO un plan JSON con este esquema:\n"
                f'{{"plan_id": "ts_XXXX", "steps": ['
                f'{{"n": 1, "tool": "tool_name", "args": {{...}}, "rationale": "por que"}}, '
                f'{{"n": 2, "tool": "...", "args": {{...}}, "rationale": "..."}}'
                f'], "parallel_groups": [[1, 3], [2, 4]], "verification": [{{"check": "output_file_exists", "path": "..."}}]'
                f"}}\n"
                f"IMPORTANTE: Si hay pasos SIN dependencia entre si, agrupalos en parallel_groups "
                f"(ej: pasos 1 y 3 pueden correr en paralelo). "
                f"Los pasos QUE ESCRIBEN archivos o abren programas NO pueden ir en paralelo."
                f"LUEGO ejecuta los pasos. Usa SOLO herramientas disponibles."
            )
            self.history.append({"role": "system", "content": plan_prompt})
            if TERMINAL_AVAILABLE and term:
                term.info("Generando plan nativo multi-paso...")
        elif TaskCoordinator is not None:
            try:
                intent = TaskCoordinator.parse_intent(user_input)
                if intent.get("action") in ("reeditar", "editar", "convertir", "organizar", "buscar", "crear") and intent.get("folder_hint"):
                    plan_prompt = (
                        f"\n[GENERA PLAN JSON ESTRUCTURADO]\n"
                        f"Tu tarea: {user_input}\n"
                        f"Genera SOLO un JSON vÃ¡lido con este esquema:\n"
                        f'{{"plan_id": "timestamp", "steps": ['
                        f'{{"n": 1, "tool": "nombre_herramienta", "args": {{...}}, "rationale": "por quÃ©"}}, '
                        f'{{"n": 2, "tool": "...", "args": {{...}}, "rationale": "..."}}'
                        f']}}'
                        f"\nUsa SOLO tools disponibles. Si necesitas crear carpeta + juego, usa create_directory + write_file."
                    )
                    self.history.append({"role": "system", "content": plan_prompt})
                    if TERMINAL_AVAILABLE and term:
                        term.info("Generando plan nativo del modelo...")
            except Exception:
                pass

        final_answer = ""
        recent_actions: List[str] = []  # anti-loop

        # ---- BUCLE PRINCIPAL ----
        max_iterations = 15  # safety net
        for iteration in range(max_iterations):
            agent_status["step"] = iteration + 1

            # Truncar historial para no explotar
            if len(self.history) > 21:
                self.history = [self.history[0]] + self.history[-20:]

            # ---- FASE 2: THINKING (llamar al LLM) ----
            _set_phase("thinking", f"Pensando cÃ³mo responder (paso {iteration+1})...")
            if TERMINAL_AVAILABLE and term:
                term.llm_thinking()

            ai_message = ""
            reasoning_accumulated = ""
            actual_model = ModelProvider.get_display_name(self.model_name)
            api_error: Optional[str] = None

            try:
                completion = self.client.chat.completions.create(
                    model=actual_model,
                    messages=self.history,
                    temperature=0.7,
                    top_p=0.95,
                    max_tokens=4096,
                    stream=True,
                )
                if TERMINAL_AVAILABLE and term:
                    term.llm_response_stream("")  # marca inicio de stream
                for chunk in completion:
                    if not getattr(chunk, "choices", None) or len(chunk.choices) == 0:
                        continue
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        reasoning_accumulated += delta.reasoning_content
                        agent_status["reasoning"] = reasoning_accumulated
                    if getattr(delta, "content", None) is not None:
                        ai_message += delta.content
                if TERMINAL_AVAILABLE and term:
                    term.llm_response_done()
            except Exception as api_err:
                # Fallback: modelo seguro
                _set_phase("error", f"Error con {self.model_name}, usando fallback...")
                if TERMINAL_AVAILABLE and term:
                    term.warn(f"Error con modelo principal: {api_err}. Probando fallback.")
                api_error = str(api_err)
                try:
                    completion = self.client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=self.history,
                        temperature=0.1,
                        max_tokens=4096,
                        stream=False,
                    )
                    ai_message = completion.choices[0].message.content
                except Exception as e2:
                    msg = f"Error conectando con OpenAI (Nvidia): {e2}"
                    _set_phase("error", msg, error_message=msg)
                    if TERMINAL_AVAILABLE and term:
                        term.error(msg)
                    agent_status["is_active"] = False
                    return msg

            self.history.append({"role": "assistant", "content": ai_message})

            # ---- FASE 3: PARSE TOOL CALLS ----
            tool_calls = self._parse_tool_calls(ai_message)
            if not tool_calls:
                # No hay tool calls → respuesta final
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
                agent_status["plan"] = {"steps": plan_steps, "total": len(plan_steps), "completed": 0}
                if TERMINAL_AVAILABLE and term:
                    try:
                        groups = self._analyze_parallel_groups(plan_steps)
                        n_parallel = sum(1 for g in groups if g["parallel"])
                        term.info(f"Plan de {len(plan_steps)} pasos ({n_parallel} en paralelo)")
                        term.render_plan(plan_steps, title=f"Plan paralelo: {user_input[:40]}...")
                    except Exception:
                        pass
                if progress_callback:
                    try: progress_callback("plan_created", f"Plan de {len(plan_steps)} pasos en paralelo", plan=plan_steps)
                    except Exception: pass
                _plan_obj = {"plan_id": f"plan_{int(time.time())}", "steps": plan_steps}
                _plan_result = self._execute_plan_parallel(_plan_obj, progress_callback=progress_callback)
                if _plan_result:
                    all_results_msg = _plan_result
                else:
                    all_results_msg = "Error ejecutando plan en paralelo."
            else:
                agent_status["plan"] = None
                agent_status["flow_phases"] = []

            # ---- FASE 4: EJECUTAR TOOL CALL UNICO (cuando no hay plan multi-paso) ----
            _set_phase("tool_executing", f"Ejecutando {len(tool_calls)} herramienta(s)...")
            all_results_msg = ""
            loop_detected = False

            for idx, tool_call in enumerate(tool_calls, 1):
                if "action" not in tool_call:
                    msg = f"[Tool {idx}] No se encontrÃ³ 'action' en tool_call. Ignorando."
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
                    _set_phase("error", f"ValidaciÃ³n fallÃ³: {validation_error[:80]}", error_message=validation_error)
                    if TERMINAL_AVAILABLE and term:
                        term.error(f"ValidaciÃ³n: {validation_error}")
                    all_results_msg += f"[Tool {idx}] {validation_error}\n"
                    continue

                # 4.2: DetecciÃ³n de loop (por acciÃ³n repetida o similar)
                _same_action_count = sum(1 for ra in recent_actions if ra.get("action") == action)
                if _same_action_count >= 3:
                    loop_detected = True
                    if TERMINAL_AVAILABLE and term:
                        term.tool_loop_warning(action, _same_action_count)
                    all_results_msg += (
                        f"SISTEMA: Detecte que intentaste '{action}' "
                        f"{_same_action_count} veces seguidas sin exito. "
                        f"CAMBIA DE ESTRATEGIA. Prueba otra herramienta o enfoque.\n"
                    )
                    continue
                recent_actions.append({"action": action, "args": args})
                if len(recent_actions) > 15:
                    recent_actions.pop(0)

                # 4.3: Comunicar QUÃ‰ voy a hacer
                args_summary = _truncate_args(args)
                agent_status["tool_name"] = action
                agent_status["tool_args_summary"] = args_summary
                _set_phase("tool_executing",
                          f"[{idx}/{len(tool_calls)}] Ejecutando {action}({args_summary})",
                          tool_name=action, tool_args_summary=args_summary)
                if TERMINAL_AVAILABLE and term:
                    term.tool_executing(action, args)

                # 4.4: Ejecutar la tool con medición de tiempo
                t0 = time.time()
                tool_result: Any = None
                tool_exc: Optional[BaseException] = None
                if progress_callback:
                    try: progress_callback("tool_executing", f"Ejecutando {action}", step=iteration+1, tool_name=action)
                    except Exception: pass
                try:
                    tool_result = self.tools[action](**args)
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
                duration_ms = int((time.time() - t0) * 1000)
                if progress_callback:
                    try: progress_callback("tool_executed", f"{action} listo en {duration_ms}ms", step=iteration+1, tool_name=action)
                    except Exception: pass

                # 4.5: Procesar resultado y comunicar
                if tool_exc is not None:
                    result_msg = f"Error ejecutando {action}: {tool_exc}"
                    ok = False
                    summary = f"exception: {str(tool_exc)[:60]}"
                    _set_phase("error", f"{action} fallÃ³: {str(tool_exc)[:60]}",
                              error_message=str(tool_exc), tool_result_summary=summary, tool_result_ok=False)
                    if TERMINAL_AVAILABLE and term:
                        term.tool_result(action, ok=False, summary=summary)
                    # Registrar para aprendizaje
                    if ErrorLearningSystem is not None:
                        try:
                            ErrorLearningSystem.log_error(action, args, str(tool_exc), context=user_input[:200])
                        except Exception:
                            pass
                else:
                    result_msg = f"Herramienta {action} ejecutada en {duration_ms}ms. Resultado: {tool_result}"
                    if isinstance(tool_result, dict):
                        ok = bool(tool_result.get("ok", True)) and not tool_result.get("error")
                        if tool_result.get("error") and ErrorLearningSystem is not None:
                            try:
                                ErrorLearningSystem.log_error(action, args, str(tool_result["error"]), context=user_input[:200])
                            except Exception:
                                pass
                    else:
                        ok = True
                    summary = _summarize_result(tool_result)
                    _set_phase("tool_executed",
                              f"{action} completado en {duration_ms}ms: {summary}",
                              tool_result_summary=summary, tool_result_ok=ok)
                    if TERMINAL_AVAILABLE and term:
                        term.tool_result(action, ok=ok, summary=f"{summary} ({duration_ms}ms)")

                all_results_msg += result_msg + "\n"

                # Actualizar progreso del plan
                if agent_status.get("plan"):
                    agent_status["plan"]["completed"] = idx
                    if agent_status["flow_phases"] and idx <= len(agent_status["flow_phases"]):
                        current_flow_id = agent_status["flow_phases"][idx - 1]["id"]
                        if TERMINAL_AVAILABLE and term and idx < len(tool_calls):
                            try:
                                next_id = agent_status["flow_phases"][idx]["id"] if idx < len(agent_status["flow_phases"]) else ""
                                term.render_flow_schema(agent_status["flow_phases"],
                                                        current_phase=next_id,
                                                        title=f"Plan paso {idx+1}/{len(tool_calls)}")
                            except Exception:
                                pass

            # ---- FASE 5: FEEDBACK AL MODELO ----
            if loop_detected:
                all_results_msg += "\nâš ï¸ SISTEMA: Hubo un bucle. Cambia de estrategia o finaliza con lo que tengas."
            if all_results_msg.strip():
                all_results_msg += "\n\nSIGUIENTE PASO: Si ya completaste la tarea, explica el resultado en espaÃ±ol sin JSON. Si aÃºn falta, ejecuta la siguiente herramienta."
                self.history.append({"role": "system", "content": all_results_msg})
            else:
                final_answer = ai_message
                break
        else:
            # Safety net: si alcanzamos max_iterations
            if TERMINAL_AVAILABLE and term:
                term.warn(f"Alcanzado lÃ­mite de {max_iterations} iteraciones. Cerrando con respuesta parcial.")
            final_answer = ai_message if ai_message else "He realizado varias acciones pero el bucle alcanzÃ³ el lÃ­mite. AquÃ­ estÃ¡ lo Ãºltimo que hice:\n" + all_results_msg

        # ---- FASE 6: CIERRE + AUTO-LEARNING ----
        _set_phase("idle", "Listo. Esperando tu siguiente solicitud.")
        agent_status["is_active"] = False
        agent_status["step"] = 0
        agent_status["total_steps"] = 0
        if TERMINAL_AVAILABLE and term:
            term.success(f"Respuesta final lista ({len(final_answer)} caracteres).")

        # Store conversation in Aumformbring for pattern learning
        if aumformbring_system is not None:
            try:
                aumformbring_system.store_conversation(user_input, final_answer)
            except Exception:
                pass

        # Periodic auto-learning cycle
        self._conversation_count += 1
        cycle_interval = 5
        if AutoLearningOrchestrator is not None and self._conversation_count % cycle_interval == 0:
            try:
                AutoLearningOrchestrator.run_full_cycle()
            except Exception:
                pass

        return final_answer
