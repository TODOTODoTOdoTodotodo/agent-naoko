import os
import time
import requests
import difflib
import subprocess
import re
from pathlib import Path
from rich.console import Console
from ..io.git_ops import GitOps
from ..auth import AuthManager

console = Console()

class CodexClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        self.has_codex_cli = False
        
        # Codex Settings
        # self.token = AuthManager.get_codex_token() # No longer primary if CLI used
        # self.api_url = os.getenv("CODEX_API_URL", "https://api.openai.com/v1/chat/completions") 
        self.model = "gpt-5.2_codex-medium"

        if not self.dry_run:
            os.makedirs(self.artifacts_dir, exist_ok=True)
            try:
                subprocess.run(["codex", "--version"], capture_output=True, check=True)
                self.has_codex_cli = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                # console.print("[yellow][Codex] 'codex' CLI not found. Will default to Gemini Fallback.[/yellow]")
                self.has_codex_cli = False

    def _clean_code(self, text: str) -> str:
        if not text: return ""
        pattern = r"```(?:\w+)?\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _call_gemini_fallback(self, prompt: str) -> str:
        console.print("[yellow][Codex] Switching to Gemini CLI (Fallback)...[/yellow]")
        try:
            command = ["gemini", "--output-format", "text"]
            result = subprocess.run(
                command, 
                input=prompt,
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
        """Executes 'codex' CLI using STDIN."""
        # Assuming usage: echo "prompt" | codex --model ...
        # Or: codex [args] (reading stdin)
        
        # NOTE: Adjust arguments based on actual `codex --help`
        # Trying to pass prompt via STDIN which is safer for large text
        command = ["codex", "--model", self.model]
        
        try:
            console.print(f"[magenta][Codex CLI] Executing command via STDIN...[/magenta]")
            
            # Using input=prompt to pipe data to stdin
            result = subprocess.run(
                command, 
                input=prompt,
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                timeout=120
            )
            
            if result.returncode != 0:
                # If STDIN fails, maybe it expects argument?
                # Fallback to argument method if returncode is non-zero (and maybe specific error)
                # But let's log error first.
                console.print(f"[red][Codex CLI] Error: {result.stderr.strip()}[/red]")
                
                # Retry with Argument strategy if STDIN failed
                console.print(f"[magenta][Codex CLI] Retrying with Argument strategy...[/magenta]")
                command_arg = ["codex", "prompt", prompt, "--model", self.model]
                result_arg = subprocess.run(
                    command_arg,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=120
                )
                if result_arg.returncode == 0:
                    return self._clean_code(result_arg.stdout)
                
                return ""
            
            return self._clean_code(result.stdout)
        except Exception as e:
            console.print(f"[red][Codex CLI] Execution failed: {e}[/red]")
            return ""

    def _generate_code(self, prompt: str) -> str:
        if self.dry_run: return ""

        if self.has_codex_cli:
            code = self._call_codex_cli(prompt)
            if code: return code
            console.print("[red][Codex] CLI execution failed. Skipping API/Fallback.[/red]")
            # If CLI exists but fails, do we fallback?
            # Yes, let's try Gemini as last resort.
        
        return self._call_gemini_fallback(prompt)

    def implement(self, req_path: str, style_guide_path: str = None) -> tuple[str, bool]:
        console.print(f"[magenta]Codex Agent:[/magenta] Reading requirements from '{req_path}'...")
        
        output_path = self.artifacts_dir / "patch.diff"
        target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"
        
        if self.dry_run: return str(output_path), True

        if not req_path or not os.path.exists(req_path):
             return str(output_path), False
             
        with open(req_path, 'r') as f: req_content = f.read()
        
        # Style Guide Injection
        style_instruction = ""
        if style_guide_path and os.path.exists(style_guide_path):
            console.print(f"[magenta]Codex Agent:[/magenta] Loading style guide from '{style_guide_path}'...")
            with open(style_guide_path, 'r') as f:
                style_content = f.read()
            style_instruction = f"Strictly follow these CODING STYLE GUIDELINES:\n{style_content}\n\n"
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists():
            target_path.write_text("package com.example;\n\npublic class User {\n    private String username;\n}\n", encoding="utf-8")
        
        old_content = target_path.read_text(encoding="utf-8")
        
        prompt = (
            f"{style_instruction}"
            f"Requirements:\n{req_content}\n\n"
            f"Current Code (User.java):\n{old_content}\n\n"
            f"Task: Implement the requirements by updating the existing code.\n"
            f"Return the COMPLETE, valid Java file content."
        )

        new_content = self._generate_code(prompt)
        
        if not new_content:
            console.print("[red][Codex] Failed to generate code.[/red]")
            return str(output_path), False

        diff_gen = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="a/src/main/java/com/example/User.java",
            tofile="b/src/main/java/com/example/User.java",
        )
        diff_content = "".join(diff_gen)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(diff_content)

        console.print(f"[magenta][Codex] Updating file: {target_path}[/magenta]")
        target_path.write_text(new_content, encoding="utf-8")
        
        return str(output_path), True

    def refine(self, review_path: str) -> tuple[str, str]:
        console.print(f"[magenta]Codex Agent:[/magenta] Analyzing review feedback...")
        
        output_path = self.artifacts_dir / "review_judgement.md"
        status = "SUITABLE"
        
        if self.dry_run: return str(output_path), status

        if not os.path.exists(review_path):
             console.print("[red][Codex] Review file missing. Aborting refine.[/red]")
             return str(output_path), "FAILED"

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
                f"Task: Fix the code based on the review.\n"
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