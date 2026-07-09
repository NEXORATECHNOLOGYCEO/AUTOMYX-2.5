"""
AUTONOMY MODEL SELECTOR
=========================
First-time model selection screen for AUTONOMY.

When AUTONOMY starts, it shows a beautiful model selection screen
where the user can pick their base model.
"""
from __future__ import annotations

import os
import sys
from typing import Optional, List, Dict, Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.box import ROUNDED, DOUBLE
    from rich.prompt import Prompt
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


# All available models organized by provider
MODEL_CATALOG = {
    "NVIDIA API (Free)": [
        {"name": "openai/gpt-oss-120b", "description": "Recommended · Free · Best for coding"},
        {"name": "minimaxai/minimax-m2.7", "description": "Free · Multimodal"},
        {"name": "z-ai/glm-5.1", "description": "Free · Bilingual"},
        {"name": "moonshotai/kimi-k2.6", "description": "Free · 256K context"},
        {"name": "nvidia/llama-3.1-nemotron-70b-instruct", "description": "Free · Reasoning"},
        {"name": "nvidia/nemotron-4-340b-instruct", "description": "Free · Large context"},
        {"name": "meta/llama-3.3-70b-instruct", "description": "Free · General purpose"},
        {"name": "mistralai/mistral-large-2-instruct", "description": "Free · Multilingual"},
    ],
    "Anthropic Claude": [
        {"name": "claude-3-5-sonnet-20241022", "description": "Best overall · Requires API key"},
        {"name": "claude-3-5-haiku-20241022", "description": "Fast and cheap · Requires API key"},
        {"name": "claude-3-opus-20240229", "description": "Most capable · Requires API key"},
        {"name": "claude-3-sonnet-20240229", "description": "Balanced · Requires API key"},
        {"name": "claude-3-haiku-20240307", "description": "Fastest · Requires API key"},
    ],
    "OpenAI": [
        {"name": "gpt-4o", "description": "Most capable · Requires API key"},
        {"name": "gpt-4o-mini", "description": "Fast and cheap · Requires API key"},
        {"name": "gpt-4-turbo", "description": "High performance · Requires API key"},
        {"name": "o1-preview", "description": "Reasoning · Requires API key"},
        {"name": "o1-mini", "description": "Reasoning, smaller · Requires API key"},
    ],
}


class ModelSelector:
    """
    First-time model selection screen for AUTONOMY.
    
    Shows a beautiful interactive menu where the user can pick
    their preferred base model.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or (Console() if Console else None)
        self.selected_model = None
        self.all_models: List[Dict[str, Any]] = []
        self._build_model_list()
    
    def _build_model_list(self):
        """Build flat list of all models with indices."""
        for provider, models in MODEL_CATALOG.items():
            for model in models:
                self.all_models.append({
                    "provider": provider,
                    "name": model["name"],
                    "description": model["description"]
                })
    
    def display(self):
        """Display the model selection screen."""
        if not self.console:
            return
        
        self.console.clear()
        
        # Header
        self.console.print(f"[bold red]── AUTONOMY v6.0 · Model Selection ──────────────────────────────────────[/bold red]")
        self.console.print()
        
        # Welcome message
        self.console.print(Panel(
            "[bold white]Welcome to AUTONOMY![/bold white]\n\n"
            "AUTONOMY is the most autonomous AI agent ever created.\n"
            "Choose your base model to get started.\n\n"
            "[dim]You can change the model anytime with /model command.[/dim]",
            title="[bold red]Base Model Selection[/bold red]",
            border_style="red",
            box=DOUBLE,
            padding=(1, 2)
        ))
        self.console.print()
        
        # Display models by provider
        idx = 1
        model_indices = {}
        
        for provider, models in MODEL_CATALOG.items():
            # Provider header
            if "Free" in provider:
                self.console.print(f"[bold cyan]{provider}[/bold cyan] [dim](No API key needed)[/dim]")
            else:
                self.console.print(f"[bold cyan]{provider}[/bold cyan] [dim](API key required)[/dim]")
            
            for model in models:
                # Truncate description for display
                desc = model["description"]
                if len(desc) > 45:
                    desc = desc[:42] + "..."
                
                # Number with color
                num_color = "green" if "Free" in provider else "yellow"
                self.console.print(f"  [dim][{num_color}]{idx:2d}[/{num_color}][/dim] [white]{model['name']:<45}[/white] [dim]{desc}[/dim]")
                model_indices[idx] = model["name"]
                idx += 1
            self.console.print()
        
        # Custom model option
        custom_idx = idx
        self.console.print(f"  [dim][yellow]{custom_idx:2d}[/yellow][/dim] [white]Custom model name[/white]")
        model_indices[custom_idx] = "__custom__"
        idx += 1
        
        # Use previous / env option
        default_idx = idx
        self.console.print(f"  [dim][yellow]{default_idx:2d}[/yellow][/dim] [white]Use default (env AUTOMYX_MODEL or openai/gpt-oss-120b)[/white]")
        model_indices[default_idx] = "__default__"
        
        self.console.print()
        self.console.print(f"  [dim]Total: {len(self.all_models) + 2} options[/dim]")
        self.console.print()
    
    def ask(self) -> str:
        """
        Show the model selection screen and ask user to choose.
        Returns the selected model name.
        """
        if not self.console:
            return "openai/gpt-oss-120b"
        
        self.display()
        
        total_options = len(self.all_models) + 2
        
        try:
            choice = Prompt.ask(
                f"[bold cyan]Select base model (1-{total_options})[/bold cyan]",
                default="1"
            )
            idx = int(choice)
            
            if idx == len(self.all_models) + 1:
                # Custom model
                custom = Prompt.ask("[bold cyan]Enter custom model name[/bold cyan]")
                return custom
            elif idx == len(self.all_models) + 2:
                # Default
                return os.environ.get("AUTOMYX_MODEL", "openai/gpt-oss-120b")
            elif 1 <= idx <= len(self.all_models):
                # Selected model
                return self.all_models[idx - 1]["name"]
            else:
                return "openai/gpt-oss-120b"
        except (ValueError, KeyboardInterrupt):
            return "openai/gpt-oss-120b"
    
    def quick_select(self) -> str:
        """Quick select default model without showing the full menu."""
        return os.environ.get("AUTOMYX_MODEL", "openai/gpt-oss-120b")


def main():
    """Test the model selector."""
    console = Console() if Console else None
    selector = ModelSelector(console=console)
    
    if "--show" in sys.argv:
        # Just show the screen
        selector.display()
    else:
        # Interactive selection
        model = selector.ask()
        console.print(f"\n[green]Selected model:[/] {model}")


if __name__ == '__main__':
    main()
