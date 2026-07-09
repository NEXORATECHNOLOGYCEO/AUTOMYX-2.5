"""
Notion Tools — Integración completa con Notion API v1
Requiere NOTION_API_KEY en .env o pasado como argumento token=
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION  = "2022-06-28"


# ─── token helpers ───────────────────────────────────────────────────────────

def _active_token(token: str = "") -> str:
    return (token or os.environ.get("NOTION_API_KEY", "")).strip()


def _save_token(token: str) -> None:
    token = token.strip()
    os.environ["NOTION_API_KEY"] = token
    env_path = Path(__file__).parent.parent / ".env"
    lines: List[str] = []
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("NOTION_API_KEY="):
                lines.append(line)
    lines.append(f"NOTION_API_KEY={token}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _headers(token: str = "") -> Dict[str, str]:
    key = _active_token(token)
    if not key:
        return {}
    return {
        "Authorization":  f"Bearer {key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }


def _check(token: str = "") -> Dict[str, Any]:
    if not REQUESTS_AVAILABLE:
        return {"ok": False, "error": "instala requests: pip install requests"}
    key = _active_token(token)
    if not key:
        return {
            "ok": False,
            "error": (
                "NOTION_API_KEY no configurado.\n"
                "Dime tu token (empieza con ntn_ o secret_) y lo guardo automáticamente,\n"
                "o ejecuta /onboard para configurarlo."
            ),
        }
    return {"ok": True, "key": key}


def _extract_title(obj: Dict) -> str:
    try:
        props = obj.get("properties", {})
        for k in ("Name", "Title", "title", "Nombre"):
            p = props.get(k, {})
            tv = p.get("title") or p.get("rich_text") or []
            if tv:
                return "".join(t.get("plain_text", "") for t in tv)
        return obj.get("id", "?")
    except Exception:
        return "?"


def _req(method: str, endpoint: str, token: str = "",
         body: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    """HTTP helper central."""
    key = _active_token(token)
    url = f"{NOTION_API_BASE}/{endpoint}"
    try:
        r = requests.request(
            method, url,
            headers=_headers(key),
            json=body,
            params=params,
            timeout=30,
        )
        data = r.json()
        if r.status_code not in (200, 201):
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}"),
                    "status": r.status_code, "details": data}
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ─── set token ───────────────────────────────────────────────────────────────

def set_token(token: str = "", **kwargs) -> Dict[str, Any]:
    """Guarda un token de Notion en .env y en el entorno actual."""
    tok = (token or kwargs.get("notion_token") or kwargs.get("api_key") or "").strip()
    if not tok:
        return {"ok": False, "error": "Token vacío"}
    _save_token(tok)
    return {"ok": True, "message": f"Token guardado ({tok[:12]}...)"}


# ─── search ──────────────────────────────────────────────────────────────────

def search(query: str = "", **kwargs) -> Dict[str, Any]:
    """
    Busca páginas y bases de datos en Notion.
    Acepta: query, filter_type ('page'|'database'), page_size, token
    """
    token       = kwargs.get("token", "")
    filter_type = kwargs.get("filter_type") or kwargs.get("type") or ""
    page_size   = int(kwargs.get("page_size", 50))

    chk = _check(token)
    if not chk["ok"]:
        return chk

    payload: Dict[str, Any] = {"page_size": min(page_size, 100)}
    if query:
        payload["query"] = query
    if filter_type in ("page", "database"):
        payload["filter"] = {"value": filter_type, "property": "object"}

    res = _req("POST", "search", token=chk["key"], body=payload)
    if not res["ok"]:
        return res

    results = res["data"].get("results", [])
    return {
        "ok":    True,
        "count": len(results),
        "items": [
            {
                "id":    obj.get("id"),
                "type":  obj.get("object"),
                "title": _extract_title(obj),
                "url":   obj.get("url"),
            }
            for obj in results
        ],
    }


# ─── get_page ────────────────────────────────────────────────────────────────

def get_page(page_id: str = "", **kwargs) -> Dict[str, Any]:
    """Obtiene metadata de una página por ID."""
    page_id = page_id or kwargs.get("id") or kwargs.get("page_id") or ""
    token   = kwargs.get("token", "")
    chk = _check(token)
    if not chk["ok"]:
        return chk
    if not page_id:
        return {"ok": False, "error": "Falta page_id"}

    res = _req("GET", f"pages/{page_id}", token=chk["key"])
    if not res["ok"]:
        return res
    obj = res["data"]
    return {
        "ok":    True,
        "id":    obj.get("id"),
        "title": _extract_title(obj),
        "url":   obj.get("url"),
        "created": obj.get("created_time"),
        "edited":  obj.get("last_edited_time"),
    }


# ─── get_page_content ────────────────────────────────────────────────────────

def get_page_content(page_id: str = "", **kwargs) -> Dict[str, Any]:
    """Lee los bloques de contenido de una página."""
    page_id    = page_id or kwargs.get("id") or kwargs.get("page_id") or ""
    token      = kwargs.get("token", "")
    max_blocks = int(kwargs.get("max_blocks", 100))
    chk = _check(token)
    if not chk["ok"]:
        return chk
    if not page_id:
        return {"ok": False, "error": "Falta page_id"}

    res = _req("GET", f"blocks/{page_id}/children",
               token=chk["key"], params={"page_size": min(max_blocks, 100)})
    if not res["ok"]:
        return res
    blocks = res["data"].get("results", [])
    return {"ok": True, "count": len(blocks), "blocks": blocks}


# ─── get_database ────────────────────────────────────────────────────────────

def get_database(database_id: str = "", **kwargs) -> Dict[str, Any]:
    """Query una base de datos Notion."""
    database_id = database_id or kwargs.get("db_id") or kwargs.get("id") or ""
    token       = kwargs.get("token", "")
    filter_obj  = kwargs.get("filter_obj") or kwargs.get("filter") or None
    sorts       = kwargs.get("sorts") or None
    page_size   = int(kwargs.get("page_size", 50))
    chk = _check(token)
    if not chk["ok"]:
        return chk
    if not database_id:
        return {"ok": False, "error": "Falta database_id"}

    body: Dict[str, Any] = {"page_size": min(page_size, 100)}
    if filter_obj:
        body["filter"] = filter_obj
    if sorts:
        body["sorts"] = sorts

    res = _req("POST", f"databases/{database_id}/query", token=chk["key"], body=body)
    if not res["ok"]:
        return res
    rows = res["data"].get("results", [])
    return {
        "ok":    True,
        "count": len(rows),
        "rows": [
            {
                "id":    r.get("id"),
                "url":   r.get("url"),
                "title": _extract_title(r),
            }
            for r in rows
        ],
    }


# ─── create_page ─────────────────────────────────────────────────────────────

def create_page(**kwargs) -> Dict[str, Any]:
    """
    Crea una página en Notion.
    Args: parent_id, title, content (str), children (list), parent_type ('page'|'database'), token
    """
    parent_id   = (kwargs.get("parent_id") or kwargs.get("page_id") or
                   kwargs.get("parent") or kwargs.get("id") or "").strip()
    title       = (kwargs.get("title") or kwargs.get("name") or "Sin título").strip()
    content     = kwargs.get("content") or kwargs.get("body") or kwargs.get("text") or ""
    children    = kwargs.get("children") or kwargs.get("blocks") or []
    parent_type = kwargs.get("parent_type") or kwargs.get("type") or "page"
    token       = kwargs.get("token", "")
    properties  = kwargs.get("properties") or None

    chk = _check(token)
    if not chk["ok"]:
        return chk
    if not parent_id:
        return {"ok": False, "error": "Falta parent_id (el ID de la página o base de datos padre)"}

    if parent_type == "database":
        props = properties or {"Name": {"title": [{"text": {"content": title}}]}}
        parent = {"database_id": parent_id}
    else:
        props  = {"title": [{"text": {"content": title}}]}
        parent = {"page_id": parent_id}

    body_blocks: List[Dict] = []
    if isinstance(content, str) and content.strip():
        for chunk in [content[i:i+2000] for i in range(0, len(content), 2000)]:
            body_blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
            })
    if isinstance(children, list):
        body_blocks.extend(children)
    if not body_blocks:
        body_blocks.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": []},
        })

    payload = {"parent": parent, "properties": props, "children": body_blocks}
    res = _req("POST", "pages", token=chk["key"], body=payload)
    if not res["ok"]:
        return res
    obj = res["data"]
    return {
        "ok":    True,
        "id":    obj.get("id"),
        "url":   obj.get("url"),
        "title": title,
        "message": f"Página '{title}' creada. URL: {obj.get('url', '(sin URL pública)')}",
    }


# ─── update_page ─────────────────────────────────────────────────────────────

def update_page(page_id: str = "", **kwargs) -> Dict[str, Any]:
    """Actualiza propiedades de una página."""
    page_id    = page_id or kwargs.get("id") or kwargs.get("page_id") or ""
    properties = kwargs.get("properties") or {}
    token      = kwargs.get("token", "")
    chk = _check(token)
    if not chk["ok"]:
        return chk
    if not page_id:
        return {"ok": False, "error": "Falta page_id"}

    res = _req("PATCH", f"pages/{page_id}", token=chk["key"], body={"properties": properties})
    if not res["ok"]:
        return res
    return {"ok": True, "id": page_id, "message": "Página actualizada"}


# ─── append_blocks ───────────────────────────────────────────────────────────

def append_blocks(page_id: str = "", **kwargs) -> Dict[str, Any]:
    """Añade bloques (o markdown) a una página existente."""
    page_id  = page_id or kwargs.get("id") or kwargs.get("page_id") or ""
    blocks   = kwargs.get("blocks") or []
    markdown = kwargs.get("markdown") or kwargs.get("content") or kwargs.get("text") or ""
    token    = kwargs.get("token", "")
    chk = _check(token)
    if not chk["ok"]:
        return chk
    if not page_id:
        return {"ok": False, "error": "Falta page_id"}

    if not blocks and markdown:
        blocks = md_to_blocks(markdown)
    if not blocks:
        return {"ok": False, "error": "Sin contenido para añadir"}

    res = _req("PATCH", f"blocks/{page_id}/children", token=chk["key"], body={"children": blocks})
    if not res["ok"]:
        return res
    return {"ok": True, "added": len(res["data"].get("results", [])), "page_id": page_id}


# ─── delete_page ─────────────────────────────────────────────────────────────

def delete_page(page_id: str = "", **kwargs) -> Dict[str, Any]:
    """Archiva una página (Notion no permite borrado permanente vía API)."""
    page_id = page_id or kwargs.get("id") or kwargs.get("page_id") or ""
    token   = kwargs.get("token", "")
    chk = _check(token)
    if not chk["ok"]:
        return chk
    if not page_id:
        return {"ok": False, "error": "Falta page_id"}

    res = _req("PATCH", f"pages/{page_id}", token=chk["key"], body={"archived": True})
    if not res["ok"]:
        return res
    return {"ok": True, "archived": True, "page_id": page_id}


# ─── md_to_blocks ────────────────────────────────────────────────────────────

def md_to_blocks(md_text: str) -> List[Dict]:
    """Convierte Markdown simple a bloques Notion."""
    blocks = []
    for line in md_text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}})
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("> "):
            blocks.append({"object": "block", "type": "quote",
                           "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}})
    return blocks


# ─── NotionTools wrapper (para compatibilidad con tool_registry) ──────────────

class NotionTools:
    @staticmethod
    def search(query: str = "", filter_type: Optional[str] = None, **kw) -> Dict[str, Any]:
        return search(query, filter_type=filter_type, **kw)

    @staticmethod
    def get_page(page_id: str = "", **kw) -> Dict[str, Any]:
        return get_page(page_id, **kw)

    @staticmethod
    def get_page_content(page_id: str = "", **kw) -> Dict[str, Any]:
        return get_page_content(page_id, **kw)

    @staticmethod
    def get_database(database_id: str = "", **kw) -> Dict[str, Any]:
        return get_database(database_id, **kw)

    @staticmethod
    def create_page(**kw) -> Dict[str, Any]:
        return create_page(**kw)

    @staticmethod
    def update_page(page_id: str = "", **kw) -> Dict[str, Any]:
        return update_page(page_id, **kw)

    @staticmethod
    def append_blocks(page_id: str = "", **kw) -> Dict[str, Any]:
        return append_blocks(page_id, **kw)

    @staticmethod
    def delete_page(page_id: str = "", **kw) -> Dict[str, Any]:
        return delete_page(page_id, **kw)

    @staticmethod
    def set_token(token: str = "", **kw) -> Dict[str, Any]:
        return set_token(token, **kw)
