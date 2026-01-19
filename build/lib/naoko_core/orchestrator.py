from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from pathlib import Path
import os
from .agents.gemini_client import GeminiClient
from .agents.codex_client import CodexClient
from .io.git_ops import GitOps

class Orchestrator:
    def __init__(self, doc_path: str, max_rounds: int, dry_run: bool, 
                 entry_point: str = None, existing_project: bool = False):
        self.doc_path = str(Path(doc_path).resolve())
        self.max_rounds = max_rounds
        self.dry_run = dry_run
        self.entry_point = entry_point
        self.existing_project = existing_project
        self.console = Console()
        
        self.root_dir = Path(os.getcwd()).resolve()
        self.gemini = GeminiClient(self.root_dir, dry_run)
        self.codex = CodexClient(self.root_dir, dry_run)

    def run(self):
        self.console.print(Panel.fit("Phase 1: Planning & Analysis", border_style="green"))
        if not os.path.exists(self.doc_path):
             self.console.print(f"[red]Error:[/red] Document '{self.doc_path}' not found.")
             return

        # 1-A. Style Analysis (If existing project)
        style_guide_path = None
        if self.entry_point:
            self.console.print(f"[bold]Targeting existing codebase starting at:[/bold] {self.entry_point}")
            style_guide_path = self.gemini.analyze_style(self.entry_point)

        # 1-B. Requirement Planning
        req_path = self.gemini.plan(self.doc_path)
        
        if not req_path or not os.path.exists(req_path) or os.path.getsize(req_path) == 0:
            self.console.print("[red]Critical Error: Planning failed. Requirement file is empty or missing.[/red]")
            return

        # 2. Implementation
        self.console.print(Panel.fit("Phase 2: Implementation", border_style="magenta"))
        # Pass entry_point as target_file
        patch_path, applied = self.codex.implement(req_path, style_guide_path, self.entry_point)
        
        if not applied:
            self.console.print("[bold red]Critical Error: Implementation patch failed to apply. Aborting.[/bold red]")
            return

        # 3. Review Loop
        self.console.print(Panel.fit(f"Phase 3: Review & Refine (Max {self.max_rounds} rounds)", border_style="cyan"))
        
        loop_success = False
        for i in range(1, self.max_rounds + 1):
            self.console.print(f"\n[bold underline]Round {i}/{self.max_rounds}[/bold underline]")
            
            review_path = self.gemini.review(patch_path, req_path, round_num=i)
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
                        answer = Prompt.ask(prompt_text, default=example)
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
                break
            elif status == "FAILED":
                self.console.print("[bold red]Result: FAILED - Patch application failed during refinement. Aborting.[/bold red]")
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
        else:
            self.console.print(Panel.fit("Phase 4: Failed", border_style="red"))
            self.console.print("[red]Workflow ended without a successful resolution.[/red]")
