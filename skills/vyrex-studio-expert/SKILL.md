---
name: vyrex-studio-expert
description: "Experto en producción de video profesional: cloud (Vyrex Studio, Gemini Veo 3.1) + local con VideoProTools (intro, promo, lower third, join con transiciones, slideshow, edición)."
---

# Vyrex Studio + Video Pro Expert (Producción Completa)

Esta habilidad cubre **dos modos de producción de video**:
1. **CLOUD** (Vyrex Studio, Gemini Veo 3.1) — generación desde cero con IA.
2. **LOCAL** (`VideoProTools` con ffmpeg) — edición, composición y post-producción con control total.

Vyrex Studio y Gemini Veo 3.1 son herramientas DISTINTAS. Para crear videos con Gemini/Veo 3.1 usa EXCLUSIVAMENTE `generate_gemini_video`. Para producción local con efectos cinematográficos usa `VideoProTools`.

---

## PARTE 1: Generación CLOUD (Vyrex Studio + Gemini)

### Vyrex Studio (`generate_vyrex_video`)
- Genera video renderizado por IA generativa en la nube (no Blender, no local).
- Excelente para: videos abstractos, cinemáticos, cortos de redes sociales.

**Conocimiento de la interfaz de Vyrex:**
- Izquierda (0-20%): menú lateral (Generator, YouTube Metrics, AI Premium Video, Image Generator, Vyrex Music 1.5, VyrexScriber, Vyrex Clonation 2.0).
- Centro (20-60%): caja gigante de "Prompt / Guion" en X: 50%, Y: 30%. Estilos visuales: Cinematic, Cyberpunk, Anime, Pixar 3D, Photorealistic, Dark Horror, Comic Book, Vaporwave, Watercolor. Voz narrador (Dalia México, etc.), formato (9:16 / 16:9 / 1:1), subtítulos (Static/Pop Up/Fade In), ritmo de edición (Cine/Viral/Mix Pro/Experto).
- Derecha (60-100%): panel de Preview, botón "Generar Video" verde/naranja en X: 85%, Y: 90% (costo: 10 créditos).

**Uso recomendado:**
1. Analiza lo que pide el usuario. Si solo da un tema (ej. "video sobre el espacio"), TÚ redactas un prompt GIGANTE, creativo y muy detallado (descripciones visuales, tono del narrador, planos de cámara, música).
2. Devuelve JSON con `action: "generate_vyrex_video"` y `prompt: "<guion>"`, `style: "Cinematic"`.
3. Estilos permitidos: Cinematic, Cyberpunk, Anime, Pixar 3D, Photorealistic, Dark Horror.
4. NUNCA respondas solo con texto. Tu respuesta DEBE incluir el JSON de la herramienta.

### Gemini Veo 3.1 (`generate_gemini_video`)
- También genera video por IA generativa en la nube, con tecnología Veo de Google.
- Diferencias con Vyrex: prompts más cortos, mejor para videos realistas, soporta audio nativo.
- **Cuándo usar Gemini en vez de Vyrex**: cuando el usuario pida explícitamente "Gemini", "Veo", "Veo 3.1", o cuando pida video realista/fotorrealista.

---

## PARTE 2: Producción LOCAL con `VideoProTools` (BESTIA)

La clase `VideoProTools` en `tools/video_pro_tools.py` (basada en ffmpeg + matplotlib) ofrece control TOTAL sobre la post-producción.

### 2.1 Generadores BESTIA (5 funciones estrella)

#### `video_intro` — Intro animada (5 estilos)
- **Estilos**: modern, cinematic, glitch, neon, minimal.
- Genera frames con matplotlib y los une con ffmpeg en un MP4.
- Args: `output_path`, `title` (ej. "AUTOMYX"), `subtitle` (ej. "Producción 2026"), `style`, `duration_s` (default 5s), `music_path` (opcional).
- **Cuándo usar**: al inicio de cada video profesional, branding.

