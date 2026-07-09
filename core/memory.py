"""
AUTOMYX MEMORY SYSTEM
=====================
Memoria persistente entre sesiones: facts, historial LLM, notas.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

MEMORY_DIR   = Path.home() / ".automyx" / "memory"
FACTS_FILE   = MEMORY_DIR / "facts.json"
HISTORY_FILE = MEMORY_DIR / "agent_history.json"
NOTES_FILE   = MEMORY_DIR / "notes.json"
TASKS_FILE   = MEMORY_DIR / "tasks.json"


def _ensure():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _save(path: Path, data):
    _ensure()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class MemoryManager:
    """Gestiona la memoria persistente de Automyx."""

    def __init__(self):
        _ensure()
        self.facts: List[Dict[str, Any]] = _load(FACTS_FILE, [])
        self.notes: List[Dict[str, Any]] = _load(NOTES_FILE, [])

    # ── Facts ──────────────────────────────────────────────────────────────

    def remember(self, fact: str, category: str = "general") -> str:
        entry = {
            "id": (self.facts[-1]["id"] + 1) if self.facts else 1,
            "fact": fact.strip(),
            "category": category,
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.facts.append(entry)
        _save(FACTS_FILE, self.facts)
        return f"Memorizado: {fact[:80]}"

    def forget(self, fact_id: int) -> str:
        before = len(self.facts)
        self.facts = [f for f in self.facts if f.get("id") != fact_id]
        _save(FACTS_FILE, self.facts)
        return "Eliminado" if len(self.facts) < before else f"No se encontro fact #{fact_id}"

    def clear_facts(self):
        self.facts = []
        _save(FACTS_FILE, [])

    def get_facts_context(self) -> str:
        if not self.facts:
            return ""
        lines = ["[MEMORIA PERSISTENTE - lo que Automyx recuerda sobre ti y el proyecto]"]
        for f in self.facts[-30:]:
            lines.append(f"- [{f.get('category', 'general')}] {f['fact']}")
        return "\n".join(lines)

    # ── Notes ──────────────────────────────────────────────────────────────

    def add_note(self, note: str) -> str:
        entry = {"note": note.strip(), "at": datetime.now().strftime("%Y-%m-%d %H:%M")}
        self.notes.append(entry)
        self.notes = self.notes[-50:]
        _save(NOTES_FILE, self.notes)
        return "Nota guardada"

    # ── Agent LLM history ─────────────────────────────────────────────────

    def save_agent_history(self, history: list, max_pairs: int = 20):
        """Guarda los ultimos max_pairs pares (user + assistant) del historial LLM."""
        filtered = []
        for msg in history:
            role = msg.get("role", "")
            if role == "system":
                continue
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 3000:
                content = content[:3000] + "…[truncado]"
            elif isinstance(content, list):
                content = str(content)[:1000]
            filtered.append({"role": role, "content": content})

        keep = filtered[-(max_pairs * 2):]
        _save(HISTORY_FILE, {
            "saved_at": datetime.now().isoformat(),
            "count": len(keep),
            "messages": keep,
        })

    def load_agent_history(self) -> list:
        """Carga el historial LLM guardado."""
        data = _load(HISTORY_FILE, {})
        return data.get("messages", [])

    def clear_history(self):
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()

    # ── Tasks ─────────────────────────────────────────────────────────────

    def save_task(self, task: str, tools_count: int = 0,
                  skill_saved: str = None, result_preview: str = "") -> None:
        tasks = _load(TASKS_FILE, [])
        tasks.append({
            "task": task.strip(),
            "tools": tools_count,
            "skill": skill_saved,
            "preview": result_preview[:200],
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        _save(TASKS_FILE, tasks[-100:])

    def get_recent_tasks(self, n: int = 10) -> List[Dict[str, Any]]:
        tasks = _load(TASKS_FILE, [])
        return tasks[-n:]

    # ── Stats ─────────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        hist  = self.load_agent_history()
        tasks = _load(TASKS_FILE, [])
        return {
            "facts":     len(self.facts),
            "notes":     len(self.notes),
            "hist_msgs": len(hist),
            "tasks":     len(tasks),
            "dir":       str(MEMORY_DIR),
        }
