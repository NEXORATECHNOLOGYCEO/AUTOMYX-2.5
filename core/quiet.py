"""
AUTOMYX Quiet Mode v1.0
=======================
Silencia los logs internos del agente para que el REPL se vea profesional
(estilo Claude Code). Por defecto esta TODO silenciado, excepto:
  - Spinner activo
  - Output final del LLM
  - Errores graves
  - Mensajes de permisos/confirmaciones

Para activar el modo verbose: AUTOMYX_VERBOSE=1
Para modo super silencioso (solo spinner + output): AUTOMYX_QUIET=1 (default)

Uso:
    from core.quiet import quiet, verbose, is_quiet, is_verbose
    quiet()  # silencia todos los loggers y prints de INFO
    verbose()  # restaura el modo normal
"""
from __future__ import annotations

import os
import sys
import io
import logging
import contextlib
from typing import Optional


# ---------------------------------------------------------------------------
# Forzar UTF-8 para que Rich no truene con cp1252 en Windows
# ---------------------------------------------------------------------------
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# Variables de entorno
ENV_VERBOSE = "AUTOMYX_VERBOSE"
ENV_QUIET = "AUTOMYX_QUIET"


def is_verbose() -> bool:
    return os.environ.get(ENV_VERBOSE, "0") == "1"


def is_quiet() -> bool:
    # Por defecto: quiet = True (silenciado)
    if os.environ.get(ENV_QUIET, "1") == "0":
        return False
    return True


# ---------------------------------------------------------------------------
# Silenciador de logging
# ---------------------------------------------------------------------------
_LOGGERS_TO_SILENCE = [
    "Agent",
    "automyx",
    "urllib3",
    "httpx",
    "httpcore",
    "numexpr.utils",
    "tools.mega_tools",
    "OpenAI",
    "openai",
]

# Patrones de mensajes a silenciar incluso si se imprimen (logs de import, etc.)
_NOISY_PRINT_PATTERNS = [
    "inicializado",
    "cargado",
    "cargadas",
    "✅",
    "compatible con",
    "disponible",
    "renderizado",
    "iniciado",
]


def _apply_logging_level(level: int) -> None:
    """Aplica un nivel de logging a todos los loggers ruidosos."""
    for name in _LOGGERS_TO_SILENCE:
        try:
            lg = logging.getLogger(name)
            lg.setLevel(level)
            lg.propagate = False
        except Exception:
            pass
    # Tambien el root logger para librerias externas
    try:
        logging.getLogger().setLevel(level)
    except Exception:
        pass


# Estado global: un StringIO que captura stdout si estamos en quiet
_silent_buffer: Optional[io.StringIO] = None
_real_stdout = None
_real_stderr = None
_silent_active = False
_real_print = None
_patched_print = False


def _should_silent_print(text: str) -> bool:
    """Decide si un print debe silenciarse en quiet mode."""
    if not text:
        return True
    text_lower = text.lower()
    return any(pat in text_lower for pat in _NOISY_PRINT_PATTERNS)


def _quiet_print(*args, **kwargs):
    """Wrapper de print que filtra mensajes ruidosos."""
    text = " ".join(str(a) for a in args)
    if _should_silent_print(text):
        return
    if _real_print:
        _real_print(*args, **kwargs)


def silence_stdout() -> None:
    """Redirige stdout/stderr a un buffer vacio (para quiet mode total)."""
    global _silent_buffer, _real_stdout, _real_stderr, _silent_active
    if _silent_active:
        return
    _real_stdout = sys.stdout
    _real_stderr = sys.stderr
    _silent_buffer = io.StringIO()
    sys.stdout = _silent_buffer
    sys.stderr = _silent_buffer
    _silent_active = True


def restore_stdout() -> None:
    """Restaura stdout/stderr a su valor original."""
    global _silent_active
    if not _silent_active:
        return
    sys.stdout = _real_stdout or sys.__stdout__
    sys.stderr = _real_stderr or sys.__stderr__
    _silent_active = False


