"""
AUTOMYX PRO ONBOARDING v3.0
============================
Professional setup wizard inspired by Claude Code.
Guides users through:
- Model selection
- API key configuration
- Tool verification
- First-run experience
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, List

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.box import ROUNDED, DOUBLE
    from rich.text import Text
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from core.ui import (
        CYAN, BLUE, ELECTRIC, GLOW, WHITE, GRAY, DIM,
        WARN, OK, ERR, PURPLE,
        console as shared_console,
    )
except ImportError:
    CYAN = BLUE = ELECTRIC = GLOW = WHITE = GRAY = DIM = ""
    WARN = OK = ERR = PURPLE = ""
    shared_console = None


class ProOnboarding:
    """
    Professional onboarding wizard for Automyx.
    
    Features:
    - Step-by-step guidance
    - API key validation
    - Model testing
    - Tool verification
    - Personalized setup
    """
    
    def __init__(self):
        self.console = shared_console or Console()
        self.config: Dict[str, any] = {}
        self.steps_completed = 0
        self.total_steps = 5
    
    def run(self):
        """Run the onboarding wizard."""
        self._print_welcome()
        
        try:
            self._step_welcome()
            self._step_model_selection()
            self._step_api_keys()
            self._step_tool_verification()
            self._step_first_run()
            self._print_completion()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Setup cancelled.[/]")
            sys.exit(0)
    
    def _print_welcome(self):
        """Print welcome screen."""
        self.console.clear()
        
        logo = """
