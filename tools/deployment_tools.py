"""
Deployment Tools - Despliegue a múltiples plataformas
======================================================
Despliega a Vercel, Netlify, Railway, Render, Heroku, AWS, DigitalOcean,
Docker registries, y SSH genérico. Lee configs existentes.
"""
from __future__ import annotations

import os
import json
import subprocess
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _run(cmd: List[str], cwd: Optional[str] = None, timeout: int = 600) -> Dict[str, Any]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": r.returncode == 0, "returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s"}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"binario no encontrado: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _check_bin(name: str, hint: str = "") -> Dict[str, Any]:
    if not shutil.which(name):
        return {"ok": False, "error": f"{name} no instalado", "hint": hint}
    return {"ok": True}


# ---------------------------------------------------------------------------
# Vercel
# ---------------------------------------------------------------------------
def vercel_deploy(path: str = ".", *, prod: bool = False, cwd: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
    chk = _check_bin("vercel", "npm i -g vercel")
    if not chk["ok"]:
        return chk
    env = os.environ.copy()
    if token:
        env["VERCEL_TOKEN"] = token
    cmd = ["vercel", "--yes"]
    if prod:
        cmd.append("--prod")
    return _run_with_env(cmd, env, cwd=cwd or path)


def _run_with_env(cmd: List[str], env: Dict[str, str], cwd: Optional[str] = None, timeout: int = 600) -> Dict[str, Any]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": r.returncode == 0, "returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr, "url": _extract_url(r.stdout)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s"}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"binario no encontrado: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _extract_url(text: str) -> Optional[str]:
    import re
    m = re.search(r"https?://[^\s]+", text)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Netlify
# ---------------------------------------------------------------------------
def netlify_deploy(path: str = ".", *, prod: bool = True, cwd: Optional[str] = None) -> Dict[str, Any]:
    chk = _check_bin("netlify", "npm i -g netlify-cli")
    if not chk["ok"]:
        return chk
    cmd = ["netlify", "deploy"]
    if prod:
        cmd.append("--prod")
    cmd += ["--dir", path]
    r = _run_with_env(cmd, os.environ.copy(), cwd=cwd or path)
    return r


# ---------------------------------------------------------------------------
# Railway
# ---------------------------------------------------------------------------
def railway_deploy(path: str = ".", *, cwd: Optional[str] = None) -> Dict[str, Any]:
    chk = _check_bin("railway", "npm i -g @railway/cli")
    if not chk["ok"]:
        return chk
    return _run_with_env(["railway", "up"], os.environ.copy(), cwd=cwd or path)


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
def docker_build(image_name: str, dockerfile_path: str = "Dockerfile", *, context: str = ".", tag: str = "latest", cwd: Optional[str] = None) -> Dict[str, Any]:
    if not shutil.which("docker"):
        return {"ok": False, "error": "docker no instalado"}
    if not Path(dockerfile_path).exists():
        return {"ok": False, "error": f"Dockerfile no existe: {dockerfile_path}"}
    full_tag = f"{image_name}:{tag}"
    return _run(["docker", "build", "-t", full_tag, "-f", dockerfile_path, context], cwd=cwd or ".")


def docker_push(image_name: str, tag: str = "latest", registry: Optional[str] = None) -> Dict[str, Any]:
    if not shutil.which("docker"):
        return {"ok": False, "error": "docker no instalado"}
    full_name = f"{registry}/{image_name}:{tag}" if registry else f"{image_name}:{tag}"
    return _run(["docker", "push", full_name])


def docker_run(image_name: str, *, ports: Optional[Dict[str, str]] = None, env: Optional[Dict[str, str]] = None,
               detach: bool = True, name: Optional[str] = None) -> Dict[str, Any]:
    if not shutil.which("docker"):
        return {"ok": False, "error": "docker no instalado"}
    cmd = ["docker", "run"]
    if detach:
        cmd.append("-d")
    if name:
        cmd += ["--name", name]
    for host_port, container_port in (ports or {}).items():
        cmd += ["-p", f"{host_port}:{container_port}"]
    for k, v in (env or {}).items():
        cmd += ["-e", f"{k}={v}"]
    cmd.append(image_name)
    return _run(cmd)


def docker_compose_up(compose_file: str = "docker-compose.yml", *, cwd: Optional[str] = None, detach: bool = True) -> Dict[str, Any]:
    if not shutil.which("docker"):
        return {"ok": False, "error": "docker no instalado"}
    if not Path(compose_file).exists():
        return {"ok": False, "error": f"compose file no existe: {compose_file}"}
    cmd = ["docker", "compose", "-f", compose_file, "up"]
    if detach:
        cmd.append("-d")
    return _run(cmd, cwd=cwd or ".")


# ---------------------------------------------------------------------------
# SSH
# ---------------------------------------------------------------------------
def ssh_run(host: str, command: str, *, user: Optional[str] = None, key_file: Optional[str] = None, port: int = 22) -> Dict[str, Any]:
    if not shutil.which("ssh"):
        return {"ok": False, "error": "ssh no instalado"}
    cmd = ["ssh"]
    if key_file:
        cmd += ["-i", key_file]
    if port != 22:
        cmd += ["-p", str(port)]
    target = f"{user}@{host}" if user else host
    cmd += [target, command]
    return _run(cmd, timeout=300)


def scp_upload(local_path: str, remote_path: str, *, host: str, user: Optional[str] = None,
               key_file: Optional[str] = None, port: int = 22) -> Dict[str, Any]:
    if not shutil.which("scp"):
        return {"ok": False, "error": "scp no instalado"}
    cmd = ["scp"]
    if key_file:
        cmd += ["-i", key_file]
    if port != 22:
        cmd += ["-P", str(port)]
    cmd += [local_path, f"{user}@{host}:{remote_path}" if user else f"{host}:{remote_path}"]
    return _run(cmd, timeout=300)


# ---------------------------------------------------------------------------
# Detección de plataforma
# ---------------------------------------------------------------------------
def detect_platform(path: str = ".") -> Dict[str, Any]:
    """Detecta qué plataforma es la más adecuada según el proyecto."""
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": f"path no existe: {path}"}

    detected: List[str] = []

    # Vercel/Netlify: frontend estático
    if (p / "package.json").exists():
        pkg = json.loads((p / "package.json").read_text(encoding="utf-8"))
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "next" in deps or "nuxt" in deps or "svelte" in deps or "astro" in deps:
            detected.append("vercel")
        if "gatsby" in deps or "react-scripts" in deps:
            detected.append("netlify")

    # Docker
    if (p / "Dockerfile").exists():
        detected.append("docker")
    if (p / "docker-compose.yml").exists() or (p / "docker-compose.yaml").exists():
        detected.append("docker-compose")

    # Python
    if (p / "pyproject.toml").exists() or (p / "requirements.txt").exists():
        detected.append("railway")
        detected.append("render")

    # Node
    if (p / "package.json").exists():
        detected.append("railway")
        detected.append("render")

    # Go
    if (p / "go.mod").exists():
        detected.append("fly.io")
        detected.append("railway")

    # Static site
    if (p / "index.html").exists() and not (p / "package.json").exists():
        detected.append("netlify")
        detected.append("vercel")

    return {"ok": True, "detected": detected, "path": path}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
def health_check(url: str, *, timeout: int = 10, expect_status: int = 200) -> Dict[str, Any]:
    """Verifica que una URL responde correctamente."""
    try:
        import requests
        t0 = time.time()
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        elapsed = round((time.time() - t0) * 1000, 2)
        return {
            "ok": r.status_code == expect_status,
            "url": url,
            "status": r.status_code,
            "elapsed_ms": elapsed,
            "size_bytes": len(r.content),
        }
    except ImportError:
        return {"ok": False, "error": "instala requests"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class DeploymentTools:
    @staticmethod
    def detect(path: str = ".") -> Dict[str, Any]:
        return detect_platform(path)

    @staticmethod
    def vercel(path: str = ".", prod: bool = False) -> Dict[str, Any]:
        return vercel_deploy(path, prod=prod)

    @staticmethod
    def netlify(path: str = ".", prod: bool = True) -> Dict[str, Any]:
        return netlify_deploy(path, prod=prod)

    @staticmethod
    def railway(path: str = ".") -> Dict[str, Any]:
        return railway_deploy(path)

    @staticmethod
    def docker_build(image: str, dockerfile: str = "Dockerfile", tag: str = "latest") -> Dict[str, Any]:
        return docker_build(image, dockerfile, tag=tag)

    @staticmethod
    def docker_push(image: str, tag: str = "latest") -> Dict[str, Any]:
        return docker_push(image, tag)

    @staticmethod
    def docker_run(image: str, ports: Optional[Dict[str, str]] = None, name: Optional[str] = None) -> Dict[str, Any]:
        return docker_run(image, ports=ports, name=name)

    @staticmethod
    def compose_up(compose_file: str = "docker-compose.yml") -> Dict[str, Any]:
        return docker_compose_up(compose_file)

    @staticmethod
    def ssh(host: str, command: str, user: Optional[str] = None, key_file: Optional[str] = None) -> Dict[str, Any]:
        return ssh_run(host, command, user=user, key_file=key_file)

    @staticmethod
    def scp(local: str, remote: str, host: str, user: Optional[str] = None) -> Dict[str, Any]:
        return scp_upload(local, remote, host, user=user)

    @staticmethod
    def health(url: str, expect_status: int = 200) -> Dict[str, Any]:
        return health_check(url, expect_status=expect_status)
