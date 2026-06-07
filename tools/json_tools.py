"""
JSON Tools - Utilidades profesionales de JSON
==============================================
Validación, reparación, comparación, schema, pretty-print, diff, JSONPath,
conversión a/from YAML/CSV/TOML/XML. El parser definitivo.
"""
from __future__ import annotations

import json
import os
import re
import csv
import io
import difflib
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False


JSONPATH_CACHE: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------
def json_validate(text: str, *, schema: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Valida un string como JSON.
    - Si provees schema (dict con 'required' list y 'types' dict), valida estructura.
    - Devuelve {ok, error, line, column, path}
    """
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "error": str(e.msg),
            "line": e.lineno,
            "column": e.colno,
            "position": e.pos,
        }

    if schema:
        issues = []
        if "required" in schema:
            for key in schema["required"]:
                if not isinstance(obj, dict) or key not in obj:
                    issues.append(f"missing required key: {key!r}")
        if "types" in schema and isinstance(obj, dict):
            for key, expected_type in schema["types"].items():
                if key in obj and not _check_type(obj[key], expected_type):
                    issues.append(f"key {key!r}: expected {expected_type}, got {type(obj[key]).__name__}")
        if issues:
            return {"ok": False, "error": "schema violation", "issues": issues, "parsed": obj}
        return {"ok": True, "parsed": obj, "schema_valid": True}

    return {"ok": True, "parsed": obj, "type": _type_name(obj)}


def _check_type(value: Any, expected: str) -> bool:
    type_map = {
        "str": str, "string": str,
        "int": int, "integer": int,
        "float": float, "number": (int, float),
        "bool": bool, "boolean": bool,
        "list": list, "array": list,
        "dict": dict, "object": dict,
        "null": type(None), "none": type(None),
    }
    exp = type_map.get(expected.lower())
    if exp is None:
        return True
    if expected.lower() in ("number",) and isinstance(value, bool):
        return False
    return isinstance(value, exp)


def _type_name(obj: Any) -> str:
    if isinstance(obj, bool):
        return "boolean"
    if isinstance(obj, int):
        return "integer"
    if isinstance(obj, float):
        return "number"
    if isinstance(obj, str):
        return "string"
    if isinstance(obj, list):
        return "array"
    if isinstance(obj, dict):
        return "object"
    if obj is None:
        return "null"
    return type(obj).__name__


# ---------------------------------------------------------------------------
# Reparación
# ---------------------------------------------------------------------------
_REPAIR_RULES = [
    (r",(\s*[}\]])", r"\1", "trailing comma"),
    (r"\bTrue\b", "true", "Python True → JSON true"),
    (r"\bFalse\b", "false", "Python False → JSON false"),
    (r"\bNone\b", "null", "Python None → JSON null"),
    (r"//[^\n]*", "", "line comment"),
    (r"/\*[\s\S]*?\*/", "", "block comment"),
    (r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', "single quotes"),
    (r"(\w+):", r'"\1":', "unquoted keys"),
]


def json_repair(text: str) -> Dict[str, Any]:
    """
    Intenta reparar JSON malformado aplicando una serie de transformaciones.
    Devuelve {ok, repaired, original, repairs_applied, attempts}.
    """
    original = text
    repairs_applied: List[str] = []
    current = text

    # Aplicar reglas una a una
    for pattern, repl, name in _REPAIR_RULES:
        new = re.sub(pattern, repl, current)
        if new != current:
            repairs_applied.append(name)
            current = new

    # Intentar parsear
    try:
        obj = json.loads(current)
        return {
            "ok": True,
            "repaired": current,
            "parsed": obj,
            "repairs_applied": repairs_applied,
            "original": original,
        }
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "error": str(e.msg),
            "repaired": current,
            "line": e.lineno,
            "column": e.colno,
            "repairs_applied": repairs_applied,
            "original": original,
        }


# ---------------------------------------------------------------------------
# Pretty / Minify / Format
# ---------------------------------------------------------------------------
def json_pretty(text: str, *, indent: int = 2, sort_keys: bool = False) -> Dict[str, Any]:
    """Formatea JSON con indentación bonita."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        repair = json_repair(text)
        if not repair["ok"]:
            return {"ok": False, "error": repair.get("error", "invalid JSON"), "input": text}
        obj = repair["parsed"]
    return {
        "ok": True,
        "output": json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False),
        "size_bytes": len(json.dumps(obj, ensure_ascii=False)),
    }


