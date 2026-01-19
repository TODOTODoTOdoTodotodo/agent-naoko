import json
import os
from pathlib import Path
from rich.console import Console

console = Console()

class AuthManager:
    @staticmethod
    def get_codex_token() -> str:
        """
        Retrieves the Codex API token from ~/.codex/auth.json
        """
        auth_path = Path.home() / ".codex" / "auth.json"
        
        if not auth_path.exists():
            console.print(f"[yellow][Auth] Codex auth file not found at {auth_path}[/yellow]")
            return ""
            
        try:
            with open(auth_path, 'r') as f:
                data = json.load(f)
                token = data.get("api_key") or data.get("token") or data.get("access_token")
                
                if token:
                    # Mask the token for security
                    masked = token[:4] + "*" * 4 if len(token) > 8 else "***"
                    console.print(f"[dim][Auth] Loaded Codex token (Starts with: {masked})[/dim]")
                    return token
                else:
                    console.print(f"[red][Auth] Token not found in {auth_path}[/red]")
                    return ""
        except Exception as e:
            console.print(f"[red][Auth] Failed to read Codex auth file: {e}[/red]")
            return ""

    @staticmethod
    def check_gemini_auth():
        """
        Checks if Gemini CLI is authenticated.
        """
        console.print(f"[dim][Auth] Verifying Gemini authentication context...[/dim]")
        # Actual check logic would go here