from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Callable, Optional

try:
    from PIL import Image, ImageChops, ImageFilter, ImageGrab
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    import pytesseract
    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False

try:
    import mss
    _HAS_MSS = True
except ImportError:
    _HAS_MSS = False

_INSTANCE: Optional[VisionAgent] = None


def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _pil_to_base64(img) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class VisionAgent:
    def __init__(self, llm_runner: Optional[Callable[[list], str]] = None):
        self._llm = llm_runner

    def analyze_screenshot(self, image_path: str, question: Optional[str] = None) -> str:
        if not _HAS_PIL:
            return "PIL no instalado. Ejecuta: pip install Pillow"

        info = self.get_image_info(image_path)
        b64 = _image_to_base64(image_path)
        default_q = question or "Describe detalladamente lo que ves en esta imagen."

        if self._llm:
            try:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": default_q},
                        ],
                    }
                ]
                return self._llm(messages)
            except Exception:
                return (
                    f"Análisis técnico de imagen (sin visión LLM):\n"
                    f"- Dimensiones: {info['width']}x{info['height']}\n"
                    f"- Formato: {info['format']}\n"
                    f"- Tamaño: {info['size_kb']} KB\n"
                    f"- Modo de color: {info['mode']}"
                )
        return (
            f"Imagen analizada: {image_path}\n"
            f"Dimensiones: {info['width']}x{info['height']} | Formato: {info['format']} | Tamaño: {info['size_kb']} KB"
        )

    def detect_text_in_image(self, image_path: str) -> str:
        if not _HAS_PIL:
            return "PIL no instalado. Ejecuta: pip install Pillow"

        img = Image.open(image_path)
        img_gray = img.convert("L")
        img_sharpened = img_gray.filter(ImageFilter.SHARPEN)

        if _HAS_TESSERACT:
            try:
                text = pytesseract.image_to_string(img_sharpened)
                return text.strip() if text.strip() else "(No se detectó texto en la imagen)"
            except Exception as e:
                return f"Error en OCR: {e}"
        else:
            return (
                "pytesseract no está disponible. Para detectar texto en imágenes:\n"
                "1. pip install pytesseract\n"
                "2. Instala Tesseract OCR: https://github.com/tesseract-ocr/tesseract\n"
                f"Imagen cargada: {img.size[0]}x{img.size[1]} px"
            )

    def compare_images(self, image1_path: str, image2_path: str) -> dict:
        if not _HAS_PIL:
            return {"error": "PIL no instalado. Ejecuta: pip install Pillow"}

        img1 = Image.open(image1_path).convert("RGB")
        img2 = Image.open(image2_path).convert("RGB")

        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.LANCZOS)

        diff = ImageChops.difference(img1, img2)
        diff_data = list(diff.getdata())
        total_pixels = len(diff_data)

        changed_pixels = sum(1 for p in diff_data if any(c > 10 for c in p))
        similarity_pct = round((1 - changed_pixels / total_pixels) * 100, 2)

        diff_regions: list[dict] = []
        width, height = img1.size
        grid_w, grid_h = width // 4, height // 4
        for row in range(4):
            for col in range(4):
                x0, y0 = col * grid_w, row * grid_h
                x1, y1 = x0 + grid_w, y0 + grid_h
                region_diff = diff.crop((x0, y0, x1, y1))
                region_data = list(region_diff.getdata())
                region_changed = sum(1 for p in region_data if any(c > 10 for c in p))
                if region_changed > len(region_data) * 0.05:
                    diff_regions.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "changed_pct": round(region_changed / len(region_data) * 100, 1)})

        summary = (
            f"Las imágenes son {similarity_pct}% similares. "
            f"{'Son prácticamente idénticas.' if similarity_pct > 95 else f'Se detectaron {len(diff_regions)} zonas con diferencias.'}"
        )

        return {"similarity_pct": similarity_pct, "diff_regions": diff_regions, "summary": summary}

    def get_image_info(self, image_path: str) -> dict:
        if not _HAS_PIL:
            return {"error": "PIL no instalado. Ejecuta: pip install Pillow"}

        path = Path(image_path)
        img = Image.open(image_path)
        size_kb = round(path.stat().st_size / 1024, 2)

        return {
            "width": img.width,
            "height": img.height,
            "format": img.format or path.suffix.lstrip(".").upper(),
            "size_kb": size_kb,
            "mode": img.mode,
        }

    def resize_image(self, image_path: str, width: int, height: int, output_path: str) -> dict:
        if not _HAS_PIL:
            return {"error": "PIL no instalado. Ejecuta: pip install Pillow"}

        img = Image.open(image_path)
        resized = img.resize((width, height), Image.LANCZOS)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        resized.save(out)
        return {"ok": True, "output_path": str(out), "new_size": f"{width}x{height}"}

    def take_and_analyze(self, question: Optional[str] = None) -> str:
        if not _HAS_PIL:
            return "PIL no instalado. Ejecuta: pip install Pillow"

        screenshot_path = os.path.join(os.path.expanduser("~"), ".automyx", "last_screenshot.png")
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

        if _HAS_MSS:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                img_data = sct.grab(monitor)
                img = Image.frombytes("RGB", img_data.size, img_data.bgra, "raw", "BGRX")
                img.save(screenshot_path)
        else:
            try:
                img = ImageGrab.grab()
                img.save(screenshot_path)
            except Exception as e:
                return f"No se pudo tomar screenshot: {e}. Instala mss: pip install mss"

        return self.analyze_screenshot(screenshot_path, question)


def get_vision_agent(llm_runner: Optional[Callable[[list], str]] = None) -> VisionAgent:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = VisionAgent(llm_runner)
    elif llm_runner and _INSTANCE._llm is None:
        _INSTANCE._llm = llm_runner
    return _INSTANCE
