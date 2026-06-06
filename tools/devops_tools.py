import subprocess
import psutil
import platform
import os

class DevOpsTools:
    """
    Herramientas para que el Agente actúe como DevOps Engineer y Cloud Architect.
    """

    @staticmethod
    def check_system_resources() -> str:
        """
        Muestra un diagnóstico profundo del sistema (CPU, RAM, Disco).
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            report = f"🖥️ DIAGNÓSTICO DE SISTEMA ({platform.system()} {platform.release()})\n"
            report += f"--------------------------------------------------\n"
            report += f"⚙️ CPU: {cpu_percent}% uso (Núcleos lógicos: {psutil.cpu_count()})\n"
            report += f"🧠 RAM: {memory.percent}% uso ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)\n"
            report += f"💾 Disco Principal: {disk.percent}% uso ({disk.free // (1024**3)}GB libres de {disk.total // (1024**3)}GB)\n"
            
            if cpu_percent > 85 or memory.percent > 85:
                report += "\n⚠️ ALERTA: Recursos críticos. El sistema está bajo alta carga."
                
            return report
        except Exception as e:
            return f"❌ Error leyendo recursos del sistema: {str(e)}"

    @staticmethod
    def manage_docker_container(action: str, container_name: str = "") -> str:
        """
        Permite gestionar contenedores Docker locales.
        action: 'start', 'stop', 'restart', 'list'
        """
        try:
            # Comprobar si docker está instalado
            subprocess.run(["docker", "-v"], check=True, capture_output=True)
            
            if action == "list":
                result = subprocess.run(["docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"], 
                                      capture_output=True, text=True)
                return f"🐳 Contenedores Docker:\n{result.stdout}"
                
            if not container_name:
                return "❌ Se requiere el nombre del contenedor para esta acción."
                
            if action in ["start", "stop", "restart"]:
                result = subprocess.run(["docker", action, container_name], capture_output=True, text=True)
                if result.returncode == 0:
                    return f"✅ Docker: Acción '{action}' ejecutada con éxito en el contenedor '{container_name}'."
                else:
                    return f"❌ Error en Docker: {result.stderr}"
            else:
                return f"❌ Acción no soportada: {action}. Usa 'start', 'stop', 'restart' o 'list'."
                
        except FileNotFoundError:
            return "❌ Error: Docker no está instalado o no está en el PATH del sistema."
        except Exception as e:
            return f"❌ Error ejecutando comando Docker: {str(e)}"