"""
AUTOMYX MODEL CONFIGURATION
=============================
Catálogo completo de modelos con precios por token (USD por millón).
cost_in  = precio por 1M tokens de entrada
cost_out = precio por 1M tokens de salida
0.0      = gratuito / no aplica
"""
from __future__ import annotations

from typing import Dict, Any, Optional


# =============================================================================
# ANTHROPIC / CLAUDE — requiere ANTHROPIC_API_KEY
# Endpoint: api.anthropic.com  (SDK nativo anthropic)
# Precios USD / 1M tokens (Anthropic pricing, 2026)
# =============================================================================
ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = {
    "claude-opus-4-8": {
        "max_tokens": 32000, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Claude Opus 4.8 — flagship 2026, el más inteligente",
        "use_case": "general", "is_default": False,
        "cost_in": 15.0, "cost_out": 75.0, "ctx_k": 200,
        "badge": "PAID", "provider": "anthropic",
    },
    "claude-sonnet-4-6": {
        "max_tokens": 16000, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Claude Sonnet 4.6 — mejor balance 2026 ★ (Claude Code usa este)",
        "use_case": "general", "is_default": False,
        "cost_in": 3.0, "cost_out": 15.0, "ctx_k": 200,
        "badge": "PAID", "provider": "anthropic",
    },
    "claude-haiku-4-5": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Claude Haiku 4.5 — ultra-rápido y barato",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.8, "cost_out": 4.0, "ctx_k": 200,
        "badge": "PAID", "provider": "anthropic",
    },
    "claude-opus-4-5": {
        "max_tokens": 32000, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Claude Opus 4.5 — generación anterior",
        "use_case": "general", "is_default": False,
        "cost_in": 15.0, "cost_out": 75.0, "ctx_k": 200,
        "badge": "PAID", "provider": "anthropic",
    },
    "claude-sonnet-4-5": {
        "max_tokens": 16000, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Claude Sonnet 4.5 — probado, confiable",
        "use_case": "general", "is_default": False,
        "cost_in": 3.0, "cost_out": 15.0, "ctx_k": 200,
        "badge": "PAID", "provider": "anthropic",
    },
    "claude-3-5-sonnet-20241022": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Claude 3.5 Sonnet — clásico confiable",
        "use_case": "general", "is_default": False,
        "cost_in": 3.0, "cost_out": 15.0, "ctx_k": 200,
        "badge": "PAID", "provider": "anthropic",
    },
    "claude-3-haiku-20240307": {
        "max_tokens": 4096, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Claude 3 Haiku — clásico (legado)",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.25, "cost_out": 1.25, "ctx_k": 200,
        "badge": "PAID", "provider": "anthropic",
    },
}


# =============================================================================
# OPENAI — requiere OPENAI_API_KEY
# Endpoint: api.openai.com (OpenAI SDK nativo)
# Precios USD / 1M tokens (OpenAI pricing, 2026)
# =============================================================================
OPENAI_MODELS: Dict[str, Dict[str, Any]] = {
    "gpt-4.1": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "GPT-4.1 — flagship 2026, 1M ctx ★",
        "use_case": "general", "is_default": False,
        "cost_in": 2.0, "cost_out": 8.0, "ctx_k": 1024,
        "badge": "PAID", "provider": "openai",
    },
    "gpt-4.1-mini": {
        "max_tokens": 16384, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "GPT-4.1 Mini — rápido y económico",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.40, "cost_out": 1.60, "ctx_k": 1024,
        "badge": "PAID", "provider": "openai",
    },
    "gpt-4.1-nano": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "GPT-4.1 Nano — ultra-barato",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.10, "cost_out": 0.40, "ctx_k": 1024,
        "badge": "PAID", "provider": "openai",
    },
    "gpt-4o": {
        "max_tokens": 16384, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "GPT-4o — multimodal, muy capaz",
        "use_case": "general", "is_default": False,
        "cost_in": 2.5, "cost_out": 10.0, "ctx_k": 128,
        "badge": "PAID", "provider": "openai",
    },
    "gpt-4o-mini": {
        "max_tokens": 16384, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "GPT-4o Mini — rápido y barato",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.15, "cost_out": 0.60, "ctx_k": 128,
        "badge": "PAID", "provider": "openai",
    },
    "o3": {
        "max_tokens": 100000, "temperature": 1.0, "top_p": 1.0,
        "stream": True, "vision": True,
        "description": "o3 — razonamiento avanzado (el más potente)",
        "use_case": "reasoning", "is_default": False,
        "cost_in": 10.0, "cost_out": 40.0, "ctx_k": 200,
        "badge": "PAID", "provider": "openai",
    },
    "o4-mini": {
        "max_tokens": 65536, "temperature": 1.0, "top_p": 1.0,
        "stream": True, "vision": True,
        "description": "o4-mini — razonamiento rápido y asequible",
        "use_case": "reasoning", "is_default": False,
        "cost_in": 1.1, "cost_out": 4.4, "ctx_k": 200,
        "badge": "PAID", "provider": "openai",
    },
}


