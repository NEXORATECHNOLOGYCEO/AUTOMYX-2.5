"""
Obsidian Tools - Trabajajar con vaults de Obsidian
===================================================
Lee, crea, busca y enlaza notas en un vault local de Obsidian.
No requiere API porque Obsidian es 100% archivos Markdown.
"""
from __future__ import annotations

import os
import re
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------
def get_default_vault() -> Optional[Path]:
    """Encuentra el vault de Obsidian por defecto en la plataforma."""
    home = Path(os.path.expanduser("~"))
    candidates = [
        home / "Documents" / "Obsidian",
        home / "Documents" / "ObsidianVault",
        home / "Obsidian",
        home / "Documents" / "MyVault",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            # Verificar que tiene .obsidian
            if (c / ".obsidian").exists():
                return c
    # Buscar recursivamente uno con .obsidian
    for c in (home / "Documents").rglob(".obsidian"):
        if c.is_dir():
            return c.parent
    return None


def list_vaults() -> List[Dict[str, Any]]:
    """Lista todos los vaults detectados."""
    home = Path(os.path.expanduser("~"))
    vaults = []
    seen = set()
    for obs_dir in home.rglob(".obsidian"):
        if not obs_dir.is_dir() or str(obs_dir) in seen:
            continue
        vault = obs_dir.parent
        seen.add(str(obs_dir))
        note_count = sum(1 for _ in vault.rglob("*.md"))
        vaults.append({
            "name": vault.name,
            "path": str(vault),
            "note_count": note_count,
        })
    return vaults


# ---------------------------------------------------------------------------
# Búsqueda
# ---------------------------------------------------------------------------
def search_notes(vault_path: str, query: str, *, max_results: int = 50, include_content: bool = False) -> Dict[str, Any]:
    """Busca notas por título o contenido."""
    vault = Path(vault_path)
    if not vault.exists():
        return {"ok": False, "error": f"vault no existe: {vault_path}"}

    q = query.lower()
    results: List[Dict[str, Any]] = []
    for md_file in vault.rglob("*.md"):
        if any(part.startswith(".") for part in md_file.parts):
            continue
        title = md_file.stem
        if q in title.lower():
            results.append({"path": str(md_file), "title": title, "match": "title"})
        elif include_content:
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
                if q in text.lower():
                    snippet = _extract_snippet(text, q)
                    results.append({
                        "path": str(md_file),
                        "title": title,
                        "match": "content",
                        "snippet": snippet,
                    })
            except Exception:
                continue
        if len(results) >= max_results:
            break

    return {"ok": True, "count": len(results), "results": results}


def _extract_snippet(text: str, query: str, context_chars: int = 80) -> str:
    idx = text.lower().find(query.lower())
    if idx < 0:
        return text[:200]
    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(query) + context_chars)
    snippet = text[start:end].replace("\n", " ")
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


# ---------------------------------------------------------------------------
# Crear / Actualizar
# ---------------------------------------------------------------------------
def create_note(vault_path: str, title: str, content: str = "", *, folder: str = "", tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Crea una nota nueva en el vault."""
    vault = Path(vault_path)
    if not vault.exists():
        return {"ok": False, "error": f"vault no existe: {vault_path}"}

    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    target_dir = vault / folder if folder else vault
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{safe_title}.md"

    if target_file.exists():
        return {"ok": False, "error": f"ya existe: {target_file}"}

    # Frontmatter YAML
    frontmatter_lines = ["---", f"title: {title}", f"created: {time.strftime('%Y-%m-%dT%H:%M:%S')}"]
    if tags:
        frontmatter_lines.append("tags:")
        for t in tags:
            frontmatter_lines.append(f"  - {t}")
    frontmatter_lines.append("---\n")
    frontmatter = "\n".join(frontmatter_lines)

    body = f"\n{content}\n" if content else "\n"
    target_file.write_text(frontmatter + body, encoding="utf-8")
    return {"ok": True, "path": str(target_file), "title": title, "size_bytes": len(frontmatter + body)}


def append_to_note(file_path: str, content: str) -> Dict[str, Any]:
    """Añade contenido al final de una nota."""
    p = Path(file_path)
    if not p.exists():
        return {"ok": False, "error": f"nota no existe: {file_path}"}
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"\n{content}\n")
        return {"ok": True, "path": file_path, "appended_chars": len(content)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def read_note(file_path: str) -> Dict[str, Any]:
    """Lee el contenido de una nota."""
    p = Path(file_path)
    if not p.exists():
        return {"ok": False, "error": f"nota no existe: {file_path}"}
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
        meta = _parse_frontmatter(text)
        return {
            "ok": True,
            "path": file_path,
            "title": meta.get("title", p.stem),
            "tags": meta.get("tags", []),
            "content": text,
            "size_bytes": len(text),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """Extrae frontmatter YAML simple (sin lib externa)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = text[3:end].strip()
    out: Dict[str, Any] = {}
    current_list_key = None
    for line in fm.splitlines():
        line = line.rstrip()
        if line.startswith("  - "):
            if current_list_key:
                out.setdefault(current_list_key, []).append(line[4:].strip())
        elif ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if not v:
                current_list_key = k
            else:
                out[k] = v
    return out


# ---------------------------------------------------------------------------
# Grafo de enlaces
# ---------------------------------------------------------------------------
WIKILINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]*)?\]\]")


