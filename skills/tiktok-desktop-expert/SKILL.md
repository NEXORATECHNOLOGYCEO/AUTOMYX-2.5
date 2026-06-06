---
name: tiktok-desktop-expert
description: Experto en automatización y reproducción de videos/música en la aplicación nativa de TikTok para PC (Windows).
---

# TikTok Desktop Expert

Cuando el usuario use palabras clave como:
- "TikTok del computador"
- "TikTok del PC"
- "TikTok del ordenador"
- "TikTok de la computadora"
- "TikTok aplicación"

DEBES entender que se refiere a la **APLICACIÓN NATIVA INSTALADA EN WINDOWS**, NO a la página web en el navegador.

### REGLA DE ORO (CERO DESASTRES WEB):
TIENES ESTRICTAMENTE PROHIBIDO usar `open_website`, `web_search` o intentar buscar "TikTok" en Google Chrome, Edge o cualquier navegador. Hacer eso arruinará la automatización y causará un desastre en la interfaz.

**OBLIGATORIAMENTE debes usar la herramienta nativa:** `play_tiktok_desktop_video`

**Instrucciones de uso:**
1. Identifica el nombre del video o la canción que el usuario quiere (ej. "let me slowly").
2. OBLIGATORIAMENTE debes devolver un bloque JSON con la acción `play_tiktok_desktop_video` pasando ese nombre en el argumento `query`.
3. Esta macro está programada en bajo nivel para presionar la tecla Windows, abrir el programa oficial "TikTok", hacer scroll y clics precisos. Tú solo debes pasarle el nombre de la canción.
4. NUNCA respondas solo con texto. Tu respuesta DEBE incluir el JSON de la herramienta para que se ejecute la acción. Ejemplo:
```json
{
  "action": "play_tiktok_desktop_video",
  "args": {
    "query": "let me slowly"
  }
}
```
