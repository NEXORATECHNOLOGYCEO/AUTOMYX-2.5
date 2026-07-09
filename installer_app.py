#!/usr/bin/env python3
"""
AUTOMYX 2.5 — Installer Wizard
================================
Este script ES el instalador. Se empaqueta con PyInstaller --onefile
junto con los archivos de Automyx en un zip embebido.

Al ejecutarse:
  1. Wizard de bienvenida en terminal
  2. Seleccionar directorio de instalación
  3. Extraer archivos con barra de progreso
  4. Crear acceso directo en Escritorio
  5. Añadir al PATH (opcional)
  6. Lanzar onboarding
"""
from __future__ import annotations

import os
import sys
import io
import shutil
import zipfile
import subprocess
import time
import threading
from pathlib import Path

# Forzar UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Rich (viene bundleado en el exe)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
    from rich.rule import Rule
    from rich.live import Live
    from rich import box as _rbox
    RICH = True
except ImportError:
    RICH = False

# ── Paleta ────────────────────────────────────────────────────────────────────
O  = "#FF8C00"
B  = "#00AAFF"
G  = "#5EE6A8"
R  = "#FF4444"
D  = "#4A6A8A"
W  = "#F0F6FF"
PU = "#A855F7"
YL = "#FFD700"

VERSION = "2.5.0"

console = Console() if RICH else None


def _clear():
    os.system("cls" if os.name == "nt" else "clear")


def _print(msg=""):
    if console:
        console.print(msg)
    else:
        print(msg)


# ── Banner ─────────────────────────────────────────────────────────────────────
def _banner():
    if not RICH:
        print(f"\n  AUTOMYX {VERSION} - Installer\n")
        return
    _clear()
    art = Text()
    art.append("\n")
    art.append("  ▄█████╗  ██╗   ██╗████████╗  ██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗\n", style=f"bold {O}")
    art.append("  ██╔══██╗ ██║   ██║╚══██╔══╝ ██╔═══██╗████╗ ████║╚██╗ ██╔╝╚██╗██╔╝\n", style=f"bold {O}")
    art.append("  ███████║ ██║   ██║   ██║    ██║   ██║██╔████╔██║ ╚████╔╝  ╚███╔╝ \n", style=f"bold {B}")
    art.append("  ██╔══██║ ██║   ██║   ██║    ██║   ██║██║╚██╔╝██║  ╚██╔╝   ██╔██╗ \n", style=f"bold {B}")
    art.append("  ██║  ██║ ╚██████╔╝   ██║    ╚██████╔╝██║ ╚═╝ ██║   ██║   ██╔╝ ██╗\n", style=f"bold {O}")
    art.append("  ╚═╝  ╚═╝  ╚═════╝    ╚═╝     ╚═════╝ ╚═╝     ╚═╝   ╚═╝   ╚═╝  ╚═╝\n", style=f"dim {O}")
    art.append("\n")
    console.print(art)

    whale = Text()
    whale.append("                         .-'\n",                            style=f"bold {B}")
    whale.append("                    '---( ()  ~  ∿  ∿  ∿\n",              style=f"bold {B}")
    whale.append("                        '-.\"∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿~\n",  style=f"bold {B}")
    whale.append("                   ~~~∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿~~~\n", style=f"dim {B}")
    whale.append(f"   \U0001f40b  Installer v{VERSION}  ·  autonomous ai agent  ·  powered by nvidia",
                 style=f"dim {D}")
    console.print(Panel(whale, border_style=B, box=_rbox.HEAVY, padding=(0, 2)))
    console.print()


