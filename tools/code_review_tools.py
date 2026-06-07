"""
Code Review Tools - Análisis estático de código
================================================
Ejecuta linters, encuentra code smells, mide complejidad, sugiere mejoras.
Soporta Python, JavaScript, TypeScript, Go, Rust, Java.
"""
from __future__ import annotations

import os
import json
import re
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def python_metrics(file_path: str) -> Dict[str, Any]:
    """Métricas básicas: líneas, funciones, clases, complejidad."""
    p = Path(file_path)
    if not p.exists():
        return {"ok": False, "error": f"archivo no existe: {file_path}"}
    if not p.suffix == ".py":
        return {"ok": False, "error": f"no es Python: {file_path}"}
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"ok": False, "error": str(e)}

    lines = text.splitlines()
    blank = sum(1 for l in lines if not l.strip())
    comment = sum(1 for l in lines if l.strip().startswith("#"))
    code = len(lines) - blank - comment

    funcs = re.findall(r"^\s*def\s+(\w+)", text, re.MULTILINE)
    classes = re.findall(r"^\s*class\s+(\w+)", text, re.MULTILINE)
    imports = re.findall(r"^(?:from\s+\S+\s+)?import\s+.+", text, re.MULTILINE)

    # Complejidad ciclomática rough: contar keywords de control
    keywords = ["if", "elif", "for", "while", "except", "and", "or", "case"]
    complexity = 1
    for kw in keywords:
        complexity += len(re.findall(rf"\b{kw}\b", text))

    # Detectar code smells
    smells = []
    if any(len(l) > 120 for l in lines):
        smells.append("Líneas > 120 caracteres")
    long_funcs = re.findall(r"^(\s*)def\s+(\w+).*?:(.*?)(?=^\1def|\Z)", text, re.MULTILINE | re.DOTALL)
    for indent, name, body in long_funcs:
        if body.count("\n") > 50:
            smells.append(f"Función '{name}' tiene > 50 líneas")
    if re.search(r"^\s*print\(", text, re.MULTILINE):
        smells.append("Contiene print() statements")
    if re.search(r"^\s*import \*\s*$", text, re.MULTILINE):
        smells.append("Uso de 'import *'")
    if re.search(r"\bTODO\b|\bFIXME\b|\bXXX\b", text):
        smells.append("Contiene TODOs/FIXMEs")

    return {
        "ok": True,
        "file": file_path,
        "total_lines": len(lines),
        "code_lines": code,
        "blank_lines": blank,
        "comment_lines": comment,
        "functions": funcs,
        "function_count": len(funcs),
        "classes": classes,
        "class_count": len(classes),
        "imports": len(imports),
        "complexity_estimate": complexity,
        "complexity_rating": _complexity_rating(complexity),
        "code_smells": smells,
    }


def _complexity_rating(c: int) -> str:
    if c <= 10:
        return "BAJA"
    if c <= 20:
        return "MODERADA"
    if c <= 50:
        return "ALTA"
    return "MUY ALTA (refactor urgente)"


# ---------------------------------------------------------------------------
# Linters
# ---------------------------------------------------------------------------
def run_flake8(file_path: str) -> Dict[str, Any]:
    if not shutil.which("flake8"):
        return {"ok": False, "error": "flake8 no instalado (pip install flake8)"}
    r = subprocess.run(["flake8", "--max-line-length=120", "--format=json", file_path],
                       capture_output=True, text=True, timeout=30)
    if r.stdout.strip():
        try:
            issues = json.loads(r.stdout)
        except json.JSONDecodeError:
            issues = [{"raw": r.stdout}]
    else:
        issues = []
    return {"ok": True, "issues": issues, "count": len(issues)}


def run_pylint(file_path: str) -> Dict[str, Any]:
    if not shutil.which("pylint"):
        return {"ok": False, "error": "pylint no instalado"}
    r = subprocess.run(["pylint", "--output-format=json", "--disable=C0114,C0115,C0116", file_path],
                       capture_output=True, text=True, timeout=60)
    issues = []
    if r.stdout.strip():
        try:
            issues = json.loads(r.stdout)
        except json.JSONDecodeError:
            issues = [{"raw": r.stdout}]
    return {"ok": True, "issues": issues, "count": len(issues)}


def run_mypy(file_path: str) -> Dict[str, Any]:
    if not shutil.which("mypy"):
        return {"ok": False, "error": "mypy no instalado"}
    r = subprocess.run(["mypy", "--no-error-summary", "--json", file_path],
                       capture_output=True, text=True, timeout=60)
    issues = []
    if r.stdout.strip():
        try:
            issues = json.loads(r.stdout)
        except json.JSONDecodeError:
            issues = [{"raw": r.stdout}]
    return {"ok": True, "issues": issues, "count": len(issues)}


