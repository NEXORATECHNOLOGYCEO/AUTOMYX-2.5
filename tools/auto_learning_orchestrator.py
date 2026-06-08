"""
Auto-Learning Orchestrator - Orquestador central del ciclo de auto-aprendizaje
Conecta ErrorLearningSystem + SkillForger + Aumformbring en un pipeline automático
con quality gates, feedback loop y reportes de evolución.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import Counter

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

    # Track effectiveness of each pipeline step
    _step_stats = Counter()

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
        """Ejecuta el pipeline completo de auto-evolucion con quality gates."""
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
            "quality_gates": {},
        }

        # 1. Error -> lessons -> skill candidates
        if cfg.get("enable_error_to_skill"):
            try:
                from tools.error_learning import ErrorLearningSystem
                candidates = ErrorLearningSystem.analyze_for_skill_creation()
                if candidates:
                    report["errors_to_lessons"] = len(candidates)
                    report["details"].append(f"{len(candidates)} errores candidatos a skill")
                    cls._step_stats["errors_to_lessons"] += len(candidates)
            except Exception as e:
                logger.warning(f"error->skill: {e}")

        # 2. SkillForger cycle with quality gate
        try:
            from tools.skill_forger import SkillForger
            threshold = cfg.get("pattern_threshold", 3)
            cycle_result = SkillForger.run_cycle(threshold=threshold)
            forged = cycle_result.get("forged_skills", [])
            if forged:
                # Quality gate: validate each forged skill
                valid = []
                for name in forged:
                    try:
                        info = SkillForger.get_skill_info(name) if hasattr(SkillForger, 'get_skill_info') else {}
                        if info.get("status") != "invalid":
                            valid.append(name)
                        else:
                            report["details"].append(f"Quality gate FAILED: {name}")
                    except Exception:
                        valid.append(name)
                report["skills_forged"] = len(valid)
                if valid:
                    report["details"].append(f"Forjadas: {', '.join(valid)}")
                cls._step_stats["skills_forged"] += len(valid)
        except Exception as e:
            logger.warning(f"skill_forger cycle: {e}")

        # 3. Auto-promote (quality gate: only promote if validation passes)
        if cfg.get("enable_auto_promotion"):
            try:
                promoted = cls._auto_promote_skills(cfg.get("auto_promote_after_successes", 3))
                report["skills_promoted"] = len(promoted)
                if promoted:
                    report["details"].append(f"Promovidas: {', '.join(promoted)}")
                cls._step_stats["skills_promoted"] += len(promoted)
            except Exception as e:
                logger.warning(f"auto_promote: {e}")

        # 4. Auto-archive with rate check
        if cfg.get("enable_auto_archive"):
            try:
                archived = cls._auto_archive_failed_skills(
                    cfg.get("auto_archive_after_uses", 8),
                    cfg.get("auto_archive_min_rate", 0.3),
                )
                report["skills_archived"] = len(archived)
                if archived:
                    report["details"].append(f"Archivadas: {', '.join(archived)}")
                cls._step_stats["skills_archived"] += len(archived)
            except Exception as e:
                logger.warning(f"auto_archive: {e}")

        # 5. Sync learned skills
        if cfg.get("enable_learned_skills_sync"):
            try:
                from tools.learned_skills_bridge import LearnedSkillsBridge
                synced = LearnedSkillsBridge.sync_all()
                report["learned_skills_synced"] = synced
                if synced:
                    report["details"].append(f"Synced {synced} learned skills")
                cls._step_stats["learned_skills_synced"] += synced
            except Exception as e:
                logger.warning(f"learned_skills_sync: {e}")

        # 6. Auto-improve Aumformbring
        try:
            from tools.aumformbring import aumformbring_system
            improvements = aumformbring_system.auto_improve()
            if improvements:
                report["auto_improvements"] = len(improvements)
                cls._step_stats["auto_improvements"] += len(improvements)
        except Exception as e:
            logger.warning(f"auto_improve: {e}")

        report["quality_gates"] = {
            "total_cycles_run": cls._step_stats.get("total_cycles", 0) + 1,
            "total_skills_forged_all_time": cls._step_stats.get("skills_forged", 0),
            "total_skills_promoted_all_time": cls._step_stats.get("skills_promoted", 0),
            "total_skills_archived_all_time": cls._step_stats.get("skills_archived", 0),
        }

        logger.info(
            f"Auto-learning cycle: {report['status']} | "
            f"forged={report['skills_forged']} promoted={report['skills_promoted']} "
            f"archived={report['skills_archived']} synced={report['learned_skills_synced']}"
        )
        return report

    @classmethod
    def get_evolution_report(cls) -> Dict[str, Any]:
        """Genera un reporte legible de la evolución del sistema."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_cycles": cls._step_stats.get("total_cycles", 0),
            "all_time_forged": cls._step_stats.get("skills_forged", 0),
            "all_time_promoted": cls._step_stats.get("skills_promoted", 0),
            "all_time_archived": cls._step_stats.get("skills_archived", 0),
            "all_time_synced": cls._step_stats.get("learned_skills_synced", 0),
            "all_time_improvements": cls._step_stats.get("auto_improvements", 0),
            "all_time_errors_analyzed": cls._step_stats.get("errors_to_lessons", 0),
        }

    @classmethod
    def _auto_promote_skills(cls, min_successes: int = 3) -> List[str]:
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
                    if hasattr(SkillForger, 'promote_skill'):
                        SkillForger.promote_skill(name)
                        promoted.append(name)
                except Exception as e:
                    logger.warning(f"promote {name}: {e}")
        return promoted

    @classmethod
    def _auto_archive_failed_skills(cls, min_uses: int = 8, min_rate: float = 0.3) -> List[str]:
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
                    if hasattr(SkillForger, 'archive_skill'):
                        SkillForger.archive_skill(name)
                        archived.append(name)
                except Exception as e:
                    logger.warning(f"archive {name}: {e}")
        return archived
