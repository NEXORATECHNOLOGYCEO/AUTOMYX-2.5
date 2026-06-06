import json
import logging
import re
import sys
import requests
import subprocess
import os

# Estado global para el frontend
agent_status = {
    "is_active": False,
    "current_action": "Esperando...",
    "reasoning": ""
}

# Forzar codificación UTF-8 para evitar errores en Windows con emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from typing import List, Dict, Any, Callable
from openai import OpenAI
from colorama import Fore, Style
from core.hardware_detector import hw_config
from core.skills import SKILLS_REGISTRY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Agent")


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
        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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"
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

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    def _parse_tool_calls(self, response_text: str) -> list:
        tool_calls = []
        
        # 1. Intentar extraer de bloques de código markdown
        matches = re.finditer(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                tool_calls.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                pass
                
        if tool_calls:
            return tool_calls
            
        # 2. Si no hay markdown, buscar objetos JSON crudos en el texto
        # Buscamos estructuras que empiecen por { y terminen por }
        # Usamos un parser simple de balance de llaves para extraer múltiples JSONs
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

    def run(self, user_input: str, custom_system_prompt: str = None, agent_skills: dict = None) -> str:
        # --- FAST PATH (Para saludos o confirmaciones cortas no necesitamos gastar tiempo en el LLM pesado) ---
        fast_responses = {
            "hola": "¡Hola! Estoy listo. ¿En qué te ayudo?",
            "estas ahi": "Sí, aquí estoy. Dime.",
            "estas ahí": "Sí, aquí estoy. Dime.",
            "estas ahi?": "Siempre activo. ¿Qué necesitas?",
            "gracias": "¡De nada! Aquí sigo si me necesitas."
        }
        user_lower = user_input.strip().lower()
        if user_lower in fast_responses:
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": fast_responses[user_lower]})
            return fast_responses[user_lower]
        # -------------------------------------------------------------------------------------------------
        # Extraer herramientas disponibles en el prompt
        tools_text = self.system_prompt.split("Herramienta")[1] if "Herramienta" in self.system_prompt else ""
        
        # Filtrar herramientas basadas en habilidades (skills)
        if agent_skills:
            if not agent_skills.get("write", True):
                # Si no tiene permiso de escritura, bloquear herramientas de escritura/acción
                blocked_tools = ["write_file", "append_to_file", "create_directory", "delete_file", "ai_form_filler", "create_tiktok_edit", "add_dynamic_zoom", "open_app_by_uri", "control_pc"]
                for tool in blocked_tools:
                    # Una forma rústica de ocultar la herramienta del prompt es reemplazar su nombre
                    tools_text = tools_text.replace(f"Herramienta: {tool}", f"Herramienta Bloqueada (Sin Permiso): {tool}")
            
            if not agent_skills.get("pc", True):
                # Si no tiene permiso de PC, bloquear shell y control de UI
                blocked_tools = ["execute_shell", "open_app_by_uri", "control_pc", "press_hotkey", "type_text", "check_system_resources", "play_youtube_video", "play_tiktok_desktop_video", "generate_vyrex_video"]
                for tool in blocked_tools:
                    tools_text = tools_text.replace(f"Herramienta: {tool}", f"Herramienta Bloqueada (Sin Permiso): {tool}")

        # Si se provee un prompt personalizado (para agentes específicos), actualizamos el primer mensaje
        hw_context = f"\n[INFO DEL SISTEMA]\nOS: {self.hw.os_name} | Arch: {self.hw.arch} | UserDir: {self.hw.user_home}\nHardware: {self.hw.gpu_vendor} | Backend: {self.hw.acceleration_backend}"
        
        if custom_system_prompt:
            if self.history and self.history[0]["role"] == "system":
                full_custom_prompt = f"{custom_system_prompt}\n\n[REGLAS DEL SISTEMA Y HERRAMIENTAS]\nDebes usar JSON para las herramientas.{hw_context}\nHerramienta{tools_text}"
                self.history[0]["content"] = full_custom_prompt
        else:
            # Restaurar el prompt original si volvemos al principal
            if self.history and self.history[0]["role"] == "system":
                # Aplicamos el filtro de herramientas al prompt principal también si aplica
                self.history[0]["content"] = self.system_prompt.split("Herramienta")[0] + f"Herramienta{hw_context}" + tools_text

        self.history.append({"role": "user", "content": user_input})
        
        global agent_status
        agent_status["is_active"] = True
        agent_status["current_action"] = f"Analizando solicitud: {user_input[:30]}..."
        agent_status["reasoning"] = ""
        
        final_answer = ""
        recent_actions = [] # Memoria a corto plazo para evitar bucles
        
        while True:
            # Limitamos el historial para que no explote, pero mantenemos una buena memoria (ej. últimos 20 mensajes)
            if len(self.history) > 21:
                # Mantenemos el system prompt (index 0) y los últimos 20 mensajes
                self.history = [self.history[0]] + self.history[-20:]

            # Llamar a OpenAI (Nvidia) SIN streaming para máxima velocidad
            try:
                # Indicador visual rápido
                print(f"\n[LLM] Evaluando: {user_input[:50]}...")
                print(f"{Fore.CYAN}[*] Procesando...{Style.RESET_ALL}", end="\r")
                sys.stdout.flush()
                
                agent_status["current_action"] = "Procesando razonamiento en la red neuronal..."
                
                # Inferencia usando el modelo seleccionado en la UI (self.model_name)
                actual_model = ModelProvider.get_display_name(self.model_name)
                try:
                    completion = self.client.chat.completions.create(
                        model=actual_model,
                        messages=self.history,
                        temperature=0.7,
                        top_p=0.95,
                        max_tokens=4096,
                        stream=True  # ACTIVADO STREAMING PARA MAYOR VELOCIDAD DE RESPUESTA
                    )
                    
                    # Manejar el streaming y acumular la respuesta
                    ai_message = ""
                    reasoning_accumulated = ""
                    
                    print(f"\n{Fore.GREEN}[IA]: {Style.RESET_ALL}", end="")
                    
                    for chunk in completion:
                        if not getattr(chunk, "choices", None) or len(chunk.choices) == 0:
                            continue
                            
                        delta = chunk.choices[0].delta
                        
                        # Extraer razonamiento si el modelo lo soporta (ej. deepseek-r1)
                        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            reasoning_accumulated += delta.reasoning_content
                            agent_status["reasoning"] = reasoning_accumulated
                        
                        # Extraer contenido real
                        if getattr(delta, "content", None) is not None:
                            content_piece = delta.content
                            ai_message += content_piece
                            
                            # Imprimir en consola en tiempo real si no es un JSON oculto
                            if not ai_message.strip().startswith("{"):
                                print(content_piece, end="", flush=True)
                                
                    print() # Salto de línea al terminar
                    
                except Exception as api_err:
                    print(f"\n{Fore.RED}[!] Error con el modelo {self.model_name}, cayendo a fallback seguro... {str(api_err)}{Style.RESET_ALL}")
                    agent_status["current_action"] = "Error en red principal, usando fallback seguro..."
                    completion = self.client.chat.completions.create(
                        model="gpt-oss-120b", 
                        messages=self.history,
                        temperature=0.1,
                        max_tokens=4096,
                        stream=False
                    )
                    ai_message = completion.choices[0].message.content
                
                # Limpiar indicador visual
                sys.stdout.write("\033[K")
                sys.stdout.flush()
                
            except Exception as e:
                return f"Error conectando con OpenAI (Nvidia): {str(e)}."

            self.history.append({"role": "assistant", "content": ai_message})
            
            # Comprobar si quiere usar herramientas
            tool_calls = self._parse_tool_calls(ai_message)
            if tool_calls:
                all_results_msg = ""
                for tool_call in tool_calls:
                    if "action" in tool_call:
                        action = tool_call["action"]
                        args = tool_call.get("args", {})
                        
                        # Protección contra bucles repetitivos
                        action_signature = f"{action}_{str(args)}"
                        if recent_actions.count(action_signature) >= 2:
                            error_msg = f"SISTEMA: Has intentado ejecutar '{action}' con los mismos argumentos varias veces sin éxito. DETENTE y busca otra solución."
                            all_results_msg += error_msg + "\n"
                            print(f"{Fore.RED}[!] Bucle detectado. Forzando a la IA a cambiar de estrategia.{Style.RESET_ALL}")
                            continue
                        
                        recent_actions.append(action_signature)
                        if len(recent_actions) > 10:
                            recent_actions.pop(0)
                        
                        if action in self.tools:
                            agent_status["current_action"] = f"Ejecutando proceso autónomo: {action}..."
                            try:
                                tool_result = self.tools[action](**args)
                                result_msg = f"Herramienta {action} ejecutada. Resultado: {tool_result}"
                                print(f"{Fore.YELLOW}[OK] Ejecutó: {action}{Style.RESET_ALL}")
                            except Exception as e:
                                result_msg = f"Error ejecutando {action}: {str(e)}"
                                print(f"{Fore.RED}[ERROR] Error en {action}: {str(e)}{Style.RESET_ALL}")
                        else:
                            result_msg = f"Error: Herramienta {action} no existe."
                            
                        all_results_msg += result_msg + "\n"
                
                if all_results_msg:
                    all_results_msg += "\nSI HAS TERMINADO LA TAREA, EXPLICA LO QUE HICISTE. SI NO, EJECUTA LA SIGUIENTE HERRAMIENTA INMEDIATAMENTE."
                    self.history.append({"role": "system", "content": all_results_msg})
                    # Continuar el bucle infinito para que decida el siguiente paso
                else:
                    final_answer = ai_message
                    break
            else:
                # Si no hay llamada a herramienta, es la respuesta final y rompemos el bucle
                final_answer = ai_message
                break
                
        agent_status["is_active"] = False
        agent_status["current_action"] = "Esperando..."
        agent_status["reasoning"] = ""
        
        return final_answer
