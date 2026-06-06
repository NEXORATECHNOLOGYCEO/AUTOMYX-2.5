import os
import webbrowser
import urllib.parse

class EmailTools:
    @staticmethod
    def read_recent_emails(limit: int = 5) -> str:
        # Dado que leer correos reales requiere OAUTH o IMAP configurado con contraseñas de aplicación
        # retornamos un mensaje de configuración
        return "❌ La lectura de correos requiere configuración previa de credenciales IMAP en las variables de entorno."
        
    @staticmethod
    def create_email_draft(to: str, subject: str, body: str) -> str:
        try:
            subject_encoded = urllib.parse.quote(subject)
            body_encoded = urllib.parse.quote(body)
            mailto_url = f"mailto:{to}?subject={subject_encoded}&body={body_encoded}"
            
            # Abre el cliente de correo predeterminado del sistema (Outlook, Mail de Windows, etc.)
            webbrowser.open(mailto_url)
            return f"✅ Borrador de correo creado y abierto en tu cliente de correo por defecto (Destino: {to})."
        except Exception as e:
            return f"❌ Error creando borrador de correo: {str(e)}"