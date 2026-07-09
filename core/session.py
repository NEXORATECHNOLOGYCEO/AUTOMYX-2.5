"""
AUTOMYX SESSION MANAGEMENT
===========================
Manages persistent sessions with command history and conversation context.
"""
from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.box import ROUNDED
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from core.ui import (
        CYAN, BLUE, WHITE, GRAY, DIM,
        console as shared_console,
    )
except ImportError:
    CYAN = BLUE = WHITE = GRAY = DIM = ""
    shared_console = None


class SessionManager:
    """
    Manages Automyx sessions.
    
    Features:
    - Persistent session storage
    - Command history
    - Conversation context
    - Multiple sessions
    - Session metadata
    """
    
    def __init__(self, sessions_dir: Optional[Path] = None):
        self.console = shared_console or Console()
        self.sessions_dir = sessions_dir or Path.home() / ".automyx" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_id: str = self._generate_session_id()
        self.history: List[str] = []
        self.context: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'message_count': 0,
        }
        
        self._load()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = int(time.time())
        return f"session_{timestamp}"
    
    def _get_session_path(self) -> Path:
        """Get the path to the current session file."""
        return self.sessions_dir / f"{self.session_id}.json"
    
    def _load(self):
        """Load the current session from file."""
        session_path = self._get_session_path()
        if session_path.exists():
            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
                    self.context = data.get('context', {})
                    self.metadata = data.get('metadata', self.metadata)
            except Exception:
                pass
    
    def save(self):
        """Save the current session to file."""
        self.metadata['updated_at'] = datetime.now().isoformat()
        self.metadata['message_count'] = len(self.history)
        
        session_path = self._get_session_path()
        try:
            with open(session_path, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'history': self.history,
                    'context': self.context,
                    'metadata': self.metadata,
                }, f, indent=2)
        except Exception as e:
            self.console.print(f"[red]Error saving session:[/] {e}")
    
    def load(self, session_id: Optional[str] = None):
        """Load a session."""
        if session_id:
            self.session_id = session_id
        self._load()
        self.console.print(f"[green]✓[/] Session loaded: [cyan]{self.session_id}[/]")
    
    def new(self):
        """Create a new session."""
        self.session_id = self._generate_session_id()
        self.history = []
        self.context = {}
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'message_count': 0,
        }
        self.console.print(f"[green]✓[/] New session created: [cyan]{self.session_id}[/]")
    
    def add_to_history(self, message: str):
        """Add a message to the history."""
        self.history.append(message)
        self.metadata['message_count'] = len(self.history)
    
    def set_context(self, key: str, value: Any):
        """Set a context value."""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)
    
    def list_sessions(self):
        """List all available sessions."""
        self.console.print("\n[bold cyan]Available Sessions:[/]\n")
        
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    sessions.append({
                        'id': data.get('session_id', session_file.stem),
                        'created_at': data.get('metadata', {}).get('created_at', 'Unknown'),
                        'updated_at': data.get('metadata', {}).get('updated_at', 'Unknown'),
                        'message_count': data.get('metadata', {}).get('message_count', 0),
                    })
            except Exception:
                pass
        
        if not sessions:
            self.console.print("[dim]No sessions found[/]")
            return
        
        # Sort by updated_at
        sessions.sort(key=lambda s: s['updated_at'], reverse=True)
        
        table = Table(box=ROUNDED, border_style=BLUE)
        table.add_column("Session ID", style="cyan")
        table.add_column("Created", style="dim")
        table.add_column("Updated", style="dim")
        table.add_column("Messages", style="white", justify="right")
        
        for session in sessions:
            table.add_row(
                session['id'],
                session['created_at'][:19],
                session['updated_at'][:19],
                str(session['message_count'])
            )
        
        self.console.print(table)
        self.console.print()
    
    def delete_session(self, session_id: str):
        """Delete a session."""
        session_path = self.sessions_dir / f"{session_id}.json"
        if session_path.exists():
            session_path.unlink()
            self.console.print(f"[green]✓[/] Session deleted: [cyan]{session_id}[/]")
        else:
            self.console.print(f"[red]Session not found:[/] {session_id}")
    
    def get_recent_history(self, n: int = 10) -> List[str]:
        """Get the most recent history items."""
        return self.history[-n:]
    
    def clear_history(self):
        """Clear the history."""
        self.history = []
        self.metadata['message_count'] = 0
        self.console.print("[green]✓[/] History cleared")
    
    def export_history(self, output_path: Optional[Path] = None) -> Path:
        """Export history to a file."""
        output_path = output_path or Path(f"automyx_history_{self.session_id}.txt")
        
        with open(output_path, 'w') as f:
            f.write(f"Automyx Session History\n")
            f.write(f"Session ID: {self.session_id}\n")
            f.write(f"Created: {self.metadata['created_at']}\n")
            f.write(f"Messages: {len(self.history)}\n")
            f.write("\n" + "="*50 + "\n\n")
            
            for i, msg in enumerate(self.history, 1):
                f.write(f"[{i}] {msg}\n\n")
        
        self.console.print(f"[green]✓[/] History exported to: [cyan]{output_path}[/]")
        return output_path


def main():
    """Test the session manager."""
    sm = SessionManager()
    
    print(f"Session ID: {sm.session_id}")
    print(f"History: {len(sm.history)} messages")
    
    # Add some test messages
    sm.add_to_history("Hello, Automyx!")
    sm.add_to_history("What can you do?")
    sm.add_to_history("Edit my video")
    
    # Save session
    sm.save()
    
    # List sessions
    sm.list_sessions()


if __name__ == '__main__':
    main()
