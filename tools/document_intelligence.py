"""
Document Intelligence Tools - OCR + análisis + extracción
=========================================================
OCR multi-idioma con Tesseract, extracción de tablas, detección de
entidades (NER), clasificación de documentos, lectura de PDFs escaneados.
"""
from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------
def ocr_image(image_path: str, *, language: str = "spa", preprocessing: bool = True) -> Dict[str, Any]:
    """OCR de una imagen con Tesseract. language: spa, eng, spa+eng, etc."""
    if not PYTESSERACT_AVAILABLE:
        return {"ok": False, "error": "instala pytesseract + tesseract-ocr"}
    if not Path(image_path).exists():
        return {"ok": False, "error": f"imagen no existe: {image_path}"}

    try:
        if preprocessing and PIL_AVAILABLE:
            img = Image.open(image_path)
            # Convertir a grayscale + aumentar contraste
            img = img.convert("L")
            from PIL import ImageEnhance, ImageFilter
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = img.filter(ImageFilter.SHARPEN)
            text = pytesseract.image_to_string(img, lang=language)
        else:
            text = pytesseract.image_to_string(Image.open(image_path), lang=language)
        return {
            "ok": True,
            "image": image_path,
            "language": language,
            "text": text.strip(),
            "char_count": len(text),
            "word_count": len(text.split()),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def ocr_pdf(pdf_path: str, *, language: str = "spa", max_pages: int = 50) -> Dict[str, Any]:
    """OCR de un PDF escaneado."""
    if not Path(pdf_path).exists():
        return {"ok": False, "error": f"PDF no existe: {pdf_path}"}

    # Primero intentar extracción de texto nativa
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages[:max_pages])
                if text.strip() and len(text.strip()) > 100:
                    return {
                        "ok": True,
                        "method": "native_text_extraction",
                        "text": text.strip(),
                        "pages": len(pdf.pages),
                    }
        except Exception:
            pass
    if PYPDF2_AVAILABLE:
        try:
            reader = PyPDF2.PdfReader(pdf_path)
            text = "\n".join((p.extract_text() or "") for p in reader.pages[:max_pages])
            if text.strip() and len(text.strip()) > 100:
                return {
                    "ok": True,
                    "method": "native_text_extraction_pypdf2",
                    "text": text.strip(),
                    "pages": len(reader.pages),
                }
        except Exception:
            pass

    # Si no hay texto, intentar OCR página por página
    if not shutil.which("pdftoppm"):
        return {"ok": False, "error": "PDF escaneado y 'pdftoppm' no instalado"}
    if not PYTESSERACT_AVAILABLE:
        return {"ok": False, "error": "PDF escaneado y pytesseract no instalado"}

    try:
        with pdfplumber.open(pdf_path) if PDFPLUMBER_AVAILABLE else _open_pdf_ctx(pdf_path) as pdf:
            page_count = len(pdf.pages) if hasattr(pdf, "pages") else 0
        if not page_count:
            page_count = max_pages

        tmp_dir = Path("/tmp/pdf_ocr")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdftoppm", "-r", "200", pdf_path, str(tmp_dir / "page")], timeout=120)

        pages_text = []
        for i, img_file in enumerate(sorted(tmp_dir.glob("page-*.ppm"))[:max_pages]):
            r = ocr_image(str(img_file), language=language)
            if r["ok"]:
                pages_text.append({"page": i + 1, "text": r["text"]})

        full_text = "\n\n".join(p["text"] for p in pages_text)
        # Cleanup
        for f in tmp_dir.glob("page-*.ppm"):
            f.unlink()

        return {
            "ok": True,
            "method": "ocr",
            "language": language,
            "text": full_text,
            "page_count": len(pages_text),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _open_pdf_ctx(path):
    """Context manager fallback para PyPDF2."""
    class Ctx:
        def __enter__(self):
            self.r = PyPDF2.PdfReader(path)
            return self.r
        def __exit__(self, *a):
            pass
    return Ctx()


# ---------------------------------------------------------------------------
# NER (Named Entity Recognition) simple
# ---------------------------------------------------------------------------
def extract_entities(text: str) -> Dict[str, Any]:
    """Extracción básica de entidades: emails, URLs, teléfonos, fechas, montos, RUT/CUIT/RFC."""
    entities: Dict[str, List[str]] = {
        "emails": [],
        "urls": [],
        "phones": [],
        "dates": [],
        "amounts": [],
        "tax_ids": [],
    }

    entities["emails"] = list(set(re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)))
    entities["urls"] = list(set(re.findall(r"https?://[^\s)\]]+", text)))

    # Teléfonos (varios formatos)
    phone_patterns = [
        r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
        r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
    ]
    phones: set = set()
    for p in phone_patterns:
        for m in re.findall(p, text):
            phones.add(m)
    entities["phones"] = sorted(phones)

    # Fechas
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
    ]
    dates: set = set()
    for p in date_patterns:
        for m in re.findall(p, text):
            dates.add(m)
    entities["dates"] = sorted(dates)

    # Montos ($1,234.56 / USD 100 / 1.500,00)
    amount_patterns = [
        r"\$\s?[\d,]+\.?\d*",
        r"USD\s?[\d,]+\.?\d*",
        r"EUR\s?[\d,]+\.?\d*",
        r"ARS\s?[\d.,]+",
        r"MXN\s?[\d.,]+",
        r"€\s?[\d.,]+",
    ]
    amounts: set = set()
    for p in amount_patterns:
        for m in re.findall(p, text):
            amounts.add(m.strip())
    entities["amounts"] = sorted(amounts)

    # IDs fiscales (AR, MX, ES, genéricos)
    tax_patterns = {
        "CUIT/CUIL (AR)": r"\b\d{2}-?\d{8}-?\d\b",
        "RFC (MX)": r"\b[A-ZÑ&]{3,4}\d{6}[A-Z\d]{3}\b",
        "NIF/CIF (ES)": r"\b[A-Z]?\d{8}[A-Z]?\b",
        "RUT (CL)": r"\b\d{1,2}\.\d{3}\.\d{3}-[\dKk]\b",
    }
    for label, pat in tax_patterns.items():
        matches = re.findall(pat, text)
        if matches:
            entities["tax_ids"].extend([{"type": label, "value": m} for m in matches])

    counts = {k: len(v) for k, v in entities.items()}
    total = sum(counts.values())

    return {
        "ok": True,
        "text_length": len(text),
        "entity_counts": counts,
        "total_entities": total,
        "entities": entities,
    }


