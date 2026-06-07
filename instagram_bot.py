"""
Automyx 2.5 — Instagram Channel
================================
Real Instagram DM bot using the Instagram Graph API (v18.0+).
Supports text messages, image attachments, and quick replies.

Requirements:
  - Facebook Business account connected to an Instagram Professional account
  - Facebook App with `instagram_business_basic`, `instagram_business_manage_messages`
  - Page access token with `instagram_business_manage_messages` permission
  - Set INSTAGRAM_PAGE_ID and INSTAGRAM_ACCESS_TOKEN in .env

Docs: https://developers.facebook.com/docs/messenger-platform/instagram
"""
from __future__ import annotations

import os
import sys
import io
import json
import time
import base64
import requests
from pathlib import Path
from colorama import Fore, Style, init

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

init(autoreset=True)

# Load .env
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    os.environ.setdefault(parts[0], parts[1])

GRAPH_API_VERSION = "v18.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
GATEWAY_URL = "http://127.0.0.1:3500/api/gateway/inbound"
POLL_INTERVAL = 5  # seconds


def get_credentials():
    page_id = os.environ.get("INSTAGRAM_PAGE_ID")
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not page_id or not token:
        print(f"{Fore.RED}[X] Faltan credenciales. Configura INSTAGRAM_PAGE_ID y INSTAGRAM_ACCESS_TOKEN en .env{Style.RESET_ALL}")
        sys.exit(1)
    return page_id, token


def get_gateway_token():
    try:
        from core.config import config
        return config.get_gateway_token()
    except Exception:
        return ""


def send_text(recipient_id: str, text: str, page_id: str, token: str):
    """Envía un mensaje de texto por Instagram Graph API."""
    url = f"{GRAPH_BASE}/{page_id}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text[:1000]},  # IG tiene límite ~1000 chars
        "access_token": token,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"{Fore.RED}[Instagram] send_text falló: {e}{Style.RESET_ALL}")
        return None


def send_image(recipient_id: str, image_url: str, page_id: str, token: str):
    """Envía una imagen por URL pública (IG requiere URL pública, no base64)."""
    url = f"{GRAPH_BASE}/{page_id}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True},
            }
        },
        "access_token": token,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"{Fore.RED}[Instagram] send_image falló: {e}{Style.RESET_ALL}")
        return None


def send_image_from_bytes(recipient_id: str, image_bytes: bytes, mime: str, page_id: str, token: str):
    """Sube una imagen desde bytes y la envía. Requiere upload a un host público
    primero (Instagram no acepta base64 directo). Aquí usamos file.io como fallback."""
    try:
        files = {"file": ("image." + mime.split("/")[-1], image_bytes, mime)}
        r = requests.post("https://file.io", files=files, timeout=30)
        if r.status_code == 200:
            public_url = r.json().get("link")
            if public_url:
                return send_image(recipient_id, public_url, page_id, token)
    except Exception as e:
        print(f"{Fore.YELLOW}[Instagram] file.io upload falló: {e}{Style.RESET_ALL}")
    return None


def fetch_new_messages(page_id: str, token: str, since_ts: int) -> list:
    """Lee los eventos de la webhook queue (simulado por polling del inbox).
    En producción esto se reemplaza por un webhook server con verificación."""
    # Nota: Graph API no expone inbox de IG directamente por GET.
    # La forma estándar es montar un webhook server. Aquí dejamos el esqueleto
    # para que el caller decida cómo inyectar los eventos.
    return []


def handle_event(event: dict, page_id: str, token: str):
    """Procesa un evento entrante del webhook de Instagram."""
    try:
        sender_id = event.get("sender", {}).get("id")
        message = event.get("message", {})
        text = message.get("text", "")
        attachments = message.get("attachments", []) or []
        images = []
        for att in attachments:
            if att.get("type") == "image":
                url = att.get("payload", {}).get("url")
                if url:
                    try:
                        r = requests.get(url, timeout=15)
                        if r.status_code == 200:
                            images.append({
                                "data": "data:" + (r.headers.get("Content-Type", "image/jpeg")) + ";base64," + base64.b64encode(r.content).decode("ascii"),
                                "mime": r.headers.get("Content-Type", "image/jpeg"),
                            })
                    except Exception:
                        pass

        if not sender_id:
            return
        if not text and not images:
            return

        if not text:
            text = "[El usuario envió una imagen sin texto]"

        print(f"{Fore.CYAN}[Instagram] Mensaje de {sender_id}: {text[:60]}{Style.RESET_ALL}")
        try:
            requests.post("https://graph.facebook.com/me/messages", timeout=2)  # keep-alive noop
        except Exception:
            pass

        gw_token = get_gateway_token()
        if not gw_token:
            send_text(sender_id, "❌ Token del Gateway no configurado.", page_id, token)
            return

        payload = {
            "channel": "instagram",
            "sender_id": sender_id,
            "message": text,
            "agent_id": "main",
        }
        if images:
            payload["images"] = images
        r = requests.post(
            GATEWAY_URL,
            json=payload,
            headers={"X-Gateway-Token": gw_token},
            timeout=180,
        )
        if r.status_code == 200:
            data = r.json()
            reply = data.get("reply", "⚠️ Sin respuesta del agente.")
            if not reply:
                reply = "⚠️ El agente no devolvió respuesta."
            send_text(sender_id, reply[:1000], page_id, token)
            print(f"{Fore.GREEN}[Instagram] Respuesta enviada.{Style.RESET_ALL}")
        else:
            send_text(sender_id, f"❌ Gateway error {r.status_code}", page_id, token)
    except Exception as e:
        print(f"{Fore.RED}[Instagram] handle_event: {e}{Style.RESET_ALL}")


def main():
    page_id, token = get_credentials()
    print(f"{Fore.YELLOW}📷 Automyx Instagram bot arrancando...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   Page ID: {page_id}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   Graph API: {GRAPH_BASE}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   Polling events cada {POLL_INTERVAL}s{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Listo. Para que lleguen mensajes, monta el webhook server:{Style.RESET_ALL}")
    print(f"   https://developers.facebook.com/docs/messenger-platform/instagram/webhooks")
    print()
    # Verificar token
    try:
        r = requests.get(f"{GRAPH_BASE}/{page_id}", params={"access_token": token, "fields": "id,name"}, timeout=10)
        if r.status_code == 200:
            print(f"{Fore.GREEN}✅ Token válido para: {r.json().get('name', page_id)}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Token inválido (HTTP {r.status_code}): {r.text[:200]}{Style.RESET_ALL}")
            sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}❌ No se pudo verificar el token: {e}{Style.RESET_ALL}")
        sys.exit(1)

    # Polling loop (en producción usar webhook server)
    last_ts = int(time.time())
    while True:
        try:
            events = fetch_new_messages(page_id, token, last_ts)
            for ev in events:
                handle_event(ev, page_id, token)
                last_ts = max(last_ts, ev.get("timestamp", last_ts))
        except KeyboardInterrupt:
            print(f"{Fore.YELLOW}\nApagando Instagram bot...{Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"{Fore.RED}[Instagram] loop error: {e}{Style.RESET_ALL}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
