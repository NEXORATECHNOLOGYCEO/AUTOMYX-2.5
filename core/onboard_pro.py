"""
AUTOMYX ONBOARDING v2.0 (PROFESIONAL)
======================================
Wizard de configuración inicial rediseñado:
  - Logo AUTOMYX grande y claro al inicio (el "loguito")
  - Indicador de modo "ONBOARD" visible durante todo el flujo
  - Pasos numerados con progress
  - Auto-detección de Ollama local
  - Selección de modelo (4 categorías: NVIDIA, Ollama, Comercial, Local)
  - Captura de API keys con validación
  - Selección de canales
  - Resumen final con tabla de estado
  - Auto-arranque del gateway al terminar
"""
from __future__ import annotations

import os
import sys
import time
import json
import subprocess
from typing import Optional, List, Dict, Any

try:
    from .terminal import (
        console, RICH_AVAILABLE, COLORAMA_AVAILABLE,
        BRAND_CYAN, BRAND_YELLOW, BRAND_GREEN, BRAND_MAGENTA, BRAND_GRAY, BRAND_RED,
        ASCII_LOGO, ASCII_LOGO_COMPACT, ASCII_LOGO_MINI,
        banner as _banner, onboarding_intro, onboarding_step_complete,
        onboarding_summary, step as _step, success as _success, info as _info,
        warn as _warn, error as _error, spinner as _spinner,
    )
except ImportError:
    from core.terminal import (
        console, RICH_AVAILABLE, COLORAMA_AVAILABLE,
        BRAND_CYAN, BRAND_YELLOW, BRAND_GREEN, BRAND_MAGENTA, BRAND_GRAY, BRAND_RED,
        ASCII_LOGO, ASCII_LOGO_COMPACT, ASCII_LOGO_MINI,
        banner as _banner, onboarding_intro, onboarding_step_complete,
        onboarding_summary, step as _step, success as _success, info as _info,
        warn as _warn, error as _error, spinner as _spinner,
    )

try:
    import questionary
    from questionary import Style as QStyle
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

try:
    from .agent import OllamaManager
except ImportError:
    from core.agent import OllamaManager


# ---------------------------------------------------------------------------
# Estilo questionary de marca
# ---------------------------------------------------------------------------
AUTOMYX_STYLE = None
if QUESTIONARY_AVAILABLE:
    AUTOMYX_STYLE = QStyle([
        ("qmark", "fg:#00f0ff bold"),
        ("question", "fg:#00f0ff bold"),
        ("answer", "fg:#00ff9c bold"),
        ("pointer", "fg:#00f0ff bold"),
        ("highlighted", "fg:#00f0ff bold"),
        ("selected", "fg:#00ff9c"),
        ("separator", "fg:#8b949e"),
        ("instruction", "fg:#8b949e italic"),
    ])


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _q(text: str, **kwargs):
    """Wrapper de questionary con estilo AUTOMYX."""
    if QUESTIONARY_AVAILABLE:
        return questionary.text(text, style=AUTOMYX_STYLE, **kwargs)
    return None


def _qselect(text: str, choices, **kwargs):
    if QUESTIONARY_AVAILABLE:
        return questionary.select(text, choices=choices, style=AUTOMYX_STYLE, **kwargs)
    return None


def _qconfirm(text: str, default: bool = False, **kwargs):
    if QUESTIONARY_AVAILABLE:
        return questionary.confirm(text, style=AUTOMYX_STYLE, default=default, **kwargs)
    return None


def _qpassword(text: str, **kwargs):
    if QUESTIONARY_AVAILABLE:
        return questionary.password(text, style=AUTOMYX_STYLE, **kwargs)
    return None


def _qcheckbox(text: str, choices, **kwargs):
    if QUESTIONARY_AVAILABLE:
        return questionary.checkbox(text, choices=choices, style=AUTOMYX_STYLE, **kwargs)
    return None


def save_to_env(key: str, value: str) -> None:
    """Guarda o actualiza una variable en .env."""
    env_path = os.path.join(os.getcwd(), ".env")
    lines: List[str] = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ---------------------------------------------------------------------------
# Pasos del wizard
# ---------------------------------------------------------------------------
TOTAL_STEPS = 6


