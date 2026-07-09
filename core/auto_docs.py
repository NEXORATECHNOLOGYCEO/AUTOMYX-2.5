from __future__ import annotations

import ast
import os
import re
import textwrap
from pathlib import Path
from typing import Callable


class AutoDocGenerator:
    def __init__(self, llm_runner: Callable[[list], str]):
        self._llm = llm_runner

    def _ask(self, prompt: str) -> str:
        return self._llm([{"role": "user", "content": prompt}])

    def generate_readme(self, directory: str) -> str:
        dir_path = Path(directory)
        files_info: list[str] = []
        for f in sorted(dir_path.rglob("*")):
            if f.is_file() and not any(p.startswith(".") for p in f.parts):
                rel = f.relative_to(dir_path)
                try:
                    snippet = f.read_text(encoding="utf-8", errors="replace")[:300]
                    files_info.append(f"### {rel}\n```\n{snippet}\n```")
                except Exception:
                    files_info.append(f"### {rel}\n(binary or unreadable)")

        combined = "\n\n".join(files_info[:30])
        prompt = (
            f"Analiza el siguiente proyecto y genera un README.md completo en español con las secciones: "
            f"descripción, instalación, uso, estructura de archivos, contribución y licencia.\n\n"
            f"Archivos del proyecto:\n{combined}"
        )
        return self._ask(prompt)

    def generate_docstrings(self, file_path: str) -> str:
        source = Path(file_path).read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        nodes_without_docs: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)):
                    src_lines = source.splitlines()
                    start = node.lineno - 1
                    end = min(node.lineno + 15, len(src_lines))
                    snippet = "\n".join(src_lines[start:end])
                    nodes_without_docs.append(snippet)

        if not nodes_without_docs:
            return source

        combined = "\n\n---\n\n".join(nodes_without_docs[:20])
        prompt = (
            f"El siguiente archivo Python tiene funciones/clases sin docstrings. "
            f"Devuelve el archivo COMPLETO con docstrings añadidos en cada función y clase que no los tenga. "
            f"Usa formato Google style. Solo devuelve el código Python, sin explicaciones.\n\n"
            f"Archivo completo:\n```python\n{source}\n```\n\n"
            f"Fragmentos sin docstring:\n{combined}"
        )
        result = self._ask(prompt)
        match = re.search(r"```python\n(.*?)```", result, re.DOTALL)
        if match:
            return match.group(1)
        return result

    def generate_mermaid_diagram(self, directory: str) -> str:
        dir_path = Path(directory)
        imports_map: dict[str, list[str]] = {}

        for py_file in sorted(dir_path.rglob("*.py")):
            rel = str(py_file.relative_to(dir_path)).replace(os.sep, "/").replace(".py", "")
            module_name = rel.replace("/", ".")
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            deps: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.append(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    deps.append(node.module.split(".")[0])

            imports_map[module_name] = list(set(deps))

        local_modules = set(imports_map.keys())
        lines = ["graph TD"]
        for mod, deps in imports_map.items():
            short = mod.split(".")[-1]
            for dep in deps:
                dep_short = dep.split(".")[-1]
                if any(m.endswith(dep) or m.endswith(dep_short) for m in local_modules) or dep in local_modules:
                    lines.append(f"    {short} --> {dep_short}")

        if len(lines) == 1:
            lines.append("    A[No se detectaron dependencias locales]")

        diagram = "\n".join(lines)
        return f"```mermaid\n{diagram}\n```"

    def generate_changelog(self, git_log_text: str) -> str:
        prompt = (
            f"Convierte el siguiente git log en un CHANGELOG.md bien formateado en español. "
            f"Categoriza los commits en: Features, Bug Fixes, Breaking Changes, Otros. "
            f"Usa formato markdown con fechas si están disponibles.\n\n"
            f"Git log:\n{git_log_text}"
        )
        return self._ask(prompt)

    def generate_api_docs(self, file_path: str) -> str:
        source = Path(file_path).read_text(encoding="utf-8")

        route_pattern = re.compile(
            r'@(?:app|router|blueprint)\.(get|post|put|delete|patch|route)\s*\(\s*["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        routes = route_pattern.findall(source)

        prompt = (
            f"Analiza el siguiente archivo Python y genera documentación de API en formato Markdown. "
            f"Incluye: método HTTP, ruta, descripción, parámetros, y ejemplo de respuesta.\n\n"
            f"Rutas detectadas: {routes}\n\n"
            f"Código fuente:\n```python\n{source[:4000]}\n```"
        )
        return self._ask(prompt)


def get_doc_generator(llm_runner: Callable[[list], str]) -> AutoDocGenerator:
    return AutoDocGenerator(llm_runner)