def json_minify(text: str) -> Dict[str, Any]:
    """Quita espacios innecesarios."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        repair = json_repair(text)
        if not repair["ok"]:
            return {"ok": False, "error": "invalid JSON"}
        obj = repair["parsed"]
    return {"ok": True, "output": json.dumps(obj, separators=(",", ":"), ensure_ascii=False)}


def json_sort_keys(text: str) -> Dict[str, Any]:
    """Re-ordena las claves alfabéticamente en todos los niveles."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid JSON"}
    sorted_obj = _deep_sort(obj)
    return {"ok": True, "output": json.dumps(sorted_obj, indent=2, ensure_ascii=False)}


def _deep_sort(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _deep_sort(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_deep_sort(x) for x in obj]
    return obj


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------
def json_diff(a: str, b: str) -> Dict[str, Any]:
    """
    Compara dos JSONs estructuralmente.
    Devuelve: {ok, identical, additions, removals, modifications, path}
    """
    try:
        obj_a = json.loads(a)
        obj_b = json.loads(b)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"invalid JSON: {e}"}

    diffs = _diff_objects(obj_a, obj_b, path="")
    return {
        "ok": True,
        "identical": len(diffs) == 0,
        "diff_count": len(diffs),
        "diffs": diffs[:100],  # cap a 100 para no saturar
    }


