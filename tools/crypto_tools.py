"""
Crypto Tools - Operaciones con criptomonedas
==============================================
Consulta precios, calcula conversiones, genera wallets, hace
análisis técnico simple. Usa CoinGecko (gratis) como fuente principal.
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import secrets
import requests
from typing import Any, Dict, List, Optional

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_CACHE_FILE = None  # definido después
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_S = 60


def _cache_get(key: str) -> Optional[Any]:
    if key in _CACHE:
        if time.time() - _CACHE[key]["ts"] < CACHE_TTL_S:
            return _CACHE[key]["value"]
        del _CACHE[key]
    return None


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = {"ts": time.time(), "value": value}


# ---------------------------------------------------------------------------
# Precios
# ---------------------------------------------------------------------------
def price(coin_id: str, vs_currency: str = "usd") -> Dict[str, Any]:
    """Precio actual de una cripto. coin_id es el slug de CoinGecko (bitcoin, ethereum, etc)."""
    cache_key = f"price:{coin_id}:{vs_currency}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{COINGECKO_BASE}/simple/price",
                         params={"ids": coin_id, "vs_currencies": vs_currency,
                                 "include_24hr_change": "true", "include_market_cap": "true",
                                 "include_24hr_vol": "true"},
                         timeout=10)
        r.raise_for_status()
        data = r.json().get(coin_id, {})
        if not data:
            return {"ok": False, "error": f"coin_id {coin_id!r} no encontrado en CoinGecko"}
        result = {
            "ok": True,
            "coin": coin_id,
            "vs": vs_currency,
            "price": data.get(vs_currency),
            "change_24h_pct": data.get(f"{vs_currency}_24h_change"),
            "market_cap": data.get(f"{vs_currency}_market_cap"),
            "volume_24h": data.get(f"{vs_currency}_24h_vol"),
        }
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def prices_batch(coin_ids: List[str], vs_currency: str = "usd") -> Dict[str, Any]:
    """Precios de varias criptos en una sola llamada."""
    try:
        r = requests.get(f"{COINGECKO_BASE}/simple/price",
                         params={"ids": ",".join(coin_ids), "vs_currencies": vs_currency,
                                 "include_24hr_change": "true"},
                         timeout=10)
        r.raise_for_status()
        return {"ok": True, "vs": vs_currency, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Conversión
# ---------------------------------------------------------------------------
def convert(from_coin: str, to_coin: str, amount: float) -> Dict[str, Any]:
    """Convierte entre criptos (o fiat). from/to son coin_ids o símbolos fiat (usd, eur, ars, mxn)."""
    fiat = {"usd", "eur", "ars", "mxn", "pen", "cop", "brl", "clp", "gbp", "jpy", "cny", "krw", "inr", "rub", "cad", "aud", "chf"}
    try:
        ids = []
        if from_coin.lower() not in fiat:
            ids.append(from_coin)
        if to_coin.lower() not in fiat:
            ids.append(to_coin)
        if not ids:
            ids = ["bitcoin"]  # dummy
        prices = requests.get(f"{COINGECKO_BASE}/simple/price",
                              params={"ids": ",".join(ids), "vs_currencies": "usd,eur,ars,mxn,pen,cop,brl"},
                              timeout=10).json()

        def get_usd_value(coin: str, amount_v: float) -> Optional[float]:
            c = coin.lower()
            if c == "usd":
                return amount_v
            if c in ("eur", "ars", "mxn", "pen", "cop", "brl"):
                # Necesito rates desde USD
                if "bitcoin" in prices and "usd" in prices["bitcoin"]:
                    usd_per_btc = prices["bitcoin"]["usd"]
                    return amount_v
            if c in prices and "usd" in prices[c]:
                return amount_v * prices[c]["usd"]
            return None

        from_usd = get_usd_value(from_coin, amount)
        if from_usd is None:
            return {"ok": False, "error": f"no se pudo obtener precio de {from_coin}"}
        # from_usd a to_coin
        to_lower = to_coin.lower()
        if to_lower == "usd":
            result = from_usd
        elif to_lower in prices and "usd" in prices[to_lower]:
            result = from_usd / prices[to_lower]["usd"]
        else:
            return {"ok": False, "error": f"no se pudo convertir a {to_coin}"}
        return {
            "ok": True,
            "from": {"coin": from_coin, "amount": amount},
            "to": {"coin": to_coin, "amount": result},
            "rate": result / amount if amount else 0,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Mercado global
# ---------------------------------------------------------------------------
def global_market() -> Dict[str, Any]:
    """Estadísticas globales del mercado crypto."""
    try:
        r = requests.get(f"{COINGECKO_BASE}/global", timeout=10)
        r.raise_for_status()
        d = r.json().get("data", {})
        return {
            "ok": True,
            "total_market_cap_usd": d.get("total_market_cap", {}).get("usd"),
            "total_volume_24h_usd": d.get("total_volume", {}).get("usd"),
            "active_cryptocurrencies": d.get("active_cryptocurrencies"),
            "market_cap_change_pct_24h": d.get("market_cap_change_percentage_24h_usd"),
            "btc_dominance_pct": d.get("market_cap_percentage", {}).get("btc"),
            "eth_dominance_pct": d.get("market_cap_percentage", {}).get("eth"),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def trending() -> Dict[str, Any]:
    """Criptos en tendencia (top 7 por búsquedas)."""
    try:
        r = requests.get(f"{COINGECKO_BASE}/search/trending", timeout=10)
        r.raise_for_status()
        coins = r.json().get("coins", [])
        return {
            "ok": True,
            "count": len(coins),
            "trending": [{"id": c["item"]["id"], "name": c["item"]["name"], "symbol": c["item"]["symbol"],
                          "rank": c["item"].get("market_cap_rank")} for c in coins],
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Histórico
# ---------------------------------------------------------------------------
def history(coin_id: str, vs_currency: str = "usd", days: int = 30) -> Dict[str, Any]:
    """Datos históricos (precio y market cap) de los últimos N días."""
    try:
        r = requests.get(f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                         params={"vs_currency": vs_currency, "days": days, "interval": "daily"},
                         timeout=15)
        r.raise_for_status()
        d = r.json()
        prices = d.get("prices", [])
        return {
            "ok": True,
            "coin": coin_id,
            "vs": vs_currency,
            "days": days,
            "first_price": prices[0][1] if prices else None,
            "last_price": prices[-1][1] if prices else None,
            "change_pct": ((prices[-1][1] / prices[0][1] - 1) * 100) if len(prices) >= 2 else None,
            "points": len(prices),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Wallet generation (offline, educacional)
# ---------------------------------------------------------------------------
def generate_wallet(network: str = "bitcoin") -> Dict[str, Any]:
    """
    Genera una dirección de wallet (SOLO EDUCACIONAL, no usa criptografía real).
    Para wallets reales usa bibliotecas como bitcoinlib, web3.py, etc.
    """
    if network == "bitcoin":
        return {
            "ok": True,
            "network": "bitcoin",
            "address": _fake_btc_address(),
            "warning": "DIRECCIÓN EDUCACIONAL. No usar para fondos reales.",
        }
    if network == "ethereum":
        return {
            "ok": True,
            "network": "ethereum",
            "address": "0x" + secrets.token_hex(20),
            "warning": "DIRECCIÓN EDUCACIONAL. No usar para fondos reales.",
        }
    if network == "solana":
        return {
            "ok": True,
            "network": "solana",
            "address": secrets.token_urlsafe(32)[:44],
            "warning": "DIRECCIÓN EDUCACIONAL. No usar para fondos reales.",
        }
    return {"ok": False, "error": f"red {network!r} no soportada (bitcoin, ethereum, solana)"}


def _fake_btc_address() -> str:
    """Genera un string con formato de dirección BTC (1xxx) - solo educacional."""
    return "1" + secrets.token_hex(20).lower()[:33]


# ---------------------------------------------------------------------------
# Análisis técnico simple
# ---------------------------------------------------------------------------
def technical_analysis(coin_id: str, vs_currency: str = "usd", days: int = 30) -> Dict[str, Any]:
    """SMA, EMA, RSI, soporte/resistencia básico."""
    hist = history(coin_id, vs_currency, days)
    if not hist["ok"]:
        return hist

    try:
        r = requests.get(f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                         params={"vs_currency": vs_currency, "days": days},
                         timeout=15)
        r.raise_for_status()
        prices = [p[1] for p in r.json().get("prices", [])]
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    if len(prices) < 14:
        return {"ok": False, "error": "datos insuficientes para análisis técnico"}

    sma_7 = sum(prices[-7:]) / 7
    sma_25 = sum(prices[-25:]) / min(25, len(prices))
    ema_12 = _ema(prices, 12)
    ema_26 = _ema(prices, 26)
    rsi = _rsi(prices, 14)
    support = min(prices[-30:])
    resistance = max(prices[-30:])

    return {
        "ok": True,
        "coin": coin_id,
        "vs": vs_currency,
        "sma_7": round(sma_7, 4),
        "sma_25": round(sma_25, 4),
        "ema_12": round(ema_12, 4),
        "ema_26": round(ema_26, 4),
        "rsi_14": round(rsi, 2),
        "support": round(support, 4),
        "resistance": round(resistance, 4),
        "current": round(prices[-1], 4),
        "signal": _rsi_signal(rsi),
    }


def _ema(prices: List[float], period: int) -> float:
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def _rsi(prices: List[float], period: int = 14) -> float:
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _rsi_signal(rsi: float) -> str:
    if rsi >= 70:
        return "SOBRECOMPRADO (>70)"
    if rsi <= 30:
        return "SOBREVENDIDO (<30)"
    if rsi >= 60:
        return "ALCISTA moderado"
    if rsi <= 40:
        return "BAJISTA moderado"
    return "NEUTRO"


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class CryptoTools:
    @staticmethod
    def price(coin_id: str, vs: str = "usd") -> Dict[str, Any]:
        return price(coin_id, vs)

    @staticmethod
    def prices(coin_ids: List[str], vs: str = "usd") -> Dict[str, Any]:
        return prices_batch(coin_ids, vs)

    @staticmethod
    def convert(from_coin: str, to_coin: str, amount: float) -> Dict[str, Any]:
        return convert(from_coin, to_coin, amount)

    @staticmethod
    def market() -> Dict[str, Any]:
        return global_market()

    @staticmethod
    def trending() -> Dict[str, Any]:
        return trending()

    @staticmethod
    def history(coin_id: str, days: int = 30) -> Dict[str, Any]:
        return history(coin_id, days=days)

    @staticmethod
    def analyze(coin_id: str, days: int = 30) -> Dict[str, Any]:
        return technical_analysis(coin_id, days=days)

    @staticmethod
    def generate_wallet(network: str = "bitcoin") -> Dict[str, Any]:
        return generate_wallet(network)
