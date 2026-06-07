"""
Error Learning - Sistema de aprendizaje de errores
Captura fallos, genera post-mortems estructurados y mantiene una base de "lessons learned"
que se inyecta automáticamente en el prompt para que el agente NO repita los mismos errores.
"""
import os
import re
import json
import hashlib
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional


class ErrorLearningSystem:
    """Memoria estructurada de errores con prevención proactiva."""

    BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data")
    ERRORS_FILE = os.path.join(BASE_DIR, "error_log.json")
    LESSONS_FILE = os.path.join(BASE_DIR, "lessons_learned.json")
    BLOCKLIST_FILE = os.path.join(BASE_DIR, "tool_blocklist.json")

    # ---------- INTERNAL ----------
    @staticmethod
    def _load(path: str, default):
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    @staticmethod
    def _save(path: str, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _signature(tool: str, args: Dict[str, Any], error_msg: str) -> str:
        # Firma estable de un patrón de error
        key_args = sorted([k for k in args.keys() if isinstance(args.get(k), (str, int, float, bool))])
        err_clean = re.sub(r"\d+", "N", error_msg)[:200]
        sig_text = f"{tool}|{','.join(key_args)}|{err_clean}"
        return hashlib.md5(sig_text.encode()).hexdigest()[:16]

    # ---------- LOG ERROR ----------
    @staticmethod
    def log_error(tool: str, args: Dict[str, Any], error_msg: str, context: str = "") -> Dict[str, Any]:
        sig = ErrorLearningSystem._signature(tool, args, error_msg)
        errors = ErrorLearningSystem._load(ErrorLearningSystem.ERRORS_FILE, [])
        entry = {
            "signature": sig,
            "tool": tool,
            "args_summary": {k: (str(v)[:120] if isinstance(v, str) else v) for k, v in args.items()},
            "error": str(error_msg)[:500],
            "context": context[:300],
            "timestamp": datetime.now().isoformat(),
        }
        errors.append(entry)
        ErrorLearningSystem._save(ErrorLearningSystem.ERRORS_FILE, errors[-1000:])

        # Auto-generar lección si el mismo error ocurre â‰¥ 2 veces
        count = sum(1 for e in errors if e["signature"] == sig)
        if count >= 2:
            ErrorLearningSystem._auto_create_lesson(tool, args, error_msg, sig, count)
        return entry

    # ---------- AUTO LESSON ----------
    @staticmethod
    def _auto_create_lesson(tool: str, args: Dict[str, Any], error_msg: str, sig: str, occurrences: int):
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        for L in lessons:
            if L.get("signature") == sig:
                L["occurrences"] = occurrences
                L["last_seen"] = datetime.now().isoformat()
                ErrorLearningSystem._save(ErrorLearningSystem.LESSONS_FILE, lessons)
                return

        # Heurismas para sugerir solución
        suggestion = ErrorLearningSystem._suggest_fix(tool, args, error_msg)
        lessons.append({
            "signature": sig,
            "tool": tool,
            "error_pattern": re.sub(r"\d+", "N", str(error_msg))[:200],
            "args_pattern": {k: type(v).__name__ for k, v in args.items()},
            "occurrences": occurrences,
            "suggestion": suggestion,
            "preventive_rule": ErrorLearningSystem._generate_rule(tool, error_msg, suggestion),
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        })
        ErrorLearningSystem._save(ErrorLearningSystem.LESSONS_FILE, lessons)

    @staticmethod
    def _suggest_fix(tool: str, args: Dict[str, Any], error_msg: str) -> str:
        err = str(error_msg).lower()
        if "not found" in err or "no such file" in err or "no existe" in err or "no encontrado" in err:
            return f"Antes de llamar a `{tool}`, verifica que el archivo/carpeta existe con `list_directory` o `task_coord_resolve_path`."
        if "permission" in err or "permiso" in err or "denied" in err or "eperm" in err:
            return f"`{tool}` falla por permisos. Usa una ruta dentro de Downloads/Documents o el bypass de `create_directory`."
        if "timeout" in err or "timed out" in err:
            return f"`{tool}` agota timeout. Reduce el tamaño del input o aumenta el timeout si el parámetro existe."
        if "syntax" in err or "json" in err:
            return f"`{tool}` recibió JSON malformado. Valida el formato de args antes de enviar."
        if "connection" in err or "refused" in err or "unreachable" in err:
            return f"`{tool}` no pudo conectar. Verifica el servicio remoto/internet y reintenta una vez."
        if "module" in err or "no module named" in err or "import" in err:
            mod = re.search(r"no module named ['\"]?(\w+)", err)
            return f"Falta instalar el módulo Python `{mod.group(1) if mod else 'desconocido'}`. Ejecuta `pip install ...` antes."
        if "invalid argument" in err or "unexpected keyword" in err:
            return f"Argumentos inválidos para `{tool}`. Revisa la firma exacta en el prompt de Soul.md."
        return f"`{tool}` falló de forma genérica. Reintenta con argumentos validados o cambia de estrategia."

    @staticmethod
    def _generate_rule(tool: str, error_msg: str, suggestion: str) -> str:
        return f"REGLA APRENDIDA: Cuando uses `{tool}`, recuerda: {suggestion}"

    # ---------- QUERY LESSONS ----------
    @staticmethod
    def get_lessons_for_tool(tool: str) -> List[Dict[str, Any]]:
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        return [L for L in lessons if L.get("tool") == tool]

    @staticmethod
    def get_all_lessons(limit: int = 20) -> Dict[str, Any]:
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        lessons = sorted(lessons, key=lambda x: x.get("occurrences", 0), reverse=True)[:limit]
        return {"count": len(lessons), "lessons": lessons}

    @staticmethod
    def get_active_warnings(tools_in_context: List[str]) -> str:
        """Devuelve texto listo para inyectar al system prompt con lecciones de las tools activas."""
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        relevant = [L for L in lessons if L.get("tool") in tools_in_context]
        if not relevant:
            return ""
        lines = ["\n[LECCIONES APRENDIDAS - NO REPITAS ESTOS ERRORES]"]
        for L in sorted(relevant, key=lambda x: x.get("occurrences", 0), reverse=True)[:10]:
            lines.append(f"- {L['preventive_rule']} (ocurrió {L['occurrences']} veces)")
        return "\n".join(lines)

    @staticmethod
    def get_warnings_for_request(user_request: str) -> str:
        """Análisis del texto del usuario para detectar tools probables y mostrar sus lecciones."""
        text = user_request.lower()
        likely_tools = []
        keyword_map = {
            "video": ["create_tiktok_edit", "auto_subtitles", "advanced_video_editor", "trim_video"],
            "blender": ["execute_blender_python_code", "generate_professional_3d_video"],
            "tiktok": ["play_tiktok_desktop_video", "create_tiktok_edit"],
            "vyrex": ["generate_vyrex_video"],
            "gemini": ["generate_gemini_video", "generate_gemini_image"],
            "carpeta": ["create_directory", "list_directory"],
            "archivo": ["write_file", "read_file"],
            "git": ["git_advanced_merge", "github_inspect_repo"],
            "docker": ["docker_deploy_stack", "manage_docker_container"],
            "factura": ["accountant_parse_invoice_pdf", "accountant_calculate_tax"],
            "stream": ["livestream_obs_start_stream", "livestream_setup_multistream"],
        }
        for kw, tools in keyword_map.items():
            if kw in text:
                likely_tools.extend(tools)
        return ErrorLearningSystem.get_active_warnings(list(set(likely_tools)))

    # ---------- STATS ----------
    @staticmethod
    def stats() -> Dict[str, Any]:
        errors = ErrorLearningSystem._load(ErrorLearningSystem.ERRORS_FILE, [])
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        tool_freq = defaultdict(int)
        for e in errors:
            tool_freq[e.get("tool", "?")] += 1
        top_failing = sorted(tool_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "total_errors_logged": len(errors),
            "total_lessons": len(lessons),
            "top_failing_tools": [{"tool": t, "errors": c} for t, c in top_failing],
        }

    @staticmethod
    def clear_lessons() -> Dict[str, Any]:
        ErrorLearningSystem._save(ErrorLearningSystem.LESSONS_FILE, [])
        return {"cleared": True}

    @staticmethod
    def add_manual_lesson(tool: str, rule: str, severity: str = "medium") -> Dict[str, Any]:
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        lessons.append({
            "signature": hashlib.md5(f"manual_{tool}_{rule}".encode()).hexdigest()[:16],
            "tool": tool,
            "preventive_rule": f"REGLA MANUAL: {rule}",
            "severity": severity,
            "manual": True,
            "occurrences": 0,
            "created_at": datetime.now().isoformat(),
        })
        ErrorLearningSystem._save(ErrorLearningSystem.LESSONS_FILE, lessons)
        return {"added": rule}
