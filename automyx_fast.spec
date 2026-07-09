# -*- mode: python ; coding: utf-8 -*-
import os
ROOT = os.path.abspath(os.path.dirname(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'automix.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'Soul.md'),  '.'),
        (os.path.join(ROOT, 'assets'),   'assets'),
        (os.path.join(ROOT, 'skills'),   'skills'),
        (os.path.join(ROOT, 'core'),     'core'),
        (os.path.join(ROOT, 'tools'),    'tools'),
    ],
    hiddenimports=[
        'rich', 'rich.console', 'rich.panel', 'rich.text', 'rich.live',
        'rich.table', 'rich.progress', 'rich.prompt', 'rich.markdown',
        'rich.syntax', 'rich.box', 'rich.align', 'rich.rule', 'rich.columns',
        'prompt_toolkit', 'prompt_toolkit.history', 'prompt_toolkit.completion',
        'prompt_toolkit.styles', 'prompt_toolkit.formatted_text',
        'prompt_toolkit.key_binding',
        'openai', 'anthropic',
        'requests', 'urllib3', 'certifi',
        'sqlite3', 'json', 'pathlib', 'threading', 'concurrent.futures',
        'PIL', 'PIL.Image',
    ],
    excludes=[
        # Heavy ML/science — no los usa Automyx en runtime
        'torch', 'tensorflow', 'keras', 'sklearn', 'scipy',
        'numpy', 'pandas', 'matplotlib', 'seaborn',
        'cv2', 'torchvision', 'torchaudio', 'torchao',
        # NLP pesados
        'transformers', 'datasets', 'tokenizers', 'huggingface_hub',
        'nltk', 'spacy', 'jieba', 'g2p_en',
        # Audio ML
        'pyannote', 'whisper', 'openai_whisper', 'soundfile',
        # GUI toolkits
        'tkinter', 'wx', 'PyQt5', 'PyQt6', 'PySide6',
        # Otros pesados
        'IPython', 'jupyter', 'notebook', 'traitlets',
        'numba', 'llvmlite', 'sympy', 'statsmodels',
        'sqlalchemy', 'alembic',
        'docker', 'kubernetes',
        'pydub', 'librosa', 'audioread',
        'selenium', 'playwright',
        'win32api', 'win32con', 'pywin32',
    ],
    hookspath=[],
    runtime_hooks=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Automyx',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    icon=os.path.join(ROOT, 'assets', 'logo.ico'),
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='Automyx',
)
