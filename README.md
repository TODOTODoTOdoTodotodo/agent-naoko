# Naoko: Dual-Agent AI Architect System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Status](https://img.shields.io/badge/Status-Alpha-orange)
![License](https://img.shields.io/badge/License-MIT-green)

**Naoko** is an automated coding orchestration system designed to simulate a professional software engineering workflow. It leverages two specialized AI agents working in a strict collaborative loop to ensure code quality and adherence to requirements.

## 🧠 Core Philosophy

Naoko separates the "thinking" (Planning & Review) from the "doing" (Coding), preventing the common pitfall of LLMs hallucinating requirements or writing unverified code.

- **Gemini Agent (The Architect):** Reads raw planning documents (PDF, PPTX, XLSX), extracts requirements, and performs strict code reviews.
- **Codex Agent (The Developer):** Implements code based on requirements, applies patches via Git, and iteratively fixes bugs based on review feedback.

## 🔄 Workflow

The system operates on a State Machine designed for stability:

1.  **Planning Phase:**
    - Input: Planning documents (PDF, MD, Excel).
    - Output: Structured `development_request.md`.
2.  **Implementation Phase:**
    - Action: Codex Agent generates code and creates a `patch.diff`.
    - Validation: System validates the patch format (Unified Diff) and applies it.
3.  **Review Loop (Iterative Refinement):**
    - **Review:** Gemini analyses the diff against original requirements.
    - **Refine:** Codex judges the review (Suitable/Changes Needed/Hold/Unnecessary).
    - **Loop:** Repeats up to 5 times until the code is deemed `SUITABLE`.
4.  **Completion:**
    - Automated Git Commit with a summarized message.

## 📂 Project Structure

```text
/naoko
├── artifacts/              # Intermediate outputs (Generated Specs, Patches, Reviews)
├── docs/                   # Place your planning documents here
├── naoko_core/             # System Source Code
│   ├── agents/             # Gemini & Codex Client Wrappers
│   ├── io/                 # Git Operations & File I/O
│   └── orchestrator.py     # Main Workflow State Machine
├── requirements.txt        # Python Dependencies
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Git installed and configured

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/TODOTODoTOdoTodotodo/agent-naoko.git
   cd agent-naoko
   ```

2. Set up a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

Run the system pointing to a planning document:

```bash
# Run with the sample plan
python -m naoko_core.main docs/sample_project_plan.md

# Options
# --max-rounds 3   : Limit review loops to 3 (Default: 5)
# --dry-run        : Simulate without applying git patches
```

## ⚠️ Current Status (v0.1.0)

This project is in **Initial Prototype** stage.
- **Core Orchestrator:** Implemented & Verified.
- **Git Operations:** Implemented (Unified Diff validation).
- **Agent Logic:** Currently runs with simulation logic (Dummy Responses) for architectural verification. Actual LLM API integration is the next step.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feat/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feat/AmazingFeature`)
5. Open a Pull Request
