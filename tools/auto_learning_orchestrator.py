"""
Auto-Learning Orchestrator - Orquestador central del ciclo de auto-aprendizaje
Conecta ErrorLearningSystem + SkillForger + Aumformbring en un pipeline automático
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("automyx.auto_learning")


class AutoLearningOrchestrator:
    """Orquestador del ciclo completo de auto-aprendizaje y auto-mejora."""

    DEFAULT_CONFIG = {
        "cycle_interval_conversations": 5,
        "pattern_threshold": 3,
        "auto_promote_after_successes": 3,
        "auto_archive_after_uses": 8,
        "auto_archive_min_rate": 0.3,
        "max_skills_per_cycle": 3,
        "enable_error_to_skill": True,
        "enable_conversation_memory": True,
        "enable_auto_promotion": True,
        "enable_auto_archive": True,
        "enable_learned_skills_sync": True,
    }

    _config = dict(DEFAULT_CONFIG)
    _config_loaded = False

    @classmethod
    def get_config(cls) -> dict:
        if not cls._config_loaded:
            cfg_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "config", "auto_learning.json"
            )
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cls._config.update(json.load(f))
                except Exception as e:
                    logger.warning(f"config error: {e}")
            cls._config_loaded = True
        return cls._config

    @classmethod
    def run_full_cycle(cls, force: bool = False) -> Dict[str, Any]:
        """Ejecuta el pipeline completo de auto-evolucion."""
        cfg = cls.get_config()
        report: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "errors_to_lessons": 0,
            "skills_forged": 0,
            "skills_promoted": 0,
            "skills_archived": 0,
            "learned_skills_synced": 0,
            "auto_improvements": 0,
            "status": "ok",
            "details": [],
        }

        # 1. Errores -> lecciones -> candidatos a skill
        if cfg.get("enable_error_to_skill"):
            try:
                from tools.error_learning import ErrorLearningSystem
                candidates = ErrorLearningSystem.analyze_for_skill_creation()
                if candidates:
                    report["errors_to_lessons"] = len(candidates)
                    report["details"].append(f"{len(candidates)} errores candidatos a skill")
            except Exception as e:
                logger.warning(f"error->skill: {e}")

        # 2. Ciclo SkillForger: analizar patrones -> forjar skills
        try:
            from tools.skill_forger import SkillForger
            cycle_result = SkillForger.run_cycle(
                threshold=cfg.get("pattern_threshold", 3)
            )
            forged = cycle_result.get("forged_skills", [])
            report["skills_forged"] = len(forged)
            if forged:
                report["details"].append(f"Forjadas: {', '.join(forged)}")
        except Exception as e:
            logger.warning(f"skill_forger cycle: {e}")

        # 3. Auto-promover skills experimentales
        if cfg.get("enable_auto_promotion"):
            try:
                promoted = cls._auto_promote_skills(cfg.get("auto_promote_after_successes", 3))
                report["skills_promoted"] = len(promoted)
                if promoted:
                    report["details"].append(f"Promovidas: {', '.join(promoted)}")
            except Exception as e:
                logger.warning(f"auto_promote: {e}")

        # 4. Auto-archivar skills con baja tasa de exito
        if cfg.get("enable_auto_archive"):
            try:
                archived = cls._auto_archive_failed_skills(
                    cfg.get("auto_archive_after_uses", 8),
                    cfg.get("auto_archive_min_rate", 0.3),
                )
                report["skills_archived"] = len(archived)
                if archived:
                    report["details"].append(f"Archivadas: {', '.join(archived)}")
            except Exception as e:
                logger.warning(f"auto_archive: {e}")

        # 5. Sincronizar learned_skills.json -> SKILL.md
        if cfg.get("enable_learned_skills_sync"):
            try:
                from tools.learned_skills_bridge import LearnedSkillsBridge
                synced = LearnedSkillsBridge.sync_all()
                report["learned_skills_synced"] = synced
                if synced:
                    report["details"].append(f"Synced {synced} learned skills")
            except Exception as e:
                logger.warning(f"learned_skills_sync: {e}")

        # 6. Auto-improve de Aumformbring
        try:
            from tools.aumformbring import aumformbring_system
            improvements = aumformbring_system.auto_improve()
            if improvements:
                report["auto_improvements"] = len(improvements)
        except Exception as e:
            logger.warning(f"auto_improve: {e}")

        logger.info(f"Auto-learning cycle: {report['status']} | "
                     f"forged={report['skills_forged']} promoted={report['skills_promoted']} "
                     f"archived={report['skills_archived']} synced={report['learned_skills_synced']}")
        return report

    @classmethod
    def _auto_promote_skills(cls, min_successes: int = 3) -> List[str]:
        """Promueve skills experimentales que han tenido suficientes usos exitosos."""
        from tools.skill_forger import SkillForger
        registry_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "nexus_data", "forged_skills.json"
        )
        if not os.path.exists(registry_path):
            return []
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            return []

        promoted = []
        for s in registry:
            name = s.get("name", "")
            status = s.get("status", "experimental")
            successes = s.get("successes", 0)
            if status == "experimental" and successes >= min_successes:
                try:
                    SkillForger.promote_skill(name)
                    promoted.append(name)
                except Exception as e:
                    logger.warning(f"promote {name}: {e}")
        return promoted

    @classmethod
    def _auto_archive_failed_skills(cls, min_uses: int = 8, min_rate: float = 0.3) -> List[str]:
        """Archiva skills con baja tasa de exito."""
        from tools.skill_forger import SkillForger
        registry_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "nexus_data", "forged_skills.json"
        )
        if not os.path.exists(registry_path):
            return []
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            return []

        archived = []
        for s in registry:
            name = s.get("name", "")
            uses = s.get("uses", 0)
            successes = s.get("successes", 0)
            rate = successes / max(uses, 1)
            if uses >= min_uses and rate < min_rate:
                try:
                    SkillForger.archive_skill(name)
                    archived.append(name)
                except Exception as e:
                    logger.warning(f"archive {name}: {e}")
        return archived
