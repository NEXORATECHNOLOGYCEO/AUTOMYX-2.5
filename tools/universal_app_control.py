"""
Automyx - Universal App Control
Habilidad única para controlar cualquier aplicación de escritorio
Inspirado en la filosofía de NemoClaw pero adaptado a Automyx
"""
import os
import sys
import time
import subprocess
from typing import Optional, List, Dict, Any

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import win32gui
    import win32con
    WINDOWS_UI_AVAILABLE = True
except ImportError:
    WINDOWS_UI_AVAILABLE = False


class UniversalAppControl:
    """Clase para control universal de aplicaciones de escritorio"""

    @staticmethod
    def get_open_windows() -> List[Dict[str, Any]]:
        """Obtiene todas las ventanas abiertas"""
        if not WINDOWS_UI_AVAILABLE:
            return [{"error": "Esta función solo está disponible en Windows"}]

        windows = []

        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "left": rect[0],
                        "top": rect[1],
                        "right": rect[2],
                        "bottom": rect[3],
                        "width": rect[2] - rect[0],
                        "height": rect[3] - rect[1]
                    })
            return True

        win32gui.EnumWindows(enum_windows_callback, None)
        return windows

    @staticmethod
    def activate_window(title: str, exact: bool = False) -> str:
        """Activa una ventana por su título"""
        if not WINDOWS_UI_AVAILABLE:
            return "Error: Esta función solo está disponible en Windows"

        def enum_windows_callback(hwnd, _):
            window_title = win32gui.GetWindowText(hwnd)
            if exact:
                match = window_title == title
            else:
                match = title.lower() in window_title.lower()

            if match and win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return False
            return True

        win32gui.EnumWindows(enum_windows_callback, None)
        return f"Ventana '{title}' activada"

    @staticmethod
    def move_window(title: str, x: int, y: int, width: int = None, height: int = None) -> str:
        """Mueve y/o redimensiona una ventana"""
        if not WINDOWS_UI_AVAILABLE:
            return "Error: Esta función solo está disponible en Windows"

        hwnd = None

        def enum_windows_callback(h, _):
            nonlocal hwnd
            window_title = win32gui.GetWindowText(h)
            if title.lower() in window_title.lower() and win32gui.IsWindowVisible(h):
                hwnd = h
                return False
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            w = width if width else rect[2] - rect[0]
            h = height if height else rect[3] - rect[1]
            win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER)
            return f"Ventana '{title}' movida/redimensionada"
        return f"Ventana '{title}' no encontrada"

    @staticmethod
    def close_window(title: str) -> str:
        """Cierra una ventana"""
        if not WINDOWS_UI_AVAILABLE:
            return "Error: Esta función solo está disponible en Windows"

        hwnd = None

        def enum_windows_callback(h, _):
            nonlocal hwnd
            window_title = win32gui.GetWindowText(h)
            if title.lower() in window_title.lower() and win32gui.IsWindowVisible(h):
                hwnd = h
                return False
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return f"Ventana '{title}' cerrada"
        return f"Ventana '{title}' no encontrada"

    @staticmethod
    def minimize_window(title: str) -> str:
        """Minimiza una ventana"""
        if not WINDOWS_UI_AVAILABLE:
            return "Error: Esta función solo está disponible en Windows"

        hwnd = None

        def enum_windows_callback(h, _):
            nonlocal hwnd
            window_title = win32gui.GetWindowText(h)
            if title.lower() in window_title.lower() and win32gui.IsWindowVisible(h):
                hwnd = h
                return False
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return f"Ventana '{title}' minimizada"
        return f"Ventana '{title}' no encontrada"

    @staticmethod
    def maximize_window(title: str) -> str:
        """Maximiza una ventana"""
        if not WINDOWS_UI_AVAILABLE:
            return "Error: Esta función solo está disponible en Windows"

        hwnd = None

        def enum_windows_callback(h, _):
            nonlocal hwnd
            window_title = win32gui.GetWindowText(h)
            if title.lower() in window_title.lower() and win32gui.IsWindowVisible(h):
                hwnd = h
                return False
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return f"Ventana '{title}' maximizada"
        return f"Ventana '{title}' no encontrada"

    @staticmethod
    def ui_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        """Hace clic en coordenadas específicas"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado. Instálalo con: pip install pyautogui"

        pyautogui.click(x, y, clicks=clicks, button=button)
        return f"Clic en ({x}, {y}) realizado"

    @staticmethod
    def ui_move(x: int, y: int) -> str:
        """Mueve el cursor a coordenadas específicas"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado. Instálalo con: pip install pyautogui"

        pyautogui.moveTo(x, y)
        return f"Cursor movido a ({x}, {y})"

    @staticmethod
    def ui_type(text: str, interval: float = 0.05) -> str:
        """Escribe texto con el teclado"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado. Instálalo con: pip install pyautogui"

        pyautogui.write(text, interval=interval)
        return f"Texto '{text}' escrito"

    @staticmethod
    def ui_press(key: str, presses: int = 1, interval: float = 0.1) -> str:
        """Presiona una tecla"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado. Instálalo con: pip install pyautogui"

        pyautogui.press(key, presses=presses, interval=interval)
        return f"Tecla '{key}' presionada {presses} veces"

    @staticmethod
    def ui_hotkey(*keys: str) -> str:
        """Presiona una combinación de teclas (hotkey)"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado. Instálalo con: pip install pyautogui"

        pyautogui.hotkey(*keys)
        return f"Combinación {'+'.join(keys)} presionada"

    @staticmethod
    def get_mouse_position() -> Dict[str, int]:
        """Obtiene la posición actual del cursor"""
        if not PYAUTOGUI_AVAILABLE:
            return {"error": "pyautogui no está instalado"}

        x, y = pyautogui.position()
        return {"x": x, "y": y}

    @staticmethod
    def get_screen_size() -> Dict[str, int]:
        """Obtiene el tamaño de la pantalla"""
        if not PYAUTOGUI_AVAILABLE:
            return {"error": "pyautogui no está instalado"}

        width, height = pyautogui.size()
        return {"width": width, "height": height}

    @staticmethod
    def screenshot_region(x: int, y: int, width: int, height: int, save_path: str = None) -> str:
        """Toma una captura de pantalla de una región específica"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado"

        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        if save_path:
            screenshot.save(save_path)
            return f"Captura guardada en {save_path}"
        return "Captura de región tomada"

    @staticmethod
    def find_image_on_screen(image_path: str, confidence: float = 0.9) -> Optional[Dict[str, int]]:
        """Busca una imagen en la pantalla y devuelve sus coordenadas"""
        if not PYAUTOGUI_AVAILABLE:
            return None

        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                return {
                    "x": location.left + location.width // 2,
                    "y": location.top + location.height // 2,
                    "left": location.left,
                    "top": location.top,
                    "width": location.width,
                    "height": location.height
                }
            return None
        except Exception:
            return None

    @staticmethod
    def click_image(image_path: str, confidence: float = 0.9) -> str:
        """Busca una imagen en la pantalla y hace clic en ella"""
        location = UniversalAppControl.find_image_on_screen(image_path, confidence)
        if location:
            pyautogui.click(location["x"], location["y"])
            return f"Imagen encontrada y clic en ({location['x']}, {location['y']})"
        return f"Imagen {image_path} no encontrada en la pantalla"

    @staticmethod
    def scroll(amount: int, direction: str = "down") -> str:
        """Desplaza la pantalla"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado"

        scroll_amount = amount if direction == "down" else -amount
        pyautogui.scroll(scroll_amount)
        return f"Scroll {direction} de {amount} unidades"

    @staticmethod
    def drag_to(x: int, y: int, duration: float = 0.5) -> str:
        """Arrastra el cursor desde su posición actual hasta (x, y)"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: pyautogui no está instalado"

        pyautogui.dragTo(x, y, duration=duration)
        return f"Arrastrado hasta ({x}, {y})"

    @staticmethod
    def automate_app_sequence(commands: List[Dict[str, Any]]) -> str:
        """
        Ejecuta una secuencia de comandos de automatización
        Ejemplo:
        [
            {"action": "activate_window", "title": "Bloc de notas"},
            {"action": "type", "text": "Hola desde Automyx!"},
            {"action": "hotkey", "keys": ["ctrl", "s"]}
        ]
        """
        results = []
        for cmd in commands:
            action = cmd.get("action")
            try:
                if action == "activate_window":
                    res = UniversalAppControl.activate_window(cmd.get("title", ""), cmd.get("exact", False))
                elif action == "type":
                    res = UniversalAppControl.ui_type(cmd.get("text", ""), cmd.get("interval", 0.05))
                elif action == "click":
                    res = UniversalAppControl.ui_click(cmd.get("x", 0), cmd.get("y", 0), cmd.get("button", "left"), cmd.get("clicks", 1))
                elif action == "press":
                    res = UniversalAppControl.ui_press(cmd.get("key", ""), cmd.get("presses", 1), cmd.get("interval", 0.1))
                elif action == "hotkey":
                    res = UniversalAppControl.ui_hotkey(*cmd.get("keys", []))
                elif action == "move":
                    res = UniversalAppControl.ui_move(cmd.get("x", 0), cmd.get("y", 0))
                elif action == "scroll":
                    res = UniversalAppControl.scroll(cmd.get("amount", 10), cmd.get("direction", "down"))
                elif action == "wait":
                    time.sleep(cmd.get("seconds", 1))
                    res = f"Esperado {cmd.get('seconds', 1)} segundos"
                else:
                    res = f"Acción desconocida: {action}"
                results.append(res)
            except Exception as e:
                results.append(f"Error en {action}: {str(e)}")
        return "\n".join(results)