#### `video_promo` — Video promocional (3 estilos)
- **Estilos**: dynamic, elegante, energetic.
- Genera una secuencia de "bullets" con texto animado + CTA final.
- Args: `output_path`, `title`, `tagline`, `cta` (call-to-action), `style`, `bullets` (lista de 3-5 puntos clave), `duration_s`.
- **Cuándo usar**: para pitches de 30-60s, anuncios cortos en redes.

#### `video_lower_third` — Banner animado sobre video
- Overlay de nombre + cargo sobre un video existente.
- Aparece y desaparece con animación (slide-in desde izquierda, fade-out).
- Args: `input_path`, `output_path`, `name` (ej. "Juan Pérez"), `title` (ej. "CEO de ACME"), `position` (bottom-left por defecto), `duration_s` (cuánto tiempo visible), `font_color`, `bg_color`.
- **Cuándo usar**: entrevistas, tutoriales, webinars, documentales.

#### `video_join_with_transitions` — Unir múltiples clips con transiciones
- **8 transiciones disponibles**: fade, slide-left, slide-right, slide-up, zoom, blur, glitch, swirl.
- Une N videos con la transición elegida entre cada par.
- Opcionalmente añade `intro_path` al principio y `outro_path` al final.
- Normaliza audio al final (loudnorm a -14 LUFS para YouTube).
- Args: `video_paths` (lista), `output_path`, `transition`, `transition_duration` (default 0.5s), `intro_path` (opcional), `outro_path` (opcional), `normalize_audio` (bool).
- **Cuándo usar**: edición de vlogs, mashups, reels multi-clip.

#### `video_slideshow` — Slideshow desde imágenes
- Convierte una carpeta de imágenes en un video con transiciones.
- Transición por defecto: fade. Configurable.
- Música de fondo opcional.
- Args: `image_paths` (lista), `output_path`, `duration_per_image` (default 3s), `transition`, `music_path`, `image_resize` (1920x1080 por defecto), `fps` (30).
- **Cuándo usar**: portafolios, recaps de eventos, presentaciones visuales.

### 2.2 Utilidades de edición (20 funciones)

- `video_probe(input_path)`: muestra metadatos (duración, resolución, fps, bitrate, códec).
- `video_convert(input, output, **kwargs)`: convierte entre formatos (mp4, mov, webm, mkv, avi).
- `video_thumbnail(input, output, time_s, width)`: extrae un frame a un PNG.
- `video_thumbnail_grid(input, output, cols, rows)`: grid de N frames para preview visual.
- `video_trim(input, output, start_s, end_s)`: recorta sin re-encoding (`-c copy`, ultra rápido).
- `video_export_for_platform(input, output, platform)`: presets TikTok/YouTube/Reels/Shorts.
- `video_concat(video_paths, output, transitions)`: concatena sin transiciones (rápido).
- `video_detect_scenes(input, threshold)`: detecta cambios de escena con PySceneDetect.
- `video_make_gif(input, output, start_s, duration_s, fps, width)`: crea GIF.
- `video_add_watermark(input, image, output, position, opacity, scale)`: logo/PNG overlay.
- `video_normalize_audio(input, output, target_lufs)`: loudnorm a -14 LUFS (YouTube).
- `video_extract_audio(input, output, format, bitrate)`: extrae a MP3/WAV/AAC.
- `video_remove_audio(input, output)`: elimina pista de audio.
- `video_slow_motion(input, output, speed)`: cámara lenta (0.5x por defecto).
- `video_time_lapse(input, output, speed)`: time-lapse (4x por defecto).
- `video_reverse(input, output)`: invierte video y audio.
- `video_picture_in_picture(main, overlay, output, position)`: PIP (B-roll en esquina).
- `video_side_by_side(left, right, output)`: divide pantalla L/R.
- `video_quality(reference, distorted)`: PSNR + SSIM para comparar calidad.
- `video_status()`: health-check de ffmpeg, ffprobe, matplotlib.

## Workflow de producción híbrido

