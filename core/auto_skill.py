"""
AUTONOMY AUTO-SKILL CREATION
=============================
Automatically creates skills when the agent needs them.

When the agent encounters a task it doesn't have a skill for, this module:
1. Detects what's needed
2. Generates instructions using the LLM
3. Creates the skill file automatically
4. Makes it available for future use
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Common skills that AUTONOMY can auto-create
SKILL_TEMPLATES = {
    "web_development": {
        "name": "web_development",
        "description": "Crear páginas web profesionales con HTML, CSS, JavaScript",
        "instructions": """# Skill: Web Development

## Cuándo usar
Cuando el usuario pide crear una página web, sitio web, landing page, dashboard web, o cualquier interfaz web.

## Herramientas a usar
1. `create_directory` - Crear carpeta del proyecto
2. `write_file` - Escribir archivos HTML, CSS, JS
3. `open_website` - Abrir en el navegador
4. `create_web_preview` - Vista previa en vivo

## Pasos
1. Analizar los requisitos
2. Crear la estructura de carpetas
3. Escribir HTML semántico
4. Escribir CSS moderno y responsivo
5. Escribir JavaScript interactivo
6. Probar y abrir en navegador

## Mejores prácticas
- Usar HTML5 semántico
- CSS Grid y Flexbox para layouts
- JavaScript vanilla o frameworks modernos
- Diseño responsivo mobile-first
- Accesibilidad (ARIA)
"""
    },
    "video_editing": {
        "name": "video_editing",
        "description": "Editar videos profesionales con FFmpeg",
        "instructions": """# Skill: Video Editing

## Cuándo usar
Cuando el usuario pide editar, cortar, unir, transcribir, o agregar efectos a videos.

## Herramientas a usar
1. `trim_video` - Cortar segmentos
2. `advanced_video_editor` - Editor completo
3. `auto_subtitles` - Subtítulos automáticos con Whisper
4. `add_music_to_video` - Agregar música
5. `professional_color_grading` - Color grading

## Pasos
1. Localizar el video
2. Analizar su contenido
3. Aplicar ediciones necesarias
4. Agregar subtítulos si es necesario
5. Exportar en formato adecuado
"""
    },
    "data_analysis": {
        "name": "data_analysis",
        "description": "Analizar datos y generar reportes",
        "instructions": """# Skill: Data Analysis

## Cuándo usar
Cuando el usuario pide analizar datos, CSV, Excel, generar estadísticas o visualizaciones.

## Herramientas a usar
1. `analyze_csv_data` - Analizar CSV
2. `read_pdf_text` - Leer PDFs
3. `export_to_excel` - Exportar a Excel
4. `generate_data_chart` - Generar gráficos

## Pasos
1. Localizar el archivo de datos
2. Leer y parsear los datos
3. Calcular estadísticas
4. Generar visualizaciones
5. Crear reporte
"""
    },
    "system_administration": {
        "name": "system_administration",
        "description": "Administrar sistema, servidores, Docker, SSH",
        "instructions": """# Skill: System Administration

## Cuándo usar
Cuando el usuario pide administrar el sistema, instalar paquetes, configurar servicios, Docker, SSH, etc.

## Herramientas a usar
1. `execute_cmd` - Ejecutar comandos
2. `manage_docker_container` - Docker
3. `check_system_resources` - Recursos
4. `deploy_docker_*` - Deployment
5. `ssh` tools - SSH

## Pasos
1. Verificar el estado del sistema
2. Identificar qué necesita hacerse
3. Ejecutar comandos con permisos apropiados
4. Verificar resultados
5. Reportar al usuario
"""
    },
    "content_creation": {
        "name": "content_creation",
        "description": "Crear contenido, documentos, PDFs, presentaciones",
        "instructions": """# Skill: Content Creation

## Cuándo usar
Cuando el usuario pide crear documentos, PDFs, reportes, contratos, facturas, etc.

## Herramientas a usar
1. `pdf_create_*` - PDFs profesionales
2. `write_file` - Archivos de texto
3. `export_to_excel` - Hojas de cálculo
4. `generate_mermaid_diagram` - Diagramas

## Pasos
1. Entender el tipo de contenido
2. Estructurar la información
3. Crear el contenido
4. Dar formato profesional
5. Exportar en el formato adecuado
"""
    },
    "ai_ml": {
        "name": "ai_ml",
        "description": "Machine Learning, análisis de datos, modelos de IA",
        "instructions": """# Skill: AI / Machine Learning

