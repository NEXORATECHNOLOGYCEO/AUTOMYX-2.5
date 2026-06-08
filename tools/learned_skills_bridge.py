"""
Learned Skills Bridge - Convierte learned_skills.json de Aumformbring
en archivos SKILL.md funcionales que el agente puede usar en runtime.
"""
import os
import json
import logging
from typing import List

logger = logging.getLogger("automyx.learned_skills_bridge")


class LearnedSkillsBridge:
    """Puente entre learned_skills.json (Aumformbring) y skills/<name>/SKILL.md."""

    @staticmethod
    def get_learned_skills() -> List[dict]:
        """Lee todas las habilidades aprendidas de Aumformbring."""
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aumformbring_data")
        skills_file = os.path.join(base_dir, "learned_skills.json")
        if not os.path.exists(skills_file):
            return []
        try:
            with open(skills_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return list(data.values())
            return []
        except Exception as e:
            logger.warning(f"error reading learned_skills.json: {e}")
            return []

    @staticmethod
    def sync_all() -> int:
        """Sincroniza TODAS las learned_skills a archivos SKILL.md.
        Retorna cuantas se sincronizaron."""
        from tools.skill_tools import SkillTools

        skills = LearnedSkillsBridge.get_learned_skills()
        synced = 0
        skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")

        for s in skills:
            name_raw = s.get("name", "") or s.get("trigger", "unknown")
            usage = s.get("usage_count", 0) or s.get("times_used", 0)
            if isinstance(usage, str):
                try:
                    usage = int(usage)
                except (ValueError, TypeError):
                    usage = 0

            # Solo sincronizar skills con uso suficiente
            if usage < 2:
                continue

            # Generar nombre valido para directorio
            safe_name = name_raw.lower().strip()
            safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in safe_name)
            safe_name = safe_name.strip("-").strip("_")
            if not safe_name:
                safe_name = f"auto-skill-{hash(name_raw) % 10000:04d}"
            if not safe_name.startswith("auto-"):
                safe_name = f"auto-{safe_name}"

            skill_path = os.path.join(skills_dir, safe_name, "SKILL.md")
            if os.path.exists(skill_path):
                continue  # ya existe, no duplicar

            # Construir contenido SKILL.md
            trigger = s.get("trigger", name_raw)
            response = s.get("response_template", "") or s.get("description", "")
            tags = s.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            description = s.get("description", trigger)[:120]
            content = f"""---
name: {safe_name}
description: {description}
source: learned_skills_bridge
created: auto
usage_count: {usage}
tags: [{', '.join(str(t) for t in tags[:5])}]
---

# {safe_name}

## Trigger
{trigger}

## Response Template
{response}

## Instrucciones
Cuando el usuario haga algo relacionado con: {trigger}
Usa las herramientas disponibles para completar la tarea siguiendo el patron aprendido.
"""
            try:
                SkillTools.create_skill(safe_name, description[:100], content)
                synced += 1
                logger.info(f"Synced learned skill: {safe_name}")
            except Exception as e:
                logger.warning(f"sync skill {safe_name}: {e}")

        return synced
