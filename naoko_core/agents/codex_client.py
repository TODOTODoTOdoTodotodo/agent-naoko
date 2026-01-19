import os
import time
import threading
import requests
import difflib
import subprocess
import re
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from ..io.git_ops import GitOps
from ..auth import AuthManager

console = Console()

class CodexClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        self.has_codex_cli = False
        self.last_error = ""
        self.error_log_path = self.artifacts_dir / "codex_error.log"
        
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

    def _clean_code(self, text: str, expected_class: str | None = None) -> str:
        """Removes markdown code fences and conversational filler."""
        if not text: return ""
        
        # 1. Try to extract from markdown code blocks
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # Return the longest block, assuming it's the main code
            cleaned = max(matches, key=len).strip()
            if expected_class and not self._has_expected_class(cleaned, expected_class):
                self.last_error = f"Expected class '{expected_class}' not found in code block."
                return ""
            return cleaned
            
        # 2. If no blocks, try to find the start of Java code
        # Look for package declaration or imports or class definition
        java_start_pattern = r"(package\s+[\w\.]+;|import\s+[\w\.]+;|public\s+(?:class|interface|enum)\s+\w+)"
        stripped = re.sub(r"^\s*(?:(//[^\n]*\n)|(/\*.*?\*/\s*))+",
                          "",
                          text,
                          flags=re.DOTALL)
        match = re.search(java_start_pattern, stripped)
        if match:
            cleaned = stripped[match.start():].strip()
            if expected_class and not self._has_expected_class(cleaned, expected_class):
                self.last_error = f"Expected class '{expected_class}' not found in output."
                return ""
            return cleaned
            
        if expected_class:
            self.last_error = f"Expected class '{expected_class}' not found in output."
            return ""
        return text.strip()

    def _has_expected_class(self, text: str, expected_class: str) -> bool:
        if re.search(rf"\\b(class|interface|enum)\\s+{re.escape(expected_class)}\\b", text):
            return True
        if "@RestController" in text and expected_class in text:
            return True
        return False

    def _log_error(self, message: str) -> None:
        if not message:
            return
        self.last_error = message
        try:
            self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.error_log_path, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")
        except Exception:
            pass

    def _start_wait_timer(self, label: str) -> tuple[threading.Event, float]:
        start = time.time()
        stop_event = threading.Event()

        def _ticker():
            while not stop_event.wait(30):
                elapsed = int(time.time() - start)
                console.print(f"[dim]{label}... elapsed {elapsed}s[/dim]")

        thread = threading.Thread(target=_ticker, daemon=True)
        thread.start()
        return stop_event, start

    def _call_gemini_fallback(
        self,
        prompt: str,
        timeout_sec: int = 1200,
        expected_class: str | None = None,
    ) -> str:
        console.print("[yellow][Codex] Switching to Gemini CLI (Fallback)...[/yellow]")
        stop_event, start = self._start_wait_timer("Gemini CLI waiting")
        try:
            command = ["gemini", "--output-format", "text"]
            result = subprocess.run(command, input=prompt, capture_output=True, text=True, encoding='utf-8', timeout=timeout_sec)
            elapsed = int(time.time() - start)
            if result.returncode == 0:
                console.print(f"[dim][Gemini CLI] Done in {elapsed}s[/dim]")
                cleaned = self._clean_code(result.stdout, expected_class=expected_class)
                if not cleaned and expected_class:
                    self._log_error(self.last_error or f"Gemini output missing expected class: {expected_class}")
                    console.print(f"[red][Codex-Fallback] {self.last_error}[/red]")
                return cleaned
            console.print(f"[dim][Gemini CLI] Finished in {elapsed}s (non-zero exit)[/dim]")
        except subprocess.TimeoutExpired:
            elapsed = int(time.time() - start)
            console.print(f"[yellow][Gemini CLI] Timed out after {elapsed}s.[/yellow]")
            choice = Prompt.ask("Continue waiting?", default="yes", choices=["yes", "no"])
            if choice == "yes":
                return self._call_gemini_fallback(prompt, timeout_sec=timeout_sec, expected_class=expected_class)
        except Exception as e:
            console.print(f"[red][Codex-Fallback] Error: {e}[/red]")
        finally:
            stop_event.set()
        return ""

    def _call_codex_cli(
        self,
        prompt: str,
        timeout_sec: int = 1200,
        expected_class: str | None = None,
    ) -> str:
        command = ["codex", "exec", "-m", self.model, "-c", "reasoning.effort=\"medium\"", "-"]
        cli_prompt = (
            "SYSTEM: You are a code generator. Output ONLY the complete Java file content. "
            "Do NOT ask questions. Do NOT include analysis or markdown.\n\n"
            f"{prompt}"
        )
        stop_event, start = self._start_wait_timer("Codex CLI waiting")
        try:
            console.print(f"[magenta][Codex CLI] Executing command via STDIN...[/magenta]")
            result = subprocess.run(
                command,
                input=cli_prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout_sec,
            )
            elapsed = int(time.time() - start)
            if result.returncode == 0:
                console.print(f"[dim][Codex CLI] Done in {elapsed}s[/dim]")
                cleaned = self._clean_code(result.stdout, expected_class=expected_class)
                if not cleaned and expected_class:
                    self._log_error(self.last_error or f"Codex CLI output missing expected class: {expected_class}")
                    console.print(f"[red][Codex CLI] {self.last_error}[/red]")
                return cleaned
            console.print(f"[red][Codex CLI] Error: {result.stderr.strip()}[/red]")
            self._log_error(result.stderr.strip())
            return ""
        except subprocess.TimeoutExpired:
            elapsed = int(time.time() - start)
            console.print(f"[yellow][Codex CLI] Timed out after {elapsed}s.[/yellow]")
            choice = Prompt.ask(
                "Continue waiting and retry? (Enter to use example)",
                default="yes",
                choices=["yes", "no"],
            )
            if choice == "yes":
                return self._call_codex_cli(prompt, timeout_sec=timeout_sec, expected_class=expected_class)
            return ""
        except Exception as e:
            console.print(f"[red][Codex CLI] Execution failed: {e}[/red]")
            return ""
        finally:
            stop_event.set()

    def _generate_code(
        self,
        prompt: str,
        codex_timeout_sec: int = 1200,
        api_timeout_sec: int = 1200,
        gemini_timeout_sec: int = 1200,
        expected_class: str | None = None,
    ) -> str:
        if self.dry_run: return ""
        
        if self.has_codex_cli:
            code = self._call_codex_cli(prompt, timeout_sec=codex_timeout_sec, expected_class=expected_class)
            if code: return code
            console.print("[red][Codex] CLI execution failed. Trying API/Fallback.[/red]")

        failures = 0
        max_retries = 3
        system_prompt = (
            "You are an expert Java developer.\n"
            "CRITICAL RULES:\n"
            "1. Output ONLY the raw Java code. Do NOT include any explanations, markdown formatting, or 'Here is the code'.\n"
            "2. You MUST return the COMPLETE file content, including all existing methods and fields. Do NOT skip or truncate existing code.\n"
            "3. If modifying an existing file, merge the new requirements into it while preserving the original structure.\n"
            "4. Start with the 'package' declaration."
        )

        while failures < max_retries:
            if not self.token: break
            stop_event, start = self._start_wait_timer("Codex API waiting")
            try:
                console.print(f"[magenta][Codex] API Request (Attempt {failures+1}/3)...[/magenta]")
                headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
                payload = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "temperature": 0.2
                }
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=api_timeout_sec)
                elapsed = int(time.time() - start)
                if response.status_code == 200:
                    console.print(f"[dim][Codex API] Done in {elapsed}s[/dim]")
                    cleaned = self._clean_code(response.json()["choices"][0]["message"]["content"], expected_class=expected_class)
                    if not cleaned and expected_class:
                        self._log_error(self.last_error or f"Codex API output missing expected class: {expected_class}")
                        console.print(f"[red][Codex] {self.last_error}[/red]")
                    return cleaned
                console.print(f"[dim][Codex API] Finished in {elapsed}s (status {response.status_code})[/dim]")
                self._log_error(f"Codex API status {response.status_code}")
                failures += 1
            except Exception as e:
                self._log_error(f"Codex API error: {e}")
                console.print(f"[yellow][Codex] Connection Error: {e}[/yellow]")
                failures += 1
                time.sleep(1)
            finally:
                stop_event.set()

        return self._call_gemini_fallback(
            f"{system_prompt}\n\n{prompt}",
            timeout_sec=gemini_timeout_sec,
            expected_class=expected_class,
        )

    def implement(self, req_path: str, style_guide_path: str = None, target_file: str = None) -> tuple[str, bool]:
        console.print(f"[magenta]Codex Agent:[/magenta] Reading requirements from '{req_path}'...")
        
        output_path = self.artifacts_dir / "patch.diff"
        
        # Determine target
        if target_file and os.path.exists(target_file):
            target_path = Path(target_file)
        elif style_guide_path:
            target_path = Path(style_guide_path).parent / "ArticleController.java" # Fallback
        else:
            target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"

        if self.dry_run: return str(output_path), True

        with open(req_path, 'r') as f: req_content = f.read()
        
        if not target_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text("// New File\n", encoding="utf-8")
        
        old_content = target_path.read_text(encoding="utf-8")
        
        style_instruction = ""
        if style_guide_path and os.path.exists(style_guide_path):
            console.print(f"[magenta]Codex Agent:[/magenta] Applying style guide from '{style_guide_path}'...")
            style_instruction = f"STYLE GUIDELINES:\n{Path(style_guide_path).read_text()}\n\n"
        
        expected_class = target_path.stem
        prompt = (
            f"{style_instruction}"
            f"Requirements:\n{req_content}\n\n"
            f"Current File Content ({target_path.name}):\n```java\n{old_content}\n```\n\n"
            f"Task: Implement the requirements into this file.\n"
            f"Constraints:\n"
            f"- Output ONLY the complete Java file content for {target_path.name}.\n"
            f"- You MUST include `public class {expected_class}` in the output.\n"
            f"- Do NOT remove any existing code unless specified.\n"
            f"- Do NOT return a diff, markdown fences, or review/analysis text."
        )

        new_content = self._generate_code(
            prompt,
            codex_timeout_sec=3600,
            api_timeout_sec=3600,
            gemini_timeout_sec=1200,
            expected_class=expected_class,
        )
        if not new_content:
            if expected_class:
                relaxed = self._generate_code(
                    prompt,
                    codex_timeout_sec=3600,
                    api_timeout_sec=3600,
                    gemini_timeout_sec=1200,
                    expected_class=None,
                )
                if relaxed and ("package " in relaxed or "import " in relaxed):
                    console.print("[yellow][Codex] Retrying without class-name guard. Please verify output.[/yellow]")
                    new_content = relaxed
                else:
                    self._log_error(self.last_error or "No valid code generated.")
                    console.print(f"[red][Codex] Generation failed. See {self.error_log_path}[/red]")
                    return str(output_path), False
            else:
                if self.last_error:
                    console.print(f"[red][Codex] Generation failed: {self.last_error}[/red]")
                return str(output_path), False

        # Safety Check: If new content is suspiciously short or doesn't look like Java
        if len(new_content) < len(old_content) * 0.5:
            self._log_error("Generated code is significantly shorter than original.")
            console.print("[red][Codex] Warning: Generated code is significantly shorter than original. Aborting overwrite to protect file.[/red]")
            console.print(f"[dim]Generated: {new_content[:200]}...[/dim]")
            return str(output_path), False

        if "package " not in new_content and "import " not in new_content:
             self._log_error("Generated code missing package/import.")
             console.print("[red][Codex] Warning: Generated code does not look like a valid Java file (missing package/import). Aborting.[/red]")
             return str(output_path), False

        # Generate Diff
        diff_gen = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{target_path.name}", tofile=f"b/{target_path.name}"
        )
        with open(output_path, "w", encoding="utf-8") as f: f.write("".join(diff_gen))

        console.print(f"[magenta]Codex Agent:[/magenta] Updating file: [bold]{target_path}[/bold]")
        target_path.write_text(new_content, encoding="utf-8")
        
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
            expected_class = self.last_target_path.stem
            prompt = (
                f"Review Feedback:\n{review_content}\n\n"
                f"Current Code:\n```java\n{old_content}\n```\n\n"
                f"Task: Fix the code based on the review.\n"
                f"Constraints:\n"
                f"- Output ONLY the complete Java file content for {self.last_target_path.name}.\n"
                f"- You MUST include `public class {expected_class}` in the output.\n"
                f"- Preserve unrelated logic.\n"
                f"- Do NOT return analysis, review text, or markdown fences."
            )
            new_content = self._generate_code(prompt, expected_class=expected_class)
            
            if new_content and new_content.strip() != old_content.strip():
                # Safety check again
                if len(new_content) > 50 and ("package " in new_content or "import " in new_content):
                    self.last_target_path.write_text(new_content, encoding="utf-8")
                else:
                    console.print("[red][Codex] Fix result invalid. Skipping update.[/red]")
        
        with open(output_path, "w") as f: f.write(f"JUDGEMENT: {status}")
        return str(output_path), status
