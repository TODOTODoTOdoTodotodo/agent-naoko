# Naoko Architect System Design Document

## 1. Overview
**Naoko** is a dual-agent coding orchestration system. It leverages two specialized CLI agents:
- **Gemini CLI (Planner/Reviewer):** Parses requirements, creates development requests, and reviews code.
- **Codex CLI (Implementer):** Writes code based on requests and fixes issues based on reviews.

## 2. System Architecture

### 2.1 Technology Stack
- **Language:** Python 3.9+
- **CLI Framework:** Typer
- **UI/Logging:** Rich (TUI for progress bars, panels)
- **State Management:** Python Class-based State Machine

### 2.2 Directory Structure
```text
/naoko/
├── .naoko_env                 # Environment variables (API Keys, Git Config)
├── docs/                      # Input Planning Documents (PDF, XLSX, PPTX, MD)
├── artifacts/                 # Intermediate Artifacts
│   ├── requirements_request.md # Parsed & Analyzed Requirements
│   ├── patch.diff             # Codex Implementation (Git Diff)
│   ├── review.md              # Gemini Code Review
│   ├── review_judgement.md    # Codex Judgement (Suitability/Hold/Unnecessary)
│   └── summary.md             # Final Summary & Commit Message
├── naoko_core/                # System Logic
│   ├── main.py                # Entry Point (CLI)
│   ├── orchestrator.py        # Core Workflow Loop (State Machine)
│   ├── state.py               # State Definitions
│   ├── agents/                # Agent Wrappers
│   │   ├── gemini_client.py   # Wrapper for Gemini CLI
│   │   └── codex_client.py    # Wrapper for Codex CLI
│   └── io/                    # I/O Utilities
│       ├── doc_parser.py      # Document Parsing Logic
│       └── git_ops.py         # Git Command Execution
└── requirements.txt           # Python Dependencies
```

## 3. Workflow Specification

### Phase 1: Planning
1. **Input:** User provides a document path via CLI.
2. **Action:** `Gemini Agent` parses the document.
3. **Output:** `artifacts/requirements_request.md` is generated.

### Phase 2: Implementation
1. **Input:** `requirements_request.md` + Target Endpoint (optional).
2. **Action:** `Codex Agent` generates code and applies it via Git.
3. **Output:** `git apply` executed, `artifacts/patch.diff` saved.

### Phase 3: Review Loop (Max 5 Rounds)
1. **Review (Gemini):** Analyzes `patch.diff` vs `requirements_request.md`. Outputs `artifacts/review.md`.
2. **Judgment (Codex):** Analyzes `review.md`. Outputs `artifacts/review_judgement.md`.
    - **Valid (Suitability):** Fix code -> `git apply` -> Loop continues.
    - **Hold:** Pauses for user confirmation.
    - **Unnecessary:** Skips fix -> Loop continues.
3. **Validation (Gemini):** Verifies the new patch.

### Phase 4: Completion
- If all checks pass or user force-approves:
- Generate `artifacts/summary.md`.
- Output Final Commit Message.

## 4. CLI Specification
```bash
# Start the process
python -m naoko_core.main start ./docs/my_plan.pdf

# Options
--max-rounds [int] : Default 5
--dry-run          : Simulate without running agents
```
