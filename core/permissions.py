"""
AUTOMYX PERMISSIONS SYSTEM
===========================
Manages permissions for dangerous operations.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, List, Set
from enum import Enum

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.box import ROUNDED
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from core.ui import (
        CYAN, BLUE, WHITE, GRAY, DIM, WARN, OK, ERR,
        console as shared_console,
    )
except ImportError:
    CYAN = BLUE = WHITE = GRAY = DIM = WARN = OK = ERR = ""
    shared_console = None


class PermissionLevel(Enum):
    """Permission levels for operations."""
    SAFE = "safe"
    NORMAL = "normal"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


class PermissionManager:
    """
    Manages permissions for operations.
    
    Features:
    - Pattern-based permission rules
    - Always allow/deny lists
    - Interactive confirmation prompts
    - Session-based permissions
    """
    
    # Default permission rules
    DEFAULT_RULES = [
        # Safe operations
        {"pattern": r"read_file|list_directory|glob_file", "level": "safe", "description": "Read operations"},
        {"pattern": r"web_search|deep_web_scrape", "level": "safe", "description": "Web search"},
        
        # Normal operations
        {"pattern": r"write_file|create_directory", "level": "normal", "description": "File creation"},
        {"pattern": r"execute_cmd", "level": "normal", "description": "Command execution"},
        
        # Caution operations
        {"pattern": r"delete_file|move_file", "level": "caution", "description": "File modification"},
        {"pattern": r"open_program|open_website", "level": "caution", "description": "Open applications"},
        
        # Dangerous operations
        {"pattern": r"system_shutdown|system_restart", "level": "dangerous", "description": "System operations"},
        {"pattern": r"format_disk|wipe_data", "level": "dangerous", "description": "Data destruction"},
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        self.console = shared_console or Console()
        self.config_path = config_path or Path.home() / ".automyx" / "permissions.json"
        self.rules: List[Dict] = self.DEFAULT_RULES.copy()
        self.always_allow: Set[str] = set()
        self.always_deny: Set[str] = set()
        self.session_permissions: Set[str] = set()
        
        self._load_config()
    
    def _load_config(self):
        """Load permission configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.always_allow = set(data.get('always_allow', []))
                    self.always_deny = set(data.get('always_deny', []))
            except Exception:
                pass
    
    def _save_config(self):
        """Save permission configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump({
                    'always_allow': list(self.always_allow),
                    'always_deny': list(self.always_deny),
                }, f, indent=2)
        except Exception:
            pass
    
    def needs_permission(self, operation: str) -> bool:
        """Check if an operation needs permission."""
        import re
        
        # Check always deny
        for pattern in self.always_deny:
            if re.search(pattern, operation, re.IGNORECASE):
                return True
        
        # Check always allow
        for pattern in self.always_allow:
            if re.search(pattern, operation, re.IGNORECASE):
                return False
        
        # Check session permissions
        for pattern in self.session_permissions:
            if re.search(pattern, operation, re.IGNORECASE):
                return False
        
        # Check rules
        for rule in self.rules:
            if re.search(rule['pattern'], operation, re.IGNORECASE):
                return rule['level'] != 'safe'
        
        # Default: needs permission
        return True
    
    def get_permission_level(self, operation: str) -> PermissionLevel:
        """Get the permission level for an operation."""
        import re
        
        for rule in self.rules:
            if re.search(rule['pattern'], operation, re.IGNORECASE):
                return PermissionLevel(rule['level'])
        
        return PermissionLevel.CAUTION
    
    def request_permission(self, operation: str) -> bool:
        """Request permission for an operation."""
        level = self.get_permission_level(operation)
        
        if level == PermissionLevel.SAFE:
            return True
        
        # Show permission prompt
        self.console.print()
        
        if level == PermissionLevel.NORMAL:
            self.console.print(f"  [#00AAFF]i[/] About to execute: [white]{operation}[/]")
        elif level == PermissionLevel.CAUTION:
            self.console.print(f"  [#FF8C00]![/] This operation requires caution: [white]{operation}[/]")
        elif level == PermissionLevel.DANGEROUS:
            self.console.print(f"  [#FF3333]![/] DANGEROUS operation: [white]{operation}[/]")
        
        # Try to use questionary for a beautiful interactive prompt
        try:
            import questionary
            from questionary import Choice
            
            # Custom style for the prompt (Blue and Orange)
            custom_style = questionary.Style([
                ('qmark', 'fg:#00AAFF bold'),       # question mark
                ('question', 'fg:#FFFFFF bold'),    # question text
                ('answer', 'fg:#00AAFF bold'),      # submitted answer text behind the question
                ('pointer', 'fg:#FF8C00 bold'),     # pointer used in select and checkbox prompts
                ('highlighted', 'fg:#00AAFF bold'), # pointed-at choice in select and checkbox prompts
                ('selected', 'fg:#FF8C00'),         # style for a selected item of a checkbox
                ('separator', 'fg:#3A5070'),        # separator in lists
                ('instruction', 'fg:#888888'),      # user instructions for select, rawselect, checkbox
                ('text', 'fg:#FFFFFF'),             # plain text
                ('disabled', 'fg:#888888 italic')   # disabled choices for select and checkbox prompts
            ])
            
            response = questionary.select(
                "Do you want to allow this operation?",
                choices=[
                    Choice("Yes, allow this time", "y"),
                    Choice("Always allow this type of operation", "a"),
                    Choice("No, deny this time", "n"),
                    Choice("Always deny this type of operation", "d"),
                ],
                style=custom_style
            ).ask()
            
            if response is None: # user pressed Ctrl+C
                return False
                
        except ImportError:
            # Fallback if questionary is not installed
            self.console.print()
            self.console.print("[dim]Options:[/]")
            self.console.print("  [#00AAFF]y[/] - Allow this time")
            self.console.print("  [#00AAFF]a[/] - Always allow this type of operation")
            self.console.print("  [#00AAFF]n[/] - Deny this time")
            self.console.print("  [#00AAFF]d[/] - Always deny this type of operation")
            self.console.print()
            
            try:
                if RICH_AVAILABLE:
                    response = Prompt.ask("[bold #00AAFF]❯[/]", choices=['y', 'a', 'n', 'd'], default='n')
                else:
                    response = input("❯ ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return False
        
        if response == 'y':
            return True
        elif response == 'a':
            self.always_allow.add(operation)
            self._save_config()
            self.console.print("  [#33FF57]✓[/] Operation added to always allow list")
            return True
        elif response == 'n':
            return False
        elif response == 'd':
            self.always_deny.add(operation)
            self._save_config()
            self.console.print("  [#FF8C00]✓[/] Operation added to always deny list")
            return False
        
        return False
    
    def add_always_allow(self, pattern: str):
        """Add a pattern to always allow."""
        self.always_allow.add(pattern)
        self._save_config()
    
    def add_always_deny(self, pattern: str):
        """Add a pattern to always deny."""
        self.always_deny.add(pattern)
        self._save_config()
    
    def add_session_permission(self, pattern: str):
        """Add a permission for this session only."""
        self.session_permissions.add(pattern)
    
    def clear_session_permissions(self):
        """Clear all session permissions."""
        self.session_permissions.clear()
    
    def display(self):
        """Display current permission settings."""
        self.console.print("\n[bold cyan]Permission Settings:[/]\n")
        
        # Always allow
        self.console.print("[bold green]Always Allow:[/]")
        if self.always_allow:
            for pattern in sorted(self.always_allow):
                self.console.print(f"  [green]✓[/] {pattern}")
        else:
            self.console.print(f"  [dim](none)[/]")
        
        # Always deny
        self.console.print("\n[bold red]Always Deny:[/]")
        if self.always_deny:
            for pattern in sorted(self.always_deny):
                self.console.print(f"  [red]✗[/] {pattern}")
        else:
            self.console.print(f"  [dim](none)[/]")
        
        # Session permissions
        self.console.print("\n[bold cyan]Session Permissions:[/]")
        if self.session_permissions:
            for pattern in sorted(self.session_permissions):
                self.console.print(f"  [cyan]⊕[/] {pattern}")
        else:
            self.console.print(f"  [dim](none)[/]")
        
        # Rules
        self.console.print("\n[bold cyan]Permission Rules:[/]")
        table = Table(box=ROUNDED, border_style=BLUE)
        table.add_column("Pattern", style="cyan")
        table.add_column("Level", style="white")
        table.add_column("Description", style="dim")
        
        for rule in self.rules:
            level_color = {
                "safe": "green",
                "normal": "cyan",
                "caution": "yellow",
                "dangerous": "red",
            }[rule['level']]
            
            table.add_row(
                rule['pattern'],
                f"[{level_color}]{rule['level']}[/]",
                rule['description']
            )
        
        self.console.print(table)
        self.console.print()


def main():
    """Test the permission manager."""
    pm = PermissionManager()
    pm.display()
    
    # Test some operations
    test_ops = [
        "read_file('test.py')",
        "delete_file('test.py')",
        "execute_cmd('rm -rf /')",
        "system_shutdown()",
    ]
    
    for op in test_ops:
        print(f"\nOperation: {op}")
        print(f"Needs permission: {pm.needs_permission(op)}")
        print(f"Level: {pm.get_permission_level(op)}")


if __name__ == '__main__':
    main()