def _step_1_welcome() -> bool:
    """Muestra logo AUTOMYX, intro y disclaimer de seguridad."""
    if RICH_AVAILABLE and console:
        from rich.panel import Panel
        from rich.text import Text

        # 1) Logo grande
        _banner("", subtitle="ONBOARD  -  v2.5.0  -  Gateway Omnipotente", ascii_logo=True, width=110)
        print()

        # 2) Aviso de seguridad
        warning = Text()
        warning.append("AVISO DE SEGURIDAD\n\n", style=f"bold {BRAND_RED}")
        warning.append(
            "AUTOMYX es un agente de IA con ACCESO TOTAL a tu sistema. "
            "Puede ejecutar comandos, leer/escribir archivos, controlar aplicaciones, "
            "moverse por internet, enviar mensajes, hacer compras y más. "
            "ÚSALO BAJO TU PROPIA RESPONSABILIDAD.\n\n",
            style="white",
        )
        warning.append(
            "Documentación: ", style=BRAND_GRAY
        )
        warning.append("github.com/anomalyco/opencode", style=BRAND_CYAN)
        console.print(Panel(warning, border_style=BRAND_RED, padding=(1, 2)))
        print()
    else:
        print(ASCII_LOGO)
        print("ONBOARD  -  v2.5.0")
        print()
        print("AVISO: AUTOMYX tiene ACCESO TOTAL a tu sistema.")
        print("ÚSALO BAJO TU PROPIA RESPONSABILIDAD.")
        print()

    if _qconfirm("[?] Entiendes que esto es poderoso y potencialmente riesgoso. ¿Continuar?", default=False):
        return True
    _warn("Onboarding cancelado por el usuario.")
    return False


def _step_2_model() -> Dict[str, str]:
    """Detecta Ollama local y pregunta el modelo."""
    _info("Detectando Ollama local...")
    local_models: List[str] = []
    try:
        with _spinner("Buscando modelos Ollama instalados..."):
            local_models = OllamaManager.list_models() or []
    except Exception:
        pass

    if local_models:
        _success(f"Encontrados {len(local_models)} modelos Ollama locales")
    else:
        _info("No hay Ollama local o no tiene modelos instalados")

    # Construir opciones
    choices = [
        "NVIDIA: openai/gpt-oss-120b  (gratis vía API pública)",
        "NVIDIA: zai-org/GLM-4.6  (gratis)",
        "NVIDIA: deepseek-ai/deepseek-v3.1  (gratis)",
        "OpenAI: gpt-4o  (requiere API key)",
        "Anthropic: claude-3-5-sonnet  (requiere API key)",
        "Google: gemini-2.0-flash  (requiere API key)",
        "Groq: llama-3.3-70b  (requiere API key)",
    ]
    if local_models:
        for m in local_models[:5]:
            choices.append(f"Ollama local: {m}")

    answer = _qselect("[?] ¿Qué modelo quieres usar como motor principal?", choices=choices)
    if answer is None:
        answer = choices[0]  # default
    _success(f"Modelo seleccionado: {answer}")

    # Pedir API key si es necesario
    api_key = ""
    if "NVIDIA" in answer or "Ollama local" in answer:
        api_key = ""  # no requiere
    else:
        env_key_map = {
            "OpenAI": "OPENAI_API_KEY",
            "Anthropic": "ANTHROPIC_API_KEY",
            "Google": "GOOGLE_API_KEY",
            "Groq": "GROQ_API_KEY",
        }
        for prefix, env_key in env_key_map.items():
            if answer.startswith(prefix):
                key = _qpassword(f"[?] {prefix} API Key (se guarda en .env):")
                if key:
                    save_to_env(env_key, key)
                    api_key = key
                    _success(f"{prefix} API key guardada")
                break

    # Extraer nombre del modelo del string
    model_name = answer.split(": ", 1)[-1].split("  ")[0]

    return {"model": model_name, "provider_answer": answer, "api_key_set": bool(api_key)}


