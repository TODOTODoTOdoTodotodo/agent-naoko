import os
import subprocess
import shlex
from pathlib import Path
from rich.console import Console
from ..io.doc_parser import DocParser

console = Console()

class GeminiClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        
        # Verify gemini CLI availability
        if not self.dry_run:
            try:
                subprocess.run(["gemini", "--version"], capture_output=True, check=True)
                os.makedirs(self.artifacts_dir, exist_ok=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print("[red][Gemini] 'gemini' CLI command not found. Agent disabled.[/red]")
                self.dry_run = True # Force dry-run if CLI missing

    def _call_gemini_cli(self, prompt: str) -> str:
        """
        Executes the external 'gemini' CLI command with the given prompt.
        """
        if self.dry_run: return ""

        # Using --output-format text for cleaner output capture
        # Adding --no-stream or similar might be needed if it streams, 
        # but --output-format text usually implies final output.
        # Based on help: `gemini [query..]`
        
        # We use shlex.quote to safely escape the prompt for shell execution
        # But subprocess.run with list args handles args safely without shell=True
        
        command = ["gemini", prompt, "--output-format", "text"]
        
        # Optional: Add model flag if needed
        # command.extend(["-m", "gemini-3"])

        try:
            console.print(f"[dim][Gemini CLI] Executing command...[/dim]")
            
            # Run command
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                timeout=120 # 2 minutes timeout for long generation
            )
            
            if result.returncode != 0:
                console.print(f"[red][Gemini CLI] Error: {result.stderr.strip()}[/red]")
                return ""
            
            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            console.print(f"[red][Gemini CLI] Timeout expired.[/red]")
            return ""
        except Exception as e:
            console.print(f"[red][Gemini CLI] Execution failed: {e}[/red]")
            return ""

    def plan(self, doc_path: str) -> str:
        console.print(f"[blue]Gemini Agent:[/blue] Analyzing document at '{doc_path}'...")
        
        parsed_text = DocParser.parse(doc_path)
        if not parsed_text: return ""
        
        output_path = self.artifacts_dir / "requirements_request.md"
        if self.dry_run: return str(output_path)
        
        console.print(f"[blue]Gemini Agent:[/blue] Sending {len(parsed_text)} chars context via CLI...")
        
        system_instruction = (
            "You are a Senior Software Architect. Analyze the provided planning document text "
            "and generate a detailed development request in Markdown format."
        )
        
        full_prompt = (
            f"{system_instruction}\n\n"
            f"Analyze this document content:\n\n{parsed_text}"
        )
        
        result = self._call_gemini_cli(full_prompt)
        
        if result:
            with open(output_path, "w", encoding="utf-8") as f: f.write(result)
            console.print(f"[blue]Gemini Agent:[/blue] Real requirements generated via CLI.")
            return str(output_path)
        return ""

    def review(self, patch_path: str, req_path: str, round_num: int) -> str:
        console.print(f"[blue]Gemini Agent:[/blue] Reviewing patch (Round {round_num})...")
        
        output_path = self.artifacts_dir / "review.md"
        if self.dry_run: return str(output_path)
        
        with open(req_path, 'r') as f: req_content = f.read()
        with open(patch_path, 'r') as f: patch_content = f.read()
        
        prompt = (
            f"Review this git patch against requirements.\n\n"
            f"Requirements:\n{req_content}\n\n"
            f"Patch:\n{patch_content}\n\n"
            f"Identify critical bugs or missing features with 'Issue:' prefix. If fine, say 'No critical issues found'."
        )
        
        result = self._call_gemini_cli(prompt)
        
        if result:
            with open(output_path, "w", encoding="utf-8") as f: f.write(result)
            
        return str(output_path)
