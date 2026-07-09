"""
AUTOMYX CONTEXT AWARENESS
==========================
Automatically detects project structure, tools, and frameworks.
Provides intelligent context for better responses.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

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


class ProjectContext:
    """
    Automatically detects and manages project context.
    
    Features:
    - Project type detection (Python, Node.js, Rust, etc.)
    - Framework detection (Django, React, FastAPI, etc.)
    - Tool availability checking
    - Git integration
    - Dependency analysis
    """
    
    def __init__(self):
        self.console = shared_console or Console()
        self.project_type: Optional[str] = None
        self.frameworks: List[str] = []
        self.tools: List[str] = []
        self.has_git: bool = False
        self.git_branch: Optional[str] = None
        self.git_status: Optional[str] = None
        self.key_files: List[str] = []
        self.dependencies: Dict[str, str] = {}
        
        self._detect_context()
    
    def _detect_context(self):
        """Detect all context information."""
        self._detect_project_type()
        self._detect_frameworks()
        self._detect_tools()
        self._detect_git()
        self._find_key_files()
        self._load_dependencies()
    
    def _detect_project_type(self):
        """Detect the type of project."""
        cwd = Path.cwd()
        
        # Check for common project files
        if (cwd / 'package.json').exists():
            self.project_type = 'Node.js'
        elif (cwd / 'requirements.txt').exists() or (cwd / 'pyproject.toml').exists():
            self.project_type = 'Python'
        elif (cwd / 'Cargo.toml').exists():
            self.project_type = 'Rust'
        elif (cwd / 'go.mod').exists():
            self.project_type = 'Go'
        elif (cwd / 'pom.xml').exists() or (cwd / 'build.gradle').exists():
            self.project_type = 'Java'
        elif (cwd / 'Gemfile').exists():
            self.project_type = 'Ruby'
        else:
            self.project_type = 'Generic'
    
    def _detect_frameworks(self):
        """Detect frameworks based on dependencies and files."""
        cwd = Path.cwd()
        
        # Python frameworks
        if (cwd / 'requirements.txt').exists():
            try:
                with open(cwd / 'requirements.txt', 'r') as f:
                    content = f.read().lower()
                    if 'django' in content:
                        self.frameworks.append('Django')
                    if 'flask' in content:
                        self.frameworks.append('Flask')
                    if 'fastapi' in content:
                        self.frameworks.append('FastAPI')
                    if 'react' in content:
                        self.frameworks.append('React')
                    if 'torch' in content or 'pytorch' in content:
                        self.frameworks.append('PyTorch')
                    if 'tensorflow' in content:
                        self.frameworks.append('TensorFlow')
            except Exception:
                pass
        
        # Node.js frameworks
        if (cwd / 'package.json').exists():
            try:
                with open(cwd / 'package.json', 'r') as f:
                    data = json.load(f)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    
                    if 'react' in deps or 'react-dom' in deps:
                        self.frameworks.append('React')
                    if 'next' in deps:
                        self.frameworks.append('Next.js')
                    if 'vue' in deps:
                        self.frameworks.append('Vue.js')
                    if 'express' in deps:
                        self.frameworks.append('Express')
                    if 'typescript' in deps:
                        self.frameworks.append('TypeScript')
            except Exception:
                pass
    
    def _detect_tools(self):
        """Detect available tools in the system."""
        import shutil
        
        tools_to_check = [
            'git', 'python', 'python3', 'node', 'npm', 'yarn', 'pnpm',
            'docker', 'docker-compose', 'kubectl', 'helm',
            'rustc', 'cargo', 'go', 'java', 'javac',
            'gcc', 'g++', 'make', 'cmake',
            'ffmpeg', 'ffprobe', 'convert', 'magick',
            'code', 'vim', 'nano',
            'curl', 'wget', 'ssh',
            'ollama', 'whisper',
        ]
        
        for tool in tools_to_check:
            if shutil.which(tool):
                self.tools.append(tool)
    
    def _detect_git(self):
        """Detect git repository information."""
        try:
            import subprocess
            
            # Check if git repo
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )
            self.has_git = result.returncode == 0
            
            if self.has_git:
                # Get current branch
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd()
                )
                self.git_branch = result.stdout.strip() if result.returncode == 0 else None
                
                # Get git status
                result = subprocess.run(
                    ['git', 'status', '--porcelain'],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd()
                )
                status_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                if len(status_lines) == 0:
                    self.git_status = "clean"
                else:
                    modified = sum(1 for l in status_lines if l.startswith(' M') or l.startswith('M '))
                    untracked = sum(1 for l in status_lines if l.startswith('??'))
                    added = sum(1 for l in status_lines if l.startswith('A ') or l.startswith(' A'))
                    
                    parts = []
                    if modified:
                        parts.append(f"{modified} modified")
                    if untracked:
                        parts.append(f"{untracked} untracked")
                    if added:
                        parts.append(f"{added} added")
                    
                    self.git_status = ", ".join(parts) if parts else "clean"
                
        except Exception:
            self.has_git = False
    
    def _find_key_files(self):
        """Find key files in the project."""
        cwd = Path.cwd()
        
        key_patterns = [
            'README.md', 'README.txt', 'README',
            'LICENSE', 'LICENSE.md',
            'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod',
            'requirements.txt', 'Pipfile', 'poetry.lock',
            'docker-compose.yml', 'Dockerfile',
            '.env', '.env.example',
            'Makefile', 'CMakeLists.txt',
            '.gitignore', '.dockerignore',
        ]
        
        for pattern in key_patterns:
            if (cwd / pattern).exists():
                self.key_files.append(pattern)
    
    def _load_dependencies(self):
        """Load project dependencies."""
        cwd = Path.cwd()
        
        # Python dependencies
        if (cwd / 'requirements.txt').exists():
            try:
                with open(cwd / 'requirements.txt', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '==' in line:
                                pkg, ver = line.split('==', 1)
                                self.dependencies[pkg.strip()] = ver.strip()
                            elif '>=' in line:
                                pkg, ver = line.split('>=', 1)
                                self.dependencies[pkg.strip()] = f">={ver.strip()}"
                            else:
                                self.dependencies[line] = 'latest'
            except Exception:
                pass
        
        # Node.js dependencies
        if (cwd / 'package.json').exists():
            try:
                with open(cwd / 'package.json', 'r') as f:
                    data = json.load(f)
                    for pkg, ver in data.get('dependencies', {}).items():
                        self.dependencies[pkg] = ver
                    for pkg, ver in data.get('devDependencies', {}).items():
                        self.dependencies[f"{pkg} (dev)"] = ver
            except Exception:
                pass
    
    def get_summary(self) -> str:
        """Get a summary of the context."""
        parts = []
        
        if self.project_type:
            parts.append(self.project_type)
        
        if self.has_git and self.git_branch:
            parts.append(f"git:{self.git_branch}")
        
        if self.frameworks:
            parts.append(f"{len(self.frameworks)} frameworks")
        
        if self.tools:
            parts.append(f"{len(self.tools)} tools")
        
        return " · ".join(parts) if parts else "Empty project"
    
    def get_context_for_prompt(self) -> str:
        """Get context information formatted for LLM prompt."""
        lines = []
        
        lines.append(f"Project Type: {self.project_type or 'Unknown'}")
        
        if self.has_git:
            lines.append(f"Git Branch: {self.git_branch}")
            lines.append(f"Git Status: {self.git_status}")
        
        if self.frameworks:
            lines.append(f"Frameworks: {', '.join(self.frameworks)}")
        
        if self.tools:
            lines.append(f"Available Tools: {', '.join(self.tools[:10])}")
            if len(self.tools) > 10:
                lines.append(f"  ... and {len(self.tools) - 10} more")
        
        if self.key_files:
            lines.append(f"Key Files: {', '.join(self.key_files[:10])}")
        
        if self.dependencies:
            lines.append(f"Dependencies: {len(self.dependencies)} packages")
        
        return "\n".join(lines)
    
    def display(self):
        """Display context information."""
        self.console.print("\n[bold cyan]Project Context:[/]\n")
        
        self.console.print(f"[dim]Working Directory:[/] {Path.cwd()}")
        self.console.print(f"[dim]Project Type:[/] {self.project_type or 'Unknown'}")
        
        if self.has_git:
            self.console.print(f"[dim]Git Branch:[/] {self.git_branch}")
            self.console.print(f"[dim]Git Status:[/] {self.git_status}")
        
        if self.frameworks:
            self.console.print(f"\n[dim]Frameworks:[/]")
            for framework in self.frameworks:
                self.console.print(f"  [cyan]•[/] {framework}")
        
        if self.tools:
            self.console.print(f"\n[dim]Available Tools:[/]")
            for tool in self.tools[:10]:
                self.console.print(f"  [cyan]•[/] {tool}")
            if len(self.tools) > 10:
                self.console.print(f"  [dim]... and {len(self.tools) - 10} more[/]")
        
        if self.key_files:
            self.console.print(f"\n[dim]Key Files:[/]")
            for f in self.key_files[:10]:
                self.console.print(f"  [cyan]•[/] {f}")
        
        if self.dependencies:
            self.console.print(f"\n[dim]Dependencies:[/] {len(self.dependencies)} packages")
        
        self.console.print()


def main():
    """Test the context detection."""
    context = ProjectContext()
    context.display()
    
    print("\nContext for prompt:")
    print(context.get_context_for_prompt())


if __name__ == '__main__':
    main()
