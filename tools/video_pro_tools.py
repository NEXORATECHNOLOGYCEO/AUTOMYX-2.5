"""
Video Pro Tools - Edición de video profesional mejorada
========================================================
Extiende VideoTools con capacidades avanzadas:
  - Detección de escenas (PySceneDetect si está disponible)
  - Generación de thumbnails/grids
  - Conversión entre formatos con control de calidad
  - Análisis de calidad (PSNR, SSIM)
  - Composición multi-pista
  - Efectos avanzados (chroma key, blur de fondo, estabilización)
  - Renderizado de subtítulos animados
  - Export multi-formato (TikTok, YouTube, Reels, Shorts)
  - Audio processing (normalización, compresión, EQ)
  - Generación de GIF
  - Slow motion / Time-lapse
"""
from __future__ import annotations

import os
import re
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from .pc_tools import PCTools
except ImportError:
    try:
        from tools.pc_tools import PCTools
    except ImportError:
        PCTools = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None


def _resolve(path: str) -> str:
    if PCTools:
        return PCTools._resolve_path(path)
    return os.path.expandvars(os.path.expanduser(path))


def _ffmpeg_bin() -> str:
    return "ffmpeg.exe" if os.name == "nt" else "ffmpeg"


def _ffprobe_bin() -> str:
    return "ffprobe.exe" if os.name == "nt" else "ffprobe"


def _check_ffmpeg() -> bool:
    return shutil.which(_ffmpeg_bin()) is not None or shutil.which("ffmpeg") is not None


def _check_ffprobe() -> bool:
    return shutil.which(_ffprobe_bin()) is not None or shutil.which("ffprobe") is not None


def _run(cmd: List[str], timeout: int = 600) -> Dict[str, Any]:
    """Run subprocess con manejo de errores uniforme."""
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "duration_s": round(time.time() - t0, 2),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout después de {timeout}s"}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"binario no encontrado: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Inspección
# ---------------------------------------------------------------------------
def probe(input_path: str) -> Dict[str, Any]:
    """Devuelve metadatos detallados del video."""
    if not _check_ffprobe():
        return {"ok": False, "error": "ffprobe no instalado"}
    r = _run([_ffprobe_bin(), "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", input_path])
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"])
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        vstreams = [s for s in streams if s.get("codec_type") == "video"]
        astreams = [s for s in streams if s.get("codec_type") == "audio"]

        result = {
            "ok": True,
            "format": fmt.get("format_name"),
            "duration_s": float(fmt.get("duration", 0)),
            "size_bytes": int(fmt.get("size", 0)),
            "bitrate_bps": int(fmt.get("bit_rate", 0)),
            "video": {},
            "audio": {},
        }
        if vstreams:
            v = vstreams[0]
            result["video"] = {
                "codec": v.get("codec_name"),
                "width": v.get("width"),
                "height": v.get("height"),
                "fps": _parse_fps(v.get("r_frame_rate", "0/1")),
                "bitrate_bps": int(v.get("bit_rate", 0)) if v.get("bit_rate") else None,
            }
        if astreams:
            a = astreams[0]
            result["audio"] = {
                "codec": a.get("codec_name"),
                "sample_rate": int(a.get("sample_rate", 0)),
                "channels": a.get("channels"),
                "bitrate_bps": int(a.get("bit_rate", 0)) if a.get("bit_rate") else None,
            }
        return result
    except Exception as e:
        return {"ok": False, "error": f"parse error: {e}", "raw": r["stdout"][:500]}


def _parse_fps(rate_str: str) -> float:
    try:
        n, d = rate_str.split("/")
        return round(int(n) / int(d), 2) if int(d) else 0.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Conversión
# ---------------------------------------------------------------------------
def convert(
    input_path: str,
    output_path: str,
    *,
    format: str = "mp4",
    codec: str = "libx264",
    crf: int = 23,
    preset: str = "medium",
    audio_codec: str = "aac",
    audio_bitrate: str = "192k",
    resolution: Optional[str] = None,
    fps: Optional[float] = None,
) -> Dict[str, Any]:
    """Conversión profesional con control fino."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    input_path = _resolve(input_path)
    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [_ffmpeg_bin(), "-y", "-i", input_path, "-c:v", codec, "-crf", str(crf), "-preset", preset,
           "-c:a", audio_codec, "-b:a", audio_bitrate]
    if resolution:
        cmd += ["-vf", f"scale={resolution}"]
    if fps:
        cmd += ["-r", str(fps)]
    cmd += ["-movflags", "+faststart", output_path]

    r = _run(cmd, timeout=1800)
    r["output"] = output_path
    return r


# ---------------------------------------------------------------------------
# Thumbnails
# ---------------------------------------------------------------------------
def thumbnail(input_path: str, output_path: str, *, time_s: float = 1.0, width: int = 320) -> Dict[str, Any]:
    """Extrae un thumbnail en un momento dado."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    input_path = _resolve(input_path)
    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    return _run([_ffmpeg_bin(), "-y", "-ss", str(time_s), "-i", input_path, "-vframes", "1",
                 "-vf", f"scale={width}:-1", output_path])


def thumbnail_grid(
    input_path: str,
    output_path: str,
    *,
    cols: int = 3,
    rows: int = 3,
    width: int = 320,
    quality: int = 2,
) -> Dict[str, Any]:
    """Genera un grid de NxM thumbnails equiespaciados."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    info = probe(input_path)
    if not info["ok"]:
        return info
    duration = info["duration_s"]
    if duration <= 0:
        return {"ok": False, "error": "duración desconocida"}
    total = cols * rows
    fps_extract = total / duration
    input_path = _resolve(input_path)
    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [_ffmpeg_bin(), "-y", "-i", input_path,
           "-vf", f"fps={fps_extract},scale={width}:-1,tile={cols}x{rows}",
           "-frames:v", "1", "-q:v", str(quality), output_path]
    return _run(cmd)


# ---------------------------------------------------------------------------
# Efectos avanzados
# ---------------------------------------------------------------------------
def blur_background(input_path: str, output_path: str, *, strength: int = 20) -> Dict[str, Any]:
    """Aplica blur al fondo manteniendo el sujeto nítido (modo retrato). Requiere modelo de segmentación (advanced)."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    # Implementación simple: blur a los bordes
    filter_complex = (
        f"[0:v]split[orig][copy];"
        f"[copy]boxblur={strength}:1[blur];"
        f"[orig][blur]overlay=(W-w)/2:(H-h)/2:enable='lt(mod(t\\,4)\\,2)'"
    )
    return _run([_ffmpeg_bin(), "-y", "-i", input_path, "-filter_complex", filter_complex,
                 "-c:a", "copy", output_path])


