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
        
        self.token = AuthManager.get_codex_token()
        self.api_url = os.getenv("CODEX_API_URL", "https://api.openai.com/v1/chat/completions") 
        self.model = "gpt-5.2-codex"

        if not self.dry_run:
            os.makedirs(self.artifacts_dir, exist_ok=True)
            try:
                subprocess.run(["codex", "--version"], capture_output=True, check=True)
                self.has_codex_cli = True
            except (subprocess.CalledProcessError, FileNotFoundError):
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
            result = subprocess.run(command, input=prompt, capture_output=True, text=True, encoding='utf-8', timeout=600)
            if result.returncode == 0:
                return self._clean_code(result.stdout)
        except Exception as e:
            console.print(f"[red][Codex-Fallback] Error: {e}[/red]")
        return ""

    def _call_codex_cli(self, prompt: str) -> str:
        command = ["codex", "exec", "-m", self.model, "-c", "reasoning.effort=\"medium\"", "-"]
        try:
            console.print(f"[magenta][Codex CLI] Executing command via STDIN...[/magenta]")
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=600,
            )
            if result.returncode == 0:
                return self._clean_code(result.stdout)
            if result.stderr.strip():
                console.print(f"[red][Codex CLI] Error: {result.stderr.strip()}[/red]")
            return ""
        except Exception as e:
            console.print(f"[red][Codex CLI] Execution failed: {e}[/red]")
            return ""

    def _generate_code(self, prompt: str) -> str:
        if self.dry_run: return ""
        if self.has_codex_cli:
            code = self._call_codex_cli(prompt)
            if code: return code

        failures = 0
        max_retries = 3
        system_prompt = "You are an expert Java developer. Output ONLY raw Java code. Follow style guides strictly."

        while failures < max_retries:
            if not self.token: break
            try:
                console.print(f"[magenta][Codex] API Request (Attempt {failures+1}/3)...[/magenta]")
                headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
                payload = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "temperature": 0.2
                }
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=300)
                if response.status_code == 200:
                    return self._clean_code(response.json()["choices"][0]["message"]["content"])
                failures += 1
            except Exception:
                failures += 1
                time.sleep(1)

        return self._call_gemini_fallback(f"{system_prompt}\n\n{prompt}")

    def implement(self, req_path: str, style_guide_path: str = None, target_file: str = None) -> tuple[str, bool]:
        """
        Implements code into the specified target_file (Entry Point).
        """
        console.print(f"[magenta]Codex Agent:[/magenta] Reading requirements from '{req_path}'...")
        
        output_path = self.artifacts_dir / "patch.diff"
        
        # 1. Determine Target Path (Priority: target_file > style_guide_dir > Default)
        if target_file and os.path.exists(target_file):
            target_path = Path(target_file)
        elif style_guide_path:
            # Fallback to a file in the same directory as style guide
            target_path = Path(style_guide_path).parent / "ArticleController.java" # Heuristic
        else:
            target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"

        if self.dry_run: return str(output_path), True

        # 2. Read Requirements and Old Code
        with open(req_path, 'r') as f: req_content = f.read()
        
        if not target_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text("// New File\n", encoding="utf-8")
        
        old_content = target_path.read_text(encoding="utf-8")
        
        # 3. Load Style Guide
        style_instruction = ""
        if style_guide_path and os.path.exists(style_guide_path):
            console.print(f"[magenta]Codex Agent:[/magenta] Applying style guide from '{style_guide_path}'...")
            style_instruction = f"STYLE GUIDELINES:\n{Path(style_guide_path).read_text()}\n\n"
        
        # 4. Generate Code
        prompt = (
            f"{style_instruction}"
            f"Requirements:\n{req_content}\n\n"
            f"Current File ({target_path.name}):\n{old_content}\n\n"
            f"Task: Update the file to implement requirements. Return COMPLETE code."
        )

        new_content = self._generate_code(prompt)
        if not new_content: return str(output_path), False

        # 5. Generate Diff and Overwrite
        diff_gen = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{target_path.name}", tofile=f"b/{target_path.name}"
        )
        with open(output_path, "w", encoding="utf-8") as f: f.write("".join(diff_gen))

        console.print(f"[magenta]Codex Agent:[/magenta] Updating file: [bold]{target_path}[/bold]")
        target_path.write_text(new_content, encoding="utf-8")
        
        # Store last target path for refine phase
        self.last_target_path = target_path
        return str(output_path), True

    def refine(self, review_path: str) -> tuple[str, str]:
        console.print(f"[magenta]Codex Agent:[/magenta] Analyzing review feedback...")
        output_path = self.artifacts_dir / "review_judgement.md"
        
        if not os.path.exists(review_path): return str(output_path), "FAILED"
        review_content = Path(review_path).read_text()

        status = "CHANGES_NEEDED" if any(k in review_content for k in ["Issue", "Bug", "Missing", "[High]", "[Medium]"]) else "SUITABLE"
        
        if status == "CHANGES_NEEDED" and hasattr(self, 'last_target_path'):
            console.print(f"[magenta]Codex Agent:[/magenta] Fixing issues in {self.last_target_path}...")
            old_content = self.last_target_path.read_text()
            prompt = f"Fix issues in this code based on review.\nReview: {review_content}\nCode:\n{old_content}"
            new_content = self._generate_code(prompt)
            
            if new_content and new_content.strip() != old_content.strip():
                self.last_target_path.write_text(new_content, encoding="utf-8")
        
        with open(output_path, "w") as f: f.write(f"JUDGEMENT: {status}")
        return str(output_path), status
