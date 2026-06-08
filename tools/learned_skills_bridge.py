"""
Learned Skills Bridge - Convierte learned_skills.json de Aumformbring
en archivos SKILL.md funcionales con validación de calidad y version tracking.
"""
import os
import json
import logging
from typing import List

logger = logging.getLogger("automyx.learned_skills_bridge")

VERSION = 2


class LearnedSkillsBridge:
    """Puente entre learned_skills.json (Aumformbring) y skills/<name>/SKILL.md."""

    @staticmethod
    def get_learned_skills() -> List[dict]:
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
    def _generate_skill_name(name_raw: str) -> str:
        """Genera un nombre de directorio válido y descriptivo."""
        safe = name_raw.lower().strip()
        safe = "".join(c if c.isalnum() or c in "- _" else " " for c in safe)
        safe = " ".join(safe.split())  # normalize whitespace
        safe = safe.replace(" ", "-")
        safe = "".join(c for c in safe if c.isalnum() or c in "-_")
        safe = safe.strip("-").strip("_")

        if not safe or len(safe) < 4:
            safe = f"auto-skill-{abs(hash(name_raw)) % 10000:04d}"

        # Extract meaningful part (first 2-3 words)
        parts = safe.split("-")
        if len(parts) > 3:
            safe = "-".join(parts[:3])

        if not safe.startswith("auto-"):
            safe = f"auto-{safe}"

        return safe[:50]

    @staticmethod
    def _validate_skill(s: dict) -> bool:
        """Quality gate: verifica que la skill tenga contenido útil."""
        name = s.get("name", "") or s.get("trigger", "")
        response = s.get("response_template", "") or s.get("description", "")
        usage = s.get("usage_count", 0) or s.get("times_used", 0)

        if isinstance(usage, str):
            try:
                usage = int(usage)
            except (ValueError, TypeError):
                usage = 0

        if usage < 2:
            return False

        if len(str(response).strip()) < 30:
            return False

        if len(str(name).strip()) < 5:
            return False

        return True

    @staticmethod
    def sync_all() -> int:
        from tools.skill_tools import SkillTools

        skills = LearnedSkillsBridge.get_learned_skills()
        synced = 0
        skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")

        for s in skills:
            if not LearnedSkillsBridge._validate_skill(s):
                continue

            name_raw = s.get("name", "") or s.get("trigger", "unknown")
            usage = s.get("usage_count", 0) or s.get("times_used", 0)
            if isinstance(usage, str):
                try:
                    usage = int(usage)
                except (ValueError, TypeError):
                    usage = 0

            safe_name = LearnedSkillsBridge._generate_skill_name(name_raw)
            skill_path = os.path.join(skills_dir, safe_name, "SKILL.md")

            trigger = str(s.get("trigger", name_raw))[:100]
            response = str(s.get("response_template", "") or s.get("description", ""))
            tags = s.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            description = str(s.get("description", trigger))[:120]

            content = f"""---
name: {safe_name}
description: {description}
source: learned_skills_bridge
bridge_version: {VERSION}
created: auto
usage_count: {usage}
tags: [{', '.join(str(t) for t in tags[:5])}]
---

# {safe_name}

## Trigger
{trigger}

## Response Pattern
```
{response[:500]}
```

## Instrucciones
Cuando el usuario haga algo relacionado con: {trigger}
Usa las herramientas disponibles para completar la tarea siguiendo el patron aprendido.

_Esta skill fue generada automaticamente por LearnedSkillsBridge v{VERSION}_
"""

            try:
                # Update if exists, create if not
                SkillTools.create_skill(safe_name, description[:100], content)
                synced += 1
                logger.info(f"Synced learned skill: {safe_name} (usage={usage})")
            except Exception as e:
                logger.warning(f"sync skill {safe_name}: {e}")

        return synced
