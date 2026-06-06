from playwright.sync_api import sync_playwright
import webbrowser
import pywhatkit
import pyautogui
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
import pyperclip

class WebTools:
    @staticmethod
    def web_search(query: str) -> str:
        """Busca en Google usando el navegador predeterminado y devuelve un mensaje de confirmación."""
        try:
            # En lugar de usar Playwright oculto que puede fallar por bloqueos de Google,
            # abrimos la búsqueda en el navegador real del usuario, lo que es más espectacular visualmente.
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            webbrowser.open(url)
            return f"✅ Búsqueda web abierta en tu navegador: '{query}'"
        except Exception as e:
            # Plan B: Intentar con DuckDuckGo si Google falla
            try:
                import requests
                from bs4 import BeautifulSoup
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                res = requests.get(f'https://html.duckduckgo.com/html/?q={query}', headers=headers)
                soup = BeautifulSoup(res.text, 'html.parser')
                results = []
                for a in soup.find_all('a', class_='result__snippet'):
                    results.append(a.text)
                return "Resultados de búsqueda:\n" + "\n".join(results[:5])
            except Exception as e2:
                return f"❌ Error en búsqueda web: {str(e)} / {str(e2)}"

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
    def open_website(url: str) -> str:
        """Abre una URL específica en el navegador (ej: https://chatgpt.com)."""
        try:
            if not url.startswith('http'):
                url = 'https://' + url
            webbrowser.open(url)
            return f"✅ Abriendo {url} en tu navegador."
        except Exception as e:
            return f"❌ Error abriendo la web: {str(e)}"
    
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