def stabilize(input_path: str, output_path: str, *, shakiness: int = 5, accuracy: int = 9) -> Dict[str, Any]:
    """Estabilización de video con vidstab (requiere libvidstab)."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    # Dos pasadas: análisis + aplicación
    trf = output_path + ".trf"
    pass1 = _run([_ffmpeg_bin(), "-y", "-i", input_path, "-vf",
                  f"vidstabdetect=shakiness={shakiness}:accuracy={accuracy}:result={trf}",
                  "-f", "null", "-"], timeout=600)
    if not pass1["ok"]:
        return {"ok": False, "error": "vidstabdetect falló", "details": pass1}
    pass2 = _run([_ffmpeg_bin(), "-y", "-i", input_path, "-vf",
                  f"vidstabtransform=input={trf}:zoom=0:smoothing=30,unsharp=5:5:0.8:3:3:0.4",
                  "-c:a", "copy", output_path], timeout=1800)
    if os.path.exists(trf):
        os.remove(trf)
    return pass2


def reverse(input_path: str, output_path: str, *, video_reverse: bool = True, audio_reverse: bool = True) -> Dict[str, Any]:
    """Invierte el video (y opcionalmente el audio)."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    vf = "reverse" if video_reverse else None
    af = "areverse" if audio_reverse else None
    cmd = [_ffmpeg_bin(), "-y", "-i", input_path]
    if vf and af:
        cmd += ["-vf", vf, "-af", af]
    elif vf:
        cmd += ["-vf", vf, "-c:a", "copy"]
    elif af:
        cmd += ["-af", af, "-c:v", "copy"]
    cmd += [output_path]
    return _run(cmd)


def slow_motion(input_path: str, output_path: str, *, speed: float = 0.5) -> Dict[str, Any]:
    """Slow motion (speed entre 0.25 y 1.0). Ajusta video y audio."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    if not 0.1 <= speed <= 2.0:
        return {"ok": False, "error": "speed debe estar entre 0.1 y 2.0"}
    # atempo acepta 0.5-2.0
    if 0.5 <= speed <= 2.0:
        atempo = speed
    else:
        # encadenar atempos
        atempo = f"atempo={speed}"
    return _run([_ffmpeg_bin(), "-y", "-i", input_path,
                 "-filter_complex", f"[0:v]setpts={1/speed}*PTS[v];[0:a]{atempo}[a]",
                 "-map", "[v]", "-map", "[a]", output_path])


def time_lapse(input_path: str, output_path: str, *, speed: float = 4.0) -> Dict[str, Any]:
    """Time-lapse (speed > 1.0)."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    if not 1.0 <= speed <= 10.0:
        return {"ok": False, "error": "speed debe estar entre 1.0 y 10.0"}
    atempo_filter = ",".join([f"atempo={min(2.0, speed)}"] * int(speed / 2)) if speed > 2.0 else f"atempo={speed}"
    return _run([_ffmpeg_bin(), "-y", "-i", input_path,
                 "-filter_complex", f"[0:v]setpts={1/speed}*PTS[v];[0:a]{atempo_filter}[a]",
                 "-map", "[v]", "-map", "[a]", output_path])


# ---------------------------------------------------------------------------
# Composición
# ---------------------------------------------------------------------------
def picture_in_picture(
    main_path: str,
    overlay_path: str,
    output_path: str,
    *,
    overlay_position: str = "top-right",  # top-left, top-right, bottom-left, bottom-right
    overlay_scale: float = 0.25,
    overlay_margin: int = 20,
) -> Dict[str, Any]:
    """Compone un video PiP (overlay sobre main)."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    pos_map = {
        "top-left": f"{overlay_margin}:{overlay_margin}",
        "top-right": f"W-w-{overlay_margin}:{overlay_margin}",
        "bottom-left": f"{overlay_margin}:H-h-{overlay_margin}",
        "bottom-right": f"W-w-{overlay_margin}:H-h-{overlay_margin}",
    }
    pos = pos_map.get(overlay_position, pos_map["top-right"])
    filter_complex = (
        f"[1:v]scale=iw*{overlay_scale}:ih*{overlay_scale}[ovl];"
        f"[0:v][ovl]overlay={pos}"
    )
    return _run([_ffmpeg_bin(), "-y", "-i", main_path, "-i", overlay_path,
                 "-filter_complex", filter_complex, "-c:a", "copy", output_path])


def side_by_side(left_path: str, right_path: str, output_path: str, *, audio_source: str = "left") -> Dict[str, Any]:
    """Pone dos videos lado a lado."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    audio_map = "0:a" if audio_source == "left" else "1:a"
    return _run([_ffmpeg_bin(), "-y", "-i", left_path, "-i", right_path,
                 "-filter_complex", "[0:v]scale=iw/2:ih/2[left];[1:v]scale=iw/2:ih/2[right];[left][right]hstack=inputs=2",
                 "-map", audio_map, "-c:a", "aac", output_path])


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
def normalize_audio(input_path: str, output_path: str, *, target_lufs: float = -14.0) -> Dict[str, Any]:
    """Normaliza audio a un loudness target (EBU R128)."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    return _run([_ffmpeg_bin(), "-y", "-i", input_path,
                 "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                 "-c:v", "copy", output_path])


def remove_audio(input_path: str, output_path: str) -> Dict[str, Any]:
    """Quita la pista de audio."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    return _run([_ffmpeg_bin(), "-y", "-i", input_path, "-an", "-c:v", "copy", output_path])


def extract_audio(input_path: str, output_path: str, *, format: str = "mp3", bitrate: str = "192k") -> Dict[str, Any]:
    """Extrae audio a un archivo separado."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    return _run([_ffmpeg_bin(), "-y", "-i", input_path, "-vn", "-c:a", "libmp3lame" if format == "mp3" else format,
                 "-b:a", bitrate, output_path])


# ---------------------------------------------------------------------------
# GIF
# ---------------------------------------------------------------------------
def make_gif(input_path: str, output_path: str, *, start_s: float = 0, duration_s: float = 5, fps: int = 15, width: int = 480) -> Dict[str, Any]:
    """Convierte un片段 a GIF optimizado."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    palette = output_path + ".palette.png"
    pass1 = _run([_ffmpeg_bin(), "-y", "-ss", str(start_s), "-t", str(duration_s), "-i", input_path,
                  "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,palettegen=stats_mode=diff", palette])
    if not pass1["ok"]:
        return pass1
    pass2 = _run([_ffmpeg_bin(), "-y", "-ss", str(start_s), "-t", str(duration_s), "-i", input_path, "-i", palette,
                  "-filter_complex", f"fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
                  output_path])
    if os.path.exists(palette):
        os.remove(palette)
    return pass2


