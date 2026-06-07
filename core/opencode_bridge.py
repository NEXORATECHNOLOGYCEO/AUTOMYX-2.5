"""
AUTOMYX OPENCODE BRIDGE
========================
Permite a AUTOMYX delegar tareas a `opencode` CLI como sub-agente.
OpenCode es una herramienta de AI coding agent que Automyx puede invocar
para:
  - Análisis profundo de código
  - Refactorizaciones automáticas
  - Generación de tests
  - Code review
  - Generación de código desde especificación
  - Sesiones de coding persistentes

Modos de invocación:
  - SUBPROCESS: lanza `opencode ...` como proceso hijo
  - HTTP: si opencode está corriendo como daemon, habla por HTTP
  - STDIN: pipe interactivo para sesiones largas

Si opencode no está instalado, los tools devuelven un error informativo
con instrucciones de instalación. NUNCA se rompe el agente principal.
"""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import time
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("automyx.opencode_bridge")

# Directorio de sesiones de opencode (un JSON por sesión)
SESSIONS_DIR = Path(__file__).parent.parent / "state" / "opencode_sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Detección
# ---------------------------------------------------------------------------
def is_opencode_available() -> bool:
    """Devuelve True si `opencode` está en PATH."""
    return shutil.which("opencode") is not None or shutil.which("opencode.exe") is not None


