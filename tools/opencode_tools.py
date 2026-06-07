"""
OpenCode Tools - Bridge a opencode CLI como sub-agente
======================================================
Wrapper de core/opencode_bridge.py que expone los métodos como tools
registrables en el agente AUTOMYX.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Asegurar que podemos importar el bridge desde core/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.opencode_bridge import (
    is_opencode_available,
    get_opencode_version,
    opencode_run,
    opencode_sessions_list,
    opencode_session_get,
    opencode_session_resume,
    opencode_code_review,
    opencode_generate_tests,
    opencode_refactor,
    opencode_explain,
    opencode_generate_from_spec,
)


class OpenCodeTools:
    """Bridge entre AUTOMYX y el CLI opencode."""

    @staticmethod
    def is_available() -> Dict[str, Any]:
        """Devuelve si opencode está instalado y su versión."""
        avail = is_opencode_available()
        ver = get_opencode_version()
        return {
            "available": avail,
            "version": ver,
            "install_hint": "npm i -g opencode-ai  (https://github.com/opencode-ai/opencode)" if not avail else None,
        }

    @staticmethod
    def run(
        prompt: str,
        working_dir: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """Ejecuta un prompt en opencode como sub-agente."""
        return opencode_run(
            prompt,
            working_dir=working_dir,
            model=model,
            session_id=session_id,
            timeout=timeout,
        )

    @staticmethod
    def code_review(file_path: str, focus: Optional[str] = None) -> Dict[str, Any]:
        """Pide a opencode que haga code review profesional de un archivo."""
        return opencode_code_review(file_path, focus=focus)

    @staticmethod
    def generate_tests(file_path: str, framework: str = "pytest") -> Dict[str, Any]:
        """Pide a opencode que genere tests para un archivo."""
        return opencode_generate_tests(file_path, framework=framework)

    @staticmethod
    def refactor(file_path: str, instruction: str) -> Dict[str, Any]:
        """Pide a opencode que refactorice un archivo según una instrucción."""
        return opencode_refactor(file_path, instruction)

    @staticmethod
    def explain(file_path: str, level: str = "intermediate") -> Dict[str, Any]:
        """Pide a opencode que explique un archivo."""
        return opencode_explain(file_path, level=level)

    @staticmethod
    def generate_from_spec(spec: str, language: str = "python", output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Genera código desde una especificación en lenguaje natural."""
        return opencode_generate_from_spec(spec, language=language, output_dir=output_dir)

    @staticmethod
    def sessions_list() -> Dict[str, Any]:
        """Lista las sesiones de opencode activas/persistidas."""
        sess = opencode_sessions_list()
        return {"ok": True, "count": len(sess), "sessions": sess}

    @staticmethod
    def session_get(session_id: str) -> Dict[str, Any]:
        """Recupera el contenido de una sesión de opencode."""
        sess = opencode_session_get(session_id)
        if sess is None:
            return {"ok": False, "error": f"sessão {session_id} não existe"}
        return {"ok": True, "session": sess}

    @staticmethod
    def session_resume(session_id: str, prompt: str, model: Optional[str] = None, timeout: int = 120) -> Dict[str, Any]:
        """Continúa una sesión de opencode con un nuevo mensaje."""
        return opencode_session_resume(session_id, prompt, model=model, timeout=timeout)


if __name__ == "__main__":
    print("OpenCode tools:", OpenCodeTools.is_available())
