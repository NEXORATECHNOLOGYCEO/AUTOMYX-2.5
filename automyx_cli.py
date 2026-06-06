import argparse
import sys
import os

# Forzar codificación UTF-8 para evitar errores en Windows con emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests
import json
import os

def check_health(fix=False):
    """Simula el comando 'openclaw doctor'"""
    print("🏥 Automyx Doctor: Revisando estado del sistema...")
    
    if fix:
        print("\n🔧 Ejecutando migraciones y reparaciones (doctor --fix)...")
        if os.path.exists("db_migrate.py"):
            os.system("python db_migrate.py")
        print("✅ Migraciones completadas.\n")
    
    # Revisar FastAPI
    try:
        res = requests.get("http://127.0.0.1:8000/")
        if res.status_code == 200:
            print("✅ Core API (FastAPI) ...... [OK]")
        else:
            print("❌ Core API (FastAPI) ...... [FALLO HTTP]")
    except:
        print("❌ Core API (FastAPI) ...... [OFFLINE]")

    # Revisar WhatsApp Node
    try:
        res = requests.get("http://127.0.0.1:3001/status")
        if res.status_code == 200:
            data = res.json()
            if data.get("connected"):
                print("✅ WhatsApp Gateway ........ [CONECTADO]")
            else:
                print("⚠️ WhatsApp Gateway ........ [ESPERANDO QR]")
        else:
            print("❌ WhatsApp Gateway ........ [FALLO HTTP]")
    except:
        print("❌ WhatsApp Gateway ........ [OFFLINE]")
        
    print("\n💡 Tip: Usa 'python start.bat' para iniciar todos los servicios.")

def send_message(to, message):
    """Simula 'openclaw message send'"""
    try:
        payload = {"number": to, "message": message}
        res = requests.post("http://127.0.0.1:3001/send", json=payload)
        if res.status_code == 200:
            print(f"🚀 Mensaje enviado exitosamente a {to}")
        else:
            print(f"❌ Error del servidor: {res.text}")
    except Exception as e:
        print(f"❌ Error de conexión: Asegúrate de que el Gateway de WhatsApp esté corriendo. ({e})")

def main():
    parser = argparse.ArgumentParser(description="Automyx CLI - Gestión del Agente")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # Comando 'doctor'
    doctor_parser = subparsers.add_parser("doctor", help="Revisa la salud de los servicios de Automyx")
    doctor_parser.add_argument("--fix", action="store_true", help="Aplica migraciones de configuración y repara el estado heredado (ej. JSON -> SQLite)")
    
    # Comando 'message'
    message_parser = subparsers.add_parser("message", help="Envía mensajes a través de los canales")
    message_sub = message_parser.add_subparsers(dest="msg_cmd")
    
    send_parser = message_sub.add_parser("send", help="Envía un mensaje")
    send_parser.add_argument("--to", required=True, help="Número de teléfono (ej: +1234567890)")
    send_parser.add_argument("--message", required=True, help="Contenido del mensaje")

    args = parser.parse_args()

    if args.command == "doctor":
        check_health(fix=getattr(args, 'fix', False))
    elif args.command == "message":
        if args.msg_cmd == "send":
            send_message(args.to, args.message)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
