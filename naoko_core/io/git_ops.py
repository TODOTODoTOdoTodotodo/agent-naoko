import os
import subprocess
from rich.console import Console

console = Console()

class GitOps:
    @staticmethod
    def validate_patch(patch_path: str) -> bool:
        """
        Validates the patch using `git apply --check`.
        """
        if not os.path.exists(patch_path):
            console.print(f"[red][GitOps] Patch file not found: {patch_path}[/red]")
            return False
        
        # 1. Basic Format Check
        with open(patch_path, 'r') as f:
            content = f.read()
            if not content.strip():
                console.print(f"[red][GitOps] Patch file is empty.[/red]")
                return False
            if "--- " not in content or "+++ " not in content or "@@" not in content:
                 console.print(f"[yellow][GitOps] Warning: Patch format looks suspicious (missing headers or hunks).[/yellow]")

        # 2. Git Check (The real test)
        try:
            # git apply --check exits with 0 if patch applies cleanly, non-zero otherwise
            result = subprocess.run(
                ["git", "apply", "--check", patch_path], 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                console.print(f"[red][GitOps] Invalid Patch: {result.stderr.strip()}[/red]")
                return False
        except FileNotFoundError:
             # git not installed or not in path
             console.print(f"[red][GitOps] 'git' command not found.[/red]")
             return False

        return True

    @staticmethod
    def apply_patch(patch_path: str, dry_run: bool = False) -> bool:
        """
        Applies a git patch file after validation.
        """
        # Always validate first
        if not GitOps.validate_patch(patch_path):
            return False

        if dry_run:
            console.print(f"[dim][GitOps] Dry-run: Would apply patch '{patch_path}'[/dim]")
            return True

        try:
            console.print(f"[dim][GitOps] Applying patch '{patch_path}'...[/dim]")
            subprocess.run(["git", "apply", patch_path], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red][GitOps] Failed to apply patch: {e.stderr if e.stderr else 'Unknown git error'}[/red]")
            return False
        except Exception as e:
            console.print(f"[red][GitOps] Unexpected error: {e}[/red]")
            return False

    @staticmethod
    def commit(message: str, dry_run: bool = False):
        if dry_run:
            console.print(f"[dim][GitOps] Dry-run: Would commit with message '{message}'[/dim]")
            return
        
        console.print(f"[dim][GitOps] Committing changes...[/dim]")
        try:
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
            console.print(f"[green][GitOps] Commit successful.[/green]")
        except subprocess.CalledProcessError as e:
             console.print(f"[red][GitOps] Commit failed: {e}[/red]")
