from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

STATS_FILE = Path.home() / ".automyx" / "token_stats.json"

COSTS: Dict[str, tuple[float, float]] = {
    "minimax-m3": (0.20, 0.80),
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku": (0.25, 1.25),
    "gpt-oss-120b": (0.20, 0.80),
    "llama": (0.10, 0.30),
    "default": (0.50, 1.50),
}

_instance: Optional[TokenTracker] = None


def _cost_for(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    key = model.lower()
    rates = COSTS.get(key)
    if rates is None:
        for k in COSTS:
            if k in key:
                rates = COSTS[k]
                break
        else:
            rates = COSTS["default"]
    input_cost = (prompt_tokens / 1_000_000) * rates[0]
    output_cost = (completion_tokens / 1_000_000) * rates[1]
    return input_cost + output_cost


class TokenTracker:
    def __init__(self) -> None:
        self.reset_session()

    def reset_session(self) -> None:
        self._session_input = 0
        self._session_output = 0
        self._session_cost = 0.0
        self._session_calls = 0
        self._session_model = "default"
        self._session_start = datetime.now().isoformat()

    def track(self, model: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, Any]:
        self._session_model = model
        self._session_input += prompt_tokens
        self._session_output += completion_tokens
        self._session_cost += _cost_for(model, prompt_tokens, completion_tokens)
        self._session_calls += 1
        return self.get_session_stats()

    def get_session_stats(self) -> Dict[str, Any]:
        return {
            "total_input": self._session_input,
            "total_output": self._session_output,
            "total_tokens": self._session_input + self._session_output,
            "cost_usd": round(self._session_cost, 6),
            "calls": self._session_calls,
            "model": self._session_model,
        }

    def get_all_time_stats(self) -> Dict[str, Any]:
        if not STATS_FILE.exists():
            return {"sessions": 0, "total_input": 0, "total_output": 0, "total_cost_usd": 0.0}
        try:
            data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        return data

    def save_session(self) -> None:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            existing = json.loads(STATS_FILE.read_text(encoding="utf-8")) if STATS_FILE.exists() else {}
        except Exception:
            existing = {}

        existing["sessions"] = existing.get("sessions", 0) + 1
        existing["total_input"] = existing.get("total_input", 0) + self._session_input
        existing["total_output"] = existing.get("total_output", 0) + self._session_output
        existing["total_cost_usd"] = round(existing.get("total_cost_usd", 0.0) + self._session_cost, 6)
        existing["last_saved"] = datetime.now().isoformat()

        STATS_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def get_tracker() -> TokenTracker:
    global _instance
    if _instance is None:
        _instance = TokenTracker()
    return _instance
