#!/usr/bin/env python3
"""
Automyx CLI - Interfaz de línea de comandos profesional
Inspirado en OpenClaw
"""
import argparse
import sys
import os
import json
import webbrowser
from pathlib import Path

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import config
from core.agent import OllamaManager


def main():
    parser = argparse.ArgumentParser(
        description="Automyx - Asistente de IA personal y gateway multi-canal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s gateway              Iniciar el gateway Automyx
  %(prog)s onboard              Configuración guiada inicial
  %(prog)s dashboard            Abrir el panel de control en el navegador
  %(prog)s config list          Ver la configuración actual
  %(prog)s agent -m "Hola"      Enviar un mensaje al agente
        """
    )
    
    subparsers = parser.add_subparsers(title="Comandos", dest="command")
    
    # Comando: gateway
    gateway_parser = subparsers.add_parser("gateway", help="Iniciar el gateway Automyx")
    gateway_parser.add_argument("--host", default="0.0.0.0", help="Host para escuchar (default: 0.0.0.0)")
    gateway_parser.add_argument("--port", type=int, default=3500, help="Puerto para escuchar (default: 3500)")
    gateway_parser.add_argument("--verbose", action="store_true", help="Modo verbose")
    
    # Comando: onboard
    onboard_parser = subparsers.add_parser("onboard", help="Configuración guiada inicial")
    
    # Comando: dashboard
    dashboard_parser = subparsers.add_parser("dashboard", help="Abrir el panel de control en el navegador")
    
    # Comando: config
    config_parser = subparsers.add_parser("config", help="Gestionar la configuración")
    config_subparsers = config_parser.add_subparsers(title="Subcomandos", dest="config_command")
    config_list_parser = config_subparsers.add_parser("list", help="Listar la configuración actual")
    config_get_parser = config_subparsers.add_parser("get", help="Obtener un valor de configuración")
    config_get_parser.add_argument("key", help="Clave de configuración (ej: gateway.port)")
    config_set_parser = config_subparsers.add_parser("set", help="Establecer un valor de configuración")
    config_set_parser.add_argument("key", help="Clave de configuración")
    config_set_parser.add_argument("value", help="Valor a establecer")
    
    # Comando: agent
    agent_parser = subparsers.add_parser("agent", help="Interactuar con el agente Automyx")
    agent_parser.add_argument("-m", "--message", required=True, help="Mensaje para enviar al agente")
    
    # Comando: version
    version_parser = subparsers.add_parser("version", help="Mostrar la versión de Automyx")
    
    # Comandos: ollama
    ollama_parser = subparsers.add_parser("ollama", help="Gestionar modelos de Ollama")
    ollama_subparsers = ollama_parser.add_subparsers(title="Subcomandos", dest="ollama_command")
    ollama_list_parser = ollama_subparsers.add_parser("list", help="Listar modelos Ollama instalados")
    ollama_pull_parser = ollama_subparsers.add_parser("pull", help="Descargar un modelo Ollama")
    ollama_pull_parser.add_argument("model", help="Modelo a descargar (ej: llama3.1:8b)")
    ollama_launch_parser = ollama_subparsers.add_parser("launch", help="Lanzar Automyx con un modelo Ollama")
    ollama_launch_parser.add_argument("--model", default="llama3.1:8b", help="Modelo de Ollama a usar")
    ollama_launch_parser.add_argument("--location", default="local", choices=["local", "cloud"], help="Ubicación del modelo")
    
    # Parsear argumentos
    args = parser.parse_args()
    
    if args.command == "version":
        print("Automyx v2.0.0")
        print("Inspirado en OpenClaw")
        return
    
    if args.command == "gateway":
        # Importar y ejecutar el gateway (usa el método start() para imprimir banner y token!)
        from api.main import app, gateway
        gateway.start(host=args.host, port=args.port)
        return
    
    if args.command == "onboard":
        try:
            from core.onboard import run_onboarding
            run_onboarding()
        except KeyboardInterrupt:
            print("\nOperación cancelada por el usuario.")
        return
    
    if args.command == "dashboard":
        url = f"http://localhost:{config.get('gateway.port', 3500)}"
        print(f"Abriendo panel de control: {url}")
        webbrowser.open(url)
        return
    
    if args.command == "config":
        if args.config_command == "list":
            print("Configuración actual de Automyx:")
            print("=" * 50)
            for key, value in config.config.items():
                if isinstance(value, dict):
                    print(f"\n{key}:")
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"{key}: {value}")
        
        elif args.config_command == "get":
            value = config.get(args.key)
            print(f"{args.key}: {value}")
        
        elif args.config_command == "set":
            config.set(args.key, args.value)
            print(f"✅ {args.key} = {args.value}")
        return
    
    if args.command == "agent":
        print("Enviando mensaje al agente...")
        from core.agent import AutomyxAgent
        agent = AutomyxAgent()
        response = agent.run(args.message)
        print(f"\n🤖 Automyx: {response}")
        return
    
    if args.command == "ollama":
        if args.ollama_command == "list":
            print("Modelos Ollama instalados:")
            models = OllamaManager.list_models()
            if not models:
                print("   No hay modelos instalados.")
            for model in models:
                print(f"  - {model['name']}")
        
        elif args.ollama_command == "pull":
            print(f"Descargando modelo: {args.model}...")
            success = OllamaManager.pull_model(args.model)
            if success:
                print("✅ Modelo descargado exitosamente!")
        
        elif args.ollama_command == "launch":
            OllamaManager.launch_automyx(args.model, args.location)
        return
    
    # Si no hay comando, mostrar ayuda
    parser.print_help()


if __name__ == "__main__":
    main()
