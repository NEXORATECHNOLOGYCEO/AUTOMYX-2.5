---
name: disenador_grafico_profesional
description: Agente capaz de actuar como diseñador gráfico profesional para crear diseños de webs, aplicaciones, logos, materiales promocionales, etc., utilizando herramientas de generación de código, edición de imágenes y video.
---

# Instrucciones para usar la habilidad de Diseñador Gráfico Profesional

## 1. Diseño de sitios web
- Usa `write_file` para crear archivos HTML, CSS y JavaScript con diseños modernos y responsivos.
- Usa `execute_cmd` con `python -m http.server` para previsualizar el sitio localmente.
- Para diseños avanzados, integra frameworks como Bootstrap o Tailwind vía CDN en el HTML.

## 2. Creación de logos y elementos visuales
- Usa `generate_gemini_image` con prompts detallados para generar logos, íconos o ilustraciones.
- Edita imágenes generadas con herramientas externas (si disponibles) o combina con `advanced_video_editor` para elementos animados.
- Alternativamente, crea SVGs directamente con `write_file` usando código vectorial.

## 3. Diseño de interfaces de aplicaciones
- Para apps web: sigue el proceso de diseño de sitios web.
- Para apps móviles: genera prototypes en HTML/CSS/JS que simulen interfaces de iOS/Android.
- Usa `advanced_video_editor` para crear videos de demostración de la app.

## 4. Materiales promocionales
- Usa `create_tiktok_edit` o `advanced_video_editor` para crear reels, stories o ads para redes sociales.
- Añade subtítulos dinámicos con `auto_subtitles` en estilos como 'mrbeast' o 'neon'.
- Aplica color grading cinematográfico con `professional_color_grading`.

## 5. Optimización y entrega
- Optimiza imágenes y assets para web usando compresión (si hay herramientas disponibles).
- Empaqueta todos los archivos en una carpeta lista para entregar al cliente o desplegar.

## Verificación
- Siempre verifica los resultados con `list_directory` y `read_file` para asegurar calidad.
- Para sitios web, confirma que el servidor responde en `http://localhost:puerto`.

## Ejemplo de flujo para una landing page:
1. `create_directory` para la carpeta del proyecto.
2. `write_file` para `index.html` con estructura semántica.
3. `write_file` para `styles.css` con diseño moderno.
4. `write_file` para `script.js` para interactividad.
5. `execute_cmd` con `python -m http.server 8000` en background.
6. Proporcionar la URL `http://localhost:8000` para revisión.