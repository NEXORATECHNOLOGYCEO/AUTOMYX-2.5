"""
Swarm Tools - Coordinador de enjambre Automyx
Orquesta múltiples instancias Automyx en paralelo (multi-VPS o multi-proceso).
"""
import os
import json
import time
import uuid
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional

try:
    import requests
except ImportError:
    requests = None


class SwarmOrchestrator:
    """Orquestador maestro de un enjambre de agentes Automyx."""

    NODES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "swarm_nodes.json")
    TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "swarm_tasks.json")
    AUDIT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data", "swarm_audit.log")

    _lock = threading.Lock()

    # ---------- INTERNAL HELPERS ----------
    @staticmethod
    def _load_nodes() -> List[Dict[str, Any]]:
        if not os.path.exists(SwarmOrchestrator.NODES_FILE):
            return []
        try:
            with open(SwarmOrchestrator.NODES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def _save_nodes(nodes: List[Dict[str, Any]]):
        os.makedirs(os.path.dirname(SwarmOrchestrator.NODES_FILE), exist_ok=True)
        with open(SwarmOrchestrator.NODES_FILE, "w", encoding="utf-8") as f:
            json.dump(nodes, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _load_tasks() -> List[Dict[str, Any]]:
        if not os.path.exists(SwarmOrchestrator.TASKS_FILE):
            return []
        try:
            with open(SwarmOrchestrator.TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def _save_tasks(tasks: List[Dict[str, Any]]):
        os.makedirs(os.path.dirname(SwarmOrchestrator.TASKS_FILE), exist_ok=True)
        with open(SwarmOrchestrator.TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks[-500:], f, ensure_ascii=False, indent=2)

    @staticmethod
    def _audit(msg: str):
        os.makedirs(os.path.dirname(SwarmOrchestrator.AUDIT_FILE), exist_ok=True)
        with open(SwarmOrchestrator.AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")

    # ---------- NODE MANAGEMENT ----------
    @staticmethod
    def register_node(node_id: str, host: str, port: int = 3500, gateway_token: str = "",
                       capabilities: List[str] = None, max_concurrent: int = 3) -> Dict[str, Any]:
        with SwarmOrchestrator._lock:
            nodes = SwarmOrchestrator._load_nodes()
            nodes = [n for n in nodes if n["node_id"] != node_id]
            nodes.append({
                "node_id": node_id,
                "host": host,
                "port": port,
                "gateway_token": gateway_token,
                "capabilities": capabilities or ["general"],
                "max_concurrent": max_concurrent,
                "status": "idle",
                "current_load": 0,
                "registered_at": datetime.now().isoformat(),
            })
            SwarmOrchestrator._save_nodes(nodes)
        SwarmOrchestrator._audit(f"Node registered: {node_id} @ {host}:{port}")
        return {"registered": node_id, "total_nodes": len(nodes)}

    @staticmethod
    def list_nodes() -> Dict[str, Any]:
        nodes = SwarmOrchestrator._load_nodes()
        return {"count": len(nodes), "nodes": nodes}

    @staticmethod
    def remove_node(node_id: str) -> Dict[str, Any]:
        with SwarmOrchestrator._lock:
            nodes = SwarmOrchestrator._load_nodes()
            before = len(nodes)
            nodes = [n for n in nodes if n["node_id"] != node_id]
            SwarmOrchestrator._save_nodes(nodes)
        SwarmOrchestrator._audit(f"Node removed: {node_id}")
        return {"removed": node_id, "deleted": before - len(nodes)}

    @staticmethod
    def health_check(node_id: str = None) -> Dict[str, Any]:
        if requests is None:
            return {"error": "Falta instalar requests"}
        nodes = SwarmOrchestrator._load_nodes()
        if node_id:
            nodes = [n for n in nodes if n["node_id"] == node_id]
        results = []
        for n in nodes:
            try:
                t0 = time.time()
                r = requests.get(f"http://{n['host']}:{n['port']}/api/agent/status",
                                  headers={"X-Gateway-Token": n.get("gateway_token", "")}, timeout=5)
                latency = round((time.time() - t0) * 1000, 1)
                ok = r.status_code == 200
                results.append({"node_id": n["node_id"], "alive": ok, "latency_ms": latency, "status_code": r.status_code})
                # Actualizar status
                with SwarmOrchestrator._lock:
                    all_nodes = SwarmOrchestrator._load_nodes()
                    for an in all_nodes:
                        if an["node_id"] == n["node_id"]:
                            an["status"] = "idle" if ok else "offline"
                            an["last_check"] = datetime.now().isoformat()
                            an["last_latency_ms"] = latency
                    SwarmOrchestrator._save_nodes(all_nodes)
            except Exception as e:
                results.append({"node_id": n["node_id"], "alive": False, "error": str(e)})
        return {"checks": results}

    # ---------- TASK DISPATCH ----------
    @staticmethod
    def _pick_best_node(required_capability: str = None) -> Optional[Dict[str, Any]]:
        nodes = SwarmOrchestrator._load_nodes()
        candidates = [n for n in nodes if n.get("status") in ("idle", None) and n.get("current_load", 0) < n.get("max_concurrent", 3)]
        if required_capability:
            candidates = [n for n in candidates if required_capability in n.get("capabilities", []) or "general" in n.get("capabilities", [])]
        if not candidates:
            return None
        # Más libre primero, luego menor latencia
        candidates.sort(key=lambda n: (n.get("current_load", 0), n.get("last_latency_ms", 999)))
        return candidates[0]

    @staticmethod
    def _execute_on_node(node: Dict[str, Any], task_prompt: str, task_id: str) -> Dict[str, Any]:
        if requests is None:
            return {"task_id": task_id, "error": "requests no instalado"}
        try:
            r = requests.post(
                f"http://{node['host']}:{node['port']}/api/gateway/inbound",
                headers={"X-Gateway-Token": node.get("gateway_token", ""), "Content-Type": "application/json"},
                json={"channel": "swarm", "sender_id": "orchestrator", "message": task_prompt, "agent_id": "main"},
                timeout=180,
            )
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
            return {"task_id": task_id, "node_id": node["node_id"], "status": "done", "response": data}
        except Exception as e:
            return {"task_id": task_id, "node_id": node["node_id"], "status": "failed", "error": str(e)}

    @staticmethod
    def dispatch_task(task_prompt: str, required_capability: str = None, priority: int = 5) -> Dict[str, Any]:
        task_id = uuid.uuid4().hex[:12]
        node = SwarmOrchestrator._pick_best_node(required_capability)
        if not node:
            return {"task_id": task_id, "status": "no_nodes_available", "fallback": "ejecutar local"}
        # Marcar nodo ocupado
        with SwarmOrchestrator._lock:
            nodes = SwarmOrchestrator._load_nodes()
            for n in nodes:
                if n["node_id"] == node["node_id"]:
                    n["current_load"] = n.get("current_load", 0) + 1
                    n["status"] = "busy"
            SwarmOrchestrator._save_nodes(nodes)

        SwarmOrchestrator._audit(f"Dispatched task {task_id} to {node['node_id']}: {task_prompt[:80]}")
        result = SwarmOrchestrator._execute_on_node(node, task_prompt, task_id)

        # Liberar nodo
        with SwarmOrchestrator._lock:
            nodes = SwarmOrchestrator._load_nodes()
            for n in nodes:
                if n["node_id"] == node["node_id"]:
                    n["current_load"] = max(0, n.get("current_load", 1) - 1)
                    n["status"] = "idle" if n["current_load"] == 0 else "busy"
            SwarmOrchestrator._save_nodes(nodes)

            tasks = SwarmOrchestrator._load_tasks()
            tasks.append({**result, "dispatched_at": datetime.now().isoformat(), "priority": priority, "prompt": task_prompt[:200]})
            SwarmOrchestrator._save_tasks(tasks)
        return result

    @staticmethod
    def dispatch_parallel(tasks: List[str], required_capability: str = None, max_workers: int = 5) -> Dict[str, Any]:
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(SwarmOrchestrator.dispatch_task, t, required_capability): t for t in tasks}
            for fut in as_completed(futures):
                results.append(fut.result())
        return {"total": len(tasks), "results": results}

    @staticmethod
    def dispatch_map_reduce(items: List[Any], task_template: str, reducer: str = "concat") -> Dict[str, Any]:
        """Distribuye N items entre nodos disponibles aplicando un template."""
        tasks = [task_template.replace("{ITEM}", str(item)) for item in items]
        parallel = SwarmOrchestrator.dispatch_parallel(tasks)
        outputs = [r.get("response", {}).get("reply", "") for r in parallel["results"]]
        if reducer == "concat":
            reduced = "\n\n---\n\n".join(str(o) for o in outputs)
        elif reducer == "list":
            reduced = outputs
        else:
            reduced = outputs
        return {"items_processed": len(items), "reduced": reduced, "raw_results": parallel["results"]}

    @staticmethod
    def pipeline(steps: List[Dict[str, str]]) -> Dict[str, Any]:
        """Ejecuta una pipeline: [{capability: 'code', prompt: '...'}, {capability: 'video', prompt: 'usa {PREV}'}]."""
        outputs = []
        prev = ""
        for step in steps:
            prompt = step["prompt"].replace("{PREV}", str(prev))
            res = SwarmOrchestrator.dispatch_task(prompt, step.get("capability"))
            prev = res.get("response", {}).get("reply", "")
            outputs.append(res)
        return {"steps_executed": len(steps), "final_output": prev, "all_steps": outputs}

    @staticmethod
    def consensus(task_prompt: str, num_voters: int = 3) -> Dict[str, Any]:
        """Lanza la misma tarea a N nodos y devuelve la respuesta más común."""
        tasks = [task_prompt] * num_voters
        results = SwarmOrchestrator.dispatch_parallel(tasks)
        votes: Dict[str, int] = {}
        for r in results["results"]:
            reply = str(r.get("response", {}).get("reply", ""))[:200]
            votes[reply] = votes.get(reply, 0) + 1
        winner = max(votes.items(), key=lambda x: x[1])
        return {"winner": winner[0], "votes": winner[1], "total_voters": num_voters, "all_votes": votes}

    @staticmethod
    def get_task_status(task_id: str = None) -> Dict[str, Any]:
        tasks = SwarmOrchestrator._load_tasks()
        if task_id:
            return next((t for t in tasks if t.get("task_id") == task_id), {"error": "task not found"})
        return {"count": len(tasks), "recent": tasks[-20:]}
