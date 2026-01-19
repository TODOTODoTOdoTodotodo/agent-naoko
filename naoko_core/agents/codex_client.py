from rich.console import Console
import time
import os
from pathlib import Path
import difflib
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
        target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"
        
        if not self.dry_run:
            time.sleep(1)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if not target_path.exists():
                target_path.write_text(
                    "package com.example;\n\npublic class User {\n    private String username;\n}\n",
                    encoding="utf-8",
                )
            old_content = target_path.read_text(encoding="utf-8")
            new_content = old_content
            if "private String bio;" not in old_content:
                new_content = new_content.replace(
                    "private String username;\n",
                    "private String username;\n    private String bio;\n",
                )

            diff_gen = difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile="a/src/main/java/com/example/User.java",
                tofile="b/src/main/java/com/example/User.java",
            )
            diff_content = "".join(diff_gen)
            
            if not diff_content:
                console.print(f"[magenta]Codex Agent:[/magenta] No changes detected (Already implemented).")
                # Create an empty file to satisfy path existence check, or better, handle it gracefully.
                # But GitOps.apply_patch fails on empty file.
                # So we skip apply_patch.
                with open(output_path, "w") as f:
                    f.write("") # Clear it
                return str(output_path), True

            with open(output_path, "w", encoding="utf-8") as f:
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
                target_path = self.root_dir / "src" / "main" / "java" / "com" / "example" / "User.java"

                # Ensure target exists
                if not target_path.exists():
                     # Should not happen in refine, but safety first
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text("package com.example;\n\npublic class User {\n    private String username;\n}\n", encoding="utf-8")

                old_content = target_path.read_text(encoding="utf-8")
                new_content = old_content
                
                # Apply changes incrementally based on content check
                if "private String bio;" not in new_content:
                    new_content = new_content.replace(
                        "private String username;\n",
                        "private String username;\n    private String bio;\n",
                    )
                if "// Fix: Added validation logic" not in new_content:
                    new_content = new_content.replace(
                        "private String bio;\n",
                        "private String bio;\n    // Fix: Added validation logic\n",
                    )
                
                # Generate diff
                diff_gen = difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile="a/src/main/java/com/example/User.java",
                    tofile="b/src/main/java/com/example/User.java",
                )
                diff_content = "".join(diff_gen)

                if not diff_content:
                    console.print(f"[magenta]Codex Agent:[/magenta] No new fixes needed (Already applied).")
                    # If status was CHANGES_NEEDED but no changes, maybe we should switch to SUITABLE?
                    # Or just return success.
                    with open(patch_path, "w") as f:
                         f.write("")
                    # Do NOT call apply_patch on empty
                else:
                    with open(patch_path, "w", encoding="utf-8") as f:
                        f.write(diff_content)

                    applied = GitOps.apply_patch(str(patch_path), self.dry_run)
                    if not applied:
                        status = "FAILED"

            with open(output_path, "w") as f:
                f.write(f"JUDGEMENT: {status}\nReason: Addressing review.")

        console.print(f"[magenta]Codex Agent:[/magenta] Judgement: {status}")
        return str(output_path), status