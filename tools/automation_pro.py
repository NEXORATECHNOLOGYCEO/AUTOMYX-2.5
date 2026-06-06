import os
import json
import subprocess
import tempfile
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("AutomationPro")

class WorkflowManager:
    """
    Estilo OpenClaw: Orquestador de Workflows Profesionales.
    Ejecuta tareas secuenciales, paralelas y con condicionales.
    """
    @staticmethod
    def create_workflow(workflow_json: str, output_path: str) -> str:
        """
        Crea un workflow desde un JSON y lo ejecuta.
        workflow_json: JSON con la estructura del workflow (steps, parallel, etc)
        """
        try:
            from tools.pc_tools import PCTools
            output_path = PCTools._resolve_path(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            workflow_data = json.loads(workflow_json)
            
            # Guardar el workflow
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=4)
            
            # Ejecutar inmediatamente
            result = WorkflowManager.run_workflow(output_path)
            return f"✅ Workflow creado y ejecutado: {result}"
        except Exception as e:
            return f"❌ Error en create_workflow: {str(e)}"
    
    @staticmethod
    def run_workflow(workflow_path: str) -> str:
        """Ejecuta un workflow desde un archivo JSON"""
        try:
            from tools.pc_tools import PCTools
            workflow_path = PCTools._resolve_path(workflow_path)
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            log_content = []
            log_content.append(f"🚀 Iniciando Workflow: {workflow_data.get('name', 'Sin nombre')}")
            log_content.append(f"⏰ Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Ejecutar pasos
            if 'steps' in workflow_data:
                for i, step in enumerate(workflow_data['steps']):
                    log_content.append(f"\n🔹 Paso {i+1}: {step.get('name', 'Sin nombre')}")
                    if step.get('type') == 'command':
                        log_content.append(f"   Ejecutando comando: {step['command']}")
                        try:
                            result = subprocess.run(step['command'], shell=True, capture_output=True, text=True, timeout=300)
                            if result.returncode == 0:
                                log_content.append(f"   ✅ Éxito: {result.stdout[:200]}")
                            else:
                                log_content.append(f"   ❌ Error: {result.stderr[:200]}")
                        except Exception as e:
                            log_content.append(f"   ⚠️ Error: {str(e)}")
            
            log_content.append(f"\n✅ Workflow completado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Guardar log
            log_path = workflow_path.replace('.json', '_log.txt')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(log_content))
            
            return f"✅ Workflow ejecutado! Log: {log_path}"
        except Exception as e:
            return f"❌ Error en run_workflow: {str(e)}"


class ScriptEditorPro:
    """
    Estilo OpenClaw: Editor y Ejecutor de Scripts Multilenguaje.
    Soporta Python, PowerShell, Bash y JavaScript.
    """
    @staticmethod
    def create_and_run_script(script_content: str, language: str = "python", output_path: str = "") -> str:
        """
        Crea un script y lo ejecuta inmediatamente.
        language: python, powershell, bash, javascript
        """
        extensions = {
            "python": "py",
            "powershell": "ps1",
            "bash": "sh",
            "javascript": "js"
        }
        
        commands = {
            "python": ["python"],
            "powershell": ["powershell", "-ExecutionPolicy", "Bypass", "-File"],
            "bash": ["bash"],
            "javascript": ["node"]
        }
        
        try:
            ext = extensions.get(language.lower(), "py")
            
            if not output_path:
                fd, output_path = tempfile.mkstemp(suffix=f".{ext}")
                os.close(fd)
            else:
                from tools.pc_tools import PCTools
                output_path = PCTools._resolve_path(output_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            cmd = commands.get(language.lower(), ["python"]) + [output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"✅ Script ejecutado con éxito! Archivo: {output_path}\nSalida: {result.stdout[:500]}"
            else:
                return f"❌ Error en script: {result.stderr[:500]}"
        except Exception as e:
            return f"❌ Error en ScriptEditorPro: {str(e)}"


class AdvancedMemory:
    """
    Estilo Hermes Agent: Memoria Avanzada y Automejora.
    Guarda conversaciones, aprende de feedback y mejora automáticamente.
    """
    @staticmethod
    def log_conversation(user_input: str, agent_response: str, metadata: str = "") -> str:
        """
        Guarda una conversación en la memoria de Automyx.
        """
        try:
            log_dir = Path("automyx_memory") / "conversations"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"conv_{timestamp}.json"
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "user": user_input,
                "agent": agent_response,
                "metadata": metadata
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=4)
            
            return f"✅ Conversación guardada en memoria: {log_file}"
        except Exception as e:
            return f"❌ Error en log_conversation: {str(e)}"
    
    @staticmethod
    def recall_conversation(query: str = "", limit: int = 10) -> str:
        """
        Busca en la memoria de Automyx conversaciones anteriores.
        """
        try:
            log_dir = Path("automyx_memory") / "conversations"
            if not log_dir.exists():
                return "⚠️ No hay memoria disponible aún."
            
            logs = []
            for log_file in sorted(log_dir.glob("*.json"), reverse=True)[:limit]:
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logs.append(data)
            
            return f"✅ Memoria recuperada ({len(logs)} registros):\n" + json.dumps(logs, indent=2)
        except Exception as e:
            return f"❌ Error en recall_conversation: {str(e)}"


class APIIntegrationPro:
    """
    Estilo Hermes Agent: Integración con APIs REST externas.
    Permite GET, POST, PUT, DELETE con headers y datos.
    """
    @staticmethod
    def make_request(url: str, method: str = "GET", headers: str = "{}", data: str = "") -> str:
        """
        Hace una solicitud HTTP a una API externa.
        method: GET, POST, PUT, DELETE
        headers: JSON string con los headers
        data: JSON string con los datos para POST/PUT
        """
        try:
            import requests
            
            headers_dict = {}
            if headers:
                headers_dict = json.loads(headers)
            
            data_dict = {}
            if data:
                data_dict = json.loads(data)
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers_dict, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers_dict, json=data_dict, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers_dict, json=data_dict, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers_dict, timeout=30)
            else:
                return f"❌ Método HTTP no soportado: {method}"
            
            try:
                resp_content = response.json()
                formatted_resp = json.dumps(resp_content, indent=2)
            except Exception:
                formatted_resp = response.text
            
            return f"✅ Solicitud HTTP {method.upper()} a {url} completada! Código: {response.status_code}\nRespuesta:\n{formatted_resp[:1000]}"
        except Exception as e:
            return f"❌ Error en APIIntegrationPro: {str(e)}"


class ChainOfThought:
    """
    Estilo Hermes Agent: Razonamiento de Múltiples Pasos.
    Ayuda a Automyx a planificar grandes tareas.
    """
    @staticmethod
    def create_plan(goal: str, steps_list: str) -> str:
        """
        Crea un plan detallado para alcanzar una meta.
        steps_list: Lista de pasos en formato JSON string.
        """
        try:
            steps = json.loads(steps_list)
            
            plan_path = Path("automyx_memory") / "plans"
            plan_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plan_file = plan_path / f"plan_{timestamp}.json"
            
            plan_data = {
                "goal": goal,
                "steps": steps,
                "timestamp": datetime.now().isoformat(),
                "status": "pending"
            }
            
            with open(plan_file, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, indent=4)
            
            plan_text = f"📋 Plan de acción para: {goal}\n"
            plan_text += "-------------------------------------\n"
            for i, step in enumerate(steps, 1):
                plan_text += f"{i}. {step.get('description', 'Sin descripción')}\n"
            
            return plan_text + f"\n✅ Plan guardado: {plan_file}"
        except Exception as e:
            return f"❌ Error en create_plan: {str(e)}"

print("✅ Herramientas profesionales de OpenClaw/Hermes cargadas!")
