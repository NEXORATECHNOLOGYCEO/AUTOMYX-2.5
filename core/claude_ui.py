"""
AUTOMYX CLAUDE-CODE STYLE TERMINAL UI
======================================
Professional terminal interface inspired by Claude Code.

Features:
- Inline code display with syntax highlighting
- File operation tracking (write, read, edit)
- Shell command execution display
- Token usage and timing
- Effort level indicator
- Branch indicator
- Plan mode
- Feedback system
"""
from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.box import ROUNDED, SIMPLE, HEAVY
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

try:
    from core.ui import (
        CYAN, BLUE, WHITE, GRAY, DIM, GREEN, YELLOW, RED, PURPLE,
        console as shared_console,
    )
except ImportError:
    CYAN = BLUE = WHITE = GRAY = DIM = GREEN = YELLOW = RED = PURPLE = ""
    shared_console = None


class ClaudeCodeUI:
    """
    Claude Code-style terminal UI for Automyx.
    
    Features:
    - Inline code display
    - File operation tracking
    - Shell command execution
    - Token/time tracking
    - Effort level
    - Branch indicator
    """
    
    def __init__(self):
        self.console = shared_console or Console()
        self.start_time = time.time()
        self.tokens_used = 0
        self.effort_level = "high"
        self.branch = self._get_git_branch()
        self.plan_mode = False
        self.file_operations: List[Dict[str, Any]] = []
        self.shell_commands: List[Dict[str, Any]] = []
        
    def _get_git_branch(self) -> str:
        """Get current git branch."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )
            return result.stdout.strip() if result.returncode == 0 else "main"
        except Exception:
            return "main"
    
    def display_file_write(self, file_path: str, content: str, line_count: int):
        """Display a file write operation like Claude Code."""
        self.file_operations.append({
            'type': 'write',
            'file': file_path,
            'lines': line_count,
            'timestamp': time.time()
        })
        
        # Show file write indicator
        self.console.print(f"\n[cyan]*[/cyan] [bold]Write({file_path})[/bold]")
        
        # Show code preview (first 10 lines)
        lines = content.split('\n')[:10]
        code_text = '\n'.join(lines)
        
        # Create code panel
        try:
            syntax = Syntax(code_text, "python", theme="monokai", line_numbers=True)
            self.console.print(Panel(
                syntax,
                title=f"[dim]L Wrote {line_count} lines to {file_path}[/dim]",
                border_style="dim",
                box=SIMPLE,
                padding=(0, 2)
            ))
        except Exception:
            self.console.print(f"[dim]  L Wrote {line_count} lines to {file_path}[/dim]")
            for i, line in enumerate(lines, 1):
                self.console.print(f"[dim]  {i:3d}[/dim] {line}")
        
        if len(lines) < line_count:
            self.console.print(f"[dim]  ... +{line_count - 10} lines[/dim]")
    
    def display_file_read(self, file_path: str, line_count: int):
        """Display a file read operation."""
        self.file_operations.append({
            'type': 'read',
            'file': file_path,
            'lines': line_count,
            'timestamp': time.time()
        })
        self.console.print(f"[green]*[/green] [bold]Read({file_path})[/bold] - {line_count} lines")
    
    def display_shell_command(self, command: str, output: Optional[str] = None):
        """Display a shell command execution."""
        self.shell_commands.append({
            'command': command,
            'output': output,
            'timestamp': time.time()
        })
        
        self.console.print(f"\n[cyan]Running 1 shell command...[/cyan]")
        self.console.print(f"[dim]  L $ {command}[/dim]")
        
        if output:
            self.console.print(f"[dim]  {output[:200]}[/dim]")
    
    def display_status(self, message: str, spinner: str = "dots"):
        """Display a status message with spinner."""
        self.console.print(f"\n[cyan]*[/cyan] {message}")
    
    def display_tokens_used(self, tokens: int):
        """Update token count."""
        self.tokens_used = tokens
    
    def display_effort_level(self, level: str):
        """Set effort level."""
        self.effort_level = level
    
    def display_plan_mode(self, enabled: bool):
        """Toggle plan mode."""
        self.plan_mode = enabled
        if enabled:
            self.console.print(f"\n[cyan]*[/cyan] [bold]Plan mode on[/bold] (shift+tab to cycle) · esc to interrupt")
        else:
            self.console.print(f"\n[dim]Plan mode off[/dim]")
    
    def display_bottom_bar(self):
        """Display the bottom status bar like Claude Code."""
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        
        # Branch indicator
        branch_text = f"[dim]{self.branch}[/dim]"
        
        # Effort level
        effort_text = f"[dim]{self.effort_level} · /effort[/dim]"
        
        # Token usage
        token_text = f"[dim]({minutes}m {seconds}s · down {self.tokens_used/1000:.1f}k tokens)[/dim]"
        
        # Plan mode
        plan_text = "[cyan]*[/cyan] [bold]plan mode on[/bold] (shift+tab to cycle) · esc to interrupt" if self.plan_mode else ""
        
        # Display bottom bar
        self.console.print()
        self.console.print(f"{branch_text} · {effort_text} · {token_text}")
        if plan_text:
            self.console.print(plan_text)
        self.console.print()
    
    def display_feedback_prompt(self):
        """Display feedback prompt like Claude Code."""
        self.console.print(f"\n[bold]How is Automyx doing this session? (optional)[/bold]")
        self.console.print(f"[dim]1: Bad    2: Fine    3: Good    0: Dismiss[/dim]")
    
    def display_summary(self, files_written: int, commands_run: int, duration: float):
        """Display session summary."""
        self.console.print(f"\n[green]*[/green] [bold]Session Summary[/bold]")
        self.console.print(f"[dim]  Files written: {files_written}[/dim]")
        self.console.print(f"[dim]  Commands run: {commands_run}[/dim]")
        self.console.print(f"[dim]  Duration: {duration:.1f}s[/dim]")
        self.console.print(f"[dim]  Tokens used: {self.tokens_used/1000:.1f}k[/dim]")


# Global UI instance
ui = ClaudeCodeUI()


def main():
    """Test the Claude Code UI."""
    ui.display_file_write(
        "explore6.py",
        """import paramiko

host = "72.62.164.42"
user = "root"
password = "#Ramon2026nexora"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password)""",
        27
    )
    
    ui.display_shell_command(
        "python explore7.py > explore7_out.txt 2>&1; echo done",
        "done"
    )
    
    ui.display_tokens_used(12600)
    ui.display_bottom_bar()
    ui.display_feedback_prompt()


if __name__ == '__main__':
    main()