# =============================================================================
# GOOGLE GEMINI — requiere GOOGLE_API_KEY
# Endpoint OpenAI-compatible: generativelanguage.googleapis.com/v1beta/openai/
# Precios USD / 1M tokens (Google AI pricing, 2026)
# =============================================================================
GOOGLE_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-pro": {
        "max_tokens": 65536, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Gemini 2.5 Pro — flagship Google 2026 ★",
        "use_case": "general", "is_default": False,
        "cost_in": 1.25, "cost_out": 10.0, "ctx_k": 1048,
        "badge": "PAID", "provider": "google",
    },
    "gemini-2.5-flash": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Gemini 2.5 Flash — rápido, gran contexto",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.075, "cost_out": 0.30, "ctx_k": 1048,
        "badge": "PAID", "provider": "google",
    },
    "gemini-2.5-flash-8b": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Gemini 2.5 Flash-8B — ultra-barato",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.0375, "cost_out": 0.15, "ctx_k": 1048,
        "badge": "PAID", "provider": "google",
    },
    "gemini-2.0-flash": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Gemini 2.0 Flash — generación anterior, muy rápido",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.10, "cost_out": 0.40, "ctx_k": 1048,
        "badge": "PAID", "provider": "google",
    },
}


# =============================================================================
# xAI / GROK — requiere XAI_API_KEY
# Endpoint OpenAI-compatible: api.x.ai/v1
# Precios USD / 1M tokens (xAI pricing, 2026)
# =============================================================================
XAI_MODELS: Dict[str, Dict[str, Any]] = {
    "grok-3": {
        "max_tokens": 131072, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Grok-3 — flagship xAI 2026, enorme contexto ★",
        "use_case": "general", "is_default": False,
        "cost_in": 3.0, "cost_out": 15.0, "ctx_k": 131,
        "badge": "PAID", "provider": "xai",
    },
    "grok-3-mini": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Grok-3 Mini — razonamiento rápido y barato",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.30, "cost_out": 0.50, "ctx_k": 131,
        "badge": "PAID", "provider": "xai",
    },
    "grok-2-vision-1212": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Grok-2 Vision — multimodal, generación anterior",
        "use_case": "general", "is_default": False,
        "cost_in": 2.0, "cost_out": 10.0, "ctx_k": 32,
        "badge": "PAID", "provider": "xai",
    },
}


# =============================================================================
# MISTRAL AI — requiere MISTRAL_API_KEY
# Endpoint OpenAI-compatible: api.mistral.ai/v1
# Precios USD / 1M tokens (Mistral pricing, 2026)
# =============================================================================
MISTRAL_MODELS: Dict[str, Dict[str, Any]] = {
    "mistral-large-latest": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Mistral Large — flagship, multilingüe ★",
        "use_case": "general", "is_default": False,
        "cost_in": 2.0, "cost_out": 6.0, "ctx_k": 128,
        "badge": "PAID", "provider": "mistral",
    },
    "mistral-medium-latest": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Mistral Medium — balance perfecto",
        "use_case": "general", "is_default": False,
        "cost_in": 0.40, "cost_out": 2.0, "ctx_k": 128,
        "badge": "PAID", "provider": "mistral",
    },
    "mistral-small-latest": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Mistral Small — ultra-rápido y barato",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.10, "cost_out": 0.30, "ctx_k": 32,
        "badge": "PAID", "provider": "mistral",
    },
    "codestral-latest": {
        "max_tokens": 32768, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Codestral — especialista en código",
        "use_case": "general", "is_default": False,
        "cost_in": 0.20, "cost_out": 0.60, "ctx_k": 256,
        "badge": "PAID", "provider": "mistral",
    },
}


