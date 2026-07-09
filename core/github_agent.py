from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

TOKEN_FILE = Path.home() / ".automyx" / "github_token.txt"
_GITHUB_API = "https://api.github.com"

_instance: Optional[GitHubAgent] = None


def _require_requests() -> None:
    if not _HAS_REQUESTS:
        raise ImportError(
            "El módulo 'requests' no está instalado. Ejecuta: pip install requests"
        )


def _encode_token(token: str) -> str:
    return base64.b64encode(token.encode()).decode()


def _decode_token(encoded: str) -> str:
    return base64.b64decode(encoded.encode()).decode()


class GitHubAgent:
    def __init__(self, token: Optional[str] = None) -> None:
        self._token: Optional[str] = None
        if token:
            self._token = token
        else:
            env_token = os.environ.get("GITHUB_TOKEN")
            if env_token:
                self._token = env_token
            else:
                self.load_token()

    def set_token(self, token: str) -> None:
        self._token = token
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(_encode_token(token), encoding="utf-8")

    def load_token(self) -> None:
        if TOKEN_FILE.exists():
            try:
                self._token = _decode_token(TOKEN_FILE.read_text(encoding="utf-8").strip())
            except Exception:
                self._token = None

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        _require_requests()
        url = f"{_GITHUB_API}{endpoint}"
        resp = _requests.get(url, headers=self._headers(), params=params, timeout=30)
        if not resp.ok:
            raise RuntimeError(
                f"Error GitHub GET {endpoint}: {resp.status_code} - {resp.text[:300]}"
            )
        return resp.json()

    def _get_raw(self, endpoint: str) -> str:
        _require_requests()
        url = f"{_GITHUB_API}{endpoint}"
        headers = self._headers()
        headers["Accept"] = "application/vnd.github.v3.diff"
        resp = _requests.get(url, headers=headers, timeout=30)
        if not resp.ok:
            raise RuntimeError(
                f"Error GitHub GET raw {endpoint}: {resp.status_code} - {resp.text[:300]}"
            )
        return resp.text

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Any:
        _require_requests()
        url = f"{_GITHUB_API}{endpoint}"
        resp = _requests.post(url, headers=self._headers(), json=data, timeout=30)
        if not resp.ok:
            raise RuntimeError(
                f"Error GitHub POST {endpoint}: {resp.status_code} - {resp.text[:300]}"
            )
        return resp.json()

    def _patch(self, endpoint: str, data: Dict[str, Any]) -> Any:
        _require_requests()
        url = f"{_GITHUB_API}{endpoint}"
        resp = _requests.patch(url, headers=self._headers(), json=data, timeout=30)
        if not resp.ok:
            raise RuntimeError(
                f"Error GitHub PATCH {endpoint}: {resp.status_code} - {resp.text[:300]}"
            )
        return resp.json()

    def list_repos(self, user: Optional[str] = None) -> List[Dict[str, Any]]:
        if user:
            data = self._get(f"/users/{user}/repos", params={"per_page": 100})
        else:
            data = self._get("/user/repos", params={"per_page": 100, "sort": "updated"})
        return [
            {
                "name": r["name"],
                "full_name": r["full_name"],
                "private": r["private"],
                "description": r.get("description"),
                "default_branch": r.get("default_branch", "main"),
                "stars": r.get("stargazers_count", 0),
                "url": r["html_url"],
            }
            for r in data
        ]

    def get_repo_info(self, repo: str) -> Dict[str, Any]:
        data = self._get(f"/repos/{repo}")
        return {
            "name": data["name"],
            "full_name": data["full_name"],
            "description": data.get("description"),
            "private": data["private"],
            "default_branch": data.get("default_branch", "main"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "url": data["html_url"],
            "language": data.get("language"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }

    def list_prs(self, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        data = self._get(f"/repos/{repo}/pulls", params={"state": state, "per_page": 50})
        return [
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "author": pr["user"]["login"],
                "head": pr["head"]["ref"],
                "base": pr["base"]["ref"],
                "url": pr["html_url"],
                "created_at": pr.get("created_at"),
                "draft": pr.get("draft", False),
            }
            for pr in data
        ]

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        return self._get_raw(f"/repos/{repo}/pulls/{pr_number}")

    def create_pr(
        self,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> Dict[str, Any]:
        data = self._post(
            f"/repos/{repo}/pulls",
            {"title": title, "body": body, "head": head_branch, "base": base_branch},
        )
        return {
            "number": data["number"],
            "title": data["title"],
            "url": data["html_url"],
            "state": data["state"],
        }

    def add_pr_comment(self, repo: str, pr_number: int, comment: str) -> Dict[str, Any]:
        data = self._post(
            f"/repos/{repo}/issues/{pr_number}/comments",
            {"body": comment},
        )
        return {"id": data["id"], "url": data["html_url"]}

    def list_issues(self, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        data = self._get(
            f"/repos/{repo}/issues",
            params={"state": state, "per_page": 50},
        )
        return [
            {
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "author": issue["user"]["login"],
                "labels": [l["name"] for l in issue.get("labels", [])],
                "url": issue["html_url"],
                "created_at": issue.get("created_at"),
            }
            for issue in data
            if "pull_request" not in issue
        ]

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        data = self._post(f"/repos/{repo}/issues", payload)
        return {
            "number": data["number"],
            "title": data["title"],
            "url": data["html_url"],
            "state": data["state"],
        }

    def close_issue(self, repo: str, issue_number: int) -> Dict[str, Any]:
        data = self._patch(
            f"/repos/{repo}/issues/{issue_number}",
            {"state": "closed"},
        )
        return {
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "url": data["html_url"],
        }

    def get_file_content(self, repo: str, path: str, branch: str = "main") -> str:
        data = self._get(
            f"/repos/{repo}/contents/{path}",
            params={"ref": branch},
        )
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content", "")

    def get_commits(self, repo: str, n: int = 10) -> List[Dict[str, Any]]:
        data = self._get(f"/repos/{repo}/commits", params={"per_page": n})
        return [
            {
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
                "url": c["html_url"],
            }
            for c in data
        ]


def get_github(token: Optional[str] = None) -> GitHubAgent:
    global _instance
    if _instance is None:
        _instance = GitHubAgent(token=token)
    return _instance
