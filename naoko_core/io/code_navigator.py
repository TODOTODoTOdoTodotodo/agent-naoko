import os
import re
from pathlib import Path
from rich.console import Console

console = Console()

class CodeNavigator:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def find_related_files(self, entry_point: str) -> list[str]:
        """
        Reads the entry point (Controller) and finds related Service, DTO, and Client files.
        """
        entry_path = Path(entry_point)
        if not entry_path.exists():
            console.print(f"[yellow][Navigator] Entry point {entry_point} not found.[/yellow]")
            return []

        related_files = [str(entry_path)]
        content = entry_path.read_text(encoding="utf-8")

        # 1. Extract potential class names (Services, DTOs, Clients)
        # Look for imports and fields
        # Regex to find capitalized words ending in Service, DTO, Repository, Client, etc.
        # This is a heuristic approach.
        potential_names = set()
        
        # Find explicit imports
        imports = re.findall(r'import\s+([\w.]+);', content)
        for imp in imports:
            class_name = imp.split('.')[-1]
            if not class_name.startswith("java.") and not class_name.startswith("org.springframework."):
                potential_names.add(class_name)

        # Find fields like "private UserService userService;"
        fields = re.findall(r'private\s+([A-Z]\w+)\s+\w+;', content)
        potential_names.update(fields)

        # 2. Search for these files in the project
        # We assume standard Maven/Gradle structure src/main/java
        base_src = self.root_dir / "src" / "main" / "java"
        if not base_src.exists():
            base_src = self.root_dir # Fallback

        for name in potential_names:
            # Skip common Java/Spring types
            if name in ["List", "Map", "String", "Integer", "Long", "ResponseEntity", "Optional"]:
                continue
                
            # Search file named {name}.java
            found = list(base_src.rglob(f"{name}.java"))
            if found:
                # Take the first match
                related_files.append(str(found[0]))
                console.print(f"[dim][Navigator] Found related file: {found[0].name}[/dim]")

        return list(set(related_files)) # Deduplicate
