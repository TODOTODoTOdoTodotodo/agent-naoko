---
name: naoko
description: Run the Naoko end-to-end workflow (planning document -> Gemini analysis/review -> Codex implementation -> review loop) when the user wants to auto-run from a prepared planning document or explicitly invokes the naoko skill.
metadata:
  short-description: Run Naoko from planning doc to implementation
---

# Naoko Skill

## When to use

Trigger this skill when the user wants to:
- start Naoko with a prepared planning document
- auto-run the full workflow without manual steps

Implicit trigger examples (non-exhaustive):
- "기획서가 준비되었으니 오토 돌려줘"
- "기획서 준비됐어, 자동으로 돌려줘"
- "기획서로 끝까지 자동 실행해줘"
- "기획서 기반으로 바로 개발 진행해줘"
- "기획서 넣었으니 나코 돌려줘"

Direct trigger example:
- "naoko 실행해줘" / "naoko skill 사용해줘"

## Scope

Full Naoko run: document parsing -> requirements generation -> implementation -> review loop -> completion. Use the current working directory as the project root (default).

## References (load only if needed)

- Read the project overview and CLI usage in `README.md`.
- Read workflow and artifacts in `DESIGN.md`.

## Inputs to confirm

Ask for or infer:
- Planning document path (PDF/PPTX/XLSX/MD)
- Optional entry point (if existing project: controller or starting file)
- Whether to run with `--dry-run`
- Max review rounds (default: 5)

## Execution

Preferred command:
```bash
naoko start <DOC_PATH> [--entry-point <PATH>] [--max-rounds N] [--dry-run]
```

Fallback command (module run):
```bash
python -m naoko_core.main start <DOC_PATH> --max-rounds 5
```

## Artifacts to expect

- `artifacts/requirements_request.md`
- `artifacts/patch.diff`
- `artifacts/review.md`
- `artifacts/review_judgement.md`

## Behavior notes

- For unsupported formats in DocParser, treat parsing as empty string and stop before implementation.
- If CLI tools are missing, surface the error and stop (do not silently proceed).
