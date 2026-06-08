"""
Error Learning - Sistema de aprendizaje de errores
Captura fallos, genera post-mortems estructurados, mantiene lecciones, detecta
fallos en cascada y genera código de auto-healing.
"""
import os
import re
import json
import hashlib
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, Any, List, Optional


class ErrorLearningSystem:
    """Memoria estructurada de errores con prevención proactiva y auto-healing."""

    BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data")
    ERRORS_FILE = os.path.join(BASE_DIR, "error_log.json")
    LESSONS_FILE = os.path.join(BASE_DIR, "lessons_learned.json")
    BLOCKLIST_FILE = os.path.join(BASE_DIR, "tool_blocklist.json")
    CASCADE_FILE = os.path.join(BASE_DIR, "cascade_failures.json")

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
    def _signature(tool: str, args: Dict[str, Any], error_msg: str, context: str = "") -> str:
        key_args = sorted([k for k in args.keys() if isinstance(args.get(k), (str, int, float, bool))])
        err_clean = re.sub(r"\d+", "N", error_msg)[:200]
        ctx_sig = hashlib.md5(context.encode()).hexdigest()[:8] if context else ""
        sig_text = f"{tool}|{','.join(key_args)}|{err_clean}|{ctx_sig}"
        return hashlib.md5(sig_text.encode()).hexdigest()[:16]

    # ---------- LOG ERROR ----------
    @staticmethod
    def log_error(tool: str, args: Dict[str, Any], error_msg: str, context: str = "") -> Dict[str, Any]:
        sig = ErrorLearningSystem._signature(tool, args, error_msg, context)
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
        ErrorLearningSystem._save(ErrorLearningSystem.ERRORS_FILE, errors[-2000:])

        count = sum(1 for e in errors if e["signature"] == sig)
        if count >= 2:
            ErrorLearningSystem._auto_create_lesson(tool, args, error_msg, sig, count)

        # Detect cascades
        ErrorLearningSystem._detect_cascade(errors, entry)

        return entry

    # ---------- CASCADE DETECTION ----------
    @staticmethod
    def _detect_cascade(errors: List[dict], new_entry: dict):
        """Detecta cuando 3+ herramientas fallan en secuencia rápida (< 60s)."""
        cascades = ErrorLearningSystem._load(ErrorLearningSystem.CASCADE_FILE, [])

        recent = [
            e for e in errors[-10:]
            if "timestamp" in e
        ]
        if len(recent) < 3:
            return

        try:
            new_ts = datetime.fromisoformat(new_entry["timestamp"])
        except Exception:
            return

        recent_timed = []
        for e in recent:
            try:
                ets = datetime.fromisoformat(e["timestamp"])
                if (new_ts - ets).total_seconds() < 60:
                    recent_timed.append(e)
            except Exception:
                continue

        if len(recent_timed) >= 3:
            tools_in_cascade = list(dict.fromkeys(e["tool"] for e in recent_timed))
            if len(tools_in_cascade) >= 2:
                cascade_key = "->".join(tools_in_cascade[-3:])
                for c in cascades:
                    if c.get("key") == cascade_key:
                        c["occurrences"] += 1
                        c["last_seen"] = new_entry["timestamp"]
                        ErrorLearningSystem._save(ErrorLearningSystem.CASCADE_FILE, cascades)
                        return
                cascades.append({
                    "key": cascade_key,
                    "tools": tools_in_cascade,
                    "errors": [e["error"][:150] for e in recent_timed],
                    "occurrences": 1,
                    "first_seen": recent_timed[0]["timestamp"],
                    "last_seen": new_entry["timestamp"],
                })
                ErrorLearningSystem._save(ErrorLearningSystem.CASCADE_FILE, cascades)

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

        suggestion = ErrorLearningSystem._suggest_fix(tool, args, error_msg)
        healing_code = ErrorLearningSystem._generate_healing_code(tool, error_msg, args)

        lessons.append({
            "signature": sig,
            "tool": tool,
            "error_pattern": re.sub(r"\d+", "N", str(error_msg))[:200],
            "args_pattern": {k: type(v).__name__ for k, v in args.items()},
            "occurrences": occurrences,
            "suggestion": suggestion,
            "healing_code": healing_code,
            "preventive_rule": ErrorLearningSystem._generate_rule(tool, error_msg, suggestion),
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        })
        ErrorLearningSystem._save(ErrorLearningSystem.LESSONS_FILE, lessons)

    @staticmethod
    def _generate_healing_code(tool: str, error_msg: str, args: Dict[str, Any]) -> str:
        """Genera código ejecutable para auto-reparar errores comunes."""
        err = str(error_msg).lower()

        if "not found" in err or "no such file" in err or "no existe" in err:
            path = next((v for v in args.values() if isinstance(v, str) and (
                v.startswith("/") or v.startswith("C:") or "\\" in v or "/" in v
            )), "")
            if path:
                return (
                    f'import os\n'
                    f'os.makedirs(r"{os.path.dirname(path)}", exist_ok=True)\n'
                )
            return "import os; os.makedirs('.', exist_ok=True)"

        if "permission" in err or "denied" in err or "eperm" in err:
            return (
                'import subprocess\n'
                'subprocess.run(["icacls", ".", "/grant", "Users:F", "/T", "/Q"], capture_output=True)\n'
            )

        if "timeout" in err or "timed out" in err:
            return "# Aumentar timeout o reducir carga"

        if "module" in err or "no module named" in err:
            mod = re.search(r"no module named ['\"]?(\w+)", err)
            if mod:
                return f'import subprocess; subprocess.run(["pip", "install", "{mod.group(1)}"], check=True)\n'
            return '# pip install <modulo_faltante>'

        if "json" in err or "syntax" in err:
            return '# json.loads() falló, intenta con json_repair de json_protocol'

        return ""

    @staticmethod
    def _suggest_fix(tool: str, args: Dict[str, Any], error_msg: str) -> str:
        err = str(error_msg).lower()
        if "not found" in err or "no such file" in err or "no existe" in err or "no encontrado" in err:
            return (
                f"Antes de llamar a `{tool}`, verifica que el archivo/carpeta existe "
                f"con `list_directory` o `glob_file`. NUNCA asumas que existe."
            )
        if "permission" in err or "permiso" in err or "denied" in err or "eperm" in err:
            return (
                f"`{tool}` falla por permisos. Usa una ruta dentro de "
                f"Downloads/Documents. La herramienta `create_directory` ya tiene bypass."
            )
        if "timeout" in err or "timed out" in err:
            return (
                f"`{tool}` agota timeout. Reduce tamaño del input o divide la tarea "
                f"en partes más pequeñas."
            )
        if "syntax" in err or "json" in err:
            return (
                f"`{tool}` recibió JSON malformado. Usa `json_validate` o `json_repair` "
                f"antes de enviar."
            )
        if "connection" in err or "refused" in err or "unreachable" in err:
            return (
                f"`{tool}` no pudo conectar. Verifica internet/servicio y reintenta "
                f"una vez con los mismos args."
            )
        if "module" in err or "no module named" in err or "import" in err:
            mod = re.search(r"no module named ['\"]?(\w+)", err)
            return (
                f"Falta instalar `{mod.group(1) if mod else 'desconocido'}`. "
                f"Ejecuta `pip install {mod.group(1) if mod else '<modulo>'}`."
            )
        if "invalid argument" in err or "unexpected keyword" in err:
            return (
                f"Argumentos inválidos para `{tool}`. Revisa los nombres exactos de "
                f"parámetros en la tool definition."
            )
        if "already exists" in err or "ya existe" in err:
            return (
                f"`{tool}` reporta que el recurso ya existe. Usa un nombre diferente "
                f"o verifica con `list_directory` primero."
            )
        if "empty" in err or "vacio" in err or "vací" in err:
            return (
                f"`{tool}` recibió datos vacíos. Verifica que el input tenga contenido "
                f"antes de llamar."
            )
        return (
            f"`{tool}` falló de forma genérica. Mensaje: {str(error_msg)[:100]}. "
            f"Reintenta con argumentos validados o cambia de estrategia."
        )

    @staticmethod
    def _generate_rule(tool: str, error_msg: str, suggestion: str) -> str:
        return f"REGLA APRENDIDA: {suggestion}"

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
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        relevant = [L for L in lessons if L.get("tool") in tools_in_context]
        if not relevant:
            return ""
        lines = ["\n[LECCIONES APRENDIDAS - NO REPITAS ESTOS ERRORES]"]
        for L in sorted(relevant, key=lambda x: x.get("occurrences", 0), reverse=True)[:10]:
            rule = L.get("preventive_rule", L.get("suggestion", ""))
            lines.append(f"- {rule} (ocurrio {L['occurrences']} veces)")
        return "\n".join(lines)

    KEYWORD_MAP = {
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
        "pdf": ["pdf_create_contract", "pdf_create_invoice", "pdf_create_report"],
        "notion": ["notion_search", "notion_create_page", "notion_get_page"],
        "obsidian": ["obsidian_create_note", "obsidian_read_note", "obsidian_search"],
        "whatsapp": ["send_whatsapp"],
        "email": ["read_recent_emails", "create_email_draft"],
        "excel": ["export_to_excel", "analyze_csv_data"],
        "capcut": ["open_program"],
        "blender": ["execute_blender_python_code", "generate_professional_3d_video",
                     "generate_cinematic_environment", "simulate_advanced_physics"],
        "3d": ["generate_professional_3d_video", "generate_cinematic_environment",
               "execute_blender_python_code"],
        "codigo": ["write_file", "execute_cmd", "autonomous_codebase_healing"],
        "web": ["web_search", "deep_web_scrape", "open_website"],
        "imagen": ["generate_gemini_image", "screenshot"],
    }

    @staticmethod
    def get_warnings_for_request(user_request: str) -> str:
        text = user_request.lower()
        likely_tools = []
        for kw, tools in ErrorLearningSystem.KEYWORD_MAP.items():
            if kw in text:
                likely_tools.extend(tools)
        return ErrorLearningSystem.get_active_warnings(list(set(likely_tools)))

    @staticmethod
    def get_healing_suggestions(error_msg: str) -> str:
        """Returns executable healing code for common error patterns."""
        err = str(error_msg).lower()
        if "no module named" in err:
            mod = re.search(r"no module named ['\"]?(\w+)", err)
            if mod:
                return (
                    f"# Auto-healing: instalar {mod.group(1)}\n"
                    f'import subprocess, sys\n'
                    f'subprocess.check_call([sys.executable, "-m", "pip", "install", "{mod.group(1)}"])\n'
                )
        if "not found" in err or "no such file" in err:
            return (
                f"# Auto-healing: verificar y crear directorio\n"
                f'import os\n'
                f'path = "[RUTA_AQUI]"\n'
                f'if not os.path.exists(path): os.makedirs(path)\n'
            )
        return ""

    # ---------- STATS ----------
    @staticmethod
    def stats() -> Dict[str, Any]:
        errors = ErrorLearningSystem._load(ErrorLearningSystem.ERRORS_FILE, [])
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        cascades = ErrorLearningSystem._load(ErrorLearningSystem.CASCADE_FILE, [])
        tool_freq = defaultdict(int)
        for e in errors:
            tool_freq[e.get("tool", "?")] += 1
        top_failing = sorted(tool_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "total_errors_logged": len(errors),
            "total_lessons": len(lessons),
            "total_cascades": len(cascades),
            "top_failing_tools": [{"tool": t, "errors": c} for t, c in top_failing],
        }

    @staticmethod
    def get_cascade_report() -> List[Dict]:
        return ErrorLearningSystem._load(ErrorLearningSystem.CASCADE_FILE, [])

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

    @staticmethod
    def analyze_for_skill_creation() -> List[Dict[str, Any]]:
        lessons = ErrorLearningSystem._load(ErrorLearningSystem.LESSONS_FILE, [])
        if not lessons:
            return []
        candidates = []
        for L in lessons:
            occurrences = L.get("occurrences", 0)
            if occurrences >= 3:
                candidates.append({
                    "tool": L.get("tool", "?"),
                    "error_pattern": L.get("error_pattern", "")[:100],
                    "suggestion": L.get("suggestion", ""),
                    "preventive_rule": L.get("preventive_rule", ""),
                    "healing_code": L.get("healing_code", ""),
                    "occurrences": occurrences,
                    "type": "preventive",
                })
        return candidates
