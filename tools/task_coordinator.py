"""
Task Coordinator - Coordinador de tareas con precisión quirúrgica
Resuelve peticiones ambiguas tipo "reedita el video en X carpeta", verifica preconditions,
genera plan estructurado y previene errores recurrentes.
"""
import os
import re
import json
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class TaskCoordinator:
    """Coordinador maestro que añade precisión y autocorrección al agente."""

    USER_HOME = os.path.expanduser("~")
    DOWNLOADS = os.path.join(USER_HOME, "Downloads")
    DESKTOP = os.path.join(USER_HOME, "Desktop")
    DOCUMENTS = os.path.join(USER_HOME, "Documents")
    PICTURES = os.path.join(USER_HOME, "Pictures")
    VIDEOS = os.path.join(USER_HOME, "Videos")
    MUSIC = os.path.join(USER_HOME, "Music")

    FOLDER_ALIASES = {
        "descargas": "Downloads", "downloads": "Downloads",
        "escritorio": "Desktop", "desktop": "Desktop",
        "documentos": "Documents", "documents": "Documents",
        "imágenes": "Pictures", "imagenes": "Pictures", "fotos": "Pictures", "pictures": "Pictures",
        "videos": "Videos", "vídeos": "Videos",
        "música": "Music", "musica": "Music", "music": "Music",
    }

    VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".heic"}
    AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
    DOC_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"}
    CODE_EXTS = {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".go", ".rs"}

    PLANS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data", "execution_plans.json")

    # ---------- PATH RESOLUTION ----------
    @staticmethod
    def resolve_path(text: str) -> Dict[str, Any]:
        """Convierte 'descargas/video' â†’ ruta absoluta verificada."""
        original = text.strip().strip('"').strip("'")

        # Si ya es absoluta y existe
        if os.path.isabs(original) and os.path.exists(original):
            return {"resolved": original, "exists": True, "is_dir": os.path.isdir(original)}

        # Detectar alias de carpeta al inicio
        lower = original.lower().replace("\\", "/")
        parts = lower.split("/", 1)
        rest = parts[1] if len(parts) > 1 else ""
        alias = parts[0]
        if alias in TaskCoordinator.FOLDER_ALIASES:
            base = os.path.join(TaskCoordinator.USER_HOME, TaskCoordinator.FOLDER_ALIASES[alias])
            resolved = os.path.join(base, *rest.split("/")) if rest else base
            resolved = os.path.normpath(resolved)
            return {"resolved": resolved, "exists": os.path.exists(resolved), "is_dir": os.path.isdir(resolved)}

        # Si menciona una carpeta especial en cualquier parte
        for alias_k, folder in TaskCoordinator.FOLDER_ALIASES.items():
            if alias_k in lower:
                base = os.path.join(TaskCoordinator.USER_HOME, folder)
                return {"resolved": base, "exists": os.path.exists(base), "is_dir": True, "guessed": True}

        # Fallback: relativa al CWD
        resolved = os.path.abspath(original)
        return {"resolved": resolved, "exists": os.path.exists(resolved), "is_dir": os.path.isdir(resolved)}

    @staticmethod
    def find_files(folder: str, extensions: List[str] = None, name_contains: str = "", recursive: bool = True, limit: int = 20) -> Dict[str, Any]:
        """Busca archivos en una carpeta con filtros."""
        path_info = TaskCoordinator.resolve_path(folder)
        if not path_info["exists"]:
            return {"error": f"Carpeta no existe: {path_info['resolved']}", "tried": path_info["resolved"]}
        folder = path_info["resolved"]
        extensions = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in (extensions or [])]
        results = []
        walker = os.walk(folder) if recursive else [(folder, [], os.listdir(folder))]
        for root, _, files in walker:
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if extensions and ext not in extensions:
                    continue
                if name_contains and name_contains.lower() not in f.lower():
                    continue
                full = os.path.join(root, f)
                try:
                    stat = os.stat(full)
                    results.append({
                        "path": full,
                        "name": f,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except Exception:
                    pass
            if not recursive:
                break
        results.sort(key=lambda x: x["modified"], reverse=True)
        return {"folder": folder, "count": len(results), "files": results[:limit]}

    # ---------- INTENT PARSING ----------
    @staticmethod
    def parse_intent(user_request: str) -> Dict[str, Any]:
        """Analiza la petición y extrae: acción, objeto, ubicación, modificadores."""
        text = user_request.lower()
        intent = {
            "raw": user_request,
            "action": None,
            "target_type": None,
            "folder_hint": None,
            "modifiers": [],
            "needs_clarification": [],
        }

        # Acción
        actions = {
            "editar": ["edita", "edit", "modifica", "cambia"],
            "reeditar": ["reedita", "vuelve a editar", "re-edita", "edita de nuevo"],
            "buscar": ["busca", "encuentra", "localiza", "find"],
            "convertir": ["convierte", "convert", "transforma", "pasa a"],
            "subir": ["sube", "publica", "upload", "postea"],
            "descargar": ["descarga", "baja", "download"],
            "renombrar": ["renombra", "rename", "cambia el nombre"],
            "borrar": ["borra", "elimina", "delete", "remove"],
            "organizar": ["organiza", "ordena", "clasifica"],
            "crear": ["crea", "genera", "haz", "construye", "create", "make"],
            "analizar": ["analiza", "analyze", "estudia", "revisa"],
            "abrir": ["abre", "open", "lanza", "ejecuta"],
        }
        for act, keys in actions.items():
            if any(k in text for k in keys):
                intent["action"] = act
                break

        # Tipo de objeto
        types = {
            "video": ["video", "vídeo", "película", "clip", "mp4", "tiktok", "reel", "short"],
            "imagen": ["imagen", "image", "foto", "picture", "png", "jpg"],
            "audio": ["audio", "cancion", "canción", "mp3", "música", "musica", "sonido"],
            "documento": ["pdf", "documento", "doc", "informe", "reporte", "contrato"],
            "codigo": ["código", "codigo", "script", "programa", "py", "js", "html", "css"],
            "juego": ["juego", "game", "jueguito", "minijuego", "2d", "3d", "canvas", "phaser", "pixi"],
            "carpeta": ["carpeta", "folder", "directorio"],
        }
        for tp, keys in types.items():
            if any(k in text for k in keys):
                intent["target_type"] = tp
                break

        # Carpeta mencionada
        for alias in TaskCoordinator.FOLDER_ALIASES:
            if alias in text:
                intent["folder_hint"] = alias
                break

        # Modificadores frecuentes
        if "subtítulos" in text or "subtitulos" in text or "subtitles" in text:
            intent["modifiers"].append("subtitles")
        if "música" in text or "musica" in text or "music" in text:
            intent["modifiers"].append("music")
        if "zoom" in text:
            intent["modifiers"].append("zoom")
        if "tiktok" in text or "short" in text or "reel" in text:
            intent["modifiers"].append("vertical_short")
        if "mrbeast" in text:
            intent["modifiers"].append("mrbeast_style")
        if "cinemático" in text or "cinematic" in text:
            intent["modifiers"].append("cinematic")

        # Detectar ambigüedad
        if intent["action"] in ("reeditar", "editar", "convertir", "borrar", "renombrar") and not intent.get("folder_hint"):
            intent["needs_clarification"].append("Â¿En qué carpeta se encuentra el archivo?")
        if intent["action"] in ("crear", "editar") and intent["target_type"] is None:
            intent["needs_clarification"].append("Â¿Qué tipo de archivo (video, imagen, audio, documento)?")

        return intent

    # ---------- PLAN GENERATION ----------
    @staticmethod
    def build_plan(user_request: str) -> Dict[str, Any]:
        """Construye un plan ejecutable estructurado paso a paso."""
        intent = TaskCoordinator.parse_intent(user_request)
        plan = {
            "request": user_request,
            "intent": intent,
            "preconditions": [],
            "steps": [],
            "verification": [],
            "created_at": datetime.now().isoformat(),
            "plan_id": datetime.now().strftime("%Y%m%d%H%M%S"),
        }

        # Resolver carpeta
        if intent["folder_hint"]:
            res = TaskCoordinator.resolve_path(intent["folder_hint"])
            plan["preconditions"].append({"check": "folder_exists", "path": res["resolved"], "ok": res["exists"]})

            # Detectar archivos candidatos
            if intent["target_type"]:
                ext_map = {
                    "video": list(TaskCoordinator.VIDEO_EXTS),
                    "imagen": list(TaskCoordinator.IMAGE_EXTS),
                    "audio": list(TaskCoordinator.AUDIO_EXTS),
                    "documento": list(TaskCoordinator.DOC_EXTS),
                    "codigo": list(TaskCoordinator.CODE_EXTS),
                    "juego": [".html", ".js", ".css", ".json"],  # archivos web para juegos
                }
                exts = ext_map.get(intent["target_type"], [])
                found = TaskCoordinator.find_files(res["resolved"], extensions=exts, limit=10)
                plan["candidate_files"] = found.get("files", [])
                if not plan["candidate_files"]:
                    plan["preconditions"].append({"check": "files_found", "ok": False, "warning": f"No hay archivos {intent['target_type']} en {res['resolved']}"})
                else:
                    plan["preconditions"].append({"check": "files_found", "ok": True, "count": len(plan["candidate_files"])})

        # Generar pasos según acción
        action = intent["action"]
        tt = intent["target_type"]
        mods = intent["modifiers"]

        if action in ("reeditar", "editar") and tt == "video":
            file_arg = "<PRIMER_VIDEO_ENCONTRADO>"
            output = os.path.join(TaskCoordinator.DOWNLOADS, f"edit_{plan['plan_id']}.mp4")
            if "vertical_short" in mods or "mrbeast_style" in mods:
                plan["steps"].append({
                    "n": 1, "tool": "create_tiktok_edit",
                    "args": {"input_path": file_arg, "output_path": output, "add_subtitles": "subtitles" in mods,
                             "effect": "vibrant", "animation": "zoom_in", "subtitle_template": "two_word_centered"},
                    "rationale": "Crea un short viral con efectos retentivos."
                })
            else:
                plan["steps"].append({
                    "n": 1, "tool": "advanced_video_editor",
                    "args": {"input_video": file_arg, "output_path": output, "color_grading": "cinematic" if "cinematic" in mods else "none"},
                    "rationale": "Edición profesional con color grading."
                })
                if "subtitles" in mods:
                    plan["steps"].append({
                        "n": 2, "tool": "auto_subtitles",
                        "args": {"input_path": output, "output_path": output.replace(".mp4", "_subs.mp4"),
                                 "language": "es", "style": "mrbeast" if "mrbeast_style" in mods else "cinematic",
                                 "position": "center", "font_color": "blanco"},
                        "rationale": "Agrega subtítulos dinámicos sincronizados."
                    })
            plan["verification"].append({"check": "output_file_exists", "path": output})

        elif action == "buscar":
            plan["steps"].append({
                "n": 1, "tool": "list_directory",
                "args": {"path": plan["preconditions"][0]["path"] if plan["preconditions"] else TaskCoordinator.DOWNLOADS},
                "rationale": "Lista archivos en la carpeta target."
            })

        elif action == "crear" and tt == "documento":
            output = os.path.join(TaskCoordinator.DOWNLOADS, f"documento_{plan['plan_id']}.pdf")
            plan["steps"].append({
                "n": 1, "tool": "execute_cmd",
                "args": {"command": "pip install fpdf2 -q"},
                "rationale": "Asegura que fpdf2 esté instalado para generar PDFs profesionales."
            })
            plan["verification"].append({"check": "output_file_exists", "path": output})

        elif action == "crear" and tt == "juego":
            # Crear juego 2D en HTML5/Canvas - archivo principal
            output_html = os.path.join(TaskCoordinator.DOWNLOADS, intent.get("folder_hint", "Downloads"), f"game_{plan['plan_id']}.html")
            plan["steps"].append({
                "n": 1,
                "tool": "write_file",
                "args": {
                    "path": output_html,
                    "content": TaskCoordinator._generate_2d_game_template(intent)
                },
                "rationale": "Crea el juego 2D profesional en HTML5/Canvas."
            })
            # Crear archivo JS separado para lógica
            output_js = output_html.replace(".html", ".js")
            plan["steps"].append({
                "n": 2,
                "tool": "write_file",
                "args": {
                    "path": output_js,
                    "content": TaskCoordinator._generate_game_js_template(intent)
                },
                "rationale": "Crea la lógica del juego en JavaScript separado."
            })
            plan["verification"].append({"check": "output_file_exists", "path": output_html})

        elif action == "crear" and tt == "video":
            # Crear video base (slideshow, color, etc.)
            output = os.path.join(TaskCoordinator.DOWNLOADS, intent.get("folder_hint", "Downloads"), f"video_{plan['plan_id']}.mp4")
            plan["steps"].append({
                "n": 1,
                "tool": "create_tiktok_edit",
                "args": {"input_path": "<PRIMER_VIDEO_ENCONTRADO>", "output_path": output, "add_subtitles": False},
                "rationale": "Crea video base para edición posterior."
            })
            plan["verification"].append({"check": "output_file_exists", "path": output})

        elif action == "crear" and tt == "imagen":
            output = os.path.join(TaskCoordinator.DOWNLOADS, intent.get("folder_hint", "Downloads"), f"imagen_{plan['plan_id']}.png")
            plan["steps"].append({
                "n": 1,
                "tool": "generate_gemini_image",
                "args": {"prompt": user_request, "output_path": output},
                "rationale": "Genera imagen con IA según descripción."
            })
            plan["verification"].append({"check": "output_file_exists", "path": output})

        elif action == "crear" and tt == "codigo":
            # Determinar extensión por mención
            ext = ".py"
            if any(k in user_request.lower() for k in ["html", "web", "página", "sitio"]):
                ext = ".html"
            elif any(k in user_request.lower() for k in ["js", "javascript", "script"]):
                ext = ".js"
            elif any(k in user_request.lower() for k in ["css", "estilo"]):
                ext = ".css"
            output = os.path.join(TaskCoordinator.DOWNLOADS, intent.get("folder_hint", "Downloads"), f"codigo_{plan['plan_id']}{ext}")
            plan["steps"].append({
                "n": 1,
                "tool": "write_file",
                "args": {"path": output, "content": f"# Código generado para: {user_request}\n\n# TODO: Implementar\n"},
                "rationale": "Crea archivo de código base."
            })
            plan["verification"].append({"check": "output_file_exists", "path": output})

        elif action == "abrir":
            plan["steps"].append({
                "n": 1, "tool": "open_program",
                "args": {"program_name": "<EXTRAER_DEL_TEXTO>"},
                "rationale": "Abre el programa solicitado."
            })

        # Guardar plan
        TaskCoordinator._persist_plan(plan)
        return plan

    @staticmethod
    def _persist_plan(plan: Dict[str, Any]):
        os.makedirs(os.path.dirname(TaskCoordinator.PLANS_FILE), exist_ok=True)
        plans = []
        if os.path.exists(TaskCoordinator.PLANS_FILE):
            try:
                with open(TaskCoordinator.PLANS_FILE, "r", encoding="utf-8") as f:
                    plans = json.load(f)
            except Exception:
                plans = []
        plans.append(plan)
        with open(TaskCoordinator.PLANS_FILE, "w", encoding="utf-8") as f:
            json.dump(plans[-100:], f, ensure_ascii=False, indent=2)

    # ---------- PRECONDITION VERIFICATION ----------
    @staticmethod
    def verify_preconditions(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Re-evalúa las preconditions del plan."""
        failures = []
        for pc in plan.get("preconditions", []):
            if pc.get("check") == "folder_exists":
                if not os.path.exists(pc["path"]):
                    failures.append(pc)
            elif pc.get("check") == "files_found" and not pc.get("ok"):
                failures.append(pc)
        return {"all_ok": len(failures) == 0, "failures": failures}

    @staticmethod
    def verify_outputs(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica que los outputs del plan se hayan creado."""
        ok = []
        missing = []
        for v in plan.get("verification", []):
            if v.get("check") == "output_file_exists":
                p = v["path"]
                if os.path.exists(p):
                    size = os.path.getsize(p)
                    ok.append({"path": p, "size_bytes": size})
                else:
                    missing.append(p)
        return {"verified": len(ok), "missing": missing, "all_ok": len(missing) == 0}

    @staticmethod
    def summarize_plan(plan: Dict[str, Any]) -> str:
        """Genera un resumen legible del plan para enviar al LLM."""
        lines = [f"# Plan de Ejecución {plan['plan_id']}", f"Petición: {plan['request']}\n"]
        lines.append(f"Acción detectada: **{plan['intent']['action']}** sobre **{plan['intent']['target_type']}**")
        if plan["intent"]["folder_hint"]:
            lines.append(f"Carpeta target: {plan['intent']['folder_hint']}")
        if plan.get("candidate_files"):
            lines.append(f"\nArchivos candidatos ({len(plan['candidate_files'])}):")
            for f in plan["candidate_files"][:5]:
                lines.append(f"  - {f['name']} ({f['size_mb']} MB, mod: {f['modified'][:10]})")
        lines.append("\nPasos planificados:")
        for s in plan["steps"]:
            lines.append(f"  {s['n']}. `{s['tool']}` â†’ {s['rationale']}")
        if plan["intent"]["needs_clarification"]:
            lines.append("\nâš ï¸ Ambiguedades detectadas:")
            for q in plan["intent"]["needs_clarification"]:
                lines.append(f"  - {q}")
        return "\n".join(lines)
