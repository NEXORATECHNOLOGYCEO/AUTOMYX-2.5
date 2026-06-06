import os
import subprocess
import stat
from tools.pc_tools import PCTools

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
        Genera subtítulos 100% perfectos estilo CapCut usando Whisper con word-timestamps y ASS.
        """
        try:
            input_path = kwargs.get('input_path') or kwargs.get('video_path') or kwargs.get('file_path')
            output_path = kwargs.get('output_path')
            language = kwargs.get('language', 'es')
            style = kwargs.get('style', 'mrbeast')
            position = kwargs.get('position', 'center')
            
            if not input_path or not output_path:
                return "❌ Error: Faltan argumentos requeridos (input_path y output_path)"
                
            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            import whisper
            if not os.path.exists(input_path): return f"❌ Error: No se encontró {input_path}"
            
            audio_path = "temp_audio.wav"
            try:
                subprocess.run(["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                return f"❌ Error extrayendo audio del vídeo: {e.stderr.decode('utf-8', errors='ignore')}"
            
            model = whisper.load_model("small")
            result = model.transcribe(audio_path, language=language, word_timestamps=True)
            
            ass_path = "temp_subs.ass"
            
            def _get_ass_color(color_name: str, default: str) -> str:
                colors = {
                    "rojo": "&H000000FF", "red": "&H000000FF",
                    "verde": "&H0000FF00", "green": "&H0000FF00",
                    "azul": "&H00FF0000", "blue": "&H00FF0000",
                    "amarillo": "&H0000FFFF", "yellow": "&H0000FFFF",
                    "blanco": "&H00FFFFFF", "white": "&H00FFFFFF",
                    "negro": "&H00000000", "black": "&H00000000",
                    "cyan": "&H00FFFF00", "celeste": "&H00FFFF00",
                    "magenta": "&H00FF00FF", "fucsia": "&H00FF00FF",
                    "naranja": "&H0000A5FF", "orange": "&H0000A5FF",
                    "morado": "&H00800080", "purple": "&H00800080"
                }
                return colors.get(color_name.lower().strip(), default)
            
            # Estilos de subtítulos
            if style == "mrbeast":
                style_def = "Style: Default,Arial Black,28,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,120,1"
            elif style == "neon":
                style_def = "Style: Default,Arial Bold,30,&H0000FFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,2,10,10,120,1"
            elif style == "cinematic":
                style_def = "Style: Default,Georgia,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,120,1"
            else:
                style_def = "Style: Default,Arial,24,&H00FFFFFF,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,120,1"
            
            # Posición
            align = 2
            margin_v = 40
            if position == "center":
                align = 5
                margin_v = 150
            elif position == "top":
                align = 8
                margin_v = 40
            
            ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_def}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            
            # Generar subtítulos por segmentos
            for seg in result['segments']:
                start = f"{int(seg['start'] // 3600):02}:{int((seg['start'] % 3600) // 60):02}:{int(seg['start'] % 60):02}.{int((seg['start'] % 1) * 100):02}"
                end = f"{int(seg['end'] // 3600):02}:{int((seg['end'] % 3600) // 60):02}:{int(seg['end'] % 60):02}.{int((seg['end'] % 1) * 100):02}"
                text = seg['text'].strip()
                ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,{margin_v},,{text}\n"
            
            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            
            safe_ass = ass_path.replace('\\', '/').replace(':', '\\:')
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", f"ass={safe_ass}",
                "-c:a", "copy", output_path
            ]
            sub_res = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(audio_path): os.remove(audio_path)
            if os.path.exists(ass_path): os.remove(ass_path)
            
            if sub_res.returncode == 0:
                return f"✅ Subtítulos estilo '{style}' aplicados! Guardado en {output_path}"
            else:
                return f"❌ Error quemando subtítulos: {sub_res.stderr}"
                
        except Exception as e:
            return f"❌ Error en subtítulos: {str(e)}"
    
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
                    style="mrbeast",
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

            filter_complex = f"zoompan=z='{zoom_expr}':d=700:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

            cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", filter_complex, "-c:a", "copy", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Zoom dinámico '{zoom_mode}' aplicado! Guardado en {output_path}"
            return f"❌ Error aplicando zoom: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    @staticmethod
    def advanced_video_editor(input_path: str, output_path: str, speed: float = 1.0, rotate: int = 0, scale: str = "") -> str:
        """Aplica múltiples ediciones avanzadas: velocidad, rotación, escalado."""
        try:
            input_path = PCTools._resolve_path(input_path)
            output_path = VideoTools._prepare_output_path(output_path)
            if not os.path.exists(input_path): return f"❌ Error: No se encontró {input_path}"

            v_filters = []
            a_filters = []

            if speed != 1.0:
                v_filters.append(f"setpts={1/speed}*PTS")
                a_filters.append(f"atempo={speed}")

            if rotate == 90:
                v_filters.append("transpose=1")
            elif rotate == 180:
                v_filters.append("transpose=2,transpose=2")
            elif rotate == 270 or rotate == -90:
                v_filters.append("transpose=2")

            if scale:
                v_filters.append(f"scale={scale}")

            cmd = ["ffmpeg", "-y", "-i", input_path]

            if v_filters:
                cmd.extend(["-vf", ",".join(v_filters)])
            if a_filters:
                cmd.extend(["-af", ",".join(a_filters)])

            cmd.append(output_path)
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return f"✅ Edición avanzada completada! Guardado en {output_path}"
            return f"❌ Error en edición avanzada: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

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