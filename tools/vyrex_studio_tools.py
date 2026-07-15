"""
AUTOMYX × VYREX STUDIO — VÍA API DIRECTA
=========================================
Genera imágenes/videos/voz de Vyrex Studio llamando a la API oficial
(https://vyrexstudio.com/v1) con la VYREX_API_KEY del .env — SIN abrir el
navegador ni depender de coordenadas de pantalla. 100% verificable: la tool
descarga el resultado a Descargas y devuelve la ruta local + URL.

Preferir SIEMPRE estas tools sobre el flujo navegador+visión para tareas de
Vyrex (el flujo visual queda para cuando el usuario pida explícitamente "ver"
o interactuar con la web).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

_BASE = os.getenv("VYREX_API_BASE", "https://vyrexstudio.com/v1")


def _key() -> str:
    k = os.getenv("VYREX_API_KEY", "").strip()
    if not k:
        raise RuntimeError("Falta VYREX_API_KEY en .env — configúrala en /onboard")
    return k


def _downloads() -> Path:
    d = Path.home() / "Downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download(url: str, dest: Path) -> Path:
    import requests
    r = requests.get(url, timeout=300, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for ch in r.iter_content(chunk_size=65536):
            if ch:
                f.write(ch)
    return dest


def _open_file(path: Path) -> None:
    try:
        os.startfile(str(path))  # visor predeterminado de Windows
    except Exception:
        pass


class VyrexStudioTools:
    @staticmethod
    def vyrex_generate_image(prompt: str, ratio: str = "1:1", model: str = "lite",
                             open_result: bool = True) -> Dict[str, Any]:
        """Genera una imagen en Vyrex Image Studio vía API oficial (SIN navegador).
        prompt: descripción de la imagen. ratio: 1:1, 16:9, 9:16, 4:3, 3:4.
        model: 'lite' (1¢) o 'pro' (3¢). Descarga el PNG a Descargas y lo abre."""
        import requests
        if not prompt or len(prompt.strip()) < 3:
            return {"ok": False, "error": "prompt requerido (mínimo 3 caracteres)"}
        try:
            r = requests.post(
                f"{_BASE}/images/generations",
                json={"prompt": prompt, "model": model, "ratio": ratio},
                headers={"Authorization": f"Bearer {_key()}"},
                timeout=300,
            )
            if r.status_code == 402:
                return {"ok": False, "error": "Saldo API insuficiente — recarga en vyrexstudio.com → API Vyrex"}
            r.raise_for_status()
            d = r.json()
            url = d.get("url")
            if not url:
                return {"ok": False, "error": f"la API no devolvió imagen: {str(d)[:200]}"}
            import re
            slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:40].strip("_") or "imagen"
            dest = _downloads() / f"vyrex_{slug}.png"
            _download(url, dest)
            if open_result:
                _open_file(dest)
            return {
                "ok": True,
                "local_path": str(dest),
                "url": url,
                "cost_cents": d.get("cost_cents"),
                "balance_cents": d.get("balance_cents"),
                "detail": f"Imagen generada y guardada en {dest.name} (abierta en el visor)",
            }
        except Exception as e:
            return {"ok": False, "error": f"vyrex_generate_image falló: {str(e)[:200]}"}

    @staticmethod
    def vyrex_generate_video_api(prompt: str, duration: float = 5.0, ratio: str = "9:16",
                                 open_result: bool = True) -> Dict[str, Any]:
        """Genera un video IA en Vyrex Studio vía API oficial (SIN navegador).
        duration: 2-20 segundos (5¢/seg). Descarga el MP4 a Descargas y lo abre.
        OJO: tarda 1-4 minutos según duración — es normal, no reintentar."""
        import requests
        if not prompt or len(prompt.strip()) < 3:
            return {"ok": False, "error": "prompt requerido"}
        try:
            r = requests.post(
                f"{_BASE}/videos/generations",
                json={"prompt": prompt, "duration": max(2.0, min(float(duration or 5.0), 20.0)),
                      "ratio": ratio},
                headers={"Authorization": f"Bearer {_key()}"},
                timeout=600,
            )
            if r.status_code == 402:
                return {"ok": False, "error": "Saldo API insuficiente — recarga en vyrexstudio.com → API Vyrex"}
            r.raise_for_status()
            d = r.json()
            url = d.get("url")
            if not url:
                return {"ok": False, "error": f"la API no devolvió video: {str(d)[:200]}"}
            import re
            slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:40].strip("_") or "video"
            dest = _downloads() / f"vyrex_{slug}.mp4"
            _download(url, dest)
            if open_result:
                _open_file(dest)
            return {
                "ok": True,
                "local_path": str(dest),
                "url": url,
                "duration_s": d.get("duration_s"),
                "cost_cents": d.get("cost_cents"),
                "detail": f"Video generado y guardado en {dest.name} (abierto en el reproductor)",
            }
        except Exception as e:
            return {"ok": False, "error": f"vyrex_generate_video_api falló: {str(e)[:200]}"}

    @staticmethod
    def vyrex_generate_voice(text: str, language: str = "spanish",
                             open_result: bool = True) -> Dict[str, Any]:
        """Genera voz IA (TTS premium Vyrex) vía API oficial. 2¢/1000 chars.
        Descarga el WAV a Descargas."""
        import requests
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "text requerido"}
        try:
            r = requests.post(
                f"{_BASE}/audio/speech",
                json={"text": text[:5000], "language": language},
                headers={"Authorization": f"Bearer {_key()}"},
                timeout=300,
            )
            if r.status_code == 402:
                return {"ok": False, "error": "Saldo API insuficiente — recarga en vyrexstudio.com → API Vyrex"}
            r.raise_for_status()
            d = r.json()
            url = d.get("url")
            if not url:
                return {"ok": False, "error": f"la API no devolvió audio: {str(d)[:200]}"}
            import re
            slug = re.sub(r"[^a-z0-9]+", "_", text.lower())[:36].strip("_") or "voz"
            dest = _downloads() / f"vyrex_voz_{slug}.wav"
            _download(url, dest)
            if open_result:
                _open_file(dest)
            return {"ok": True, "local_path": str(dest), "url": url,
                    "cost_cents": d.get("cost_cents"),
                    "detail": f"Voz generada y guardada en {dest.name}"}
        except Exception as e:
            return {"ok": False, "error": f"vyrex_generate_voice falló: {str(e)[:200]}"}


    @staticmethod
    def vyrex_create_story_video(topic: str, duration: int = 30, style: str = "Viral",
                                 image_style: str = "Cinematografico", ratio: str = "9:16",
                                 language: str = "", script: str = "",
                                 voice_url: str = "", open_result: bool = True) -> Dict[str, Any]:
        """Crea un VIDEO PROFESIONAL MULTI-ESCENA desde cero con el pipeline completo
        de Vyrex Studio: guion IA → escenas → imágenes IA → narración con voz →
        subtítulos → transiciones cinematográficas con efectos de sonido.
        topic: tema o idea del video. duration: 30, 60 o 90 segundos.
        style: 'Viral' (cortes rápidos TikTok) o 'Profesional' (cinematográfico).
        ratio: 9:16 (TikTok/Shorts), 16:9 (YouTube), 1:1, 4:3, 3:4.
        language: es/en/fr/de/it/pt/ru/ja/ko/zh (vacío = idioma del tema).
        script: guion literal opcional (si no, la IA lo escribe).
        voice_url: URL de audio para CLONAR la voz del narrador.
        TARDA 3-12 MIN según duración — la tool espera y descarga el MP4 final.
        Costo: 2¢/segundo (30s=60¢, 60s=$1.20, 90s=$1.80)."""
        import requests, time
        if not topic or len(topic.strip()) < 3:
            return {"ok": False, "error": "topic requerido"}
        payload = {"topic": topic, "duration": int(duration) if int(duration) in (30, 60, 90) else 30,
                   "style": style if style in ("Viral", "Profesional") else "Viral",
                   "image_style": image_style or "Cinematografico",
                   "ratio": ratio if ratio in ("9:16", "16:9", "1:1", "4:3", "3:4") else "9:16"}
        if language:
            payload["language"] = language
        if script:
            payload["script"] = script
        if voice_url:
            payload["voice_url"] = voice_url
        try:
            r = requests.post(f"{_BASE}/videos/story", json=payload,
                              headers={"Authorization": f"Bearer {_key()}"}, timeout=60)
            if r.status_code == 402:
                return {"ok": False, "error": "Saldo API insuficiente — recarga en vyrexstudio.com"}
            r.raise_for_status()
            job = r.json()
            job_id = job["job_id"]
            # poll hasta 20 min
            deadline = time.time() + 1200
            last = {}
            while time.time() < deadline:
                time.sleep(10)
                try:
                    s = requests.get(f"{_BASE}/videos/story/{job_id}",
                                     headers={"Authorization": f"Bearer {_key()}"}, timeout=30)
                    last = s.json()
                except Exception:
                    continue
                if last.get("status") == "done":
                    break
                if last.get("status") == "error":
                    return {"ok": False, "error": f"pipeline falló: {last.get('error')}",
                            "refunded": last.get("refunded", False)}
            if last.get("status") != "done":
                return {"ok": False, "error": "timeout esperando el video (sigue en el servidor; reintenta el poll)",
                        "job_id": job_id}
            url = last["url"]
            import re
            slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40].strip("_") or "video"
            dest = _downloads() / f"vyrex_story_{slug}.mp4"
            _download(url, dest)
            if open_result:
                _open_file(dest)
            return {"ok": True, "local_path": str(dest), "url": url,
                    "cost_cents": job.get("cost_cents"),
                    "script_preview": last.get("script", ""),
                    "detail": f"Video profesional de {payload['duration']}s creado y guardado en {dest.name}"}
        except Exception as e:
            return {"ok": False, "error": f"vyrex_create_story_video falló: {str(e)[:200]}"}

    @staticmethod
    def vyrex_publish_youtube(video_url: str, title: str, description: str = "",
                              privacy: str = "public") -> Dict[str, Any]:
        """Publica un video en el canal de YouTube conectado a la cuenta Vyrex.
        video_url: URL del video (la que devuelven las tools vyrex_*, o externa).
        privacy: public | unlisted | private. Devuelve el link de YouTube."""
        import requests
        if not video_url or not title:
            return {"ok": False, "error": "video_url y title requeridos"}
        try:
            r = requests.post(f"{_BASE}/publish/youtube",
                              json={"video_url": video_url, "title": title,
                                    "description": description or title, "privacy": privacy},
                              headers={"Authorization": f"Bearer {_key()}"}, timeout=900)
            if not r.ok:
                try:
                    det = r.json().get("detail", r.text[:200])
                except Exception:
                    det = r.text[:200]
                return {"ok": False, "error": f"HTTP {r.status_code}: {det}"}
            d = r.json()
            return {"ok": True, "watch_url": d.get("watch_url"), "video_id": d.get("video_id"),
                    "detail": f"Publicado en YouTube: {d.get('watch_url')}"}
        except Exception as e:
            return {"ok": False, "error": f"vyrex_publish_youtube falló: {str(e)[:200]}"}

    @staticmethod
    def vyrex_publish_facebook(video_url: str, title: str, description: str = "") -> Dict[str, Any]:
        """Publica un video en la página de Facebook conectada a la cuenta Vyrex."""
        import requests
        if not video_url or not title:
            return {"ok": False, "error": "video_url y title requeridos"}
        try:
            r = requests.post(f"{_BASE}/publish/facebook",
                              json={"video_url": video_url, "title": title,
                                    "description": description or title},
                              headers={"Authorization": f"Bearer {_key()}"}, timeout=900)
            if not r.ok:
                try:
                    det = r.json().get("detail", r.text[:200])
                except Exception:
                    det = r.text[:200]
                return {"ok": False, "error": f"HTTP {r.status_code}: {det}"}
            d = r.json()
            return {"ok": True, "video_id": d.get("video_id"),
                    "detail": "Publicado en la página de Facebook"}
        except Exception as e:
            return {"ok": False, "error": f"vyrex_publish_facebook falló: {str(e)[:200]}"}


    @staticmethod
    def _poll_video_job(job_id: str, max_wait: int = 600) -> Dict[str, Any]:
        import requests, time
        deadline = time.time() + max_wait
        last: Dict[str, Any] = {}
        while time.time() < deadline:
            time.sleep(8)
            try:
                s = requests.get(f"{_BASE}/videos/story/{job_id}",
                                 headers={"Authorization": f"Bearer {_key()}"}, timeout=30)
                last = s.json()
            except Exception:
                continue
            if last.get("status") in ("done", "error"):
                return last
        last.setdefault("status", "timeout")
        return last

    @staticmethod
    def vyrex_text_to_clip(prompt: str, duration: int = 5, ratio: str = "9:16",
                           subtitles: bool = False, open_result: bool = True) -> Dict[str, Any]:
        """TEXTO A CLIP con AUDIO NATIVO (la seccion Texto a Video de Vyrex):
        describe una escena y la IA genera el video CON sonido/voz nativos.
        duration: 5, 10, 15 o 20 segundos (5 centavos/seg). ratio: 9:16, 16:9, 1:1.
        subtitles=True quema subtitulos estilo viral sincronizados con el audio.
        Tarda 1-4 min segun duracion — la tool espera y descarga el MP4."""
        import requests
        if not prompt or len(prompt.strip()) < 3:
            return {"ok": False, "error": "prompt requerido"}
        try:
            r = requests.post(f"{_BASE}/videos/clip",
                              json={"prompt": prompt, "duration": int(duration),
                                    "ratio": ratio, "subtitles": bool(subtitles)},
                              headers={"Authorization": f"Bearer {_key()}"}, timeout=60)
            if r.status_code == 402:
                return {"ok": False, "error": "Saldo API insuficiente — recarga en vyrexstudio.com"}
            if not r.ok:
                try:
                    det = r.json().get("detail", r.text[:200])
                except Exception:
                    det = r.text[:200]
                return {"ok": False, "error": f"HTTP {r.status_code}: {det}"}
            job = r.json()
            last = VyrexStudioTools._poll_video_job(job["job_id"], max_wait=420)
            if last.get("status") != "done":
                return {"ok": False, "error": last.get("error") or f"estado: {last.get('status')}",
                        "job_id": job["job_id"]}
            import re
            slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:40].strip("_") or "clip"
            dest = _downloads() / f"vyrex_clip_{slug}.mp4"
            _download(last["url"], dest)
            if open_result:
                _open_file(dest)
            _subs = " y subtitulos" if subtitles else ""
            return {"ok": True, "local_path": str(dest), "url": last["url"],
                    "cost_cents": job.get("cost_cents"),
                    "detail": f"Clip de {duration}s con audio nativo{_subs} en {dest.name}"}
        except Exception as e:
            return {"ok": False, "error": f"vyrex_text_to_clip fallo: {str(e)[:200]}"}

    @staticmethod
    def vyrex_animate_image(image_path: str, prompt: str = "", duration: int = 5,
                            ratio: str = "9:16", subtitles: bool = False,
                            open_result: bool = True) -> Dict[str, Any]:
        """ANIMAR IMAGEN con AUDIO NATIVO (seccion Animar Imagen de Vyrex): da vida
        a una imagen local o URL. Mantiene la identidad facial y anima labios de forma
        natural si el prompt implica hablar. image_path: ruta local (png/jpg) o URL.
        duration: 5/10/15/20s (5 centavos/seg). subtitles=True quema subtitulos.
        Tarda 1-4 min — la tool espera y descarga el MP4."""
        import requests
        import base64 as _b64
        payload: Dict[str, Any] = {"prompt": prompt or "", "duration": int(duration),
                                   "ratio": ratio, "subtitles": bool(subtitles)}
        if str(image_path).startswith(("http://", "https://")):
            payload["image_url"] = image_path
        else:
            fp = Path(image_path)
            if not fp.exists():
                return {"ok": False, "error": f"no existe la imagen: {image_path}"}
            payload["image_b64"] = _b64.b64encode(fp.read_bytes()).decode()
        try:
            r = requests.post(f"{_BASE}/videos/animate", json=payload,
                              headers={"Authorization": f"Bearer {_key()}"}, timeout=120)
            if r.status_code == 402:
                return {"ok": False, "error": "Saldo API insuficiente — recarga en vyrexstudio.com"}
            if not r.ok:
                try:
                    det = r.json().get("detail", r.text[:200])
                except Exception:
                    det = r.text[:200]
                return {"ok": False, "error": f"HTTP {r.status_code}: {det}"}
            job = r.json()
            last = VyrexStudioTools._poll_video_job(job["job_id"], max_wait=420)
            if last.get("status") != "done":
                return {"ok": False, "error": last.get("error") or f"estado: {last.get('status')}",
                        "job_id": job["job_id"]}
            import re
            base = Path(str(image_path)).stem if not str(image_path).startswith("http") else "imagen"
            slug = re.sub(r"[^a-z0-9]+", "_", base.lower())[:36].strip("_") or "imagen"
            dest = _downloads() / f"vyrex_anim_{slug}.mp4"
            _download(last["url"], dest)
            if open_result:
                _open_file(dest)
            _subs = ", subtitulos" if subtitles else ""
            return {"ok": True, "local_path": str(dest), "url": last["url"],
                    "cost_cents": job.get("cost_cents"),
                    "detail": f"Imagen animada ({duration}s, audio nativo{_subs}) en {dest.name}"}
        except Exception as e:
            return {"ok": False, "error": f"vyrex_animate_image fallo: {str(e)[:200]}"}
