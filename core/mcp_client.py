from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from itertools import count
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

try:
    import urllib.request
    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False

_INSTANCE: Optional[MCPClient] = None
_id_counter = count(1)


def _next_id() -> int:
    return next(_id_counter)


class _StdioServer:
    def __init__(self, server_id: str, command: str, args: list[str]):
        self.server_id = server_id
        self.command = command
        self.args = args
        self.proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._initialized = False

    def start(self):
        self.proc = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._initialize()

    def _initialize(self):
        result = self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "automyx", "version": "2.5"},
        })
        if result:
            self._send("notifications/initialized", {})
            self._initialized = True

    def _send(self, method: str, params: dict = {}) -> Any:
        if not self.proc:
            return None
        msg = json.dumps({"jsonrpc": "2.0", "id": _next_id(), "method": method, "params": params})
        with self._lock:
            try:
                self.proc.stdin.write(msg.encode() + b"\n")
                self.proc.stdin.flush()
                if method.startswith("notifications/"):
                    return None
                line = self.proc.stdout.readline()
                if not line:
                    return None
                response = json.loads(line.decode("utf-8", errors="replace"))
                return response.get("result")
            except Exception:
                return None

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                pass
            self.proc = None


class _HttpServer:
    def __init__(self, server_id: str, url: str, headers: dict):
        self.server_id = server_id
        self.url = url
        self.headers = headers

    def _send(self, method: str, params: dict = {}) -> Any:
        payload = json.dumps({"jsonrpc": "2.0", "id": _next_id(), "method": method, "params": params}).encode()
        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json", **self.headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data.get("result")
        except Exception:
            return None

    def stop(self):
        pass


class MCPClient:
    def __init__(self):
        self._servers: dict[str, Any] = {}
        self._config_path = Path(os.path.expanduser("~")) / ".automyx" / "mcp_servers.json"
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_config()

    def _load_config(self):
        if self._config_path.exists():
            try:
                self._saved_config = json.loads(self._config_path.read_text(encoding="utf-8"))
            except Exception:
                self._saved_config = {}
        else:
            self._saved_config = {}

    def _save_config(self):
        config = {}
        for sid, srv in self._servers.items():
            if isinstance(srv, _StdioServer):
                config[sid] = {"type": "stdio", "command": srv.command, "args": srv.args}
            elif isinstance(srv, _HttpServer):
                config[sid] = {"type": "http", "url": srv.url, "headers": srv.headers}
        self._config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def connect_stdio(self, command: str, args: list[str] = []) -> dict:
        server_id = f"{command}-{len(self._servers)}"
        srv = _StdioServer(server_id, command, args)
        try:
            srv.start()
            self._servers[server_id] = srv
            self._save_config()
            return {"ok": True, "server_id": server_id, "type": "stdio", "initialized": srv._initialized}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def connect_http(self, url: str, headers: dict = {}) -> dict:
        server_id = urlparse(url).netloc or url
        srv = _HttpServer(server_id, url, headers)
        self._servers[server_id] = srv
        self._save_config()
        return {"ok": True, "server_id": server_id, "type": "http"}

    def disconnect(self, server_id: str) -> dict:
        if server_id not in self._servers:
            return {"ok": False, "error": f"Servidor '{server_id}' no encontrado"}
        self._servers[server_id].stop()
        del self._servers[server_id]
        self._save_config()
        return {"ok": True}

    def list_servers(self) -> list[dict]:
        result = []
        for sid, srv in self._servers.items():
            entry = {"server_id": sid}
            if isinstance(srv, _StdioServer):
                entry.update({"type": "stdio", "command": srv.command, "initialized": srv._initialized})
            else:
                entry.update({"type": "http", "url": srv.url})
            result.append(entry)
        return result

    def list_tools(self, server_id: Optional[str] = None) -> list[dict]:
        targets = [server_id] if server_id else list(self._servers.keys())
        all_tools: list[dict] = []
        for sid in targets:
            srv = self._servers.get(sid)
            if not srv:
                continue
            result = srv._send("tools/list", {})
            if result and "tools" in result:
                for tool in result["tools"]:
                    tool["_server_id"] = sid
                    all_tools.append(tool)
        return all_tools

    def call_tool(self, server_name: str, tool_name: str, args: dict = {}) -> Any:
        srv = self._servers.get(server_name)
        if not srv:
            return {"error": f"Servidor '{server_name}' no encontrado"}
        result = srv._send("tools/call", {"name": tool_name, "arguments": args})
        return result

    def list_resources(self, server_id: str) -> list[dict]:
        srv = self._servers.get(server_id)
        if not srv:
            return []
        result = srv._send("resources/list", {})
        if result and "resources" in result:
            return result["resources"]
        return []

    def read_resource(self, server_id: str, uri: str) -> Any:
        srv = self._servers.get(server_id)
        if not srv:
            return {"error": f"Servidor '{server_id}' no encontrado"}
        return srv._send("resources/read", {"uri": uri})

    def get_all_tools_as_automyx(self) -> dict[str, Any]:
        tools: dict[str, Any] = {}
        for tool in self.list_tools():
            sid = tool.get("_server_id", "")
            name = tool.get("name", "")
            if not name:
                continue
            full_name = f"mcp_{sid}_{name}".replace("-", "_").replace(".", "_")

            def make_callable(server_id=sid, tool_name=name):
                def call(**kwargs):
                    return self.call_tool(server_id, tool_name, kwargs)
                call.__name__ = full_name
                call.__doc__ = tool.get("description", "")
                return call

            tools[full_name] = make_callable()
        return tools


def get_mcp_client() -> MCPClient:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = MCPClient()
    return _INSTANCE