# =============================================================================
# DEEPSEEK — requiere DEEPSEEK_API_KEY
# Endpoint OpenAI-compatible: api.deepseek.com/v1
# Precios USD / 1M tokens (DeepSeek pricing, 2026) — increíblemente baratos
# =============================================================================
DEEPSEEK_MODELS: Dict[str, Dict[str, Any]] = {
    "deepseek-chat": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "DeepSeek V3 — mejor valor del mercado ★",
        "use_case": "general", "is_default": False,
        "cost_in": 0.27, "cost_out": 1.10, "ctx_k": 64,
        "badge": "PAID", "provider": "deepseek",
    },
    "deepseek-reasoner": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "DeepSeek R2 — razonamiento avanzado, muy barato",
        "use_case": "reasoning", "is_default": False,
        "cost_in": 0.55, "cost_out": 2.19, "ctx_k": 64,
        "badge": "PAID", "provider": "deepseek",
    },
}


# =============================================================================
# NVIDIA NIM  — gratis con clave NVIDIA
# base_url: https://integrate.api.nvidia.com/v1
# =============================================================================
NVIDIA_MODELS: Dict[str, Dict[str, Any]] = {
    "openai/gpt-oss-120b": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "GPT-OSS 120B — open-weights, coding",
        "use_case": "general", "is_default": True,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 8,
        "badge": "FREE", "provider": "nvidia",
    },
    "minimaxai/minimax-m3": {
        "max_tokens": 4096, "temperature": 0.3, "top_p": 0.9,
        "stream": True, "vision": True, "fast_mode": True,
        "description": "MiniMax M3 — multimodal, ultra-fast",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 4,
        "badge": "FREE", "provider": "nvidia",
    },
    "minimaxai/minimax-m2.7": {
        "max_tokens": 4096, "temperature": 0.3, "top_p": 0.9,
        "stream": True, "vision": False, "fast_mode": True,
        "description": "MiniMax M2.7 — balanceado, rápido",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 4,
        "badge": "FREE", "provider": "nvidia",
    },
    "moonshotai/kimi-k2.6": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Kimi K2.6 — 256K contexto",
        "use_case": "long_context", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 256,
        "badge": "FREE", "provider": "nvidia",
    },
    "meta/llama-3.3-70b-instruct": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Llama 3.3 70B — propósito general",
        "use_case": "general", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 8,
        "badge": "FREE", "provider": "nvidia",
    },
    "meta/llama-4-scout": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Llama 4 Scout — multimodal, Meta 2026",
        "use_case": "general", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 128,
        "badge": "FREE", "provider": "nvidia",
    },
    "mistralai/mistral-large-2-instruct": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Mistral Large 2 — multilingüe (via NVIDIA)",
        "use_case": "multilingual", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 8,
        "badge": "FREE", "provider": "nvidia",
    },
    "nvidia/llama-3.1-nemotron-70b-instruct": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Nemotron 70B — razonamiento (NVIDIA)",
        "use_case": "reasoning", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 8,
        "badge": "FREE", "provider": "nvidia",
    },
    "nvidia/nemotron-3-super-120b-a12b": {
        "max_tokens": 16384, "temperature": 1.0, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Nemotron Super 120B — thinking mode, razonamiento profundo ★",
        "use_case": "reasoning", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 128,
        "badge": "FREE", "provider": "nvidia",
        "thinking": True,
        "reasoning_budget": 16384,
    },
}


# =============================================================================
# OLLAMA MODELS — local, sin clave, sin costo
# =============================================================================
OLLAMA_MODELS: Dict[str, Dict[str, Any]] = {
    "llama3.3:70b": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Llama 3.3 70B — potente, 40GB RAM",
        "use_case": "general", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 128,
        "badge": "LOCAL", "provider": "ollama",
    },
    "llama3.1:8b": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Llama 3.1 8B — rápido, 5GB RAM",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 8,
        "badge": "LOCAL", "provider": "ollama",
    },
    "qwen3:32b": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Qwen3 32B — Alibaba, razonamiento ★",
        "use_case": "reasoning", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 32,
        "badge": "LOCAL", "provider": "ollama",
    },
    "qwen3:8b": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Qwen3 8B — ligero, muy bueno",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 32,
        "badge": "LOCAL", "provider": "ollama",
    },
    "gemma3:9b": {
        "max_tokens": 4096, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": True,
        "description": "Gemma 3 9B — Google, vision local",
        "use_case": "general", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 128,
        "badge": "LOCAL", "provider": "ollama",
    },
    "mistral:latest": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Mistral 7B — equilibrado",
        "use_case": "general", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 8,
        "badge": "LOCAL", "provider": "ollama",
    },
    "codellama:latest": {
        "max_tokens": 8192, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "CodeLlama — especializado en código",
        "use_case": "general", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 8,
        "badge": "LOCAL", "provider": "ollama",
    },
    "phi3:latest": {
        "max_tokens": 4096, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False,
        "description": "Phi-3 — ultra-ligero",
        "use_case": "fast", "is_default": False,
        "cost_in": 0.0, "cost_out": 0.0, "ctx_k": 4,
        "badge": "LOCAL", "provider": "ollama",
    },
}