# ---------------------------------------------------------------------------
# Clasificación de documentos
# ---------------------------------------------------------------------------
def classify_document(text: str) -> Dict[str, Any]:
    """Heurística simple: detecta tipo de documento según palabras clave."""
    text_lower = text.lower()
    scores: Dict[str, int] = {}

    rules = {
        "factura": ["factura", "invoice", "subtotal", "iva", "total a pagar", "rfc", "cuit"],
        "contrato": ["contrato", "acuerdo", "cláusula", "firmante", "partes", "vigence"],
        "recibo": ["recibo", "comprobante", "received", "pago recibido"],
        "carta": ["estimado", "atentamente", "saludos cordiales", "cordialmente"],
        "cv": ["experiencia laboral", "educación", "habilidades", "curriculum"],
        "informe": ["informe", "reporte", "conclusiones", "metodología", "resumen ejecutivo"],
        "manual": ["instrucciones", "paso 1", "cómo", "tutorial", "guía"],
        "legal": ["artículo", "decreto", "resolución", "jurisprudencia", "tribunal"],
        "académico": ["abstract", "resumen", "hipótesis", "metodología", "bibliografía"],
    }

    for category, keywords in rules.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        return {"ok": True, "type": "desconocido", "confidence": 0, "scores": {}}

    best = max(scores.items(), key=lambda x: x[1])
    return {
        "ok": True,
        "type": best[0],
        "confidence": min(1.0, best[1] / 3.0),
        "scores": scores,
    }