# ── Encontrar zip embebido ────────────────────────────────────────────────────
def _find_bundle() -> Path | None:
    """Busca Automyx.zip — embebido via PyInstaller o junto al exe."""
    # Si está frozen (exe), sys._MEIPASS contiene los datos extraídos
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent

    candidates = [
        base / "Automyx.zip",
        base / "automyx_bundle.zip",
        Path(sys.executable).parent / "Automyx.zip",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


# ── Crear acceso directo en Escritorio (Windows) ──────────────────────────────
def _create_shortcut(exe_path: Path, shortcut_name: str = "Automyx") -> bool:
    try:
        import winreg
        desktop = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
        lnk = desktop / f"{shortcut_name}.lnk"

        # Usar PowerShell para crear el .lnk (no requiere pywin32)
        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{lnk}"); '
            f'$s.TargetPath = "{exe_path}"; '
            f'$s.WorkingDirectory = "{exe_path.parent}"; '
            f'$s.IconLocation = "{exe_path}"; '
            f'$s.Description = "Automyx 2.5 - Autonomous AI Agent"; '
            f'$s.Save()'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=10
        )
        return result.returncode == 0 and lnk.exists()
    except Exception:
        return False


def _create_startmenu_shortcut(exe_path: Path) -> bool:
    """Crea acceso directo en Menú de Inicio."""
    try:
        start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        app_folder = start_menu / "Automyx"
        app_folder.mkdir(exist_ok=True)
        lnk = app_folder / "Automyx.lnk"

        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{lnk}"); '
            f'$s.TargetPath = "{exe_path}"; '
            f'$s.WorkingDirectory = "{exe_path.parent}"; '
            f'$s.IconLocation = "{exe_path}"; '
            f'$s.Description = "Automyx 2.5 - Autonomous AI Agent"; '
            f'$s.Save()'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _add_to_path(install_dir: Path) -> bool:
    """Añade install_dir al PATH del usuario (HKCU)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Environment", 0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
        try:
            current, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current = ""
        dir_str = str(install_dir)
        if dir_str.lower() not in current.lower():
            new_path = current.rstrip(";") + ";" + dir_str
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)
        # Notificar al sistema del cambio de PATH
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             '[System.Environment]::GetEnvironmentVariable("Path","User")'],
            capture_output=True, timeout=5
        )
        return True
    except Exception:
        return False


# ── Paso 1: Bienvenida ────────────────────────────────────────────────────────
def step_welcome() -> bool:
    _banner()

    if RICH:
        welcome = Text()
        welcome.append("  Bienvenido al instalador de ", style=f"dim {W}")
        welcome.append("Automyx 2.5", style=f"bold {O}")
        welcome.append("\n\n")
        welcome.append("  Automyx es un agente de IA autónomo que funciona en tu terminal.\n", style=f"dim {W}")
        welcome.append("  Puede escribir código, buscar en la web, crear archivos,\n", style=f"dim {W}")
        welcome.append("  ejecutar proyectos y mucho más — todo desde tu teclado.\n", style=f"dim {W}")
        welcome.append("\n")
        welcome.append("  Este asistente instalará Automyx en tu PC.\n", style=f"dim {D}")
        welcome.append("  Solo necesitas una API key gratuita de NVIDIA para empezar.", style=f"dim {D}")
        console.print(Panel(
            welcome,
            title=f"[bold {B}]  Instalador de Automyx v{VERSION}  [/]",
            border_style=B,
            box=_rbox.ROUNDED,
            padding=(1, 2),
        ))
        console.print()

        try:
            choice = Confirm.ask(f"  [{O}]¿Deseas instalar Automyx en este equipo?[/{O}]", default=True)
        except (KeyboardInterrupt, EOFError):
            return False
        return choice
    else:
        print("\nBienvenido a Automyx 2.5 Installer")
        ans = input("¿Instalar? [S/n] ").strip().lower()
        return ans != "n"


# ── Paso 2: Directorio ────────────────────────────────────────────────────────
def step_directory() -> Path:
    default_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Automyx"

    _print()
    if RICH:
        console.print(Rule(f"[bold {B}]Directorio de instalación[/]", style=f"dim {D}"))
        console.print()
        console.print(f"  [{D}]Por defecto:[/{D}]  [{W}]{default_dir}[/{W}]")
        console.print()
        try:
            raw = Prompt.ask(
                f"  [{O}]Directorio[/{O}]  [{D}](Enter para usar el predeterminado)[/{D}]",
                default=str(default_dir)
            )
        except (KeyboardInterrupt, EOFError):
            raw = str(default_dir)
    else:
        print(f"\nDirectorio de instalación [{default_dir}]: ", end="")
        raw = input().strip() or str(default_dir)

    install_dir = Path(raw.strip() or str(default_dir))
    _print()
    return install_dir


# ── Paso 3: Extraer archivos ──────────────────────────────────────────────────
def step_extract(bundle: Path, install_dir: Path) -> bool:
    if RICH:
        console.print(Rule(f"[bold {B}]Instalando archivos[/]", style=f"dim {D}"))
        console.print()

    # Limpiar instalación previa si existe
    if install_dir.exists():
        if RICH:
            console.print(f"  [{YL}]Se encontró una instalación previa en:[/{YL}]")
            console.print(f"  [{W}]{install_dir}[/{W}]")
            console.print()
            try:
                overwrite = Confirm.ask(f"  [{O}]¿Sobreescribir?[/{O}]", default=True)
            except (KeyboardInterrupt, EOFError):
                overwrite = True
        else:
            overwrite = True
        if overwrite:
            shutil.rmtree(install_dir, ignore_errors=True)
        else:
            return False

    install_dir.mkdir(parents=True, exist_ok=True)

    if RICH:
        with zipfile.ZipFile(bundle, 'r') as zf:
            members = zf.namelist()
            with Progress(
                SpinnerColumn(spinner_name="dots", style=f"bold {B}"),
                TextColumn(f"[{W}]{{task.description}}[/{W}]"),
                BarColumn(bar_width=40, style=f"dim {D}", complete_style=f"bold {B}"),
                TaskProgressColumn(style=f"dim {D}"),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Extrayendo archivos...", total=len(members))
                for member in members:
                    zf.extract(member, install_dir)
                    # Mostrar nombre del archivo actual (truncado)
                    short = member[-45:] if len(member) > 45 else member
                    progress.update(task, description=f"[dim]{short}[/dim]", advance=1)
    else:
        with zipfile.ZipFile(bundle, 'r') as zf:
            zf.extractall(install_dir)

    # Crear .env si no existe
    env_file = install_dir / ".env"
    if not env_file.exists():
        env_file.write_text(
            "# Automyx 2.5 - Configuracion de API Keys\n"
            "# Edita este archivo con tu API key\n\n"
            "# NVIDIA (GRATIS - build.nvidia.com)\n"
            "NVIDIA_API_KEY=\n\n"
            "# Anthropic\n"
            "ANTHROPIC_API_KEY=\n\n"
            "# OpenAI\n"
            "OPENAI_API_KEY=\n\n"
            "AUTOMYX_MODEL=openai/gpt-oss-120b\n",
            encoding="utf-8"
        )

    if RICH:
        console.print(f"\n  [{G}]✓[/{G}]  {len(members)} archivos instalados en [{W}]{install_dir}[/{W}]")
        console.print()

    return True


# ── Paso 4: Accesos directos ──────────────────────────────────────────────────
def step_shortcuts(install_dir: Path) -> Path | None:
    """Crea accesos directos. Retorna la ruta al exe instalado."""
    exe = install_dir / "Automyx.exe"
    if not exe.exists():
        # Buscar el exe en subdirectorio
        for f in install_dir.rglob("Automyx.exe"):
            exe = f
            break

    if not exe.exists():
        if RICH:
            console.print(f"  [{YL}]No se encontró Automyx.exe en {install_dir}[/{YL}]")
        return None

    if RICH:
        console.print(Rule(f"[bold {B}]Accesos directos[/]", style=f"dim {D}"))
        console.print()

    # Escritorio
    ok_desk = _create_shortcut(exe)
    if RICH:
        icon = f"[{G}]✓[/{G}]" if ok_desk else f"[{YL}]![/{YL}]"
        status = "creado" if ok_desk else "no se pudo crear"
        console.print(f"  {icon}  Acceso directo en Escritorio — {status}")

    # Menú Inicio
    ok_start = _create_startmenu_shortcut(exe)
    if RICH:
        icon = f"[{G}]✓[/{G}]" if ok_start else f"[{YL}]![/{YL}]"
        status = "creado" if ok_start else "no se pudo crear"
        console.print(f"  {icon}  Menú de Inicio — {status}")

    console.print() if RICH else None
    return exe


# ── Paso 5: PATH ─────────────────────────────────────────────────────────────
def step_path(install_dir: Path):
    if RICH:
        try:
            add = Confirm.ask(
                f"  [{O}]¿Añadir Automyx al PATH para usar desde cualquier terminal?[/{O}]",
                default=True
            )
        except (KeyboardInterrupt, EOFError):
            add = False
    else:
        add = input("\n¿Añadir al PATH? [S/n] ").strip().lower() != "n"

    if add:
        ok_path = _add_to_path(install_dir)
        if RICH:
            icon = f"[{G}]✓[/{G}]" if ok_path else f"[{YL}]![/{YL}]"
            status = "añadido (abre un nuevo terminal para usar 'Automyx')" if ok_path else "no se pudo añadir"
            console.print(f"  {icon}  PATH — {status}")
            console.print()


# ── Paso 6: Finalización ──────────────────────────────────────────────────────
def step_done(install_dir: Path, exe: Path | None):
    if RICH:
        console.print(Rule(f"[bold {G}]Instalación completada[/]", style=f"dim {D}"))
        console.print()
        done_text = Text()
        done_text.append(f"  [{G}]✓  Automyx 2.5 instalado correctamente[/{G}]\n\n")
        done_text.append(f"  [{D}]Directorio:[/{D}]  [{W}]{install_dir}[/{W}]\n\n")
        if exe:
            done_text.append(f"  [{D}]Para iniciar:[/{D}]  doble clic en el ícono del Escritorio\n")
            done_text.append(f"  [{D}]  o ejecuta:[/{D}]  [{B}]{exe}[/{B}]\n\n")
        done_text.append(f"  [{YL}]Primer paso:[/{YL}]  [{W}]configura tu API key en {install_dir / '.env'}[/{W}]\n")
        done_text.append(f"  [{D}]API key gratuita:[/{D}]  [{B}]https://build.nvidia.com[/{B}]")
        console.print(Panel(
            done_text,
            border_style=G,
            box=_rbox.ROUNDED,
            padding=(1, 2),
        ))
        console.print()

        try:
            launch = Confirm.ask(f"  [{O}]¿Abrir Automyx ahora?[/{O}]", default=True)
        except (KeyboardInterrupt, EOFError):
            launch = False

        if launch and exe and exe.exists():
            subprocess.Popen([str(exe)], cwd=str(install_dir))
    else:
        print(f"\nInstalado en: {install_dir}")
        print("Abre una nueva terminal y escribe: Automyx")


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    # 1. Bienvenida
    if not step_welcome():
        _print(f"\n  [{D}]Instalación cancelada.[/{D}]" if RICH else "\nInstalación cancelada.")
        input("\nPresiona Enter para salir...")
        sys.exit(0)

    # 2. Directorio
    install_dir = step_directory()

    # 3. Buscar bundle
    bundle = _find_bundle()
    if not bundle:
        if RICH:
            console.print(f"\n  [{R}]Error:[/{R}]  No se encontró el paquete de Automyx.")
            console.print(f"  [{D}]Asegúrate de que Automyx.zip está junto al instalador.[/{D}]")
        else:
            print("\nError: No se encontró Automyx.zip")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    # 4. Extraer
    if not step_extract(bundle, install_dir):
        _print(f"\n  [{D}]Instalación cancelada.[/{D}]" if RICH else "\nCancelado.")
        sys.exit(0)

    # 5. Accesos directos
    exe = step_shortcuts(install_dir)

    # 6. PATH
    step_path(install_dir)

    # 7. Finalizar
    step_done(install_dir, exe)

    input("\nPresiona Enter para cerrar...")


if __name__ == "__main__":
    main()
