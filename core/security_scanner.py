from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_instance: Optional[SecurityScanner] = None

_PATTERNS: List[Dict[str, Any]] = [
    {
        "severity": "CRITICAL",
        "rule": "hardcoded_password",
        "description": "Contraseña hardcodeada detectada",
        "regex": re.compile(r'password\s*=\s*["\'][^"\']{4,}', re.IGNORECASE),
    },
    {
        "severity": "CRITICAL",
        "rule": "hardcoded_api_key",
        "description": "API key hardcodeada detectada",
        "regex": re.compile(r'api_key\s*=\s*["\'][^"\']+', re.IGNORECASE),
    },
    {
        "severity": "CRITICAL",
        "rule": "hardcoded_secret",
        "description": "Secret hardcodeado detectado",
        "regex": re.compile(r'secret\s*=\s*["\'][^"\']+', re.IGNORECASE),
    },
    {
        "severity": "CRITICAL",
        "rule": "hardcoded_token",
        "description": "Token hardcodeado detectado",
        "regex": re.compile(r'token\s*=\s*["\'][^"\']{10,}', re.IGNORECASE),
    },
    {
        "severity": "CRITICAL",
        "rule": "sql_injection",
        "description": "Posible SQL injection via f-string o formato en execute()",
        "regex": re.compile(
            r'execute\s*\(\s*f["\']|f".*SELECT.*\{|cursor\.execute.*%s.*format',
            re.IGNORECASE,
        ),
    },
    {
        "severity": "HIGH",
        "rule": "xss",
        "description": "Posible XSS via innerHTML o document.write con concatenación",
        "regex": re.compile(r'innerHTML\s*=\s*.*\+|document\.write\s*\(', re.IGNORECASE),
    },
    {
        "severity": "HIGH",
        "rule": "eval_with_input",
        "description": "eval() o exec() con input de usuario",
        "regex": re.compile(r'eval\s*\(.*input|exec\s*\(.*request', re.IGNORECASE),
    },
    {
        "severity": "HIGH",
        "rule": "path_traversal",
        "description": "Posible path traversal",
        "regex": re.compile(r'\.\.\\/|os\.path\.join.*request|open\s*\(.*\+', re.IGNORECASE),
    },
    {
        "severity": "MEDIUM",
        "rule": "insecure_import",
        "description": "Import de módulo inseguro (pickle/marshal)",
        "regex": re.compile(r'import pickle|import marshal|from pickle', re.IGNORECASE),
    },
    {
        "severity": "MEDIUM",
        "rule": "debug_in_production",
        "description": "Flag DEBUG=True en código",
        "regex": re.compile(r'DEBUG\s*=\s*True|debug\s*=\s*True'),
    },
    {
        "severity": "MEDIUM",
        "rule": "http_not_https",
        "description": "URL HTTP en lugar de HTTPS (excluye localhost)",
        "regex": re.compile(r'http://(?!localhost|127\.0\.0\.1)', re.IGNORECASE),
    },
    {
        "severity": "LOW",
        "rule": "print_sensitive_data",
        "description": "print() con datos potencialmente sensibles",
        "regex": re.compile(r'print.*password|print.*token|print.*secret', re.IGNORECASE),
    },
    {
        "severity": "LOW",
        "rule": "security_todo",
        "description": "TODO/FIXME de seguridad pendiente",
        "regex": re.compile(r'#\s*TODO.*auth|#\s*FIXME.*security', re.IGNORECASE),
    },
]

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "CLEAN": 4}


class SecurityScanner:
    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return []

        findings: List[Dict[str, Any]] = []
        for lineno, line in enumerate(lines, start=1):
            for pat in _PATTERNS:
                if pat["regex"].search(line):
                    findings.append({
                        "severity": pat["severity"],
                        "rule": pat["rule"],
                        "line_number": lineno,
                        "line_content": line.rstrip(),
                        "description": pat["description"],
                        "file": str(path),
                    })
        return findings

    def scan_directory(
        self,
        directory: str,
        extensions: List[str] = None,
    ) -> List[Dict[str, Any]]:
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".php", ".rb"]
        root = Path(directory)
        findings: List[Dict[str, Any]] = []
        for ext in extensions:
            for fpath in root.rglob(f"*{ext}"):
                if any(part.startswith(".") for part in fpath.parts):
                    continue
                findings.extend(self.scan_file(str(fpath)))
        return findings

    def generate_report(self, findings: List[Dict[str, Any]]) -> str:
        if not findings:
            return "RESULTADO: CLEAN - No se encontraron problemas de seguridad.\n"

        by_severity: Dict[str, List[Dict[str, Any]]] = {}
        for f in findings:
            by_severity.setdefault(f["severity"], []).append(f)

        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("REPORTE DE SEGURIDAD - Automyx Security Scanner")
        lines.append("=" * 60)
        lines.append(f"Total hallazgos: {len(findings)}")
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = len(by_severity.get(sev, []))
            if count:
                lines.append(f"  {sev}: {count}")
        lines.append("")

        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            items = by_severity.get(sev, [])
            if not items:
                continue
            lines.append(f"[{sev}]")
            for item in items:
                lines.append(f"  Regla:    {item['rule']}")
                lines.append(f"  Archivo:  {item.get('file', '?')}")
                lines.append(f"  Línea:    {item['line_number']}")
                lines.append(f"  Detalle:  {item['description']}")
                lines.append(f"  Código:   {item['line_content'][:120]}")
                lines.append("")

        lines.append(f"Nivel de riesgo global: {self.get_risk_level(findings)}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def get_risk_level(self, findings: List[Dict[str, Any]]) -> str:
        if not findings:
            return "CLEAN"
        severities = {f["severity"] for f in findings}
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if level in severities:
                return level
        return "CLEAN"


def get_security_scanner() -> SecurityScanner:
    global _instance
    if _instance is None:
        _instance = SecurityScanner()
    return _instance
