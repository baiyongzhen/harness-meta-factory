# harness-meta-factory

AI 코딩 도구(Claude Code / Cursor / Gemini CLI / Codex)에 맞는
에이전트·스킬·훅·룰을 **자동 설계·생성·검증**하는 메타 스킬 팩토리.

```
프롬프트 한 줄 → harness 스킬 → 하네스 파일 세트 → Docker 검증 → 즉시 사용
```

---

## 목차

1. [리포 구조](#1-리포-구조)
2. [harness 스킬이란](#2-harness-스킬이란)
3. [스킬 설치](#3-스킬-설치)
4. [하네스 생성 — 플랫폼별 사용법](#4-하네스-생성--플랫폼별-사용법)
5. [생성된 하네스 구조 이해](#5-생성된-하네스-구조-이해)
6. [Docker 검증 환경 설정](#6-docker-검증-환경-설정)
7. [하네스 검증 실행](#7-하네스-검증-실행)
8. [tests/ 임시 하네스 워크플로우](#8-tests-임시-하네스-워크플로우)
9. [레퍼런스](#9-레퍼런스)

---

## 1. 리포 구조

```
harness-meta-factory/
│
├── skills/
│   └── harness/                    ← 핵심: 하네스 생성 메타 스킬
│       ├── SKILL.md                    (스킬 본문 — Phase 0~7 워크플로우)
│       └── references/                 (16개 참조 문서)
│           ├── platform-paths.md           플랫폼별 파일 경로 정의
│           ├── platform-orchestration.md   오케스트레이션 API 패턴
│           ├── platform-components.md      플랫폼별 구성 요소 + SubAgent 안티패턴
│           ├── platform-hooks.md           훅 이벤트·가드레일·컨텍스트 주입 예시
│           ├── platform-rules.md           Rules 설계 (CLAUDE.md/AGENTS.md/.mdc)
│           ├── platform-commands.md        Slash Commands + Gemini !{shell} 패턴
│           ├── platform-plugin.md          Plugin/Extension 패키징·배포
│           ├── platform-learning.md        Continuous Learning 설계
│           ├── component-templates.md      agents/skills/hooks 템플릿
│           ├── agent-design-patterns.md    6가지 아키텍처 패턴
│           ├── orchestrator-template.md    Claude 오케스트레이터 템플릿
│           ├── skill-writing-guide.md      스킬 작성 가이드 (Scripts §10 포함)
│           ├── skill-testing-guide.md      스킬 테스트 방법론
│           ├── qa-agent-guide.md           QA 에이전트 설계 가이드
│           ├── team-examples.md            팀 구성 예시 6가지
│           └── continuous-learning-templates.md  학습 스크립트 템플릿
│
├── scripts/
│   └── validate-harness.py         ← Docker 검증 파이프라인
│
├── tests/                          ← 임시 하네스 검증 공간
│   └── {harness-name}/                 (생성된 하네스를 여기서 먼저 검증)
│
├── Dockerfile                      ← 검증 환경 이미지
├── docker-compose.yaml             ← 검증 서비스 정의
├── requirements.txt                ← Python 검증 도구
├── .env.example                    ← LLM API 키 템플릿
└── GUIDE.md                        ← 상세 사용 가이드 (eval 도구별)
```

---

## 2. harness 스킬이란

`skills/harness/SKILL.md`는 AI 에이전트가 읽고 따르는 **메타 스킬**입니다.
이 스킬을 설치한 AI 도구에 "하네스 구성해줘"라고 요청하면,
Phase 0(감사) → Phase 6(검증)까지 자동으로 실행하여 하네스 파일 세트를 생성합니다.

### 생성 가능한 하네스 구성 요소

| 구성 요소 | Claude Code | Cursor | Gemini CLI | Codex |
|----------|-------------|--------|------------|-------|
| **에이전트** | `.claude/agents/*.md` | `.cursor/agents/*.md` | `.gemini/skills/*/SKILL.md` (skill role) | `.codex/agents/*.toml` |
| **스킬** | `.claude/skills/*/SKILL.md` | `.cursor/skills/*/SKILL.md` | `.gemini/skills/*/SKILL.md` | `.agents/skills/*/SKILL.md` |
| **훅** | `.claude/hooks/hooks.json` | `.cursor/hooks.json` | `.gemini/settings.json` | `.codex/hooks.json` |
| **룰** | `CLAUDE.md` | `.cursor/rules/*.mdc` + `AGENTS.md` | `GEMINI.md` | `AGENTS.md` / `AGENTS.override.md` |
| **Commands** | `.claude/commands/*.md` | `.cursor/commands/*.md` | `.gemini/commands/*.toml` | `.codex/commands/*.md` |
| **Plugin** | `.claude-plugin/plugin.json` | `package.json` (npm) | `manifest.json` | `.codex-plugin/plugin.json` |
| **Handoff** | `_workspace/` | `artifacts/` | `artifacts/` | `artifacts/` |

### 지원 아키텍처 패턴

- **파이프라인** — 순차 의존 작업 (A → B → C)
- **팬아웃/팬인** — 병렬 독립 작업 후 통합
- **전문가 풀** — 상황별 에이전트 선택 호출
- **생성-검증** — 생성 후 품질 검수
- **감독자** — 중앙 에이전트가 동적 분배
- **계층적 위임** — 상위 → 하위 재귀 위임

---

## 3. 스킬 설치

`skills/harness/` 디렉터리를 사용 중인 AI 도구의 **스킬 경로**에 복사합니다.

### Claude Code

```bash
# 글로벌 스킬 (모든 프로젝트에서 사용)
cp -r skills/harness ~/.claude/skills/harness

# 또는 프로젝트 로컬
cp -r skills/harness {your-project}/.claude/skills/harness
```

### Cursor

```bash
# 글로벌 스킬 (Cursor 설정 경로)
cp -r skills/harness ~/.cursor/skills/harness

# 또는 프로젝트 로컬
cp -r skills/harness {your-project}/.cursor/skills/harness
```

> Cursor는 `.cursor/skills/` 우선 탐색 후 `~/.cursor/skills/`를 탐색합니다.

### Gemini CLI

```bash
cp -r skills/harness ~/.gemini/skills/harness
```

### Codex

```bash
cp -r skills/harness {your-project}/.agents/skills/harness
```

---

## 4. 하네스 생성 — 플랫폼별 사용법

스킬 설치 후, AI 도구에 다음과 같이 요청합니다.

### 기본 프롬프트 구조

```
{도메인 설명} + {플랫폼 명시} + 하네스를 구성해주세요
```

### Claude Code 하네스 생성

```
FastAPI async REST API 프로젝트에 맞는
Claude Code 하네스를 구성해주세요.
```

생성 위치:
```
your-project/
├── CLAUDE.md
├── _workspace/
└── .claude/
    ├── agents/       ← 에이전트 팀
    ├── skills/       ← 오케스트레이터 + 도메인 스킬
    └── hooks/hooks.json
```

### Cursor 하네스 생성

```
FastAPI async + SQLAlchemy 2 REST API.
로컬 JWT와 Keycloak OIDC 이중 인증을 지원하는
Cursor 하네스를 구성해주세요.
```

생성 위치:
```
your-project/
├── AGENTS.md
├── artifacts/
└── .cursor/
    ├── agents/       ← 에이전트 팀
    ├── skills/       ← 오케스트레이터 + 도메인 스킬
    ├── rules/        ← 프로젝트 코딩 룰 (.mdc)
    ├── hooks.json
    └── hooks/check-doc-sync.sh   ← 필수 훅
```

### Gemini CLI 하네스 생성

```
소설 작성 파이프라인(리서치 → 집필 → 편집)에 맞는
Gemini CLI 하네스를 구성해주세요.
```

생성 위치:
```
your-project/
├── GEMINI.md
├── artifacts/
└── .gemini/
    ├── skills/       ← 오케스트레이터 + 도메인 스킬
    ├── commands/     ← !{shell} 동적 주입 Commands (선택)
    └── settings.json
```

### Codex 하네스 생성

```
TypeScript + Next.js 풀스택 앱을 위한
Codex 하네스를 구성해주세요.
```

생성 위치:
```
your-project/
├── AGENTS.md
├── artifacts/
├── .agents/skills/   ← 공통 스킬
└── .codex/
    ├── agents/       ← 에이전트 팀 (.toml)
    ├── config.toml
    └── hooks.json
```

### 멀티플랫폼 하네스 생성

```
Django REST Framework + Celery 비동기 작업 시스템을 위한
Claude Code와 Cursor 모두에서 사용할 수 있는
하네스를 구성해주세요.
```

공통 스킬은 `.agents/skills/`에 1회 생성,
플랫폼별 agents/hooks/rules만 분리 생성됩니다.

### Continuous Learning 포함

```
Rust CLI 도구 개발 하네스를 구성해주세요.
학습 기능(continuous learning)도 포함해주세요.
```

추가 생성: `observe.py`, `instinct-cli.py`, `compact-suggest.py` + 플랫폼별 훅 등록.

---

## 5. 생성된 하네스 구조 이해

### 청사진 승인 게이트

스킬은 파일을 바로 생성하지 않고 **청사진**을 먼저 제시합니다.

```
[청사진 예시]
플랫폼: Cursor
패턴: Pipeline (Auth → DB → API → QA → Docs)

에이전트:
  - auth-agent    : JWT + Keycloak OIDC 인증
  - db-agent      : SQLAlchemy 2 async 모델
  - api-builder   : FastAPI 라우터
  - qa-agent      : pytest-asyncio 테스트
  - doc-writer    : AGENTS.md 동기화 (필수)

스킬:
  - fastapi-auth-orchestrator  (오케스트레이터)
  - auth-handler               (JWT + Keycloak 패턴)
  - db-schema                  (SQLAlchemy 2 패턴)
  - api-builder                (FastAPI 패턴)
  - sync-docs                  (문서 동기화 — 필수)

이 구조로 만들어드릴까요?
```

승인 후 파일이 생성됩니다.

### 필수 포함 요소

모든 하네스에는 다음이 **반드시** 포함됩니다:

| 요소 | 역할 |
|------|------|
| `doc-writer` agent | entry file(CLAUDE.md/AGENTS.md) 동기화 |
| `sync-docs` skill | 코드와 문서 일치 유지 |
| 오케스트레이터 skill | 전체 파이프라인 조율 |

---

## 6. Docker 검증 환경 설정

### 사전 요구사항

```
□ Docker Desktop (또는 Docker Engine) 실행 중
□ docker compose v2 사용 가능
□ (선택) Ollama 로컬 실행 — API 키 없이 SkillOpt 평가 시
```

### 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 편집:

```dotenv
# LLM API (선택 — 하나만 있으면 됨)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# 로컬 Ollama (Docker Desktop 기본값 — 변경 불필요)
OLLAMA_HOST=http://host.docker.internal:11434
```

### 이미지 빌드

```bash
docker compose build
```

> 최초 빌드 시 약 5~10분 소요됩니다 (Go 1.25, Node 20, 11개 OSS eval 저장소 clone).

빌드된 이미지에 포함된 도구:

| 도구 | 용도 |
|------|------|
| `skillgrade` | SKILL.md 품질 채점 (Node.js) |
| `sanity` | frontmatter 정합성 검사 (Go) |
| `SkillOpt` | LLM 기반 스킬 품질 평가 |
| `SkillsBench` | 스킬 벤치마크 |
| `SWE-agent` | 코딩 에이전트 평가 |
| `hal-harness` | LLM 에이전트 HAL 평가 |
| `agentevals` | 범용 에이전트 궤적 평가 |
| `tau-bench` | Tool-augmented LLM 평가 |

---

## 7. 하네스 검증 실행

### 빠른 검증

```bash
# 환경 상태 확인 (필수 첫 단계)
docker compose run --rm harness-eval harness-eval-verify

# 기본 검증 (레포 전체 스킬 검증)
docker compose run --rm harness-validate

# tests/ 임시 하네스 검증
docker compose run --rm harness-test-validate
```

### 검증 단계별 설명

`validate-harness.py`가 자동으로 수행하는 5단계:

```
Step 0: 환경 검증     — Python/Node/Go/uv/skillgrade/sanity 설치 확인
Step 1: frontmatter   — 모든 SKILL.md의 name/description 필드 검사
Step 2: skillgrade    — 스킬 품질 점수 산출 (0~100)
Step 3: 구조 검증     — 플랫폼별 필수 파일 존재 확인
Step 4: pytest        — Python 스크립트 단위 테스트 (tests/ 있을 때)
```

### 검증 옵션

```bash
# 특정 tests/ 폴더 검증
TEST_TARGET=tests/my-harness docker compose run --rm harness-test-validate

# 특정 플랫폼만 검증
TEST_PLATFORM=cursor docker compose run --rm harness-test-validate

# SkillOpt LLM 품질 평가 (Ollama 실행 중일 때)
SKILLOPT_ENABLED=true SKILLOPT_MODEL=llama3.2 \
  docker compose run --rm harness-test-validate

# 인터랙티브 셸 (수동 탐색)
docker compose run --rm harness-eval bash
```

### 검증 결과 확인

검증 후 `eval-results/{timestamp}/` 에 결과가 저장됩니다:

```
eval-results/20260621-160303/
├── summary.json        ← PASS/FAIL/SKIP 요약
├── env-check.log       ← 환경 검증 로그
├── sanity.log          ← frontmatter 검사 결과
├── skillgrade-*.json   ← 스킬별 품질 점수
└── pytest.log          ← 테스트 결과 (있을 때)
```

`summary.json` 예시:

```json
{
  "timestamp": "20260621-163201",
  "pass": 12,
  "fail": 0,
  "skip": 1,
  "structure": {
    "cursor": { "pass": 5, "fail": 0 }
  }
}
```

---

## 8. tests/ 임시 하네스 워크플로우

실제 프로젝트에 적용하기 전에 `tests/` 폴더에서 먼저 검증하는 권장 흐름:

```
① AI 도구에 하네스 생성 요청
        ↓
② tests/{harness-name}/ 에 생성
        ↓
③ Docker로 구조 검증
   docker compose run --rm harness-test-validate
        ↓
④ PASS 확인 후 실제 프로젝트에 복사
        ↓
⑤ 실제 AI 도구에서 오케스트레이터 스킬 실행 테스트
```

### 예시: FastAPI 하네스 검증

```bash
# 1. AI 도구에 요청
# "FastAPI async + SQLAlchemy 2 REST API.
#  로컬 JWT + Keycloak 이중 인증 Cursor 하네스를
#  tests/fastapi-jwt-keycloak-cursor/ 에 생성해주세요"

# 2. Docker 검증
docker compose run --rm harness-test-validate
# → PASS=12 / FAIL=0 확인

# 3. 실제 프로젝트에 복사
cp -r tests/fastapi-jwt-keycloak-cursor/.cursor/ your-project/.cursor/
cp tests/fastapi-jwt-keycloak-cursor/AGENTS.md   your-project/AGENTS.md
```

### 다른 플랫폼 검증

```bash
# Claude Code 하네스
TEST_TARGET=tests/my-claude-harness \
TEST_PLATFORM=claude \
  docker compose run --rm harness-test-validate

# Gemini CLI 하네스
TEST_TARGET=tests/my-gemini-harness \
TEST_PLATFORM=gemini \
  docker compose run --rm harness-test-validate

# 멀티플랫폼 (all)
TEST_TARGET=tests/my-multi-harness \
TEST_PLATFORM=all \
  docker compose run --rm harness-test-validate
```

---

## 9. 레퍼런스

### 주요 문서

| 문서 | 내용 |
|------|------|
| [`GUIDE.md`](GUIDE.md) | Docker 검증 환경 상세 사용 가이드 (eval 도구별 절차) |
| [`skills/harness/SKILL.md`](skills/harness/SKILL.md) | harness 스킬 본문 (Phase 0~7 워크플로우) |

### 플랫폼 참조 문서

| 문서 | 내용 |
|------|------|
| [`references/platform-paths.md`](skills/harness/references/platform-paths.md) | 플랫폼별 파일 경로 정의 |
| [`references/platform-orchestration.md`](skills/harness/references/platform-orchestration.md) | 오케스트레이션 API 패턴 |
| [`references/platform-components.md`](skills/harness/references/platform-components.md) | 플랫폼별 구성 요소 + SubAgent 안티패턴 |
| [`references/platform-hooks.md`](skills/harness/references/platform-hooks.md) | 훅 이벤트·가드레일·컨텍스트 주입 예시 |
| [`references/platform-rules.md`](skills/harness/references/platform-rules.md) | Rules 설계 (CLAUDE.md / AGENTS.md / .mdc) |
| [`references/platform-commands.md`](skills/harness/references/platform-commands.md) | Slash Commands + Gemini `!{shell}` 패턴 |
| [`references/platform-plugin.md`](skills/harness/references/platform-plugin.md) | Plugin / Extension 패키징·배포 |
| [`references/platform-learning.md`](skills/harness/references/platform-learning.md) | Continuous Learning 설계 |

### 설계·작성 참조 문서

| 문서 | 내용 |
|------|------|
| [`references/agent-design-patterns.md`](skills/harness/references/agent-design-patterns.md) | 6가지 아키텍처 패턴 |
| [`references/component-templates.md`](skills/harness/references/component-templates.md) | 에이전트·스킬·훅 파일 템플릿 |
| [`references/orchestrator-template.md`](skills/harness/references/orchestrator-template.md) | Claude 오케스트레이터 템플릿 |
| [`references/team-examples.md`](skills/harness/references/team-examples.md) | 팀 구성 예시 6가지 |
| [`references/skill-writing-guide.md`](skills/harness/references/skill-writing-guide.md) | 스킬 작성 가이드 (Scripts §10 포함) |
| [`references/skill-testing-guide.md`](skills/harness/references/skill-testing-guide.md) | 스킬 테스트 방법론 |
| [`references/qa-agent-guide.md`](skills/harness/references/qa-agent-guide.md) | QA 에이전트 설계 가이드 |
| [`references/continuous-learning-templates.md`](skills/harness/references/continuous-learning-templates.md) | Continuous Learning 스크립트 템플릿 |

### 검증 도구 링크

- [skillgrade](https://www.npmjs.com/package/skillgrade) — 스킬 품질 채점
- [SanityHarness](https://github.com/lemon07r/SanityHarness) — 정합성 검증
- [SkillOpt](https://github.com/microsoft/SkillOpt) — LLM 기반 스킬 최적화
- [SkillsBench](https://github.com/benchflow-ai/skillsbench) — 스킬 벤치마크
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) — 코딩 에이전트 평가
- [hal-harness](https://github.com/princeton-pli/hal-harness) — HAL 에이전트 평가
- [agentevals](https://github.com/langchain-ai/agentevals) — 에이전트 궤적 평가
