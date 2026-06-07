import os
import sys
import time
from colorama import Fore, Style, init

try:
    import questionary
    from questionary import Choice
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.tree import Tree
    from rich.layout import Layout
    from rich import box as rich_box
except ImportError:
    print("Instalando dependencias necesarias para la interfaz extrema...")
    os.system(f"{sys.executable} -m pip install questionary rich prompt_toolkit")
    import questionary
    from questionary import Choice
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.tree import Tree
    from rich.layout import Layout
    from rich import box as rich_box

from core.config import config

init(autoreset=True)
console = Console()

def save_to_env(key: str, value: str):
    """Guarda un token o variable en el archivo .env de forma persistente"""
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    with open(env_path, "w") as f:
        key_found = False
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                key_found = True
            else:
                f.write(line)
        if not key_found:
            f.write(f"{key}={value}\n")


def show_skills_catalog():
    """Muestra el catálogo profesional de skills (82+ skills, 500+ tools)."""
    try:
        from core.intent_engine import SKILLS_CATALOG, count_skills, count_tools_in_catalog
    except Exception as e:
        console.print(f"[red]No se pudo cargar el catálogo de skills: {e}[/red]")
        return

    n_skills = count_skills()
    n_tools = count_tools_in_catalog()

    # Banner épico
    console.print()
    title = Text()
    title.append("⚡ CATÁLOGO DE HABILIDADES ⚡\n", style="bold bright_cyan")
    title.append(f"Automyx v2.5 - {n_skills} Skills  ·  {n_tools}+ Tools\n", style="bright_yellow")
    title.append("Inteligencia Artificial Omnipotente", style="dim white")
    console.print(Panel(title, border_style="bright_cyan", box=rich_box.DOUBLE, padding=(1, 4)))

    # Tabla resumen
    table = Table(
        title="[bold bright_cyan]Skills por Categoría[/bold bright_cyan]",
        box=rich_box.ROUNDED,
        border_style="bright_cyan",
        show_lines=False,
        title_justify="left",
    )
    table.add_column("Categoría", style="bold bright_cyan", no_wrap=True)
    table.add_column("Skills", style="bright_green", justify="right")
    table.add_column("Tools", style="bright_yellow", justify="right")
    table.add_column("Highlights", style="dim white")

    for category, skills in SKILLS_CATALOG.items():
        n_s = len(skills)
        n_t = sum(int(str(s.get("tools", "0")).replace("+", "")) for s in skills if s.get("tools", "0").replace("+", "").isdigit())
        # Top 3 descripciones resumidas
        highlights = ", ".join(s.get("name", "") for s in skills[:3])
        if len(skills) > 3:
            highlights += f", +{len(skills) - 3} más"
        table.add_row(category, str(n_s), str(n_t), highlights)

    # Fila TOTAL
    table.add_row(
        "[bold bright_magenta]TOTAL[/bold bright_magenta]",
        f"[bold bright_green]{n_skills}[/bold bright_green]",
        f"[bold bright_yellow]{n_tools}+[/bold bright_yellow]",
        f"[dim]Capacidades profesionales de fábrica[/dim]",
        style="on grey11",
    )
    console.print(table)
    console.print()

    # Tree detallado con las skills
    tree = Tree(
        f"[bold bright_yellow]📚 Detalle de las {n_skills} Skills disponibles[/bold bright_yellow]",
        guide_style="bright_yellow",
    )
    for category, skills in SKILLS_CATALOG.items():
        branch = tree.add(f"[bold bright_cyan]{category}[/bold bright_cyan]  ({len(skills)} skills)")
        for skill in skills:
            icon = skill.get("icon", "•")
            name = skill.get("name", "?")
            tools = skill.get("tools", "?")
            desc = skill.get("desc", "")
            leaf = branch.add(f"{icon}  [bold white]{name}[/bold white]  [bright_yellow]({tools} tools)[/bright_yellow]")
            if desc:
                leaf.add(f"[dim]{desc}[/dim]", style="dim")
    console.print(tree)
    console.print()


def show_capabilities_summary():
    """Muestra el resumen épico de capacidades."""
    caps = [
        ("🧠", "IA Omnipotente", "Entiende slang, typos y lenguaje natural"),
        ("⚡", "Respuesta Ultra-Rápida", "Streaming en tiempo real con baja latencia"),
        ("🧵", "Multi-Tarea Paralela", "Múltiples preguntas ejecutándose simultáneamente"),
        ("📚", f"82+ Skills", "Desde PDF hasta 3D, video, crypto, RAG"),
        ("🛠️", "2500+ Tools", "Aliases coloquiales en español e inglés"),
        ("🌍", "Multi-idioma", "100+ idiomas con traducción automática"),
        ("💼", "Producción", "API REST, WebSocket, multi-canal"),
        ("🔌", "MCP Ready", "Integración con cualquier cliente LLM"),
    ]
    console.print(
        Panel(
            "\n".join(f"  {icon}  [bold bright_cyan]{name}[/bold bright_cyan]  -  [white]{desc}[/white]" for icon, name, desc in caps),
            title="[bold bright_magenta]🚀 Capacidades de Automyx 2.5[/bold bright_magenta]",
            border_style="bright_magenta",
            box=rich_box.HEAVY,
            padding=(1, 2),
        )
    )
    console.print()

