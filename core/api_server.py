from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_server_instance: Optional["AutomyxAPIServer"] = None

API_KEY_FILE = Path.home() / ".automyx" / "api_key.txt"

try:
    from flask import Flask, request, jsonify, abort
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    from flask_sock import Sock
    SOCK_AVAILABLE = True
except ImportError:
    SOCK_AVAILABLE = False


def _load_api_key() -> Optional[str]:
    if API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text(encoding="utf-8").strip()
        return key if key else None
    return None


class AutomyxAPIServer:
    def __init__(self, port: int = 7799, agent_getter: Optional[Callable] = None):
        self.port = port
        self.agent_getter = agent_getter
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._start_time: Optional[float] = None
        self._app: Any = None
        self._api_key: Optional[str] = _load_api_key()

    @property
    def is_running(self) -> bool:
        return self._running

    def get_url(self) -> str:
        return f"http://localhost:{self.port}"

    def _check_auth(self):
        if self._api_key is None:
            return
        key = request.headers.get("X-Automyx-Key", "")
        if key != self._api_key:
            abort(401, description="Unauthorized: invalid or missing X-Automyx-Key header")

    def _build_app(self):
        if not FLASK_AVAILABLE:
            print("instala flask: pip install flask flask-sock")
            return None

        app = Flask("automyx_api")
        app.config["SECRET_KEY"] = "automyx-internal"

        @app.before_request
        def auth_middleware():
            self._check_auth()

        @app.route("/v1/task", methods=["POST"])
        def task_endpoint():
            data = request.get_json(silent=True) or {}
            task_text = data.get("task", "")
            workspace = data.get("workspace", "default")
            if not task_text:
                return jsonify({"error": "task is required"}), 400

            agent = self.agent_getter() if self.agent_getter else None
            if agent is None:
                return jsonify({"error": "no agent available"}), 503

            start = time.time()
            try:
                response = agent.run(task_text)
                duration_ms = round((time.time() - start) * 1000)
                return jsonify({
                    "response": response,
                    "tokens_used": getattr(agent, "last_tokens_used", 0),
                    "tools_called": getattr(agent, "last_tools_called", []),
                    "duration_ms": duration_ms,
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/v1/status", methods=["GET"])
        def status_endpoint():
            agent = self.agent_getter() if self.agent_getter else None
            uptime = round(time.time() - self._start_time) if self._start_time else 0
            return jsonify({
                "is_active": agent is not None and getattr(agent, "is_active", False),
                "current_task": getattr(agent, "current_task", None) if agent else None,
                "workspace": getattr(agent, "workspace", "default") if agent else None,
                "model": getattr(agent, "model", None) if agent else None,
                "uptime_s": uptime,
            })

        @app.route("/v1/memory", methods=["GET"])
        def memory_endpoint():
            agent = self.agent_getter() if self.agent_getter else None
            mem = getattr(agent, "memory", None) if agent else None
            if mem is None:
                return jsonify({"facts": [], "recent_tasks": [], "workspaces": []})
            return jsonify({
                "facts": getattr(mem, "facts", [])[:50],
                "recent_tasks": getattr(mem, "recent_tasks", [])[:20],
                "workspaces": getattr(mem, "workspaces", []),
            })

        @app.route("/v1/tools", methods=["GET"])
        def tools_endpoint():
            agent = self.agent_getter() if self.agent_getter else None
            tools = getattr(agent, "available_tools", []) if agent else []
            return jsonify({"tools": tools})

        @app.route("/v1/audit", methods=["GET"])
        def audit_endpoint():
            n = int(request.args.get("n", 50))
            try:
                from core.audit import get_audit_log
                entries = get_audit_log(n)
                return jsonify({"entries": entries})
            except Exception:
                return jsonify({"entries": []})

        @app.route("/v1/remember", methods=["POST"])
        def remember_endpoint():
            data = request.get_json(silent=True) or {}
            fact = data.get("fact", "")
            category = data.get("category", "general")
            if not fact:
                return jsonify({"error": "fact is required"}), 400
            try:
                from core.memory import MemoryManager
                mem = MemoryManager()
                result = mem.remember(fact, category)
                return jsonify({"result": result})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        if SOCK_AVAILABLE:
            sock = Sock(app)

            @sock.route("/v1/stream")
            def stream_ws(ws):
                try:
                    data_raw = ws.receive(timeout=30)
                    if not data_raw:
                        ws.send(json.dumps({"error": "no data received"}))
                        return
                    data = json.loads(data_raw)
                    task_text = data.get("task", "")
                    if not task_text:
                        ws.send(json.dumps({"error": "task required"}))
                        return

                    agent = self.agent_getter() if self.agent_getter else None
                    if agent is None:
                        ws.send(json.dumps({"error": "no agent available"}))
                        return

                    ws.send(json.dumps({"type": "start", "task": task_text}))

                    def stream_cb(chunk: str):
                        try:
                            ws.send(json.dumps({"type": "chunk", "content": chunk}))
                        except Exception:
                            pass

                    if hasattr(agent, "run_streaming"):
                        result = agent.run_streaming(task_text, callback=stream_cb)
                    else:
                        result = agent.run(task_text)

                    ws.send(json.dumps({"type": "done", "result": result}))
                except Exception as e:
                    try:
                        ws.send(json.dumps({"type": "error", "message": str(e)}))
                    except Exception:
                        pass

        return app

    def start(self, background: bool = True):
        if not FLASK_AVAILABLE:
            print("instala flask: pip install flask flask-sock")
            return

        self._app = self._build_app()
        if self._app is None:
            return

        self._start_time = time.time()
        self._running = True

        if background:
            self._thread = threading.Thread(target=self._serve, daemon=True, name="automyx-api")
            self._thread.start()
        else:
            self._serve()

    def _serve(self):
        try:
            self._app.run(host="0.0.0.0", port=self.port, threaded=True, use_reloader=False)
        except Exception as e:
            print(f"[API] error: {e}")
        finally:
            self._running = False

    def stop(self):
        self._running = False
        try:
            import requests as req
            req.get(f"{self.get_url()}/shutdown", timeout=1)
        except Exception:
            pass


def get_api_server(port: int = 7799, agent_getter: Optional[Callable] = None) -> AutomyxAPIServer:
    global _server_instance
    if _server_instance is None:
        _server_instance = AutomyxAPIServer(port=port, agent_getter=agent_getter)
    return _server_instance
