"""
AUTOMYX VISION TOOLS
=====================
Le da al agente ojos reales: describe imágenes y capturas de pantalla usando
un modelo multimodal (NVIDIA NIM `minimaxai/minimax-m3`, gratis, ya configurado
en el .env) reforzado con OCR (Tesseract) para el texto que contenga la imagen.

El modelo de chat activo (ej. vyrex-qwen3.6-35b) NO recibe la imagen directamente
-- la API de Vyrex solo acepta "content" como string plano y rechaza payloads
multimodales -- así que estas tools hacen de "ojos": analizan la imagen con un
modelo con visión real y devuelven una descripción en texto que el modelo activo
usa para razonar y responder.
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
            "description": description,
        }
        ocr = _ocr_text(image_path)
        if ocr:
            result["text_detected"] = ocr
        return result

    @staticmethod
    def see_screen(question: str = "") -> Dict[str, Any]:
        """Toma una captura de la pantalla actual y la analiza con visión real."""
        if not _HAS_PIL:
            return {"ok": False, "error": "PIL no instalado. Ejecuta: pip install Pillow"}
        shot_dir = Path(os.path.expanduser("~")) / ".automyx"
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot_path = shot_dir / "last_screenshot.png"
        try:
            img = ImageGrab.grab()
            img.save(shot_path)
        except Exception as e:
            return {"ok": False, "error": f"No se pudo tomar la captura de pantalla: {e}"}
        return VisionTools.see_image(str(shot_path), question)
