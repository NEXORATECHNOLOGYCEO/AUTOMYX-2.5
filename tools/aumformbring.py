"""
AUMFORMBRING - Sistema de Auto-Aprendizaje y Auto-Mejo de Automyx
Aprende de las conversaciones, extrae patrones y se mejora a sí mismo automáticamente
"""
import os
import json
import re
import math
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import Counter


STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las",
    "por", "un", "una", "para", "con", "no", "al", "lo", "como", "más",
    "pero", "sus", "le", "ya", "este", "entre", "porque", "todo", "esta",
    "muy", "sin", "ese", "esa", "eso", "esa", "les", "son", "era", "han",
}


class Aumformbring:
    """Clase principal del sistema AUMFORMBRING"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aumformbring_data")

        self.storage_dir = storage_dir
        self.memory_file = os.path.join(storage_dir, "conversation_memory.json")
        self.skills_file = os.path.join(storage_dir, "learned_skills.json")
        self.patterns_file = os.path.join(storage_dir, "learned_patterns.json")
        self.improvements_file = os.path.join(storage_dir, "auto_improvements.json")

        os.makedirs(storage_dir, exist_ok=True)
        self._init_data_files()

    def _init_data_files(self):
        for file_path in [self.memory_file, self.skills_file, self.patterns_file, self.improvements_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)

    def _load_json(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_json(self, file_path: str, data: List[Dict]):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:16]

    _CACHED_IDF = None

    def _compute_idf(self, memory: List[Dict] = None) -> Dict[str, float]:
        """Compute IDF weights from conversation memory."""
        if self._CACHED_IDF is not None:
            return self._CACHED_IDF
        if memory is None:
            memory = self._load_json(self.memory_file)
        n_docs = len(memory) + 1
        df = Counter()
        for conv in memory:
            words = set(
                w for w in re.findall(r"\w{3,}", conv.get("user_input", "").lower())
                if w not in STOPWORDS
            )
            for w in words:
                df[w] += 1
        idf = {w: math.log(n_docs / (1 + df[w])) for w in df}
        idf["_default"] = 1.0
        self._CACHED_IDF = idf
        return idf

    def _text_to_vector(self, text: str, idf: Dict[str, float]) -> Dict[str, float]:
        words = re.findall(r"\w{3,}", text.lower())
        tf = Counter(words)
        mag = math.sqrt(sum((tf[w] * idf.get(w, idf.get("_default", 1.0))) ** 2 for w in tf))
        if mag == 0:
            return {}
        return {w: (tf[w] * idf.get(w, idf.get("_default", 1.0))) / mag for w in tf}

    def _cosine_similarity(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        if not common:
            return 0.0
        dot = sum(a[w] * b[w] for w in common)
        return dot  # both vectors are already unit-normalized

    # ---------- STORE ----------

    def store_conversation(self, user_input: str, agent_response: str, metadata: Dict = None) -> str:
        memory = self._load_json(self.memory_file)

        raw_tags = self._extract_tags(user_input + " " + agent_response)
        tools_used = self._extract_tools_used(agent_response)
        success, error_hint = self._detect_success(agent_response)
        intent = self._detect_intent(user_input)

        conversation = {
            "id": self._generate_hash(user_input + agent_response),
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input[:500],
            "agent_response": agent_response[:2000],
            "metadata": metadata or {},
            "tools_used": tools_used,
            "success": success,
            "error_hint": error_hint,
            "intent": intent,
            "tags": raw_tags,
        }

        memory.append(conversation)
        self._save_json(self.memory_file, memory[-500:])  # keep last 500

        self._extract_useful_patterns(conversation)
        self._learn_skill_if_tutorial(conversation)

        # Invalidate IDF cache
        self._CACHED_IDF = None

        return conversation["id"]

    def _extract_tools_used(self, response: str) -> List[str]:
        tools = []
        for m in re.finditer(r'"action"\s*:\s*"([^"]+)"', response):
            tools.append(m.group(1))
        for m in re.finditer(r'"tool"\s*:\s*"([^"]+)"', response):
            t = m.group(1)
            if t not in tools:
                tools.append(t)
        return list(dict.fromkeys(tools))  # dedup preserving order

    def _detect_success(self, response: str) -> tuple:
        r = response.lower()
        if any(p in r for p in ["error", "fallo", "fail", "exception", "traceback"]):
            return False, r[:200]
        if any(p in r for p in ["completado", "exitosamente", "success", "ok"]):
            return True, ""
        return True, ""

    def _detect_intent(self, text: str) -> str:
        t = text.lower()
        pairs = [
            ("create", ["crea", "haz", "genera", "nuevo", "nueva", "crear", "escribe"]),
            ("edit", ["edita", "modifica", "cambia", "actualiza", "editar"]),
            ("search", ["busca", "encuentra", "localiza", "investiga", "buscar"]),
            ("delete", ["borra", "elimina", "quita", "suprime"]),
            ("analyze", ["analiza", "revisa", "examina", "comprueba"]),
            ("play", ["reproduce", "pon", "abre video", "reproducir"]),
            ("setup", ["configura", "instala", "prepara", "conectar"]),
        ]
        for label, kws in pairs:
            if any(kw in t for kw in kws):
                return label
        return "general"

    def _extract_tags(self, text: str) -> List[str]:
        keywords = [
            "blender", "3d", "foto", "imagen", "editar", "autopilot", "git",
            "python", "codigo", "programar", "web", "automatico", "voz",
            "video", "audio", "windows", "app", "archivo", "carpeta",
            "whatsapp", "email", "excel", "pdf", "docker", "tiktok",
            "gemini", "vyrex", "capcut", "obs", "notion",
        ]
        tags = []
        text_lower = text.lower()
        for kw in keywords:
            if kw in text_lower:
                tags.append(kw)
        return tags[:5]

    # ---------- ANALYSIS ----------

    def _extract_useful_patterns(self, conversation: Dict):
        patterns = self._load_json(self.patterns_file)
        user_input = conversation["user_input"]

        pattern_id = self._generate_hash(user_input)

        existing = next((p for p in patterns if p["id"] == pattern_id), None)
        if existing:
            existing["usage_count"] += 1
            existing["last_seen"] = conversation["timestamp"]
        else:
            patterns.append({
                "id": pattern_id,
                "pattern": user_input[:150],
                "tools_used": conversation.get("tools_used", []),
                "intent": conversation.get("intent", "general"),
                "success": conversation.get("success", True),
                "response_example": conversation["agent_response"][:300],
                "tags": conversation["tags"],
                "timestamp": conversation["timestamp"],
                "last_seen": conversation["timestamp"],
                "usage_count": 1,
            })

        patterns = sorted(patterns, key=lambda x: x["usage_count"], reverse=True)[:100]
        self._save_json(self.patterns_file, patterns)

    def _learn_skill_if_tutorial(self, conversation: Dict):
        ui = conversation["user_input"].lower()
        if not any(word in ui for word in ["como", "como", "que hacer", "que hacer", "tutorial", "paso a paso"]):
            return

        skills = self._load_json(self.skills_file)
        name_raw = conversation["user_input"][:60]
        safe_name = f"auto-{self._generate_hash(name_raw)}"

        for s in skills:
            if s.get("id") == safe_name:
                return  # already exists

        skills.append({
            "id": safe_name,
            "name": f"Aprendizaje: {name_raw}",
            "description": conversation["user_input"][:120],
            "trigger": conversation["user_input"][:80],
            "response_template": conversation["agent_response"],
            "tools_used": conversation.get("tools_used", []),
            "tags": conversation["tags"],
            "learned_at": conversation["timestamp"],
            "usage_count": 0,
            "success_rate": 1.0,
            "active": True,
        })
        self._save_json(self.skills_file, skills)

    # ---------- QUERY ----------

    def get_learned_skills(self) -> List[Dict]:
        return self._load_json(self.skills_file)

    def get_conversation_memory(self, limit: int = 20, tags: List[str] = None) -> List[Dict]:
        memory = self._load_json(self.memory_file)
        if tags:
            memory = [m for m in memory if any(tag in m.get("tags", []) for tag in tags)]
        return sorted(memory, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_useful_patterns(self, limit: int = 10) -> List[Dict]:
        patterns = self._load_json(self.patterns_file)
        return sorted(patterns, key=lambda x: x["usage_count"], reverse=True)[:limit]

    def search_memory(self, query: str) -> List[Dict]:
        memory = self._load_json(self.memory_file)
        q = query.lower()
        results = []
        for conv in memory:
            if (q in conv["user_input"].lower() or
                q in conv["agent_response"].lower() or
                any(q in tag.lower() for tag in conv.get("tags", []))):
                results.append(conv)
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:10]

    # ---------- SEMANTIC RECALL (TF-IDF) ----------

    def recall_similar_conversation(self, user_input: str, threshold: float = 0.12) -> Optional[Dict]:
        memory = self._load_json(self.memory_file)
        if not memory or not user_input.strip():
            return None

        idf = self._compute_idf(memory)
        q_vec = self._text_to_vector(user_input, idf)
        if not q_vec:
            return None

        best_score = 0.0
        best_conv = None

        for conv in reversed(memory):
            c_vec = self._text_to_vector(conv.get("user_input", ""), idf)
            score = self._cosine_similarity(q_vec, c_vec)
            if score > best_score:
                best_score = score
                best_conv = conv

        return best_conv if best_score >= threshold else None

    def recall_similar_conversations(self, user_input: str, limit: int = 3, threshold: float = 0.08) -> List[Dict]:
        """Returns top-K similar conversations sorted by relevance."""
        memory = self._load_json(self.memory_file)
        if not memory or not user_input.strip():
            return []

        idf = self._compute_idf(memory)
        q_vec = self._text_to_vector(user_input, idf)
        if not q_vec:
            return []

        scored = []
        for conv in memory:
            c_vec = self._text_to_vector(conv.get("user_input", ""), idf)
            score = self._cosine_similarity(q_vec, c_vec)
            if score >= threshold:
                scored.append((score, conv))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:limit]]

    # ---------- CONTEXT INJECTION ----------

    def inject_context(self, user_input: str, max_convs: int = 3, max_lessons: int = 5) -> str:
        """Generates a formatted string of relevant past experiences for LLM context injection."""
        parts = []

        # 1. Similar conversations — SOLO pistas de tools útiles. NUNCA incluir las
        # respuestas pasadas del agente: el modelo las confundía con la conversación
        # actual y continuaba tareas viejas en vez de atender la orden nueva.
        similar = self.recall_similar_conversations(user_input, limit=max_convs)
        hints = [
            (conv["user_input"][:90], conv.get("tools_used", [])[:4])
            for conv in similar if conv.get("tools_used")
        ]
        if hints:
            parts.append(
                "[EXPERIENCIA PREVIA — tareas PASADAS ya terminadas, solo referencia "
                "de qué tools funcionaron. NO continúes ni repitas esas tareas: "
                "atiende únicamente la orden actual del usuario.]"
            )
            for i, (q, tools) in enumerate(hints, 1):
                parts.append(f"{i}. \"{q}\" → tools útiles: {', '.join(tools)}")

        # 2. Relevant patterns
        patterns = self._load_json(self.patterns_file)
        q_words = set(re.findall(r"\w{4,}", user_input.lower()))
        relevant = [
            p for p in patterns
            if q_words & set(re.findall(r"\w{4,}", p.get("pattern", "").lower()))
        ]
        relevant.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
        if relevant:
            parts.append("\n[PATRONES RELEVANTES]")
            for p in relevant[:3]:
                parts.append(
                    f"- \"{p['pattern'][:80]}...\" (usado {p['usage_count']} veces, "
                    f"intent: {p.get('intent', '?')})"
                )

        # 3. Error lessons matching intent
        try:
            from tools.error_learning import ErrorLearningSystem
            warnings = ErrorLearningSystem.get_warnings_for_request(user_input)
            if warnings:
                parts.append(f"\n{warnings}")
        except Exception:
            pass

        return "\n".join(parts)

    # ---------- AUTO-IMPROVE ----------

    def auto_improve(self, focus_area: str = None) -> List[str]:
        improvements = self._load_json(self.improvements_file)
        memory = self._load_json(self.memory_file)
        patterns = self._load_json(self.patterns_file)
        skills = self._load_json(self.skills_file)

        actions_taken = []

        # 1. Archive failed skills
        for s in skills:
            if not s.get("active", True):
                continue
            usage = s.get("usage_count", 0)
            rate = s.get("success_rate", 1.0)
            if usage >= 3 and rate < 0.3:
                s["active"] = False
                actions_taken.append(f"archived_skill:{s.get('name','?')} (rate={rate:.1f})")

        self._save_json(self.skills_file, skills)

        # 2. Deduplicate patterns by fuzzy similarity
        unique = []
        seen_hashes = set()
        for p in patterns:
            pid = p.get("id", "")
            if pid not in seen_hashes:
                seen_hashes.add(pid)
                unique.append(p)
            else:
                actions_taken.append(f"merged_duplicate:{p.get('pattern','')[:30]}")
        self._save_json(self.patterns_file, unique)

        # 3. Log the improvement
        now = datetime.now()
        recent = sum(
            1 for m in memory
            if (now - datetime.fromisoformat(m.get("timestamp", "2000-01-01"))).days < 1
        )
        improvement = {
            "id": self._generate_hash(now.isoformat()),
            "timestamp": now.isoformat(),
            "focus_area": focus_area,
            "analysis": {
                "total_conversations": len(memory),
                "total_patterns": len(unique),
                "total_skills": len(skills),
                "recent_activity": recent,
            },
            "actions_taken": actions_taken,
        }
        improvements.append(improvement)
        self._save_json(self.improvements_file, improvements)

        return actions_taken

    # ---------- SKILL MANAGEMENT ----------

    def create_custom_skill(self, name: str, trigger: str, response: str, description: str = "") -> str:
        skills = self._load_json(self.skills_file)
        skill_id = self._generate_hash(name + trigger)

        for s in skills:
            if s.get("id") == skill_id:
                return f"Skill '{name}' ya existe."

        skills.append({
            "id": skill_id,
            "name": name,
            "description": description or name,
            "trigger": trigger,
            "response_template": response,
            "tags": ["custom", "manual"],
            "learned_at": datetime.now().isoformat(),
            "usage_count": 0,
            "success_rate": 1.0,
            "active": True,
        })
        self._save_json(self.skills_file, skills)
        return f"Habilidad personalizada '{name}' creada exitosamente!"

    def track_skill_usage(self, skill_name: str, success: bool = True) -> None:
        skills = self._load_json(self.skills_file)
        for s in skills:
            if s.get("name", "").lower() == skill_name.lower():
                old_usage = s.get("usage_count", 0)
                old_rate = s.get("success_rate", 1.0)
                s["usage_count"] = old_usage + 1
                if success:
                    s["success_rate"] = ((old_rate * old_usage) + 1) / (old_usage + 1)
                else:
                    s["success_rate"] = (old_rate * old_usage) / (old_usage + 1)
                break
        self._save_json(self.skills_file, skills)

    # ---------- MISC ----------

    def forget_conversation(self, conversation_id: str) -> str:
        memory = self._load_json(self.memory_file)
        before = len(memory)
        memory = [m for m in memory if m["id"] != conversation_id]
        if len(memory) < before:
            self._save_json(self.memory_file, memory)
            return f"Conversación {conversation_id} olvidada"
        return f"Conversación {conversation_id} no encontrada"

    def clear_all_memory(self) -> str:
        self._save_json(self.memory_file, [])
        self._save_json(self.skills_file, [])
        self._save_json(self.patterns_file, [])
        self._CACHED_IDF = None
        return "Toda la memoria de AUMFORMBRING ha sido limpiada"

    def get_stats(self) -> Dict[str, Any]:
        memory = self._load_json(self.memory_file)
        skills = self._load_json(self.skills_file)
        patterns = self._load_json(self.patterns_file)
        improvements = self._load_json(self.improvements_file)
        return {
            "total_conversations": len(memory),
            "total_learned_skills": len(skills),
            "total_patterns": len(patterns),
            "total_improvements": len(improvements),
            "successful_convs": sum(1 for m in memory if m.get("success", True)),
            "failed_convs": sum(1 for m in memory if not m.get("success", True)),
            "top_tools": self._get_top_tools(memory),
            "storage_location": self.storage_dir,
        }

    @staticmethod
    def _get_top_tools(memory: List[Dict], limit: int = 5) -> List[str]:
        counter = Counter()
        for m in memory:
            for t in m.get("tools_used", []):
                counter[t] += 1
        return [t for t, _ in counter.most_common(limit)]


aumformbring_system = Aumformbring()
