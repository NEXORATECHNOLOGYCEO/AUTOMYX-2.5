import pywhatkit
import time
import urllib.parse
from playwright.sync_api import sync_playwright
import requests
import os
import json

class SocialTools:
    @staticmethod
    def send_whatsapp(phone: str, message: str) -> str:
        """Envía un mensaje de WhatsApp usando el bot real en Node.js."""
        try:
            res = requests.post(
                "http://localhost:3001/send", 
                json={"number": phone, "message": message},
                timeout=10
            )
            if res.status_code == 200:
                return f"✅ Mensaje de WhatsApp enviado silenciosamente a {phone}"
            else:
                return f"❌ Error del Bot de WhatsApp: {res.text}"
        except Exception as e:
            return f"❌ Error conectando con el bot de WhatsApp interno: {str(e)}. ¿Escaneaste el QR en la vista de Canales?"

    @staticmethod
    def upload_tiktok(video_path: str, description: str) -> str:
        """Automatiza la subida de un video a TikTok (requiere sesión iniciada en navegador)."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto("https://www.tiktok.com/upload")
                
                # Aquí iría la lógica compleja de login si no hay sesión y subir video.
                # Como es un prototipo avanzado, simularemos el acceso y carga.
                page.wait_for_timeout(3000)
                
                # page.locator("input[type='file']").set_input_files(video_path)
                # ...
                
                browser.close()
            return f"Simulación: Video {video_path} subido a TikTok con descripción: '{description}'"
        except Exception as e:
            return f"Error en TikTok upload: {str(e)}"

    @staticmethod
    def post_facebook(content: str) -> str:
        """Publica en Facebook automatizando el navegador."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto("https://www.facebook.com/")
                # Aquí iría el login y publicación
                page.wait_for_timeout(3000)
                browser.close()
            return f"Simulación: Publicado en Facebook: '{content}'"
        except Exception as e:
            return f"Error en Facebook post: {str(e)}"

    @staticmethod
    def send_telegram(chat_id: str, message: str) -> str:
        """Envía un mensaje usando un bot de Telegram. Requiere TOKEN configurado en la vista de Canales."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            try:
                with open("config.json", "r") as f:
                    token = json.load(f).get("TELEGRAM_BOT_TOKEN")
            except:
                pass
                
        if not token:
            return "❌ Error: Token de Telegram no configurado. Ve a la vista de 'Canales' y conecta tu bot."
            
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                return f"✅ Mensaje enviado a Telegram chat_id {chat_id}"
            else:
                return f"❌ Error enviando Telegram: {response.text}"
        except Exception as e:
            return f"❌ Error de red con Telegram: {str(e)}"
