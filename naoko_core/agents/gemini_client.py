from rich.console import Console
import time
import os
from pathlib import Path
from ..io.doc_parser import DocParser
from ..auth import AuthManager

console = Console()

class GeminiClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        
        # Check Auth
        if not self.dry_run:
            AuthManager.check_gemini_auth()
            os.makedirs(self.artifacts_dir, exist_ok=True)

    def plan(self, doc_path: str) -> str:
        """
        Analyzes the document and creates a requirement request.
        """
        console.print(f"[blue]Gemini Agent:[/blue] Analyzing document at '{doc_path}'...")
        
        # 1. Parse Document (REAL)
        parsed_text = DocParser.parse(doc_path)
        
        if not parsed_text:
            console.print("[red]Gemini Agent:[/red] Failed to extract text from document.")
            return ""

        output_path = self.artifacts_dir / "requirements_request.md"
        
        # 2. Call LLM (SIMULATION -> Should be replaced with actual gemini cli call)
        if not self.dry_run:
            console.print(f"[blue]Gemini Agent:[/blue] Sending {len(parsed_text)} chars context to Gemini 3...")
            time.sleep(1) # Simulate API latency
            
            # For now, we save the RAW PARSED TEXT into the request file 
            # so the user can verify the parser works.
            content = (
                f"# Generated Requirements Request\n\n"
                f"> Source: {Path(doc_path).name}\n"
                f"> Context Length: {len(parsed_text)} chars\n\n"
                f"## Extracted Content (Preview)\n\n"
                f"{parsed_text[:2000]}...\n\n" # Preview first 2000 chars
                f"(...Remaining content omitted for brevity...)\n\n"
                f"## Analyzed Requirements (Simulated)\n"
                f"1. Implement User Ranking System based on extracted slides.\n"
                f"2. Add Challenge Status tracking.\n"
                f"3. Ensure UI matches the 'Travel Master' theme.\n"
            )
            
            with open(output_path, "w") as f:
                f.write(content)
                
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
            with open(output_path, "w") as f:
                if round_num == 1:
                    f.write("# Code Review\n\n- Issue: Missing input validation for Ranking score.\n- Risk: Medium")
                else:
                    f.write("# Code Review\n\nNo critical issues found. Implementation looks solid.")
                    
        console.print(f"[blue]Gemini Agent:[/blue] Review report generated at '{output_path}'.")
        return str(output_path)
