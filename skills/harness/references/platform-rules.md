# 플랫폼별 Rules 설계 가이드

> 에이전트 컨텍스트에 항상(또는 조건부로) 주입되는 영구 지시 레이어. 코딩 컨벤션·아키텍처·보안 가드레일 자동 적용.

## Rules vs Skill 구분

| 구분 | Rules (CLAUDE.md / .mdc / AGENTS.md) | Skill |
|------|---------------------------------------|-------|
| 로드 시점 | 항상 / 패턴 매칭 / AI 관련성 판단 | 트리거 시에만 |
| 내용 | 사실·규칙·금지 사항 | 절차·워크플로·다단계 작업 |
| 컨텍스트 비용 | 지속 소비 (alwaysApply 시) | Progressive Disclosure |
| 적합 | "항상 지켜라" | "이 작업할 때만 따라라" |

**하네스 Entry file 원칙:** 에이전트/스킬 목록·디렉터리 트리 **금지** — 트리거 규칙 + 변경 이력만 기록.

---

## 플랫폼별 위치 및 형식

| 플랫폼 | 공식 이름 | 저장 위치 | 형식 |
|--------|-----------|-----------|------|
| **Cursor** | **Rules** | `.cursor/rules/*.mdc` | MDC (YAML frontmatter + Markdown) |
| Claude Code | **CLAUDE.md** | `CLAUDE.md`, `~/.claude/CLAUDE.md` | Markdown (계층 병합) |
| Gemini CLI | **Project context** | `GEMINI.md`, 중첩 `GEMINI.md` | Markdown (계층 병합) |
| Codex | **AGENTS.md** | `AGENTS.md`, `AGENTS.override.md`, `~/.codex/AGENTS.md` | Markdown (CWD → root) |

---

## Cursor — Rules (.cursor/rules/*.mdc)

### 4가지 적용 방식

| 방식 | frontmatter | 동작 | 권장 여부 |
|------|-------------|------|----------|
| **Always** | `alwaysApply: true` | 모든 세션 항상 포함 | 전역 코딩 규칙 |
| **Glob** | `globs: ["**/*.py"]` | 파일 패턴 매칭 시만 | 언어·레이어별 규칙 |
| **Intelligent** | `description:` 만 (나머지 없음) | AI가 관련성 판단 | **Skill 이전 권장** |
| **Manual** | 없음 | `@rule-name` 멘션 시만 | 선택적 참조 |

**Intelligent Rule → Skill 이전:** `alwaysApply: false` + `globs` 없는 규칙은 `/migrate-to-skills` 로 변환 권장 (Cursor 2.4+).

### 예시: alwaysApply + Glob 조합

```markdown
---
description: FastAPI 프로젝트 전반 규칙
globs: ["**/*.py"]
alwaysApply: true
---

# Project Rules
- Layer: endpoint → service → DB (엔드포인트에서 직접 DB 쿼리 금지)
- 응답: `PydanticSchema.model_validate(orm_obj)`
- 로깅: `structlog.get_logger(__name__)`, `print()` 금지
```

### 예시: 보안 가드레일 (Always)

```markdown
---
description: 보안 가드레일
alwaysApply: true
---

# Security Guardrails
## 절대 금지 셸 명령
rm -rf /, git push --force, git reset --hard, eval, curl|sh
## 코드 금지
SECRET_KEY = "hardcoded"   # 환경 변수만
f"SELECT * FROM {user_input}"  # 파라미터 바인딩 사용
```

> **이중 방어:** 보안 규칙은 Rules(`alwaysApply`) + Hooks(`guard-shell.sh`) 양쪽에 적용.

---

## Claude Code — CLAUDE.md

### 계층 구조

```
monorepo/
├── CLAUDE.md              # 공통: 커밋 규칙, 브랜치 전략
├── packages/api/
│   └── CLAUDE.md          # API만: REST 규칙, OpenAPI
└── packages/web/
    └── CLAUDE.md          # 프론트만: a11y, 컴포넌트
```

