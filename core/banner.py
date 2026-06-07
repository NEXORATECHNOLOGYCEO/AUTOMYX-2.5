"""
AUTOMYX BANNER v2.0
===================
Banner rediseñado con el sistema terminal.py.
Logo AUTOMYX grande, árbol de capacidades, tabla de estado.
"""
from __future__ import annotations

import time
import os
from typing import Optional

try:
    from .terminal import (
        banner as _banner,
        banner_compact,
        success as _success,
        info as _info,
        warn as _warn,
        error as _error,
        step as _step,
        panel as _panel,
        tree as _tree,
        table as _table,
        BRAND_CYAN, BRAND_YELLOW, BRAND_GREEN, BRAND_MAGENTA, BRAND_GRAY,
        ASCII_LOGO, ASCII_LOGO_COMPACT, ASCII_LOGO_MINI,
        RICH_AVAILABLE, console,
    )
except ImportError:
    from core.terminal import (
        banner as _banner, banner_compact, success as _success, info as _info,
        warn as _warn, error as _error, step as _step, panel as _panel, tree as _tree,
        table as _table, BRAND_CYAN, BRAND_YELLOW, BRAND_GREEN, BRAND_MAGENTA, BRAND_GRAY,
        ASCII_LOGO, ASCII_LOGO_COMPACT, ASCII_LOGO_MINI, RICH_AVAILABLE, console,
    )


def print_automyx_banner(
    model_name: str = "automyx",
    show_details: bool = True,
    *,
    version: str = "2.5.0",
    provider: Optional[str] = None,
    agent_count: int = 1,
    skill_count: int = 18,
    tool_count: int = 275,
    channels: Optional[list] = None,
) -> None:
    """
    Imprime el banner principal de AUTOMYX.
    - Logo AUTOMYX grande
    - Subtítulo con versión + modelo
    - Si show_details: árbol de capacidades + tabla de inventario
    """
    try:
        # 1) Banner principal con logo
        subtitle_parts = [f"v{version}"]
        if provider:
            subtitle_parts.append(provider)
        subtitle_parts.append("Gateway Omnipotente")
        _banner(
            "",
            subtitle="  ·  ".join(subtitle_parts),
            ascii_logo=True,
            width=110,
        )
        print() if not RICH_AVAILABLE else None

        # 2) Información del modelo activo
        if model_name:
            try:
                from rich.text import Text
                t = Text()
                t.append("  Modelo activo: ", style=BRAND_GRAY)
                t.append(model_name, style=f"bold {BRAND_CYAN}")
                if provider:
                    t.append(f"  ({provider})", style=BRAND_GRAY)
                if RICH_AVAILABLE and console:
                    console.print(t)
                else:
                    print(f"  Modelo activo: {model_name}")
            except Exception:
                print(f"  Modelo activo: {model_name}")
            print() if not RICH_AVAILABLE else None

        if not show_details:
            return

        # 3) Árbol de capacidades
        _tree(
            "Capacidades de AUTOMYX",
            {
                "Chat & Razonamiento": [
                    "Multi-modelo (OpenAI, Anthropic, NVIDIA, Ollama local)",
                    "Streaming de respuestas",
                    "Memoria persistente (RAG vector + SQLite)",
                    "Sistema de auto-mejora por errores",
                ],
                "Productividad": [
                    "280+ herramientas registradas",
                    "Ejecución de comandos del sistema",
                    "Lectura/escritura de archivos",
                    "Búsqueda web profunda",
                ],
                "Multimedia": [
                    "Edición de video FFmpeg (estilos MrBeast, Cinematic, etc)",
                    "Renderizado 3D con Blender",
                    "Audio mastering profesional",
                    "OBS livestreaming",
                ],
                "Desarrollo": [
                    "Generación de código desde especificación",
                    "Code review automático",
                    "Test runner",
                    "OpenCode CLI bridge (sub-agente)",
                ],
                "Conocimiento": [
                    "Búsqueda arXiv/PubMed/Semantic Scholar",
                    "OSINT y auditoría de seguridad",
                    "Contabilidad multi-país (AR/MX/PE/CO/ES)",
                    "Swarm orchestrator multi-instancia",
                ],
                "Canales": [
                    "Web dashboard (SPA)",
                    "WebSocket gateway",
                    "Telegram bot",
                    "WhatsApp (en desarrollo)",
                ],
            },
        )
        print() if not RICH_AVAILABLE else None

        # 4) Tabla de inventario
        _table(
            "Inventario del sistema",
            ["Categoría", "Cantidad", "Estado"],
            [
                ["Agentes registrados", str(agent_count), "OK"],
                ["Skills disponibles", str(skill_count), "OK"],
                ["Tools registradas", str(tool_count), "OK"],
                ["Canales activos", str(len(channels) if channels else 1), "OK"],
                ["Versión", version, "STABLE"],
            ],
            styles=[BRAND_CYAN, BRAND_YELLOW, BRAND_GREEN],
        )
        print() if not RICH_AVAILABLE else None

    except Exception as e:
        # Fallback extremo: print plano
        print(ASCII_LOGO)
        print(f"AUTOMYX v{version} - {model_name}")
        print(f"Tools: {tool_count} | Skills: {skill_count}")
        print(f"Error decorando banner: {e}")


def print_startup_sequence() -> None:
    """Secuencia de arranque rápida (boot)."""
    _banner_compact_fallback = lambda: print(f"{ASCII_LOGO_MINI}")
    if RICH_AVAILABLE and console:
        from rich.text import Text
        t = Text()
        t.append("AUTOMYX", style=f"bold {BRAND_CYAN}")
        t.append(" iniciando", style=BRAND_GRAY)
        console.print(t)
    else:
        print("AUTOMYX iniciando")


if __name__ == "__main__":
    print_automyx_banner(
        model_name="openai/gpt-oss-120b",
        show_details=True,
        version="2.5.0",
        provider="nvidia",
        agent_count=1,
        skill_count=18,
        tool_count=275,
        channels=["web", "telegram"],
    )
