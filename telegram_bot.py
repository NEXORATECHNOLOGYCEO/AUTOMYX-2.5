import os
import sys
import io
import base64
import tempfile
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from colorama import Fore, Style, init

# Forzar codificación UTF-8 para evitar errores en Windows con emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

init(autoreset=True)

# Cargar .env manualmente de forma ultra robusta
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    os.environ[parts[0]] = parts[1]

# Configuraciones
GATEWAY_URL = "http://127.0.0.1:3500/api/gateway/inbound"
HEALTH_URL = "http://127.0.0.1:3500/api/health"
USER_MODELS = {} # Memoria temporal del modelo elegido por el usuario


# Reusable HTTP session with automatic retry/backoff for transient errors.
def _build_session() -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=4, pool_maxsize=8)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    sess.headers.update({"Connection": "keep-alive"})
    return sess


SESSION = _build_session()


def _gateway_alive(timeout: float = 3.0) -> bool:
    """Chequeo barato con /api/health (no requiere auth)."""
    try:
        r = SESSION.get(HEALTH_URL, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def get_telegram_token():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    # Si no está en las variables de entorno, intentamos buscarlo en config.json
    if not token:
        try:
            import json
            with open("state/automyx.sqlite", "r") as f: # solo comprobacion rapida
                pass
            # Intentar cargar desde el entorno de .env
            from core.config import config
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
        except:
            pass

    if not token:
        print(f"{Fore.RED}[X] Error: No se encontró la variable TELEGRAM_BOT_TOKEN.{Style.RESET_ALL}")
        print("Por favor, ve al Dashboard de Automyx > Canales, ingresa tu Token de Telegram y guarda.")
        print("O ejecuta: set TELEGRAM_BOT_TOKEN=tu_token (en Windows)")
        exit(1)
    return token

def get_gateway_token():
    # Leer el token del gateway desde SQLite o .env si es necesario, 
    # pero por simplicidad usaremos la conexión local. Si tu gateway exige token, 
    # asegúrate de pasarlo en los headers.
    try:
        from core.config import config
        return config.get_gateway_token()
    except:
        return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user = update.effective_user
    welcome_msg = (
        f"🤖 ¡Hola {user.first_name}! Soy Automyx.\n\n"
        "Estoy conectado directamente a tu computadora.\n"
        "Puedes pedirme que cree archivos, analice datos, edite videos, abra programas o haga OSINT.\n\n"
        "¿En qué te puedo ayudar hoy?"
    )
    await update.message.reply_text(welcome_msg)

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /model para elegir el cerebro de la IA desde Telegram"""
    keyboard = [
        [InlineKeyboardButton("⚡ MiniMax-m2.7 (NVIDIA API)", callback_data="model:minimaxai/minimax-m2.7")],
        [InlineKeyboardButton("🧠 GPT-OSS-120b (NVIDIA API)", callback_data="model:openai/gpt-oss-120b")],
        [InlineKeyboardButton("🌐 GLM-5.1 (NVIDIA API)", callback_data="model:z-ai/glm-5.1")],
        [InlineKeyboardButton("🔮 Kimi K2.6 (NVIDIA API)", callback_data="model:moonshotai/kimi-k2.6")],
        [InlineKeyboardButton("🔒 Llama 3 (Local Ollama)", callback_data="model:ollama/llama3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 **Automyx Core**\nSelecciona el modelo de Inteligencia Artificial que deseas usar en esta sesión:", reply_markup=reply_markup, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las selecciones de botones en Telegram"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("model:"):
        selected_model = data.split("model:")[1]
        user_id = str(query.from_user.id)
        USER_MODELS[user_id] = selected_model
        await query.edit_message_text(text=f"✅ **Modelo actualizado a:** `{selected_model}`\nAutomyx usará este cerebro a partir de ahora.", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto entrantes y los envía al Gateway de Automyx"""
    user_msg = update.message.text or ""
    chat_id = str(update.message.chat_id)
    user_name = update.effective_user.first_name

    print(f"{Fore.CYAN}[Telegram] Recibido de {user_name}: {user_msg}{Style.RESET_ALL}")

    # Enviar un mensaje de "Escribiendo..." para dar feedback
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    except Exception:
        pass

    # Pre-chequeo: ¿el gateway está vivo?
    gw_token = get_gateway_token()
    if not gw_token:
        await update.message.reply_text(
            "❌ No se encontró el token del gateway.\n"
            "Ve al Dashboard de Automyx > Ajustes y verifica el Gateway Token."
        )
        return

    try:
        # Probe rápido al gateway (sin auth) con retry automático
        try:
            probe = SESSION.get(HEALTH_URL, timeout=5)
            if probe.status_code != 200:
                await update.message.reply_text(
                    f"⚠️ El Gateway responde con HTTP {probe.status_code}.\n"
                    "Puede que esté arrancando o caído. Intenta de nuevo en unos segundos."
                )
                return
        except requests.exceptions.ConnectionError:
            await update.message.reply_text(
                "❌ No se puede conectar con Automyx Gateway (127.0.0.1:3500).\n\n"
                "Asegúrate de que el servidor esté corriendo:\n"
                "  python automix.py gateway\n\n"
                "O desde el Dashboard > botón Iniciar Gateway."
            )
            return
        except requests.exceptions.Timeout:
            await update.message.reply_text(
                "⏱️ El Gateway no responde (timeout 5s). Está sobrecargado o caído."
            )
            return
        except Exception as e:
            # No bloqueamos si el probe falla por algo raro, seguimos al POST
            print(f"{Fore.YELLOW}[Telegram] probe falló pero seguimos: {e}{Style.RESET_ALL}")

        headers = {"X-Gateway-Token": gw_token}

        # Recuperar el modelo elegido por el usuario, si lo hay
        selected_model = USER_MODELS.get(str(update.effective_user.id), None)

        # Detectar si el mensaje incluye imágenes
        images_payload = []
        try:
            if update.message.photo:
                # Telegram envía varias resoluciones; tomamos la mayor
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                buf = await file.download_as_bytearray()
                images_payload.append({
                    "data": "data:image/jpeg;base64," + base64.b64encode(bytes(buf)).decode("ascii"),
                    "mime": "image/jpeg",
                })
                user_msg = (user_msg + "\n\n[El usuario adjuntó 1 foto]").strip()
            elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith("image/"):
                doc = update.message.document
                file = await context.bot.get_file(doc.file_id)
                buf = await file.download_as_bytearray()
                images_payload.append({
                    "data": f"data:{doc.mime_type};base64," + base64.b64encode(bytes(buf)).decode("ascii"),
                    "mime": doc.mime_type,
                })
                user_msg = (user_msg + f"\n\n[El usuario adjuntó imagen: {doc.file_name or 'archivo'}]").strip()
        except Exception as e:
            print(f"{Fore.YELLOW}[Telegram] no se pudo descargar imagen: {e}{Style.RESET_ALL}")

        payload = {
            "channel": "telegram",
            "sender_id": chat_id,
            "message": user_msg,
            "agent_id": "main",
            "model": selected_model,
            # Modo async para que el gateway responda rápido y no se cierre
            # la conexión de Telegram si el agente tarda mucho.
            "async_exec": True,
        }
        if images_payload:
            payload["images"] = images_payload

        # POST inicial: si el gateway lo acepta como async, devuelve 202 + task_id
        try:
            response = SESSION.post(GATEWAY_URL, json=payload, headers=headers, timeout=10)
        except requests.exceptions.ConnectionError:
            await update.message.reply_text(
                "❌ Se cayó la conexión con el Gateway mientras procesaba tu mensaje. "
                "Inténtalo de nuevo."
            )
            return
        except requests.exceptions.Timeout:
            await update.message.reply_text(
                "⏱️ El Gateway no aceptó la solicitud (timeout 10s). Reintentando…"
            )
            try:
                response = SESSION.post(GATEWAY_URL, json=payload, headers=headers, timeout=20)
            except Exception:
                await update.message.reply_text("❌ Gateway no responde, reintenta en unos segundos.")
                return

        # --- MODO ASYNC: polling del resultado ---
        if response.status_code == 202 or (response.status_code == 200 and response.json().get("status") == "accepted"):
            try:
                data = response.json()
            except Exception:
                data = {}
            task_id = data.get("task_id")
            if not task_id:
                # No se pudo obtener task_id → fallback a síncrono
                pass
            else:
                # Poll for up to 50s
                poll_url = f"http://127.0.0.1:3500/api/gateway/result/{task_id}"
                deadline = time.time() + 50
                reply_text = None
                while time.time() < deadline:
                    await __import__("asyncio").sleep(1.5)
                    try:
                        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
                    except Exception:
                        pass
                    try:
                        pr = SESSION.get(poll_url, params={"wait": 5}, headers=headers, timeout=10)
                    except Exception:
                        continue
                    if pr.status_code != 200:
                        continue
                    try:
                        pd = pr.json()
                    except Exception:
                        continue
                    st = pd.get("status")
                    if st == "done":
                        reply_text = pd.get("reply")
                        break
                    if st == "error":
                        await update.message.reply_text(
                            f"❌ El Gateway reportó un error:\n\n{str(pd.get('error', ''))[:600]}"
                        )
                        return
                if reply_text is None:
                    # Timeout pero la tarea sigue corriendo → guardamos task_id
                    # y avisamos al usuario que seguimos trabajando.
                    await update.message.reply_text(
                        f"⏳ Sigo trabajando en tu mensaje… (tarea `{task_id}`). "
                        "Te aviso en cuanto termine."
                    )
                    return
                # Tenemos respuesta
                if not reply_text:
                    await update.message.reply_text("⚠️ El agente devolvió una respuesta vacía.")
                    return
                if len(reply_text) > 4000:
                    for i in range(0, len(reply_text), 4000):
                        await update.message.reply_text(reply_text[i:i+4000])
                else:
                    await update.message.reply_text(reply_text)
                print(f"{Fore.GREEN}[Telegram] Respondido a {user_name} ({len(reply_text)} chars){Style.RESET_ALL}")
                return

        # --- MODO SÍNCRONO (fallback) ---

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                await update.message.reply_text(
                    f"❌ El Gateway devolvió una respuesta no-JSON:\n{response.text[:500]}"
                )
                return

            # Si el gateway devolvió un error embebido, mostrarlo
            if isinstance(data, dict) and data.get("error") and not data.get("reply"):
                err = str(data.get("error", ""))[:600]
                await update.message.reply_text(
                    f"❌ El Gateway reportó un error:\n\n{err}"
                )
                print(f"{Fore.RED}[Gateway error] {err}{Style.RESET_ALL}")
                return

            reply = data.get("reply") if isinstance(data, dict) else None

            # Si la respuesta es None o vacía
            if not reply:
                # Diagnóstico adicional: mirar agent_status
                try:
                    status_res = requests.get(
                        "http://127.0.0.1:3500/api/agent/status",
                        headers={"X-Gateway-Token": gw_token},
                        timeout=5,
                    )
                    if status_res.status_code == 200:
                        st = status_res.json()
                        phase = st.get("phase", "?")
                        action = st.get("current_action", "")
                        err_msg = st.get("error_message", "")
                        if err_msg:
                            await update.message.reply_text(
                                f"⚠️ El agente no produjo respuesta.\n"
                                f"Fase: {phase}\n"
                                f"Acción: {action}\n"
                                f"Error: {err_msg[:400]}"
                            )
                            return
                except Exception:
                    pass

                await update.message.reply_text(
                    "⚠️ El agente no devolvió respuesta (posible timeout del LLM o modelo no disponible).\n"
                    "Prueba con /model para cambiar de cerebro, o revisa los logs del Gateway."
                )
                print(f"{Fore.YELLOW}[Telegram] reply vacío de gateway{Style.RESET_ALL}")
                return

            # Limpiar la respuesta de JSONs crudos por si acaso
            import re
            json_regex = re.compile(r'```(?:json)?\s*(\{[\s\S]*?"action"[\s\S]*?\})\s*```', re.IGNORECASE)
            reply = json_regex.sub('', reply).strip()

            if not reply:
                reply = "✅ Tarea ejecutada en el sistema."

            # Telegram tiene límite de 4096 chars; truncar con aviso
            if len(reply) > 4000:
                reply = reply[:3950] + "\n\n…[truncado, respuesta muy larga]"

            await update.message.reply_text(reply)
            print(f"{Fore.GREEN}[Automyx] Respuesta enviada a Telegram ({len(reply)} chars).{Style.RESET_ALL}")
        else:
            # 401, 403, 422, 500, etc.
            body = response.text[:500] if response.text else "(sin cuerpo)"
            if response.status_code in (401, 403):
                error_msg = (
                    f"🔒 Token del Gateway rechazado (HTTP {response.status_code}).\n\n"
                    "Verifica que el token en Telegram coincida con el del Gateway.\n"
                    "Dashboard > Ajustes > Gateway Token."
                )
            elif response.status_code == 422:
                error_msg = (
                    f"⚠️ El Gateway no entendió el mensaje (HTTP 422).\n"
                    f"Detalle: {body}"
                )
            else:
                error_msg = f"❌ Error del Gateway: HTTP {response.status_code}\n{body}"
            await update.message.reply_text(error_msg)
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")

    except requests.exceptions.ConnectionError:
        await update.message.reply_text(
            "❌ No se puede conectar con Automyx Gateway (127.0.0.1:3500).\n\n"
            "Asegúrate de que esté corriendo:\n"
            "  python automix.py gateway"
        )
        print(f"{Fore.RED}[Telegram] ConnectionError al gateway{Style.RESET_ALL}")
    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ El Gateway tardó demasiado en responder (>180s).\n"
            "El agente puede estar atascado. Revisa los logs del Gateway."
        )
        print(f"{Fore.RED}[Telegram] Timeout al gateway{Style.RESET_ALL}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        error_msg = f"❌ Error inesperado en Telegram bot:\n{type(e).__name__}: {str(e)[:400]}"
        await update.message.reply_text(error_msg)
        print(f"{Fore.RED}[Telegram] {error_msg}\n{tb}{Style.RESET_ALL}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler dedicado para fotos sin texto adjunto."""
    if not update.message.caption:
        # Sin caption: tratamos como "describe esta imagen"
        update.message.text = "[El usuario envió una imagen sin texto]"
    await handle_message(update, context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status: muestra el estado del gateway y del agente"""
    gw_token = get_gateway_token()
    if not gw_token:
        await update.message.reply_text("❌ Token del Gateway no configurado.")
        return

    msg = "🔍 *Estado de Automyx*\n\n"

    # Probe al gateway
    try:
        r = requests.get(
            "http://127.0.0.1:3500/api/agent/status",
            headers={"X-Gateway-Token": gw_token},
            timeout=5,
        )
        if r.status_code == 200:
            st = r.json()
            phase = st.get("phase", "?")
            is_active = st.get("is_active", False)
            step = st.get("step", 0)
            total = st.get("total_steps", 0)
            err = st.get("error_message", "")
            tool = st.get("tool_name", "")

            msg += f"✅ Gateway: ONLINE\n"
            msg += f"🤖 Agente: {'ACTIVO' if is_active else 'inactivo'}\n"
            msg += f"📊 Fase: `{phase}`\n"
            msg += f"🔄 Iteración: {step}/{total}\n"
            if tool:
                msg += f"🔧 Tool: `{tool}`\n"
            if err:
                msg += f"⚠️ Error: `{err[:200]}`\n"
        elif r.status_code in (401, 403):
            msg += f"🔒 Gateway alcanzable pero token rechazado (HTTP {r.status_code})\n"
        else:
            msg += f"⚠️ Gateway responde HTTP {r.status_code}\n"
    except requests.exceptions.ConnectionError:
        msg += "❌ Gateway: CAÍDO (no se puede conectar a 127.0.0.1:3500)\n"
        msg += "Inicia con: `python automix.py gateway`\n"
    except requests.exceptions.Timeout:
        msg += "⏱️ Gateway: timeout\n"
    except Exception as e:
        msg += f"❌ Error: {type(e).__name__}: {str(e)[:200]}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    token = get_telegram_token()
    print(f"{Fore.YELLOW}Iniciando puente de comunicación Telegram <-> Automyx...{Style.RESET_ALL}")
    
    # Construir la aplicación
    application = Application.builder().token(token).build()

    # Manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(
        filters.Document.ALL & ~filters.COMMAND,
        handle_message,
    ))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Iniciar el bot
    print(f"{Fore.GREEN}✅ Automyx Telegram Bot está en línea y escuchando.{Style.RESET_ALL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