@contextlib.contextmanager
def silent():
    """Context manager que silencia stdout/stderr temporalmente."""
    was_active = _silent_active
    if not was_active:
        silence_stdout()
    try:
        yield
    finally:
        if not was_active:
            restore_stdout()


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------
def quiet() -> None:
    """Activa el modo silencioso: solo se ven los prints/spinners del REPL."""
    global _real_print, _patched_print
    os.environ[ENV_QUIET] = "1"
    os.environ[ENV_VERBOSE] = "0"
    # Silenciar loggers
    _apply_logging_level(logging.CRITICAL)
    # Capturar warnings de Python
    logging.captureWarnings(True)
    # Reemplazar print/log de las funciones ruidosas en runtime
    _patch_noisy_modules()
    # Patchear print global para filtrar mensajes de import/carga
    if not _patched_print:
        import builtins
        _real_print = builtins.print
        builtins.print = _quiet_print
        _patched_print = True


def verbose() -> None:
    """Activa el modo verbose: todo se muestra como antes."""
    global _patched_print
    os.environ[ENV_QUIET] = "0"
    os.environ[ENV_VERBOSE] = "1"
    _apply_logging_level(logging.INFO)
    # Restaurar print original
    if _patched_print:
        import builtins
        builtins.print = _real_print
        _patched_print = False


# ---------------------------------------------------------------------------
# Monkey-patching de funciones ruidosas
# ---------------------------------------------------------------------------
_patched = False


def _patch_noisy_modules() -> None:
    """
    Reemplaza las funciones que imprimen mensajes internos ruidosos por
    equivalentes silenciosas. Asi no tenemos que modificar cada modulo.
    """
    global _patched
    if _patched:
        return
    _patched = True

    # 1) Patching de core.terminal: las funciones info/warn/debug/llm_thinking
    #    solo imprimen en modo verbose. El REPL intercepta el progreso via
    #    progress_callback, por lo que silenciamos tambien tool_executing/result.
    try:
        from core import terminal as term

        def _silent(*args, **kwargs):
            """No-op silencioso que acepta cualquier firma."""
            return None

        # En quiet mode silenciamos todo el output interno.
        # El REPL muestra su propio output formateado via progress_callback.
        term.info = _silent
        term.warn = _silent
        term.debug = _silent
        term.llm_thinking = _silent
        term.success = _silent
        term.tool_executing = _silent
        term.tool_result = _silent
        term.tool_loop_warning = _silent
        term.render_plan = _silent
        term.render_flow_schema = _silent
        term.render_parallel_groups = _silent
        term.render_plan_summary = _silent
        term.multitask_status = _silent
        term.print_json = _silent
        term.print_markdown = _silent
        term.print_code = _silent
        # Mantener term.error y term.tool_loop_warning para errores graves
    except Exception:
        pass

    # 2) Patching del logger de core.agent
    try:
        logger = logging.getLogger("Agent")
        logger.handlers = []  # quitar handlers
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
    except Exception:
        pass

    # 3) Patching de tools.* que tengan prints/INFOs
    try:
        import tools.mega_tools as mt
        if hasattr(mt, "logger"):
            mt.logger.setLevel(logging.CRITICAL)
    except Exception:
        pass

    # 4) Silenciar urllib3/httpx/httpcore verbose
    for name in ["urllib3", "httpx", "httpcore"]:
        try:
            logging.getLogger(name).setLevel(logging.CRITICAL)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Inicializacion automatica: si la variable AUTOMYX_QUIET esta en '1'
# (default), activar quiet mode al importar.
# ---------------------------------------------------------------------------
def init_from_env() -> None:
    """Inicializa el modo segun las variables de entorno."""
    if is_verbose():
        verbose()
    else:
        quiet()


# Auto-init al importar (a menos que se importe explicitamente para configurar)
init_from_env()
