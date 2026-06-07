"""
Test Runner Tools - Ejecuta tests en múltiples frameworks
==========================================================
pytest, unittest, jest, mocha, go test, cargo test. Con coverage.
"""
from __future__ import annotations

import os
import json
import re
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


def _run(cmd: List[str], cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout, encoding="utf-8", errors="replace")
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout,
            "stderr": r.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s"}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"binario no encontrado: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------
def pytest_run(path: str = ".", *, args: Optional[List[str]] = None, coverage: bool = True,
               cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    """Ejecuta pytest con coverage opcional."""
    if not shutil.which("pytest"):
        return {"ok": False, "error": "pytest no instalado"}
    cmd = ["pytest", path, "-v", "--tb=short", "--color=no"]
    if coverage:
        cmd += ["--cov=" + path, "--cov-report=term-missing", "--cov-report=json:/tmp/cov.json"]
    if args:
        cmd += args
    r = _run(cmd, cwd=cwd, timeout=timeout)
    parsed = _parse_pytest_output(r["stdout"] + r["stderr"])
    result = {"ok": r["ok"], "returncode": r["returncode"], "output": r["stdout"]}
    result.update(parsed)
    if coverage and os.path.exists("/tmp/cov.json"):
        try:
            cov_data = json.loads(Path("/tmp/cov.json").read_text(encoding="utf-8"))
            totals = cov_data.get("totals", {})
            result["coverage_pct"] = round(totals.get("percent_covered", 0), 2)
        except Exception:
            pass
    return result


def _parse_pytest_output(output: str) -> Dict[str, Any]:
    """Extrae passed/failed/errors del output de pytest."""
    result = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "duration_s": 0.0}
    m = re.search(r"(\d+)\s+passed", output)
    if m: result["passed"] = int(m.group(1))
    m = re.search(r"(\d+)\s+failed", output)
    if m: result["failed"] = int(m.group(1))
    m = re.search(r"(\d+)\s+error", output)
    if m: result["errors"] = int(m.group(1))
    m = re.search(r"(\d+)\s+skipped", output)
    if m: result["skipped"] = int(m.group(1))
    m = re.search(r"in\s+([\d.]+)s", output)
    if m: result["duration_s"] = float(m.group(1))
    # Fallos individuales
    failures = []
    for fm in re.finditer(r"FAILED\s+(\S+).*?(?=\nFAILED|\n=+|\Z)", output, re.DOTALL):
        failures.append(fm.group(1).strip())
    result["failed_tests"] = failures[:20]
    return result


