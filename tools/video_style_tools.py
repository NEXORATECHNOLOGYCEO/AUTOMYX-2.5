"""
AUTOMYX VIDEO STYLE ANALYZER
=============================
Ve videos de TikTok / YouTube / Shorts / cualquier URL soportada por yt-dlp,
extrae frames y los analiza con el modelo de visión para producir un REPORTE DE
ESTILO: estética visual, paleta, ritmo, formato, tono narrativo — y un prompt
listo para replicar ese estilo con `vyrex_create_story_video`.

Caso estrella: analizar videos de frutinovelas / frutas antropomórficas y
clonar su estilo en videos nuevos.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict


def _ensure_ytdlp() -> bool:
    try:
        import yt_dlp  # noqa
        return True
    except ImportError:
        try:
            import sys
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"],
                           timeout=180, check=True)
            import yt_dlp  # noqa
            return True
        except Exception:
            return False


def _ffmpeg_ok() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


class VideoStyleTools:
    @staticmethod
    def analyze_video_style(url: str, focus: str = "") -> Dict[str, Any]:
        """VE un video de TikTok/YouTube/Shorts y analiza su ESTILO con visión IA.
        Devuelve: metadatos (título, autor, duración, formato), análisis visual de
        4 frames (estética, personajes, colores, texto en pantalla), y un
        'style_prompt' listo para copiar el estilo con vyrex_create_story_video.
        focus: opcional, en qué fijarse (ej 'el estilo de las frutas antropomórficas').
        Analiza solo los primeros ~60s (suficiente para captar el estilo)."""
        if not url or not url.startswith("http"):
            return {"ok": False, "error": "url requerida (TikTok, YouTube, Shorts...)"}
        if not _ensure_ytdlp():
            return {"ok": False, "error": "no pude instalar yt-dlp (pip install yt-dlp)"}
        if not _ffmpeg_ok():
            return {"ok": False, "error": "ffmpeg no encontrado en el PATH — instálalo para analizar videos"}

        import yt_dlp

        workdir = Path(tempfile.mkdtemp(prefix="automyx_style_"))
        video_path = workdir / "clip.mp4"
        meta: Dict[str, Any] = {}
        try:
            ydl_opts = {
                "outtmpl": str(video_path),
                "format": "b[height<=480]/bv*[height<=480]+ba/b",
                "quiet": True, "no_warnings": True,
                "noplaylist": True,
                "download_ranges": yt_dlp.utils.download_range_func(None, [(0, 60)]),
                "force_keyframes_at_cuts": False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            meta = {
                "title": info.get("title"),
                "uploader": info.get("uploader") or info.get("channel"),
                "duration_s": info.get("duration"),
                "width": info.get("width"), "height": info.get("height"),
                "view_count": info.get("view_count"),
                "tags": (info.get("tags") or [])[:10],
                "description": (info.get("description") or "")[:300],
            }
            fmt = "9:16 (vertical/short)" if (info.get("height") or 0) > (info.get("width") or 1) \
                  else "16:9 (horizontal)"
            meta["formato"] = fmt

            if not video_path.exists():
                # yt-dlp puede añadir extensión distinta
                cands = list(workdir.glob("clip.*"))
                if cands:
                    video_path = cands[0]
                else:
                    return {"ok": False, "error": "no se pudo descargar el video", "meta": meta}

            # ── extraer 4 frames repartidos ──
            dur = min(float(info.get("duration") or 60), 60.0)
            stamps = [dur * f for f in (0.1, 0.35, 0.6, 0.85)]
            frames = []
            for i, ts in enumerate(stamps):
                fp = workdir / f"frame_{i}.jpg"
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", f"{ts:.1f}", "-i", str(video_path),
                     "-vframes", "1", "-q:v", "4", str(fp)],
                    capture_output=True, timeout=60)
                if fp.exists() and fp.stat().st_size > 2000:
                    frames.append(fp)
            if not frames:
                return {"ok": False, "error": "no se pudieron extraer frames", "meta": meta}

            # ── visión IA sobre los frames ──
            from tools.vision_tools import VisionTools
            q = (
                "Analiza el ESTILO de este frame de video: estética visual (2D/3D/real/"
                "cartoon), personajes (¿frutas u objetos antropomórficos? ¿personas?), "
                "paleta de colores dominante, iluminación, estilo de subtítulos/texto en "
                "pantalla, encuadre. Sé conciso y concreto."
            )
            if focus:
                q += f" Fíjate especialmente en: {focus}"
            frame_reports = []
            for fp in frames:
                r = VisionTools.see_image(str(fp), q)
                if r.get("ok"):
                    frame_reports.append(r.get("description", "")[:600])

            if not frame_reports:
                return {"ok": False, "error": "el modelo de visión no pudo analizar los frames", "meta": meta}

            # ── sintetizar el reporte de estilo + prompt replicable ──
            joined = "\n---\n".join(frame_reports)
            style_prompt = None
            try:
                from core.agent import ModelProvider
                client = ModelProvider.get_client("minimaxai/minimax-m3", provider="nvidia")
                resp = client.chat.completions.create(
                    model="minimaxai/minimax-m3",
                    messages=[{"role": "user", "content": (
                        "A partir de estos análisis de 4 frames de un video"
                        + (f" (foco: {focus})" if focus else "") + ":\n" + joined +
                        f"\n\nMetadatos: {json.dumps(meta, ensure_ascii=False)[:400]}\n\n"
                        "1) Resume el ESTILO del video en 4-6 líneas (estética, personajes, "
                        "colores, ritmo, tono).\n"
                        "2) Escribe un STYLE_PROMPT de una línea (español) que capture ese "
                        "estilo visual para replicarlo en un generador de video IA — empieza "
                        "esa línea exactamente con 'STYLE_PROMPT:'."
                    )}],
                    max_tokens=500, temperature=0.4,
                )
                synthesis = (resp.choices[0].message.content or "").strip()
                m = re.search(r"STYLE_PROMPT:\s*(.+)", synthesis)
                style_prompt = m.group(1).strip() if m else None
            except Exception:
                synthesis = joined[:900]

            return {
                "ok": True,
                "meta": meta,
                "style_analysis": synthesis[:1400],
                "style_prompt": style_prompt,
                "how_to_replicate": (
                    "Usa vyrex_create_story_video(topic='TU TEMA. Estilo visual: ' + style_prompt, "
                    f"ratio='{'9:16' if 'vertical' in meta.get('formato', '') else '16:9'}', "
                    "style='Viral') para crear un video nuevo con este estilo."
                ),
            }
        except Exception as e:
            return {"ok": False, "error": f"analyze_video_style falló: {str(e)[:250]}", "meta": meta}
        finally:
            try:
                import shutil
                shutil.rmtree(workdir, ignore_errors=True)
            except Exception:
                pass
