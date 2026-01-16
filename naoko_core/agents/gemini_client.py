from rich.console import Console
import time
import os
from pathlib import Path

console = Console()

class GeminiClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        
        # Ensure artifacts directory exists
        if not self.dry_run:
            os.makedirs(self.artifacts_dir, exist_ok=True)

    def plan(self, doc_path: str) -> str:
        """
        Analyzes the document and creates a requirement request.
        """
        console.print(f"[blue]Gemini Agent:[/blue] Analyzing document at '{doc_path}'...")
        
        output_path = self.artifacts_dir / "requirements_request.md"
        
        if not self.dry_run:
            time.sleep(1) # Simulate processing
            with open(output_path, "w") as f:
                f.write(f"# Generated Requirements\n\nAnalyzed from {doc_path}")
                
        console.print(f"[blue]Gemini Agent:[/blue] Requirements generated at '{output_path}'.")
        return str(output_path)

    def review(self, patch_path: str, req_path: str, round_num: int) -> str:
        """
        Reviews the patch against the requirements.
        """
        console.print(f"[blue]Gemini Agent:[/blue] Reviewing patch '{patch_path}' (Round {round_num})...")
        
        output_path = self.artifacts_dir / "review.md"
        
        if not self.dry_run:
            time.sleep(1)
            # SIMULATION LOGIC:
            # Round 1: Find issues
            # Round 2+: No issues
            with open(output_path, "w") as f:
                if round_num == 1:
                    f.write("# Code Review\n\n- Issue: Missing input validation.\n- Risk: Medium")
                else:
                    f.write("# Code Review\n\nNo critical issues found. Looks good.")
                    
        console.print(f"[blue]Gemini Agent:[/blue] Review report generated at '{output_path}'.")
        return str(output_path)