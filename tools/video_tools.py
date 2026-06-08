import os
import subprocess
import stat
import logging
import threading
from pathlib import Path
from typing import Optional, Any
from tools.pc_tools import PCTools

logger = logging.getLogger("automyx.video")

# File locks para evitar conflictos en ediciones concurrentes del mismo video
_video_file_locks: dict[str, threading.RLock] = {}
_video_locks_lock = threading.Lock()

def _get_video_lock(path: str) -> threading.RLock:
    """Obtiene (o crea) un lock por ruta de archivo."""
    norm = os.path.normpath(PCTools._resolve_path(path))
    with _video_locks_lock:
        if norm not in _video_file_locks:
            _video_file_locks[norm] = threading.RLock()
        return _video_file_locks[norm]

class VideoTools:
    """
    Automyx Studio de Edición de Vídeo Profesional:
    - Color grading (corrección de color)
    - Transiciones avanzadas
    - Subtítulos automáticos (Whisper)
    - Normalización de audio
    - Composición básica
    """
    
    @staticmethod
    def _prepare_output_path(output_path: str) -> str:
        """Resuelve la ruta y se asegura de que haya permisos para sobrescribir."""
        resolved = PCTools._resolve_path(output_path)
        dir_name = os.path.dirname(resolved)
        if dir_name:
            try:
                os.makedirs(dir_name, exist_ok=True)
            except Exception as e:
                pass
        if os.path.exists(resolved):
            try:
                os.chmod(resolved, stat.S_IWRITE)
            except Exception:
                pass
        return resolved

    @staticmethod
    def _normalize_position(pos) -> str:
        """Normaliza cualquier variante de posición a 'top'/'center'/'bottom'."""
        if not pos:
            return "center"
        s = str(pos).lower().strip()
        if s in ("center", "centered", "centrado", "centrada", "middle", "centro", "mid", "c"):
            return "center"
        if s in ("top", "arriba", "superior", "t", "up", "header"):
            return "top"
        if s in ("bottom", "abajo", "inferior", "b", "down", "footer"):
            return "bottom"
        return "center"  # fallback seguro

    @staticmethod
    def _normalize_color(color) -> Optional[str]:
        """Normaliza variantes de color a nombres canónicos en español que auto_subtitles reconoce."""
        if not color:
            return None
        s = str(color).lower().strip()
        mapping = {
            # verde
            "verde": "verde", "green": "verde", "verdes": "verde", "g": "verde",
            # amarillo
            "amarillo": "amarillo", "amarilla": "amarillo", "yellow": "amarillo", "y": "amarillo",
            # rojo
            "rojo": "rojo", "roja": "rojo", "red": "rojo", "r": "rojo",
            # azul
            "azul": "azul", "blue": "azul", "b": "azul",
            # blanco
            "blanco": "blanco", "blanca": "blanco", "white": "blanco", "w": "blanco",
            # negro
            "negro": "negro", "negra": "negro", "black": "negro", "k": "negro",
            # cyan
            "cyan": "cyan", "celeste": "cyan", "c": "cyan",
            # magenta
            "magenta": "magenta", "fucsia": "magenta", "m": "magenta",
            # naranja
            "naranja": "naranja", "orange": "naranja", "o": "naranja",
            # morado
            "morado": "morado", "morada": "morado", "purple": "morado", "violeta": "morado", "p": "morado",
        }
        return mapping.get(s, s)


    @staticmethod
    def _parse_subtitle_style_string(style_str: str) -> dict:
        """
        Parsea strings de estilo que el LLM suele inventar a partir de lenguaje natural.
        Ejemplos:
          'centered_green'  -> {position: 'center', color: 'verde'}
          'bottom_yellow'   -> {position: 'bottom', color: 'amarillo'}
          'mrbeast'         -> {style: 'mrbeast'}
          'neon_white'      -> {style: 'neon', color: 'blanco'}
          'centered'        -> {position: 'center'}
          'verde_centrado'  -> {color: 'verde', position: 'center'}
        """
        s = (style_str or "").lower().strip().replace("-", "_").replace(" ", "_")
        out: dict = {}

        # Tokenizar por underscores (word-boundary para evitar falsos positivos)
        tokens = set(s.split("_"))

        # Posición
        pos_map = {
            "center": "center", "centered": "center", "centrado": "center", "centrada": "center", "middle": "center", "centro": "center",
            "top": "top", "arriba": "top", "superior": "top",
            "bottom": "bottom", "abajo": "bottom", "inferior": "bottom",
        }
        for k, v in pos_map.items():
            if k in tokens or k in s.split("_"):
                out["position"] = v
                break

        # Color (mapea a los nombres que auto_subtitles reconoce)
        color_map = {
            "verde": "verde", "green": "verde", "verdes": "verde",
            "amarillo": "amarillo", "yellow": "amarillo", "amarilla": "amarillo",
            "rojo": "rojo", "red": "rojo", "roja": "rojo",
            "azul": "azul", "blue": "azul",
            "blanco": "blanco", "white": "blanco", "blanca": "blanco",
            "negro": "negro", "black": "negro", "negra": "negro",
            "cyan": "cyan", "celeste": "cyan",
            "magenta": "magenta", "fucsia": "magenta",
            "naranja": "naranja", "orange": "naranja",
            "morado": "morado", "purple": "morado", "violeta": "morado",
        }
        for k, v in color_map.items():
            if k in tokens:
                out["color"] = v
                out["font_color"] = v
                break

        # Estilo de plantilla (si no hay position/color, asumir que es un style name)
        style_names = {"mrbeast", "neon", "cinematic", "karaoke", "default", "minimal", "bold", "simple"}
        for st in style_names:
            if st in tokens and "style" not in out:
                out["style"] = st
                break
        if not out:
            # Fallback: tratar todo el string como nombre de style
            out["style"] = s

        return out

    @staticmethod
    def professional_color_grading(input_path: str, output_path: str, style: str = "cinematic") -> str:
        """
        Aplica una corrección de color profesional.
        Estilos disponibles: 'cinematic', 'mrbeast', 'vintage', 'black_and_white', 'vibrant', 'teal_and_orange'
        """
        input_path = PCTools._resolve_path(input_path)
        output_path = VideoTools._prepare_output_path(output_path)
        if not os.path.exists(input_path):
            return f"❌ Error: No se encontró el archivo {input_path}"
        
        # Definir filtros FFmpeg para cada estilo
        video_filters = {
            "cinematic": "eq=contrast=1.2:brightness=0.05:saturation=1.1:gamma=1.05, vignette",
            "mrbeast": "eq=contrast=1.4:brightness=0.1:saturation=1.4:gamma=1.1, unsharp=lms=1.5:la=1.5",
            "vintage": "colorbalance=rs=0.3:gs=-0.2:bs=-0.2, eq=contrast=0.9:saturation=0.6, curves=all=vintage",
            "black_and_white": "format=gray, eq=contrast=1.2",
            "vibrant": "eq=contrast=1.2:saturation=1.5:gamma=1.05",
            "teal_and_orange": "colorbalance=rm=0.2:gm=-0.2:bm=-0.2:rs=-0.2:gs=0.2:bs=0.2:rh=0.1:gh=-0.1:bh=-0.1, eq=saturation=1.2"
        }
        
        filter_str = video_filters.get(style, video_filters["cinematic"])
        
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", filter_str,
            "-c:a", "copy",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return f"✅ Corrección de color estilo '{style}' aplicada con éxito! Guardado en {output_path}"
        except subprocess.CalledProcessError as e:
            return f"❌ Error en la corrección de color: {e.stderr}"
        except Exception as e:
            return f"❌ Error inesperado: {str(e)}"

    @staticmethod
    def advanced_transition(input_path1: str, input_path2: str, output_path: str, transition_type: str = "crossfade", duration: float = 1.0) -> str:
        """
        Crea una transición entre dos vídeos muy profesional.
        Tipos de transición: 'crossfade', 'wipe_left', 'wipe_right', 'wipe_up', 'wipe_down', 'cube', 'zoom', 'slide'
        """
        input_path1 = PCTools._resolve_path(input_path1)
        input_path2 = PCTools._resolve_path(input_path2)
        output_path = VideoTools._prepare_output_path(output_path)
        
        for path in [input_path1, input_path2]:
            if not os.path.exists(path):
                return f"❌ Error: No se encontró el archivo {path}"
        
        # Obtener la duración del primer vídeo para calcular el inicio de la transición
        try:
            cmd_probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path1]
            result_probe = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
            dur1 = float(result_probe.stdout.strip())
            start_transition = dur1 - duration
        except Exception as e:
            return f"❌ Error al analizar la duración del vídeo: {str(e)}"
        
        # Definir filtros para cada transición
        transition_filters = {
            "crossfade": f"xfade=transition=fade:duration={duration}:offset={start_transition}",
            "wipe_left": f"xfade=transition=wiperight:duration={duration}:offset={start_transition}",
            "wipe_right": f"xfade=transition=wipeleft:duration={duration}:offset={start_transition}",
            "wipe_up": f"xfade=transition=wipedown:duration={duration}:offset={start_transition}",
            "wipe_down": f"xfade=transition=wipeup:duration={duration}:offset={start_transition}",
            "cube": f"xfade=transition=cube:duration={duration}:offset={start_transition}",
            "zoom": f"xfade=transition=zoom:duration={duration}:offset={start_transition}",
            "slide": f"xfade=transition=slideleft:duration={duration}:offset={start_transition}"
        }
        
        transition_filter = transition_filters.get(transition_type, transition_filters["crossfade"])
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path1, "-i", input_path2,
            "-filter_complex", f"{transition_filter}[v];[0:a][1:a]acrossfade=d={duration}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "320k",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return f"✅ Transición '{transition_type}' creada con éxito! Guardado en {output_path}"
        except subprocess.CalledProcessError as e:
            return f"❌ Error al crear la transición: {e.stderr}"
        except Exception as e:
            return f"❌ Error inesperado: {str(e)}"

    @staticmethod
    def professional_audio_mastering(input_path: str, output_path: str, target_loudness: float = -14.0) -> str:
        """
        Normaliza y mejora el audio del vídeo.
        Target loudness: -14 LUFS es estándar para plataformas como YouTube.
        """
        input_path = PCTools._resolve_path(input_path)
        output_path = VideoTools._prepare_output_path(output_path)
        if not os.path.exists(input_path):
            return f"❌ Error: No se encontró el archivo {input_path}"
        
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-filter_complex", 
            f"loudnorm=I={target_loudness}:LRA=7:TP=-1.5, highpass=f=30, equalizer=f=100:t=q:w=1:g=2, equalizer=f=5000:t=q:w=2:g=1",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "320k",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return f"✅ Mastering de audio profesional completado! Guardado en {output_path}"
        except subprocess.CalledProcessError as e:
            return f"❌ Error en el mastering de audio: {e.stderr}"
        except Exception as e:
            return f"❌ Error inesperado: {str(e)}"

    @staticmethod
    def add_intro_outro(main_video: str, intro: str, outro: str, output_path: str) -> str:
        """
        Añade una intro al principio y un outro al final del vídeo principal.
        """
        main_video = PCTools._resolve_path(main_video)
        output_path = VideoTools._prepare_output_path(output_path)
        
        video_files = [main_video]
        if intro:
            video_files.insert(0, intro)
        if outro:
            video_files.append(outro)
        
        return VideoTools.composite_movie_sequence(video_files, output_path, transition="crossfade")

    @staticmethod
    def composite_movie_sequence(video_files: list, output_path: str, transition: str = "none") -> str:
        """
        Une múltiples vídeos con transiciones.
        """
        output_path = VideoTools._prepare_output_path(output_path)
        resolved_paths = [PCTools._resolve_path(p) for p in video_files if os.path.exists(PCTools._resolve_path(p))]
        
        if not resolved_paths:
            return "❌ No hay vídeos válidos para compilar."
        
        if len(resolved_paths) == 1:
            try:
                cmd = ["ffmpeg", "-y", "-i", resolved_paths[0], "-c", "copy", output_path]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return f"✅ Vídeo guardado en {output_path}"
            except Exception as e:
                return f"❌ Error al guardar el vídeo: {str(e)}"
        
        if transition == "none" or len(resolved_paths) == 2:
            if len(resolved_paths) == 2:
                return VideoTools.advanced_transition(resolved_paths[0], resolved_paths[1], output_path, transition_type=transition if transition != "none" else "crossfade")
            
            list_file = os.path.join(os.path.dirname(output_path), "temp_list.txt")
            try:
                with open(list_file, "w", encoding="utf-8") as f:
                    for p in resolved_paths:
                        f.write(f"file '{p.replace(os.sep, '/')}'\n")
                
                cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                os.remove(list_file)
                
                return f"✅ Vídeos unidos con éxito! Guardado en {output_path}"
            except Exception as e:
                return f"❌ Error al unir los vídeos: {str(e)}"
        
        # Para más de 2 vídeos, usaremos la herramienta de Blender VSE para mejores transiciones
        try:
            from tools.three_d_tools import ThreeDTools
            return ThreeDTools.composite_movie_sequence(video_files=resolved_paths, output_path=output_path)
        except Exception as e:
            return f"❌ Error al usar el editor de Blender: {str(e)}"

    @staticmethod
    def trim_video(input_path: str, start_time: str, end_time: str, output_path: str) -> str:
        """Recorta un vídeo usando FFmpeg directamente."""
        try:
            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(input_path):
                return f"❌ Error: No se encontró el archivo {input_path}"
            
            cmd = [
                "ffmpeg", "-y", "-i", input_path, 
                "-ss", str(start_time), "-to", str(end_time), 
                "-c:v", "copy", "-c:a", "copy", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Vídeo recortado con éxito! Guardado en {output_path}"
            else:
                return f"❌ Error de FFmpeg: {result.stderr}"
        except Exception as e:
            return f"❌ Error ejecutando FFmpeg: {str(e)}"
    
    @staticmethod
    def add_music_to_video(video_path: str, audio_path: str, output_path: str, volume: float = 0.5) -> str:
        """Mezcla el audio original del vídeo con una música de fondo."""
        try:
            video_path = PCTools._resolve_path(video_path)
            audio_path = PCTools._resolve_path(audio_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(video_path): return f"❌ Error: No se encontró {video_path}"
            if not os.path.exists(audio_path): return f"❌ Error: No se encontró {audio_path}"
            
            cmd = [
                "ffmpeg", "-y", 
                "-i", video_path, 
                "-i", audio_path,
                "-filter_complex", f"[0:a]volume=1.0[a1];[1:a]volume={volume}[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Música de fondo agregada y guardada en {output_path}"
            else:
                return f"❌ Error agregando música: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    @staticmethod
    def apply_visual_effect(input_path: str, effect: str, output_path: str) -> str:
        """Aplica un efecto visual al vídeo."""
        try:
            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(input_path): return f"❌ Error: No se encontró {input_path}"
            
            vf_filter = ""
            if effect == "blur": vf_filter = "boxblur=10:1"
            elif effect == "bw": vf_filter = "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3"
            elif effect == "vintage": vf_filter = "curves=vintage"
            else: return f"❌ Efecto desconocido: {effect}"
            
            cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", vf_filter, "-c:a", "copy", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Efecto '{effect}' aplicado! Guardado en {output_path}"
            else:
                return f"❌ Error aplicando efecto: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    @staticmethod
    def auto_subtitles(**kwargs) -> str:
        """
        Genera subtítulos con Whisper y los QUEMA en el vídeo usando ffmpeg + ASS.

        Catálogo de presets (ver core/subtitle_presets.list_presets()):
          Bold/Energetic:  hype, beast_gold, tiktok_pop, reel_clean, youtube_shorts
          Minimal/Clean:   minimal, documentary, news_banner, subtitle_bar, clean_white
          Cinematic:       cinematic, film_noir, netflix, letterbox
          Neon/Glow:       neon, neon_pink, neon_green, synthwave, retro_arcade
          Social:          karaoke, capcut_bold, tiktok_classic, meme, explainer
          Animated:        karaoke_word, fade_in, typewriter
          Pro:             studio, podcast, sports, vlog, interview

        Acepta aliases: style, template, preset, subtitle_template, subtitle_style
        (string o dict).

        Acepta overrides por argumento para control total:
          font_color, outline_color, back_color, font_size, font_family,
          outline_w (ancho del borde), shadow, bold, italic, alignment (1-9),
          margin_v (margen vertical en px), position ('top'/'center'/'bottom'),
          language, uppercase.

        Posición rápida (atajos):
          'top' / 'arriba' / 'up'             → alignment 8  (top-center)
          'center' / 'centrado' / 'middle'    → alignment 5  (mid-center)
          'bottom' / 'abajo' / 'down'         → alignment 2  (bottom-center, default)

        Ejemplo:
          auto_subtitles(input_path='v.mp4', output_path='out.mp4',
                         style='hype', font_color='verde', position='center')
        """
        try:
            from core.subtitle_presets import get_preset, build_ass_style, list_presets, ass_color
            from core.auto_install import ensure_packages

            # --- 0. Auto-instalar whisper si no está (silencioso) ---
            try:
                ensure_packages(["whisper"], verbose=False)
            except Exception:
                pass

            # --- 1. Resolver argumentos con aliases ---
            input_path = (kwargs.get('input_path') or kwargs.get('video_path') or kwargs.get('file_path')
                          or kwargs.get('text') or kwargs.get('text_path') or kwargs.get('source')
                          or kwargs.get('input_video') or kwargs.get('input_file'))
            output_path = kwargs.get('output_path') or kwargs.get('out_path') or kwargs.get('output') or kwargs.get('dest')
            language = kwargs.get('language', 'es')
            whisper_model = kwargs.get('whisper_model') or kwargs.get('model_size') or 'small'
            style = (kwargs.get('style') or kwargs.get('subtitle_style_name') or kwargs.get('template')
                     or kwargs.get('preset') or kwargs.get('subtitle_template')
                     or kwargs.get('subtitle_style') or 'hype')
            # If style is a dict (e.g. subtitle_style={"preset":"hype",...}) handle below
            if isinstance(style, dict):
                style = style.get("preset") or style.get("style") or style.get("name") or "hype"

            position = (kwargs.get('position') or kwargs.get('subtitle_position') or kwargs.get('text_position')
                        or kwargs.get('pos') or 'center')
            position = VideoTools._normalize_position(position)

            font_color = (kwargs.get('font_color') or kwargs.get('color') or kwargs.get('subtitle_color')
                          or kwargs.get('text_color') or kwargs.get('colour'))
            if font_color:
                font_color = VideoTools._normalize_color(font_color)

            # Parse 'centered_green' style strings
            subtitle_style = kwargs.get('subtitle_style') or kwargs.get('sub_style')
            if isinstance(subtitle_style, str) and not style or style == 'hype':
                parsed = VideoTools._parse_subtitle_style_string(subtitle_style)
                if "style" in parsed: style = parsed["style"]
                if "position" in parsed: position = parsed["position"]
                if "color" in parsed and not font_color: font_color = parsed["color"]
            elif isinstance(subtitle_style, dict):
                if 'preset' in subtitle_style or 'style' in subtitle_style:
                    style = subtitle_style.get('preset') or subtitle_style.get('style')
                if 'position' in subtitle_style: position = subtitle_style['position']
                if ('color' in subtitle_style or 'font_color' in subtitle_style) and not font_color:
                    font_color = subtitle_style.get('color') or subtitle_style.get('font_color')

            if not input_path or not output_path:
                available = ", ".join(p["id"] for p in list_presets()[:5]) + ", ..."
                return (f"❌ Faltan argumentos requeridos (input_path y output_path).\n"
                        f"Ejemplo: auto_subtitles(input_path='v.mp4', output_path='out.mp4', style='hype')\n"
                        f"Presets disponibles: {available}")

            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(input_path):
                return f"❌ No se encontró el vídeo: {input_path}"
            if os.path.getsize(input_path) < 1000:
                return f"❌ El vídeo es demasiado pequeño ({os.path.getsize(input_path)} bytes). ¿Archivo corrupto?"

            # --- 2. Asegurar ffmpeg ---
            from shutil import which
            ffmpeg_bin = which("ffmpeg") or ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if not which(ffmpeg_bin):
                return ("❌ ffmpeg no está instalado.\n"
                        "Instálalo desde https://ffmpeg.org/download.html o con:\n"
                        "  - Windows (choco): choco install ffmpeg\n"
                        "  - macOS:  brew install ffmpeg\n"
                        "  - Linux:  sudo apt install ffmpeg")

            # --- 3. Extraer audio + normalizar volumen (clave para whisper con audio bajo) ---
            audio_path = "_automyx_temp_audio.wav"
            try:
                af = subprocess.run(
                    [ffmpeg_bin, "-y", "-i", input_path, "-vn",
                     "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                     "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path],
                    capture_output=True, text=True, timeout=120,
                )
                if af.returncode != 0:
                    err = (af.stderr or "").strip()
                    tail = "\n".join(err.splitlines()[-8:])
                    return (f"❌ Error extrayendo audio del vídeo (ffmpeg exit {af.returncode}).\n"
                            f"{tail}\n"
                            f"💡 Comprueba que el vídeo no esté corrupto y que ffmpeg soporte el códec.")
            except subprocess.TimeoutExpired:
                return "❌ Timeout extrayendo audio (>120s). El vídeo es demasiado largo o el disco está lento."
            except FileNotFoundError:
                return f"❌ ffmpeg no se pudo ejecutar (binario: {ffmpeg_bin})"

            # --- 4. Transcribir con Whisper ---
            try:
                import whisper
            except ImportError:
                return ("❌ Whisper no está instalado. Ejecuta: pip install openai-whisper\n"
                        "O dile al agente: 'instala whisper' y lo hará automáticamente.")
            # Whisper model sizes: tiny, base, small, medium, large
            # Default 'small' es un buen balance velocidad/precisión para CPU.
            try:
                model = whisper.load_model(whisper_model)
                result = model.transcribe(audio_path, language=language, word_timestamps=True)
            except Exception as e:
                return f"❌ Error transcribiendo audio con Whisper (modelo={whisper_model}): {e}"
            finally:
                if os.path.exists(audio_path):
                    try: os.remove(audio_path)
                    except Exception: pass

            if not result.get('segments'):
                return "⚠️ Whisper no detectó habla en el audio. No hay nada que subtitular."

            # --- 5. Construir el preset + overrides ---
            preset = get_preset(style)
            overrides = {
                "alignment": {"top": 8, "center": 5, "bottom": 2}.get(position, 2),
                "margin_v":  {"top": 40, "center": 80, "bottom": 60}.get(position, 60),
            }
            if font_color:
                overrides["primary"] = ass_color(font_color)
            # Explicit overrides
            for k in ("font_color", "font_family", "font_size",
                      "outline_color", "outline_w", "shadow",
                      "bold", "italic", "margin_v", "alignment"):
                v = kwargs.get(k)
                if v is not None:
                    target = {"font_color": "primary", "outline_color": "outline"}.get(k, k)
                    if target in ("primary", "outline", "back") and isinstance(v, str):
                        v = ass_color(v)
                    overrides[target] = v

            style_def = build_ass_style(preset, overrides)
            margin_v = int(overrides.get("margin_v", 60))
            uppercase = bool(preset.get("uppercase") or kwargs.get("uppercase"))
            karaoke_mode = bool(preset.get("karaoke")) and result.get("segments") and any(
                seg.get("words") for seg in result["segments"]
            )

            # --- 6. Generar contenido ASS ---
            ass_path = "_automyx_temp_subs.ass"

            def _fmt(t: float) -> str:
                h = int(t // 3600); m = int((t % 3600) // 60)
                s = int(t % 60); cs = int((t % 1) * 100)
                return f"{h:02}:{m:02}:{s:02}.{cs:02}"

            ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_def}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            for seg in result['segments']:
                start = _fmt(seg['start'])
                end = _fmt(seg['end'])
                text = seg['text'].strip()
                if uppercase:
                    text = text.upper()
                if karaoke_mode and seg.get("words"):
                    # Word-by-word highlighting using {\k} karaoke tags
                    parts = []
                    for w in seg["words"]:
                        wd = max(int((w["end"] - w["start"]) * 100), 5)
                        wt = w["word"].strip()
                        if uppercase: wt = wt.upper()
                        parts.append("{{\\k%d}}%s" % (wd, wt))
                    text = "".join(parts)
                ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,{margin_v},,{text}\n"

            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)

            # --- 7. Quemar subtítulos con ffmpeg ---
            # Obtener resolución del video para original_size (requerido en ffmpeg git builds)
            _w, _h = 1920, 1080
            try:
                _fp = which("ffprobe") or "ffprobe"
                _ps = subprocess.run(
                    [_fp, "-v", "error",
                     "-select_streams", "v:0", "-show_entries", "stream=width,height",
                     "-of", "csv=p=0", input_path],
                    capture_output=True, text=True, timeout=10,
                )
                _parts = _ps.stdout.strip().split(",")
                if len(_parts) == 2:
                    _w, _h = int(_parts[0]), int(_parts[1])
            except Exception:
                pass
            cmd = [
                ffmpeg_bin, "-y", "-i", input_path,
                "-vf", f"subtitles={ass_path}:original_size={_w}x{_h}",
                "-c:a", "aac", "-b:a", "128k",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
                "-movflags", "+faststart",
                output_path,
            ]
            try:
                sub_res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            except subprocess.TimeoutExpired:
                if os.path.exists(ass_path):
                    try: os.remove(ass_path)
                    except Exception: pass
                return "❌ Timeout quemando subtítulos (>600s). El vídeo es demasiado largo."
            except FileNotFoundError:
                return f"❌ ffmpeg no se pudo ejecutar (binario: {ffmpeg_bin})"

            if os.path.exists(ass_path):
                try: os.remove(ass_path)
                except Exception: pass

            if sub_res.returncode == 0 and os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                return (f"✅ Subtítulos aplicados correctamente\n"
                        f"   Estilo: {preset.get('label', style)} ({style})\n"
                        f"   Posición: {position}\n"
                        f"   Color: {font_color or '(default)'}\n"
                        f"   Salida: {output_path} ({size_mb:.1f} MB)\n"
                        f"   Segmentos: {len(result['segments'])}")
            else:
                err = (sub_res.stderr or sub_res.stdout or "").strip()
                tail = "\n".join(err.splitlines()[-12:])
                return (f"❌ ffmpeg falló al quemar subtítulos (exit {sub_res.returncode}).\n"
                        f"Comando: {' '.join(cmd)}\n"
                        f"Detalle:\n{tail}")
        except Exception as e:
            import traceback
            return f"❌ Error en subtítulos: {e}\n{traceback.format_exc()[:600]}"
    
    @staticmethod
    def _generate_ass_subtitles(
        input_path: str,
        language: str = "es",
        style: str = "hype",
        position: str = "center",
        **overrides
    ) -> str:
        """Genera archivo ASS de subtítulos con Whisper (sin quemar en vídeo)."""
        try:
            from core.subtitle_presets import get_preset, build_ass_style, ass_color
            from core.auto_install import ensure_packages

            try:
                ensure_packages(["whisper"], verbose=False)
            except Exception:
                pass

            input_path = PCTools._resolve_path(input_path)
            if not os.path.exists(input_path):
                return ""

            # Extraer audio
            audio_path = "_automyx_temp_audio.wav"
            ffmpeg_bin = "ffmpeg"
            af = subprocess.run(
                [ffmpeg_bin, "-y", "-i", input_path, "-vn",
                 "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                 "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path],
                capture_output=True, text=True, timeout=120,
            )
            if af.returncode != 0:
                return ""

            # Transcribir con Whisper
            try:
                import whisper
                model = whisper.load_model("small")
                result = model.transcribe(audio_path, language=language, word_timestamps=True)
            except Exception:
                return ""
            finally:
                if os.path.exists(audio_path):
                    try: os.remove(audio_path)
                    except Exception: pass

            if not result.get('segments'):
                return ""

            # Construir preset
            preset = get_preset(style)
            position = VideoTools._normalize_position(position)
            ass_overrides = {
                "alignment": {"top": 8, "center": 5, "bottom": 2}.get(position, 2),
                "margin_v":  {"top": 40, "center": 80, "bottom": 60}.get(position, 60),
            }
            for k, v in overrides.items():
                if k in ("font_color", "font_family", "font_size", "outline_color", "outline_w", "shadow", "bold", "italic", "margin_v", "alignment"):
                    target = {"font_color": "primary", "outline_color": "outline"}.get(k, k)
                    if target in ("primary", "outline", "back") and isinstance(v, str):
                        v = ass_color(v)
                    ass_overrides[target] = v

            style_def = build_ass_style(preset, ass_overrides)
            margin_v = int(ass_overrides.get("margin_v", 60))
            uppercase = bool(preset.get("uppercase") or overrides.get("uppercase"))
            karaoke_mode = bool(preset.get("karaoke")) and result.get("segments") and any(
                seg.get("words") for seg in result["segments"]
            )

            # Generar ASS
            ass_path = "_automyx_temp_subs.ass"

            def _fmt(t: float) -> str:
                h = int(t // 3600); m = int((t % 3600) // 60)
                s = int(t % 60); cs = int((t % 1) * 100)
                return f"{h:02}:{m:02}:{s:02}.{cs:02}"

            ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_def}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            for seg in result['segments']:
                start = _fmt(seg['start'])
                end = _fmt(seg['end'])
                text = seg['text'].strip()
                if uppercase:
                    text = text.upper()
                if karaoke_mode and seg.get("words"):
                    parts = []
                    for w in seg["words"]:
                        wd = max(int((w["end"] - w["start"]) * 100), 5)
                        wt = w["word"].strip()
                        if uppercase: wt = wt.upper()
                        parts.append("{{\\k%d}}%s" % (wd, wt))
                    text = "".join(parts)
                ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,{margin_v},,{text}\n"

            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)

            return ass_path

        except Exception:
            return ""
    
    @staticmethod
    def create_tiktok_edit(**kwargs) -> str:
        """[Tool] Edita un vídeo para TikTok."""
        try:
            input_path = kwargs.get('input_path') or kwargs.get('video_path') or kwargs.get('file_path')
            output_path = kwargs.get('output_path')
            hook_text = kwargs.get('hook_text', "")
            
            if not input_path or not output_path:
                return "❌ Error: Faltan argumentos (input_path y output_path)"
                
            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(input_path): return f"❌ Error: No se encontró {input_path}"
            
            temp_out = output_path.replace(".mp4", "_temp_tiktok.mp4")
            filter_complex = "crop=ih*(9/16):ih,scale=1080:1920,eq=saturation=1.3:contrast=1.1"
            
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", filter_complex,
                "-c:a", "aac", "-b:a", "192k",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                temp_out
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return f"❌ Error creando la edición de TikTok: {result.stderr}"
            
            # Añadir subtítulos si hay hook_text
            if hook_text:
                subs_result = VideoTools.auto_subtitles(
                    input_path=temp_out,
                    output_path=output_path,
                    style="hype",
                    position="center"
                )
                if os.path.exists(temp_out): os.remove(temp_out)
                if "Error" in subs_result:
                    return f"⚠️ Edición TikTok completada, pero fallaron los subtítulos: {subs_result}"
                return f"🔥 Edición TikTok completada! Guardado en {output_path}"
            
            os.rename(temp_out, output_path)
            return f"🔥 Edición TikTok completada! Guardado en {output_path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    @staticmethod
    def add_dynamic_zoom(input_path: str, output_path: str, zoom_mode: str = "in", zoom_factor: float = 1.5) -> str:
        """Añade un efecto de zoom dinámico (in o out) al vídeo."""
        try:
            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(input_path): return f"❌ Error: No se encontró {input_path}"

            if zoom_mode == "in":
                zoom_expr = f"min(zoom+0.002,{zoom_factor})"
            else: # out
                zoom_expr = f"max({zoom_factor}-0.002,1)"

            # Obtener FPS del source para zoompan 1:1
            try:
                fps_probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=r_frame_rate",
                     "-of", "default=noprint_wrappers=1:nokey=1", input_path],
                    capture_output=True, text=True, timeout=10,
                )
                fps_raw = fps_probe.stdout.strip()
                if "/" in fps_raw:
                    n, d = fps_raw.split("/")
                    fps_val = max(1, min(120, int(float(n) / max(float(d), 1))))
                else:
                    fps_val = max(1, min(120, int(float(fps_raw) or 30)))
            except Exception:
                fps_val = 30

            filter_complex = f"zoompan=z='{zoom_expr}':fps={fps_val}:d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080"

            cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", filter_complex, "-c:a", "aac", "-b:a", "128k", "-preset", "ultrafast", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Zoom dinámico '{zoom_mode}' aplicado! Guardado en {output_path}"
            return f"❌ Error aplicando zoom: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    @staticmethod
    def advanced_video_editor(
        input_path: str = "",
        output_path: str = "",
        platform: str = "tiktok",
        auto_subtitles: bool = False,
        subtitle_style: Optional[dict] = None,
        effects: Any = False,
        transitions: Any = False,
        color_grading: str = "",
        analyze_and_edit: bool = False,
        speed: float = 1.0,
        rotate: int = 0,
        scale: str = "",
        intro_path: str = "",
        outro_path: str = "",
        max_duration_s: float = 0,
        language: str = "es",
        **kwargs,
    ) -> str:
        """
        Editor de video profesional todo-en-uno (el "hub" de AUTOMYX para edición).

        Aliases tolerantes: el LLM a veces inventa nombres de parámetros. Esta función
        acepta variantes comunes sin lanzar TypeError.

        Aliases para input_path:    video_path, input_video, input_file, file_path, source
        Aliases para output_path:   output, out_path, dest, save_path
        Aliases para transitions:   transition, trans
        Aliases para effects:       effect, fx
        Aliases para subtitle_style: sub_style, subs_style
        """
        # ---- Normalizar aliases que el LLM suele inventar ----
        if not input_path:
            for alias in ("video_path", "input_video", "input_file", "file_path", "source", "video"):
                v = kwargs.pop(alias, None)
                if v:
                    input_path = v
                    break
        if not output_path:
            for alias in ("output", "out_path", "dest", "save_path", "output_file"):
                v = kwargs.pop(alias, None)
                if v:
                    output_path = v
                    break
        if not transitions:
            for alias in ("transition", "trans"):
                v = kwargs.pop(alias, None)
                if v is not None:
                    transitions = v
                    break
        if not effects:
            for alias in ("effect", "fx"):
                v = kwargs.pop(alias, None)
                if v is not None:
                    effects = v
                    break
        if subtitle_style is None:
            for alias in ("sub_style", "subs_style", "subtitle_format"):
                v = kwargs.pop(alias, None)
                if v is not None:
                    subtitle_style = v
                    break

        # Si subtitle_style viene como string (ej 'centered_green'), parsearlo
        if isinstance(subtitle_style, str):
            subtitle_style = VideoTools._parse_subtitle_style_string(subtitle_style)

        # Si quedan kwargs desconocidos, loguearlos pero no fallar
        if kwargs:
            logger.debug(f"advanced_video_editor: kwargs ignorados: {list(kwargs.keys())}")

        # ---- INICIO DEL PIPELINE ----
        """
        Editor de video profesional todo-en-uno (el "hub" de AUTOMYX para edición).

        Pipeline (en orden):
          1. Validar input
          2. analyze_and_edit → detectar cortes/scores (opcional, solo log)
          3. color_grading → aplicar LUT cinematográfica/vibrant/vintage (opcional)
          4. effects → zoom dinámico, shake, transiciones internas (opcional)
          5. auto_subtitles → Whisper + burn ASS (opcional)
          6. intro/outro → concatenar (opcional)
          7. platform → reencodar al aspect ratio / bitrate / duración target
          8. speed/rotate/scale → transforms básicos

        Args:
            input_path: ruta del video de entrada
            output_path: ruta de salida (si vacía, se genera automáticamente)
            platform: 'tiktok' | 'reels' | 'shorts' | 'youtube' | 'instagram' | 'twitter' | 'custom'
            auto_subtitles: True para subtítulos con Whisper
            subtitle_style: dict con {engine, font, color, size, position, style, ...}
            effects: True/False o lista de efectos ['zoom','shake','flash']
            transitions: True para añadir crossfade de 0.3s al inicio/fin
            color_grading: '' | 'cinematic' | 'vibrant' | 'vintage' | 'bw' | 'warm' | 'cold'
            analyze_and_edit: True para analizar contenido (log + sugerencias)
            speed: multiplicador de velocidad (1.0 = normal)
            rotate: 0|90|180|270 grados
            scale: ej. "1080:1920" para forzar tamaño
            intro_path: video de intro a concatenar (opcional)
            outro_path: video de outro a concatenar (opcional)
            max_duration_s: truncar a N segundos (0 = sin límite)
            language: idioma para subtítulos ('es','en',...)
        """
        # Lock por archivo de entrada para evitar ediciones concurrentes
        lock = _get_video_lock(input_path)
        lock.acquire()
        try:
            # ---- 0. Resolver paths ----
            if not input_path:
                return "❌ Error: input_path es requerido"
            input_path = PCTools._resolve_path(input_path)
            if not os.path.exists(input_path):
                return f"❌ Error: No se encontró {input_path}"

            if not output_path:
                stem = Path(input_path).stem
                folder = Path(input_path).parent
                suffix = f"_{platform}_edit" if platform else "_edit"
                output_path = str(folder / f"{stem}{suffix}.mp4")
            output_path = VideoTools._prepare_output_path(output_path)

            platform_norm = (platform or "tiktok").lower().strip()
            subtitle_style = subtitle_style or {}

            log_lines = [f"🎬 advanced_video_editor | platform={platform_norm} | subs={auto_subtitles} | grading={color_grading or '-'} | effects={bool(effects)}"]

            # ---- 1. Determinar aspect ratio / resolución / max dur target por plataforma ----
            PLATFORM_PRESETS = {
                "tiktok":    {"aspect": "9:16", "size": "1080:1920", "max_dur": 180, "vbr": "4500k", "abr": "160k"},
                "reels":     {"aspect": "9:16", "size": "1080:1920", "max_dur": 180, "vbr": "4500k", "abr": "160k"},
                "shorts":    {"aspect": "9:16", "size": "1080:1920", "max_dur": 60,  "vbr": "4500k", "abr": "160k"},
                "youtube":   {"aspect": "16:9", "size": "1920:1080", "max_dur": 0,   "vbr": "8000k", "abr": "192k"},
                "instagram": {"aspect": "1:1",  "size": "1080:1080", "max_dur": 90,  "vbr": "4500k", "abr": "160k"},
                "twitter":   {"aspect": "16:9", "size": "1280:720",  "max_dur": 140, "vbr": "5000k", "abr": "128k"},
                "custom":    {"aspect": "16:9", "size": "1920:1080", "max_dur": 0,   "vbr": "6000k", "abr": "160k"},
            }
            preset = PLATFORM_PRESETS.get(platform_norm, PLATFORM_PRESETS["tiktok"])
            if not scale:
                scale = preset["size"]
            if not max_duration_s:
                max_duration_s = float(preset["max_dur"])

            # ---- 2. analyze_and_edit (solo info, sin modificar video) ----
            if analyze_and_edit:
                try:
                    analysis = VideoTools.analyze_video_content(input_path)
                    log_lines.append(f"   📊 Análisis: {analysis[:200]}")
                except Exception as e:
                    log_lines.append(f"   ⚠️ analyze_and_edit no se pudo ejecutar: {e}")

            # ---- 3. color_grading como paso previo (genera archivo intermedio) ----
            current = input_path
            tmp_dir = Path(output_path).parent / "_automyx_tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            stage_counter = 0

            def _next_tmp(suffix=""):
                nonlocal stage_counter
                stage_counter += 1
                return str(tmp_dir / f"stage_{stage_counter:02d}{suffix}.mp4")

            if color_grading:
                graded = _next_tmp("_graded.mp4")
                gr_res = VideoTools.professional_color_grading(current, graded, style=color_grading)
                if gr_res.startswith("✅"):
                    current = graded
                    log_lines.append(f"   🎨 Color grading '{color_grading}' aplicado")
                else:
                    log_lines.append(f"   ⚠️ Color grading falló, continúo sin él: {gr_res[:120]}")

            # ---- 4. effects (zoom dinámico, etc.) ----
            if effects:
                if effects is True:
                    effects_list = ["zoom"]
                elif isinstance(effects, str):
                    effects_list = [e.strip() for e in effects.split(",") if e.strip()]
                else:
                    effects_list = list(effects) if effects else []

                for eff in effects_list:
                    eff_l = eff.lower()
                    if eff_l in ("zoom", "dynamic_zoom", "kenburns"):
                        zoomed = _next_tmp(f"_{eff_l}")
                        zm_res = VideoTools.add_dynamic_zoom(current, zoomed, zoom_mode="in", zoom_factor=1.4)
                        if zm_res.startswith("✅"):
                            current = zoomed
                            log_lines.append(f"   🔍 Effect '{eff_l}' aplicado")
                        else:
                            log_lines.append(f"   ⚠️ Effect '{eff_l}' falló: {zm_res[:120]}")

            # ---- 5. auto_subtitles (Whisper → genera ASS, NO quema aún) ----
            ass_subtitle_path = None
            if auto_subtitles:
                try:
                    # Generar ASS sin quemar (nueva función interna)
                    ass_subtitle_path = VideoTools._generate_ass_subtitles(
                        input_path=current,
                        language=language,
                        style=subtitle_style.get("style", "hype"),
                        position=subtitle_style.get("position", "center"),
                        **{k: v for k, v in subtitle_style.items() if k not in ("style", "position")}
                    )
                    if ass_subtitle_path and os.path.exists(ass_subtitle_path):
                        log_lines.append("   💬 Subtítulos generados (ASS), se quemarán en render final")
                    else:
                        log_lines.append(f"   ⚠️ No se pudo generar ASS: {ass_subtitle_path}")
                        ass_subtitle_path = None
                except Exception as e:
                    log_lines.append(f"   ⚠️ auto_subtitles excepción: {e}")
                    ass_subtitle_path = None

            # ---- 6. intro/outro (concatenar) ----
            if intro_path and os.path.exists(intro_path):
                concat_list = tmp_dir / "concat_in.txt"
                concat_list.write_text(f"file '{intro_path}'\nfile '{current}'\n", encoding="utf-8")
                with_intro = _next_tmp("_intro.mp4")
                r = subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                     "-c", "copy", with_intro],
                    capture_output=True, text=True,
                )
                if r.returncode == 0 and os.path.exists(with_intro):
                    current = with_intro
                    log_lines.append("   🎞️ Intro concatenada")
            if outro_path and os.path.exists(outro_path):
                concat_list = tmp_dir / "concat_out.txt"
                concat_list.write_text(f"file '{current}'\nfile '{outro_path}'\n", encoding="utf-8")
                with_outro = _next_tmp("_outro.mp4")
                r = subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                     "-c", "copy", with_outro],
                    capture_output=True, text=True,
                )
                if r.returncode == 0 and os.path.exists(with_outro):
                    current = with_outro
                    log_lines.append("   🎞️ Outro concatenado")

            # ---- 7. transitions (crossfade 0.3s al inicio/fin, ligero) ----
            v_filters = []
            a_filters = []
            if transitions:
                # fade-in 0.3s al inicio + fade-out 0.3s al final
                v_filters.append("fade=in:0:7")
                v_filters.append("fade=out:st=9999:d=0.3")  # se sobreescribe abajo con duración real
                a_filters.append("afade=in:st=0:d=0.3")
                a_filters.append("afade=out:st=9999:d=0.3")
                log_lines.append("   ✨ Transitions (fade in/out 0.3s) aplicadas")

            # ---- 8. transforms básicos: speed / rotate / scale ----
            if speed != 1.0 and speed > 0:
                v_filters.append(f"setpts={1/speed}*PTS")
                a_filters.append(f"atempo={speed}")
            if rotate == 90:
                v_filters.append("transpose=1")
            elif rotate == 180:
                v_filters.append("transpose=2,transpose=2")
            elif rotate in (270, -90):
                v_filters.append("transpose=2")
            if scale:
                v_filters.append(f"scale={scale}")

            # Aplicar fade-out real (necesita conocer duración del video actual)
            if transitions and v_filters:
                try:
                    probe = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                         "default=noprint_wrappers=1:nokey=1", current],
                        capture_output=True, text=True, timeout=10,
                    )
                    dur_s = float(probe.stdout.strip() or 0)
                    # Reemplazar el placeholder de fade-out con la duración real
                    v_filters = [f if not f.startswith("fade=out:st=9999") else f"fade=out:st={max(0, dur_s-0.3):.2f}:d=0.3" for f in v_filters]
                    a_filters = [f if not f.startswith("afade=out:st=9999") else f"afade=out:st={max(0, dur_s-0.3):.2f}:d=0.3" for f in a_filters]
                except Exception:
                    # Si no se puede obtener duración, remover los fades de salida
                    v_filters = [f for f in v_filters if not f.startswith("fade=out:st=9999")]
                    a_filters = [f for f in a_filters if not f.startswith("afade=out:st=9999")]

            # Añadir subtítulos ASS al final (después de scale para que se vean en 9:16)
            if ass_subtitle_path and os.path.exists(ass_subtitle_path):
                safe_ass = ass_subtitle_path.replace('\\', '/').replace(':', '\\:')
                v_filters.append(f"ass={safe_ass}")

            # ---- 9. Truncar a max_duration_s si se especificó ----
            t_input_flags = ["-y", "-i", current]
            if max_duration_s and max_duration_s > 0:
                t_input_flags += ["-t", str(max_duration_s)]

            # ---- 10. Render final ----
            cmd = ["ffmpeg", "-y"] + t_input_flags
            if v_filters:
                cmd += ["-vf", ",".join(v_filters)]
            if a_filters:
                cmd += ["-af", ",".join(a_filters)]
            cmd += [
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "aac", "-b:a", preset["abr"],
                "-movflags", "+faststart",
                "-r", "30",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                return f"❌ Error en render final: {result.stderr[-800:]}"

            # ---- 11. Limpiar temporales ----
            try:
                for f in tmp_dir.glob("stage_*.mp4"):
                    try: f.unlink()
                    except Exception: pass
                for f in tmp_dir.glob("concat_*.txt"):
                    try: f.unlink()
                    except Exception: pass
                # Limpiar ASS generado
                if ass_subtitle_path and os.path.exists(ass_subtitle_path):
                    try: os.remove(ass_subtitle_path)
                    except Exception: pass
            except Exception:
                pass

            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            log_lines.append(f"   📁 Salida: {output_path} ({size_mb:.1f} MB)")
            return "\n".join(log_lines) + f"\n✅ Edición profesional completada! {output_path}"

        except subprocess.TimeoutExpired:
            return f"❌ Timeout (>600s) en edición de {input_path}. El video es demasiado largo o el sistema está sobrecargado."
        except Exception as e:
            return f"❌ Error en advanced_video_editor: {type(e).__name__}: {e}"
        finally:
            lock.release()

    @staticmethod
    def analyze_video_content(input_path: str) -> str:
        """Analiza el vídeo y extrae metadatos detallados usando ffprobe."""
        try:
            import json
            input_path = PCTools._resolve_path(input_path)
            if not os.path.exists(input_path): return f"❌ Error: No se encontró {input_path}"

            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", input_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                format_info = data.get("format", {})
                streams = data.get("streams", [])
                
                video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
                
                analysis = [f"📊 Análisis de {os.path.basename(input_path)}:"]
                analysis.append(f"- Duración: {format_info.get('duration', 'N/A')} segundos")
                analysis.append(f"- Tamaño: {int(format_info.get('size', 0)) / (1024*1024):.2f} MB")
                
                if video_stream:
                    analysis.append(f"- Vídeo: {video_stream.get('width')}x{video_stream.get('height')} ({video_stream.get('codec_name')})")
                    fps = video_stream.get('r_frame_rate', '0/0')
                    if '/' in fps:
                        num, den = fps.split('/')
                        fps_val = float(num) / float(den) if float(den) != 0 else 0
                        analysis.append(f"- FPS: {fps_val:.2f}")
                
                if audio_stream:
                    analysis.append(f"- Audio: {audio_stream.get('codec_name')} ({audio_stream.get('sample_rate')} Hz)")
                    
                return "\\n".join(analysis)
            return f"❌ Error analizando vídeo: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    @staticmethod
    def smart_auto_edit(input_path: str, output_path: str) -> str:
        """Aplica una edición automática inteligente (mejora de color, contraste y audio)."""
        try:
            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(input_path): return f"❌ Error: No se encontró {input_path}"

            v_filter = "eq=contrast=1.1:brightness=0.02:saturation=1.1, unsharp=5:5:0.8:3:3:0.4"
            a_filter = "loudnorm=I=-14:LRA=11:TP=-1.5"

            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", v_filter,
                "-af", a_filter,
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✨ Edición automática inteligente aplicada! Guardado en {output_path}"
            return f"❌ Error en smart auto edit: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"