# ---------------------------------------------------------------------------
# Watermark
# ---------------------------------------------------------------------------
def add_watermark(input_path: str, image_path: str, output_path: str, *, position: str = "bottom-right", opacity: float = 0.7, scale: float = 0.15) -> Dict[str, Any]:
    """Añade un watermark de imagen al video."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    pos_map = {
        "top-left": "20:20",
        "top-right": "W-w-20:20",
        "bottom-left": "20:H-h-20",
        "bottom-right": "W-w-20:H-h-20",
        "center": "(W-w)/2:(H-h)/2",
    }
    pos = pos_map.get(position, pos_map["bottom-right"])
    return _run([_ffmpeg_bin(), "-y", "-i", input_path, "-i", image_path,
                 "-filter_complex", f"[1:v]scale=iw*{scale}:-1,format=rgba,colorchannelmixer=aa={opacity}[wm];[0:v][wm]overlay={pos}",
                 "-c:a", "copy", output_path])


# ---------------------------------------------------------------------------
# Export presets para redes sociales
# ---------------------------------------------------------------------------
PRESETS = {
    "tiktok": {"width": 1080, "height": 1920, "fps": 30, "crf": 20, "max_duration_s": 60},
    "reels": {"width": 1080, "height": 1920, "fps": 30, "crf": 20, "max_duration_s": 90},
    "shorts": {"width": 1080, "height": 1920, "fps": 30, "crf": 20, "max_duration_s": 60},
    "youtube": {"width": 1920, "height": 1080, "fps": 30, "crf": 20, "max_duration_s": 900},
    "youtube_shorts": {"width": 1080, "height": 1920, "fps": 30, "crf": 20, "max_duration_s": 60},
    "twitter": {"width": 1280, "height": 720, "fps": 30, "crf": 21, "max_duration_s": 140},
    "instagram_feed": {"width": 1080, "height": 1080, "fps": 30, "crf": 20, "max_duration_s": 60},
    "linkedin": {"width": 1920, "height": 1080, "fps": 30, "crf": 22, "max_duration_s": 600},
    "facebook": {"width": 1280, "height": 720, "fps": 30, "crf": 22, "max_duration_s": 240},
}


def export_for_platform(input_path: str, output_path: str, platform: str = "tiktok", *, crf: Optional[int] = None) -> Dict[str, Any]:
    """Exporta video optimizado para una red social."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    preset = PRESETS.get(platform.lower())
    if not preset:
        return {"ok": False, "error": f"plataforma no soportada: {platform}. Opciones: {list(PRESETS.keys())}"}
    w, h, fps, default_crf, max_dur = preset["width"], preset["height"], preset["fps"], preset["crf"], preset["max_duration_s"]
    crf = crf or default_crf

    # Crop al aspect ratio del preset (center crop)
    filter_str = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}"
    return _run([_ffmpeg_bin(), "-y", "-i", input_path, "-vf", filter_str,
                 "-c:v", "libx264", "-crf", str(crf), "-preset", "fast",
                 "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                 "-t", str(max_dur), output_path])


# ---------------------------------------------------------------------------
# Detección de escenas
# ---------------------------------------------------------------------------
def detect_scenes(input_path: str, *, threshold: float = 0.4, output_json: Optional[str] = None) -> Dict[str, Any]:
    """Detecta cambios de escena (usa ffmpeg scene change detection)."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    # ffmpeg scene detection imprime "pts_time:HMS" por cada corte
    cmd = [_ffmpeg_bin(), "-i", input_path, "-filter:v", f"select='gt(scene,{threshold})',showinfo",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
    output = r.stderr
    scenes = []
    for line in output.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            scenes.append({"timestamp_s": float(m.group(1)), "human": _fmt_time(float(m.group(1)))})

    result = {"ok": True, "scene_count": len(scenes), "scenes": scenes}
    if output_json:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(output_json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        result["saved_to"] = output_json
    return result


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


# ---------------------------------------------------------------------------
# Concat avanzado
# ---------------------------------------------------------------------------
def concat_videos(video_paths: List[str], output_path: str, *, transitions: bool = False, transition_duration: float = 0.5) -> Dict[str, Any]:
    """Une múltiples videos en uno. Si transitions=True, usa xfade entre ellos."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    if not video_paths:
        return {"ok": False, "error": "no hay videos"}
    if len(video_paths) == 1:
        shutil.copy(video_paths[0], output_path)
        return {"ok": True, "output": output_path, "method": "single_copy"}

    if not transitions:
        # Método simple: concat demuxer (requiere mismo codec/resolución)
        list_file = output_path + ".list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for vp in video_paths:
                f.write(f"file '{os.path.abspath(vp)}'\n")
        r = _run([_ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path])
        if os.path.exists(list_file):
            os.remove(list_file)
        return r

    # Con transiciones: encadenar xfade
    inputs = []
    for vp in video_paths:
        inputs += ["-i", vp]
    n = len(video_paths)

    # Construir filter_complex con xfade chain
    parts = []
    for i in range(n):
        parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}];[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

    # Chain xfade
    last_v = "v0"
    last_a = "a0"
    cumulative = 0.0
    for i in range(1, n):
        cumulative += transition_duration
        out_v = f"vx{i}"
        parts.append(f"[{last_v}][v{i}]xfade=transition=fade:duration={transition_duration}:offset={cumulative}[{out_v}]")
        parts.append(f"[{last_a}][a{i}]acrossfade=d={transition_duration}[ax{i}]")
        last_v = out_v
        last_a = f"ax{i}"

    parts.append(f"[{last_v}][{last_a}]concat=n=1:v=1:a=1[outv][outa]")
    filter_complex = ";\n".join(parts)

    cmd = [_ffmpeg_bin(), "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[outv]", "-map", "[outa]",
                                            "-c:v", "libx264", "-crf", "20", "-preset", "fast", output_path]
    return _run(cmd, timeout=3600)


# ---------------------------------------------------------------------------
# Análisis de calidad
# ---------------------------------------------------------------------------
def analyze_quality(reference_path: str, distorted_path: str) -> Dict[str, Any]:
    """Compara dos videos (PSNR + SSIM). Útil para validar encoding."""
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado"}
    cmd = [_ffmpeg_bin(), "-i", reference_path, "-i", distorted_path,
           "-lavfi", "psnr=stats_file=-;ssim=stats_file=-",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace")
    output = r.stderr
    psnr_m = re.search(r"psnr_avg:([\d.]+)", output)
    ssim_m = re.search(r"SSIM Y:([\d.]+)", output)
    return {
        "ok": r.returncode == 0,
        "psnr_db": float(psnr_m.group(1)) if psnr_m else None,
        "ssim": float(ssim_m.group(1)) if ssim_m else None,
        "interpretation": _interpret_quality(
            float(psnr_m.group(1)) if psnr_m else None,
            float(ssim_m.group(1)) if ssim_m else None,
        ),
    }


def _interpret_quality(psnr: Optional[float], ssim: Optional[float]) -> str:
    out = []
    if psnr is not None:
        if psnr > 40:
            out.append(f"PSNR {psnr:.2f} dB = excelente")
        elif psnr > 30:
            out.append(f"PSNR {psnr:.2f} dB = bueno")
        elif psnr > 20:
            out.append(f"PSNR {psnr:.2f} dB = aceptable")
        else:
            out.append(f"PSNR {psnr:.2f} dB = pobre")
    if ssim is not None:
        if ssim > 0.95:
            out.append(f"SSIM {ssim:.4f} = casi idéntico")
        elif ssim > 0.8:
            out.append(f"SSIM {ssim:.4f} = diferencias menores")
        else:
            out.append(f"SSIM {ssim:.4f} = diferencias notables")
    return "  |  ".join(out) if out else "sin métricas"


# ===========================================================================
# GENERADORES DE VIDEO DESDE CERO (intros, promos, slideshows)
# ===========================================================================

def _check_ffmpeg_or_error() -> Dict[str, Any]:
    if not _check_ffmpeg():
        return {"ok": False, "error": "ffmpeg no instalado. Instala con: choco install ffmpeg / apt install ffmpeg / brew install ffmpeg"}
    return {"ok": True}


def _check_matte_or_error() -> Dict[str, Any]:
    if not MATPLOTLIB_AVAILABLE:
        return {"ok": False, "error": "matplotlib no instalado (pip install matplotlib)"}
    return {"ok": True}


def _render_text_overlay(
    text: str,
    output_image: str,
    *,
    width: int = 1920,
    height: int = 1080,
    font_size: int = 80,
    font_color: str = "white",
    bg_color: Optional[str] = None,
    font_path: Optional[str] = None,
    align: str = "center",
    bold: bool = True,
) -> Dict[str, Any]:
    """Renderiza texto como imagen PNG con tipografía configurable."""
    chk = _check_matte_or_error()
    if not chk["ok"]:
        return chk
    try:
        from PIL import Image, ImageDraw, ImageFont
        if bg_color:
            img = Image.new("RGB", (width, height), bg_color)
        else:
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            try:
                font = ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if align == "center":
            x = (width - tw) // 2
        elif align == "right":
            x = width - tw - 50
        else:
            x = 50
        y = (height - th) // 2
        draw.text((x, y), text, fill=font_color, font=font)
        img.save(output_image, "PNG")
        return {"ok": True, "image": output_image, "width": width, "height": height}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Intro animada
# ---------------------------------------------------------------------------
def intro(
    output_path: str,
    *,
    title: str = "AUTOMYX",
    subtitle: str = "",
    duration_s: float = 5.0,
    style: str = "modern",  # modern, cinematic, glitch, neon, minimal
    bg_color: str = "#0B0B1A",
    text_color: str = "white",
    accent_color: str = "#00F0FF",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    music_path: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Genera una INTRO animada profesional con título + subtítulo.
    Estilos:
      - modern:    texto con fade-in + scale + color highlight
      - cinematic: bars cinematográficas + texto centrado con glow
      - glitch:    efecto de interferencia estilo cyberpunk
      - neon:      texto neón con resplandor
      - minimal:   solo texto en negro con fade limpio
    """
    chk = _check_ffmpeg_or_error()
    if not chk["ok"]:
        return chk
    if not MATPLOTLIB_AVAILABLE:
        return {"ok": False, "error": "matplotlib requerido para intros"}

    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    w = output_width or width
    h = output_height or height

    # Generar frames PNG con matplotlib
    tmp = Path(os.path.dirname(output_path)) / f"_intro_tmp_{int(time.time()*1000)}"
    tmp.mkdir(parents=True, exist_ok=True)

    total_frames = int(duration_s * fps)
    print(f"[INTRO] Generando {total_frames} frames @ {fps}fps...")

    for i in range(total_frames):
        progress = i / max(1, total_frames - 1)
        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        if style == "modern":
            # Texto con scale + fade-in
            scale = 0.6 + 0.4 * min(1.0, progress * 2.5)
            alpha = min(1.0, progress * 2.5)
            ax.text(0.5, 0.55, title, fontsize=80 * scale, color=text_color,
                    ha="center", va="center", fontweight="bold", alpha=alpha)
            if subtitle:
                ax.text(0.5, 0.40, subtitle, fontsize=30, color=accent_color,
                        ha="center", va="center", alpha=max(0, min(1, (progress - 0.4) * 2.5)))
            # Línea decorativa
            line_y = 0.32
            line_w = 0.0 + 0.6 * min(1.0, progress * 2.0)
            ax.plot([0.5 - line_w/2, 0.5 + line_w/2], [line_y, line_y], color=accent_color, linewidth=3, alpha=alpha)

        elif style == "cinematic":
            # Barras cinematográficas
            bar_h = 0.08
            ax.add_patch(plt.Rectangle((0, 0), 1, bar_h, color="black"))
            ax.add_patch(plt.Rectangle((0, 1 - bar_h), 1, bar_h, color="black"))
            # Texto con glow
            scale = 0.5 + 0.5 * min(1.0, progress * 2.0)
            for dx, dy, alpha_g in [(0, 0, 0.3), (0.003, 0.003, 0.2), (-0.003, -0.003, 0.2)]:
                ax.text(0.5 + dx, 0.5 + dy, title, fontsize=70 * scale, color=accent_color,
                        ha="center", va="center", fontweight="bold", alpha=alpha_g * min(1, progress * 2))
            ax.text(0.5, 0.5, title, fontsize=70 * scale, color=text_color,
                    ha="center", va="center", fontweight="bold", alpha=min(1, progress * 2))
            if subtitle:
                ax.text(0.5, 0.38, subtitle, fontsize=24, color=text_color,
                        ha="center", va="center", alpha=max(0, min(1, (progress - 0.3) * 2)))

        elif style == "glitch":
            # Glitch: texto duplicado con offset RGB
            for j, (color, off_x, off_y) in enumerate([("#FF003C", -0.005, 0), ("#00F0FF", 0.005, 0), (text_color, 0, 0)]):
                ax.text(0.5 + off_x, 0.5 + off_y, title, fontsize=72,
                        color=color, ha="center", va="center", fontweight="bold",
                        alpha=min(1, progress * 1.5) * (1.0 if j == 2 else 0.6))
            if subtitle:
                ax.text(0.5, 0.40, subtitle, fontsize=24, color=accent_color,
                        ha="center", va="center", alpha=max(0, min(1, (progress - 0.4) * 2)))
            # Scanlines
            for k in range(0, h, 4):
                ax.axhline(y=k / h, color=accent_color, alpha=0.03, linewidth=0.5)

        elif style == "neon":
            # Neon: glow multi-layer
            for r in [40, 30, 20, 10]:
                ax.text(0.5, 0.5, title, fontsize=72, color=accent_color,
                        ha="center", va="center", fontweight="bold", alpha=0.2)
            ax.text(0.5, 0.5, title, fontsize=72, color=text_color,
                    ha="center", va="center", fontweight="bold", alpha=min(1, progress * 2))
            if subtitle:
                ax.text(0.5, 0.40, subtitle, fontsize=24, color=accent_color,
                        ha="center", va="center", alpha=max(0, min(1, (progress - 0.3) * 2)))

        elif style == "minimal":
            ax.text(0.5, 0.55, title, fontsize=60, color=text_color,
                    ha="center", va="center", fontweight="light", alpha=min(1, progress * 1.5))
            if subtitle:
                ax.text(0.5, 0.42, subtitle, fontsize=20, color=text_color,
                        ha="center", va="center", alpha=max(0, min(1, (progress - 0.4) * 2)))

        frame_path = tmp / f"frame_{i:05d}.png"
        plt.savefig(frame_path, facecolor=bg_color, dpi=100, bbox_inches="tight", pad_inches=0)
        plt.close()

    # Ensamblar con ffmpeg
    cmd = [_ffmpeg_bin(), "-y", "-framerate", str(fps),
           "-i", str(tmp / "frame_%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "fast"]
    if music_path and os.path.exists(music_path):
        cmd += ["-i", music_path, "-c:a", "aac", "-shortest"]
    cmd += [output_path]
    r = _run(cmd, timeout=300)

    # Cleanup
    for f in tmp.glob("frame_*.png"):
        f.unlink()
    tmp.rmdir()

    r["output"] = output_path
    r["style"] = style
    r["duration_s"] = duration_s
    r["frames"] = total_frames
    return r


# ---------------------------------------------------------------------------
# Lower third / banner animado
# ---------------------------------------------------------------------------
def lower_third(
    input_path: str,
    output_path: str,
    *,
    title: str = "",
    subtitle: str = "",
    start_s: float = 0.0,
    duration_s: float = 4.0,
    position: str = "bottom",  # bottom, top, center
    bg_color: str = "#0B3D91@0.9",
    text_color: str = "white",
    accent_color: str = "#00F0FF",
) -> Dict[str, Any]:
    """Añade un banner/lower-third animado a un video existente."""
    chk = _check_ffmpeg_or_error()
    if not chk["ok"]:
        return chk
    input_path = _resolve(input_path)
    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    pos_y = {"bottom": "h*0.78", "center": "(h-text_h)/2", "top": "h*0.05"}[position]
    alpha = "1" if "0.9" in bg_color else "0.8"

    # Crear overlay PNG con el banner
    banner_path = output_path + "_banner.png"
    try:
        from PIL import Image, ImageDraw, ImageFont
        w, h = 1920, 240
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Fondo
        rgb = tuple(int(bg_color.split("@")[0].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        draw.rectangle([0, 0, w, h], fill=(*rgb, int(255 * float(alpha))))
        # Barra accent
        accent_rgb = tuple(int(accent_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        draw.rectangle([0, 0, 8, h], fill=(*accent_rgb, 255))
        # Textos
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 56)
            font_sub = ImageFont.truetype("arial.ttf", 32)
        except OSError:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
        draw.text((40, 60), title, fill=text_color, font=font_title)
        if subtitle:
            draw.text((40, 150), subtitle, fill=accent_color, font=font_sub)
        img.save(banner_path, "PNG")
    except Exception as e:
        return {"ok": False, "error": f"PIL error: {e}"}

    cmd = [_ffmpeg_bin(), "-y", "-i", input_path, "-i", banner_path,
           "-filter_complex",
           f"[1:v]format=rgba[lt];"
           f"[0:v][lt]overlay=0:H*{pos_y.split('*')[0] if '*' in pos_y else '0'}:"
           f"enable='between(t,{start_s},{start_s+duration_s})'",
           "-c:a", "copy", output_path]
    r = _run(cmd)
    if os.path.exists(banner_path):
        os.remove(banner_path)
    r["output"] = output_path
    return r


# ---------------------------------------------------------------------------
# Promo / anuncio publicitario
# ---------------------------------------------------------------------------
def promo(
    output_path: str,
    *,
    title: str,
    tagline: str = "",
    cta: str = "",  # call to action: "Visítanos en..."
    bullets: Optional[List[str]] = None,
    duration_s: float = 15.0,
    style: str = "dynamic",  # dynamic, elegant, energetic
    bg_color: str = "#0B0B1A",
    accent_color: str = "#00F0FF",
    text_color: str = "white",
    music_path: Optional[str] = None,
    output_width: int = 1920,
    output_height: int = 1080,
    fps: int = 30,
) -> Dict[str, Any]:
    """
    Genera un VIDEO PROMOCIONAL desde cero con:
    - Título con animación dramática
    - Bullets con reveal secuencial
    - CTA al final
    - Música opcional
    """
    chk = _check_ffmpeg_or_error()
    if not chk["ok"]:
        return chk
    if not MATPLOTLIB_AVAILABLE:
        return {"ok": False, "error": "matplotlib requerido para promos"}

    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    w, h = output_width, output_height
    bullets = bullets or []

    # Fase: 0-0.2 título, 0.2-0.7 bullets, 0.7-1.0 CTA
    total_frames = int(duration_s * fps)
    tmp = Path(os.path.dirname(output_path)) / f"_promo_tmp_{int(time.time()*1000)}"
    tmp.mkdir(parents=True, exist_ok=True)

    print(f"[PROMO] Generando {total_frames} frames @ {fps}fps...")

    accent_rgb = tuple(int(accent_color.lstrip("#")[i:i+2], 16) / 255 for i in (0, 2, 4))

    for i in range(total_frames):
        progress = i / max(1, total_frames - 1)
        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        if style == "dynamic":
            # Fondo con gradiente diagonal animado
            for j in range(20):
                alpha = 0.02 + 0.02 * abs(((progress * 5 + j / 20) % 1) - 0.5)
                ax.plot([0, 1], [j/20 + 0.02 * (progress * 3 % 1), j/20 + 0.02 * (progress * 3 % 1)],
                        color=accent_color, alpha=alpha, linewidth=2)
        elif style == "elegant":
            # Centro con spotlight radial
            for r in np.linspace(0.5, 0.0, 10):
                alpha = 0.08 * (1 - r * 2)
                circle = plt.Circle((0.5, 0.5), r, color=accent_color, alpha=max(0, alpha))
                ax.add_patch(circle)

        if progress < 0.25:
            # Fase 1: título dramático
            t_prog = progress / 0.25
            scale = 0.4 + 0.6 * min(1.0, t_prog * 1.5)
            ax.text(0.5, 0.55, title, fontsize=72 * scale, color=text_color,
                    ha="center", va="center", fontweight="bold",
                    alpha=min(1.0, t_prog * 2))
            if tagline:
                ax.text(0.5, 0.40, tagline, fontsize=24, color=accent_color,
                        ha="center", va="center", alpha=max(0, min(1, (t_prog - 0.5) * 2)))

        elif progress < 0.75 and bullets:
            # Fase 2: bullets secuenciales
            t_prog = (progress - 0.25) / 0.50
            bullet_idx = int(t_prog * len(bullets))
            if bullet_idx >= len(bullets):
                bullet_idx = len(bullets) - 1
            # Título pequeño arriba
            ax.text(0.5, 0.85, title, fontsize=24, color=accent_color,
                    ha="center", va="center", fontweight="bold", alpha=0.6)
            # Bullet actual con animación
            bullet = bullets[bullet_idx]
            ax.text(0.5, 0.50, f"• {bullet}", fontsize=44, color=text_color,
                    ha="center", va="center", fontweight="normal",
                    alpha=min(1.0, (t_prog * len(bullets) - bullet_idx) * 2.5))
            # Indicador de progreso
            for k in range(len(bullets)):
                if k == bullet_idx:
                    color, alpha_d, size = accent_color, 1.0, 14
                else:
                    color, alpha_d, size = text_color, 0.3, 8
                ax.plot(0.3 + k * 0.4 / max(1, len(bullets) - 1), 0.20, "o",
                        color=color, alpha=alpha_d, markersize=size)

        else:
            # Fase 3: CTA
            t_prog = (progress - 0.75) / 0.25
            ax.text(0.5, 0.65, title, fontsize=20, color=accent_color,
                    ha="center", va="center", fontweight="bold", alpha=0.7)
            if cta:
                scale = 0.7 + 0.3 * min(1.0, t_prog * 2)
                ax.text(0.5, 0.45, cta, fontsize=44 * scale, color=text_color,
                        ha="center", va="center", fontweight="bold",
                        alpha=min(1.0, t_prog * 2))
                # Recuadro alrededor del CTA
                box_w = 0.5 * min(1.0, t_prog * 1.5)
                box_h = 0.15
                ax.add_patch(plt.Rectangle((0.5 - box_w/2, 0.45 - box_h/2), box_w, box_h,
                                            fill=False, edgecolor=accent_color, linewidth=2,
                                            alpha=min(1.0, t_prog * 1.5)))

        frame_path = tmp / f"frame_{i:05d}.png"
        plt.savefig(frame_path, facecolor=bg_color, dpi=100, bbox_inches="tight", pad_inches=0)
        plt.close()

    cmd = [_ffmpeg_bin(), "-y", "-framerate", str(fps),
           "-i", str(tmp / "frame_%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "fast"]
    if music_path and os.path.exists(music_path):
        # Loopear música si es más corta
        cmd += ["-stream_loop", "-1", "-i", music_path, "-c:a", "aac", "-shortest"]
    cmd += [output_path]
    r = _run(cmd, timeout=600)

    for f in tmp.glob("frame_*.png"):
        f.unlink()
    tmp.rmdir()

    r["output"] = output_path
    r["duration_s"] = duration_s
    r["style"] = style
    r["bullets"] = len(bullets)
    return r


# ---------------------------------------------------------------------------
# Joiner / Merge con transiciones animadas
# ---------------------------------------------------------------------------
def join_with_transitions(
    video_paths: List[str],
    output_path: str,
    *,
    transition: str = "fade",  # fade, slide-left, slide-right, slide-up, zoom, blur, glitch, swirl
    transition_duration: float = 0.8,
    add_intro: bool = False,
    intro_title: str = "",
    add_outro: bool = False,
    outro_text: str = "",
    music_path: Optional[str] = None,
    target_resolution: Optional[str] = "1920x1080",
) -> Dict[str, Any]:
    """
    Une múltiples videos con transiciones cinematográficas.
    Genera clips con crossfade/zoom/blur/glitch.
    Opcionalmente añade intro y outro.
    """
    chk = _check_ffmpeg_or_error()
    if not chk["ok"]:
        return chk
    if not video_paths:
        return {"ok": False, "error": "video_paths vacío"}
    if len(video_paths) == 1:
        # Solo copiar
        import shutil as sh
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sh.copy(video_paths[0], output_path)
        return {"ok": True, "output": output_path, "method": "single_copy"}

    resolved = [_resolve(p) for p in video_paths]
    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 1) Normalizar todos al mismo tamaño y fps
    norm_dir = Path(os.path.dirname(output_path)) / f"_norm_{int(time.time()*1000)}"
    norm_dir.mkdir(parents=True, exist_ok=True)
    norm_paths = []
    target_res = target_resolution or "1920x1080"

    for i, vp in enumerate(resolved):
        norm_path = norm_dir / f"norm_{i:03d}.mp4"
        cmd = [_ffmpeg_bin(), "-y", "-i", vp,
               "-vf", f"scale={target_res.replace('x', ':')}:force_original_aspect_ratio=increase,"
                      f"crop={target_res.replace('x', ':')},fps=30",
               "-c:v", "libx264", "-crf", "20", "-preset", "fast",
               "-c:a", "aac", "-ar", "48000",
               str(norm_path)]
        r = _run(cmd, timeout=600)
        if not r["ok"]:
            for f in norm_dir.glob("*.mp4"):
                f.unlink()
            norm_dir.rmdir()
            return {"ok": False, "error": f"normalize falló en {vp}: {r.get('error', r.get('stderr', ''))[:200]}"}
        norm_paths.append(str(norm_path))

    # 2) Construir filter_complex con xfade + acrossfade
    inputs_args = []
    for np_ in norm_paths:
        inputs_args += ["-i", np_]

    # Obtener duraciones
    durations = []
    for np_ in norm_paths:
        info = probe(np_)
        durations.append(info.get("duration_s", 5) if info["ok"] else 5)

    # Construir chain xfade
    n = len(norm_paths)
    filter_parts = []
    for i in range(n):
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
        filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

    last_v = "v0"
    last_a = "a0"
    offset = durations[0] - transition_duration
    for i in range(1, n):
        new_v = f"vx{i}"
        new_a = f"ax{i}"
        filter_parts.append(f"[{last_v}][v{i}]xfade=transition={transition}:duration={transition_duration}:offset={offset}[{new_v}]")
        filter_parts.append(f"[{last_a}][a{i}]acrossfade=d={transition_duration}[{new_a}]")
        last_v = new_v
        last_a = new_a
        if i < n - 1:
            offset += durations[i] - transition_duration

    filter_parts.append(f"[{last_v}][{last_a}]concat=n=1:v=1:a=1[outv][outa]")
    filter_complex = ";\n".join(filter_parts)

    tmp_merged = norm_dir / "merged.mp4"
    cmd = [_ffmpeg_bin(), "-y"] + inputs_args + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac",
        str(tmp_merged)
    ]
    r = _run(cmd, timeout=1800)
    if not r["ok"]:
        for f in norm_dir.glob("*"):
            f.unlink()
        norm_dir.rmdir()
        return {"ok": False, "error": f"xfade chain falló: {r.get('stderr', '')[:300]}"}

    # 3) Concatenar con intro/outro
    pieces = []
    if add_intro and intro_title:
        intro_path = str(norm_dir / "intro.mp4")
        ir = intro(intro_path, title=intro_title, duration_s=3.0, style="modern",
                   output_width=int(target_resolution.split("x")[0]),
                   output_height=int(target_resolution.split("x")[1]))
        if ir["ok"]:
            pieces.append(intro_path)
    pieces.append(str(tmp_merged))
    if add_outro and outro_text:
        outro_path = str(norm_dir / "outro.mp4")
        or_ = intro(outro_path, title=outro_text, duration_s=3.0, style="minimal",
                    output_width=int(target_resolution.split("x")[0]),
                    output_height=int(target_resolution.split("x")[1]))
        if or_["ok"]:
            pieces.append(outro_path)

    final_cmd = [_ffmpeg_bin(), "-y"]
    for p in pieces:
        final_cmd += ["-i", p]
    if len(pieces) > 1:
        concat_filter = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(len(pieces)))
        final_cmd += ["-filter_complex", f"{concat_filter}concat=n={len(pieces)}:v=1:a=1[outv][outa]",
                      "-map", "[outv]", "-map", "[outa]"]
    else:
        final_cmd += ["-map", "0:v", "-map", "0:a"]
    final_cmd += ["-c:v", "libx264", "-crf", "20", "-preset", "fast", "-c:a", "aac"]
    if music_path and os.path.exists(music_path):
        final_cmd += ["-i", music_path, "-map", f"{len(pieces)}:a", "-c:a", "aac", "-shortest"]
    final_cmd += [output_path]

    r = _run(final_cmd, timeout=1800)
    for f in norm_dir.glob("*"):
        try:
            f.unlink()
        except Exception:
            pass
    norm_dir.rmdir()

    r["output"] = output_path
    r["transition"] = transition
    r["videos_joined"] = len(video_paths)
    r["added_intro"] = add_intro
    r["added_outro"] = add_outro
    return r


# ---------------------------------------------------------------------------
# Slideshow desde imágenes con transiciones
# ---------------------------------------------------------------------------
def slideshow(
    image_paths: List[str],
    output_path: str,
    *,
    duration_per_image: float = 4.0,
    transition: str = "fade",
    transition_duration: float = 0.5,
    title: str = "",
    music_path: Optional[str] = None,
    target_resolution: str = "1920x1080",
    fps: int = 30,
) -> Dict[str, Any]:
    """
    Genera un slideshow a partir de imágenes con transiciones + música.
    Cada imagen se muestra durante duration_per_image segundos.
    """
    chk = _check_ffmpeg_or_error()
    if not chk["ok"]:
        return chk
    if not image_paths:
        return {"ok": False, "error": "image_paths vacío"}

    output_path = _resolve(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    w, h = target_resolution.split("x")
    duration = max(1.0, duration_per_image)

    # Crear clips individuales desde cada imagen
    tmp = Path(os.path.dirname(output_path)) / f"_slideshow_{int(time.time()*1000)}"
    tmp.mkdir(parents=True, exist_ok=True)
    clip_paths = []
    for i, img in enumerate(image_paths):
        if not os.path.exists(img):
            continue
        clip_path = tmp / f"clip_{i:03d}.mp4"
        # Cada imagen como clip de video estático
        cmd = [_ffmpeg_bin(), "-y", "-loop", "1", "-t", str(duration),
               "-i", img,
               "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                      f"fps={fps},format=yuv420p",
               "-c:v", "libx264", "-crf", "20", "-tune", "stillimage",
               "-pix_fmt", "yuv420p", "-r", str(fps),
               str(clip_path)]
        r = _run(cmd, timeout=120)
        if r["ok"]:
            clip_paths.append(str(clip_path))

    if not clip_paths:
        for f in tmp.glob("*"):
            f.unlink()
        tmp.rmdir()
        return {"ok": False, "error": "ninguna imagen pudo convertirse"}

    # Unir con xfade
    inputs_args = []
    for cp in clip_paths:
        inputs_args += ["-i", cp]

    n = len(clip_paths)
    filter_parts = [f"[{i}:v]setpts=PTS-STARTPTS[v{i}]" for i in range(n)]
    last_v = "v0"
    offset = duration - transition_duration
    for i in range(1, n):
        new_v = f"vx{i}"
        filter_parts.append(f"[{last_v}][v{i}]xfade=transition={transition}:duration={transition_duration}:offset={offset}[{new_v}]")
        last_v = new_v
        if i < n - 1:
            offset += duration - transition_duration
    filter_complex = ";\n".join(filter_parts)

    final_args = [_ffmpeg_bin(), "-y"] + inputs_args
    if music_path and os.path.exists(music_path):
        final_args += ["-stream_loop", "-1", "-i", music_path]
    final_args += ["-filter_complex", filter_complex, "-map", f"[{last_v}]"]
    if music_path and os.path.exists(music_path):
        final_args += ["-map", f"{n}:a", "-c:a", "aac", "-shortest"]
    final_args += ["-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p"]
    final_args += [output_path]

    r = _run(final_args, timeout=1800)
    for f in tmp.glob("*"):
        try:
            f.unlink()
        except Exception:
            pass
    tmp.rmdir()

    r["output"] = output_path
    r["slides_count"] = len(clip_paths)
    r["duration_per_slide_s"] = duration
    return r


# ---------------------------------------------------------------------------
# Wrapper class
# ---------------------------------------------------------------------------
class VideoProTools:
    @staticmethod
    def status() -> Dict[str, Any]:
        return {
            "ok": True,
            "ffmpeg": _check_ffmpeg(),
            "ffprobe": _check_ffprobe(),
            "matplotlib": MATPLOTLIB_AVAILABLE,
        }

    @staticmethod
    def probe(input_path: str) -> Dict[str, Any]:
        return probe(input_path)

    @staticmethod
    def convert(input_path: str, output_path: str, **kwargs) -> Dict[str, Any]:
        return convert(input_path, output_path, **kwargs)

    @staticmethod
    def thumbnail(input_path: str, output_path: str, time_s: float = 1.0) -> Dict[str, Any]:
        return thumbnail(input_path, output_path, time_s=time_s)

    @staticmethod
    def thumbnail_grid(input_path: str, output_path: str, cols: int = 3, rows: int = 3) -> Dict[str, Any]:
        return thumbnail_grid(input_path, output_path, cols=cols, rows=rows)

    @staticmethod
    def trim(input_path: str, output_path: str, start_s: float, end_s: float) -> Dict[str, Any]:
        return _run([_ffmpeg_bin(), "-y", "-ss", str(start_s), "-to", str(end_s),
                     "-i", _resolve(input_path), "-c", "copy", _resolve(output_path)])

    @staticmethod
    def export_for_platform(input_path: str, output_path: str, platform: str = "tiktok") -> Dict[str, Any]:
        return export_for_platform(input_path, output_path, platform)

    @staticmethod
    def concat(video_paths: List[str], output_path: str, transitions: bool = False) -> Dict[str, Any]:
        return concat_videos(video_paths, output_path, transitions=transitions)

    @staticmethod
    def detect_scenes(input_path: str) -> Dict[str, Any]:
        return detect_scenes(input_path)

    @staticmethod
    def make_gif(input_path: str, output_path: str, start_s: float = 0, duration_s: float = 5) -> Dict[str, Any]:
        return make_gif(input_path, output_path, start_s=start_s, duration_s=duration_s)

    @staticmethod
    def add_watermark(input_path: str, image_path: str, output_path: str, position: str = "bottom-right") -> Dict[str, Any]:
        return add_watermark(input_path, image_path, output_path, position=position)

    @staticmethod
    def normalize_audio(input_path: str, output_path: str, target_lufs: float = -14.0) -> Dict[str, Any]:
        return normalize_audio(input_path, output_path, target_lufs=target_lufs)

    @staticmethod
    def extract_audio(input_path: str, output_path: str, format: str = "mp3") -> Dict[str, Any]:
        return extract_audio(input_path, output_path, format=format)

    @staticmethod
    def remove_audio(input_path: str, output_path: str) -> Dict[str, Any]:
        return remove_audio(input_path, output_path)

    @staticmethod
    def slow_motion(input_path: str, output_path: str, speed: float = 0.5) -> Dict[str, Any]:
        return slow_motion(input_path, output_path, speed=speed)

    @staticmethod
    def time_lapse(input_path: str, output_path: str, speed: float = 4.0) -> Dict[str, Any]:
        return time_lapse(input_path, output_path, speed=speed)

    @staticmethod
    def reverse(input_path: str, output_path: str) -> Dict[str, Any]:
        return reverse(input_path, output_path)

    @staticmethod
    def picture_in_picture(main_path: str, overlay_path: str, output_path: str, position: str = "top-right") -> Dict[str, Any]:
        return picture_in_picture(main_path, overlay_path, output_path, overlay_position=position)

    @staticmethod
    def side_by_side(left_path: str, right_path: str, output_path: str) -> Dict[str, Any]:
        return side_by_side(left_path, right_path, output_path)

    @staticmethod
    def quality(reference_path: str, distorted_path: str) -> Dict[str, Any]:
        return analyze_quality(reference_path, distorted_path)


# ---------------------------------------------------------------------------
# Wrapper class
# ---------------------------------------------------------------------------

    @staticmethod
    def intro(output_path: str, *, title: str = "AUTOMYX", subtitle: str = "",
              duration_s: float = 5.0, style: str = "modern",
              music_path: Optional[str] = None,
              output_width: int = 1920, output_height: int = 1080) -> Dict[str, Any]:
        return intro(output_path, title=title, subtitle=subtitle, duration_s=duration_s,
                    style=style, music_path=music_path,
                    output_width=output_width, output_height=output_height)

    @staticmethod
    def promo(output_path: str, *, title: str, tagline: str = "", cta: str = "",
              bullets: Optional[List[str]] = None, duration_s: float = 15.0,
              style: str = "dynamic", music_path: Optional[str] = None) -> Dict[str, Any]:
        return promo(output_path, title=title, tagline=tagline, cta=cta,
                    bullets=bullets or [], duration_s=duration_s,
                    style=style, music_path=music_path)

    @staticmethod
    def lower_third(input_path: str, output_path: str, *,
                    title: str = "", subtitle: str = "",
                    start_s: float = 0.0, duration_s: float = 4.0,
                    position: str = "bottom") -> Dict[str, Any]:
        return lower_third(input_path, output_path, title=title, subtitle=subtitle,
                          start_s=start_s, duration_s=duration_s, position=position)

    @staticmethod
    def join(video_paths: List[str], output_path: str, *,
             transition: str = "fade", transition_duration: float = 0.8,
             add_intro: bool = False, intro_title: str = "",
             add_outro: bool = False, outro_text: str = "",
             music_path: Optional[str] = None,
             target_resolution: str = "1920x1080") -> Dict[str, Any]:
        return join_with_transitions(video_paths, output_path,
                                    transition=transition, transition_duration=transition_duration,
                                    add_intro=add_intro, intro_title=intro_title,
                                    add_outro=add_outro, outro_text=outro_text,
                                    music_path=music_path, target_resolution=target_resolution)

    @staticmethod
    def slideshow(image_paths: List[str], output_path: str, *,
                  duration_per_image: float = 4.0, transition: str = "fade",
                  title: str = "", music_path: Optional[str] = None) -> Dict[str, Any]:
        return slideshow(image_paths, output_path,
                        duration_per_image=duration_per_image, transition=transition,
                        music_path=music_path)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("FFmpeg disponible:", _check_ffmpeg())
    print("FFprobe disponible:", _check_ffprobe())
    print("Plataformas soportadas:", list(PRESETS.keys()))
    print("Transiciones disponibles:", ["fade", "slide-left", "slide-right", "slide-up", "zoom", "blur", "glitch", "swirl"])
    print("Estilos de intro:", ["modern", "cinematic", "glitch", "neon", "minimal"])
    print("Estilos de promo:", ["dynamic", "elegant", "energetic"])
