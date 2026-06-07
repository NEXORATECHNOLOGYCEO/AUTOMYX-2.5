"""
AUTOMYX JSON PROTOCOL v2.0
===========================
Parser blindado para respuestas de LLM. Maneja:
- JSON envuelto en ```json ... ```
- JSON con texto alrededor (prose + tool call)
- Múltiples tool calls en una respuesta
- JSON malformado (comas trailing, comillas sin escapar, comentarios)
- Esquemas con validación de campos requeridos
- Reintentos con auto-reparación
- Fallback a extraer campos clave por regex

Diseñado para ser el ÚNICO punto de entrada de parsing de tool calls.
"""
from __future__ import annotations

import json
import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field

log = logging.getLogger("automyx.json_protocol")


@dataclass
class ToolCall:
    """Un tool call normalizado extraído de la respuesta del LLM."""
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    confidence: float = 1.0
    repaired: bool = False
    source_block: str = "markdown_fence"  # o "raw_braces", "regex_extract", "manual"

    def to_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "args": self.args}


@dataclass
class ParseResult:
    """Resultado del parseo completo de una respuesta LLM."""
    tool_calls: List[ToolCall] = field(default_factory=list)
    plain_text: str = ""
    has_json: bool = False
    parse_quality: float = 1.0  # 0.0 (fallo) a 1.0 (perfecto)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# ---------------------------------------------------------------------------
# CAPA 1: extracción cruda
# ---------------------------------------------------------------------------
_FENCE_RE = re.compile(
    r"```(?:json|JSON)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```",
    re.DOTALL,
)

_BRACE_BALANCE_RE = re.compile(r"\{[^{}]*\}")  # captura rápida sin anidamiento
_ACTION_KEY_RE = re.compile(
    r'"action"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"',
    re.DOTALL,
)


def _strip_code_fence(text: str) -> List[str]:
    """Extrae JSON de bloques ```json ...``` o ``` ... ```"""
    return [m.group(1) for m in _FENCE_RE.finditer(text)]


