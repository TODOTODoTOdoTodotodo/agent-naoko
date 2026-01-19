![Naoko](magi.jpg)

# Naoko: 듀얼 에이전트 AI 아키텍트 시스템

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Status](https://img.shields.io/badge/Status-Beta-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

**Naoko**는 전문적인 소프트웨어 엔지니어링 워크플로우를 시뮬레이션하기 위해 설계된 자동화 코딩 오케스트레이션 시스템입니다. 두 개의 특화된 AI 에이전트가 엄격한 협업 루프에서 동작하며, 코드 품질과 요구사항 준수를 보장합니다.

## 🧠 핵심 철학

Naoko는 "사고(기획/리뷰)"와 "실행(코딩)"을 분리하여, LLM이 요구사항을 환각하거나 검증되지 않은 코드를 작성하는 문제를 방지합니다.

- **Gemini 에이전트(아키텍트):** 기획 문서(PDF, PPTX, XLSX)를 읽고 요구사항을 추출하며, 기존 코드의 스타일을 분석하고 엄격한 코드 리뷰를 수행합니다.
- **Codex 에이전트(개발자):** 요구사항 및 스타일 가이드를 바탕으로 코드를 구현(Overwrite 전략)하고, 리뷰 피드백에 따라 반복 수정합니다.

## 🔄 워크플로우

1.  **기획 및 분석 단계:**
    - 입력: 기획 문서(PDF, MD, Excel) 및 시작점(Controller).
    - 분석: 기존 프로젝트인 경우, 시작점과 연관된 파일을 분석하여 `CODING_STYLE.md` 생성.
    - 출력: 구조화된 `requirements_request.md`.
2.  **구현 단계:**
    - 동작: Codex 에이전트가 코드를 생성하고 파일을 직접 업데이트(Overwrite)합니다.
    - 기록: 변경 사항은 `artifacts/patch.diff`에 기록됩니다.
3.  **리뷰 루프(반복 개선):**
    - **리뷰:** Gemini가 요구사항 및 현재 코드 전체를 비교 분석합니다.
    - **판단:** Codex가 리뷰를 판정(Suitable/Changes Needed/Hold/Unnecessary)합니다.
    - **반복:** 최대 5회까지 반복하며 `SUITABLE` 판정 시 종료합니다.
4.  **완료:**
    - 신규 프로젝트인 경우 요약 메시지로 Git 커밋을 자동 생성합니다.
    - 기존 프로젝트인 경우 `git apply` 상태로 유지하여 사용자가 최종 검토하게 합니다.

## 🚀 시작하기

### 설치

저장소를 클론한 후, 프로젝트 루트에서 패키지를 설치하여 `naoko` 명령어를 활성화합니다.

```bash
git clone https://github.com/TODOTODoTOdoTodotodo/agent-naoko.git
cd agent-naoko
pip install .
```

### 인증 설정 (최초 1회)

`naoko` 명령어를 처음 실행하면 인증 방식을 묻는 프롬프트가 나타납니다.
- **API Key:** Google AI Studio에서 발급받은 키를 입력합니다.
- **OAuth Login:** Google Cloud OAuth 클라이언트 정보를 입력하고 브라우저 로그인을 진행합니다.
- 설정 파일은 `~/.naoko/` 폴더에 안전하게 저장되어 어떤 경로에서든 공유됩니다.

## 💻 사용 방법

### 1. 신규 프로젝트 시작
```bash
naoko start ./docs/my_plan.md
```

### 2. 기존 프로젝트에 기능 추가 (스타일 유지)
기존 프로젝트 폴더로 이동한 뒤 실행합니다. 시작점(`--entry-point`)을 지정하면 주변 코드를 분석하여 일관된 스타일로 개발을 진행합니다.

```bash
cd ~/my-existing-project
naoko start ./docs/feature_req.pdf --entry-point src/main/java/com/example/UserController.java
```

### 주요 옵션
- `--max-rounds [N]`: 리뷰 루프 횟수 제한 (기본 5회).
- `--dry-run`: 실제 파일 수정이나 Git 반영 없이 흐름만 확인.
- `--entry-point [PATH]`: 스타일 분석 기준이 될 소스 파일 경로.

## 📂 프로젝트 구조

```text
/naoko
├── artifacts/              # 중간 산출물(요구사항, 패치, 리뷰)
├── docs/                   # 기획 문서를 두는 곳 (보안 패턴 적용됨)
├── naoko_core/             # 시스템 소스 코드
│   ├── agents/             # Gemini/Codex CLI 래퍼
│   ├── io/                 # Git 작업, 문서 파서, 코드 네비게이터
│   └── orchestrator.py     # 메인 워크플로우 상태 머신
└── pyproject.toml          # CLI 패키지 설정
```

## ⚠️ 현재 상태 (v0.2.0)

- **LLM 연동:** Gemini 3(CLI Proxy) 및 Codex API 연동 완료.
- **코드 스타일 분석:** 기존 프로젝트 분석 및 `CODING_STYLE.md` 기반 개발 지원.
- **안정성:** STDIN 파이프 방식 도입으로 대용량 컨텍스트 처리 지원 및 Overwrite 전략으로 패치 오류 해결.

## 🤝 기여 방법

1. 프로젝트 Fork
2. 기능 브랜치 생성 (`git checkout -b feat/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 브랜치 푸시 (`git push origin master`)
5. Pull Request 생성