#!/usr/bin/env python3
"""Test del banner de Automyx"""
import sys
import os

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.banner import print_automyx_banner

if __name__ == "__main__":
    print_automyx_banner(model_name="ollama/llama3.2:1b")
