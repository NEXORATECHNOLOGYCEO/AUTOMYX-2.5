from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

AGENT_ROLES: Dict[str, Dict[str, str]] = {
    "code": {
        "description": "Experto en escribir y refactorizar código",
        "system": (
            "Eres CodeAgent, experto en escribir código limpio, eficiente y mantenible. "
            "Aplicas principios SOLID, patrones de diseño y mejores prácticas. "
            "Siempre produces código funcional, bien estructurado, con manejo de errores robusto. "
            "Prefieres soluciones simples sobre complejas. No añades comentarios innecesarios."
        ),
    },
    "test": {
        "description": "Experto en testing y calidad de software",
        "system": (
            "Eres TestAgent, experto en testing, TDD y aseguramiento de calidad. "
            "Escribes tests unitarios, de integración y end-to-end. Usas mocks y fixtures correctamente. "
            "Buscas cubrir casos borde y condiciones de error. "
            "Sigues el patrón Arrange-Act-Assert y produces tests legibles y mantenibles."
        ),
    },
    "security": {
        "description": "Experto en seguridad y vulnerabilidades",
        "system": (
            "Eres SecurityAgent, experto en ciberseguridad y hardening de aplicaciones. "
            "Conoces OWASP Top 10, CVEs comunes, inyecciones SQL/XSS, gestión de secretos y autenticación. "
            "Identificas vulnerabilidades en código y propones remediaciones concretas. "
            "Nunca sugieres guardar secretos en código o logs. Priorizas por criticidad."
        ),
    },
    "devops": {
        "description": "Experto en infraestructura, CI/CD y despliegues",
        "system": (
            "Eres DevOpsAgent, experto en Docker, Kubernetes, CI/CD, terraform y cloud. "
            "Diseñas pipelines eficientes, configuras monitoreo y alertas, optimizas deployments. "
            "Priorizas alta disponibilidad, rollbacks seguros y observabilidad. "
            "Das comandos exactos y configuraciones listas para usar en producción."
        ),
    },
    "data": {
        "description": "Experto en análisis de datos y bases de datos",
        "system": (
            "Eres DataAgent, experto en SQL, Python (pandas, numpy), visualización y ETL. "
            "Analizas datasets, optimizas queries, diseñas schemas y construyes pipelines de datos. "
            "Siempre validas calidad de datos, manejas nulos y outliers correctamente. "
            "Propones visualizaciones claras y métricas accionables para el negocio."
        ),
    },
    "docs": {
        "description": "Experto en documentación técnica",
        "system": (
            "Eres DocsAgent, experto en documentación técnica clara y útil. "
            "Escribes READMEs, docstrings, changelogs, diagramas C4 y guías de integración. "
            "Tu documentación es concisa, con ejemplos reales y orientada al lector objetivo. "
            "Usas Markdown bien estructurado y evitas documentación que repite el código."
        ),
    },
    "review": {
        "description": "Experto en code review y mejores prácticas",
        "system": (
            "Eres ReviewAgent, experto en code review constructivo y detallado. "
            "Analizas legibilidad, mantenibilidad, performance, seguridad y cobertura de tests. "
            "Das feedback específico con línea de código, problema y sugerencia de mejora. "
            "Distingues entre bloqueantes críticos, mejoras importantes y sugerencias opcionales."
        ),
    },
}

ROLE_KEYWORDS: Dict[str, List[str]] = {
    "code": ["implementa", "escribe", "crea", "refactoriza", "función", "clase", "código", "script", "programa", "fix", "arregla", "corrige"],
    "test": ["test", "tests", "prueba", "pruebas", "cobertura", "mock", "unittest", "pytest", "testing", "tdd"],
    "security": ["seguridad", "vulnerability", "vulnerabilidad", "owasp", "xss", "sql injection", "auth", "token", "secret", "csrf", "hack", "pentest"],
    "devops": ["docker", "kubernetes", "k8s", "ci/cd", "deploy", "pipeline", "nginx", "terraform", "aws", "gcp", "azure", "helm", "container"],
    "data": ["sql", "query", "pandas", "dataset", "dataframe", "csv", "etl", "análisis", "grafica", "visualiza", "database", "base de datos"],
    "docs": ["documentación", "readme", "documenta", "docstring", "changelog", "diagrama", "guía", "manual", "explica"],
    "review": ["review", "revisa", "mejora", "feedback", "code review", "analiza el código", "qué falla", "problemas en"],
}

_orchestrator_instance: Optional["AgentOrchestrator"] = None
_last_base_agent: Any = None


class AgentOrchestrator:
    def __init__(self, base_agent: Any):
        self.base_agent = base_agent

    def detect_role(self, task: str) -> str:
        task_lower = task.lower()
        scores: Dict[str, int] = {role: 0 for role in AGENT_ROLES}
        for role, keywords in ROLE_KEYWORDS.items():
            for kw in keywords:
                if kw in task_lower:
                    scores[role] += 1
        best = max(scores, key=lambda r: scores[r])
        if scores[best] == 0:
            return "code"
        return best

    def get_specialized_prompt(self, role: str) -> str:
        if role not in AGENT_ROLES:
            raise ValueError(f"Rol desconocido: {role}. Disponibles: {list(AGENT_ROLES.keys())}")
        return AGENT_ROLES[role]["system"]

    def run_as(self, role: str, task: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        system_prompt = self.get_specialized_prompt(role)
        agent = self.base_agent

        original_system = None
        if hasattr(agent, "system_prompt"):
            original_system = agent.system_prompt

        try:
            if hasattr(agent, "system_prompt"):
                agent.system_prompt = system_prompt

            if progress_callback:
                progress_callback(f"[{role.upper()}] Iniciando tarea...")

            if hasattr(agent, "run"):
                result = agent.run(task)
            elif callable(agent):
                result = agent(task)
            else:
                result = f"Agente no ejecutable para rol {role}"

            if progress_callback:
                progress_callback(f"[{role.upper()}] Tarea completada.")

            return result
        finally:
            if original_system is not None and hasattr(agent, "system_prompt"):
                agent.system_prompt = original_system

    def run_auto(self, task: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        role = self.detect_role(task)
        if progress_callback:
            progress_callback(f"[AUTO] Rol detectado: {role}")
        return self.run_as(role, task, progress_callback=progress_callback)

    def list_roles(self) -> List[Dict[str, str]]:
        return [
            {"role": role, "description": info["description"]}
            for role, info in AGENT_ROLES.items()
        ]


def get_orchestrator(base_agent: Any) -> AgentOrchestrator:
    global _orchestrator_instance, _last_base_agent
    if _orchestrator_instance is None or _last_base_agent is not base_agent:
        _orchestrator_instance = AgentOrchestrator(base_agent)
        _last_base_agent = base_agent
    return _orchestrator_instance
