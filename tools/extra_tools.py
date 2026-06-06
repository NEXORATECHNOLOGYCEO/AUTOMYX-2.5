import os
import subprocess
import yt_dlp
import pytesseract
from PIL import Image
import asyncio

class ExtraTools:
    @staticmethod
    def extract_text_from_image(image_path: str) -> str:
        """Extrae texto de una imagen usando OCR (Tesseract)."""
        try:
            if not os.path.exists(image_path):
                return f"Error: No se encontró la imagen {image_path}"
            
            # Requiere tesseract instalado en el sistema. En Windows suele estar en C:\Program Files\Tesseract-OCR\tesseract.exe
            # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return f"✅ Texto extraído de la imagen:\n{text}"
        except Exception as e:
            return f"❌ Error extrayendo texto (Asegúrate de tener Tesseract OCR instalado en el sistema): {str(e)}"

    @staticmethod
    def text_to_speech(text: str, output_path: str, voice: str = 'es-MX-JorgeNeural') -> str:
        """
        Convierte texto a voz (audio MP3) usando Microsoft Edge TTS (alta calidad).
        Voces recomendadas:
        - Español Latino: 'es-MX-JorgeNeural' (Hombre) o 'es-MX-DaliaNeural' (Mujer)
        - Español España: 'es-ES-AlvaroNeural' (Hombre) o 'es-ES-ElviraNeural' (Mujer)
        - Inglés: 'en-US-ChristopherNeural' (Hombre) o 'en-US-AriaNeural' (Mujer)
        """
        try:
            # edge-tts funciona mejor como comando CLI en scripts síncronos
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"✅ Audio generado correctamente con la voz '{voice}' y guardado en {output_path}"
            else:
                return f"❌ Error de edge-tts: {result.stderr}"
        except Exception as e:
            return f"❌ Error generando audio (Asegúrate de tener edge-tts instalado): {str(e)}"

    @staticmethod
    def download_video(**kwargs) -> str:
        """Descarga un video desde YouTube, TikTok, Twitter u otra plataforma usando yt-dlp."""
        try:
            url = kwargs.get('url') or kwargs.get('link') or kwargs.get('video_url')
            output_path = kwargs.get('output_path') or kwargs.get('path') or kwargs.get('dest') or './'
            
            if not url:
                return "❌ Error: Se requiere el parámetro 'url' con el enlace del video."
                
            from tools.pc_tools import PCTools
            output_path = PCTools._resolve_path(output_path)
            
            # Limpiar la URL de posibles backticks que le pase el LLM
            url = url.replace('`', '').strip()
            
            ydl_opts = {
                'outtmpl': f'{output_path}/%(title)s.%(ext)s',
                # Forzar la descarga de formatos que no requieran streaming complejo
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                # Ignorar errores menores y continuar
                'ignoreerrors': True,
                'no_warnings': True,
                'quiet': False,
                # Evitar problemas de certificados
                'nocheckcertificate': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return f"✅ Video descargado correctamente en la carpeta {output_path} usando yt-dlp"
        except Exception as e:
            return f"❌ Error descargando el video: {str(e)}"
