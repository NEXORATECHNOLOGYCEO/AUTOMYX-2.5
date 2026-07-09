from __future__ import annotations

import difflib
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    _HAS_WATCHDOG = True
except ImportError:
    _HAS_WATCHDOG = False

_INSTANCE: Optional[PairAgent] = None

_SENSITIVITY_THRESHOLDS = {
    "low": 0.3,
    "medium": 0.05,
    "high": 0.0,
}


class PairAgent:
    def __init__(self, llm_runner: Callable[[list], str], callback: Optional[Callable[[str, str], None]] = None):
        self._llm = llm_runner
        self._callback = callback
        self._watching = False
        self._paused = False
        self._sensitivity = "medium"
        self._threshold = _SENSITIVITY_THRESHOLDS["medium"]
        self._history: list[dict] = []
        self._watched_dir: Optional[str] = None
        self._extensions: list[str] = [".py", ".js", ".ts"]
        self._last_known: dict[str, str] = {}
        self._observer = None
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_watching(self, directory: str, extensions: Optional[list[str]] = None):
        if extensions:
            self._extensions = extensions
        self._watched_dir = directory
        self._stop_event.clear()

        dir_path = Path(directory)
        for ext in self._extensions:
            for f in dir_path.rglob(f"*{ext}"):
                try:
                    self._last_known[str(f)] = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

        if _HAS_WATCHDOG:
            self._start_watchdog(directory)
        else:
            self._start_polling()

        self._watching = True

    def _start_watchdog(self, directory: str):
        agent = self

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.is_directory or agent._paused:
                    return
                path = event.src_path
                if not any(path.endswith(ext) for ext in agent._extensions):
                    return
                try:
                    new_content = Path(path).read_text(encoding="utf-8", errors="replace")
                except Exception:
                    return
                old_content = agent._last_known.get(path, "")
                if new_content != old_content:
                    agent._on_file_changed(path, new_content, old_content)
                    agent._last_known[path] = new_content

        self._observer = Observer()
        self._observer.schedule(Handler(), directory, recursive=True)
        self._observer.start()

    def _start_polling(self):
        def poll_loop():
            while not self._stop_event.is_set():
                if not self._paused:
                    dir_path = Path(self._watched_dir)
                    for ext in self._extensions:
                        for f in dir_path.rglob(f"*{ext}"):
                            path = str(f)
                            try:
                                current = f.read_text(encoding="utf-8", errors="replace")
                            except Exception:
                                continue
                            old = self._last_known.get(path, "")
                            if current != old:
                                self._on_file_changed(path, current, old)
                                self._last_known[path] = current
                time.sleep(5)

        self._poll_thread = threading.Thread(target=poll_loop, daemon=True)
        self._poll_thread.start()

    def stop_watching(self):
        self._stop_event.set()
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=2)
            except Exception:
                pass
            self._observer = None
        self._watching = False

    @property
    def is_watching(self) -> bool:
        return self._watching

    def set_sensitivity(self, level: str):
        if level not in _SENSITIVITY_THRESHOLDS:
            raise ValueError(f"Nivel inválido: {level}. Usa: {list(_SENSITIVITY_THRESHOLDS.keys())}")
        self._sensitivity = level
        self._threshold = _SENSITIVITY_THRESHOLDS[level]

    def _on_file_changed(self, file_path: str, new_content: str, old_content: str):
        if not old_content:
            return

        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

        if not diff:
            return

        changed_lines = sum(1 for l in diff if l.startswith(("+", "-")) and not l.startswith(("+++", "---")))
        total_lines = max(len(old_lines), 1)
        change_ratio = changed_lines / total_lines

        if change_ratio < self._threshold:
            return

        diff_text = "\n".join(diff[:50])
        suggestion = self._get_suggestion(file_path, diff_text)

        entry = {
            "file": file_path,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat(),
            "change_ratio": round(change_ratio, 3),
        }
        self._history.append(entry)

        if self._callback:
            try:
                self._callback(suggestion, file_path)
            except Exception:
                pass

    def _get_suggestion(self, file_path: str, diff: str) -> str:
        filename = Path(file_path).name
        prompt = (
            f"Analiza este cambio en el archivo '{filename}' y da una sugerencia corta (máximo 2 líneas). "
            f"Sé directo y específico. Si el cambio es correcto, confirma. Si hay mejora posible, indícala.\n\n"
            f"Diff:\n{diff}"
        )
        try:
            return self._llm([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"Error al obtener sugerencia: {e}"

    def get_history(self) -> list[dict]:
        return list(self._history)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False


def get_pair_agent(llm_runner: Callable[[list], str]) -> PairAgent:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = PairAgent(llm_runner)
    return _INSTANCE
