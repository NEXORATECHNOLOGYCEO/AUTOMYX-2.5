from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

REVIEW_SYSTEM_PROMPT = """Eres un experto en code review con más de 15 años de experiencia en desarrollo de software.
Analiza el código o diff proporcionado de forma exhaustiva y estructurada.
Responde SIEMPRE en español con las siguientes secciones exactas (usa estos headers exactamente):

## Resumen
Un párrafo conciso con el estado general del código.

## Bugs
Lista cada bug encontrado. Si no hay, escribe "Ninguno".

## Seguridad
Lista cada problema de seguridad. Si no hay, escribe "Ninguno".

## Performance
Lista cada problema de performance. Si no hay, escribe "Ninguno".

## Sugerencias
Lista mejoras de calidad, legibilidad o arquitectura.

## Tests Faltantes
Lista qué casos de prueba faltan o deberían añadirse.

## Severidad
Una sola línea: CRITICAL, HIGH, MEDIUM, LOW, o OK
"""

PR_DESCRIPTION_PROMPT = """Eres un experto técnico. Analiza el siguiente diff git y genera:
1. Un título de PR conciso (máximo 70 caracteres), en inglés, en formato convencional (feat:, fix:, refactor:, etc.)
2. Una descripción en Markdown con secciones: ## Summary, ## Changes, ## Testing

Responde EXACTAMENTE con este formato:
TITULO: <título aquí>
DESCRIPCION:
<descripción markdown aquí>
"""


@dataclass
class ReviewResult:
    summary: str = ""
    bugs: List[str] = field(default_factory=list)
    security: List[str] = field(default_factory=list)
    performance: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    missing_tests: List[str] = field(default_factory=list)
    severity: str = "OK"
    formatted: str = ""


def _extract_section(text: str, header: str) -> List[str]:
    pattern = rf"##\s+{re.escape(header)}\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    block = match.group(1).strip()
    if block.lower() in ("ninguno", "none", "n/a", "-", ""):
        return []
    lines = [l.lstrip("-*• ").strip() for l in block.split("\n") if l.strip() and l.strip() not in ("-", "*")]
    return [l for l in lines if l]


def _extract_simple(text: str, header: str) -> str:
    pattern = rf"##\s+{re.escape(header)}\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_severity(text: str) -> str:
    pattern = r"##\s+Severidad\s*\n\s*(CRITICAL|HIGH|MEDIUM|LOW|OK)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "OK"):
        if level in text.upper():
            return level
    return "MEDIUM"


def _format_result(result: ReviewResult) -> str:
    lines = []
    lines.append(f"SEVERIDAD: [{result.severity}]")
    lines.append("")
    lines.append(f"RESUMEN: {result.summary}")

    def section(title: str, items: List[str], emoji: str = ""):
        if not items:
            return
        lines.append(f"\n{emoji} {title}:")
        for item in items:
            lines.append(f"  - {item}")

    section("BUGS", result.bugs, "BUG")
    section("SEGURIDAD", result.security, "SEC")
    section("PERFORMANCE", result.performance, "PERF")
    section("SUGERENCIAS", result.suggestions, "TIP")
    section("TESTS FALTANTES", result.missing_tests, "TEST")

    return "\n".join(lines)


def _parse_review_response(raw: str) -> ReviewResult:
    result = ReviewResult()
    result.summary = _extract_simple(raw, "Resumen")
    result.bugs = _extract_section(raw, "Bugs")
    result.security = _extract_section(raw, "Seguridad")
    result.performance = _extract_section(raw, "Performance")
    result.suggestions = _extract_section(raw, "Sugerencias")
    result.missing_tests = _extract_section(raw, "Tests Faltantes")
    result.severity = _extract_severity(raw)
    result.formatted = _format_result(result)
    return result


class CodeReviewAgent:
    def __init__(self, llm_runner: Callable[[List[dict]], str]):
        self.llm_runner = llm_runner

    def _call_llm(self, user_content: str) -> str:
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        return self.llm_runner(messages)

    def review_diff(self, diff_text: str, context: str = "") -> ReviewResult:
        if not diff_text.strip():
            r = ReviewResult(summary="Diff vacío, nada que revisar.", severity="OK")
            r.formatted = _format_result(r)
            return r

        user_msg = f"Revisa el siguiente diff git:\n\n```diff\n{diff_text}\n```"
        if context:
            user_msg += f"\n\nContexto adicional:\n{context}"

        raw = self._call_llm(user_msg)
        return _parse_review_response(raw)

    def review_file(self, file_path: str, context: str = "") -> ReviewResult:
        path = Path(file_path)
        if not path.exists():
            r = ReviewResult(summary=f"Archivo no encontrado: {file_path}", severity="OK")
            r.formatted = _format_result(r)
            return r

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            r = ReviewResult(summary=f"Error leyendo archivo: {e}", severity="OK")
            r.formatted = _format_result(r)
            return r

        suffix = path.suffix.lstrip(".") or "text"
        user_msg = f"Revisa el siguiente archivo ({path.name}):\n\n```{suffix}\n{content}\n```"
        if context:
            user_msg += f"\n\nContexto adicional:\n{context}"

        raw = self._call_llm(user_msg)
        return _parse_review_response(raw)

    def review_pr_files(self, file_paths: List[str], context: str = "") -> ReviewResult:
        combined_parts = []
        for fp in file_paths:
            path = Path(fp)
            if not path.exists():
                combined_parts.append(f"# {fp}\n[archivo no encontrado]")
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                suffix = path.suffix.lstrip(".") or "text"
                combined_parts.append(f"# {fp}\n```{suffix}\n{content[:3000]}\n```")
            except Exception as e:
                combined_parts.append(f"# {fp}\n[error: {e}]")

        combined = "\n\n".join(combined_parts)
        user_msg = f"Revisa los siguientes archivos del PR:\n\n{combined}"
        if context:
            user_msg += f"\n\nContexto adicional:\n{context}"

        raw = self._call_llm(user_msg)
        return _parse_review_response(raw)

    def generate_pr_description(self, diff_text: str) -> dict:
        messages = [
            {"role": "system", "content": PR_DESCRIPTION_PROMPT},
            {"role": "user", "content": f"Diff:\n```diff\n{diff_text}\n```"},
        ]
        raw = self.llm_runner(messages)

        title = ""
        description = ""

        title_match = re.search(r"TITULO:\s*(.+)", raw)
        if title_match:
            title = title_match.group(1).strip()

        desc_match = re.search(r"DESCRIPCION:\s*\n(.*)", raw, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()

        return {"title": title, "description": description, "raw": raw}


def get_code_reviewer(llm_runner: Callable[[List[dict]], str]) -> CodeReviewAgent:
    return CodeReviewAgent(llm_runner=llm_runner)
