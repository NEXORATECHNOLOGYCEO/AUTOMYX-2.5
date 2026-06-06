"""
Sistema de configuración profesional para Automyx Gateway
Inspirado en OpenClaw
"""
import json
import os
import secrets
from pathlib import Path


class AutomyxConfig:
    """Gestión centralizada de la configuración de Automyx"""
    
    def __init__(self, config_dir: str = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Use a local config directory in the project folder instead of user's home
            self.config_dir = Path(__file__).parent.parent / "state" / ".automix"
        
        self.config_file = self.config_dir / "automix.json"
        self.config = self._load_or_create_default()
        # Forzar puerto 3500 siempre
        self.config['gateway']['port'] = 3500
        self.save()
    
    def _load_or_create_default(self):
        """Carga la configuración o crea la predeterminada"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CONFIG] Error cargando configuración: {e}, usando defaults")
        
        # Configuración predeterminada
        default_config = {
            "version": "2.0.0",
            "gateway": {
                "host": "0.0.0.0",
                "port": 3500,
                "auth": {
                    "mode": "token",  # none, token, password
                    "token": secrets.token_urlsafe(32),
                    "password": None
                },
                "tls": {
                    "enabled": False,
                    "cert_file": None,
                    "key_file": None
                },
                "health": {
                    "enabled": True,
                    "interval": 30
                }
            },
            "channels": {
                "whatsapp": {
                    "enabled": False,
                    "allow_from": [],
                    "groups": []
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": None,
                    "allow_from": []
                },
                "webchat": {
                    "enabled": True
                }
            },
            "agents": {
                "default": {
                    "model": "nvidia/gpt-oss-120b",
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            },
            "models": {
                "default_provider": "nvidia",  # nvidia, ollama_local, ollama_cloud, openai
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "models": ["llama3.1:8b", "llama3.1:70b", "mistral:latest"]
                },
                "nvidia": {
                    "base_url": "https://integrate.api.nvidia.com/v1",
                    "api_key": "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",
                    "models": ["nvidia/gpt-oss-120b", "nvidia/llama-3.1-nemotron-70b-instruct"]
                },
                "openai": {
                    "base_url": "https://api.openai.com/v1",
                    "api_key": None,
                    "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
                }
            },
            "sessions": {
                "per_sender": True,
                "max_history": 50
            },
            "logging": {
                "level": "INFO",
                "file": "automix.log"
            }
        }
        
        # Crear directorio y guardar configuración
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.save(default_config)
        return default_config
    
    def save(self, config: dict = None):
        """Guarda la configuración actual"""
        config_to_save = config or self.config
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
    
    def get(self, key_path: str, default=None):
        """Obtiene un valor de la configuración usando notación de puntos"""
        keys = key_path.split(".")
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def set(self, key_path: str, value):
        """Establece un valor en la configuración usando notación de puntos"""
        keys = key_path.split(".")
        current = self.config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save()
    
    def reload(self):
        """Recarga la configuración desde disco"""
        self.config = self._load_or_create_default()
    
    def get_gateway_token(self):
        """Obtiene el token de autenticación del gateway"""
        return self.get("gateway.auth.token")


# Instancia global de configuración
config = AutomyxConfig()
