---
name: auto-real-video-tiempo-20260712-ed60bd
description: "Skill auto-forjada por skill-forger. Tema: real video tiempo. Estado: experimental."
---
# auto-real-video-tiempo-20260712-ed60bd

**Estado:** EXPERIMENTAL (forjada automáticamente el 2026-07-12 11:55)
**Patrones detectados:** 19 conversaciones similares.
**Tema principal:** real video tiempo

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
1. Cuando el usuario mencione conceptos relacionados con: **real, video, tiempo, instrucción**, considera usar esta skill.
2. Sigue el patrón de respuesta del ejemplo, adaptando a los argumentos específicos.
3. Si la ejecución falla, registra el error en `forger_track_skill_usage` con `success=false` para que la skill se degrade.

## Promoción
Esta skill saldrá de estado experimental tras 3 usos exitosos consecutivos.
