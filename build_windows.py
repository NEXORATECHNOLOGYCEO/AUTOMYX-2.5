#!/usr/bin/env python3
"""
Automyx 2.5 -- Build Script para Windows
=========================================
Genera dist/AutomyxSetup.exe -- instalador unico, sin dependencias externas.

Flujo:
  1. Compila automix.py con PyInstaller  -->  dist/Automyx/
  2. Zipea dist/Automyx/                -->  dist/Automyx.zip
  3. Compila installer_app.py            -->  dist/AutomyxSetup.exe
     (con Automyx.zip embebido)

Uso:
  python build_windows.py              # todo el proceso
  python build_windows.py --app-only   # solo el app (paso 1)
  python build_windows.py --pack       # solo zip + installer (pasos 2-3)
"""
from __future__ import annotations

import os
import sys
import io
import shutil
import zipfile
import subprocess
import argparse
from pathlib import Path

# UTF-8 en stdout Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT       = Path(__file__).parent.resolve()
DIST       = ROOT / "dist"
BUILD      = ROOT / "build"
APP_DIR    = DIST / "Automyx"
BUNDLE_ZIP = DIST / "Automyx.zip"
SETUP_EXE  = DIST / "AutomyxSetup.exe"
ICON       = ROOT / "assets" / "logo.ico"
APP_SPEC   = ROOT / "automyx.spec"

G  = "\033[32m"; R = "\033[31m"; B = "\033[34m"
Y  = "\033[33m"; D = "\033[2m";  RS = "\033[0m"; BD = "\033[1m"

def ok(msg):   print(f"  {G}[OK]{RS}  {msg}")
def fail(msg): print(f"  {R}[ERR]{RS}  {msg}"); sys.exit(1)
def info(msg): print(f"  {D}{msg}{RS}")
def step(msg): print(f"\n{BD}{B}-- {msg}{RS}")


# ── 1. Dependencias ────────────────────────────────────────────────────────────
def check_deps():
    step("Verificando dependencias")
    try:
        import PyInstaller
        ok(f"PyInstaller {PyInstaller.__version__}")
    except ImportError:
        info("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
        ok("PyInstaller instalado")
    try:
        from PIL import Image
        ok("Pillow OK")
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
        ok("Pillow instalado")


# ── 2. Icono ICO ──────────────────────────────────────────────────────────────
def build_icon():
    step("Generando icono")
    png = ROOT / "assets" / "logo.png"
    if not png.exists():
        fail(f"No se encontro {png}")
    from PIL import Image
    img = Image.open(png).convert("RGBA")
    img.resize((256, 256), Image.LANCZOS).save(
        str(ICON), format="ICO",
        sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    )
    ok(f"assets/logo.ico  ({ICON.stat().st_size // 1024} KB)")


# ── 3. Compilar la app ────────────────────────────────────────────────────────
def build_app():
    step("Compilando Automyx con PyInstaller")
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(APP_SPEC),
        "--noconfirm", "--clean",
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        "--log-level=WARN",
    ]
    info(" ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        fail("PyInstaller fallo al compilar la app.")
    if not (APP_DIR / "Automyx.exe").exists():
        fail(f"No se genero {APP_DIR / 'Automyx.exe'}")
    size = sum(f.stat().st_size for f in APP_DIR.rglob("*") if f.is_file())
    ok(f"dist/Automyx/  ({size // (1024*1024)} MB)")


# ── 4. Crear bundle zip ───────────────────────────────────────────────────────
def create_bundle():
    step("Empaquetando en Automyx.zip")
    if BUNDLE_ZIP.exists():
        BUNDLE_ZIP.unlink()

    files = [f for f in APP_DIR.rglob("*") if f.is_file()]
    total = len(files)
    with zipfile.ZipFile(BUNDLE_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for i, f in enumerate(files, 1):
            arc = f.relative_to(APP_DIR)
            zf.write(f, arc)
            if i % 50 == 0 or i == total:
                pct = int(i / total * 100)
                print(f"\r  Comprimiendo... {pct}% ({i}/{total})", end="", flush=True)
    print()
    ok(f"Automyx.zip  ({BUNDLE_ZIP.stat().st_size // (1024*1024)} MB)")


# ── 5. Compilar el instalador ─────────────────────────────────────────────────
def build_installer():
    step("Compilando instalador AutomyxSetup.exe")
    if not BUNDLE_ZIP.exists():
        fail("Automyx.zip no encontrado. Ejecuta sin --pack primero.")

    installer_src = ROOT / "installer_app.py"
    if not installer_src.exists():
        fail("installer_app.py no encontrado.")

    # El zip se embebe via --add-data para que sys._MEIPASS lo tenga
    sep = ";" if sys.platform == "win32" else ":"
    add_data = f"{BUNDLE_ZIP}{sep}."

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(installer_src),
        "--onefile",
        "--noconfirm",
        "--clean",
        "--name", "AutomyxSetup",
        f"--icon={ICON}",
        f"--add-data={add_data}",
        f"--distpath={DIST}",
        f"--workpath={BUILD / 'installer'}",
        "--log-level=WARN",
        "--hidden-import=rich",
        "--hidden-import=rich.console",
        "--hidden-import=rich.panel",
        "--hidden-import=rich.text",
        "--hidden-import=rich.prompt",
        "--hidden-import=rich.progress",
        "--hidden-import=rich.rule",
        "--hidden-import=rich.live",
        "--hidden-import=rich.box",
        "--console",  # necesita consola para el wizard
    ]
    info(f"PyInstaller installer_app.py --onefile")
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        fail("PyInstaller fallo al compilar el instalador.")
    if not SETUP_EXE.exists():
        fail(f"No se genero {SETUP_EXE}")
    ok(f"dist/AutomyxSetup.exe  ({SETUP_EXE.stat().st_size // (1024*1024)} MB)")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-only", action="store_true", help="Solo compilar la app")
    parser.add_argument("--pack",     action="store_true", help="Solo zip + instalador (requiere build previo)")
    args = parser.parse_args()

    print(f"\n{BD}{B}+------------------------------------------+")
    print(f"|   AUTOMYX 2.5 -- Windows Build Tool      |")
    print(f"+------------------------------------------+{RS}")

    check_deps()
    build_icon()

    if args.pack:
        create_bundle()
        build_installer()
    elif args.app_only:
        build_app()
    else:
        build_app()
        create_bundle()
        build_installer()

    print(f"\n{BD}{G}[OK] Build completado{RS}\n")
    if SETUP_EXE.exists():
        print(f"  Instalador:  {SETUP_EXE}")
        print(f"  Tamanio:     {SETUP_EXE.stat().st_size // (1024*1024)} MB")
    if APP_DIR.exists():
        print(f"  App (zip):   {BUNDLE_ZIP}")
    print()


if __name__ == "__main__":
    main()