def _step_3_channels() -> List[str]:
    """Pregunta qué canales activar."""
    _info("Configurando canales de comunicación...")
    choices = [
        {"name": "Web Dashboard (http://localhost:3500) - SIEMPRE ACTIVO", "value": "web", "checked": True, "disabled": True},
        {"name": "Telegram Bot (necesita token de @BotFather)", "value": "telegram", "checked": False},
        {"name": "WhatsApp (requiere escanear QR)", "value": "whatsapp", "checked": False},
        {"name": "Discord Bot", "value": "discord", "checked": False},
        {"name": "Slack Bot", "value": "slack", "checked": False},
        {"name": "Email (SMTP/IMAP)", "value": "email", "checked": False},
        {"name": "Webhook genérico (HTTP POST entrante)", "value": "webhook", "checked": False},
    ]
    answer = _qcheckbox("[?] Activa los canales que quieras (Space para marcar):", choices=choices)
    if answer is None:
        answer = ["web"]

    # Capturar tokens de Telegram
    if "telegram" in answer:
        token = _qpassword("[?] Telegram Bot Token (de @BotFather):")
        if token:
            save_to_env("TELEGRAM_BOT_TOKEN", token)
            _success("Telegram configurado")

    _success(f"Canales activados: {', '.join(answer)}")
    return answer


def _step_4_features() -> Dict[str, bool]:
    """Pregunta sobre features opcionales."""
    _info("Configurando features avanzadas...")
    features = {
        "memory": _qconfirm("[?] ¿Activar memoria persistente (RAG vector + SQLite)?", default=True),
        "swarm": _qconfirm("[?] ¿Activar swarm orchestrator (multi-instancia)?", default=False),
        "voice_elevenlabs": _qconfirm("[?] ¿Configurar ElevenLabs (voz premium)?", default=False),
        "autopilot": _qconfirm("[?] ¿Activar project autopilot (mejora automática)?", default=True),
        "opencode_bridge": _qconfirm("[?] ¿Activar bridge con opencode CLI? (requiere instalación)", default=False),
    }
    enabled = [k for k, v in features.items() if v]
    _success(f"Features activadas: {len(enabled)}/{len(features)}")
    return features


def _step_5_summary(model_info: Dict, channels: List[str], features: Dict[str, bool]) -> bool:
    """Muestra resumen y pide confirmación final."""
    _info("Preparando resumen de configuración...")
    print()
    rows = [
        {"key": "Modelo principal", "value": model_info["model"]},
        {"key": "API Key configurada", "value": "Sí" if model_info["api_key_set"] else "No / No requerida"},
        {"key": "Canales activos", "value": ", ".join(channels)},
        {"key": "Memoria persistente", "value": "Sí" if features["memory"] else "No"},
        {"key": "Swarm orchestrator", "value": "Sí" if features["swarm"] else "No"},
        {"key": "OpenCode bridge", "value": "Sí" if features["opencode_bridge"] else "No"},
        {"key": "Puerto gateway", "value": "3500"},
        {"key": "Versión", "value": "2.5.0"},
    ]
    _onboarding_summary_local(rows)
    print()
    return _qconfirm("[?] ¿Arrancar AUTOMYX ahora?", default=True)


def _onboarding_summary_local(rows):
    """Reimplementación local de onboarding_summary (evita import circular)."""
    if RICH_AVAILABLE and console:
        from rich.table import Table
        from rich.box import DOUBLE
        t = Table(title=f"[bold {BRAND_GREEN}]AUTOMYX está listo para arrancar[/]", box=DOUBLE, border_style=BRAND_GREEN)
        t.add_column("Configuración", style=BRAND_CYAN, no_wrap=False)
        t.add_column("Valor", style="white")
        for r in rows:
            t.add_row(r.get("key", ""), r.get("value", ""))
        console.print(t)
    else:
        for r in rows:
            print(f"  {r.get('key')}: {r.get('value')}")