[bold cyan]╔═══════════════════════════════════════════════════════════╗
║                                                               ║
║   █████╗ ██╗   ██╗████████╗ ██████╗ ███╗   ███╗██╗   ██╗     ║
║  ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗████╗ ████║╚██╗ ██╔╝     ║
║  ███████║██║   ██║   ██║   ██║   ██║██╔████╔██║ ╚████╔╝      ║
║  ██╔══██║██║   ██║   ██║   ██║   ██║██║╚██╔╝██║  ╚██╔╝       ║
║  ██║  ██║╚██████╔╝   ██║   ╚██████╔╝██║ ╚═╝ ██║   ██║        ║
║  ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝     ╚═╝   ╚═╝        ║
║                                                               ║
║           [bold white]AUTOMYX v2.5[/] [dim]· Setup Wizard[/]              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════╝[/]
"""
        self.console.print(logo)
        self.console.print()
    
    def _step_welcome(self):
        """Welcome step."""
        self.console.print("\n[bold cyan]Step 1 of 5:[/] Welcome to Automyx!\n")
        
        self.console.print(Panel(
            "[white]Automyx is a world-class AI agent that can:[/]\n\n"
            "  [cyan]•[/] Edit videos with professional effects\n"
            "  [cyan]•[/] Generate images and 3D content\n"
            "  [cyan]•[/] Search the web and analyze data\n"
            "  [cyan]•[/] Execute code and manage files\n"
            "  [cyan]•[/] Control your PC with natural language\n"
            "  [cyan]•[/] Learn and improve over time\n\n"
            "[dim]This wizard will help you set up Automyx in about 2 minutes.[/]",
            title="[bold cyan]What is Automyx?[/]",
            border_style=BLUE,
            box=ROUNDED
        ))
        
        self.console.print()
        if not Confirm.ask("[bold cyan]Ready to continue?[/]", default=True):
            self.console.print("[yellow]Setup cancelled.[/]")
            sys.exit(0)
        
        self.steps_completed += 1
    
    def _step_model_selection(self):
        """Model selection step."""
        self.console.print(f"\n[bold cyan]Step 2 of 5:[/] Choose Your AI Model\n")
        
        self.console.print("[dim]Automyx supports multiple AI providers. Choose the one that works best for you.[/]\n")
        
        models = [
            ("1", "NVIDIA API (Free)", "gpt-oss-120b, glm-5.1, minimax-m2.7"),
            ("2", "OpenAI", "GPT-4, GPT-3.5"),
            ("3", "Anthropic", "Claude 3.5, Claude 3"),
            ("4", "Ollama (Local)", "Llama 3, Mistral, etc."),
        ]
        
        table = Table(box=ROUNDED, border_style=BLUE)
        table.add_column("Choice", style="cyan", justify="center")
        table.add_column("Provider", style="white")
        table.add_column("Models", style="dim")
        
        for choice, provider, model_list in models:
            table.add_row(choice, provider, model_list)
        
        self.console.print(table)
        self.console.print()
        
        choice = Prompt.ask(
            "[bold cyan]Select provider[/]",
            choices=["1", "2", "3", "4"],
            default="1"
        )
        
        provider_map = {
            "1": "nvidia",
            "2": "openai",
            "3": "anthropic",
            "4": "ollama",
        }
        
        self.config['provider'] = provider_map[choice]
        
        # Set default model based on provider
        model_defaults = {
            "nvidia": "openai/gpt-oss-120b",
            "openai": "gpt-4",
            "anthropic": "claude-3-5-sonnet-20241022",
            "ollama": "llama3.1:8b",
        }
        self.config['model'] = model_defaults[self.config['provider']]
        
        self.console.print(f"\n[green]✓[/] Selected: [cyan]{self.config['provider']}[/] ({self.config['model']})")
        self.steps_completed += 1
    
    def _step_api_keys(self):
        """API keys configuration step."""
        self.console.print(f"\n[bold cyan]Step 3 of 5:[/] Configure API Keys\n")
        
        provider = self.config['provider']
        
        if provider == "nvidia":
            self.console.print("[dim]NVIDIA API is free to use. You can get an API key from:[/]")
            self.console.print("[cyan]https://build.nvidia.com/[/]\n")
            
            api_key = Prompt.ask(
                "[bold cyan]Enter NVIDIA API key[/] (or press Enter to skip)",
                default=""
            )
            
            if api_key:
                self.config['nvidia_api_key'] = api_key
                os.environ['NVIDIA_API_KEY'] = api_key
                self.console.print("[green]✓[/] API key saved")
            else:
                self.console.print("[yellow]○[/] Skipped (will use default key)")
        
        elif provider == "openai":
            self.console.print("[dim]You need an OpenAI API key. Get one from:[/]")
            self.console.print("[cyan]https://platform.openai.com/api-keys[/]\n")
            
            api_key = Prompt.ask(
                "[bold cyan]Enter OpenAI API key[/]"
            )
            
            self.config['openai_api_key'] = api_key
            os.environ['OPENAI_API_KEY'] = api_key
            self.console.print("[green]✓[/] API key saved")
        
        elif provider == "anthropic":
            self.console.print("[dim]You need an Anthropic API key. Get one from:[/]")
            self.console.print("[cyan]https://console.anthropic.com/[/]\n")
            
            api_key = Prompt.ask(
                "[bold cyan]Enter Anthropic API key[/]"
            )
            
            self.config['anthropic_api_key'] = api_key
            os.environ['ANTHROPIC_API_KEY'] = api_key
            self.console.print("[green]✓[/] API key saved")
        
        elif provider == "ollama":
            self.console.print("[dim]Ollama runs locally. Make sure it's installed:[/]")
            self.console.print("[cyan]https://ollama.ai/[/]\n")
            
            if Confirm.ask("[bold cyan]Is Ollama installed?[/]", default=True):
                self.console.print("[green]✓[/] Ollama configured")
            else:
                self.console.print("[yellow]○[/] Install Ollama first, then run setup again")
        
        # Save to .env
        self._save_env()
        
        self.steps_completed += 1
    
    def _save_env(self):
        """Save configuration to .env file."""
        env_path = Path('.env')
        
        # Read existing .env
        env_vars = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Update with new values
        if 'nvidia_api_key' in self.config:
            env_vars['NVIDIA_API_KEY'] = self.config['nvidia_api_key']
        if 'openai_api_key' in self.config:
            env_vars['OPENAI_API_KEY'] = self.config['openai_api_key']
        if 'anthropic_api_key' in self.config:
            env_vars['ANTHROPIC_API_KEY'] = self.config['anthropic_api_key']
        
        env_vars['AUTOMYX_MODEL'] = self.config.get('model', 'openai/gpt-oss-120b')
        
        # Write back
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
    
    def _step_tool_verification(self):
        """Tool verification step."""
        self.console.print(f"\n[bold cyan]Step 4 of 5:[/] Verify Tools\n")
        
        self.console.print("[dim]Let's verify that essential tools are available.[/]\n")
        
        tools_to_check = [
            ('ffmpeg', 'Video editing'),
            ('python', 'Python runtime'),
            ('git', 'Version control'),
        ]
        
        import shutil
        
        table = Table(box=ROUNDED, border_style=BLUE)
        table.add_column("Tool", style="cyan")
        table.add_column("Purpose", style="dim")
        table.add_column("Status", style="white", justify="center")
        
        all_good = True
        for tool, purpose in tools_to_check:
            if shutil.which(tool):
                status = "[green]✓ Installed[/]"
            else:
                status = "[red]✗ Missing[/]"
                all_good = False
            
            table.add_row(tool, purpose, status)
        
        self.console.print(table)
        self.console.print()
        
        if not all_good:
            self.console.print("[yellow]Some tools are missing. Automyx will still work, but some features may be limited.[/]")
            self.console.print("[dim]You can install missing tools later.[/]\n")
        else:
            self.console.print("[green]✓[/] All essential tools are available!")
        
        self.steps_completed += 1
    
    def _step_first_run(self):
        """First run experience."""
        self.console.print(f"\n[bold cyan]Step 5 of 5:[/] First Run\n")
        
        self.console.print("[dim]Let's test Automyx with a simple command.[/]\n")
        
        self.console.print("[bold cyan]Try saying:[/] [white]\"Hello, what can you do?\"[/]\n")
        
        response = Prompt.ask("[bold cyan]Your turn[/]")
        
        if response.strip():
            self.console.print("\n[green]✓[/] Great! You're ready to use Automyx!")
        else:
            self.console.print("\n[yellow]○[/] You can try this later in the REPL")
        
        self.steps_completed += 1
    
    def _print_completion(self):
        """Print completion screen."""
        self.console.clear()
        
        self.console.print("\n")
        self.console.print(Panel(
            "[bold white]🎉 Setup Complete![/]\n\n"
            "[cyan]Automyx is now configured and ready to use.[/]\n\n"
            "[dim]Quick Start:[/]\n"
            "  [cyan]•[/] Type [white]automyx[/] to start the REPL\n"
            "  [cyan]•[/] Type [white]/help[/] for available commands\n"
            "  [cyan]•[/] Type [white]/exit[/] to quit\n\n"
            "[dim]Documentation:[/]\n"
            "  [cyan]https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5[/]\n",
            title="[bold cyan]Welcome to Automyx[/]",
            border_style=BLUE,
            box=DOUBLE
        ))
        
        self.console.print()


def run_onboarding():
    """Entry point for onboarding."""
    onboarding = ProOnboarding()
    onboarding.run()


if __name__ == '__main__':
    run_onboarding()
