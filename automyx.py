#!/usr/bin/env python3
"""Punto de entrada — alias de automix.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from automix import main
if __name__ == "__main__":
    sys.exit(main())