def graph(vault_path: str, *, max_nodes: int = 500) -> Dict[str, Any]:
    """Construye el grafo de enlaces [[wikilink]] del vault."""
    vault = Path(vault_path)
    if not vault.exists():
        return {"ok": False, "error": f"vault no existe: {vault_path}"}

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, str]] = []

    for md in vault.rglob("*.md"):
        if any(part.startswith(".") for part in md.parts):
            continue
        title = md.stem
        nodes[title] = {"path": str(md), "outgoing": [], "incoming": 0}
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip()
            if target == title:
                continue
            edges.append({"from": title, "to": target})
            nodes[title]["outgoing"].append(target)
            nodes.setdefault(target, {"path": "", "outgoing": [], "incoming": 0})
            nodes[target]["incoming"] += 1

    # Detectar huérfanos
    orphans = [n for n, d in nodes.items() if not d.get("path") or (not d["outgoing"] and d["incoming"] == 0)]

    return {
        "ok": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "orphan_count": len(orphans),
        "orphans": orphans[:50],
        "nodes": dict(list(nodes.items())[:max_nodes]),
    }


# ---------------------------------------------------------------------------
# Daily note
# ---------------------------------------------------------------------------
def daily_note(vault_path: str, content: str = "", *, template: Optional[str] = None) -> Dict[str, Any]:
    """Crea o abre la nota del día actual."""
    vault = Path(vault_path)
    today = time.strftime("%Y-%m-%d")
    target = vault / "daily" / f"{today}.md"
    if target.exists() and not content:
        text = target.read_text(encoding="utf-8", errors="ignore")
        return {"ok": True, "path": str(target), "content": text, "existed": True}
    body = template or f"# {today}\n\n## Notas del día\n\n{content}\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return {"ok": True, "path": str(target), "content": body, "existed": False}


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
def list_tags(vault_path: str) -> Dict[str, Any]:
    """Lista todos los tags del vault con su frecuencia."""
    vault = Path(vault_path)
    if not vault.exists():
        return {"ok": False, "error": f"vault no existe: {vault_path}"}
    tag_re = re.compile(r"#([A-Za-z0-9_\-/\.]+)")
    tags: Dict[str, int] = {}
    for md in vault.rglob("*.md"):
        if any(part.startswith(".") for part in md.parts):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in tag_re.finditer(text):
            t = m.group(1)
            tags[t] = tags.get(t, 0) + 1
    sorted_tags = sorted(tags.items(), key=lambda x: -x[1])
    return {
        "ok": True,
        "count": len(sorted_tags),
        "tags": [{"name": t, "count": c} for t, c in sorted_tags],
    }


# ---------------------------------------------------------------------------
# Wrapper class
# ---------------------------------------------------------------------------
class ObsidianTools:
    @staticmethod
    def list_vaults() -> Dict[str, Any]:
        return {"ok": True, "vaults": list_vaults()}

    @staticmethod
    def search(vault_path: str, query: str, include_content: bool = True) -> Dict[str, Any]:
        return search_notes(vault_path, query, include_content=include_content)

    @staticmethod
    def create_note(vault_path: str, title: str, content: str = "", folder: str = "", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        return create_note(vault_path, title, content, folder=folder, tags=tags or [])

    @staticmethod
    def read_note(file_path: str) -> Dict[str, Any]:
        return read_note(file_path)

    @staticmethod
    def append(file_path: str, content: str) -> Dict[str, Any]:
        return append_to_note(file_path, content)

    @staticmethod
    def graph(vault_path: str) -> Dict[str, Any]:
        return graph(vault_path)

    @staticmethod
    def daily(vault_path: str, content: str = "") -> Dict[str, Any]:
        return daily_note(vault_path, content)

    @staticmethod
    def tags(vault_path: str) -> Dict[str, Any]:
        return list_tags(vault_path)
