---
name: skill-forger
description: "Forjador de habilidades. Detecta patrones repetidos en AUMFORMBRING y crea nuevas skills automáticamente (auto-evolución)."
---
# Skill Forger (Auto-Evolución Real)

**Descripción:** Esta habilidad le da a Automyx la capacidad de **CREAR SUS PROPIAS SKILLS** sin intervención del desarrollador. Detecta patrones repetidos en las conversaciones (vía AUMFORMBRING), generaliza la solución y genera un archivo SKILL.md nuevo, listo para reutilizar.

**Reglas de Ejecución:**
Cuando el usuario te pida "aprende de lo que hemos hecho", "crea una skill propia", "auto-evoluciona", "detecta lo que repito", o periódicamente cada N conversaciones:

1. **Análisis de Patrones:**
   - Usa `forger_analyze_patterns` para leer `aumformbring_data/learned_patterns.json` y detectar patrones con `usage_count >= 3` (umbral configurable).
   - Usa `forger_cluster_similar_requests` para agrupar peticiones similares semánticamente (no solo por palabras exactas).
   - Si encuentras un cluster con â‰¥ 3 ocurrencias y solución consistente, es candidato a forjar skill.

2. **Generación de Skill:**
   - Usa `forger_forge_skill` con `cluster_id` â†’ produce un SKILL.md con:
     - Frontmatter YAML (name auto-generado: `auto_<tema>_<timestamp>`, description sintetizada).
     - Descripción del patrón detectado.
     - Reglas de ejecución derivadas de las acciones exitosas pasadas.
     - Lista de tools utilizadas en la secuencia típica.
   - Guarda en `skills/<nombre-skill>/SKILL.md` (mismo formato que skills manuales).

3. **Validación y Promoción:**
   - Toda skill forjada nace en estado `experimental`. Para promoverla a `stable`:
     - Debe usarse exitosamente al menos 3 veces más sin errores (`forger_track_skill_usage`).
     - Pasa por `forger_validate_skill` (chequea que las tools mencionadas existan, sintaxis YAML, coherencia).
   - Usa `forger_promote_skill` cuando esté lista. Usa `forger_demote_skill` o `forger_archive_skill` si falla repetidamente.

4. **Catálogo y Evolución:**
   - Usa `forger_list_forged_skills` para ver todas las creadas, su estado y stats de uso.
   - Usa `forger_merge_skills` cuando dos skills experimentales sean redundantes.
   - Usa `forger_refine_skill` para refactorizar una skill existente con nuevas lecciones aprendidas.

5. **Auto-Ejecución Periódica:**
   - Usa `forger_run_cycle` para correr un ciclo completo de análisis + forja + validación.
   - Puede programarse con `schedule_task` (ej. cada 24h corre un ciclo).
   - El sistema mantiene un log en `nexus_data/forger_history.json`.

6. **Reglas de Seguridad:**
   - NUNCA forjes una skill que requiera credenciales hardcodeadas.
   - NUNCA dupliques una skill existente: usa `forger_check_duplicates` antes de crear.
   - Si una skill forjada provoca errores repetidos, archívala automáticamente.
   - Los nombres de skills deben ser kebab-case sin caracteres especiales.

**Â¡ESTA ES LA HABILIDAD MÃS PODEROSA! TE PERMITE EVOLUCIONAR SIN INTERVENCIÃ“N HUMANA. ComplementaÂ AUMFORMBRING.**
