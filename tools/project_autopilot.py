
import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime


class ProjectAutopilot:
    """
    Motor de Autonomía Total para proyectos: analiza, mejora, escribe código,
    corrige errores y gestiona proyectos de forma completamente automática.
    """

    @staticmethod
    def analyze_project(project_path="."):
        """
        Analiza la estructura del proyecto y genera un informe completo.
        """
        project_path = Path(project_path)
        structure = []
        
        for root, dirs, files in os.walk(project_path):
            level = root.replace(str(project_path), '').count(os.sep)
            indent = ' ' * 2 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 2 * (level + 1)
            for file in files:
                structure.append(f"{sub_indent}{file}")
        
        return "\n".join(structure)

    @staticmethod
    def find_files_by_extension(extension, project_path="."):
        """
        Encuentra todos los archivos con una extensión específica.
        """
        project_path = Path(project_path)
        files = list(project_path.rglob(f"*.{extension}"))
        return [str(file.relative_to(project_path)) for file in files]

    @staticmethod
    def read_file(file_path, project_path="."):
        """
        Lee un archivo del proyecto.
        """
        full_path = Path(project_path) / file_path
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        return None

    @staticmethod
    def write_file(file_path, content, project_path="."):
        """
        Escribe contenido en un archivo del proyecto.
        """
        full_path = Path(project_path) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return f"Archivo {file_path} guardado exitosamente"

    @staticmethod
    def run_command(command, project_path=".", timeout=300):
        """
        Ejecuta un comando en el directorio del proyecto.
        """
        try:
            result = subprocess.run(
                command,
                cwd=str(Path(project_path)),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    @staticmethod
    def check_git_status(project_path="."):
        """
        Verifica el estado del repositorio Git del proyecto.
        """
        return ProjectAutopilot.run_command("git status", project_path)

    @staticmethod
    def git_add(file_path=".", project_path="."):
        """
        Añade archivos al staging area de Git.
        """
        return ProjectAutopilot.run_command(f"git add {file_path}", project_path)

    @staticmethod
    def git_commit(message, project_path="."):
        """
        Crea un commit en el repositorio Git.
        """
        return ProjectAutopilot.run_command(f'git commit -m "{message}"', project_path)

    @staticmethod
    def git_push(project_path="."):
        """
        Hace push al repositorio Git remoto.
        """
        return ProjectAutopilot.run_command("git push", project_path)

    @staticmethod
    def git_pull(project_path="."):
        """
        Hace pull desde el repositorio Git remoto.
        """
        return ProjectAutopilot.run_command("git pull", project_path)

    @staticmethod
    def detect_bugs(project_path="."):
        """
        Busca errores automáticamente en el proyecto.
        """
        project_path = Path(project_path)
        code_files = []
        for ext in ["py", "js", "ts", "java", "cpp", "c", "html", "css"]:
            code_files.extend(ProjectAutopilot.find_files_by_extension(ext, project_path))
        
        bug_report = []
        for file_path in code_files[:5]:  # Analizar primeros 5 archivos para empezar
            content = ProjectAutopilot.read_file(file_path, project_path)
            if content:
                bug_report.append({
                    "file": file_path,
                    "status": "analizado",
                    "content_preview": content[:200] + "..." if len(content) > 200 else content
                })
        
        return {
            "files_analyzed": len(bug_report),
            "files": bug_report,
            "message": "Archivos analizados. Usa un agente para generar análisis más detallado."
        }

    @staticmethod
    def fix_bugs(project_path="."):
        """
        Busca y corrige errores automáticamente (marcador).
        """
        return {
            "message": "Fix de bugs requiere integración con el agente principal",
            "project_path": str(project_path)
        }

    @staticmethod
    def generate_documentation(project_path="."):
        """
        Genera documentación automática para el proyecto.
        """
        structure = ProjectAutopilot.analyze_project(project_path)
        return {
            "structure": structure,
            "message": "Estructura del proyecto analizada. Usa un agente para generar README.md"
        }

    @staticmethod
    def auto_improve_project(project_path="."):
        """
        Analiza y mejora el proyecto automáticamente.
        """
        return {
            "project_path": str(project_path),
            "status": "Analizado",
            "message": "Auto-mejora requiere integración con el agente principal"
        }

    @staticmethod
    def full_autopilot_run(project_path="."):
        """
        Ejecuta el piloto automático completo: analiza, mejora, documenta.
        """
        return {
            "project_path": str(project_path),
            "status": "Completo",
            "message": "Autopilot ejecutado. Integración completa requiere agente principal"
        }


print("ProjectAutopilot inicializado: Motor de Autonomía Total para proyectos!")
