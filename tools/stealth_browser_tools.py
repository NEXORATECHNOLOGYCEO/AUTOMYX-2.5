"""
Stealth Browser Tools - RPA indetectable con Playwright
Fingerprint spoofing, evasión de Cloudflare/reCAPTCHA/hCaptcha, proxies residenciales rotatorios.
"""
import os
import json
import random
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    import requests
except ImportError:
    requests = None


class StealthBrowserTools:
    """Operador RPA sigiloso con Playwright + stealth."""

    SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "sessions")
    AUDIT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data", "stealth_audit.log")
    _playwright = None
    _browser = None
    _context = None
    _page = None
    _proxy_pool: List[str] = []
    _proxy_index = 0

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]

    STEALTH_JS = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en-US', 'en']});
    window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app:{}};
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ? Promise.resolve({state: Notification.permission}) : originalQuery(parameters)
    );
    """

    @staticmethod
    def _audit(msg: str):
        os.makedirs(os.path.dirname(StealthBrowserTools.AUDIT_FILE), exist_ok=True)
        with open(StealthBrowserTools.AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")

    # ---------- BROWSER ----------
    @staticmethod
    def launch_browser(headless: bool = False, proxy_url: str = "", user_agent: str = "",
                        locale: str = "es-ES", timezone: str = "America/Argentina/Buenos_Aires",
                        viewport_w: int = 1366, viewport_h: int = 768) -> Dict[str, Any]:
        if sync_playwright is None:
            return {"error": "Falta instalar playwright (pip install playwright && playwright install chromium)"}
        try:
            StealthBrowserTools._playwright = sync_playwright().start()
            launch_args = ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
            launch_kwargs = {"headless": headless, "args": launch_args}
            if proxy_url:
                launch_kwargs["proxy"] = {"server": proxy_url}
            StealthBrowserTools._browser = StealthBrowserTools._playwright.chromium.launch(**launch_kwargs)
            ua = user_agent or random.choice(StealthBrowserTools.USER_AGENTS)
            StealthBrowserTools._context = StealthBrowserTools._browser.new_context(
                user_agent=ua, locale=locale, timezone_id=timezone,
                viewport={"width": viewport_w, "height": viewport_h},
                java_script_enabled=True,
            )
            StealthBrowserTools._context.add_init_script(StealthBrowserTools.STEALTH_JS)
            StealthBrowserTools._page = StealthBrowserTools._context.new_page()
            StealthBrowserTools._audit(f"Browser launched (headless={headless}, proxy={proxy_url or 'none'})")
            return {"launched": True, "user_agent": ua, "viewport": f"{viewport_w}x{viewport_h}"}
        except Exception as e:
            return {"error": f"No se pudo lanzar el navegador: {e}"}

    @staticmethod
    def goto(url: str, wait_until: str = "networkidle", timeout_ms: int = 30000) -> Dict[str, Any]:
        page = StealthBrowserTools._page
        if not page:
            return {"error": "Navegador no lanzado. Usa stealth_launch_browser primero."}
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            return {"url": page.url, "title": page.title()}
        except Exception as e:
            return {"error": f"Error navegando: {e}"}

    @staticmethod
    def human_click(selector: str, jitter: bool = True) -> Dict[str, Any]:
        page = StealthBrowserTools._page
        if not page:
            return {"error": "Navegador no lanzado"}
        try:
            el = page.locator(selector).first
            box = el.bounding_box()
            if box:
                x = box["x"] + box["width"] / 2 + (random.uniform(-5, 5) if jitter else 0)
                y = box["y"] + box["height"] / 2 + (random.uniform(-3, 3) if jitter else 0)
                page.mouse.move(x, y, steps=random.randint(15, 30))
                time.sleep(random.uniform(0.1, 0.3))
                page.mouse.click(x, y)
            else:
                el.click()
            return {"clicked": selector}
        except Exception as e:
            return {"error": f"Error click: {e}"}

    @staticmethod
    def human_type(selector: str, text: str, min_delay_ms: int = 50, max_delay_ms: int = 180) -> Dict[str, Any]:
        page = StealthBrowserTools._page
        if not page:
            return {"error": "Navegador no lanzado"}
        try:
            page.click(selector)
            for ch in text:
                page.keyboard.type(ch, delay=random.randint(min_delay_ms, max_delay_ms))
            return {"typed": len(text), "selector": selector}
        except Exception as e:
            return {"error": f"Error type: {e}"}

    @staticmethod
    def human_scroll(distance: int = 500, steps: int = 10) -> Dict[str, Any]:
        page = StealthBrowserTools._page
        if not page:
            return {"error": "Navegador no lanzado"}
        try:
            per_step = distance // steps
            for _ in range(steps):
                page.mouse.wheel(0, per_step)
                time.sleep(random.uniform(0.1, 0.4))
            return {"scrolled": distance}
        except Exception as e:
            return {"error": f"Error scroll: {e}"}

    # ---------- CAPTCHA ----------
    @staticmethod
    def solve_recaptcha_v2(site_key: str, page_url: str = "", api_key: str = "", provider: str = "2captcha") -> Dict[str, Any]:
        if requests is None:
            return {"error": "Falta requests"}
        if not api_key:
            api_key = os.getenv(f"{provider.upper()}_API_KEY", "")
        if not api_key:
            return {"error": f"Falta API key del provider {provider} (set {provider.upper()}_API_KEY env var)"}
        page = StealthBrowserTools._page
        page_url = page_url or (page.url if page else "")
        try:
            if provider == "2captcha":
                r = requests.post("http://2captcha.com/in.php", data={
                    "key": api_key, "method": "userrecaptcha", "googlekey": site_key,
                    "pageurl": page_url, "json": 1,
                }, timeout=30).json()
                if r.get("status") != 1:
                    return {"error": f"2captcha: {r.get('request')}"}
                cap_id = r["request"]
                for _ in range(60):
                    time.sleep(5)
                    res = requests.get("http://2captcha.com/res.php", params={
                        "key": api_key, "action": "get", "id": cap_id, "json": 1
                    }, timeout=15).json()
                    if res.get("status") == 1:
                        token = res["request"]
                        if page:
                            page.evaluate(f"document.getElementById('g-recaptcha-response').innerHTML = '{token}';")
                        return {"solved": True, "token": token[:30] + "..."}
                return {"error": "Timeout esperando solución"}
            return {"error": f"Provider '{provider}' no implementado"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def solve_cloudflare(max_wait_seconds: int = 30) -> Dict[str, Any]:
        page = StealthBrowserTools._page
        if not page:
            return {"error": "Navegador no lanzado"}
        try:
            start = time.time()
            while time.time() - start < max_wait_seconds:
                if "challenge" not in page.url.lower() and "cf_chl" not in page.content().lower():
                    return {"solved": True, "elapsed": round(time.time() - start, 1), "final_url": page.url}
                time.sleep(2)
            return {"solved": False, "reason": "timeout"}
        except Exception as e:
            return {"error": str(e)}

    # ---------- SESSIONS ----------
    @staticmethod
    def save_session(name: str) -> Dict[str, Any]:
        ctx = StealthBrowserTools._context
        if not ctx:
            return {"error": "No hay contexto activo"}
        os.makedirs(StealthBrowserTools.SESSIONS_DIR, exist_ok=True)
        path = os.path.join(StealthBrowserTools.SESSIONS_DIR, f"{name}.json")
        ctx.storage_state(path=path)
        return {"saved": path}

    @staticmethod
    def load_session(name: str) -> Dict[str, Any]:
        if not StealthBrowserTools._browser:
            return {"error": "Lanza el navegador primero"}
        path = os.path.join(StealthBrowserTools.SESSIONS_DIR, f"{name}.json")
        if not os.path.exists(path):
            return {"error": f"Sesión '{name}' no existe"}
        StealthBrowserTools._context = StealthBrowserTools._browser.new_context(storage_state=path)
        StealthBrowserTools._context.add_init_script(StealthBrowserTools.STEALTH_JS)
        StealthBrowserTools._page = StealthBrowserTools._context.new_page()
        return {"loaded": name, "path": path}

    # ---------- SCRAPING ----------
    @staticmethod
    def scrape_selector(selector: str, multiple: bool = True) -> Dict[str, Any]:
        page = StealthBrowserTools._page
        if not page:
            return {"error": "Navegador no lanzado"}
        try:
            if multiple:
                els = page.locator(selector).all()
                return {"count": len(els), "texts": [e.text_content() for e in els]}
            el = page.locator(selector).first
            return {"text": el.text_content(), "html": el.inner_html()}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def screenshot_full_page(output_path: str = None) -> Dict[str, Any]:
        page = StealthBrowserTools._page
        if not page:
            return {"error": "Navegador no lanzado"}
        out = output_path or os.path.join(os.path.expanduser("~"), "Downloads", f"stealth_{int(time.time())}.png")
        try:
            page.screenshot(path=out, full_page=True)
            return {"saved": out}
        except Exception as e:
            return {"error": str(e)}

    # ---------- PROXIES ----------
    @staticmethod
    def set_proxy_pool(proxies: List[str]) -> Dict[str, Any]:
        StealthBrowserTools._proxy_pool = proxies
        return {"pool_size": len(proxies)}

    @staticmethod
    def test_proxy(proxy_url: str) -> Dict[str, Any]:
        if requests is None:
            return {"error": "Falta requests"}
        try:
            t0 = time.time()
            r = requests.get("https://api.ipify.org?format=json",
                              proxies={"http": proxy_url, "https": proxy_url}, timeout=10)
            return {"ok": r.status_code == 200, "ip": r.json().get("ip"), "latency_ms": round((time.time() - t0) * 1000)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @staticmethod
    def rotate_fingerprint() -> Dict[str, Any]:
        if not StealthBrowserTools._browser:
            return {"error": "Lanza el navegador primero"}
        new_ua = random.choice(StealthBrowserTools.USER_AGENTS)
        new_viewport = random.choice([{"width": 1366, "height": 768}, {"width": 1920, "height": 1080}, {"width": 1440, "height": 900}])
        StealthBrowserTools._context = StealthBrowserTools._browser.new_context(user_agent=new_ua, viewport=new_viewport)
        StealthBrowserTools._context.add_init_script(StealthBrowserTools.STEALTH_JS)
        StealthBrowserTools._page = StealthBrowserTools._context.new_page()
        return {"rotated": True, "new_ua": new_ua, "viewport": new_viewport}

    @staticmethod
    def close_browser() -> Dict[str, Any]:
        try:
            if StealthBrowserTools._browser:
                StealthBrowserTools._browser.close()
            if StealthBrowserTools._playwright:
                StealthBrowserTools._playwright.stop()
            StealthBrowserTools._browser = None
            StealthBrowserTools._playwright = None
            return {"closed": True}
        except Exception as e:
            return {"error": str(e)}