- 하위 디렉터리 CLAUDE.md가 상위를 **상속 후 덮어씀**
- `~/.claude/CLAUDE.md` — 전역 사용자 규칙

### CLAUDE.md vs Skill 분리 기준

| CLAUDE.md (Rules) | Skill |
|-------------------|-------|
| "서비스 레이어 경유 필수" | "새 도메인 7단계 절차" |
| "Conventional Commits" | `/commit` 워크플로 전체 |
| 기술 스택 한 줄 요약 | PDF 처리 상세 절차 + scripts |

**하네스 Entry file 예시 (CLAUDE.md):**

```markdown
## 하네스: {도메인명}

**목표:** {핵심 목표 한 줄}

**트리거:** {도메인} 작업 요청 시 `{orchestrator-skill}` 스킬 사용.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-06-01 | 초기 구성 | 전체 | - |
```

---

## Gemini CLI — GEMINI.md

### 계층 병합

```
project/
├── GEMINI.md            # 전체 프로젝트 규칙
└── pipelines/ingest/
    └── GEMINI.md        # 인제스트 레이어 전용 규칙 (상위에 추가 병합)
```

- `~/.gemini/GEMINI.md` — 사용자 전역
- GEMINI.md = 항상 알 것 / Skill = 작업 절차 (분리 원칙)

### 예시

```markdown
# Gemini Project Context

## Repository
- Python data pipeline, Dagster orchestration, PostgreSQL 16

## Conventions
- SQL은 `sql/` 디렉터리, Jinja 템플릿 사용
- 시크릿은 환경 변수만 — `.env` 커밋 금지

## 하네스: data-pipeline
**트리거:** 파이프라인/배포/DQ 작업 요청 시 `data-pipeline-orchestrator` 스킬 사용.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-06-01 | 초기 구성 | 전체 | - |
```

> ⚠️ Entry file 원칙(§ 상단)에 따라 GEMINI.md에 **스킬·에이전트 목록이나 디렉터리 경로를 나열하지 않는다.** 트리거 규칙 + 변경 이력만 둔다.

---

## Codex — AGENTS.md

### Discovery 순서

1. **Global:** `~/.codex/AGENTS.override.md` → 없으면 `~/.codex/AGENTS.md` (하나만)
2. **Project:** Git root → CWD까지 각 디렉터리 `AGENTS.override.md` → `AGENTS.md`
3. **병합:** root → CWD 순 concatenation (CWD = 나중 = **우선**)

### `AGENTS.override.md` 활용 (서브패키지 우선 적용)

```markdown
# Payments Service Override

- PCI: 카드 번호 로그 금지
- 이 디렉터리 변경 시 `payments-team` 리뷰어 태그 필수
```

CWD가 `services/payments/`이면 루트 AGENTS.md 뒤에 이 파일이 붙어 payments 규칙이 우선 적용.

### 예시 (하네스 포인터 포함)

```markdown
# Agent Guide

## Stack
FastAPI, async SQLAlchemy, JWT auth.

## Rules
- DB 접근은 반드시 서비스 레이어 경유
- `structlog` 사용, `print()` 금지

## Harness map
| Role | Path |
|------|------|
| Skills | `.agents/skills/` |
| Subagents | `.codex/agents/` |
| Rules (Cursor) | `.cursor/rules/` |
```

---

## 하네스 Rules 체크리스트

- [ ] Entry file(CLAUDE.md/AGENTS.md/GEMINI.md)은 **트리거 + 변경 이력만** (에이전트/스킬 목록 금지)
- [ ] Cursor: `alwaysApply: true` 전역 규칙 + `globs` 파일별 규칙 분리
- [ ] Intelligent Rule → skill 이전 여부 검토 (`alwaysApply: false` + `globs` 없는 경우)
- [ ] 보안 규칙은 Rules + Hooks **이중 적용** (Rules 단독으로 강제 실행 불가)
- [ ] 멀티플랫폼: 동일 프로젝트에서 CLAUDE.md + AGENTS.md 공존 가능 (내용 일치 권장)
