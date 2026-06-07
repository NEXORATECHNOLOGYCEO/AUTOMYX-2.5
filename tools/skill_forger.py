"""
Skill Forger - Auto-evolución de habilidades
Detecta patrones repetidos en AUMFORMBRING y forja nuevas SKILL.md automáticamente.
"""
import os
import re
import json
import hashlib
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional


class SkillForger:
    """Forjador automático de habilidades a partir de patrones aprendidos."""

    SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")
    AUMFORMBRING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aumformbring_data")
    HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nexus_data", "forger_history.json")
    REGISTRY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nexus_data", "forged_skills.json")

    DEFAULT_THRESHOLD = 3

    @staticmethod
    def _load_json(path: str, default=None):
        if not os.path.exists(path):
            return default if default is not None else []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default if default is not None else []

    @staticmethod
    def _save_json(path: str, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _kebab_case(text: str) -> str:
        s = re.sub(r"[^\w\s-]", "", text.lower())
        s = re.sub(r"[\s_]+", "-", s).strip("-")
        return s[:40] or "auto-skill"

    @staticmethod
    def _extract_keywords(text: str, n: int = 5) -> List[str]:
        stop = {"que", "como", "para", "con", "una", "del", "los", "las", "esto", "esta", "the", "and", "for", "with"}
        words = re.findall(r"\b[a-záéíóúñ]{4,}\b", text.lower())
        freq = defaultdict(int)
        for w in words:
            if w not in stop:
                freq[w] += 1
        return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:n]]

    # ---------- PATTERN ANALYSIS ----------
    @staticmethod
    def analyze_patterns(threshold: int = None) -> Dict[str, Any]:
        """Detecta patrones con usage_count >= threshold."""
        threshold = threshold or SkillForger.DEFAULT_THRESHOLD
        patterns_file = os.path.join(SkillForger.AUMFORMBRING_DIR, "learned_patterns.json")
        patterns = SkillForger._load_json(patterns_file, [])
        candidates = [p for p in patterns if p.get("usage_count", 0) >= threshold]
        return {
            "total_patterns": len(patterns),
            "candidates": len(candidates),
            "patterns": [{"pattern": p.get("pattern", ""), "count": p.get("usage_count", 0), "tags": p.get("tags", [])} for p in candidates],
        }

    @staticmethod
    def cluster_similar_requests(min_cluster_size: int = 3) -> Dict[str, Any]:
        """Agrupa peticiones similares por palabras clave compartidas."""
        memory_file = os.path.join(SkillForger.AUMFORMBRING_DIR, "conversation_memory.json")
        memory = SkillForger._load_json(memory_file, [])
        clusters: Dict[str, List[Dict]] = defaultdict(list)
        for conv in memory:
            kws = SkillForger._extract_keywords(conv.get("user_input", ""), 3)
            cluster_key = "_".join(sorted(kws)) if kws else "general"
            clusters[cluster_key].append(conv)
        valid = {k: v for k, v in clusters.items() if len(v) >= min_cluster_size}
        return {
            "total_clusters": len(clusters),
            "valid_clusters": len(valid),
            "clusters": [{"key": k, "size": len(v), "sample": v[0].get("user_input", "")[:100]} for k, v in valid.items()],
        }

    # ---------- FORGE SKILL ----------
    @staticmethod
    def check_duplicates(name: str) -> bool:
        return os.path.exists(os.path.join(SkillForger.SKILLS_DIR, name, "SKILL.md"))

    @staticmethod
    def forge_skill(cluster_key: str = None, custom_name: str = None) -> Dict[str, Any]:
        """Forja una nueva skill desde un cluster detectado o desde un trigger custom."""
        memory_file = os.path.join(SkillForger.AUMFORMBRING_DIR, "conversation_memory.json")
        memory = SkillForger._load_json(memory_file, [])

        related = []
        if cluster_key:
            target_kws = set(cluster_key.split("_"))
            for conv in memory:
                kws = set(SkillForger._extract_keywords(conv.get("user_input", ""), 3))
                if target_kws & kws:
                    related.append(conv)
        else:
            related = memory[-10:]

        if not related:
            return {"error": "No hay datos suficientes para forjar la skill"}

        # Extraer tools usadas en las respuestas
        tools_used = set()
        tool_pattern = re.compile(r'"action"\s*:\s*"(\w+)"')
        for conv in related:
            for m in tool_pattern.finditer(conv.get("agent_response", "")):
                tools_used.add(m.group(1))

        topic_kws = SkillForger._extract_keywords(" ".join(c.get("user_input", "") for c in related), 4)
        topic = " ".join(topic_kws[:3]) if topic_kws else "tarea"
        name = custom_name or SkillForger._kebab_case(f"auto-{topic}-{datetime.now().strftime('%Y%m%d')}")

        if SkillForger.check_duplicates(name):
            name = f"{name}-{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]}"

        sample_input = related[0].get("user_input", "")[:200]
        sample_response = related[0].get("agent_response", "")[:300]
        tools_list = "\n".join(f"- `{t}`" for t in sorted(tools_used)) if tools_used else "- (ninguna detectada)"

        skill_md = f"""---
name: {name}
description: "Skill auto-forjada por skill-forger. Tema: {topic}. Estado: experimental."
---
# {name}

**Estado:** EXPERIMENTAL (forjada automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M')})
**Patrones detectados:** {len(related)} conversaciones similares.
**Tema principal:** {topic}

## Trigger Típico
> {sample_input}

## Ejemplo de respuesta exitosa
{sample_response}

## Tools usadas históricamente
{tools_list}

## Reglas de ejecución derivadas
1. Cuando el usuario mencione conceptos relacionados con: **{', '.join(topic_kws[:5])}**, considera usar esta skill.
2. Sigue el patrón de respuesta del ejemplo, adaptando a los argumentos específicos.
3. Si la ejecución falla, registra el error en `forger_track_skill_usage` con `success=false` para que la skill se degrade.

## Promoción
Esta skill saldrá de estado experimental tras 3 usos exitosos consecutivos.
"""
        skill_dir = os.path.join(SkillForger.SKILLS_DIR, name)
        os.makedirs(skill_dir, exist_ok=True)
        skill_path = os.path.join(skill_dir, "SKILL.md")
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(skill_md)

        # Registrar en registry
        registry = SkillForger._load_json(SkillForger.REGISTRY_FILE, [])
        registry.append({
            "name": name,
            "status": "experimental",
            "created_at": datetime.now().isoformat(),
            "based_on": len(related),
            "tools": list(tools_used),
            "topic_keywords": topic_kws,
            "uses": 0,
            "successes": 0,
        })
        SkillForger._save_json(SkillForger.REGISTRY_FILE, registry)

        # History
        history = SkillForger._load_json(SkillForger.HISTORY_FILE, [])
        history.append({"action": "forge", "name": name, "at": datetime.now().isoformat()})
        SkillForger._save_json(SkillForger.HISTORY_FILE, history)

        return {"forged": name, "path": skill_path, "based_on_conversations": len(related), "tools_detected": list(tools_used)}

    # ---------- VALIDATION & PROMOTION ----------
    @staticmethod
    def validate_skill(name: str) -> Dict[str, Any]:
        path = os.path.join(SkillForger.SKILLS_DIR, name, "SKILL.md")
        if not os.path.exists(path):
            return {"valid": False, "reason": "no existe"}
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        has_frontmatter = content.startswith("---")
        has_name = re.search(r"name:\s*\S+", content) is not None
        has_description = re.search(r"description:\s*", content) is not None
        return {"valid": has_frontmatter and has_name and has_description, "name": name}

    @staticmethod
    def track_skill_usage(name: str, success: bool = True) -> Dict[str, Any]:
        registry = SkillForger._load_json(SkillForger.REGISTRY_FILE, [])
        for entry in registry:
            if entry["name"] == name:
                entry["uses"] = entry.get("uses", 0) + 1
                if success:
                    entry["successes"] = entry.get("successes", 0) + 1
                entry["last_used"] = datetime.now().isoformat()
                entry["success_rate"] = entry["successes"] / max(1, entry["uses"])
                SkillForger._save_json(SkillForger.REGISTRY_FILE, registry)
                return entry
        return {"error": f"Skill '{name}' no en registry"}

    @staticmethod
    def promote_skill(name: str) -> Dict[str, Any]:
        registry = SkillForger._load_json(SkillForger.REGISTRY_FILE, [])
        for entry in registry:
            if entry["name"] == name:
                if entry.get("successes", 0) >= 3:
                    entry["status"] = "stable"
                    SkillForger._save_json(SkillForger.REGISTRY_FILE, registry)
                    return {"promoted": name, "status": "stable"}
                return {"error": "InsuficientesÂ éxitos (necesita â‰¥ 3)"}
        return {"error": "no encontrada"}

    @staticmethod
    def demote_skill(name: str) -> Dict[str, Any]:
        registry = SkillForger._load_json(SkillForger.REGISTRY_FILE, [])
        for entry in registry:
            if entry["name"] == name:
                entry["status"] = "deprecated"
                SkillForger._save_json(SkillForger.REGISTRY_FILE, registry)
                return {"demoted": name}
        return {"error": "no encontrada"}

    @staticmethod
    def archive_skill(name: str) -> Dict[str, Any]:
        src = os.path.join(SkillForger.SKILLS_DIR, name)
        if not os.path.exists(src):
            return {"error": "no existe"}
        archive_dir = os.path.join(SkillForger.SKILLS_DIR, "_archived")
        os.makedirs(archive_dir, exist_ok=True)
        dst = os.path.join(archive_dir, name + "_" + datetime.now().strftime("%Y%m%d%H%M"))
        os.rename(src, dst)
        return {"archived": name, "moved_to": dst}

    @staticmethod
    def list_forged_skills() -> Dict[str, Any]:
        registry = SkillForger._load_json(SkillForger.REGISTRY_FILE, [])
        return {"count": len(registry), "skills": registry}

    @staticmethod
    def run_cycle(threshold: int = 3) -> Dict[str, Any]:
        """Ciclo completo: analiza â†’ forja â†’ valida."""
        analysis = SkillForger.analyze_patterns(threshold)
        clusters = SkillForger.cluster_similar_requests(threshold)
        forged = []
        for c in clusters["clusters"][:3]:
            res = SkillForger.forge_skill(c["key"])
            if "forged" in res:
                forged.append(res["forged"])
        return {"analysis": analysis, "clusters": clusters, "forged_skills": forged}
