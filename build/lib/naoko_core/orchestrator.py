from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
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
        # Pass style guide if available
        patch_path, applied = self.codex.implement(req_path, style_guide_path)
        
        if not applied:
            self.console.print("[bold red]Critical Error: Implementation patch failed to apply. Aborting.[/bold red]")
            return

        # 3. Review Loop
        self.console.print(Panel.fit(f"Phase 3: Review & Refine (Max {self.max_rounds} rounds)", border_style="cyan"))
        
        loop_success = False
        for i in range(1, self.max_rounds + 1):
            self.console.print(f"\n[bold underline]Round {i}/{self.max_rounds}[/bold underline]")
            
            review_path = self.gemini.review(patch_path, req_path, round_num=i)
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