def unittest_run(path: str = ".", *, cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    """Ejecuta unittest estándar de Python."""
    r = _run(["python", "-m", "unittest", "discover", "-s", path, "-v"], cwd=cwd, timeout=timeout)
    return {
        "ok": r["ok"],
        "returncode": r["returncode"],
        "output": r["stdout"],
        "stderr": r["stderr"],
    }


# ---------------------------------------------------------------------------
# JavaScript / TypeScript
# ---------------------------------------------------------------------------
def jest_run(path: str = ".", *, args: Optional[List[str]] = None,
             cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    """Ejecuta jest."""
    if not shutil.which("jest") and not (Path("node_modules/.bin/jest").exists() if cwd is None else (Path(cwd) / "node_modules" / ".bin" / "jest").exists()):
        return {"ok": False, "error": "jest no instalado (npm i -D jest)"}
    bin_path = "jest" if shutil.which("jest") else "npx jest"
    cmd = bin_path.split() if isinstance(bin_path, str) else [bin_path]
    cmd += [path, "--json", "--outputFile=/tmp/jest-out.json"]
    if args:
        cmd += args
    r = _run(cmd, cwd=cwd, timeout=timeout)
    result = {"ok": r["ok"], "returncode": r["returncode"], "output": r["stdout"]}
    if os.path.exists("/tmp/jest-out.json"):
        try:
            data = json.loads(Path("/tmp/jest-out.json").read_text(encoding="utf-8"))
            result.update({
                "num_total_tests": data.get("numTotalTests"),
                "num_passed_tests": data.get("numPassedTests"),
                "num_failed_tests": data.get("numFailedTests"),
                "num_pending_tests": data.get("numPendingTests"),
            })
        except Exception:
            pass
    return result


def mocha_run(path: str = ".", *, cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    if not shutil.which("mocha") and not (Path("node_modules/.bin/mocha").exists()):
        return {"ok": False, "error": "mocha no instalado"}
    return _run(["mocha", path, "--reporter", "json"], cwd=cwd, timeout=timeout)


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------
def go_test(path: str = ".", *, cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    if not shutil.which("go"):
        return {"ok": False, "error": "go no instalado"}
    r = _run(["go", "test", path, "-v", "-cover"], cwd=cwd, timeout=timeout)
    # Parsear coverage
    coverage = None
    m = re.search(r"coverage:\s*([\d.]+)%", r["stdout"])
    if m:
        coverage = float(m.group(1))
    return {"ok": r["ok"], "returncode": r["returncode"], "output": r["stdout"], "coverage_pct": coverage}


# ---------------------------------------------------------------------------
# Rust
# ---------------------------------------------------------------------------
def cargo_test(path: str = ".", *, cwd: Optional[str] = None, timeout: int = 600) -> Dict[str, Any]:
    if not shutil.which("cargo"):
        return {"ok": False, "error": "cargo no instalado"}
    return _run(["cargo", "test", "--", "--nocapture"], cwd=cwd, timeout=timeout)


# ---------------------------------------------------------------------------
# Detección automática
# ---------------------------------------------------------------------------
def detect_and_run(path: str = ".", *, cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    """Detecta el framework de test disponible y ejecuta."""
    c = cwd or path
    p = Path(c)
    if not p.exists():
        return {"ok": False, "error": f"path no existe: {c}"}

    # Python
    if (p / "pytest.ini").exists() or (p / "pyproject.toml").exists() or (p / "setup.cfg").exists():
        if shutil.which("pytest"):
            return pytest_run(path, cwd=c, timeout=timeout)
        return unittest_run(path, cwd=c, timeout=timeout)

    if any(p.rglob("test_*.py")) or any(p.rglob("*_test.py")):
        if shutil.which("pytest"):
            return pytest_run(path, cwd=c, timeout=timeout)
        return unittest_run(path, cwd=c, timeout=timeout)

    # JS
    if (p / "package.json").exists():
        pkg = json.loads((p / "package.json").read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        if "test" in scripts:
            test_cmd = scripts["test"]
            if "jest" in test_cmd or "vitest" in test_cmd:
                return jest_run(path, cwd=c, timeout=timeout)
            if "mocha" in test_cmd:
                return mocha_run(path, cwd=c, timeout=timeout)
            # Fallback: npm test
            return _run(["npm", "test"], cwd=c, timeout=timeout)

    # Go
    if any(p.rglob("*_test.go")):
        return go_test(path, cwd=c, timeout=timeout)

    # Rust
    if (p / "Cargo.toml").exists():
        return cargo_test(path, cwd=c, timeout=timeout)

    return {"ok": False, "error": "no se detectó ningún framework de test"}


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class TestRunnerTools:
    @staticmethod
    def pytest(path: str = ".", coverage: bool = True) -> Dict[str, Any]:
        return pytest_run(path, coverage=coverage)

    @staticmethod
    def unittest(path: str = ".") -> Dict[str, Any]:
        return unittest_run(path)

    @staticmethod
    def jest(path: str = ".") -> Dict[str, Any]:
        return jest_run(path)

    @staticmethod
    def go(path: str = ".") -> Dict[str, Any]:
        return go_test(path)

    @staticmethod
    def cargo(path: str = ".") -> Dict[str, Any]:
        return cargo_test(path)

    @staticmethod
    def auto(path: str = ".") -> Dict[str, Any]:
        return detect_and_run(path)
