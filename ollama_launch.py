#!/usr/bin/env python3
"""
Comando: ollama launch automyx
Inspiración en OpenClaw
Uso:
  ollama launch automyx --model llama3.1:8b
  ollama launch automyx --model glm-5.1:cloud
  ollama launch automyx --model glm-5.1 --location cloud
"""
import argparse
import sys
import os
import subprocess

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import OllamaManager


def main():
    parser = argparse.ArgumentParser(
        description="Launch Automyx with an Ollama model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  ollama launch automyx
  ollama launch automyx --model llama3.1:8b
  ollama launch automyx --model nvidia/gpt-oss-120b
  ollama launch automyx --model glm-5.1 --location local
  ollama launch automyx --model glm-5.1 --location cloud
        """
    )
    
    parser.add_argument(
        "--model", 
        default="llama3.1:8b", 
        help="Modelo de Ollama a usar (default: llama3.1:8b)"
    )
    parser.add_argument(
        "--location",
        default="local",
        choices=["local", "cloud"],
        help="Ubicación del modelo: local o cloud (default: local)"
    )
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Manejar modelos con prefijo (nvidia/, openai/, cloud/, ollama/)
    if args.model.startswith("nvidia/") or args.model.startswith("openai/") or args.model.startswith("cloud/") or args.model.startswith("ollama/"):
        # Para modelos con proveedor, solo establecemos la variable de entorno directamente
        print(f"Iniciando Automyx con {args.model}...")
        os.environ["AUTOMYX_MODEL"] = args.model
        
        # Ejecutar Automyx
        # Encontrar la ruta correcta del script principal
        # El archivo ollama_launch.py está en la raíz del proyecto, así que automix.py también está ahí
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "automix.py")
        
        if not os.path.exists(script_path):
            print(f"❌ No se encontró automix.py en: {script_path}")
            return
        
        subprocess.run([sys.executable, script_path, "gateway"], cwd=os.path.dirname(os.path.abspath(__file__)))
        return
    
    # Manejar sintaxis como "glm-5.1:cloud"
    if ":" in args.model and args.location == "local":
        parts = args.model.split(":")
        if parts[-1] in ["local", "cloud"]:
            args.location = parts[-1]
            args.model = ":".join(parts[:-1])
    
    # Lanzar Automyx
    OllamaManager.launch_automyx(args.model, args.location)


if __name__ == "__main__":
    main()
