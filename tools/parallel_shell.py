"""
AUTOMYX — ORQUESTA DE SHELL (paralelo + background jobs)
========================================================
Hace que el agente NUNCA se estanque en un comando:
- `shell_batch`  → dispara N comandos a la vez (locales y/o SSH) y devuelve
  TODOS los resultados juntos. Paralelismo garantizado sin depender del modelo.
- `run_background`/`check_jobs`/`job_output`/`kill_job` → lanza comandos largos
  (builds, deploys, escaneos) que siguen corriendo mientras el agente hace otra
  cosa; el output se captura a archivo y se consulta cuando quiera.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()
_JOBS_DIR = Path.home() / ".automyx" / "jobs"
MAX_PARALLEL = 32


def _run_one_local(command: str, timeout: int, cwd: str = ".") -> Dict[str, Any]:
    t0 = time.time()
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            cwd=cwd, stdin=subprocess.DEVNULL,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        out = (r.stdout or "") + (("\n[stderr] " + r.stderr) if r.returncode != 0 and r.stderr else "")
        return {"command": command, "ok": r.returncode == 0, "exit": r.returncode,
                "output": out.strip()[-1500:], "ms": round((time.time() - t0) * 1000)}
    except subprocess.TimeoutExpired:
        return {"command": command, "ok": False, "exit": None,
                "output": f"⏱️ timeout ({timeout}s)", "ms": round((time.time() - t0) * 1000)}
    except Exception as e:
        return {"command": command, "ok": False, "exit": None,
                "output": f"error: {str(e)[:200]}", "ms": round((time.time() - t0) * 1000)}


def _run_one_ssh(command: str, host: str, user: str, password: str,
                 key_path: str, port: int, timeout: int) -> Dict[str, Any]:
    t0 = time.time()
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ck = {"hostname": host, "port": port, "username": user,
              "timeout": 20, "allow_agent": False, "look_for_keys": bool(key_path)}
        if key_path:
            ck["key_filename"] = key_path
        elif password:
            ck["password"] = password
        ssh.connect(**ck)
        _, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        ssh.close()
        res = out.strip()
        if err.strip() and code != 0:
            res = (res + "\n[stderr] " + err.strip()).strip()
        return {"command": command, "host": host, "ok": code == 0, "exit": code,
                "output": res[-1500:], "ms": round((time.time() - t0) * 1000)}
    except Exception as e:
        return {"command": command, "host": host, "ok": False, "exit": None,
                "output": f"SSH error: {str(e)[:200]}", "ms": round((time.time() - t0) * 1000)}


class ParallelShell:
    @staticmethod
    def shell_batch(**kwargs) -> str:
        """Ejecuta VARIOS comandos A LA VEZ (en paralelo) y devuelve todos los
        resultados. Úsalo cuando tengas varias cosas independientes que hacer —
        no las hagas una por una. Corre local por defecto; si pasas host/password
        (o key_path) los corre por SSH en ese servidor.

        Args:
            commands: lista de comandos (o string separado por saltos de línea)
            host/user/password/key_path/port: si quieres correrlos por SSH remoto
            timeout_seconds: por comando (default 60)
            max_parallel: cuántos a la vez (default 8, máx 32)
        """
        commands = kwargs.get("commands") or kwargs.get("cmds") or kwargs.get("command")
        if isinstance(commands, str):
            commands = [c.strip() for c in commands.splitlines() if c.strip()]
        if not commands or not isinstance(commands, list):
            return "❌ Error: 'commands' debe ser una lista de comandos."
        commands = [str(c) for c in commands][:64]
        timeout = int(kwargs.get("timeout_seconds") or kwargs.get("timeout") or 60)
        workers = max(1, min(int(kwargs.get("max_parallel") or 8), MAX_PARALLEL))
        cwd = kwargs.get("cwd") or "."
        host = kwargs.get("host") or kwargs.get("ip")
        user = kwargs.get("user") or kwargs.get("username") or "root"
        password = kwargs.get("password")
        key_path = kwargs.get("key_path") or kwargs.get("key")
        port = int(kwargs.get("port") or 22)

        def _job(cmd):
            if host:
                return _run_one_ssh(cmd, host, user, password, key_path, port, timeout)
            return _run_one_local(cmd, timeout, cwd)

        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(workers, len(commands))) as ex:
            futs = {ex.submit(_job, c): c for c in commands}
            for f in as_completed(futs):
                results.append(f.result())

        order = {c: i for i, c in enumerate(commands)}
        results.sort(key=lambda r: order.get(r["command"], 0))
        n_ok = sum(1 for r in results if r["ok"])
        lines = [f"⚡ {len(results)} comandos en paralelo · {n_ok} ok · {len(results)-n_ok} fallos"
                 + (f" · SSH {host}" if host else "")]
        for i, r in enumerate(results, 1):
            mark = "✓" if r["ok"] else "✗"
            lines.append(f"\n[{i}] {mark} $ {r['command'][:90]}  ({r['ms']}ms)")
            body = (r["output"] or "(sin output)").strip()
            lines.append("    " + body.replace("\n", "\n    ")[:900])
        return "\n".join(lines)

    # ── Background jobs ───────────────────────────────────────────────────────
    @staticmethod
    def run_background(**kwargs) -> str:
        """Lanza un comando LARGO en segundo plano (build, deploy, escaneo,
        descarga) SIN bloquear — devuelve un job_id al instante y sigues con
        otra cosa. Revisa luego con check_jobs / job_output.

        Args:
            command: el comando a ejecutar
            name: etiqueta corta (opcional)
            cwd: directorio (opcional)
        """
        command = kwargs.get("command") or kwargs.get("cmd")
        if not command:
            return "❌ Error: Se requiere 'command'."
        name = kwargs.get("name") or command.split()[0][:20]
        cwd = kwargs.get("cwd") or "."
        _JOBS_DIR.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex[:8]
        log_path = _JOBS_DIR / f"{job_id}.log"

        def _worker():
            with open(log_path, "w", encoding="utf-8") as fh:
                try:
                    p = subprocess.Popen(
                        command, shell=True, stdout=fh, stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL, cwd=cwd,
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                    )
                    with _JOBS_LOCK:
                        _JOBS[job_id]["pid"] = p.pid
                    code = p.wait()
                    with _JOBS_LOCK:
                        _JOBS[job_id]["status"] = "done" if code == 0 else "failed"
                        _JOBS[job_id]["exit"] = code
                        _JOBS[job_id]["finished"] = time.time()
                except Exception as e:
                    fh.write(f"\n[automyx] error: {e}")
                    with _JOBS_LOCK:
                        _JOBS[job_id]["status"] = "failed"
                        _JOBS[job_id]["exit"] = -1
                        _JOBS[job_id]["finished"] = time.time()

        with _JOBS_LOCK:
            _JOBS[job_id] = {"id": job_id, "name": name, "command": command,
                             "status": "running", "started": time.time(),
                             "finished": None, "exit": None, "pid": None,
                             "log": str(log_path)}
        threading.Thread(target=_worker, daemon=True, name=f"job-{job_id}").start()
        return (f"🚀 Job '{name}' lanzado en background · id={job_id}\n"
                f"Sigue con otra cosa; revisa con check_jobs o job_output(job_id={job_id}).")

    @staticmethod
    def check_jobs(**kwargs) -> str:
        """Lista todos los jobs en background con su estado (running/done/failed),
        duración y las últimas líneas del output. NO bloquea."""
        with _JOBS_LOCK:
            jobs = list(_JOBS.values())
        if not jobs:
            return "No hay jobs en background."
        jobs.sort(key=lambda j: j["started"], reverse=True)
        icons = {"running": "⠿", "done": "✓", "failed": "✗"}
        lines = [f"📋 {len(jobs)} jobs en background:"]
        for j in jobs:
            end = j["finished"] or time.time()
            dur = end - j["started"]
            tail = ""
            try:
                txt = Path(j["log"]).read_text(encoding="utf-8", errors="replace").strip()
                if txt:
                    last = txt.splitlines()[-1][:80]
                    tail = f"  · {last}"
            except Exception:
                pass
            lines.append(f"  {icons.get(j['status'],'?')} [{j['id']}] {j['name']} "
                         f"· {j['status']} · {dur:.0f}s{tail}")
        lines.append("Usa job_output(job_id=...) para ver el output completo.")
        return "\n".join(lines)

    @staticmethod
    def job_output(**kwargs) -> str:
        """Devuelve el output completo (o últimas N líneas) de un job en background.

        Args:
            job_id: id del job
            tail_lines: solo las últimas N líneas (opcional)
        """
        job_id = kwargs.get("job_id") or kwargs.get("id")
        if not job_id:
            return "❌ Error: Se requiere 'job_id'."
        with _JOBS_LOCK:
            j = _JOBS.get(job_id)
        if not j:
            return f"❌ Job no encontrado: {job_id}"
        try:
            txt = Path(j["log"]).read_text(encoding="utf-8", errors="replace")
        except Exception:
            txt = "(sin log)"
        tail = kwargs.get("tail_lines") or kwargs.get("tail")
        if tail:
            txt = "\n".join(txt.splitlines()[-int(tail):])
        head = (f"Job [{j['id']}] {j['name']} · {j['status']}"
                + (f" (exit {j['exit']})" if j['exit'] is not None else "") + "\n$ "
                + j["command"] + "\n" + "─" * 40 + "\n")
        return head + txt.strip()[-3000:]

    @staticmethod
    def kill_job(**kwargs) -> str:
        """Mata un job en background por su job_id."""
        job_id = kwargs.get("job_id") or kwargs.get("id")
        with _JOBS_LOCK:
            j = _JOBS.get(job_id)
        if not j:
            return f"❌ Job no encontrado: {job_id}"
        if j["status"] != "running" or not j.get("pid"):
            return f"Job {job_id} ya está {j['status']}."
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(j["pid"])],
                               capture_output=True, timeout=10)
            else:
                os.kill(j["pid"], 9)
            with _JOBS_LOCK:
                _JOBS[job_id]["status"] = "failed"
                _JOBS[job_id]["finished"] = time.time()
            return f"🛑 Job {job_id} detenido."
        except Exception as e:
            return f"No se pudo matar el job: {str(e)[:150]}"
