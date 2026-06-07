"""
Notion Tools - Integración con Notion API
==========================================
Lee, crea, actualiza, busca y sincroniza páginas de Notion.
Requiere NOTION_API_KEY en .env.
"""
from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers() -> Dict[str, str]:
    key = os.environ.get("NOTION_API_KEY", "")
    if not key:
        return {}
    return {
        "Authorization": f"Bearer {key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _check() -> Dict[str, Any]:
    if not REQUESTS_AVAILABLE:
        return {"ok": False, "error": "instala requests (pip install requests)"}
    if not os.environ.get("NOTION_API_KEY"):
        return {"ok": False, "error": "configura NOTION_API_KEY en .env"}
    return {"ok": True}


# ---------------------------------------------------------------------------
# Búsqueda
# ---------------------------------------------------------------------------
def search(query: str = "", *, filter_type: Optional[str] = None, page_size: int = 50) -> Dict[str, Any]:
    """Busca páginas o bases de datos en Notion."""
    chk = _check()
    if not chk["ok"]:
        return chk
    payload: Dict[str, Any] = {"page_size": min(page_size, 100)}
    if query:
        payload["query"] = query
    if filter_type in ("page", "database"):
        payload["filter"] = {"value": filter_type, "property": "object"}

    try:
        r = requests.post(f"{NOTION_API_BASE}/search", headers=_headers(), json=payload, timeout=30)
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}"), "code": r.status_code}
        return {"ok": True, "results": data.get("results", []), "count": len(data.get("results", []))}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Leer
# ---------------------------------------------------------------------------
def get_page(page_id: str) -> Dict[str, Any]:
    """Obtiene una página por ID."""
    chk = _check()
    if not chk["ok"]:
        return chk
    try:
        r = requests.get(f"{NOTION_API_BASE}/pages/{page_id}", headers=_headers(), timeout=30)
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
        return {"ok": True, "page": data}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def get_page_content(page_id: str, *, max_blocks: int = 100) -> Dict[str, Any]:
    """Lee los bloques de contenido de una página."""
    chk = _check()
    if not chk["ok"]:
        return chk
    try:
        r = requests.get(f"{NOTION_API_BASE}/blocks/{page_id}/children?page_size={min(max_blocks, 100)}",
                         headers=_headers(), timeout=30)
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
        return {"ok": True, "blocks": data.get("results", []), "count": len(data.get("results", []))}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def get_database(database_id: str, *, filter_obj: Optional[Dict] = None, sorts: Optional[List[Dict]] = None, page_size: int = 50) -> Dict[str, Any]:
    """Query una base de datos con filtros opcionales."""
    chk = _check()
    if not chk["ok"]:
        return chk
    payload: Dict[str, Any] = {"page_size": min(page_size, 100)}
    if filter_obj:
        payload["filter"] = filter_obj
    if sorts:
        payload["sorts"] = sorts
    try:
        r = requests.post(f"{NOTION_API_BASE}/databases/{database_id}/query",
                          headers=_headers(), json=payload, timeout=30)
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
        return {"ok": True, "results": data.get("results", []), "count": len(data.get("results", []))}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Crear
# ---------------------------------------------------------------------------
def create_page(parent_id: str, title: str, *, content: Optional[str] = None,
                properties: Optional[Dict] = None, parent_type: str = "page",
                children: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Crea una página o entrada de base de datos."""
    chk = _check()
    if not chk["ok"]:
        return chk

    if parent_type == "database":
        props = properties or {"Name": {"title": [{"text": {"content": title}}]}}
        parent = {"database_id": parent_id}
    else:
        props = {"title": [{"text": {"content": title}}]}
        parent = {"page_id": parent_id}

    body_blocks: List[Dict] = []
    if content:
        body_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]},
        })
    if children:
        body_blocks.extend(children)
    if not body_blocks:
        body_blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}})

    payload = {"parent": parent, "properties": props, "children": body_blocks}
    try:
        r = requests.post(f"{NOTION_API_BASE}/pages", headers=_headers(), json=payload, timeout=30)
        data = r.json()
        if r.status_code not in (200, 201):
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}"), "code": r.status_code}
        return {"ok": True, "page": data, "url": data.get("url")}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Actualizar
# ---------------------------------------------------------------------------
def update_page(page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza las propiedades de una página."""
    chk = _check()
    if not chk["ok"]:
        return chk
    try:
        r = requests.patch(f"{NOTION_API_BASE}/pages/{page_id}",
                           headers=_headers(), json={"properties": properties}, timeout=30)
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
        return {"ok": True, "page": data}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def append_blocks(page_id: str, blocks: List[Dict]) -> Dict[str, Any]:
    """Añade bloques de contenido a una página."""
    chk = _check()
    if not chk["ok"]:
        return chk
    try:
        r = requests.patch(f"{NOTION_API_BASE}/blocks/{page_id}/children",
                           headers=_headers(), json={"children": blocks}, timeout=30)
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
        return {"ok": True, "added": len(data.get("results", []))}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def delete_page(page_id: str) -> Dict[str, Any]:
    """Archiva una página (Notion no permite delete real)."""
    chk = _check()
    if not chk["ok"]:
        return chk
    try:
        r = requests.patch(f"{NOTION_API_BASE}/pages/{page_id}",
                           headers=_headers(), json={"archived": True}, timeout=30)
        if r.status_code != 200:
            return {"ok": False, "error": r.json().get("message", f"HTTP {r.status_code}")}
        return {"ok": True, "archived": True, "page_id": page_id}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Markdown ↔ Notion blocks
# ---------------------------------------------------------------------------
def md_to_blocks(md_text: str) -> List[Dict]:
    """Conversión simple de Markdown a bloques Notion."""
    blocks = []
    for line in md_text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({
                "object": "block", "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]},
            })
        elif line.startswith("### "):
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]},
            })
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        elif line.startswith("> "):
            blocks.append({
                "object": "block", "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        elif line.startswith("```"):
            blocks.append({
                "object": "block", "type": "code",
                "code": {"rich_text": [{"type": "text", "text": {"content": ""}}], "language": "plain text"},
            })
        else:
            blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
            })
    return blocks


# ---------------------------------------------------------------------------
# Wrapper class
# ---------------------------------------------------------------------------
class NotionTools:
    @staticmethod
    def search(query: str = "", filter_type: Optional[str] = None) -> Dict[str, Any]:
        return search(query, filter_type=filter_type)

    @staticmethod
    def get_page(page_id: str) -> Dict[str, Any]:
        return get_page(page_id)

    @staticmethod
    def get_page_content(page_id: str) -> Dict[str, Any]:
        return get_page_content(page_id)

    @staticmethod
    def get_database(database_id: str) -> Dict[str, Any]:
        return get_database(database_id)

    @staticmethod
    def create_page(parent_id: str, title: str, content: Optional[str] = None, parent_type: str = "page") -> Dict[str, Any]:
        return create_page(parent_id, title, content=content, parent_type=parent_type)

    @staticmethod
    def update_page(page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        return update_page(page_id, properties)

    @staticmethod
    def append_blocks(page_id: str, markdown: str) -> Dict[str, Any]:
        return append_blocks(page_id, md_to_blocks(markdown))

    @staticmethod
    def delete_page(page_id: str) -> Dict[str, Any]:
        return delete_page(page_id)
