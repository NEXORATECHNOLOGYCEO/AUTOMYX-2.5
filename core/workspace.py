from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACES_ROOT = Path.home() / ".automyx" / "workspaces"

_instance: Optional[WorkspaceManager] = None


def _load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class WorkspaceManager:
    def __init__(self) -> None:
        WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
        self._current_name: str = "default"
        self._current_config: Dict[str, Any] = {}
        self._ensure_default()
        self.switch("default")

    def _ws_dir(self, name: str) -> Path:
        return WORKSPACES_ROOT / name

    def _config_path(self, name: str) -> Path:
        return self._ws_dir(name) / "config.json"

    def _ensure_default(self) -> None:
        if not self._config_path("default").exists():
            self.create("default", directory=str(Path.cwd()), description="Workspace por defecto")

    def create(
        self,
        name: str,
        directory: Optional[str] = None,
        model: Optional[str] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        ws_dir = self._ws_dir(name)
        ws_dir.mkdir(parents=True, exist_ok=True)
        (ws_dir / "memory").mkdir(exist_ok=True)

        config: Dict[str, Any] = {
            "name": name,
            "directory": directory or str(Path.cwd()),
            "model": model or "default",
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
        }
        _save_json(self._config_path(name), config)

        facts_path = ws_dir / "memory" / "facts.json"
        tasks_path = ws_dir / "memory" / "tasks.json"
        notes_path = ws_dir / "notes.md"
        if not facts_path.exists():
            _save_json(facts_path, [])
        if not tasks_path.exists():
            _save_json(tasks_path, [])
        if not notes_path.exists():
            notes_path.write_text("", encoding="utf-8")

        return config

    def switch(self, name: str) -> Dict[str, Any]:
        cfg_path = self._config_path(name)
        if not cfg_path.exists():
            raise FileNotFoundError(f"Workspace '{name}' no existe. Usa create() primero.")
        config = _load_json(cfg_path, {})
        config["last_used"] = datetime.now().isoformat()
        _save_json(cfg_path, config)
        self._current_name = name
        self._current_config = config
        return config

    def list_all(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for ws_dir in sorted(WORKSPACES_ROOT.iterdir()):
            if not ws_dir.is_dir():
                continue
            cfg = _load_json(ws_dir / "config.json", {})
            if not cfg:
                continue
            facts = _load_json(ws_dir / "memory" / "facts.json", [])
            tasks = _load_json(ws_dir / "memory" / "tasks.json", [])
            cfg["_stats"] = {"facts": len(facts), "tasks": len(tasks)}
            result.append(cfg)
        return result

    def delete(self, name: str, confirm: bool = False) -> str:
        if name == "default":
            raise ValueError("No se puede eliminar el workspace 'default'.")
        if not confirm:
            raise ValueError(f"Pasa confirm=True para eliminar el workspace '{name}'.")
        ws_dir = self._ws_dir(name)
        if not ws_dir.exists():
            raise FileNotFoundError(f"Workspace '{name}' no existe.")
        shutil.rmtree(ws_dir)
        if self._current_name == name:
            self.switch("default")
        return f"Workspace '{name}' eliminado."

    @property
    def current_name(self) -> str:
        return self._current_name

    @property
    def current_config(self) -> Dict[str, Any]:
        return self._current_config

    def get_context_string(self) -> str:
        cfg = self._current_config
        return (
            f"[WORKSPACE: {cfg.get('name', self._current_name)} | "
            f"Dir: {cfg.get('directory', '?')} | "
            f"Model: {cfg.get('model', 'default')}]"
        )

    def save_current_state(self, agent_history: list) -> None:
        ws_dir = self._ws_dir(self._current_name)
        history_path = ws_dir / "agent_history.json"
        filtered = []
        for msg in agent_history:
            if msg.get("role") == "system":
                continue
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 3000:
                content = content[:3000] + "…[truncado]"
            filtered.append({"role": msg.get("role"), "content": content})
        _save_json(history_path, {
            "saved_at": datetime.now().isoformat(),
            "messages": filtered[-40:],
        })

    def load_current_state(self) -> list:
        ws_dir = self._ws_dir(self._current_name)
        data = _load_json(ws_dir / "agent_history.json", {})
        return data.get("messages", [])


def get_workspace_manager() -> WorkspaceManager:
    global _instance
    if _instance is None:
        _instance = WorkspaceManager()
    return _instance
