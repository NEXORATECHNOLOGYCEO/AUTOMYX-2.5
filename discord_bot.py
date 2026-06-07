"""
Automyx 2.5 — Discord Channel
=============================
Real Discord bot using discord.py v2.3+. Supports DMs, server mentions,
text + image attachments, and slash commands.

Requirements:
  pip install discord.py
  Set DISCORD_BOT_TOKEN in .env

Docs: https://discordpy.readthedocs.io/
"""
from __future__ import annotations

import os
import sys
import io
import base64
import asyncio
import requests
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

GATEWAY_URL = "http://127.0.0.1:3500/api/gateway/inbound"


def get_token():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print(f"{Fore.RED}[X] Falta DISCORD_BOT_TOKEN en .env{Style.RESET_ALL}")
        sys.exit(1)
    return token


def get_gateway_token():
    try:
        from core.config import config
        return config.get_gateway_token()
    except Exception:
        return ""


try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print(f"{Fore.RED}[X] discord.py no instalado. pip install discord.py{Style.RESET_ALL}")


def build_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    return bot


def process_message(content: str, attachments: list, gw_token: str) -> str:
    """Envía el mensaje (con imágenes) al gateway y devuelve la respuesta."""
    images = []
    for att in attachments:
        # Filtrar solo imágenes
        if att.content_type and att.content_type.startswith("image/"):
            try:
                r = requests.get(att.url, timeout=15)
                if r.status_code == 200:
                    images.append({
                        "data": "data:" + att.content_type + ";base64," + base64.b64encode(r.content).decode("ascii"),
                        "mime": att.content_type,
                    })
            except Exception:
                pass

    user_msg = content
    if not user_msg and images:
        user_msg = "[El usuario envió una imagen sin texto]"

    payload = {
        "channel": "discord",
        "sender_id": "dm",  # Se completa en el handler
        "message": user_msg,
        "agent_id": "main",
    }
    if images:
        payload["images"] = images
        if content:
            payload["message"] = content + f"\n\n[Adjuntó {len(images)} imagen(es)]"

    r = requests.post(
        GATEWAY_URL,
        json=payload,
        headers={"X-Gateway-Token": gw_token},
        timeout=180,
    )
    if r.status_code == 200:
        data = r.json()
        return data.get("reply", "⚠️ Sin respuesta del agente.") or "⚠️ El agente no devolvió respuesta."
    return f"❌ Gateway error {r.status_code}"


def setup_handlers(bot: "commands.Bot"):
    gw_token_holder = {"value": get_gateway_token()}

    @bot.event
    async def on_ready():
        print(f"{Fore.GREEN}✅ Discord bot conectado como {bot.user} (id={bot.user.id}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}   Servidores: {len(bot.guilds)}{Style.RESET_ALL}")
        # Refrescar el gateway token (puede haber cambiado)
        gw_token_holder["value"] = get_gateway_token()
        # Sync slash commands
        try:
            synced = await bot.tree.sync()
            print(f"{Fore.CYAN}   {len(synced)} slash commands sincronizados{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}   No se pudieron sincronizar slash commands: {e}{Style.RESET_ALL}")

    @bot.event
    async def on_message(message: "discord.Message"):
        # Ignorar mensajes del propio bot
        if message.author == bot.user:
            return
        # Solo responder a DMs o menciones al bot
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = bot.user in message.mentions
        if not (is_dm or is_mentioned):
            return
        # Quitar la mención del texto
        content = message.content
        if is_mentioned and bot.user:
            content = content.replace(f"@{bot.user.name}", "").strip()
        if not gw_token_holder["value"]:
            await message.channel.send("❌ Gateway token no configurado.")
            return
        # Indicador "escribiendo..."
        async with message.channel.typing():
            try:
                atts = list(message.attachments)
                # Para evitar bloquear el event loop, corremos en executor
                loop = asyncio.get_event_loop()
                reply = await loop.run_in_executor(
                    None, process_message, content, atts, gw_token_holder["value"]
                )
            except Exception as e:
                reply = f"❌ Error: {e}"
        # Discord límite 2000 chars por mensaje
        for i in range(0, len(reply), 1990):
            await message.channel.send(reply[i:i + 1990])
        # Procesar comandos (!) si los hay
        await bot.process_commands(message)

    @bot.tree.command(name="status", description="Muestra el estado del agente Automyx")
    async def status(interaction: "discord.Interaction"):
        await interaction.response.defer(thinking=True)
        try:
            r = requests.get(
                "http://127.0.0.1:3500/api/agent/status",
                headers={"X-Gateway-Token": gw_token_holder["value"]},
                timeout=5,
            )
            if r.status_code == 200:
                st = r.json()
                phase = st.get("phase", "?")
                is_active = st.get("is_active", False)
                await interaction.followup.send(
                    f"🤖 **Automyx Status**\n"
                    f"• Fase: `{phase}`\n"
                    f"• Activo: {'✅' if is_active else '❌'}\n"
                    f"• Gateway: online"
                )
            else:
                await interaction.followup.send(f"⚠️ Gateway HTTP {r.status_code}")
        except Exception as e:
            await interaction.followup.send(f"❌ Gateway caído: {e}")

    @bot.tree.command(name="model", description="Cambia el modelo de IA para esta sesión")
    async def model(interaction: "discord.Interaction", model_name: str):
        """Uso: /model gpt-4o"""
        # En una versión completa guardaríamos en estado de usuario
        await interaction.response.send_message(f"🧠 Modelo configurado: `{model_name}` (próximamente persistente)")

    @bot.command(name="ping")
    async def ping(ctx: "commands.Context"):
        latency = round(bot.latency * 1000)
        await ctx.send(f"🏓 Pong! Latencia: {latency}ms")


def main():
    if not DISCORD_AVAILABLE:
        sys.exit(1)
    token = get_token()
    bot = build_bot()
    setup_handlers(bot)
    print(f"{Fore.YELLOW}🤖 Automyx Discord bot arrancando...{Style.RESET_ALL}")
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