def _diff_objects(a: Any, b: Any, path: str = "") -> List[Dict[str, Any]]:
    diffs = []
    if type(a) != type(b):
        diffs.append({"path": path or "/", "type": "type_change", "from": a, "to": b})
        return diffs
    if isinstance(a, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in keys:
            sub = f"{path}.{k}" if path else k
            if k not in a:
                diffs.append({"path": sub, "type": "added", "value": b[k]})
            elif k not in b:
                diffs.append({"path": sub, "type": "removed", "value": a[k]})
            else:
                diffs.extend(_diff_objects(a[k], b[k], sub))
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append({"path": path or "/", "type": "length_change", "from": len(a), "to": len(b)})
        for i, (x, y) in enumerate(zip(a, b)):
            diffs.extend(_diff_objects(x, y, f"{path}[{i}]"))
    else:
        if a != b:
            diffs.append({"path": path or "/", "type": "modified", "from": a, "to": b})
    return diffs


# ---------------------------------------------------------------------------
# JSONPath (búsqueda simple)
# ---------------------------------------------------------------------------
def json_query(obj: Any, path: str) -> Dict[str, Any]:
    """
    Búsqueda estilo JSONPath simplificado:
    - "a.b.c" -> navega por claves
    - "a[0]"   -> indexa en array
    - "a.*"    -> wildcard
    Soporta la sintaxis básica más común.
    """
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError:
            return {"ok": False, "error": "input no es JSON válido"}

    try:
        # Parser simple
        tokens = _tokenize_path(path)
        result = _eval_path(obj, tokens)
        return {"ok": True, "result": result, "path": path}
    except (KeyError, IndexError, ValueError) as e:
        return {"ok": False, "error": f"path no encontrado: {e}", "path": path}


def _tokenize_path(path: str) -> List[str]:
    # Reemplaza "[" por ".[", luego split por "."
    path = path.replace("[", ".[")
    path = path.replace("]", "]")
    tokens = [t for t in path.split(".") if t]
    return tokens


def _eval_path(obj: Any, tokens: List[str]) -> Any:
    current = obj
    for tok in tokens:
        if tok == "*":
            if isinstance(current, dict):
                return list(current.values())
            if isinstance(current, list):
                return current
            return []
        if tok.endswith("]"):
            # index [0] o [name]
            inner = tok[:-1]
            if not inner:
                continue
            if inner.startswith("[") and inner.endswith("]"):
                inner = inner[1:-1]
            if inner.isdigit() or (inner.startswith("-") and inner[1:].isdigit()):
                current = current[int(inner)]
            else:
                # Quitar comillas
                inner = inner.strip("'\"")
                current = current[inner]
        else:
            if not isinstance(current, dict):
                raise KeyError(f"no se puede indexar {type(current).__name__} con clave {tok!r}")
            current = current[tok]
    return current


# ---------------------------------------------------------------------------
# Conversiones
# ---------------------------------------------------------------------------
def json_to_format(text: str, target_format: str) -> Dict[str, Any]:
    """Convierte JSON a YAML, CSV, TOML o XML."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        repair = json_repair(text)
        if not repair["ok"]:
            return {"ok": False, "error": "JSON inválido"}
        obj = repair["parsed"]

    target = target_format.lower()
    if target in ("yaml", "yml"):
        if not YAML_AVAILABLE:
            return {"ok": False, "error": "instala pyyaml (pip install pyyaml)"}
        return {"ok": True, "output": yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), "format": "yaml"}
    if target == "toml":
        if not TOML_AVAILABLE:
            return {"ok": False, "error": "instala toml (pip install toml)"}
        if not isinstance(obj, dict):
            return {"ok": False, "error": "TOML requiere objeto JSON raíz"}
        return {"ok": True, "output": toml.dumps(obj), "format": "toml"}
    if target == "csv":
        return _json_to_csv(obj)
    if target in ("xml",):
        return {"ok": True, "output": _to_xml(obj), "format": "xml"}
    return {"ok": False, "error": f"formato no soportado: {target_format}. Usa yaml/csv/toml/xml."}


def _json_to_csv(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, list):
        return {"ok": False, "error": "JSON→CSV requiere array de objetos"}
    if not obj:
        return {"ok": True, "output": "", "rows": 0}
    if not all(isinstance(x, dict) for x in obj):
        return {"ok": False, "error": "todos los items deben ser objetos"}
    keys = sorted({k for item in obj for k in item.keys()})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for row in obj:
        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    return {"ok": True, "output": output.getvalue(), "format": "csv", "rows": len(obj)}


def _to_xml(obj: Any, root: str = "root") -> str:
    """Conversión simple a XML."""
    parts = [f'<?xml version="1.0" encoding="UTF-8"?>', f"<{root}>"]
    parts.extend(_xml_body(obj, ""))
    parts.append(f"</{root}>")
    return "\n".join(parts)


def _xml_body(obj: Any, indent: str) -> str:
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            safe_k = re.sub(r"[^A-Za-z0-9_]", "_", str(k))
            if isinstance(v, (dict, list)):
                lines.append(f"{indent}<{safe_k}>")
                lines.extend(_xml_body(v, indent + "  "))
                lines.append(f"{indent}</{safe_k}>")
            else:
                val = str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lines.append(f"{indent}<{safe_k}>{val}</{safe_k}>")
    elif isinstance(obj, list):
        for item in obj:
            lines.append(f"{indent}<item>")
            lines.extend(_xml_body(item, indent + "  "))
            lines.append(f"{indent}</item>")
    else:
        val = str(obj).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"{indent}{val}")
    return lines


def format_to_json(text: str, source_format: str) -> Dict[str, Any]:
    """Convierte YAML/CSV/TOML a JSON."""
    src = source_format.lower()
    try:
        if src in ("yaml", "yml"):
            if not YAML_AVAILABLE:
                return {"ok": False, "error": "instala pyyaml"}
            obj = yaml.safe_load(text)
        elif src == "toml":
            if not TOML_AVAILABLE:
                return {"ok": False, "error": "instala toml"}
            obj = toml.loads(text)
        elif src == "csv":
            reader = csv.DictReader(io.StringIO(text))
            obj = list(reader)
        else:
            return {"ok": False, "error": f"formato no soportado: {source_format}"}
        return {"ok": True, "output": json.dumps(obj, indent=2, ensure_ascii=False), "format": "json"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Estadísticas y análisis
# ---------------------------------------------------------------------------
def json_stats(text: str) -> Dict[str, Any]:
    """Estadísticas de un JSON."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": "JSON inválido"}

    counts = {"objects": 0, "arrays": 0, "strings": 0, "numbers": 0, "booleans": 0, "nulls": 0}
    _count_types(obj, counts)

    keys = _collect_keys(obj)
    return {
        "ok": True,
        "size_bytes": len(text.encode("utf-8")),
        "depth_max": _max_depth(obj),
        "counts": counts,
        "total_nodes": sum(counts.values()),
        "unique_keys": sorted(set(keys)),
        "key_count": len(set(keys)),
    }


def _count_types(obj: Any, counts: Dict[str, int]) -> None:
    if isinstance(obj, dict):
        counts["objects"] += 1
        for v in obj.values():
            _count_types(v, counts)
    elif isinstance(obj, list):
        counts["arrays"] += 1
        for v in obj:
            _count_types(v, counts)
    elif isinstance(obj, bool):
        counts["booleans"] += 1
    elif isinstance(obj, (int, float)):
        counts["numbers"] += 1
    elif isinstance(obj, str):
        counts["strings"] += 1
    elif obj is None:
        counts["nulls"] += 1


