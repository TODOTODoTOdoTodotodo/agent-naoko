import os
import subprocess
import shlex
import re
from pathlib import Path
from rich.console import Console
from ..io.doc_parser import DocParser
from ..io.code_navigator import CodeNavigator

console = Console()

class GeminiClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        self.primary_model = "gemini-3"
        self.fallback_models = ["gemini-2.5-pro", "gemini-2.5-flash"]
        
        if not self.dry_run:
            try:
                subprocess.run(["gemini", "--version"], capture_output=True, check=True)
                os.makedirs(self.artifacts_dir, exist_ok=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print("[red][Gemini] 'gemini' CLI command not found. Agent disabled.[/red]")
                self.dry_run = True

    def _call_gemini_cli_once(self, prompt: str, timeout_sec: int, model: str) -> tuple[str, str, int]:
        command = ["gemini", "--output-format", "text", "--model", model]
        try:
            console.print(f"[dim][Gemini CLI] Executing command via STDIN (Model: {model})...[/dim]")
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout_sec,
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "timeout", 124
        except Exception as e:
            return "", str(e), 1

    def _call_gemini_cli(self, prompt: str, timeout_sec: int = 1800) -> str:
        """
        Executes 'gemini' CLI using STDIN to avoid argument length limits.
        """
        if self.dry_run: return ""

        sanitized_prompt = re.sub(r"(?m)^@", r"\\@", prompt)
        console.print(f"[dim][Gemini CLI] Executing command via STDIN (Length: {len(sanitized_prompt)} chars)...[/dim]")
        stdout, stderr, code = self._call_gemini_cli_once(sanitized_prompt, timeout_sec, self.primary_model)
        if code == 0:
            return stdout
        if "RESOURCE_EXHAUSTED" in stderr or "quota" in stderr.lower() or "rate limit" in stderr.lower():
            for fallback in self.fallback_models:
                console.print(f"[yellow][Gemini CLI] Quota/limit reached. Retrying with {fallback}...[/yellow]")
                stdout, stderr, code = self._call_gemini_cli_once(sanitized_prompt, timeout_sec, fallback)
                if code == 0:
                    return stdout
                if "ModelNotFound" not in stderr:
                    break
        if stderr == "timeout":
            console.print(f"[red][Gemini CLI] Timeout expired.[/red]")
            return ""
        console.print(f"[red][Gemini CLI] Error: {stderr}[/red]")
        return ""

    def analyze_style(self, entry_point: str) -> str:
        """
        Analyzes the coding style of the existing project starting from the entry point via CLI.
        """
        console.print(f"[blue]Gemini Agent:[/blue] Analyzing code style from '{entry_point}'...")
        
        if self.dry_run: return ""

        # 1. Find related files
        navigator = CodeNavigator(self.root_dir)
        related_files = navigator.find_related_files(entry_point)
        
        if not related_files:
            console.print("[yellow]No related files found for analysis.[/yellow]")
            return ""

        # 2. Prepare Context
        context = ""
        for file_path in related_files[:5]: 
            try:
                p = Path(file_path)
                content = p.read_text(encoding="utf-8")
                if len(content) > 5000: content = content[:5000] + "\n...[Truncated]"
                context += f"--- File: {p.name} ---\n{content}\n\n"
            except Exception as e:
                console.print(f"[yellow]Skipped file {file_path}: {e}[/yellow]")

        # 3. Call Gemini via CLI
        sys_inst = "You are a Tech Lead. Analyze the code to extract the project's Coding Style Guidelines."
        prompt = (
            f"{sys_inst}\n\n"
            f"Analyze the following source code files and document the coding style conventions.\n"
            f"Context:\n{context}\n\n"
            f"Output a Markdown file (`CODING_STYLE.md`) covering:\n"
            f"1. Language & Framework versions\n"
            f"2. Naming Conventions\n"
            f"3. Library Usage (Lombok, etc.)\n"
            f"4. Architecture\n"
        )
        
        result = self._call_gemini_cli(prompt, timeout_sec=3600)
        
        if result:
            style_path = Path(entry_point).parent / "CODING_STYLE.md"
            with open(style_path, "w", encoding="utf-8") as f:
                f.write(result)
            console.print(f"[blue]Gemini Agent:[/blue] Style guide created at '{style_path}'.")
            return str(style_path)
        
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
        console.print(f"[blue]Gemini Agent:[/blue] Reviewing code (Round {round_num})...")
        
        output_path = self.artifacts_dir / "review.md"
        if self.dry_run: return str(output_path)
        
        with open(req_path, 'r') as f: req_content = f.read()
        
        # Assume target from context or just review diff logic if simple
        # For better context, reading the actual target file is best
        # Hardcoded for prototype:
        target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"
        current_code = ""
        if target_path.exists():
            current_code = target_path.read_text(encoding="utf-8")
        else:
            current_code = "(File not found)"

        prompt = (
            "Review the code against the requirements and respond in this exact format.\n\n"
            "Format:\n"
            "Summary:\n"
            "- <one paragraph>\n\n"
            "Findings:\n"
            "- [High] <issue> (Location: <file or snippet>)\n"
            "- [Medium] <issue> (Location: <file or snippet>)\n"
            "- [Low] <issue> (Location: <file or snippet>)\n"
            "- If no findings, write: Findings: None\n\n"
            "Additional Considerations:\n"
            "- <extra checks, risks, or test suggestions>\n"
            "- If none, write: Additional Considerations: None\n\n"
            "User Questions (only if user confirmation is required):\n"
            "- Q: <question> | Example: <short suggested answer> | Required: yes/no\n\n"
            "Review Focus:\n"
            "- Verify the controller file contains only the target controller class (no extra top-level classes).\n\n"
            f"Requirements:\n{req_content}\n\n"
            f"Current Code Implementation:\n{current_code}\n"
        )
        
        result = self._call_gemini_cli(prompt)
        
        if result:
            with open(output_path, "w", encoding="utf-8") as f: f.write(result)
            
        return str(output_path)