def _find_balanced_objects(text: str) -> List[str]:
    """
    Encuentra TODOS los objetos JSON balanceados de primer nivel.
    Soporta anidamiento (objetos dentro de objetos) y arreglos.
    """
    results: List[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False
    start_idx = -1
    depth = 0
    container_stack: List[str] = []  # '[' o '{'

    while i < n:
        c = text[i]

        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c in "{[":
                if depth == 0:
                    start_idx = i
                depth += 1
                container_stack.append(c)
            elif c in "}]":
                if depth > 0:
                    depth -= 1
                    container_stack.pop()
                    if depth == 0 and start_idx != -1:
                        results.append(text[start_idx : i + 1])
                        start_idx = -1
        i += 1

    return results


# ---------------------------------------------------------------------------
# CAPA 2: reparación
# ---------------------------------------------------------------------------
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
_PYTHON_TRUE_RE = re.compile(r"\bTrue\b")
_PYTHON_FALSE_RE = re.compile(r"\bFalse\b")
_PYTHON_NONE_RE = re.compile(r"\bNone\b")
_COMMENT_LINE_RE = re.compile(r"//[^\n]*")
_COMMENT_BLOCK_RE = re.compile(r"/\*[\s\S]*?\*/")
_SINGLE_QUOTE_RE = re.compile(r"'([^'\\]*(?:\\.[^'\\]*)*)'")


def _repair_json(text: str) -> Tuple[str, List[str]]:
    """
    Intenta reparar JSON malformado.
    Devuelve (texto_reparado, lista_de_reparaciones_aplicadas).
    NO falla si no puede: devuelve el texto original.
    """
    repairs: List[str] = []
    repaired = text

    # 1. Quitar comentarios de bloque /* ... */
    if _COMMENT_BLOCK_RE.search(repaired):
        repaired = _COMMENT_BLOCK_RE.sub("", repaired)
        repairs.append("removed_block_comments")

    # 2. Quitar comentarios de línea // ...
    if _COMMENT_LINE_RE.search(repaired):
        repaired = _COMMENT_LINE_RE.sub("", repaired)
        repairs.append("removed_line_comments")

    # 3. Reemplazar True/False/None de Python
    if _PYTHON_TRUE_RE.search(repaired):
        repaired = _PYTHON_TRUE_RE.sub("true", repaired)
        repairs.append("python_true_to_json")
    if _PYTHON_FALSE_RE.search(repaired):
        repaired = _PYTHON_FALSE_RE.sub("false", repaired)
        repairs.append("python_false_to_json")
    if _PYTHON_NONE_RE.search(repaired):
        repaired = _PYTHON_NONE_RE.sub("null", repaired)
        repairs.append("python_none_to_json")

    # 4. Quitar comas trailing antes de } o ]
    if _TRAILING_COMMA_RE.search(repaired):
        repaired = _TRAILING_COMMA_RE.sub(r"\1", repaired)
        repairs.append("removed_trailing_commas")

    # 5. Reemplazar comillas simples por dobles (heurística: solo si no hay dobles)
    if '"' not in repaired and _SINGLE_QUOTE_RE.search(repaired):
        repaired = _SINGLE_QUOTE_RE.sub(r'"\1"', repaired)
        repairs.append("single_to_double_quotes")

    return repaired, repairs


# ---------------------------------------------------------------------------
# CAPA 3: parseo y normalización
# ---------------------------------------------------------------------------
def _parse_one(text: str) -> Tuple[Optional[Dict[str, Any]], bool, List[str]]:
    """Parsea un único bloque de texto como JSON. Devuelve (obj, repaired, repairs)."""
    try:
        return json.loads(text), False, []
    except json.JSONDecodeError:
        pass

    repaired_text, repairs = _repair_json(text)
    if repairs:
        try:
            return json.loads(repaired_text), True, repairs
        except json.JSONDecodeError as e:
            log.debug(f"Repair falló: {e} en {text[:100]}")

    return None, False, repairs


def _normalize_tool_call(obj: Any) -> Optional[ToolCall]:
    """
    Convierte un objeto JSON parseado en un ToolCall.
    Acepta: {action, args}, {action, parameters}, {name, parameters}, {function, args}.
    """
    if not isinstance(obj, dict):
        return None

    # 1. Extraer nombre de la acción
    action = (
        obj.get("action")
        or obj.get("tool")
        or obj.get("name")
        or obj.get("function")
        or obj.get("function_name")
    )
    if not isinstance(action, str):
        return None

    # 2. Extraer argumentos
    args = (
        obj.get("args")
        or obj.get("arguments")
        or obj.get("parameters")
        or obj.get("params")
        or obj.get("input")
        or obj.get("kwargs")
        or {}
    )
    if not isinstance(args, dict):
        # Si los args vinieron como string JSON, parsear
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {"_raw": args}
        else:
            args = {}

    return ToolCall(action=action, args=args, raw=json.dumps(obj, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CAPA 4: extracción final con fallback
# ---------------------------------------------------------------------------
def _extract_via_regex(text: str) -> Optional[ToolCall]:
    """Último recurso: extraer action + primer argumento por regex."""
    action_match = _ACTION_KEY_RE.search(text)
    if not action_match:
        return None
    action = action_match.group(1)

    # Buscar un bloque "args" cercano
    args_match = re.search(
        r'"args?"\s*:\s*\{([^{}]*)\}',
        text[action_match.end():],
        re.DOTALL,
    )
    args: Dict[str, Any] = {}
    if args_match:
        inner = args_match.group(1)
        for kv_match in re.finditer(
            r'"([^"]+)"\s*:\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|(\d+(?:\.\d+)?)|true|false|null)',
            inner,
        ):
            key = kv_match.group(1)
            if kv_match.group(2) is not None:
                args[key] = kv_match.group(2)
            elif kv_match.group(3) is not None:
                num = kv_match.group(3)
                args[key] = float(num) if "." in num else int(num)
            else:
                args[key] = None

    return ToolCall(
        action=action,
        args=args,
        raw=text[:500],
        confidence=0.5,
        source_block="regex_extract",
    )


def parse_response(
    response_text: str,
    *,
    strict: bool = False,
    allow_regex_fallback: bool = True,
    schema_validator: Optional[Callable[[ToolCall], Optional[str]]] = None,
) -> ParseResult:
    """
    Parsea la respuesta completa de un LLM.
    Estrategia:
      1) Extraer bloques ```json ... ```
      2) Buscar objetos balanceados de primer nivel
      3) Reparar si hace falta
      4) Fallback por regex si está habilitado
      5) Limpiar texto plano de todos los JSONs extraídos
    """
    result = ParseResult()
    if not response_text or not response_text.strip():
        return result

    extracted_blocks: List[str] = []
    source_tags: List[str] = []

    # Paso 1: bloques de markdown
    fences = _strip_code_fence(response_text)
    extracted_blocks.extend(fences)
    source_tags.extend(["markdown_fence"] * len(fences))

    # Paso 2: objetos balanceados de primer nivel
    if not extracted_blocks:
        balanced = _find_balanced_objects(response_text)
        # Filtrar los que no contienen 'action'
        for b in balanced:
            if '"action"' in b or '"tool"' in b or '"function"' in b:
                extracted_blocks.append(b)
                source_tags.append("raw_braces")

    # Paso 3: parsear y normalizar
    seen_signatures: set = set()
    for block, source in zip(extracted_blocks, source_tags):
        obj, repaired, repairs = _parse_one(block)
        if obj is None:
            if repairs:
                result.warnings.append(f"repair_failed: {repairs}")
            continue

        # Si es un arreglo, desempaquetar
        items: List[Any]
        if isinstance(obj, list):
            items = list(obj)
        else:
            items = [obj]

        for it in items:
            tc = _normalize_tool_call(it)
            if tc is None:
                continue

            # Schema validation opcional
            if schema_validator is not None:
                err = schema_validator(tc)
                if err:
                    result.warnings.append(f"schema_reject: {tc.action} -> {err}")
                    continue

            # Deduplicar
            sig = (tc.action, json.dumps(tc.args, sort_keys=True))
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)

            tc.source_block = source
            tc.repaired = repaired
            tc.confidence = 0.95 if not repaired else 0.8
            result.tool_calls.append(tc)

    # Paso 4: fallback por regex si no obtuvimos nada
    if not result.tool_calls and allow_regex_fallback:
        tc = _extract_via_regex(response_text)
        if tc:
            tc.confidence = 0.5
            result.tool_calls.append(tc)
            result.warnings.append("regex_fallback_used")

    # Paso 5: limpiar texto plano
    result.plain_text = _clean_text(response_text, extracted_blocks)
    result.has_json = bool(result.tool_calls)

    # Calidad global
    if result.tool_calls:
        result.parse_quality = sum(t.confidence for t in result.tool_calls) / len(result.tool_calls)
    else:
        result.parse_quality = 1.0  # no había JSON, eso está bien

    if strict and not result.tool_calls and '"action"' in response_text:
        result.errors.append("strict_mode: action_key_present_but_unparseable")

    return result


def _clean_text(original: str, blocks_to_remove: List[str]) -> str:
    """Quita los bloques JSON extraídos del texto y devuelve el resto."""
    cleaned = original
    for block in blocks_to_remove:
        # Quitar también las vallas ```json ... ``` que los envuelven
        patterns = [
            f"```json\n{block}\n```",
            f"```json{block}```",
            f"```\n{block}\n```",
            f"```{block}```",
            block,
        ]
        for p in patterns:
            if p in cleaned:
                cleaned = cleaned.replace(p, "")
                break
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Utilidades para LLM
# ---------------------------------------------------------------------------
def make_tool_call(action: str, **args: Any) -> str:
    """Genera un string JSON de tool call para usar en prompts few-shot."""
    obj = {"action": action, "args": args}
    return json.dumps(obj, ensure_ascii=False)


def wrap_tool_calls(*calls: Tuple[str, Dict[str, Any]]) -> str:
    """Genera múltiples tool calls envueltos en fences markdown."""
    arr = [{"action": a, "args": args} for a, args in calls]
    return "```json\n" + json.dumps(arr, indent=2, ensure_ascii=False) + "\n```"


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_cases = [
        # 1. JSON limpio en fence
        ('Voy a hacer eso ```json\n{"action": "create_file", "args": {"path": "test.txt"}}\n```', 1),
        # 2. JSON malformado (trailing comma)
        ('Ok ```json\n{"action": "create_file", "args": {"path": "test.txt",},}\n```', 1),
        # 3. JSON con texto alrededor
        ('Claro, voy a buscar el archivo {"action": "search", "args": {"query": "foo"}} espero que sirva', 1),
        # 4. JSON con Python True/False
        ('```json\n{"action": "test", "args": {"active": True, "items": False}}\n```', 1),
        # 5. JSON inválido - regex fallback
        ('Necesito hacer algo: "action": "list", "args": {"folder": "downloads"}', 1),
        # 6. Texto sin JSON
        ('Hola, ¿cómo estás?', 0),
        # 7. Múltiples JSONs
        ('```json\n[{"action":"a","args":{}},{"action":"b","args":{}}]\n```', 2),
    ]
    for text, expected_count in test_cases:
        r = parse_response(text)
        status = "OK" if len(r.tool_calls) == expected_count else "FAIL"
        print(f"[{status}] '{text[:60]}...' -> {len(r.tool_calls)} calls (expected {expected_count}), quality={r.parse_quality:.2f}")
        if r.warnings:
            print(f"   warnings: {r.warnings}")
        for tc in r.tool_calls:
            print(f"   -> {tc.action}({tc.args}) confidence={tc.confidence} repaired={tc.repaired} src={tc.source_block}")
