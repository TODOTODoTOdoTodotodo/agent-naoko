# Naoko Architect System 개발 이력 (History)

이 문서는 Naoko 시스템의 초기 설계부터 현재(v0.2.0)까지의 주요 개발 마일스톤과 기술적 결정 사항을 기록합니다.

---

## 📅 2026-01-16: 시스템 초기 설계 및 골격 구축 (v0.1.0)

### 1. Dual-Agent 아키텍처 수립
- **Gemini (아키텍트/리뷰어):** 기획 분석 및 코드 품질 검증 담당.
- **Codex (개발자):** 실제 코드 구현 및 수정 담당.
- **Orchestrator:** 두 에이전트 간의 5회 핑퐁 루프 및 상태 머신 제어.

### 2. 기술 스택 확정
- **Language:** Python 3.9+
- **CLI Framework:** Typer & Rich (TUI 제공)
- **Git Operations:** `subprocess` 기반 `git apply` 및 `commit` 로직 구현.

### 3. 핵심 기능 구현
- **문서 파서 (DocParser):** PDF, PPTX, XLSX, MD 파일에서 텍스트 추출 기능 구현 (`python-pptx`, `pypdf`, `pandas` 활용).
- **인증 매니저 (AuthManager):** 초기 API Key 및 OAuth 2.0 기반 인증 구조 설계.

---

## 📅 2026-01-16 (오후): 안정성 강화 및 실전 연동 (v0.2.0)

### 1. 패치 전략 수정: Overwrite 전략 도입
- **문제:** `git apply`가 컨텍스트 불일치로 인해 빈번하게 실패하는 현상 발견.
- **해결:** LLM에게 `Full Code`를 요청하고, 로컬에서 `difflib`로 Diff를 생성하되, 실제 파일 반영은 **강제 덮어쓰기(Overwrite)** 방식으로 변경하여 안정성 100% 확보.

### 2. Google One 구독 활용: CLI Proxy 모드 전환
- **아이디어:** `googleapis` 직접 호출 대신 로컬에 설치된 `gemini` CLI를 호출하도록 변경.
- **장점:** 사용자가 이미 로그인된 Google One(Gemini Advanced) 환경과 인증 정보를 그대로 활용 가능.
- **개선:** OS 인자 길이 제한을 방지하기 위해 **STDIN(표준 입력) 파이프** 방식으로 프롬프트 전달.

### 3. 기존 프로젝트 지원 (Legacy Support)
- **Code Navigator:** 특정 엔드포인트(Controller) 지정 시 연동된 Service, DTO 등을 자동 탐색.
- **Style 분석:** 기존 코드를 분석하여 `CODING_STYLE.md`를 자동 생성하고, 신규 코드 생성 시 이를 참조하여 일관성 유지.
- **안전장치:** 기존 프로젝트 모드에서는 자동 커밋을 스킵하고 `git apply` 상태만 유지.

### 4. 사용자 경험(UX) 최적화
- **Global CLI:** `pyproject.toml` 설정을 통해 `pipx`로 설치 시 어디서나 `naoko` 명령어로 실행 가능하도록 래핑.
- **Single Command:** `naoko start`와 같은 서브커맨드 구조에서 발생하는 인자 오류를 방지하기 위해 `naoko [PATH]` 단일 명령 구조로 단순화.
- **설정 공용화:** 인증 및 설정 파일을 `~/.naoko/` 폴더에 저장하여 프로젝트 간 세션 공유.

---

## 🛠️ 주요 이슈 해결 기록 (Debug Log)

- **Syntax Error:** 정규식 처리 및 문자열 종료 미비 이슈 수정.
- **Quota Exceeded (429):** API Key 방식에서 발생하던 할당량 문제를 CLI Proxy 모드로 전환하며 해결.
- **Invalid Patch:** `git apply` 실패 이슈를 파일 직접 쓰기 방식으로 우회하여 해결.
- **Auth Sync:** 기존 프로젝트 기능 추가 시 발생했던 코드 롤백 이슈를 최종 통합 버전으로 복구.

---

## 🚀 향후 과제
- Claude MCP(Model Context Protocol) 연동을 통한 Claude Skill 등록.
- 다양한 프레임워크(Spring Boot 외)에 대한 스타일 분석 정교화.
- 다중 파일 동시 수정 로직 강화.
