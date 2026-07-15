---
name: auto-video-real-subtitulos-20260714
description: "Skill auto-forjada por skill-forger. Tema: video real subtitulos. Estado: experimental."
---
# auto-video-real-subtitulos-20260714

**Estado:** EXPERIMENTAL (forjada automáticamente el 2026-07-14 00:44)
**Patrones detectados:** 25 conversaciones similares.
**Tema principal:** video real subtitulos

## Trigger Típico
> pero en el video osea ya no tiene zoom pero los subtitulos no aparecen?

## Ejemplo de respuesta exitosa
He procesado el video **fabricio.mp4** sin aplicar ningún efecto de zoom y le he añadido subtítulos automáticos en español, centrados y de color amarillo, usando la plantilla de dos palabras estilo “mrbeast”.  

El archivo resultante se ha guardado en:

```
C:\Users\COMPUMAX\Downloads\fabricio_subti

## Tools usadas históricamente
- `execute_cmd`

## Reglas de ejecución derivadas
1. Cuando el usuario mencione conceptos relacionados con: **video, real, subtitulos, tiempo**, considera usar esta skill.
2. Sigue el patrón de respuesta del ejemplo, adaptando a los argumentos específicos.
3. Si la ejecución falla, registra el error en `forger_track_skill_usage` con `success=false` para que la skill se degrade.

## Promoción
Esta skill saldrá de estado experimental tras 3 usos exitosos consecutivos.