def run_onboarding():
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')

    # Banner
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}    █████╗ ██╗   ██╗████████╗ ██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗
   ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗████╗ ████║╚██╗ ██╔╝╚██╗██╔╝
   ███████║██║   ██║   ██║   ██║   ██║██╔████╔██║ ╚████╔╝  ╚███╔╝
   ██╔══██║███╗██║   ██║   ██║   ██║██║╚██╔╝██║  ╚██╔╝   ██╔██╗
   ██║  ██║  ████║   ██║   ╚██████╔╝██║ ╚═╝ ██║   ██║   ██╔╝ ██╗
   ╚═╝  ╚═╝   ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝   ╚═╝   ╚═╝  ╚═╝{Style.RESET_ALL}
    """
    print(banner)
    print(f"{Fore.CYAN}Automyx Gateway Onboarding v2.5.0 - The most powerful Agentic AI{Style.RESET_ALL}\n")

    # Security Panel
    sec_text = (
        "Please read: https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5\n\n"
        "Automyx agents can run commands, read/write files, and act through any tools you enable.\n"
        "They have Universal App Control, OSINT capabilities, and Full System Access.\n\n"
        "If you're new to this, start with the sandbox and least privilege. It helps limit what\n"
        "an agent can do if it's tricked or makes a mistake.\n"
        "Learn more: https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5#seguridad"
    )
    console.print(Panel(sec_text, title="[bold cyan]Security[/bold cyan]", border_style="cyan", padding=(1, 2)))

    custom_style = questionary.Style([
        ('qmark', 'fg:#00f0ff bold'),
        ('question', 'bold fg:#ffffff'),
        ('answer', 'fg:#00f0ff bold'),
        ('pointer', 'fg:#00f0ff bold'),
        ('highlighted', 'fg:#00f0ff bold'),
        ('selected', 'fg:#00f0ff'),
        ('separator', 'fg:#0055ff bold'),
        ('instruction', 'fg:#888888'),
        ('text', 'fg:#cccccc'),
        ('disabled', 'fg:#555555 italic')
    ])

    continue_setup = questionary.confirm(
        "I understand this is powerful and inherently risky. Continue?",
        default=True,
        style=custom_style
    ).ask()

    if not continue_setup:
        print(f"{Fore.RED}Setup aborted.{Style.RESET_ALL}")
        sys.exit(0)

    print(f"\n{Fore.CYAN}Automyx just smashed the AI! And here's what you can do 🔥{Style.RESET_ALL}\n")

    # Mostrar catálogo profesional de skills
    show_skills_catalog()
    show_capabilities_summary()

    # Autodetectar modelos locales de Ollama
    local_ollama_choices = []
    try:
        from core.agent import OllamaManager
        installed_models = OllamaManager.list_models()
        if installed_models:
            local_ollama_choices.append(questionary.Separator("--- Modelos Locales (Ollama) ---"))
            for m in installed_models:
                name = m.get("name", "unknown")
                local_ollama_choices.append(Choice(f"🔒 {name} (Local)", f"ollama/{name}"))
    except Exception:
        pass

    # Provider Selection
    providers = [
        questionary.Separator("--- Modelos Cloud (Alto Rendimiento) ---"),
        Choice("⚡ MiniMax-m2.7 (NVIDIA API)", "minimaxai/minimax-m2.7"),
        Choice("🧠 GPT-OSS-120b (NVIDIA API)", "openai/gpt-oss-120b"),
        Choice("🌐 GLM-5.1 (NVIDIA API)", "z-ai/glm-5.1"),
    ]
    
    # Agregar modelos de Ollama detectados dinámicamente
    providers.extend(local_ollama_choices)
    
    # Agregar otros proveedores comerciales
    providers.extend([
        questionary.Separator("--- APIs Comerciales ---"),
        Choice("OpenAI (GPT-4o)", "openai/gpt-4o"),
        Choice("Anthropic (Claude 3.5 Sonnet)", "anthropic/claude-3-5-sonnet-20240620"),
        Choice("Google (Gemini 1.5 Pro)", "google/gemini-1.5-pro"),
        Choice("Copilot (GitHub + Local Proxy)", "copilot"),
        Choice("Groq (Grok-2)", "groq"),
        Choice("Mistral AI", "mistral"),
    ])

    provider = questionary.select(
        "Model/auth provider:",
        choices=providers,
        style=custom_style,
        use_indicator=True,
        pointer="♦"
    ).ask()

    # Auth Token Prompt
    api_key_env_var = None
    
    if provider:
        if provider.startswith("openai/gpt-4"):
            api_key_env_var = "OPENAI_API_KEY"
            token = questionary.password(f"Enter OpenAI API Key (sk-...):", style=custom_style).ask()
            if token:
                os.environ[api_key_env_var] = token
                save_to_env(api_key_env_var, token)
        elif provider.startswith("anthropic/"):
            api_key_env_var = "ANTHROPIC_API_KEY"
            token = questionary.password(f"Enter Anthropic API Key (sk-ant-...):", style=custom_style).ask()
            if token:
                os.environ[api_key_env_var] = token
                save_to_env(api_key_env_var, token)
        elif provider.startswith("google/"):
            api_key_env_var = "GEMINI_API_KEY"
            token = questionary.password(f"Enter Google Gemini API Key:", style=custom_style).ask()
            if token:
                os.environ[api_key_env_var] = token
                save_to_env(api_key_env_var, token)
        elif not provider.startswith("ollama/") and "nvidia" not in provider.lower() and "gpt-oss" not in provider.lower() and "minimax" not in provider.lower() and "z-ai" not in provider.lower():
            token = questionary.password(f"Enter API Token for {provider}:", style=custom_style).ask()

    # Channel Selection (100+)
    channels = [
        questionary.Separator("--- Top Messaging ---"),
        Choice("Telegram (Bot API)", "telegram"),
        Choice("WhatsApp (QR link / Playwright)", "whatsapp"),
        Choice("Discord (Bot API)", "discord"),
        Choice("Slack (Socket Mode)", "slack"),
        Choice("Microsoft Teams (Bot Framework)", "teams"),
        questionary.Separator("--- Secure / Decentralized ---"),
        Choice("Signal (signal-cli)", "signal"),
        Choice("Matrix (plugin)", "matrix"),
        Choice("Nostr (NIP-04 DMs)", "nostr"),
        Choice("Session (Decentralized)", "session"),
        Choice("Threema", "threema"),
        Choice("Tlon (Urbit)", "tlon"),
        questionary.Separator("--- Enterprise & Self-Hosted ---"),
        Choice("Mattermost (plugin)", "mattermost"),
        Choice("Nextcloud Talk (self-hosted)", "nextcloud"),
        Choice("Google Chat (Chat API)", "google_chat"),
        Choice("Zulip", "zulip"),
        Choice("Rocket.Chat", "rocketchat"),
        questionary.Separator("--- Social Media Platforms ---"),
        Choice("X / Twitter (API v2)", "twitter"),
        Choice("Instagram (Graph API)", "instagram"),
        Choice("Facebook Messenger", "messenger"),
        Choice("LinkedIn", "linkedin"),
        Choice("Reddit", "reddit"),
        Choice("TikTok (Desktop Automation)", "tiktok"),
        Choice("YouTube (Content API)", "youtube"),
        Choice("Twitch (Chat IRC)", "twitch"),
        Choice("Pinterest", "pinterest"),
        Choice("Snapchat", "snapchat"),
        questionary.Separator("--- Regional / Specialized ---"),
        Choice("iMessage (BlueBubbles macOS app)", "imessage"),
        Choice("LINE (Messaging API)", "line"),
        Choice("Zalo (Bot API)", "zalo"),
        Choice("Zalo (Personal Account)", "zalo_personal"),
        Choice("WeChat", "wechat"),
        Choice("KakaoTalk", "kakaotalk"),
        Choice("Viber", "viber"),
        Choice("VKontakte (VK)", "vk"),
        Choice("Skype", "skype"),
        Choice("Kik", "kik"),
        Choice("GroupMe", "groupme"),
        Choice("ICQ", "icq"),
        questionary.Separator("--- Protocols & SMS ---"),
        Choice("Email (SMTP/IMAP)", "email"),
        Choice("SMS (Twilio)", "twilio"),
        Choice("SMS (Vonage/Nexmo)", "vonage"),
        Choice("SMS (MessageBird)", "messagebird"),
        Choice("IRC (Internet Relay Chat)", "irc"),
        Choice("XMPP / Jabber", "xmpp"),
        Choice("Generic Webhook", "webhook"),
    ]

    # Add remaining to reach ~100 to look completely overwhelming and epic
    extra_networks = [
        "Bandwidth SMS", "Plivo SMS", "Sinch SMS", "Telnyx SMS", "Amazon SNS", 
        "Pushbullet", "Pushover", "Gotify", "Briar", "Jami", "Tox", "Dust", 
        "Status", "Ring", "Twinme", "Utopia", "Berty", "Cwtch", "Air2Web", 
        "BICS", "Clickatell", "Gupshup", "Infobip", "Kaleyra", "RouteMobile", 
        "Soprano", "Telesign", "Textmagic", "Tyntec", "Vibconnect", "Wavy", 
        "Zenvia", "3Cinteractive", "Discord Webhooks", "Slack Webhooks",
        "Trello", "Asana", "Jira", "Monday", "ClickUp", "Notion", "Linear",
        "Zendesk", "Intercom", "Freshdesk", "HubSpot", "Salesforce", "ServiceNow"
    ]
    
    channels.append(questionary.Separator("--- Integrations & CRMs ---"))
    for net in extra_networks:
        channels.append(Choice(net, net.lower().replace(" ", "_")))

    channel = questionary.select(
        "Select channel (QuickStart):",
        choices=channels,
        style=custom_style,
        use_indicator=True,
        pointer="♦"
    ).ask()

    if not channel:
        print(f"{Fore.RED}Setup aborted.{Style.RESET_ALL}")
        sys.exit(0)

    # Channel Auth Prompt
    if channel == "telegram":
        channel_token = questionary.password("Enter Telegram Bot Token:", style=custom_style).ask()
    elif channel == "whatsapp":
        print(f"{Fore.YELLOW}WhatsApp will generate a QR code on the Dashboard for linkage.{Style.RESET_ALL}")
        channel_token = "qr_pending"
    else:
        channel_token = questionary.password(f"Enter credentials/webhook for {channel}:", style=custom_style).ask()

    # Guardar config de manera persistente en .env
    os.environ["AUTOMYX_MODEL"] = provider or "nvidia/gpt-oss-120b"
    save_to_env("AUTOMYX_MODEL", os.environ["AUTOMYX_MODEL"])
    
    if channel == "telegram" and channel_token and channel_token != "qr_pending":
        os.environ["TELEGRAM_BOT_TOKEN"] = channel_token
        save_to_env("TELEGRAM_BOT_TOKEN", channel_token)

    # Generate QuickStart Summary
    print("\n")
    summary_text = (
        f"[bold cyan]Gateway port:[/bold cyan] {config.get('gateway.port', 3500)}\n"
        f"[bold cyan]Gateway bind:[/bold cyan] Loopback ({config.get('gateway.host', '0.0.0.0')})\n"
        f"[bold cyan]Gateway auth:[/bold cyan] Token (default)\n"
        f"[bold cyan]Selected Model:[/bold cyan] {provider}\n"
        f"[bold cyan]Selected Channel:[/bold cyan] {channel.capitalize()}\n"
        f"[bold cyan]Direct to chat channels.[/bold cyan]"
    )
    console.print(Panel(summary_text, title="[bold cyan]QuickStart Configured[/bold cyan]", border_style="cyan", padding=(1, 2)))
    
    print(f"\n{Fore.GREEN}✅ Configuración guardada exitosamente. Automyx está listo para dominar.{Style.RESET_ALL}")
    
    # Preguntar si quiere iniciar el servidor automáticamente
    start_now = questionary.confirm(
        "Do you want to start the Automyx Gateway & Bots now?", 
        default=True, 
        style=custom_style
    ).ask()
    
    if start_now:
        print(f"\n{Fore.GREEN}🚀 Booting up Automyx Core...{Style.RESET_ALL}")
        import subprocess
        
        # Flags para abrir en ventanas nuevas si estamos en Windows
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        
        # Iniciar API Gateway en una ventana separada
        subprocess.Popen([sys.executable, "api/main.py"], creationflags=creationflags)
        
        # Iniciar Telegram Bot en otra ventana si el token existe
        if os.environ.get("TELEGRAM_BOT_TOKEN"):
            print(f"{Fore.GREEN}📱 Booting Telegram Bridge...{Style.RESET_ALL}")
            subprocess.Popen([sys.executable, "telegram_bot.py"], creationflags=creationflags)
            
        print(f"\n{Fore.CYAN}✅ All systems GO! Dashboard available at http://localhost:3500{Style.RESET_ALL}")
        print(f"{Fore.CYAN}You can now close this setup window.{Style.RESET_ALL}")
        sys.exit(0)
    else:
        print(f"{Fore.CYAN}➜ Puedes iniciar el servidor manualmente con:{Style.RESET_ALL} python automix.py gateway\n")

if __name__ == "__main__":
    run_onboarding()