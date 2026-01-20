import typer
from rich.console import Console
from .orchestrator import Orchestrator

console = Console()

def main(
    doc_path: str = typer.Argument(..., help="Path to the planning document (PDF, XLSX, MD, etc.)"),
    max_rounds: int = typer.Option(5, help="Maximum number of review rounds"),
    dry_run: bool = typer.Option(False, help="Run without executing actual agents"),
    entry_point: str = typer.Option(None, help="Path to the Controller file for style analysis (e.g. src/.../UserController.java)"),
    existing_project: bool = typer.Option(False, help="Set flag if working on an existing project (skips auto-commit)"),
    resume: str = typer.Option(None, help="Resume a previous run by session id"),
    gemini_quality: str = typer.Option(None, help="Gemini quality: high, normal, fast")
):
    """
    Naoko Architect System: Automated Coding Agent.
    """
    console.print(f"[bold green]Starting Naoko Architect System[/bold green]")
    console.print(f"Target Document: [bold]{doc_path}[/bold]")
    
    if entry_point:
        console.print(f"Entry Point: [bold]{entry_point}[/bold]")
        if not existing_project:
            existing_project = True
            
    if existing_project:
        console.print("[yellow]Mode: Existing Project (No Auto-Commit)[/yellow]")

    if not gemini_quality:
        gemini_quality = "high"
    orchestrator = Orchestrator(doc_path, max_rounds, dry_run, entry_point, existing_project, resume, gemini_quality)
    orchestrator.run()

def app():
    typer.run(main)

if __name__ == "__main__":
    app()