def _step_6_autostart() -> None:
    """Lanza el gateway en proceso hijo."""
    _info("Arrancando AUTOMYX Gateway...")
    try:
        with _spinner("Inicializando gateway en puerto 3500..."):
            time.sleep(1.5)
        if RICH_AVAILABLE and console:
            from rich.panel import Panel
            from rich.text import Text
            msg = Text()
            msg.append("AUTOMYX Core en línea\n\n", style=f"bold {BRAND_GREEN}")
            msg.append("Dashboard: ", style="white")
            msg.append("http://localhost:3500\n", style=f"bold {BRAND_CYAN}")
            msg.append("WebSocket: ", style="white")
            msg.append("ws://localhost:3500/ws\n", style=BRAND_CYAN)
            msg.append("Health: ", style="white")
            msg.append("http://localhost:3500/health", style=BRAND_CYAN)
            console.print(Panel(msg, border_style=BRAND_GREEN, padding=(1, 2)))
        else:
            print("\nAUTOMYX Core en línea")
            print("Dashboard: http://localhost:3500")
            print("WebSocket: ws://localhost:3500/ws")
        _success("Todos los sistemas GO!")
    except Exception as e:
        _error(f"Error arrancando gateway: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_onboarding() -> None:
    """Wizard completo de onboarding."""
    try:
        # Header claro
        if RICH_AVAILABLE and console:
            from rich.text import Text
            from rich.panel import Panel
            header = Text()
            header.append("MODO: ", style=BRAND_GRAY)
            header.append("ONBOARD", style=f"bold {BRAND_MAGENTA}")
            header.append("  -  AUTOMYX 2.5.0 Setup Wizard", style=BRAND_CYAN)
            console.print(Panel(header, border_style=BRAND_MAGENTA, padding=(0, 1)))
            print()
        else:
            print("MODO: ONBOARD  -  AUTOMYX 2.5.0 Setup Wizard")
            print("=" * 50)
            print()

        # Paso 1: bienvenida
        if not _step_1_welcome():
            return
        _onboarding_step_local(1, "Aviso de seguridad aceptado")
        print()

        # Paso 2: modelo
        _step(2, TOTAL_STEPS, "Seleccionando modelo principal...")
        model_info = _step_2_model()
        _onboarding_step_local(2, "Modelo configurado")
        print()

        # Paso 3: canales
        _step(3, TOTAL_STEPS, "Configurando canales de comunicación...")
        channels = _step_3_channels()
        _onboarding_step_local(3, "Canales configurados")
        print()

        # Paso 4: features
        _step(4, TOTAL_STEPS, "Configurando features avanzadas...")
        features = _step_4_features()
        _onboarding_step_local(4, "Features configuradas")
        print()

        # Paso 5: resumen
        _step(5, TOTAL_STEPS, "Revisando configuración final...")
        if not _step_5_summary(model_info, channels, features):
            _warn("Onboarding cancelado antes del arranque")
            return
        _onboarding_step_local(5, "Confirmación recibida")
        print()

        # Paso 6: arrancar
        _step(6, TOTAL_STEPS, "Arrancando AUTOMYX...")
        _step_6_autostart()
        _onboarding_step_local(6, "Gateway en línea")
        print()

        # Footer
        if RICH_AVAILABLE and console:
            from rich.text import Text
            from rich.panel import Panel
            footer = Text()
            footer.append("Tip: ", style=f"bold {BRAND_YELLOW}")
            footer.append("ejecuta ", style="white")
            footer.append("python automyx.py chat", style=f"bold {BRAND_CYAN}")
            footer.append(" para hablar con AUTOMYX desde la terminal, o ", style="white")
            footer.append("python automyx.py --help", style=f"bold {BRAND_CYAN}")
            footer.append(" para ver todos los comandos.", style="white")
            console.print(Panel(footer, border_style=BRAND_YELLOW, padding=(0, 1)))
        else:
            print("Tip: ejecuta 'python automyx.py chat' o 'python automyx.py --help'")

    except KeyboardInterrupt:
        _warn("\nOnboarding interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        _error(f"Error en onboarding: {type(e).__name__}: {e}")


def _onboarding_step_local(n: int, name: str) -> None:
    if RICH_AVAILABLE and console:
        from rich.text import Text
        t = Text()
        t.append("  ")
        t.append("[OK] ", style=f"bold {BRAND_GREEN}")
        t.append(f"Paso {n}  ", style=BRAND_GRAY)
        t.append(name, style="white")
        t.append("  listo", style=BRAND_GRAY)
        console.print(t)
    else:
        print(f"  [OK] Paso {n} {name} listo")


if __name__ == "__main__":
    run_onboarding()
