"""
AUTONOMY PERMISSION ESCALATION
================================
Auto-escalation of permissions for denied files/folders.

When AUTONOMY encounters a PermissionError or Access Denied:
1. First tries: normal access
2. If denied: try takeown + icacls (Windows) or chmod (Unix)
3. If still denied: try as administrator
4. If still denied: try PowerShell with elevation
5. Reports final status
"""
from __future__ import annotations

import os
import sys
import subprocess
import platform
import time
from pathlib import Path
from typing import Optional, Tuple

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class PermissionEscalator:
    """
    Auto-escalate permissions for denied files/folders.
    
    Methods tried in order:
    1. Normal access
    2. Take ownership (Windows: takeown, Unix: chown)
    3. Grant full permissions (Windows: icacls, Unix: chmod 777)
    4. Run as administrator (Windows: UAC elevation, Unix: sudo)
    5. PowerShell with elevation
    """
    
    def __init__(self, console: Optional[Console] = None, verbose: bool = True):
        self.console = console
        self.verbose = verbose
        self.is_windows = platform.system() == 'Windows'
        self.escalation_log: list = []
        
    def log(self, message: str, level: str = "info"):
        """Log a message."""
        self.escalation_log.append({"level": level, "message": message, "time": time.time()})
        if self.verbose and self.console:
            color = {
                "info": "dim",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "action": "cyan"
            }.get(level, "white")
            self.console.print(f"  [{color}]PermissionEscalator: {message}[/{color}]")
    
    def try_access(self, path: str, mode: str = "read") -> Tuple[bool, str]:
        """
        Try to access a path with auto-escalation.
        
        Args:
            path: File or directory path
            mode: "read", "write", or "execute"
        
        Returns:
            (success, error_message)
        """
        path = Path(path)
        if not path.exists():
            return False, f"Path does not exist: {path}"
        
        # First try: normal access
        try:
            if mode == "read":
                if path.is_file():
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.read(1)  # Just read 1 char
                else:
                    os.listdir(path)
            elif mode == "write":
                if path.is_file():
                    with open(path, 'a', encoding='utf-8') as f:
                        f.write('')
                else:
                    test_file = path / ".autonomy_write_test"
                    test_file.touch()
                    test_file.unlink()
            elif mode == "execute":
                if path.is_file():
                    # Check if executable
                    os.access(path, os.X_OK)
            
            self.log(f"Normal access succeeded for: {path}", "success")
            return True, ""
        except PermissionError as e:
            self.log(f"Normal access denied for {path}: {e}", "warning")
        except Exception as e:
            self.log(f"Access error for {path}: {e}", "warning")
        
        # Second try: take ownership
        if self.escalate_ownership(path):
            return self.retry_access(path, mode)
        
        # Third try: grant full permissions
        if self.grant_full_permissions(path):
            return self.retry_access(path, mode)
        
        # Fourth try: run as administrator
        if self.escalate_to_admin(path, mode):
            return self.retry_access(path, mode)
        
        # Fifth try: PowerShell with elevation
        if self.powershell_elevation(path, mode):
            return self.retry_access(path, mode)
        
        # All methods failed
        self.log(f"All escalation methods failed for: {path}", "error")
        return False, "Permission denied - all escalation methods failed"
    
    def retry_access(self, path: Path, mode: str) -> Tuple[bool, str]:
        """Retry access after escalation."""
        try:
            if mode == "read":
                if path.is_file():
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.read(1)
                else:
                    os.listdir(path)
            elif mode == "write":
                if path.is_file():
                    with open(path, 'a', encoding='utf-8') as f:
                        f.write('')
                else:
                    test_file = path / ".autonomy_write_test"
                    test_file.touch()
                    test_file.unlink()
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def escalate_ownership(self, path: Path) -> bool:
        """Take ownership of the path."""
        self.log(f"Trying to take ownership of {path}...", "action")
        try:
            if self.is_windows:
                # Windows: takeown
                result = subprocess.run(
                    ["takeown", "/F", "/R", "/D", "Y", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.log(f"Ownership taken: {path}", "success")
                    return True
                else:
                    self.log(f"takeown failed: {result.stderr[:100]}", "warning")
                    return False
            else:
                # Unix: chown to current user
                import getpass
                user = getpass.getuser()
                result = subprocess.run(
                    ["sudo", "chown", "-R", f"{user}:{user}", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.log(f"Ownership changed to {user}: {path}", "success")
                    return True
                return False
        except subprocess.TimeoutExpired:
            self.log(f"Ownership change timed out for {path}", "warning")
            return False
        except Exception as e:
            self.log(f"Ownership change error: {e}", "warning")
            return False
    
    def grant_full_permissions(self, path: Path) -> bool:
        """Grant full permissions to the path."""
        self.log(f"Granting full permissions to {path}...", "action")
        try:
            if self.is_windows:
                # Windows: icacls grant full control to everyone
                result = subprocess.run(
                    ["icacls", str(path), "/grant", "Everyone:(OI)(CI)F", "/T"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.log(f"Full permissions granted: {path}", "success")
                    return True
                else:
                    self.log(f"icacls failed: {result.stderr[:100]}", "warning")
                    return False
            else:
                # Unix: chmod 777
                result = subprocess.run(
                    ["sudo", "chmod", "-R", "777", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.log(f"chmod 777 applied: {path}", "success")
                    return True
                return False
        except subprocess.TimeoutExpired:
            self.log(f"Permission grant timed out for {path}", "warning")
            return False
        except Exception as e:
            self.log(f"Permission grant error: {e}", "warning")
            return False
    
    def escalate_to_admin(self, path: Path, mode: str) -> bool:
        """Try to access as administrator."""
        self.log(f"Trying admin-level access for {path}...", "action")
        try:
            if self.is_windows:
                # Windows: run as administrator via PowerShell
                ps_cmd = f"""
                $Path = '{path}'
                $Mode = '{mode}'
                $psi = New-Object System.Diagnostics.ProcessStartInfo
                $psi.FileName = 'powershell.exe'
                $psi.Arguments = '-NoProfile -Command "Test-Path $Path; if ($Mode -eq ''write'') {{ New-Item -ItemType File -Path $Path -Force }} else {{ Get-ChildItem $Path | Out-Null }}"'
                $psi.Verb = 'runas'
                $psi.UseShellExecute = $true
                $p = [System.Diagnostics.Process]::Start($psi)
                $p.WaitForExit()
                if ($p.ExitCode -eq 0) {{
                    Write-Output 'SUCCESS'
                }} else {{
                    Write-Output 'FAILED'
                }}
                """
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                success = "SUCCESS" in result.stdout
                if success:
                    self.log(f"Admin access succeeded: {path}", "success")
                else:
                    self.log(f"Admin access failed: {path}", "warning")
                return success
            else:
                # Unix: sudo
                if mode == "read":
                    cmd = f"sudo ls {path}"
                else:
                    cmd = f"sudo touch {path}/.test && sudo rm {path}/.test"
                
                result = subprocess.run(
                    cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                success = result.returncode == 0
                if success:
                    self.log(f"sudo access succeeded: {path}", "success")
                return success
        except subprocess.TimeoutExpired:
            self.log(f"Admin escalation timed out for {path}", "warning")
            return False
        except Exception as e:
            self.log(f"Admin escalation error: {e}", "warning")
            return False
    
    def powershell_elevation(self, path: Path, mode: str) -> bool:
        """Use PowerShell with elevation as last resort."""
        self.log(f"Final escalation: PowerShell elevation for {path}...", "action")
        try:
            if not self.is_windows:
                return False
            
            # Use PowerShell Start-Process with -Verb RunAs for UAC
            ps_cmd = f"""
            $path = '{path}'
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = 'cmd.exe'
            $psi.Arguments = '/c takeown /F /R /D Y "{path}" && icacls "{path}" /grant Everyone:(OI)(CI)F /T'
            $psi.Verb = 'runas'
            $psi.UseShellExecute = $true
            try {{
                $p = [System.Diagnostics.Process]::Start($psi)
                $p.WaitForExit()
                Write-Output 'SUCCESS'
            }} catch {{
                Write-Output 'FAILED'
            }}
            """
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=60
            )
            success = "SUCCESS" in result.stdout
            if success:
                self.log(f"PowerShell elevation succeeded: {path}", "success")
            else:
                self.log(f"PowerShell elevation failed: {path}", "warning")
            return success
        except subprocess.TimeoutExpired:
            self.log(f"PowerShell elevation timed out for {path}", "warning")
            return False
        except Exception as e:
            self.log(f"PowerShell elevation error: {e}", "warning")
            return False
    
    def create_directory_with_permissions(self, path: str) -> Tuple[bool, str]:
        """Create directory with auto-escalation."""
        path = Path(path)
        
        # First try: normal creation
        try:
            path.mkdir(parents=True, exist_ok=True)
            self.log(f"Directory created normally: {path}", "success")
            return True, ""
        except PermissionError:
            self.log(f"Normal creation denied for {path}, escalating...", "warning")
        except Exception as e:
            self.log(f"Creation error: {e}", "warning")
        
        # Try with PowerShell
        if self.is_windows:
            try:
                ps_cmd = f"New-Item -ItemType Directory -Path '{path}' -Force"
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.log(f"Directory created via PowerShell: {path}", "success")
                    return True, ""
            except Exception as e:
                self.log(f"PowerShell creation error: {e}", "warning")
        
        # Try with takeown + mkdir
        if self.is_windows:
            try:
                # First takeown the parent
                parent = path.parent
                self.escalate_ownership(parent)
                self.grant_full_permissions(parent)
                # Then create
                path.mkdir(parents=True, exist_ok=True)
                self.log(f"Directory created after escalation: {path}", "success")
                return True, ""
            except Exception as e:
                self.log(f"Final creation error: {e}", "error")
                return False, str(e)
        
        return False, "All creation methods failed"
    
    def read_file_with_permissions(self, path: str) -> Tuple[bool, str]:
        """Read file with auto-escalation."""
        return self.try_access(path, mode="read")
    
    def write_file_with_permissions(self, path: str, content: str) -> Tuple[bool, str]:
        """Write file with auto-escalation."""
        path = Path(path)
        
        # First try: normal write
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log(f"File written normally: {path}", "success")
            return True, ""
        except PermissionError:
            self.log(f"Normal write denied for {path}, escalating...", "warning")
        except Exception as e:
            self.log(f"Write error: {e}", "warning")
        
        # Try with escalation
        success, _ = self.try_access(path, mode="write")
        if success:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"File written after escalation: {path}", "success")
                return True, ""
            except Exception as e:
                return False, str(e)
        
        return False, "Write denied and escalation failed"
    
    def get_escalation_log(self) -> list:
        """Get the log of all escalation attempts."""
        return self.escalation_log


def main():
    """Test the permission escalator."""
    console = Console() if Console else None
    escalator = PermissionEscalator(console=console, verbose=True)
    
    # Test directory creation
    test_dir = "C:\\Users\\COMPUMAX\\AppData\\Local\\Temp\\autonomy_test"
    print(f"\nTest 1: Create directory {test_dir}")
    success, msg = escalator.create_directory_with_permissions(test_dir)
    print(f"  Result: {'SUCCESS' if success else 'FAILED'} - {msg}")
    
    # Test file write
    test_file = f"{test_dir}\\test.txt"
    print(f"\nTest 2: Write file {test_file}")
    success, msg = escalator.write_file_with_permissions(test_file, "test content")
    print(f"  Result: {'SUCCESS' if success else 'FAILED'} - {msg}")
    
    # Test file read
    if success:
        print(f"\nTest 3: Read file {test_file}")
        success, msg = escalator.read_file_with_permissions(test_file)
        print(f"  Result: {'SUCCESS' if success else 'FAILED'} - {msg}")
    
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
    if os.path.exists(test_dir):
        os.rmdir(test_dir)


if __name__ == '__main__':
    main()
