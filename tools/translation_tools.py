"""
Translation Tools - Traducción multi-idioma
===========================================
Traducción con detección de idioma, glosarios, y fallback entre
múltiples servicios. Usa la API de MyMemory como fallback gratuito.
"""
from __future__ import annotations

import os
import json
import time
import re
import requests
from typing import Any, Dict, List, Optional

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator, DeeplTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False

try:
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


LANG_NAMES = {
    "es": "español", "en": "inglés", "pt": "portugués", "fr": "francés",
    "de": "alemán", "it": "italiano", "zh": "chino", "ja": "japonés",
    "ko": "coreano", "ru": "ruso", "ar": "árabe", "hi": "hindi",
    "nl": "holandés", "pl": "polaco", "tr": "turco", "sv": "sueco",
    "fi": "finlandés", "no": "noruego", "da": "danés", "cs": "checo",
    "el": "griego", "he": "hebreo", "th": "tailandés", "vi": "vietnamita",
    "id": "indonesio", "ms": "malayo", "uk": "ucraniano", "ro": "rumano",
    "hu": "húngaro", "ca": "catalán", "gl": "gallego", "eu": "euskera",
}


# ---------------------------------------------------------------------------
# Detección
# ---------------------------------------------------------------------------
def detect_language(text: str) -> Dict[str, Any]:
    """Detecta el idioma del texto."""
    if not LANGDETECT_AVAILABLE:
        return {"ok": False, "error": "instala langdetect (pip install langdetect)"}
    try:
        primary = detect(text)
        probs = detect_langs(text)
        return {
            "ok": True,
            "language": primary,
            "language_name": LANG_NAMES.get(primary, primary),
            "alternatives": [{"lang": p.lang, "prob": round(p.prob, 3)} for p in probs[:5]],
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Traducción
# ---------------------------------------------------------------------------
def translate(text: str, target: str = "en", source: str = "auto",
              *, engine: str = "google", glossary: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Traduce texto. engine: google (default), mymemory, deepl."""
    if not text.strip():
        return {"ok": False, "error": "texto vacío"}

    if engine == "deepl":
        if not DEEP_TRANSLATOR_AVAILABLE:
            return {"ok": False, "error": "instala deep-translator"}
        if not os.environ.get("DEEPL_API_KEY"):
            return {"ok": False, "error": "configura DEEPL_API_KEY"}
        try:
            translator = DeeplTranslator(api_key=os.environ["DEEPL_API_KEY"], source=source, target=target)
            out = translator.translate(text)
            return {"ok": True, "engine": "deepl", "source": source, "target": target, "translated": out}
        except Exception as e:
            return {"ok": False, "error": f"deepl: {type(e).__name__}: {e}"}

    if engine == "mymemory":
        try:
            params = {"q": text, "langpair": f"{source}|{target}"}
            r = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=10)
            data = r.json()
            if data.get("responseStatus") != 200:
                return {"ok": False, "error": data.get("responseDetails", "error"), "engine": "mymemory"}
            translated = data["responseData"]["translatedText"]
            return {"ok": True, "engine": "mymemory", "source": source, "target": target,
                    "translated": translated, "match": data["responseData"].get("match")}
        except Exception as e:
            return {"ok": False, "error": f"mymemory: {type(e).__name__}: {e}"}

    # Default: Google vía deep-translator
    if not DEEP_TRANSLATOR_AVAILABLE:
        return {"ok": False, "error": "instala deep-translator (pip install deep-translator)"}
    try:
        translator = GoogleTranslator(source=source, target=target)
        translated = translator.translate(text)
        return {"ok": True, "engine": "google", "source": source, "target": target, "translated": translated}
    except Exception as e:
        # Fallback a MyMemory
        return translate(text, target=target, source=source, engine="mymemory", glossary=glossary)


def apply_glossary(text: str, glossary: Dict[str, str], reverse: bool = False) -> str:
    """Aplica un glosario de términos (post-procesado)."""
    out = text
    items = glossary.items() if not reverse else [(v, k) for k, v in glossary.items()]
    for src, tgt in items:
        pattern = re.compile(r"\b" + re.escape(src) + r"\b", re.IGNORECASE)
        out = pattern.sub(tgt, out)
    return out


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------
def translate_batch(texts: List[str], target: str = "en", source: str = "auto",
                    *, engine: str = "google", delay_s: float = 0.3) -> Dict[str, Any]:
    """Traduce múltiples textos con rate limiting."""
    results = []
    errors = []
    for i, t in enumerate(texts):
        r = translate(t, target=target, source=source, engine=engine)
        if r["ok"]:
            results.append({"input": t, "output": r["translated"]})
        else:
            errors.append({"input": t, "error": r.get("error")})
        if delay_s > 0 and i < len(texts) - 1:
            time.sleep(delay_s)
    return {"ok": True, "translated": results, "errors": errors, "count": len(results)}


# ---------------------------------------------------------------------------
# Idiomas soportados
# ---------------------------------------------------------------------------
def supported_languages() -> Dict[str, Any]:
    if not DEEP_TRANSLATOR_AVAILABLE:
        return {"ok": False, "error": "instala deep-translator"}
    try:
        langs = GoogleTranslator().get_supported_languages(as_dict=True)
        return {
            "ok": True,
            "count": len(langs),
            "languages": [{"code": k, "name": v.capitalize() if isinstance(v, str) else k} for k, v in langs.items()],
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class TranslationTools:
    @staticmethod
    def detect(text: str) -> Dict[str, Any]:
        return detect_language(text)

    @staticmethod
    def translate(text: str, target: str = "en", source: str = "auto", engine: str = "google") -> Dict[str, Any]:
        return translate(text, target, source, engine=engine)

    @staticmethod
    def translate_batch(texts: List[str], target: str = "en", engine: str = "google") -> Dict[str, Any]:
        return translate_batch(texts, target, engine=engine)

    @staticmethod
    def languages() -> Dict[str, Any]:
        return supported_languages()
