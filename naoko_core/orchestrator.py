from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from pathlib import Path
import os
import secrets
import select
import sys
from .agents.gemini_client import GeminiClient
from .agents.codex_client import CodexClient
from .io.git_ops import GitOps

class Orchestrator:
    def __init__(self, doc_path: str, max_rounds: int, dry_run: bool, 
                 entry_point: str = None, existing_project: bool = False, resume: str = None, gemini_quality: str = "high"):
        self.doc_path = str(Path(doc_path).resolve())
        self.max_rounds = max_rounds
        self.dry_run = dry_run
        self.entry_point = entry_point
        self.existing_project = existing_project
        self.resume = resume
        self.gemini_quality = gemini_quality
        self.console = Console()
        
        self.root_dir = Path(os.getcwd()).resolve()
        self.gemini = GeminiClient(self.root_dir, dry_run, self.gemini_quality)
        self.codex = CodexClient(self.root_dir, dry_run)
        self.artifacts_dir = self.root_dir / "artifacts"
        self.session_id = resume or secrets.token_hex(4)
        self.session_dir = self.artifacts_dir / "sessions" / self.session_id
        self.progress_path = self.session_dir / "progress.md"
        self.run_log_path = self.session_dir / "run_log.md"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        state = {}
        if not self.progress_path.exists():
            return state
        for line in self.progress_path.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            state[key.strip()] = value.strip()
        return state

    def _save_state(self) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(f"{k}: {v}" for k, v in self.state.items())
        self.progress_path.write_text(content + "\n", encoding="utf-8")

    def _log_run(self, message: str) -> None:
        self.run_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.run_log_path, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def _prompt_with_timeout(self, question: str, default: str = "yes", timeout_sec: int = 15) -> str:
        self.console.print(f"{question} (auto '{default}' after {timeout_sec}s)")
        rlist, _, _ = select.select([sys.stdin], [], [], timeout_sec)
        if rlist:
            answer = sys.stdin.readline().strip()
            return answer if answer else default
        return default

    def run(self):
        if self.resume and not self.progress_path.exists():
            self.console.print(f"[red]Error:[/red] Session '{self.resume}' not found.")
            return
        self._log_run(f"run: start session={self.session_id}")
        self.console.print(Panel.fit("Phase 1: Planning & Analysis", border_style="green"))
        if not os.path.exists(self.doc_path):
             self.console.print(f"[red]Error:[/red] Document '{self.doc_path}' not found.")
             return

        # 1-A. Style Analysis (If existing project)
        style_guide_path = None
        if self.entry_point:
            self.console.print(f"[bold]Targeting existing codebase starting at:[/bold] {self.entry_point}")
            cached_style = self.state.get("style_guide_path")
            if cached_style and os.path.exists(cached_style):
                style_guide_path = cached_style
                self._log_run(f"phase1: reuse style_guide_path={cached_style}")
            else:
                style_guide_path = self.gemini.analyze_style(self.entry_point)
                if style_guide_path:
                    self.state["style_guide_path"] = style_guide_path
                    self._save_state()
                    self._log_run(f"phase1: style_guide_path={style_guide_path}")

        # 1-B. Requirement Planning
        cached_req = self.state.get("requirements_path")
        if cached_req and os.path.exists(cached_req):
            req_path = cached_req
            self._log_run(f"phase1: reuse requirements_path={cached_req}")
        else:
            req_path = self.gemini.plan(self.doc_path)
            if req_path:
                self.state["requirements_path"] = req_path
                self._save_state()
                self._log_run(f"phase1: requirements_path={req_path}")
        
        if not req_path or not os.path.exists(req_path) or os.path.getsize(req_path) == 0:
            self.console.print("[red]Critical Error: Planning failed. Requirement file is empty or missing.[/red]")
            self.state["last_failed_phase"] = "phase1"
            self._save_state()
            return

        # 2. Implementation
        self.console.print(Panel.fit("Phase 2: Implementation", border_style="magenta"))
        # Pass entry_point as target_file
        cached_patch = self.state.get("patch_path")
        if cached_patch and os.path.exists(cached_patch) and self.state.get("phase2_applied") == "true":
            patch_path = cached_patch
            applied = True
            self._log_run(f"phase2: reuse patch_path={cached_patch}")
        else:
            patch_path, applied = self.codex.implement(req_path, style_guide_path, self.entry_point)
            if applied and patch_path:
                self.state["patch_path"] = patch_path
                self.state["phase2_applied"] = "true"
                self._save_state()
                self._log_run(f"phase2: patch_path={patch_path}")
        
        if not applied:
            self.console.print("[bold red]Critical Error: Implementation patch failed to apply. Aborting.[/bold red]")
            self.state["last_failed_phase"] = "phase2"
            self.state["phase2_applied"] = "false"
            self._save_state()
            return

        # 3. Review Loop
        self.console.print(Panel.fit(f"Phase 3: Review & Refine (Max {self.max_rounds} rounds)", border_style="cyan"))
        
        loop_success = False
        for i in range(1, self.max_rounds + 1):
            self.console.print(f"\n[bold underline]Round {i}/{self.max_rounds}[/bold underline]")
            
            target_path = getattr(self.codex, "last_target_path", None) or self.entry_point
            review_path = self.gemini.review(patch_path, req_path, round_num=i, target_path=str(target_path) if target_path else None)
            if review_path and os.path.exists(review_path):
                review_content = Path(review_path).read_text(encoding="utf-8")
                questions = []
                in_questions = False
                for line in review_content.splitlines():
                    stripped = line.strip()
                    if stripped.lower().startswith("user questions"):
                        in_questions = True
                        continue
                    if in_questions and stripped.startswith("##"):
                        break
                    if in_questions and stripped.startswith("-"):
                        questions.append(stripped)

                if questions:
                    answers = []
                    for qline in questions:
                        qtext = qline.lstrip("-").strip()
                        example = ""
                        if "Example:" in qtext:
                            parts = qtext.split("Example:", 1)
                            qtext = parts[0].replace("Q:", "").strip(" |")
                            example = parts[1].split("|", 1)[0].strip()
                        else:
                            qtext = qtext.replace("Q:", "").strip()

                        prompt_text = f"{qtext}\nPress Enter to use the example."
                        answer = self._prompt_with_timeout(prompt_text, default=example, timeout_sec=15)
                        answers.append((qtext, answer))

                    if answers:
                        review_content += "\n\nUser Answers:\n"
                        for qtext, answer in answers:
                            review_content += f"- {qtext}: {answer}\n"
                        Path(review_path).write_text(review_content, encoding="utf-8")

            judgement_path, status = self.codex.refine(review_path)
            
            if status == "SUITABLE":
                self.console.print("[bold green]Result: SUITABLE - Process Complete![/bold green]")
                loop_success = True
                self.state["last_failed_phase"] = ""
                self.state["phase3_status"] = "SUITABLE"
                self._save_state()
                self._log_run("phase3: status=SUITABLE")
                break
            elif status == "FAILED":
                self.console.print("[bold red]Result: FAILED - Patch application failed during refinement. Aborting.[/bold red]")
                self.state["last_failed_phase"] = "phase3"
                self.state["phase3_status"] = "FAILED"
                self._save_state()
                self._log_run("phase3: status=FAILED")
                break
            elif status == "HOLD":
                if not Confirm.ask("Codex requests manual approval. Proceed?"):
                    self.console.print("[bold red]Process Aborted by User.[/bold red]")
                    return
                self.console.print("[green]User Approved. Continuing...[/green]")
            elif status == "CHANGES_NEEDED":
                 self.console.print("[yellow]Result: CHANGES NEEDED - Iterating...[/yellow]")
            elif status == "UNNECESSARY":
                 self.console.print("[yellow]Result: UNNECESSARY - Skipping fix...[/yellow]")
        
        if loop_success:
            if self.existing_project:
                self.console.print(Panel.fit("Phase 4: Completion (Draft)", border_style="yellow"))
                self.console.print("[yellow]Existing project detected. Changes applied but NOT committed.[/yellow]")
                self.console.print("Please review the changes and commit manually.")
            else:
                self.console.print(Panel.fit("Phase 4: Completion", border_style="green"))
                GitOps.commit("feat: Implemented features from " + Path(self.doc_path).name, self.dry_run)
            self.state["last_failed_phase"] = ""
            self.state["phase4_status"] = "COMPLETE"
            self._save_state()
            self._log_run("phase4: status=COMPLETE")
        else:
            self.console.print(Panel.fit("Phase 4: Failed", border_style="red"))
            self.console.print("[red]Workflow ended without a successful resolution.[/red]")
            self.state["phase4_status"] = "FAILED"
            self._save_state()
            self._log_run("phase4: status=FAILED")
