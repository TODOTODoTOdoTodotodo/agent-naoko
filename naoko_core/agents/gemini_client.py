import os
import requests
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from pathlib import Path
from rich.console import Console
from ..io.doc_parser import DocParser
from ..io.code_navigator import CodeNavigator
from ..auth import AuthManager

console = Console()

class GeminiClient:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.artifacts_dir = self.root_dir / "artifacts"
        self.dry_run = dry_run
        self.auth_obj = None 
        
        if not self.dry_run:
            self.auth_obj = AuthManager.get_gemini_credentials()
            os.makedirs(self.artifacts_dir, exist_ok=True)
            
            if isinstance(self.auth_obj, str):
                genai.configure(api_key=self.auth_obj)
            elif not self.auth_obj:
                 console.print("[red][Gemini] Authentication failed/skipped. Agent disabled.[/red]")

    def _call_gemini_oauth(self, prompt: str, system_instruction: str = None) -> str:
        if not self.auth_obj or not isinstance(self.auth_obj, Credentials): return ""
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3:generateContent"
        headers = {
            "Authorization": f"Bearer {self.auth_obj.token}",
            "Content-Type": "application/json"
        }
        contents = [{"parts": [{"text": prompt}]}]
        payload = {"contents": contents}
        if system_instruction:
             payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            console.print(f"[red][Gemini] OAuth API Error: {e}[/red]")
            return ""

    def _call_gemini_sdk(self, prompt: str, system_instruction: str = None) -> str:
        try:
            model = genai.GenerativeModel(
                model_name="gemini-3",
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            return response.text if response else ""
        except Exception as e:
            console.print(f"[red][Gemini] SDK Error: {e}[/red]")
            return ""

    def _call_model(self, prompt: str, sys_inst: str = None) -> str:
        if isinstance(self.auth_obj, str):
            return self._call_gemini_sdk(prompt, sys_inst)
        return self._call_gemini_oauth(prompt, sys_inst)

    def analyze_style(self, entry_point: str) -> str:
        """
        Analyzes the coding style of the existing project starting from the entry point.
        """
        console.print(f"[blue]Gemini Agent:[/blue] Analyzing code style from '{entry_point}'...")
        
        if self.dry_run or not self.auth_obj: return ""

        # 1. Find related files
        navigator = CodeNavigator(self.root_dir)
        related_files = navigator.find_related_files(entry_point)
        
        if not related_files:
            console.print("[yellow]No related files found for analysis.[/yellow]")
            return ""

        # 2. Prepare Context (Concatenate file contents)
        context = ""
        for file_path in related_files[:5]: # Limit to 5 files to save tokens
            try:
                p = Path(file_path)
                content = p.read_text(encoding="utf-8")
                # Truncate large files
                if len(content) > 5000: content = content[:5000] + "\n...[Truncated]"
                context += f"--- File: {p.name} ---\n{content}\n\n"
            except Exception as e:
                console.print(f"[yellow]Skipped file {file_path}: {e}[/yellow]")

        # 3. Call Gemini
        sys_inst = "You are a Tech Lead. Analyze the code to extract the project's Coding Style Guidelines."
        prompt = (
            f"Analyze the following source code files and document the coding style conventions.\n"
            f"Context:\n{context}\n\n"
            f"Output a Markdown file (`CODING_STYLE.md`) covering:\n"
            f"1. Language & Framework versions\n"
            f"2. Naming Conventions (Classes, Methods, Variables)\n"
            f"3. Library Usage (Lombok, Jakarta/Javax, etc.)\n"
            f"4. Error Handling patterns\n"
            f"5. Architecture (Controller-Service-Repository pattern?)\n"
            f"6. DTO/Entity patterns\n"
        )
        
        result = self._call_model(prompt, sys_inst)
        
        if result:
            # Save to entry point directory
            style_path = Path(entry_point).parent / "CODING_STYLE.md"
            with open(style_path, "w", encoding="utf-8") as f:
                f.write(result)
            console.print(f"[blue]Gemini Agent:[/blue] Style guide created at '{style_path}'.")
            return str(style_path)
        
        return ""

    def plan(self, doc_path: str) -> str:
        console.print(f"[blue]Gemini Agent:[/blue] Analyzing document at '{doc_path}'...")
        if not self.auth_obj: return ""
        
        parsed_text = DocParser.parse(doc_path)
        if not parsed_text: return ""
        
        output_path = self.artifacts_dir / "requirements_request.md"
        if self.dry_run: return str(output_path)
        
        console.print(f"[blue]Gemini Agent:[/blue] Sending {len(parsed_text)} chars context...")
        
        sys_inst = "You are a Senior Software Architect. Analyze the document and generate a development request in Markdown."
        prompt = f"Analyze this document content:\n\n{parsed_text}"
        
        result = self._call_model(prompt, sys_inst)
        if result:
            with open(output_path, "w", encoding="utf-8") as f: f.write(result)
            console.print(f"[blue]Gemini Agent:[/blue] Real requirements generated.")
            return str(output_path)
        return ""

    def review(self, patch_path: str, req_path: str, round_num: int) -> str:
        console.print(f"[blue]Gemini Agent:[/blue] Reviewing patch (Round {round_num})...")
        if not self.auth_obj: return ""
        
        output_path = self.artifacts_dir / "review.md"
        if self.dry_run: return str(output_path)
        
        with open(req_path, 'r') as f: req_content = f.read()
        with open(patch_path, 'r') as f: patch_content = f.read()
        
        prompt = f"Review patch against requirements.\nReq:\n{req_content}\nPatch:\n{patch_content}\nIdentify issues."
        
        result = self._call_model(prompt)
        if result:
            with open(output_path, "w", encoding="utf-8") as f: f.write(result)
            
        return str(output_path)
