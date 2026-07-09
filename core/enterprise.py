from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

_INSTANCE: Optional[EnterpriseManager] = None

_ROLES = {
    "admin": {"execute", "read", "write", "manage_users", "view_history"},
    "developer": {"execute", "read", "write", "view_history"},
    "viewer": {"read", "view_history"},
}

_BASE_DIR = Path(os.path.expanduser("~")) / ".automyx" / "enterprise"


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return dk.hex(), salt


class EnterpriseManager:
    def __init__(self):
        _BASE_DIR.mkdir(parents=True, exist_ok=True)
        self._config_path = _BASE_DIR / "config.json"
        self._users_path = _BASE_DIR / "users.json"
        self._log_path = _BASE_DIR / "team_log.jsonl"
        self._tokens: dict[str, dict] = {}
        self._config: dict = {}
        self._users: dict = {}
        self._load()

    def _load(self):
        if self._config_path.exists():
            try:
                self._config = json.loads(self._config_path.read_text(encoding="utf-8"))
            except Exception:
                self._config = {}
        if self._users_path.exists():
            try:
                self._users = json.loads(self._users_path.read_text(encoding="utf-8"))
            except Exception:
                self._users = {}

    def _save_config(self):
        self._config_path.write_text(json.dumps(self._config, indent=2), encoding="utf-8")

    def _save_users(self):
        self._users_path.write_text(json.dumps(self._users, indent=2), encoding="utf-8")

    @property
    def is_enabled(self) -> bool:
        return bool(self._config.get("org_name"))

    def setup(self, org_name: str, admin_username: str, admin_password: str) -> dict:
        self._config = {
            "org_name": org_name,
            "created_at": datetime.now().isoformat(),
            "version": "2.5",
        }
        self._save_config()
        result = self.create_user(admin_username, admin_password, "admin")
        return {"ok": True, "org": org_name, "admin": admin_username, "user_created": result.get("ok")}

    def create_user(self, username: str, password: str, role: str) -> dict:
        if role not in _ROLES:
            return {"ok": False, "error": f"Rol inválido: {role}. Usa: {list(_ROLES.keys())}"}
        if username in self._users:
            return {"ok": False, "error": f"Usuario '{username}' ya existe"}

        hashed, salt = _hash_password(password)
        self._users[username] = {
            "role": role,
            "password_hash": hashed,
            "salt": salt,
            "created_at": datetime.now().isoformat(),
            "active": True,
        }
        self._save_users()
        return {"ok": True, "username": username, "role": role}

    def authenticate(self, username: str, password: str) -> dict:
        user = self._users.get(username)
        if not user:
            return {"ok": False, "error": "Usuario no encontrado"}
        if not user.get("active", True):
            return {"ok": False, "error": "Usuario desactivado"}

        hashed, _ = _hash_password(password, user["salt"])
        if hashed != user["password_hash"]:
            return {"ok": False, "error": "Contraseña incorrecta"}

        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=24)
        self._tokens[token] = {
            "username": username,
            "role": user["role"],
            "expires_at": expiry.isoformat(),
        }
        return {"ok": True, "token": token, "role": user["role"], "username": username, "expires_at": expiry.isoformat()}

    def verify_token(self, token: str) -> Optional[dict]:
        entry = self._tokens.get(token)
        if not entry:
            return None
        if datetime.fromisoformat(entry["expires_at"]) < datetime.now():
            del self._tokens[token]
            return None
        return {"username": entry["username"], "role": entry["role"]}

    def check_permission(self, token: str, action: str) -> bool:
        user_info = self.verify_token(token)
        if not user_info:
            return False
        allowed = _ROLES.get(user_info["role"], set())
        return action in allowed

    def list_users(self) -> list[dict]:
        result = []
        for username, data in self._users.items():
            result.append({
                "username": username,
                "role": data["role"],
                "active": data.get("active", True),
                "created_at": data.get("created_at"),
            })
        return result

    def deactivate_user(self, username: str) -> dict:
        if username not in self._users:
            return {"ok": False, "error": f"Usuario '{username}' no encontrado"}
        self._users[username]["active"] = False
        self._save_users()
        tokens_to_remove = [t for t, d in self._tokens.items() if d["username"] == username]
        for t in tokens_to_remove:
            del self._tokens[t]
        return {"ok": True, "username": username, "status": "deactivated"}

    def get_team_history(self, n: int = 20) -> list[dict]:
        if not self._log_path.exists():
            return []
        lines = self._log_path.read_text(encoding="utf-8").strip().splitlines()
        entries: list[dict] = []
        for line in lines:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return entries[-n:]

    def log_team_action(self, username: str, task: str, result_preview: str):
        entry = {
            "username": username,
            "task": task,
            "result_preview": result_preview[:200],
            "timestamp": datetime.now().isoformat(),
        }
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_current_user(self) -> Optional[str]:
        return os.environ.get("AUTOMYX_USER")


def get_enterprise() -> EnterpriseManager:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = EnterpriseManager()
    return _INSTANCE