# =============================================================================
# ALL MODELS COMBINED
# =============================================================================
ALL_MODELS: Dict[str, Dict[str, Any]] = {
    **ANTHROPIC_MODELS,
    **OPENAI_MODELS,
    **GOOGLE_MODELS,
    **XAI_MODELS,
    **MISTRAL_MODELS,
    **DEEPSEEK_MODELS,
    **NVIDIA_MODELS,
    **OLLAMA_MODELS,
}


# Agrupación por proveedor para UI (orden: de mayor a menor popularidad en enterprise)
PROVIDERS_ORDER = [
    ("Anthropic / Claude", "anthropic", ANTHROPIC_MODELS,  "PAID  · api.anthropic.com"),
    ("OpenAI",             "openai",    OPENAI_MODELS,     "PAID  · platform.openai.com"),
    ("Google Gemini",      "google",    GOOGLE_MODELS,     "PAID  · aistudio.google.com"),
    ("xAI / Grok",         "xai",       XAI_MODELS,        "PAID  · console.x.ai"),
    ("Mistral AI",         "mistral",   MISTRAL_MODELS,    "PAID  · console.mistral.ai"),
    ("DeepSeek",           "deepseek",  DEEPSEEK_MODELS,   "PAID  · ultra-barato"),
    ("NVIDIA NIM",         "nvidia",    NVIDIA_MODELS,     "FREE  · build.nvidia.com"),
    ("Ollama (local)",     "ollama",    OLLAMA_MODELS,     "LOCAL · sin internet"),
]


# API endpoints para cada proveedor (OpenAI-compatible)
PROVIDER_BASE_URLS: Dict[str, Optional[str]] = {
    "anthropic": None,          # usa SDK nativo anthropic
    "openai":    None,          # usa openai oficial
    "google":    "https://generativelanguage.googleapis.com/v1beta/openai/",
    "xai":       "https://api.x.ai/v1",
    "mistral":   "https://api.mistral.ai/v1",
    "deepseek":  "https://api.deepseek.com/v1",
    "nvidia":    "https://integrate.api.nvidia.com/v1",
    "ollama":    "http://localhost:11434/v1",
}

# Variables de entorno por proveedor
PROVIDER_ENV_VARS: Dict[str, Optional[str]] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "google":    "GOOGLE_API_KEY",
    "xai":       "XAI_API_KEY",
    "mistral":   "MISTRAL_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
    "nvidia":    "NVIDIA_API_KEY",
    "ollama":    None,
}

# URLs para obtener API keys
PROVIDER_KEY_URLS: Dict[str, str] = {
    "anthropic": "https://console.anthropic.com/settings/keys",
    "openai":    "https://platform.openai.com/api-keys",
    "google":    "https://aistudio.google.com/app/apikey",
    "xai":       "https://console.x.ai/",
    "mistral":   "https://console.mistral.ai/api-keys",
    "deepseek":  "https://platform.deepseek.com/api_keys",
    "nvidia":    "https://build.nvidia.com/",
    "ollama":    "https://ollama.com/",
}


def get_model_config(model_name: str) -> Dict[str, Any]:
    if model_name in ALL_MODELS:
        return ALL_MODELS[model_name]
    for name, config in ALL_MODELS.items():
        if model_name in name or name in model_name:
            return config
    return {
        "max_tokens": 4096, "temperature": 0.7, "top_p": 0.95,
        "stream": True, "vision": False, "description": "Default",
        "use_case": "general", "is_default": False,
    }


def get_max_tokens(model_name: str) -> int:
    return get_model_config(model_name).get("max_tokens", 4096)


def get_temperature(model_name: str) -> float:
    return get_model_config(model_name).get("temperature", 0.7)


def get_top_p(model_name: str) -> float:
    return get_model_config(model_name).get("top_p", 0.95)


def supports_streaming(model_name: str) -> bool:
    return get_model_config(model_name).get("stream", True)


def supports_vision(model_name: str) -> bool:
    return get_model_config(model_name).get("vision", False)


