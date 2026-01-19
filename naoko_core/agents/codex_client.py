import os
import time
import difflib
import subprocess
import re
from pathlib import Path
from rich.console import Console

console = Console()

class CodexClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        
        # Verify CLI tools availability
        if not self.dry_run:
            os.makedirs(self.artifacts_dir, exist_ok=True)
            # Check for codex CLI availability
            try:
                subprocess.run(["codex", "--version"], capture_output=True, check=True)
                self.has_codex_cli = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print("[yellow][Codex] 'codex' CLI not found. Will default to Gemini Fallback.[/yellow]")
                self.has_codex_cli = False

    def _clean_code(self, text: str) -> str:
        """Removes markdown code fences if present."""
        if not text: return ""
        pattern = r"```(?:\w+)?\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _call_gemini_fallback(self, prompt: str) -> str:
        """Fallback to Gemini CLI."""
        console.print("[yellow][Codex] Switching to Gemini CLI (Fallback)...[/yellow]")
        try:
            command = ["gemini", prompt, "--output-format", "text"]
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                timeout=120
            )
            if result.returncode == 0:
                return self._clean_code(result.stdout)
            else:
                console.print(f"[red][Codex-Fallback] Gemini failed: {result.stderr.strip()}[/red]")
        except Exception as e:
            console.print(f"[red][Codex-Fallback] Error: {e}[/red]")
        return ""

    def _call_codex_cli(self, prompt: str) -> str:
        """Executes the external 'codex' CLI command."""
        # Adjust command format based on actual CLI spec
        # Assuming: codex prompt "..." --model ...
        command = ["codex", "prompt", prompt, "--model", "gpt-5.2_codex-medium"]
        
        try:
            console.print(f"[magenta][Codex CLI] Executing command...[/magenta]")
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                timeout=120
            )
            
            if result.returncode != 0:
                console.print(f"[red][Codex CLI] Error: {result.stderr.strip()}[/red]")
                return ""
            
            return self._clean_code(result.stdout)
        except Exception as e:
            console.print(f"[red][Codex CLI] Execution failed: {e}[/red]")
            return ""

    def _generate_code(self, prompt: str) -> str:
        """
        Tries Codex CLI, then falls back to Gemini CLI.
        """
        if self.dry_run: return ""

        if self.has_codex_cli:
            code = self._call_codex_cli(prompt)
            if code: return code
            console.print("[red][Codex] CLI execution failed. Trying fallback.[/red]")
        
        return self._call_gemini_fallback(prompt)

    def implement(self, req_path: str) -> tuple[str, bool]:
        console.print(f"[magenta]Codex Agent:[/magenta] Reading requirements from '{req_path}'...")
        
        output_path = self.artifacts_dir / "patch.diff"
        target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"
        
        if self.dry_run: return str(output_path), True

        if not req_path or not os.path.exists(req_path):
             return str(output_path), False
             
        with open(req_path, 'r') as f: req_content = f.read()
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists():
            target_path.write_text("package com.example;\n\npublic class User {\n    private String username;\n}\n", encoding="utf-8")
        
        old_content = target_path.read_text(encoding="utf-8")
        
        prompt = (
            f"Requirements:\n{req_content}\n\n"
            f"Current Code (User.java):\n{old_content}\n\n"
            f"Task: Implement the requirements. Update the existing code. "
            f"Return the COMPLETE, valid Java file content."
        )

        new_content = self._generate_code(prompt)
        
        if not new_content:
            console.print("[red][Codex] Failed to generate code.[/red]")
            return str(output_path), False

        # Generate Diff for Artifacts (Reference only)
        diff_gen = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="a/src/main/java/com/example/User.java",
            tofile="b/src/main/java/com/example/User.java",
        )
        diff_content = "".join(diff_gen)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(diff_content)

        # OVERWRITE STRATEGY
        console.print(f"[magenta][Codex] Updating file: {target_path}[/magenta]")
        target_path.write_text(new_content, encoding="utf-8")
        
        return str(output_path), True

    def refine(self, review_path: str) -> tuple[str, str]:
        console.print(f"[magenta]Codex Agent:[/magenta] Analyzing review feedback...")
        
        output_path = self.artifacts_dir / "review_judgement.md"
        status = "SUITABLE"
        
        if self.dry_run: return str(output_path), status

        with open(review_path, 'r') as f: review_content = f.read()

        if "Issue" in review_content or "Bug" in review_content or "Missing" in review_content:
            status = "CHANGES_NEEDED"
        
        if status == "CHANGES_NEEDED":
            console.print(f"[magenta]Codex Agent:[/magenta] Applying fixes...")
            patch_path = self.artifacts_dir / "patch.diff"
            target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"
            
            old_content = target_path.read_text(encoding="utf-8")
            
            prompt = (
                f"Review Feedback:\n{review_content}\n\n"
                f"Current Code:\n{old_content}\n\n"
                f"Task: Fix the code based on the review. "
                f"Return the COMPLETE, valid Java file content."
            )
            
            new_content = self._generate_code(prompt)
            
            if new_content and new_content.strip() != old_content.strip():
                diff_gen = difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile="a/src/main/java/com/example/User.java",
                    tofile="b/src/main/java/com/example/User.java",
                )
                with open(patch_path, "w", encoding="utf-8") as f:
                    f.write("".join(diff_gen))
                
                target_path.write_text(new_content, encoding="utf-8")
            else:
                pass

        with open(output_path, "w") as f:
            f.write(f"JUDGEMENT: {status}\nReason: Processed by Agent.")

        return str(output_path), status