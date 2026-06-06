import os
import subprocess
from tools.pc_tools import PCTools

class AudioTools:
    @staticmethod
    def apply_autotune(input_path: str, output_path: str, scale: str = "major", speed: int = 1) -> str:
        try:
            input_path = PCTools._resolve_path(input_path)
            output_path = PCTools._resolve_path(output_path)
            if not os.path.exists(input_path): return f"Error: No se encontró {input_path}"
            
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-af", "compand=attacks=0:points=-80/-80|-15/-15|0/-1.2|20/-1.2,chorus=0.5:0.9:50|60:0.4|0.32:0.25|0.4:2|2.3,reverb=50:50:100:100:20:0:0:0:0",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Autotune y corrección de pitch aplicado. Guardado en {output_path}"
            else:
                return f"❌ Error aplicando autotune: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def mix_music(voice_path: str, beat_path: str, output_path: str) -> str:
        try:
            voice_path = PCTools._resolve_path(voice_path)
            beat_path = PCTools._resolve_path(beat_path)
            output_path = PCTools._resolve_path(output_path)
            if not os.path.exists(voice_path): return f"Error: No se encontró {voice_path}"
            if not os.path.exists(beat_path): return f"Error: No se encontró {beat_path}"
            
            cmd = [
                "ffmpeg", "-y", 
                "-i", voice_path, 
                "-i", beat_path,
                "-filter_complex", "[0:a]volume=1.2[a1];[1:a]volume=0.8[a2];[a1][a2]amix=inputs=2:duration=longest[a]",
                "-map", "[a]", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Mezcla de voz y beat completada en {output_path}"
            return f"❌ Error mezclando: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
        
    @staticmethod
    def master_audio(input_path: str, output_path: str) -> str:
        try:
            input_path = PCTools._resolve_path(input_path)
            output_path = PCTools._resolve_path(output_path)
            if not os.path.exists(input_path): return f"Error: No se encontró {input_path}"
            
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-af", "loudnorm=I=-14:LRA=11:TP=-1.5",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Masterización a -14 LUFS (Estándar Spotify/YouTube) completada en {output_path}"
            return f"❌ Error masterizando: {result.stderr}"
        except Exception as e:
            return f"❌ Error: {str(e)}"