def get_opencode_version() -> Optional[str]:
    """Devuelve la versión instalada de opencode, o None si no está."""
    bin_name = "opencode.exe" if os.name == "nt" else "opencode"
    bin_path = shutil.which(bin_name) or shutil.which("opencode")
    if not bin_path:
        return None
    try:
        r = subprocess.run(
            [bin_path, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return (r.stdout or r.stderr).strip().split("\n")[0]
    except Exception as e:
        log.debug(f"opencode --version falló: {e}")
        return None


# ---------------------------------------------------------------------------
# Sesiones
# ---------------------------------------------------------------------------
def _load_sessions() -> List[Dict[str, Any]]:
    if not SESSIONS_DIR.exists():
        return []
    out = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                out.append(json.load(fp))
        except Exception:
            continue
    return out


def _save_session(session_id: str, data: Dict[str, Any]) -> None:
    fp = SESSIONS_DIR / f"{session_id}.json"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _new_session(label: str = "") -> str:
    sid = uuid.uuid4().hex[:12]
    _save_session(sid, {
        "id": sid,
        "label": label or f"opencode-{time.strftime('%Y%m%d-%H%M%S')}",
        "created_at": time.time(),
        "last_used": time.time(),
        "messages": [],
        "status": "active",
    })
    return sid


# ---------------------------------------------------------------------------
# Invocación
# ---------------------------------------------------------------------------
def _resolve_binary() -> Optional[str]:
    for name in ("opencode", "opencode.exe", "opencode.cmd", "opencode.bat"):
        p = shutil.which(name)
        if p:
            return p
    return None


def opencode_run(
    prompt: str,
    *,
    working_dir: Optional[str] = None,
    model: Optional[str] = None,
    session_id: Optional[str] = None,
    timeout: int = 120,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Lanza una invocación one-shot a opencode con un prompt.
    Devuelve: {ok, session_id, output, error, duration_s}
    """
    bin_path = _resolve_binary()
    if not bin_path:
        return {
            "ok": False,
            "error": "opencode no está instalado. Instálalo desde https://github.com/opencode-ai/opencode y vuelve a intentar.",
            "install_hint": "npm i -g opencode-ai  # o descarga binario desde github",
        }

    args = [bin_path]
    if model:
        args += ["--model", model]
    if session_id:
        args += ["--session", session_id]
    args += ["run"]
    if extra_args:
        args += list(extra_args)

    cwd = working_dir or os.getcwd()
    t0 = time.time()
    try:
        proc = subprocess.run(
            args,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding="utf-8",
            errors="replace",
        )
        duration = round(time.time() - t0, 2)
        ok = proc.returncode == 0
        out = {
            "ok": ok,
            "session_id": session_id or _new_session(prompt[:50]),
            "output": proc.stdout or "",
            "error": proc.stderr or "",
            "returncode": proc.returncode,
            "duration_s": duration,
            "working_dir": cwd,
        }

        # Persistir sesión
        if ok or proc.stdout:
            sid = out["session_id"]
            sess_fp = SESSIONS_DIR / f"{sid}.json"
            sess = {
                "id": sid,
                "created_at": time.time(),
                "last_used": time.time(),
                "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": proc.stdout}],
                "status": "completed" if ok else "error",
            }
            sess_fp.write_text(json.dumps(sess, ensure_ascii=False, indent=2), encoding="utf-8")

        return out
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"opencode timeout después de {timeout}s", "timeout": timeout}
    except FileNotFoundError:
        return {"ok": False, "error": f"opencode binario no encontrado en {bin_path}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def opencode_sessions_list() -> List[Dict[str, Any]]:
    return _load_sessions()


def opencode_session_get(session_id: str) -> Optional[Dict[str, Any]]:
    fp = SESSIONS_DIR / f"{session_id}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def opencode_session_resume(session_id: str, prompt: str, *, model: Optional[str] = None, timeout: int = 120) -> Dict[str, Any]:
    """Continúa una sesión existente con un nuevo mensaje."""
    sess = opencode_session_get(session_id)
    if not sess:
        return {"ok": False, "error": f"sessão {session_id} não existe"}

    # Construir contexto acumulado de la sesión
    context = "\n\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in sess.get("messages", [])[-10:]  # últimas 10 para no explotar
    )
    full_prompt = f"CONTEXTO DE LA SESIÓN PREVIA:\n{context}\n\nNUEVA INSTRUCCIÓN:\n{prompt}"

    return opencode_run(full_prompt, model=model, session_id=session_id, timeout=timeout)


# ---------------------------------------------------------------------------
# Wrappers de alto nivel para tareas comunes
# ---------------------------------------------------------------------------
def opencode_code_review(file_path: str, *, focus: Optional[str] = None) -> Dict[str, Any]:
    """Pide a opencode que revise un archivo y devuelva sugerencias."""
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"Archivo no existe: {file_path}"}
    code = Path(file_path).read_text(encoding="utf-8", errors="replace")[:50000]
    prompt = (
        f"Revisa este código y dame un análisis profesional:\n"
        f"- Bugs y vulnerabilidades\n- Mejoras de diseño\n- Sugerencias de performance\n- Estilo y legibilidad\n"
    )
    if focus:
        prompt += f"\nFoco especial: {focus}\n"
    prompt += f"\n```\n{code}\n```\n\nDevuelve un reporte estructurado en Markdown."
    return opencode_run(prompt, working_dir=str(Path(file_path).parent))


def opencode_generate_tests(file_path: str, framework: str = "pytest") -> Dict[str, Any]:
    """Pide a opencode que genere tests para un archivo."""
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"Archivo no existe: {file_path}"}
    code = Path(file_path).read_text(encoding="utf-8", errors="replace")[:30000]
    prompt = (
        f"Genera tests unitarios completos en {framework} para este código. "
        f"Cubre casos normales, edge cases y errores. Devuelve SOLO el código de los tests, "
        f"sin explicaciones, envuelto en bloque de código.\n\n```\n{code}\n```"
    )
    return opencode_run(prompt, working_dir=str(Path(file_path).parent))


def opencode_refactor(file_path: str, instruction: str) -> Dict[str, Any]:
    """Pide a opencode que refactorice un archivo según una instrucción."""
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"Archivo no existe: {file_path}"}
    code = Path(file_path).read_text(encoding="utf-8", errors="replace")[:30000]
    prompt = (
        f"Refactoriza este código aplicando: {instruction}\n\n"
        f"Devuelve el código completo refactorizado envuelto en bloque. "
        f"NO modifiques funcionalidad, solo estructura/estilo/claridad.\n\n```\n{code}\n```"
    )
    return opencode_run(prompt, working_dir=str(Path(file_path).parent))


def opencode_explain(file_path: str, *, level: str = "intermediate") -> Dict[str, Any]:
    """Pide a opencode que explique un archivo en español."""
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"Archivo no existe: {file_path}"}
    code = Path(file_path).read_text(encoding="utf-8", errors="replace")[:30000]
    level_es = {"beginner": "principiante", "intermediate": "intermedio", "expert": "experto"}.get(level, "intermedio")
    prompt = (
        f"Explica este código en español a nivel {level_es}. "
        f"Estructura: 1) Propósito general, 2) Flujo principal, 3) Funciones clave, "
        f"4) Dependencias, 5) Posibles problemas. Sé conciso.\n\n```\n{code}\n```"
    )
    return opencode_run(prompt, working_dir=str(Path(file_path).parent))


def opencode_generate_from_spec(spec: str, *, language: str = "python", output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Pide a opencode que genere código desde una especificación en lenguaje natural."""
    prompt = (
        f"Genera un archivo en {language} que implemente:\n\n{spec}\n\n"
        f"Devuelve SOLO el código en un bloque. Sin explicaciones. "
        f"Comenta las partes importantes. Usa buenas prácticas."
    )
    return opencode_run(prompt, working_dir=output_dir)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("opencode disponible:", is_opencode_available())
    print("versión:", get_opencode_version())
    if is_opencode_available():
        # Test rápido
        result = opencode_run("echo 'hello from automyx'")
        print("test run:", result.get("ok"), "salida:", result.get("output", "")[:200])