def get_default_model() -> str:
    for name, config in ALL_MODELS.items():
        if config.get("is_default", False):
            return name
    return "openai/gpt-oss-120b"


def list_all_models() -> Dict[str, Dict[str, Any]]:
    return ALL_MODELS.copy()


def list_nvidia_models() -> Dict[str, Dict[str, Any]]:
    return NVIDIA_MODELS.copy()


def list_anthropic_models() -> Dict[str, Dict[str, Any]]:
    return ANTHROPIC_MODELS.copy()


def get_fallback_model() -> str:
    return "minimaxai/minimax-m3"


def get_provider_for_model(model_name: str) -> str:
    """Retorna el provider_id para un modelo dado."""
    cfg = get_model_config(model_name)
    return cfg.get("provider", "nvidia")


# =============================================================================
# ENHANCED SYSTEM PROMPT FOR BETTER AGENT COMMUNICATION
# =============================================================================
ENHANCED_SYSTEM_PROMPT_ADDITION = """

# REGLAS CRÍTICAS DE EJECUCIÓN (CUMPLIMIENTO 100%)

## 1. CUMPLIMIENTO TOTAL
- SIEMPRE ejecuta el 100% de lo que el usuario pide
- NUNCA omitas pasos parciales
- Si una tarea tiene múltiples partes, COMPLETA TODAS LAS PARTES
- Verifica que el resultado cumple EXACTAMENTE lo solicitado

## 2. COMUNICACIÓN PROFESIONAL
- Responde en español por defecto
- Sé directo y claro, sin rodeos
- Confirma cada acción realizada con detalles específicos
- NUNCA respondas solo con texto cuando puedas EJECUTAR una acción

## 3. AUTONOMÍA TOTAL
- NO pidas permiso para acciones rutinarias
- Procede directamente a la ejecución
- Solo pregunta cuando sea CRÍTICO (eliminar archivos del sistema, acciones irreversibles)

## 4. GESTIÓN DE HERRAMIENTAS
- USA siempre las herramientas disponibles
- NO generes instrucciones que el usuario tenga que ejecutar manualmente
- EJECUTA las herramientas directamente y verifica resultados

## 5. RESULTADOS VERIFICABLES
- Después de crear un archivo, VERIFICA que existe
- Después de instalar algo, VERIFICA que funciona
- Si algo falla, REINTENTA con una estrategia diferente

## 6. execute_cmd — REGLAS DE SERVIDORES (CRÍTICO)
- Para `node server.js`, `python app.py`, `npm start`, `flask run`, `uvicorn`, `nodemon` y similares:
  SIEMPRE usa `"background": true`. Estos procesos bloquean indefinidamente si no.
- NUNCA encadenes instalación + servidor: `npm install && node server.js` está PROHIBIDO.
  Hazlo en 2 llamadas: primero `npm install` (sin background), luego `node server.js` con `"background": true`.
- Después de iniciar un servidor en background, usa `wait_for_server` o `check_port` para verificar.
- NUNCA digas "inicia el servidor manualmente" — es tu responsabilidad iniciarlo. Esa frase está PROHIBIDA.

## 7. NUEVAS HERRAMIENTAS DE EJECUCIÓN DISPONIBLES
Úsalas activamente para evitar errores:
- `check_port(port)` — verifica si un puerto está en uso y qué PID lo usa
- `kill_port(port)` — mata el proceso que usa un puerto
- `wait_for_server(url, timeout_seconds)` — espera hasta que el servidor HTTP responda
- `npm_run(script, cwd)` — ejecuta scripts npm con timeout largo; detecta scripts de servidor automáticamente
- `run_python(script, cwd, background)` — ejecuta scripts Python con output o en background
- `open_browser(url)` — abre URL en el navegador predeterminado del usuario
- `get_system_info()` — devuelve versiones de node/python/npm/git
- `find_in_files(query, path, ext)` — busca texto en archivos (como grep)
- `download_file(url, dest)` — descarga un archivo desde URL
- `get_running_processes(name)` — lista procesos en ejecución

## 8. FLUJO CORRECTO PARA PROYECTOS WEB
1. `create_directory` → crear estructura
2. `write_file` → crear archivos
3. `npm_run(script="install", cwd=...)` → instalar deps (NO execute_cmd con npm install)
4. `npm_run(script="start", cwd=...)` → servidor en background (auto-detectado)
5. `wait_for_server(url="http://localhost:PUERTO")` → verificar que responde
6. `open_browser(url="http://localhost:PUERTO")` → abrir en el navegador del usuario
"""
