import webbrowser
import time
import urllib.parse
import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    import pywhatkit
except ImportError:
    pywhatkit = None

_DDG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}

class WebTools:
    @staticmethod
    def web_search(query: str, num_results: int = 8) -> str:
        """Busca en internet y devuelve resultados reales con títulos, URLs y fragmentos."""
        import os, json, time

        # ── 1. Brave Search API (si hay key) ──────────────────────────────
        brave_key = os.environ.get("BRAVE_API_KEY", "").strip()
        if brave_key:
            try:
                resp = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": brave_key,
                    },
                    params={"q": query, "count": num_results, "freshness": "month"},
                    timeout=12,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    hits = data.get("web", {}).get("results", [])
                    if hits:
                        lines = [f"[Brave Search] '{query}'\n"]
                        for h in hits[:num_results]:
                            title = h.get("title", "")
                            url   = h.get("url", "")
                            desc  = h.get("description", "")
                            lines.append(f"• {title}\n  {url}\n  {desc}\n")
                        return "\n".join(lines)
            except Exception:
                pass

        # ── 2. DuckDuckGo JSON (sin key) ──────────────────────────────────
        try:
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1",
                        "skip_disambig": "1", "no_redirect": "1"},
                headers=_DDG_HEADERS,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText", "")
                abstract_url = data.get("AbstractURL", "")
                related = data.get("RelatedTopics", [])
                lines = [f"[DuckDuckGo Instant] '{query}'\n"]
                if abstract:
                    lines.append(f"Resumen: {abstract}\nFuente: {abstract_url}\n")
                for item in related[:6]:
                    if isinstance(item, dict) and item.get("Text"):
                        url = item.get("FirstURL", "")
                        lines.append(f"• {item['Text'][:200]}\n  {url}\n")
                if len(lines) > 1:
                    return "\n".join(lines)
        except Exception:
            pass

        # ── 3. DuckDuckGo HTML scraping ───────────────────────────────────
        try:
            resp = requests.get(
                f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}",
                headers=_DDG_HEADERS,
                timeout=12,
            )
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for r in soup.select(".result")[:num_results]:
                    title_el = r.select_one(".result__title a")
                    snip_el  = r.select_one(".result__snippet")
                    url_el   = r.select_one(".result__url")
                    if title_el:
                        title = title_el.get_text(strip=True)
                        url   = url_el.get_text(strip=True) if url_el else ""
                        snip  = snip_el.get_text(strip=True) if snip_el else ""
                        results.append(f"• {title}\n  {url}\n  {snip}")
                if results:
                    return f"[DuckDuckGo] '{query}'\n\n" + "\n\n".join(results)
        except Exception:
            pass

        # ── 4. Último fallback: abrir navegador + mensaje claro ───────────
        try:
            webbrowser.open(f"https://duckduckgo.com/?q={urllib.parse.quote_plus(query)}")
        except Exception:
            pass
        return (
            f"⚠️ No se pudo obtener resultados programáticos para: '{query}'. "
            f"Se abrió el navegador. Verifica BRAVE_API_KEY para búsquedas confiables."
        )

    @staticmethod
    def play_youtube_video(query: str) -> str:
        """Abre el navegador por defecto del usuario, busca en YouTube y reproduce el primer video de forma garantizada."""
        try:
            import pywhatkit
            # pywhatkit.playonyt usa la API de búsqueda interna para encontrar el video más relevante
            # y abre directamente la URL del reproductor de YouTube, evitando clics fantasma o páginas de búsqueda.
            pywhatkit.playonyt(query)
            return f"🎵✅ Reproduciendo '{query}' directamente en YouTube. (Usando PyWhatKit para máxima precisión)."
        except Exception as e:
            # Fallback seguro: Si pywhatkit falla, construimos la URL de búsqueda y la abrimos.
            try:
                search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                webbrowser.open(search_url)
                return f"⚠️ pywhatkit falló. Abriendo los resultados de búsqueda de YouTube para '{query}' en tu navegador."
            except Exception as e2:
                return f"❌ Error intentando reproducir en YouTube: {str(e)} | {str(e2)}"
            
    @staticmethod
    def open_website(url: str, just_open: bool = False) -> str:
        """Abre una URL y devuelve el contenido de texto de la página.
        Si just_open=True, solo abre el navegador sin raspar contenido."""
        if not url.startswith("http"):
            url = "https://" + url

        if just_open:
            try:
                webbrowser.open(url)
            except Exception:
                pass
            return f"✅ Abriendo {url} en el navegador."

        # Intentar raspar el contenido con requests + BeautifulSoup
        try:
            resp = requests.get(url, headers=_DDG_HEADERS, timeout=15)
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header",
                              "aside", "form", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # Compactar líneas vacías
            lines = [l for l in text.splitlines() if l.strip()]
            content = "\n".join(lines[:300])
            if len(lines) > 300:
                content += f"\n... [{len(lines) - 300} líneas más]"
            return f"📄 Contenido de {url}:\n\n{content}"
        except Exception as e_req:
            # Fallback: Playwright headless si está disponible
            try:
                from playwright.sync_api import sync_playwright
                from bs4 import BeautifulSoup
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, timeout=20000, wait_until="domcontentloaded")
                    html = page.content()
                    browser.close()
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                lines = [l for l in text.splitlines() if l.strip()]
                content = "\n".join(lines[:300])
                return f"📄 Contenido (Playwright) de {url}:\n\n{content}"
            except Exception as e_pw:
                # Último fallback: abrir en navegador
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
                return f"⚠️ No se pudo raspar {url}: {e_req}. Se abrió en el navegador."
    
    @staticmethod
    def get_current_browser_url() -> str:
        """Intenta obtener la URL de la pestaña activa del navegador usando atajos de teclado (Ctrl+L, Ctrl+C)."""
        try:
            import pyperclip
            import pyautogui
            import time
            
            # Guardar contenido anterior del portapapeles
            old_clipboard = pyperclip.paste()
            
            # Simular Ctrl+L (seleccionar barra de direcciones) y Ctrl+C (copiar)
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.2)
            pyautogui.press('esc') # Quitar selección
            
            url = pyperclip.paste()
            
            # Restaurar portapapeles
            pyperclip.copy(old_clipboard)
            
            if url.startswith('http'):
                return f"URL obtenida: {url}"
            else:
                return "No se pudo obtener una URL válida. ¿Está el navegador activo?"
        except Exception as e:
            return f"❌ Error intentando obtener la URL: {str(e)}"

    @staticmethod
    def _get_proxy_config():
        import json
        import os
        try:
            if os.path.exists("credentials.json"):
                with open("credentials.json", "r") as f:
                    creds = json.load(f)
                    proxy_url = creds.get("global_proxy")
                    if proxy_url:
                        return {"server": proxy_url}
        except:
            pass
        return None

    @staticmethod
    def deep_web_scrape(url: str, extract_selector: str = None) -> str:
        """
        [Nivel OpenClaw Avanzado]: Usa Playwright para navegar a una URL,
        esperar a que el JS cargue, y extraer el texto limpio o un selector específico.
        """
        try:
            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup

            if not url.startswith('http'):
                url = 'https://' + url

            with sync_playwright() as p:
                proxy = WebTools._get_proxy_config()
                browser = p.chromium.launch(headless=True, proxy=proxy)
                page = browser.new_page()
                page.goto(url, timeout=30000, wait_until="networkidle")
                
                if extract_selector:
                    # Extraer texto de un elemento específico
                    element = page.query_selector(extract_selector)
                    content = element.inner_text() if element else "Selector no encontrado."
                else:
                    # Extraer todo el body y limpiarlo con BeautifulSoup
                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Eliminar scripts y estilos para dejar solo texto legible
                    for script in soup(["script", "style", "nav", "footer"]):
                        script.decompose()
                        
                    content = soup.get_text(separator='\n', strip=True)
                
                browser.close()
                
                # Devolver un resumen (los LLMs tienen límite de contexto)
                return f"📄 Extracción web de {url}:\n{content[:2000]}...\n[Contenido truncado]"
        except ImportError:
            return "❌ Playwright no está instalado. Ejecuta 'pip install playwright bs4' y 'playwright install'."
        except Exception as e:
            return f"❌ Error en deep scraping: {str(e)}"

    @staticmethod
    def ai_form_filler(url: str, fields_data: dict) -> str:
        """
        Navega a una URL y llena un formulario automáticamente usando Playwright.
        fields_data debe ser un diccionario { "selector_css": "valor_a_escribir" }.
        """
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False) # Visible para que el usuario vea
                page = browser.new_page()
                page.goto(url)
                
                for selector, value in fields_data.items():
                    page.fill(selector, value)
                    time.sleep(0.5)
                
                return f"✅ Formulario llenado exitosamente en {url}. (La ventana se dejó abierta para enviar manual o revisión)."
        except Exception as e:
            return f"❌ Error llenando formulario: {str(e)}"
    
    @staticmethod
    def create_web_preview(html_content: str) -> str:
        """Crea o actualiza una página web (HTML/CSS/JS) para previsualizarla en la plataforma."""
        try:
            with open("preview.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            return "✅ Web generada con éxito. Dile al usuario que puede verla en la pestaña 'Web Preview' de la barra lateral."
        except Exception as e:
            return f"❌ Error creando la web: {str(e)}"
            
    @staticmethod
    def update_live_canvas(component_id: str, html_content: str) -> str:
        """
        [Característica inspirada en OpenClaw - A2UI]
        Actualiza o inyecta componentes visuales dinámicos directamente en el dashboard en tiempo real.
        El agente controla el 'Canvas' del usuario.
        """
        try:
            # En un entorno de producción real esto se enviaría vía WebSocket.
            # Aquí simulamos guardando el estado en un archivo que el frontend puede sondear.
            import json
            import os
            
            canvas_file = "canvas_state.json"
            state = {}
            if os.path.exists(canvas_file):
                with open(canvas_file, "r") as f:
                    state = json.load(f)
                    
            state[component_id] = html_content
            
            with open(canvas_file, "w") as f:
                json.dump(state, f)
                
            return f"🎨 Live Canvas actualizado: El componente '{component_id}' ha sido inyectado en la interfaz de usuario."
        except Exception as e:
            return f"❌ Error actualizando el Live Canvas: {str(e)}"

    @staticmethod
    def analyze_browser_screen() -> str:
        """
        Toma una captura de pantalla de la ventana activa (asumiendo que es el navegador) 
        y usa OCR para leer qué pestañas o contenido está viendo el usuario.
        """
        try:
            import pytesseract
            from PIL import ImageGrab
            
            # Tomar captura de la pantalla principal
            img = ImageGrab.grab()
            
            # Extraer texto con Tesseract
            text = pytesseract.image_to_string(img)
            
            # Limpiar un poco el texto para no saturar al LLM
            lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 3]
            summary = "\n".join(lines[:20]) # Solo las primeras 20 líneas relevantes
            
            return f"👁️ Veo lo siguiente en tu pantalla actual (posiblemente tu navegador):\n{summary}\n[...]"
        except Exception as e:
            return f"❌ Error intentando ver la pantalla: {str(e)}"
