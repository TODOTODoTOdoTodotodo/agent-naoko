import json
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

# OAuth imports
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

console = Console()
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

class AuthManager:
    @staticmethod
    def get_base_dir() -> Path:
        """Returns the global configuration directory (~/.naoko)."""
        base_dir = Path.home() / ".naoko"
        if not base_dir.exists():
            base_dir.mkdir(exist_ok=True)
        return base_dir

    @staticmethod
    def get_codex_token() -> str:
        """Retrieves the Codex API token."""
        auth_path = Path.home() / ".codex" / "auth.json"
        try:
            if auth_path.exists():
                with open(auth_path, 'r') as f:
                    data = json.load(f)
                    token = data.get("api_key") or data.get("OPENAI_API_KEY") or data.get("access_token")
                    if not token and "tokens" in data and isinstance(data["tokens"], dict):
                        token = data["tokens"].get("access_token") or data["tokens"].get("api_key")
                    if token:
                        return token
        except Exception:
            pass
        console.print(Panel.fit(
            "[bold cyan]Codex Authentication[/bold cyan]\n\n"
            "No Codex API token found. Enter it now, or store it at:\n"
            "~/.codex/auth.json with a key like 'OPENAI_API_KEY' or 'api_key'.",
            border_style="cyan"
        ))
        new_key = Prompt.ask("Enter Codex API Key (leave blank to skip)", password=True, default="")
        if new_key:
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            with open(auth_path, "w") as f:
                json.dump({"OPENAI_API_KEY": new_key.strip()}, f)
            console.print("[green][Auth] Codex API key saved to ~/.codex/auth.json.[/green]")
            return new_key.strip()
        return ""

    @staticmethod
    def authenticate_gemini():
        """Authenticates Gemini using OAuth 2.0 (Legacy Wrapper)."""
        # This function is kept for backward compatibility if called directly
        # It redirects to the new interactive flow logic or just checks token existence
        return AuthManager.get_gemini_credentials()

    @staticmethod
    def get_gemini_credentials():
        """
        Returns either an API Key string OR an OAuth Credentials object.
        """
        base_dir = AuthManager.get_base_dir()
        token_path = base_dir / "token.json"
        key_path = base_dir / "gemini_key.txt"
        creds_path = base_dir / "credentials.json"

        # 1. OAuth Token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    console.print("[dim][Auth] Refreshing OAuth token...[/dim]")
                    creds.refresh(Request())
                console.print("[green][Auth] Using existing OAuth login.[/green]")
                return creds
            except Exception:
                console.print("[yellow][Auth] OAuth token expired/invalid.[/yellow]")

        # 2. API Key
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
             console.print("[green][Auth] Using GOOGLE_API_KEY from environment.[/green]")
             return env_key
             
        if key_path.exists():
            key = key_path.read_text().strip()
            if key:
                console.print("[green][Auth] Using saved API Key.[/green]")
                return key

        # 3. Interactive
        console.print(Panel.fit(
            "[bold cyan]Gemini Authentication[/bold cyan]\n\n"
            "Choose your preferred authentication method:\n"
            "[1] API Key (Simple) - Paste a key from Google AI Studio\n"
            "[2] OAuth Login (Advanced) - Use Client ID/Secret to log in via browser",
            border_style="cyan"
        ))

        choice = Prompt.ask("Select method", choices=["1", "2"], default="1")

        if choice == "1":
            console.print("Get your key at: [underline]https://aistudio.google.com/app/apikey[/underline]")
            new_key = Prompt.ask("Enter Gemini API Key", password=True)
            if new_key:
                key_path.write_text(new_key.strip())
                console.print("[green][Auth] API Key saved![/green]")
                return new_key.strip()

        elif choice == "2":
            if not creds_path.exists():
                console.print("\n[yellow]No 'credentials.json' found.[/yellow]")
                client_id = Prompt.ask("Enter Client ID")
                client_secret = Prompt.ask("Enter Client Secret", password=True)
                
                if client_id and client_secret:
                    client_config = {
                        "installed": {
                            "client_id": client_id.strip(),
                            "client_secret": client_secret.strip(),
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                        }
                    }
                    with open(creds_path, "w") as f:
                        json.dump(client_config, f)
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                console.print("\n[bold cyan]Please visit this URL to authorize:[/bold cyan]")
                creds = flow.run_console()
                
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                console.print("[green][Auth] Login successful![/green]")
                return creds
            except Exception as e:
                console.print(f"[red][Auth] OAuth failed: {e}[/red]")
        
        return None

    @staticmethod
    def check_gemini_auth():
        return AuthManager.get_gemini_credentials() is not None