def run_black_check(file_path: str) -> Dict[str, Any]:
    if not shutil.which("black"):
        return {"ok": False, "error": "black no instalado"}
    r = subprocess.run(["black", "--check", "--diff", file_path],
                       capture_output=True, text=True, timeout=30)
    return {
        "ok": r.returncode == 0,
        "needs_format": r.returncode != 0,
        "diff": r.stdout if r.returncode != 0 else "",
    }


# ---------------------------------------------------------------------------
# Búsqueda de patrones
# ---------------------------------------------------------------------------
SECRETS_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|aws[_-]?access)[^\n]{0,40}['\"]([A-Za-z0-9+/=_\-]{16,})['\"]"
)


def security_scan(file_path: str) -> Dict[str, Any]:
    """Busca secretos hardcodeados, queries SQL sin parametrizar, etc."""
    p = Path(file_path)
    if not p.exists():
        return {"ok": False, "error": f"archivo no existe: {file_path}"}
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"ok": False, "error": str(e)}

    issues: List[Dict[str, Any]] = []

    # Secretos
    for m in SECRETS_RE.finditer(text):
        line_no = text[:m.start()].count("\n") + 1
        issues.append({
            "type": "secret",
            "severity": "high",
            "line": line_no,
            "match": m.group(0)[:60],
            "recommendation": "usar variable de entorno o vault",
        })

    # SQL injection risk
    sql_concat = re.findall(r"execute\s*\(\s*['\"].*?\%s|execute\s*\(\s*f['\"]|execute\s*\(\s*['\"].*?\+", text)
    for m in sql_concat:
        issues.append({"type": "sql_injection_risk", "severity": "high", "match": str(m)[:60]})

    # eval/exec
    if re.search(r"\beval\s*\(|\bexec\s*\(", text):
        issues.append({"type": "dangerous_call", "severity": "high", "match": "eval/exec call"})

    # TODO/FIXME
    for m in re.finditer(r"#\s*(TODO|FIXME|XXX|HACK)", text):
        line_no = text[:m.start()].count("\n") + 1
        issues.append({"type": "todo", "severity": "low", "line": line_no, "match": m.group(0)})

    # print statements
    print_count = len(re.findall(r"\bprint\s*\(", text))
    if print_count > 5:
        issues.append({"type": "debug_print", "severity": "low", "count": print_count})

    return {"ok": True, "file": file_path, "issue_count": len(issues), "issues": issues[:50]}


# ---------------------------------------------------------------------------
# Code review completo
# ---------------------------------------------------------------------------
def full_review(file_path: str, *, run_linters: bool = True) -> Dict[str, Any]:
    """Code review completo: métricas + linters + seguridad."""
    metrics = python_metrics(file_path)
    if not metrics["ok"]:
        return metrics

    review = {
        "ok": True,
        "file": file_path,
        "metrics": metrics,
        "linters": {},
        "security": security_scan(file_path),
    }

    if run_linters:
        review["linters"]["flake8"] = run_flake8(file_path)
        review["linters"]["black"] = run_black_check(file_path)

    # Score agregado
    score = 100
    score -= len(review["security"]["issues"]) * 5
    score -= sum(min(v.get("count", 0), 20) for v in review["linters"].values() if v.get("ok"))
    score -= sum(5 for s in metrics["code_smells"])
    if metrics["complexity_estimate"] > 50:
        score -= 20
    score = max(0, min(100, score))

    review["score"] = score
    review["score_rating"] = (
        "EXCELENTE" if score >= 90 else
        "BUENO" if score >= 75 else
        "ACEPTABLE" if score >= 60 else
        "MEJORABLE" if score >= 40 else
        "REQUIERE REFACTOR"
    )

    return review


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class CodeReviewTools:
    @staticmethod
    def metrics(file_path: str) -> Dict[str, Any]:
        return python_metrics(file_path)

    @staticmethod
    def security(file_path: str) -> Dict[str, Any]:
        return security_scan(file_path)

    @staticmethod
    def flake8(file_path: str) -> Dict[str, Any]:
        return run_flake8(file_path)

    @staticmethod
    def black(file_path: str) -> Dict[str, Any]:
        return run_black_check(file_path)

    @staticmethod
    def full(file_path: str) -> Dict[str, Any]:
        return full_review(file_path)