### Paso 1: Decide cloud vs local
- **Cloud (Vyrex/Gemini)**: si el usuario quiere un video generado desde cero con IA y no tiene material base.
- **Local (VideoProTools)**: si tiene material (videos, imágenes) o quiere post-producción profesional.
- **Híbrido**: genera intro/promo en LOCAL, únelas a un video cloud con `video_join_with_transitions`.

### Paso 2: Para cloud, redacta el prompt adecuado
- Vyrex: prompt LARGO (200+ palabras), cinematográfico, con detalles visuales.
- Gemini: prompt CORTO y descriptivo, sin rodeos.

### Paso 3: Para local, planifica la edición
1. **Probe** cada video: `video_probe()`.
2. **Recorta** lo mejor: `video_trim()`.
3. **Normaliza audio**: `video_normalize_audio()`.
4. **Genera intro/promo** con `video_intro` o `video_promo`.
5. **Une con transiciones**: `video_join_with_transitions()`.
6. **Exporta para plataforma**: `video_export_for_platform()` (TikTok = 9:16 1080x1920, YouTube = 16:9 1920x1080).

### Paso 4: Verifica el output
- `video_probe()` del output para confirmar duración, resolución, códec.
- `video_thumbnail_grid()` para preview visual de los frames clave.
- `video_quality(reference, output)` para comparar con el original.

## Reglas de oro

- **Vyrex para creativos, Gemini para realistas, VideoProTools para edición**.
- **NO confundas Vyrex/Gemini con Blender**: Blender = geometría 3D real (ThreeDTools); Vyrex/Gemini = video AI generativo.
- **Usa `video_normalize_audio` SIEMPRE** antes de subir a YouTube (target -14 LUFS).
- **Resuelve rutas absolutas** con `task_coord_resolve_path` antes de operar.
- **Si el output es > 500 MB, exporta a H.264 con CRF 23** (`video_convert` con `crf=23`).
- **Para TikTok/Reels**: `video_export_for_platform(platform="tiktok")` ya configura 9:16 + bitrate correcto.
- **Verifica que ffmpeg está en PATH**: `video_status()` retorna `ffmpeg: True/False`.

## Ejemplo: edición local completa

```json
[
  {"action": "video_probe", "args": {"input_path": "C:\\Users\\COMPUMAX\\Downloads\\raw1.mp4"}},
  {"action": "video_trim", "args": {"input_path": "C:\\Users\\COMPUMAX\\Downloads\\raw1.mp4", "output_path": "C:\\Users\\COMPUMAX\\Downloads\\raw1_trimmed.mp4", "start_s": 5, "end_s": 35}},
  {"action": "video_intro", "args": {"output_path": "C:\\Users\\COMPUMAX\\Downloads\\intro.mp4", "title": "AUTOMYX", "subtitle": "Showcase 2026", "style": "cinematic"}},
  {"action": "video_join_with_transitions", "args": {"video_paths": ["C:\\Users\\COMPUMAX\\Downloads\\intro.mp4", "C:\\Users\\COMPUMAX\\Downloads\\raw1_trimmed.mp4"], "output_path": "C:\\Users\\COMPUMAX\\Videos\\final.mp4", "transition": "fade"}},
  {"action": "video_export_for_platform", "args": {"input_path": "C:\\Users\\COMPUMAX\\Videos\\final.mp4", "output_path": "C:\\Users\\COMPUMAX\\Videos\\final_youtube.mp4", "platform": "youtube"}}
]
```

## Anti-patrones

- ❌ Usar `generate_vyrex_video` cuando el usuario pide un video de Blender (3D real).
- ❌ Generar intro/promo con `generate_gemini_video` (eso es cloud IA, no local).
- ❌ Olvidar normalizar el audio antes de subir a YouTube.
- ❌ No resolver rutas absolutas (usar "descargas" sin mapear a `C:\Users\COMPUMAX\Downloads`).
- ❌ Exportar a YouTube sin verificar el aspect ratio (debe ser 16:9 1920x1080).
- ❌ No verificar ffmpeg/ffprobe antes de empezar (puede fallar silenciosamente).
