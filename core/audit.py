from __future__ import annotations

import csv
import json
import os
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

AUDIT_DIR = Path.home() / ".automyx" / "audit"

_instance: Optional[AuditLog] = None


class AuditLog:
    def __init__(self) -> None:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        self.session_id = uuid.uuid4().hex[:8]
        self._user = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
        self._day_file = self._day_path(datetime.now())

    def _day_path(self, dt: datetime) -> Path:
        return AUDIT_DIR / f"audit_{dt.strftime('%Y-%m-%d')}.jsonl"

    def log(
        self,
        action: str,
        args: Dict[str, Any],
        result: Any,
        ok: bool,
        duration_ms: int,
        workspace: str = "default",
    ) -> None:
        if isinstance(result, str):
            preview = result[:200]
        else:
            try:
                preview = str(result)[:200]
            except Exception:
                preview = ""

        entry = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "session": self.session_id,
            "action": action,
            "args": args,
            "result_ok": ok,
            "result_preview": preview,
            "user": self._user,
            "workspace": workspace,
            "duration_ms": duration_ms,
        }
        self._day_file = self._day_path(datetime.now())
        with self._day_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _iter_entries(self, days: int = 1) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for i in range(days):
            path = self._day_path(datetime.now() - timedelta(days=i))
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    def get_recent(self, n: int = 50, filter_tool: Optional[str] = None) -> List[Dict[str, Any]]:
        entries = self._iter_entries(days=7)
        if filter_tool:
            entries = [e for e in entries if e.get("action") == filter_tool]
        return entries[-n:]

    def export_csv(self, output_path: str, days: int = 7) -> str:
        entries = self._iter_entries(days=days)
        out = Path(output_path)
        fieldnames = ["ts", "session", "action", "result_ok", "user", "workspace", "duration_ms", "result_preview"]
        with out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(entries)
        return str(out)

    def get_stats(self) -> Dict[str, Any]:
        all_entries = self._iter_entries(days=365)
        today_entries = self._iter_entries(days=1)

        total = len(all_entries)
        ok_count = sum(1 for e in all_entries if e.get("result_ok"))
        success_rate = round(ok_count / total, 4) if total else 0.0

        tool_counter: Counter = Counter(e.get("action", "") for e in all_entries)
        top_tools = [{"tool": t, "count": c} for t, c in tool_counter.most_common(5)]

        sessions_today = len({e.get("session") for e in today_entries if e.get("session")})

        return {
            "total_actions": total,
            "success_rate": success_rate,
            "top_tools": top_tools,
            "sessions_today": sessions_today,
        }


def get_audit() -> AuditLog:
    global _instance
    if _instance is None:
        _instance = AuditLog()
    return _instance
