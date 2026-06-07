"""
GitHub Pro Tools - GitHub CLI wrapper (gh) + Git operations
=============================================================
Requiere `gh` CLI autenticado o token en GITHUB_TOKEN.
"""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _gh() -> Optional[str]:
    return shutil.which("gh") or shutil.which("gh.exe")


def _check_gh() -> Dict[str, Any]:
    p = _gh()
    if not p:
        return {"ok": False, "error": "gh CLI no instalado. Instala desde https://cli.github.com/"}
    r = subprocess.run([p, "auth", "status"], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return {"ok": False, "error": "gh no autenticado. Ejecuta 'gh auth login'", "stderr": r.stderr}
    return {"ok": True, "bin": p}


def _run(args: List[str], cwd: Optional[str] = None, timeout: int = 60) -> Dict[str, Any]:
    p = _gh()
    if not p:
        return {"ok": False, "error": "gh no instalado"}
    t0 = time.time()
    try:
        r = subprocess.run([p] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout, encoding="utf-8", errors="replace")
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "returncode": r.returncode,
            "duration_s": round(time.time() - t0, 2),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Repos
# ---------------------------------------------------------------------------
def list_repos(*, limit: int = 30, visibility: str = "all") -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    return _run(["repo", "list", "--limit", str(limit), "--visibility", visibility, "--json",
                 "name,fullName,description,isPrivate,url,createdAt,stargazerCount,forkCount"])


def clone(repo: str, target_dir: Optional[str] = None) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["repo", "clone", repo]
    if target_dir:
        args.append(target_dir)
    return _run(args, timeout=600)


def create_repo(name: str, *, description: str = "", private: bool = False, gitignore: Optional[str] = None, license: Optional[str] = None) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["repo", "create", name, "--description", description or "Created by AUTOMYX", "--confirm"]
    args.append("--private" if private else "--public")
    if gitignore:
        args += ["--gitignore", gitignore]
    if license:
        args += ["--license", license]
    return _run(args, timeout=120)


def fork_repo(repo: str) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    return _run(["repo", "fork", repo, "--clone=false"], timeout=120)


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------
def list_issues(repo: str, *, state: str = "open", limit: int = 30, labels: Optional[str] = None) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["issue", "list", "--repo", repo, "--state", state, "--limit", str(limit),
            "--json", "number,title,state,author,createdAt,labels,url,body"]
    if labels:
        args += ["--label", labels]
    return _run(args, timeout=60)


def create_issue(repo: str, title: str, body: str = "", *, labels: Optional[List[str]] = None, assignees: Optional[List[str]] = None) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["issue", "create", "--repo", repo, "--title", title, "--body", body or "Created by AUTOMYX"]
    for l in (labels or []):
        args += ["--label", l]
    for a in (assignees or []):
        args += ["--assignee", a]
    return _run(args, timeout=30)


def close_issue(repo: str, number: int, *, comment: Optional[str] = None) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["issue", "close", str(number), "--repo", repo]
    if comment:
        args += ["--comment", comment]
    return _run(args, timeout=30)


# ---------------------------------------------------------------------------
# Pull Requests
# ---------------------------------------------------------------------------
def list_prs(repo: str, *, state: str = "open", limit: int = 30) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    return _run(["pr", "list", "--repo", repo, "--state", state, "--limit", str(limit),
                 "--json", "number,title,state,author,createdAt,url,headRefName,baseRefName"], timeout=60)


def create_pr(repo: str, title: str, body: str = "", *, base: str = "main", head: Optional[str] = None, draft: bool = False) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["pr", "create", "--repo", repo, "--title", title, "--body", body, "--base", base]
    if head:
        args += ["--head", head]
    if draft:
        args.append("--draft")
    return _run(args, cwd=os.getcwd(), timeout=30)


def merge_pr(repo: str, number: int, *, method: str = "merge", delete_branch: bool = False) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["pr", "merge", str(number), "--repo", repo, f"--{method}"]
    if delete_branch:
        args.append("--delete-branch")
    return _run(args, timeout=60)


# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------
def list_releases(repo: str, *, limit: int = 10) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    return _run(["release", "list", "--repo", repo, "--limit", str(limit)], timeout=30)


def create_release(repo: str, tag: str, *, title: str = "", notes: str = "", target: str = "main", draft: bool = False, prerelease: bool = False) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["release", "create", tag, "--repo", repo, "--title", title or tag, "--notes", notes, "--target", target]
    if draft:
        args.append("--draft")
    if prerelease:
        args.append("--prerelease")
    return _run(args, timeout=60)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
def list_workflows(repo: str, *, limit: int = 20) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    return _run(["workflow", "list", "--repo", repo, "--limit", str(limit)], timeout=30)


def run_workflow(repo: str, workflow: str, ref: str = "main", *, inputs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    args = ["workflow", "run", workflow, "--repo", repo, "--ref", ref]
    for k, v in (inputs or {}).items():
        args += ["-f", f"{k}={v}"]
    return _run(args, timeout=30)


def watch_runs(repo: str, run_id: Optional[str] = None, *, limit: int = 5) -> Dict[str, Any]:
    chk = _check_gh()
    if not chk["ok"]:
        return chk
    if run_id:
        return _run(["run", "watch", run_id, "--repo", repo], timeout=1800)
    return _run(["run", "list", "--repo", repo, "--limit", str(limit)], timeout=30)


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class GitHubProTools:
    @staticmethod
    def status() -> Dict[str, Any]:
        return _check_gh()

    @staticmethod
    def list_repos(limit: int = 30) -> Dict[str, Any]:
        return list_repos(limit=limit)

    @staticmethod
    def clone(repo: str, target: Optional[str] = None) -> Dict[str, Any]:
        return clone(repo, target)

    @staticmethod
    def create_repo(name: str, description: str = "", private: bool = False) -> Dict[str, Any]:
        return create_repo(name, description=description, private=private)

    @staticmethod
    def list_issues(repo: str, state: str = "open") -> Dict[str, Any]:
        return list_issues(repo, state=state)

    @staticmethod
    def create_issue(repo: str, title: str, body: str = "", labels: Optional[List[str]] = None) -> Dict[str, Any]:
        return create_issue(repo, title, body, labels=labels or [])

    @staticmethod
    def close_issue(repo: str, number: int, comment: Optional[str] = None) -> Dict[str, Any]:
        return close_issue(repo, number, comment=comment)

    @staticmethod
    def list_prs(repo: str, state: str = "open") -> Dict[str, Any]:
        return list_prs(repo, state=state)

    @staticmethod
    def create_pr(repo: str, title: str, body: str = "", base: str = "main") -> Dict[str, Any]:
        return create_pr(repo, title, body, base=base)

    @staticmethod
    def merge_pr(repo: str, number: int, method: str = "merge") -> Dict[str, Any]:
        return merge_pr(repo, number, method=method)

    @staticmethod
    def list_releases(repo: str) -> Dict[str, Any]:
        return list_releases(repo)

    @staticmethod
    def create_release(repo: str, tag: str, title: str = "", notes: str = "", draft: bool = False) -> Dict[str, Any]:
        return create_release(repo, tag, title=title, notes=notes, draft=draft)

    @staticmethod
    def list_workflows(repo: str) -> Dict[str, Any]:
        return list_workflows(repo)

    @staticmethod
    def run_workflow(repo: str, workflow: str, ref: str = "main") -> Dict[str, Any]:
        return run_workflow(repo, workflow, ref=ref)
