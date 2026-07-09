from __future__ import annotations

import json
import math
import re
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

RAG_DIR = Path.home() / ".automyx" / "rag"
INDEX_FILE = RAG_DIR / "index.json"

_rag_instance: Optional["RAGSystem"] = None


def _ensure():
    RAG_DIR.mkdir(parents=True, exist_ok=True)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ_\w]{2,}", text.lower())


def _tfidf_score(query_terms: List[str], doc_terms: List[str], all_doc_term_lists: List[List[str]]) -> float:
    if not doc_terms or not query_terms:
        return 0.0
    doc_counter = Counter(doc_terms)
    doc_len = len(doc_terms)
    N = len(all_doc_term_lists)
    score = 0.0
    for term in query_terms:
        tf = doc_counter.get(term, 0) / doc_len
        df = sum(1 for d in all_doc_term_lists if term in d)
        if df == 0:
            continue
        idf = math.log((N + 1) / (df + 1)) + 1.0
        score += tf * idf
    return score


class RAGSystem:
    def __init__(self):
        _ensure()
        self._index: Dict[str, Any] = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        if INDEX_FILE.exists():
            try:
                return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"chunks": [], "last_indexed": None}

    def save_index(self):
        _ensure()
        INDEX_FILE.write_text(json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8")

    def _make_chunks(self, content: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunks.append(content[start:end])
            start += chunk_size - overlap
        return chunks

    def index_file(self, file_path: str, workspace: Optional[str] = None):
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        self._index["chunks"] = [
            c for c in self._index["chunks"]
            if not (c["path"] == str(path) and c.get("workspace") == workspace)
        ]

        raw_chunks = self._make_chunks(content)
        lines = content.split("\n")
        line_offsets = []
        pos = 0
        for line in lines:
            line_offsets.append(pos)
            pos += len(line) + 1

        chunk_start = 0
        for i, chunk_text in enumerate(raw_chunks):
            char_start = i * (500 - 100)
            line_start = 0
            for li, off in enumerate(line_offsets):
                if off <= char_start:
                    line_start = li + 1
                else:
                    break

            keywords = list(set(_tokenize(chunk_text)))[:50]
            self._index["chunks"].append({
                "id": f"{path}::{i}",
                "path": str(path),
                "workspace": workspace,
                "content": chunk_text,
                "keywords": keywords,
                "line_start": line_start,
            })

        self._index["last_indexed"] = datetime.now().isoformat()

    def index_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        max_files: int = 200,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".md", ".txt", ".json"]

        root = Path(directory)
        files = []
        for ext in extensions:
            files.extend(root.rglob(f"*{ext}"))
            if len(files) >= max_files:
                break
        files = files[:max_files]

        for i, f in enumerate(files):
            if progress_callback:
                progress_callback(i + 1, len(files), str(f))
            self.index_file(str(f))

        self.save_index()

    def search(self, query: str, k: int = 5, workspace: Optional[str] = None) -> List[Dict[str, Any]]:
        query_terms = _tokenize(query)
        chunks = self._index.get("chunks", [])
        if workspace is not None:
            chunks = [c for c in chunks if c.get("workspace") == workspace]

        if not chunks:
            return []

        all_doc_terms = [c["keywords"] for c in chunks]

        scored = []
        for chunk in chunks:
            doc_terms = chunk["keywords"]
            score = _tfidf_score(query_terms, doc_terms, all_doc_terms)
            if score > 0:
                scored.append({
                    "path": chunk["path"],
                    "content": chunk["content"],
                    "score": round(score, 4),
                    "line_start": chunk.get("line_start", 0),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def get_context_for_query(self, query: str, max_chars: int = 3000) -> str:
        results = self.search(query, k=10)
        parts = []
        total = 0
        for r in results:
            header = f"[RAG CONTEXT - {r['path']}:{r['line_start']}]"
            block = f"{header}\n{r['content']}\n---"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n".join(parts)

    def clear_index(self, workspace: Optional[str] = None):
        if workspace is None:
            self._index = {"chunks": [], "last_indexed": None}
        else:
            self._index["chunks"] = [c for c in self._index["chunks"] if c.get("workspace") != workspace]
        self.save_index()

    def get_stats(self) -> Dict[str, Any]:
        chunks = self._index.get("chunks", [])
        paths = set(c["path"] for c in chunks)
        total_size = sum(len(c["content"]) for c in chunks)
        return {
            "total_chunks": len(chunks),
            "total_files": len(paths),
            "total_size_kb": round(total_size / 1024, 2),
            "last_indexed": self._index.get("last_indexed"),
        }


def get_rag() -> RAGSystem:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGSystem()
    return _rag_instance
