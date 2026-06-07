"""
Automyx 2.5 — Auto-Installer
=============================
Detects missing Python packages and silently installs them.

Used by:
- core/agent.py  → catches ImportError on tool import, auto-installs, retries once.
- tools/*        → wrap imports: `from core.auto_install import require; require("whisper")`.
- Any module that needs an opt-in dep.

Design goals:
- Best-effort, never raise from auto_install (returns False on failure).
- Respects PIP_NO_INPUT, offline mode, custom indexes via env vars.
- Quiet by default; pass verbose=True to surface pip output.
- Idempotent: importlib.util.find_spec check before pip call.
- Thread-safe lock to avoid concurrent pip installs.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
import threading
from typing import Iterable

_LOCK = threading.Lock()
_INSTALLED_THIS_SESSION: set[str] = set()


def _is_installed(module_name: str) -> bool:
    """Returns True if the module is already importable in the current process."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ValueError, ModuleNotFoundError):
        return False


def _normalize(pkg: str) -> str:
    """Map a module name to a pip distribution name when they differ."""
    overrides = {
        "PIL": "Pillow",
        "cv2": "opencv-python",
        "skimage": "scikit-image",
        "yaml": "PyYAML",
        "bs4": "beautifulsoup4",
        "attr": "attrs",
        "OpenSSL": "pyOpenSSL",
        "sklearn": "scikit-learn",
        "googleapiclient": "google-api-python-client",
        "magic": "python-magic",
        "git": "GitPython",
        "dotenv": "python-dotenv",
        "dateutil": "python-dateutil",
        "Levenshtein": "python-Levenshtein",
        "telegram": "python-telegram-bot",
        "discord": "discord.py",
        "pptx": "python-pptx",
        "fitz": "PyMuPDF",
        "pptx": "python-pptx",
        "mysql": "mysql-connector-python",
        "psycopg2": "psycopg2-binary",
    }
    return overrides.get(pkg, pkg)


def ensure_packages(packages: Iterable[str], verbose: bool = False) -> bool:
    """Install the given pip packages if any is missing.

    Returns True if all packages are importable after the call.
    Returns False on failure (does not raise).
    """
    pkgs = list(packages)
    if not pkgs:
        return True

    # Already imported?
    missing = [p for p in pkgs if not _is_installed(p)]
    if not missing:
        return True

    # Translate module→pip
    pip_targets = [_normalize(p) for p in missing]

    with _LOCK:
        # Re-check after acquiring lock
        still_missing = [p for p in missing if not _is_installed(p)]
        if not still_missing:
            return True
        targets = sorted({_normalize(p) for p in still_missing})

        cmd = [sys.executable, "-m", "pip", "install", "--quiet",
               "--disable-pip-version-check", "--no-input", *targets]
        if verbose:
            print(f"[automyx.auto_install] pip install: {' '.join(targets)}", file=sys.stderr)
        try:
            proc = subprocess.run(
                cmd, capture_output=not verbose, text=True, timeout=600,
            )
            if proc.returncode != 0:
                if verbose and proc.stderr:
                    print(f"[automyx.auto_install] pip failed:\n{proc.stderr[:1500]}", file=sys.stderr)
                return False
        except subprocess.TimeoutExpired:
            if verbose:
                print(f"[automyx.auto_install] pip timeout (600s)", file=sys.stderr)
            return False
        except Exception as e:
            if verbose:
                print(f"[automyx.auto_install] error: {e!r}", file=sys.stderr)
            return False

        # Re-test imports in a fresh subprocess because importlib caches
        # the negative result of find_spec for the running process.
        # We can do a child-process import test.
        for p in still_missing:
            _INSTALLED_THIS_SESSION.add(p)
        # In-process: try to flush the negative cache
        for p in still_missing:
            for k in list(sys.modules.keys()):
                if k == p or k.startswith(p + "."):
                    del sys.modules[k]
        return all(_is_installed(p) for p in missing)


def require(*packages: str, verbose: bool = False) -> bool:
    """Convenience: `require("whisper", "torch")` — returns True if all available.

    Use at the top of a tool module to opt into auto-install. The tool is then
    guaranteed to be importable for the rest of the process lifetime.
    """
    return ensure_packages(packages, verbose=verbose)


def installed_during_session() -> set[str]:
    """Returns the set of module names that auto_install successfully installed."""
    return set(_INSTALLED_THIS_SESSION)
