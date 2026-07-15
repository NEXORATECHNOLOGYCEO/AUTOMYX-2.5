"""
GIT TOOLS — despliegue seguro a GitHub/remotos
==============================================
git_deploy hace TODO el flujo correcto en un solo paso determinista:
excluye binarios >95MB, commitea, repara historial local no subido con
blobs gigantes (causa #1 de pushes imposibles) y pushea con timeout largo.
NUNCA usa --force ni toca el historial ya publicado en el remoto.
"""
import os
import subprocess
from typing import List, Optional


GITHUB_LIMIT_MB = 95  # GitHub rechaza blobs >100MB; margen de seguridad


def _git(args: List[str], cwd: str, timeout: int = 120):
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
        stdin=subprocess.DEVNULL,
    )


def _out(r) -> str:
    return ((r.stdout or "") + (r.stderr or "")).strip()


class GitTools:

    @staticmethod
    def git_deploy(**kwargs) -> str:
        """Despliega los cambios de un repositorio a su remoto de forma segura.

        Args:
            path/repo: carpeta del repo (default: directorio actual)
            message/mensaje: mensaje de commit
            remote_url: (opcional) URL del remoto si el usuario dio una nueva
            branch: (opcional) rama; default la rama actual
            max_mb: (interno/test) umbral de binario grande, default 95
        """
        cwd = str(kwargs.get("path") or kwargs.get("repo") or kwargs.get("directory")
                  or os.getcwd())
        message = str(kwargs.get("message") or kwargs.get("mensaje")
                      or "Actualización desplegada por Automyx").strip()[:200]
        remote_url = kwargs.get("remote_url") or kwargs.get("url")
        try:
            max_mb = float(kwargs.get("max_mb", GITHUB_LIMIT_MB))
        except (TypeError, ValueError):
            max_mb = GITHUB_LIMIT_MB
        limit_bytes = int(max_mb * 1024 * 1024)
        steps: List[str] = []

        if not os.path.isdir(cwd):
            return f"❌ La carpeta no existe: {cwd}"
        if _git(["rev-parse", "--git-dir"], cwd).returncode != 0:
            return (f"❌ '{cwd}' no es un repositorio git. Verifica la ruta o "
                    f"pregunta al usuario dónde está el repo.")

        # ── Rama actual ───────────────────────────────────────────────────
        branch = str(kwargs.get("branch") or "").strip()
        if not branch:
            r = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
            branch = _out(r) or "main"
        if branch == "HEAD":
            return "❌ El repo está en detached HEAD. Pide al usuario a qué rama desplegar."

        # ── Remoto: usar el configurado; JAMÁS inventar URLs ─────────────
        if remote_url:
            if _git(["remote", "get-url", "origin"], cwd).returncode == 0:
                _git(["remote", "set-url", "origin", str(remote_url)], cwd)
            else:
                _git(["remote", "add", "origin", str(remote_url)], cwd)
            steps.append(f"remoto origin → {remote_url}")
        r = _git(["remote", "get-url", "origin"], cwd)
        if r.returncode != 0:
            return ("❌ Este repo no tiene remoto 'origin' configurado. NO inventes "
                    "URLs: pregunta al usuario la URL exacta del repositorio "
                    "(ej. https://github.com/USUARIO/REPO.git) y reintenta con remote_url.")
        origin = _out(r)
        steps.append(f"remoto: {origin} · rama: {branch}")

        # ── Binarios grandes en el working tree → .gitignore + untrack ───
        big_files: List[str] = []
        for dirpath, dirnames, filenames in os.walk(cwd):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "venv", ".venv")]
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(fp) > limit_bytes:
                        big_files.append(os.path.relpath(fp, cwd).replace("\\", "/"))
                except OSError:
                    pass
        if big_files:
            gi_path = os.path.join(cwd, ".gitignore")
            try:
                existing = open(gi_path, encoding="utf-8", errors="replace").read() if os.path.exists(gi_path) else ""
            except OSError:
                existing = ""
            new_lines = [bf for bf in big_files if bf not in existing]
            if new_lines:
                with open(gi_path, "a", encoding="utf-8") as f:
                    f.write("\n# >%.0fMB — excluidos por git_deploy (límite de GitHub)\n" % max_mb)
                    f.write("\n".join(new_lines) + "\n")
            for bf in big_files:
                _git(["rm", "--cached", "--ignore-unmatch", "-q", bf], cwd)
            steps.append(f"excluidos {len(big_files)} archivo(s) >{max_mb:.0f}MB: "
                         + ", ".join(big_files[:5]))

        # ── Commit de lo pendiente ────────────────────────────────────────
        _git(["add", "-A"], cwd, timeout=300)
        r = _git(["commit", "-m", message], cwd, timeout=300)
        if r.returncode == 0:
            steps.append(f"commit: \"{message}\"")
        else:
            steps.append("sin cambios nuevos que commitear")

        # ── Blobs gigantes en commits locales AÚN NO subidos ─────────────
        # (la causa real de los pushes que nunca terminan)
        _git(["fetch", "origin", branch], cwd, timeout=120)
        upstream = f"origin/{branch}"
        has_upstream = _git(["rev-parse", "--verify", upstream], cwd).returncode == 0
        rev_range = f"{upstream}..{branch}" if has_upstream else branch
        r = _git(["rev-list", "--objects", rev_range], cwd, timeout=180)
        big_blobs: List[str] = []
        if r.returncode == 0 and r.stdout:
            oids = [ln.split()[0] for ln in r.stdout.splitlines() if ln.strip()]
            batch = subprocess.run(
                ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                cwd=cwd, input="\n".join(oids), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=300,
            )
            paths = {}
            for ln in r.stdout.splitlines():
                if not ln.strip():
                    continue
                oid, _, p = ln.rstrip().partition(" ")
                paths[oid] = p or "?"
            for ln in (batch.stdout or "").splitlines():
                parts = ln.split()
                if len(parts) == 3 and parts[1] == "blob" and int(parts[2]) > limit_bytes:
                    big_blobs.append(f"{paths.get(parts[0], '?')} ({int(parts[2]) // (1024*1024)}MB)")

        if big_blobs and has_upstream:
            # Reparación segura: compactar SOLO los commits locales no subidos
            # en uno limpio sin los blobs gigantes. El historial remoto no se toca.
            for bb in big_blobs:
                bf = bb.rsplit(" (", 1)[0]
                gi_path = os.path.join(cwd, ".gitignore")
                try:
                    existing = open(gi_path, encoding="utf-8", errors="replace").read() if os.path.exists(gi_path) else ""
                except OSError:
                    existing = ""
                if bf not in existing:
                    with open(gi_path, "a", encoding="utf-8") as f:
                        f.write(bf + "\n")
            r = _git(["reset", "--soft", upstream], cwd)
            if r.returncode != 0:
                return ("❌ No pude compactar los commits locales: " + _out(r)[:300])
            _git(["add", "-A"], cwd, timeout=300)
            for bb in big_blobs:
                _git(["rm", "--cached", "--ignore-unmatch", "-q", bb.rsplit(" (", 1)[0]], cwd)
            r = _git(["commit", "-m", message + " (historial local compactado: binarios grandes excluidos)"], cwd, timeout=300)
            if r.returncode != 0 and "nothing to commit" not in _out(r).lower():
                return "❌ Falló el commit de compactación: " + _out(r)[:300]
            steps.append(f"historial local compactado — blobs gigantes eliminados: {', '.join(big_blobs[:4])}")
        elif big_blobs:
            return ("❌ Hay blobs >%dMB en el historial y no existe rama remota de "
                    "referencia para compactar con seguridad: %s. Dile al usuario que "
                    "hace falta 'git filter-repo' o empezar el remoto limpio."
                    % (int(max_mb), ", ".join(big_blobs[:4])))

        # ── Push (timeout largo, sin force JAMÁS) ────────────────────────
        push_args = ["push", "-u", "origin", branch]
        r = _git(push_args, cwd, timeout=600)
        if r.returncode != 0:
            err = _out(r)
            if "non-fast-forward" in err or "fetch first" in err or "rejected" in err:
                steps.append("push rechazado → pull --rebase e reintento")
                pr = _git(["pull", "--rebase", "origin", branch], cwd, timeout=300)
                if pr.returncode != 0:
                    return ("❌ El remoto tiene commits que no están aquí y el rebase "
                            "falló:\n" + _out(pr)[:400] + "\nPasos previos: " + " | ".join(steps))
                r = _git(push_args, cwd, timeout=600)
            if r.returncode != 0:
                err = _out(r)[:500]
                hint = ""
                if "403" in err or "denied" in err.lower() or "authentication" in err.lower():
                    hint = ("\nSugerencia: problema de credenciales — pide al usuario que "
                            "verifique su token/login de GitHub (git credential manager).")
                elif "not found" in err.lower() or "404" in err:
                    hint = ("\nSugerencia: el repositorio remoto no existe con esa URL — "
                            "pide al usuario la URL correcta, NO pruebes URLs inventadas.")
                elif "large" in err.lower() or "exceeds" in err.lower():
                    hint = "\nSugerencia: aún hay un archivo gigante; vuelve a ejecutar git_deploy."
                return "❌ Push falló:\n" + err + hint + "\nPasos previos: " + " | ".join(steps)

        r = _git(["log", "--oneline", "-1"], cwd)
        return ("✅ Desplegado a " + origin + " (rama " + branch + ").\n"
                "Último commit: " + _out(r)[:120] + "\n"
                "Pasos: " + " | ".join(steps))


def register_git_tools(agent) -> int:
    """Registra las tools git en el agente. Devuelve cuántas registró."""
    agent.register_tool("git_deploy", GitTools.git_deploy)
    return 1
