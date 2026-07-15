"""
AUTOMYX VISION TOOLS
=====================
Le da al agente ojos reales: describe imágenes y capturas de pantalla con la
visión NATIVA de Vyrex (qwen3-vl en las GPUs propias, vía vyrexstudio.com/v1)
y, si Vyrex no responde, cae a NVIDIA NIM `minimaxai/minimax-m3` como respaldo.
El OCR (Tesseract) refuerza el texto que contenga la imagen.
"""
from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any, Dict

try:
    from PIL import Image, ImageGrab
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

_VISION_MODEL = "minimaxai/minimax-m3"
_VYREX_URL = os.environ.get("VYREX_API_BASE", "https://vyrexstudio.com/v1") + "/chat/completions"
_MAX_SIDE = 1600
_DEFAULT_QUESTION = (
    "Describe detalladamente qué hay en esta imagen: objetos, texto visible, "
    "personas, colores y composición. Sé específico y concreto."
)


def _load_and_encode(image_path: str) -> Dict[str, Any]:
    if not _HAS_PIL:
        return {"ok": False, "error": "PIL no instalado. Ejecuta: pip install Pillow"}
    path = Path(image_path)
    if not path.exists():
        return {"ok": False, "error": f"No existe el archivo: {image_path}"}
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        return {"ok": False, "error": f"No se pudo abrir la imagen: {e}"}
    if max(img.size) > _MAX_SIDE:
        ratio = _MAX_SIDE / max(img.size)
        img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return {"ok": True, "b64": b64, "width": img.width, "height": img.height}


def _vyrex_describe(b64: str, prompt: str) -> str:
    import requests
    key = os.environ.get("VYREX_API_KEY", "")
    if not key:
        raise RuntimeError("sin VYREX_API_KEY")
    r = requests.post(_VYREX_URL, json={
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
        "max_tokens": 1024,
    }, headers={"Authorization": f"Bearer {key}"}, timeout=180)
    r.raise_for_status()
    out = (r.json()["choices"][0]["message"]["content"] or "").strip()
    if not out:
        raise RuntimeError("respuesta vacia del modelo de vision")
    return out


def _ocr_text(image_path: str) -> str:
    try:
        import pytesseract
        text = pytesseract.image_to_string(Image.open(image_path))
        return text.strip()
    except Exception:
        return ""


class VisionTools:
    @staticmethod
    def see_image(image_path: str, question: str = "") -> Dict[str, Any]:
        """Analiza una imagen (foto, screenshot, diseño, etc.) con un modelo de visión real."""
        enc = _load_and_encode(image_path)
        if not enc.get("ok"):
            return enc

        prompt = question.strip() or _DEFAULT_QUESTION

        engine = "vyrex-vision"
        try:
            description = _vyrex_describe(enc["b64"], prompt)
        except Exception:
            engine = "minimax"
            try:
                from core.agent import ModelProvider
                client = ModelProvider.get_client(_VISION_MODEL, provider="nvidia")
                resp = client.chat.completions.create(
                    model=_VISION_MODEL,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{enc['b64']}"}},
                        ],
                    }],
                    max_tokens=1024,
                    temperature=0.3,
                )
                description = (resp.choices[0].message.content or "").strip()
            except Exception as e:
                return {"ok": False, "error": f"No se pudo analizar la imagen con el modelo de visión: {e}"}

        result: Dict[str, Any] = {
            "ok": True,
            "path": image_path,
            "size": f"{enc['width']}x{enc['height']}",
            "engine": engine,
            "description": description,
        }
        ocr = _ocr_text(image_path)
        if ocr:
            # tope de 800 chars: el OCR de una pantalla completa infla el contexto
            # del LLM en miles de tokens por iteración
            result["text_detected"] = ocr[:800] + ("…" if len(ocr) > 800 else "")
        return result

    @staticmethod
    def see_screen(question: str = "", window_title: str = "") -> Dict[str, Any]:
        """Toma una captura de la pantalla actual y la analiza con visión real.
        window_title: si lo pasas (ej 'Chrome', 'Vyrex Studio'), esa ventana se trae
        al FRENTE antes de capturar — imprescindible para ver el navegador u otra
        app y no la terminal donde corre Automyx."""
        if not _HAS_PIL:
            return {"ok": False, "error": "PIL no instalado. Ejecuta: pip install Pillow"}
        if window_title:
            try:
                from tools.universal_app_control import UniversalAppControl
                UniversalAppControl.activate_window(window_title)
                import time as _t
                _t.sleep(0.7)
            except Exception:
                pass
        shot_dir = Path(os.path.expanduser("~")) / ".automyx"
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot_path = shot_dir / "last_screenshot.png"
        try:
            img = ImageGrab.grab()
            img.save(shot_path)
        except Exception as e:
            return {"ok": False, "error": f"No se pudo tomar la captura de pantalla: {e}"}
        return VisionTools.see_image(str(shot_path), question)
