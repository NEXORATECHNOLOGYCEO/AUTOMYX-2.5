"""
RAG Memory Tools - Memoria vectorial local
Indexa archivos personales en ChromaDB para búsqueda semántica.
"""
import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import requests
except ImportError:
    requests = None


class RAGMemoryTools:
    """Sistema RAG local con ChromaDB."""

    BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data", "rag_vectors")
    QUERY_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data", "rag_queries.log")
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    _client = None
    _embedder = None
    _model_name = DEFAULT_MODEL

    @staticmethod
    def _ensure_client():
        if RAGMemoryTools._client is not None:
            return RAGMemoryTools._client
        if chromadb is None:
            return None
        os.makedirs(RAGMemoryTools.BASE_DIR, exist_ok=True)
        RAGMemoryTools._client = chromadb.PersistentClient(path=RAGMemoryTools.BASE_DIR, settings=Settings(anonymized_telemetry=False))
        return RAGMemoryTools._client

    @staticmethod
    def _ensure_embedder():
        if RAGMemoryTools._embedder is not None:
            return RAGMemoryTools._embedder
        if SentenceTransformer is None:
            return None
        RAGMemoryTools._embedder = SentenceTransformer(RAGMemoryTools._model_name)
        return RAGMemoryTools._embedder

    @staticmethod
    def _embed(texts: List[str]) -> Optional[List[List[float]]]:
        emb = RAGMemoryTools._ensure_embedder()
        if emb is None:
            return None
        return emb.encode(texts, show_progress_bar=False).tolist()

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
            i += chunk_size - overlap
        return chunks

    @staticmethod
    def _extract_file_text(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".pdf":
                if pdfplumber:
                    with pdfplumber.open(file_path) as pdf:
                        return "\n".join((p.extract_text() or "") for p in pdf.pages)
                if PdfReader:
                    reader = PdfReader(file_path)
                    return "\n".join((p.extract_text() or "") for p in reader.pages)
                return ""
            if ext == ".docx" and DocxDocument:
                doc = DocxDocument(file_path)
                return "\n".join(p.text for p in doc.paragraphs)
            if ext in {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv", ".log", ".yml", ".yaml"}:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except Exception:
            return ""
        return ""

    # ---------- COLLECTIONS ----------
    @staticmethod
    def init_collection(collection_name: str, embedding_model: str = None) -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "Falta instalar chromadb (pip install chromadb sentence-transformers)"}
        if embedding_model:
            RAGMemoryTools._model_name = embedding_model
            RAGMemoryTools._embedder = None
        try:
            client.get_or_create_collection(collection_name)
            return {"initialized": collection_name, "model": RAGMemoryTools._model_name}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def list_collections() -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        cols = client.list_collections()
        return {"count": len(cols), "collections": [c.name for c in cols]}

    @staticmethod
    def collection_stats(collection_name: str) -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        try:
            col = client.get_collection(collection_name)
            return {"name": collection_name, "count": col.count()}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def delete_collection(collection_name: str) -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        try:
            client.delete_collection(collection_name)
            return {"deleted": collection_name}
        except Exception as e:
            return {"error": str(e)}

    # ---------- INDEXING ----------
    @staticmethod
    def index_file(collection_name: str, file_path: str) -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        if not os.path.exists(file_path):
            return {"error": f"Archivo no existe: {file_path}"}
        text = RAGMemoryTools._extract_file_text(file_path)
        if not text.strip():
            return {"skipped": file_path, "reason": "sin texto extraíble"}
        chunks = RAGMemoryTools._chunk_text(text)
        embeddings = RAGMemoryTools._embed(chunks)
        if embeddings is None:
            return {"error": "Falta sentence-transformers"}
        col = client.get_or_create_collection(collection_name)
        ids = [hashlib.md5(f"{file_path}_{i}".encode()).hexdigest() for i in range(len(chunks))]
        metadatas = [{"source": file_path, "chunk_index": i, "indexed_at": datetime.now().isoformat()} for i in range(len(chunks))]
        col.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        return {"indexed": file_path, "chunks": len(chunks)}

    @staticmethod
    def index_folder(collection_name: str, folder_path: str, extensions: List[str] = None) -> Dict[str, Any]:
        if not os.path.isdir(folder_path):
            return {"error": f"Carpeta no existe: {folder_path}"}
        extensions = extensions or [".pdf", ".docx", ".txt", ".md", ".py", ".html", ".json"]
        extensions = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions]
        indexed_files = 0
        total_chunks = 0
        errors = []
        for root, _, files in os.walk(folder_path):
            for f in files:
                if os.path.splitext(f)[1].lower() in extensions:
                    full = os.path.join(root, f)
                    res = RAGMemoryTools.index_file(collection_name, full)
                    if "indexed" in res:
                        indexed_files += 1
                        total_chunks += res.get("chunks", 0)
                    elif "error" in res:
                        errors.append({full: res["error"]})
        return {"indexed_files": indexed_files, "total_chunks": total_chunks, "errors": errors[:10]}

    @staticmethod
    def index_url(collection_name: str, url: str) -> Dict[str, Any]:
        if requests is None:
            return {"error": "Falta requests"}
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 Automyx-RAG"})
            r.raise_for_status()
            text = re.sub(r"<[^>]+>", " ", r.text)
            text = re.sub(r"\s+", " ", text).strip()
        except Exception as e:
            return {"error": f"Error descargando: {e}"}
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        chunks = RAGMemoryTools._chunk_text(text)
        embeddings = RAGMemoryTools._embed(chunks)
        if embeddings is None:
            return {"error": "Falta sentence-transformers"}
        col = client.get_or_create_collection(collection_name)
        ids = [hashlib.md5(f"{url}_{i}".encode()).hexdigest() for i in range(len(chunks))]
        metadatas = [{"source": url, "chunk_index": i, "type": "url"} for i in range(len(chunks))]
        col.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        return {"indexed": url, "chunks": len(chunks)}

    @staticmethod
    def index_conversation(collection_name: str, user_input: str, agent_response: str) -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        text = f"USER: {user_input}\nASSISTANT: {agent_response}"
        chunks = RAGMemoryTools._chunk_text(text, chunk_size=300)
        embeddings = RAGMemoryTools._embed(chunks)
        if embeddings is None:
            return {"error": "Falta sentence-transformers"}
        col = client.get_or_create_collection(collection_name)
        ids = [hashlib.md5(f"{user_input}_{i}_{datetime.now().isoformat()}".encode()).hexdigest() for i in range(len(chunks))]
        metadatas = [{"source": "conversation", "chunk_index": i, "timestamp": datetime.now().isoformat()} for i in range(len(chunks))]
        col.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        return {"indexed_conversation": True, "chunks": len(chunks)}

    # ---------- QUERY ----------
    @staticmethod
    def query(collection_name: str, query_text: str, k: int = 5) -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        try:
            col = client.get_collection(collection_name)
            emb = RAGMemoryTools._embed([query_text])
            if emb is None:
                return {"error": "Falta sentence-transformers"}
            res = col.query(query_embeddings=emb, n_results=k)
            results = []
            for i in range(len(res.get("documents", [[]])[0])):
                results.append({
                    "text": res["documents"][0][i][:500],
                    "source": res["metadatas"][0][i].get("source", ""),
                    "distance": res["distances"][0][i] if "distances" in res else None,
                })
            os.makedirs(os.path.dirname(RAGMemoryTools.QUERY_LOG), exist_ok=True)
            with open(RAGMemoryTools.QUERY_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] {collection_name}: {query_text[:100]}\n")
            return {"query": query_text, "results": results}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def answer(collection_name: str, question: str, k: int = 5) -> Dict[str, Any]:
        """Devuelve respuesta sintetizada con citas (texto crudo, listo para inyectar en LLM)."""
        q = RAGMemoryTools.query(collection_name, question, k)
        if "error" in q:
            return q
        context_parts = []
        citations = []
        for r in q["results"]:
            context_parts.append(r["text"])
            if r["source"] not in citations:
                citations.append(r["source"])
        return {
            "question": question,
            "context": "\n\n---\n\n".join(context_parts),
            "citations": citations,
            "instruction_for_llm": f"Responde a la pregunta '{question}' usando SOLO el contexto provisto. Cita las fuentes al final.",
        }

    @staticmethod
    def delete_document(collection_name: str, source: str) -> Dict[str, Any]:
        client = RAGMemoryTools._ensure_client()
        if client is None:
            return {"error": "ChromaDB no disponible"}
        try:
            col = client.get_collection(collection_name)
            col.delete(where={"source": source})
            return {"deleted_source": source}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def sync_aumformbring(collection_name: str = "aumformbring") -> Dict[str, Any]:
        memory_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aumformbring_data", "conversation_memory.json")
        if not os.path.exists(memory_file):
            return {"error": "No hay memoria AUMFORMBRING"}
        with open(memory_file, "r", encoding="utf-8") as f:
            memory = json.load(f)
        count = 0
        for conv in memory:
            res = RAGMemoryTools.index_conversation(collection_name, conv.get("user_input", ""), conv.get("agent_response", ""))
            if "indexed_conversation" in res:
                count += 1
        return {"synced_conversations": count, "collection": collection_name}
