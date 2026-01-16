import typer
from rich.console import Console
from .orchestrator import Orchestrator

app = typer.Typer()
console = Console()

@app.command()
def start(
    doc_path: str = typer.Argument(..., help="Path to the planning document (PDF, XLSX, MD, etc.)"),
    max_rounds: int = typer.Option(5, help="Maximum number of review rounds"),
    dry_run: bool = typer.Option(False, help="Run without executing actual agents")
):
    """
    Start the Naoko Architect System.
    """
    console.print(f"[bold green]Starting Naoko Architect System[/bold green]")
    console.print(f"Target Document: [bold]{doc_path}[/bold]")
    console.print(f"Max Rounds: {max_rounds}")
    
    if dry_run:
        console.print("[yellow]Dry Run Mode Enabled[/yellow]")
        return

    orchestrator = Orchestrator(doc_path, max_rounds, dry_run)
    orchestrator.run()

if __name__ == "__main__":
    app()