# ---------------------------------------------------------------------------
# Resumen / key sentences
# ---------------------------------------------------------------------------
def summarize(text: str, *, sentences: int = 5, language: str = "es") -> Dict[str, Any]:
    """Resumen extractivo simple: rankea oraciones por frecuencia de palabras."""
    if not text.strip():
        return {"ok": False, "error": "texto vacío"}
    try:
        import nltk
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            try:
                nltk.download("punkt", quiet=True)
                nltk.download("punkt_tab", quiet=True)
            except Exception:
                pass
        from nltk.tokenize import sent_tokenize
    except ImportError:
        # Fallback: split por .!?
        sents = re.split(r"(?<=[.!?])\s+", text)
        return _summarize_with_sents(text, sents, sentences)

    try:
        sents = sent_tokenize(text, language=language)
    except Exception:
        sents = re.split(r"(?<=[.!?])\s+", text)
    return _summarize_with_sents(text, sents, sentences)


def _summarize_with_sents(text: str, sents: List[str], n: int) -> Dict[str, Any]:
    if len(sents) <= n:
        return {"ok": True, "summary": text, "sentence_count": len(sents)}
    # Frecuencia de palabras
    words = re.findall(r"\w+", text.lower())
    stopwords = {"el", "la", "los", "las", "de", "del", "al", "a", "y", "o", "en", "un", "una", "que", "se", "es", "por", "con", "para", "su", "sus", "le", "lo", "como", "más", "pero", "sin", "sobre", "entre"}
    freq: Dict[str, int] = {}
    for w in words:
        if w not in stopwords and len(w) > 3:
            freq[w] = freq.get(w, 0) + 1
    # Score por oración
    scored = []
    for i, s in enumerate(sents):
        score = sum(freq.get(w, 0) for w in re.findall(r"\w+", s.lower()))
        scored.append((score / max(1, len(s.split())), i, s))
    scored.sort(reverse=True)
    top = sorted(scored[:n], key=lambda x: x[1])
    return {
        "ok": True,
        "summary": " ".join(s[2] for s in top),
        "sentence_count": len(sents),
        "selected_indices": [s[1] for s in top],
    }


# ---------------------------------------------------------------------------
# Tabla de contenido / outline
# ---------------------------------------------------------------------------
def outline(text: str, *, max_items: int = 50) -> Dict[str, Any]:
    """Extrae un outline de headings (markdown, mayúsculas, numerados)."""
    items: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line_strip = line.rstrip()
        if not line_strip:
            continue
        m = re.match(r"^(#+)\s+(.+)", line_strip)
        if m:
            items.append({"level": len(m.group(1)), "text": m.group(2).strip(), "type": "markdown"})
            continue
        if re.match(r"^\d+[\.\)]\s+\S", line_strip):
            items.append({"level": 1, "text": line_strip, "type": "numbered"})
            continue
        if line_strip.isupper() and 3 <= len(line_strip.split()) <= 15:
            items.append({"level": 1, "text": line_strip, "type": "caps"})
    return {"ok": True, "items": items[:max_items], "count": len(items)}


# ---------------------------------------------------------------------------
# Comparar documentos
# ---------------------------------------------------------------------------
def compare(text_a: str, text_b: str) -> Dict[str, Any]:
    """Compara dos textos: similaridad + líneas únicas de cada uno."""
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, text_a, text_b).ratio()
    a_lines = set(text_a.splitlines())
    b_lines = set(text_b.splitlines())
    return {
        "ok": True,
        "similarity_ratio": round(ratio, 4),
        "similarity_pct": round(ratio * 100, 2),
        "only_in_a_count": len(a_lines - b_lines),
        "only_in_b_count": len(b_lines - a_lines),
        "common_lines": len(a_lines & b_lines),
    }


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class DocumentIntelligenceTools:
    @staticmethod
    def ocr(image_path: str, language: str = "spa") -> Dict[str, Any]:
        return ocr_image(image_path, language=language)

    @staticmethod
    def ocr_pdf(pdf_path: str, language: str = "spa") -> Dict[str, Any]:
        return ocr_pdf(pdf_path, language=language)

    @staticmethod
    def entities(text: str) -> Dict[str, Any]:
        return extract_entities(text)

    @staticmethod
    def classify(text: str) -> Dict[str, Any]:
        return classify_document(text)

    @staticmethod
    def summarize(text: str, sentences: int = 5) -> Dict[str, Any]:
        return summarize(text, sentences=sentences)

    @staticmethod
    def outline(text: str) -> Dict[str, Any]:
        return outline(text)

    @staticmethod
    def compare(text_a: str, text_b: str) -> Dict[str, Any]:
        return compare(text_a, text_b)
