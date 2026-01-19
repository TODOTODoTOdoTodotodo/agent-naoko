from rich.console import Console
import time
import os
from pathlib import Path
from ..io.git_ops import GitOps
from ..auth import AuthManager

console = Console()

class CodexClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        
        # Load Auth Token
        self.token = AuthManager.get_codex_token()
        
        if not self.dry_run:
            os.makedirs(self.artifacts_dir, exist_ok=True)

    def implement(self, req_path: str) -> tuple[str, bool]:
        """
        Implements the code and returns (patch_path, success_flag).
        """
        console.print(f"[magenta]Codex Agent:[/magenta] Reading requirements from '{req_path}'...")
        
        output_path = self.artifacts_dir / "patch.diff"
        
        if not self.dry_run:
            time.sleep(1)
            # Create a valid unified diff (Simulation: Initial State)
            # Assuming src/main/java/com/example/User.java exists from previous steps
            diff_content = (
                "--- a/src/main/java/com/example/User.java\n"
                "+++ b/src/main/java/com/example/User.java\n"
                "@@ -2,4 +2,5 @@\n"
                " \n"
                " public class User {\n"
                "     private String username;\n"
                "+    private String bio;\n"
                " }\n"
            )
            with open(output_path, "w") as f:
                f.write(diff_content)
            
            applied = GitOps.apply_patch(str(output_path), self.dry_run)
            return str(output_path), applied
        else:
             console.print(f"[magenta]Codex Agent:[/magenta] (Dry-run) Skipping implementation.")
             return str(output_path), True

    def refine(self, review_path: str) -> tuple[str, str]:
        """
        Analyzes the review and decides the next action.
        """
        console.print(f"[magenta]Codex Agent:[/magenta] Analyzing review feedback from '{review_path}'...")
        
        output_path = self.artifacts_dir / "review_judgement.md"
        status = "SUITABLE"
        
        if not self.dry_run:
            time.sleep(1)
            
            review_content = ""
            if os.path.exists(review_path):
                with open(review_path, 'r') as f:
                    review_content = f.read()
            
            if "Issue" in review_content:
                status = "CHANGES_NEEDED"
            else:
                status = "SUITABLE"

            if status == "CHANGES_NEEDED":
                 console.print(f"[magenta]Codex Agent:[/magenta] Applying fixes (Regenerating patch)...")
                 patch_path = self.artifacts_dir / "patch.diff"
                 
                 # Fix: Do NOT append. Regenerate the FULL valid diff.
                 # Simulation: Adding validation comment and fields properly
                 new_diff_content = (
                    "--- a/src/main/java/com/example/User.java\n"
                    "+++ b/src/main/java/com/example/User.java\n"
                    "@@ -2,4 +2,6 @@\n"
                    " \n"
                    " public class User {\n"
                    "     private String username;\n"
                    "+    private String bio;\n"
                    "+    // Fix: Added validation logic\n"
                    " }\n"
                 )
                 
                 # First, revert the previous patch to apply the new one cleanly (or assume git handles it if context matches)
                 # For simplicity in simulation, we assume we are applying to the original state 
                 # OR we need to reverse the previous patch. 
                 # Here, we will try to apply. If it fails due to conflict, we might need a reset strategy.
                 # Let's write the NEW patch.
                 with open(patch_path, "w") as f:
                     f.write(new_diff_content)
                 
                 # In a real scenario, we might need `git apply -R` first or `git checkout`.
                 # We will assume the user has a clean slate or we use `git apply --reject`
                 # For this sim, let's try applying directly.
                 applied = GitOps.apply_patch(str(patch_path), self.dry_run)
                 if not applied:
                     status = "FAILED"

            with open(output_path, "w") as f:
                f.write(f"JUDGEMENT: {status}\nReason: Addressing review.")

        console.print(f"[magenta]Codex Agent:[/magenta] Judgement: {status}")
        return str(output_path), status
