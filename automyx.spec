# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para Automyx 2.5
Genera: dist/Automyx/Automyx.exe
"""
import sys
import os
from pathlib import Path

block_cipher = None
ROOT = os.path.abspath(os.path.dirname(SPEC))

# ── Archivos de datos a incluir ───────────────────────────────────────────────
datas = [
    (os.path.join(ROOT, 'Soul.md'),         '.'),
    (os.path.join(ROOT, 'assets'),          'assets'),
    (os.path.join(ROOT, 'skills'),          'skills'),
    (os.path.join(ROOT, 'core'),            'core'),
    (os.path.join(ROOT, 'tools'),           'tools'),
    (os.path.join(ROOT, '.env.example'),    '.'),
    (os.path.join(ROOT, 'AUTOMYX.md'),      '.'),
]

# Añadir nexus_data si existe
if os.path.exists(os.path.join(ROOT, 'nexus_data')):
    datas.append((os.path.join(ROOT, 'nexus_data'), 'nexus_data'))

# ── Imports ocultos (módulos que PyInstaller no detecta automáticamente) ──────
hidden_imports = [
    # Rich
    'rich', 'rich.console', 'rich.panel', 'rich.text', 'rich.live',
    'rich.layout', 'rich.table', 'rich.progress', 'rich.prompt',
    'rich.markdown', 'rich.syntax', 'rich.box', 'rich.align',
    'rich.rule', 'rich.columns', 'rich.spinner', 'rich.status',
    # Prompt toolkit
    'prompt_toolkit', 'prompt_toolkit.history', 'prompt_toolkit.completion',
    'prompt_toolkit.styles', 'prompt_toolkit.formatted_text',
    'prompt_toolkit.key_binding',
    # OpenAI / Anthropic
    'openai', 'anthropic',
    # HTTP
    'requests', 'urllib3', 'certifi',
    # Core modules
    'core.agent', 'core.repl', 'core.config', 'core.ui', 'core.model_config',
    'core.tool_registry', 'core.memory', 'core.session', 'core.permissions',
    'core.context', 'core.multi_agent', 'core.multi_task', 'core.intent_engine',
    'core.onboard_pro_v5', 'core.automyx_cli_v5', 'core.quiet',
    'core.hardware_detector', 'core.banner', 'core.audit', 'core.workspace',
    'core.token_tracker', 'core.speed', 'core.auto_skill',
    # Tools
    'tools.pc_tools', 'tools.web_tools', 'tools.extra_tools', 'tools.mega_tools',
    'tools.video_tools', 'tools.audio_tools', 'tools.social_tools',
    # Std lib
    'sqlite3', 'json', 'pathlib', 'threading', 'concurrent.futures',
    'subprocess', 'webbrowser', 'shutil', 'stat', 'base64',
    # Optional (pueden fallar, no críticos)
    'PIL', 'PIL.Image', 'PIL.ImageGrab',
]

# ── Excluir módulos pesados innecesarios ──────────────────────────────────────
excludes = [
    'tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy',
    'torch', 'tensorflow', 'cv2', 'sklearn',
    'IPython', 'jupyter', 'notebook',
    'pywin32', 'win32api',
    'playwright', 'selenium',
    'docker',
]

a = Analysis(
    [os.path.join(ROOT, 'automix.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Automyx',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,          # Es una app de terminal — necesita consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'assets', 'logo.ico'),
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Automyx',
)