def _max_depth(obj: Any, current: int = 0) -> int:
    if isinstance(obj, dict):
        if not obj:
            return current + 1
        return max(_max_depth(v, current + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return current + 1
        return max(_max_depth(v, current + 1) for v in obj)
    return current + 1


def _collect_keys(obj: Any) -> List[str]:
    keys = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(str(k))
            keys.extend(_collect_keys(v))
    elif isinstance(obj, list):
        for v in obj:
            keys.extend(_collect_keys(v))
    return keys


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------
def json_merge(*texts: str, deep: bool = True) -> Dict[str, Any]:
    """Mergea múltiples JSONs. El último gana en conflictos (shallow) o recursivo (deep)."""
    if not texts:
        return {"ok": False, "error": "no JSONs provided"}
    parsed: List[Any] = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"JSON inválido: {e}"}

    if deep:
        result: Any = parsed[0]
        for p in parsed[1:]:
            result = _deep_merge(result, p)
    else:
        result = {}
        for p in parsed:
            if isinstance(p, dict):
                result.update(p)
            else:
                result = p
    return {"ok": True, "output": json.dumps(result, indent=2, ensure_ascii=False)}


def _deep_merge(a: Any, b: Any) -> Any:
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            if k in out:
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    return b


# ---------------------------------------------------------------------------
# Hash & fingerprint
# ---------------------------------------------------------------------------
def json_fingerprint(text: str, *, algorithm: str = "sha256") -> Dict[str, Any]:
    """Hash estable del contenido (normalizado: keys ordenadas)."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": "JSON inválido"}
    normalized = json.dumps(_deep_sort(obj), separators=(",", ":"), ensure_ascii=False)
    algo = algorithm.lower()
    if algo not in hashlib.algorithms_available:
        return {"ok": False, "error": f"algoritmo no soportado: {algo}"}
    h = hashlib.new(algo, normalized.encode("utf-8")).hexdigest()
    return {"ok": True, "hash": h, "algorithm": algo, "size": len(normalized)}


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------
def json_read_file(file_path: str) -> Dict[str, Any]:
    """Lee un archivo JSON del disco con manejo de errores."""
    p = Path(file_path)
    if not p.exists():
        return {"ok": False, "error": f"archivo no existe: {file_path}"}
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = p.read_text(encoding="latin-1")
        except Exception as e:
            return {"ok": False, "error": f"encoding error: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"read error: {e}"}
    try:
        obj = json.loads(text)
        return {"ok": True, "parsed": obj, "size_bytes": len(text)}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON inválido en {file_path}: {e}", "raw": text[:500]}


def json_write_file(file_path: str, obj: Any, *, indent: int = 2, sort_keys: bool = False) -> Dict[str, Any]:
    """Escribe un objeto a un archivo JSON."""
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
        Path(file_path).write_text(text, encoding="utf-8")
        return {"ok": True, "file": file_path, "size_bytes": len(text)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# JSONL (JSON Lines)
# ---------------------------------------------------------------------------
def jsonl_parse(text: str) -> Dict[str, Any]:
    """Parsea JSON Lines (un objeto por línea)."""
    out = []
    errors = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append({"line": i, "error": str(e)})
    return {"ok": len(errors) == 0, "items": out, "count": len(out), "errors": errors}


def jsonl_format(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convierte una lista de objetos a JSON Lines."""
    try:
        out = "\n".join(json.dumps(it, ensure_ascii=False) for it in items)
        return {"ok": True, "output": out, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cases = [
        ('{"a": 1, "b": [1, 2, 3]}', "valid"),
        ('{"a": 1, "b": [1, 2, 3],}', "valid con trailing"),
        ("{'a': True, 'b': None}", "single quotes + python types"),
        ("not json at all", "inválido"),
    ]
    for text, label in cases:
        r = json_validate(text)
        print(f"[{label}] -> ok={r['ok']}, error={r.get('error', '-')}")
    print()
    bad = '{"a": 1, "b": [1, 2, 3],}'
    print("repair:", json_repair(bad)["repairs_applied"])
    print("pretty:", json_pretty(bad)["output"][:80])
    print("diff:", json_diff('{"a":1}', '{"a":2}')["diffs"])
    print("query:", json_query('{"users":[{"name":"alice"},{"name":"bob"}]}', "users[1].name")["result"])