## Cuándo usar
Cuando el usuario pide entrenar modelos, análisis predictivo, machine learning, deep learning.

## Herramientas a usar
1. `jupyter_live_kernel` - Jupyter
2. `sql_execute_query` - SQL queries
3. `predictive_market_analysis` - Análisis predictivo
4. `autonomous_codebase_healing` - Auto-healing

## Pasos
1. Recopilar datos
2. Limpiar y preparar
3. Entrenar modelo
4. Evaluar
5. Desplegar
"""
    }
}


class AutoSkillCreator:
    """
    Automatically creates skills when needed.
    
    Detects what skills are needed based on the task and creates them.
    """
    
    def __init__(self, model: Optional[str] = None, console: Optional[Console] = None):
        self.console = console
        self.model = model or os.environ.get('AUTOMYX_MODEL', 'openai/gpt-oss-120b')
        self.skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.created_skills: List[str] = []
        
    def detect_needed_skill(self, task: str) -> Optional[str]:
        """
        Detect what skill is needed for a task.
        """
        task_lower = task.lower()
        
        # Web development
        if any(kw in task_lower for kw in ['web', 'página', 'sitio', 'html', 'css', 'javascript', 'frontend']):
            return "web_development"
        
        # Video editing
        if any(kw in task_lower for kw in ['video', 'mp4', 'avi', 'cortar video', 'editar video']):
            return "video_editing"
        
        # Data analysis
        if any(kw in task_lower for kw in ['datos', 'csv', 'excel', 'análisis', 'estadística', 'gráfico']):
            return "data_analysis"
        
        # System administration
        if any(kw in task_lower for kw in ['docker', 'ssh', 'servidor', 'sistema', 'instalar', 'desplegar']):
            return "system_administration"
        
        # Content creation
        if any(kw in task_lower for kw in ['pdf', 'documento', 'reporte', 'contrato', 'factura', 'contenido']):
            return "content_creation"
        
        # AI/ML
        if any(kw in task_lower for kw in ['machine learning', 'ia', 'modelo', 'entrenar', 'predicción']):
            return "ai_ml"
        
        return None
    
    def create_skill_from_template(self, skill_name: str) -> bool:
        """
        Create a skill from a predefined template.
        """
        if skill_name not in SKILL_TEMPLATES:
            return False
        
        template = SKILL_TEMPLATES[skill_name]
        skill_dir = self.skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        skill_file = skill_dir / "SKILL.md"
        
        content = f"""---
name: {template['name']}
description: {template['description']}
---

{template['instructions']}
"""
        
        try:
            skill_file.write_text(content, encoding='utf-8')
            self.created_skills.append(skill_name)
            if self.console:
                self.console.print(f"[green]Skill created:[/] {skill_name}")
            return True
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error creating skill: {e}[/red]")
            return False
    
    def create_custom_skill(self, name: str, description: str, 
                            instructions: str) -> bool:
        """
        Create a custom skill with provided details.
        """
        try:
            from tools.skill_tools import SkillTools
            result = SkillTools.create_skill(
                name=name,
                description=description,
                instrucciones=instructions
            )
            if "[OK]" in result or "creada" in result.lower():
                self.created_skills.append(name)
                if self.console:
                    self.console.print(f"[green]Custom skill created:[/] {name}")
                return True
            return False
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error: {e}[/red]")
            return False
    
    def auto_create_for_task(self, task: str) -> Optional[str]:
        """
        Auto-detect and create skill for a task.
        """
        skill_name = self.detect_needed_skill(task)
        if skill_name:
            self.create_skill_from_template(skill_name)
            return skill_name
        return None


def main():
    """Test auto-skill creation."""
    console = Console() if Console else None
    creator = AutoSkillCreator(console=console)
    
    tasks = [
        "creame una página web profesional",
        "edita este video y agregale subtítulos",
        "analiza este CSV de ventas",
        "instala Docker en el servidor"
    ]
    
    for task in tasks:
        print(f"\nTask: {task}")
        skill = creator.auto_create_for_task(task)
        if skill:
            print(f"  → Created skill: {skill}")


if __name__ == '__main__':
    main()
