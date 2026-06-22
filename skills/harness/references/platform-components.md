# Platform Components — Rules, Hooks, Commands, Skill-Agent 연결

## Claude Code Settings (`.claude/settings.json`)

프로젝트 단위 Claude Code 동작을 제어한다. 하네스 구성 시 **에이전트 팀 또는 권한 제한이 필요하면 반드시 생성**한다.

### 설정 키

| 키 | 용도 | 하네스 생성 조건 |
|----|------|----------------|
| `env` | 세션 환경변수 주입 | 에이전트 팀 사용 시 필수 |
| `permissions.allow` | 허용할 도구·명령 패턴 | 도구 접근 제한 에이전트 포함 시 |
| `permissions.deny` | 차단할 도구·명령 패턴 | 위험 명령(rm -rf 등) 방지 가드레일 |
| `model` | 기본 모델 지정 | 프로젝트 전체 모델 고정 시 |

### 에이전트 팀 필수 설정

`TeamCreate` / `SendMessage` 를 사용하는 하네스는 반드시 이 설정을 포함해야 한다.
환경변수를 셸에서 직접 설정하면 세션마다 수동 설정이 필요하지만, `settings.json`에 기록하면 프로젝트를 열 때 자동 적용된다.

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

> ⚠️ `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 없이 `TeamCreate`를 호출하면 오류 발생.

### 권한 제어 패턴

```json
{
  "permissions": {
    "allow": [
      "Bash(git log:*)",
      "Bash(git diff:*)",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(curl:*)",
      "Bash(wget:*)"
    ]
  }
}
```

읽기 전용 탐색 에이전트(QA, 리서치)에 적합. `permissions`를 설정하면 해당 프로젝트에서 에이전트가 사용할 수 있는 도구가 제한된다.

### 범위 우선순위

| 범위 | 경로 | 우선순위 |
|------|------|----------|
| 사용자 전역 | `~/.claude/settings.json` | 낮음 |
| 프로젝트 | `.claude/settings.json` | 높음 (전역 덮어쓰기) |

> 시크릿(API 키 등)은 `settings.json`에 넣지 않는다. 환경변수나 `.env` 파일을 사용한다.

> 전체 템플릿: `references/component-templates.md` `.claude/settings.json`

---

## Rules (영구 지시)

| 플랫폼 | 위치 | 형식 |
|--------|------|------|
| Claude Code | `CLAUDE.md` | Markdown (계층 병합) |
| Cursor | `.cursor/rules/*.mdc` | MDC (alwaysApply / globs) |
| Gemini CLI | `GEMINI.md` | Markdown (계층 병합) |
| Codex | `AGENTS.md` | Markdown (CWD → repo root) |

**Entry file 포인터만 기록** — 에이전트/스킬 목록 중복 금지. 트리거 규칙 + 변경 이력만.

### Cursor Rules 예시 (`.cursor/rules/project.mdc`)

```markdown
---
description: Project-wide coding rules
globs: ["**/*.py"]
alwaysApply: true
---
# Project Rules
- Layer: endpoint → service → DB
```

## Hooks

| 플랫폼 | 설정 파일 | 주요 이벤트 |
|--------|-----------|-------------|
| Claude | `.claude/hooks/hooks.json` | SessionStart, PreToolUse, PostToolUse, Stop |
| Cursor | `.cursor/hooks.json` | sessionStart, beforeShellExecution, afterFileEdit, subagentStart/Stop, stop |
| Gemini | `.gemini/settings.json` | SessionStart, BeforeTool, AfterTool, SessionEnd |
| Codex | `.codex/hooks.json` | SessionStart, PreToolUse, PostToolUse, SubagentStart/Stop, Stop |

**공통 패턴:** guard-shell (위험 명령 차단), session-context (git 브랜치 주입), lint-after-edit.

스크립트 로직은 공유 가능; **설정 JSON/TOML은 플랫폼별 분리**.

## Commands

| 플랫폼 | 권장 | 레거시 |
|--------|------|--------|
| Claude | skill (`/skill-name`) | `.claude/commands/*.md` |
| Cursor | skill | `.cursor/commands/*.md` |
| Gemini | `.gemini/commands/*.toml` | TOML `prompt` 필수 |
| Codex | skill (`/skills`, `$name`) | 별도 commands 폴더 없음 |

### Gemini command 예시

```toml
# .gemini/commands/code-review.toml
description = "Run code review orchestrator"
prompt = "Use the code-review-orchestrator skill for this request."
```

## Skill ↔ Sub Agent 연결

| 연결 | 설명 |
|------|------|
| 1 agent : 1~N skills | agent가 참조할 skill 목록 |
| orchestrator skill | agent 호출 순서·handoff 정의 |
| work skill | 단일 작업 절차 |

### Cursor 연결 패턴

1. `.cursor/skills/{domain}-orchestrator/SKILL.md` — Phase·Task 순서
2. `.cursor/agents/{name}.md` — 역할·handoff
3. Task 호출 전 `Read(.cursor/agents/{name}.md)` → prompt 삽입

### Codex 연결 패턴

1. `.agents/skills/{domain}-orchestrator/SKILL.md` — spawn 지시 포함
2. `.codex/agents/{name}.toml` — `developer_instructions`
3. 사용자/부모가 agent 이름으로 **명시적 spawn**

### Claude 연결 패턴

1. `.claude/skills/{domain}-orchestrator/SKILL.md` — TeamCreate/SendMessage
2. `.claude/agents/{name}.md` — frontmatter + tools/skills

## 공통 Skill + scripts (Agent Skills 표준)

```
.agents/skills/{name}/
├── SKILL.md          # 모든 플랫폼 공통 (Cursor/Gemini/Codex 로드)
├── scripts/          # 결정적 검증·변환
└── references/       # on-demand
```

멀티플랫폼 요청 시: **work skill + scripts**는 `.agents/skills/`에 1회 작성 → `.cursor/skills/`에 symlink 또는 동일 내용 복사.

## Plugin (배포)

| 플랫폼 | Manifest |
|--------|----------|
| Claude | `.claude-plugin/plugin.json` + 루트 skills/agents/hooks |
| Cursor | Marketplace manifest |
| Gemini | `.gemini/extensions/` |
| Codex | `.codex-plugin/plugin.json` |

하네스 **프로젝트 생성** 시 plugin은 선택. 도메인 하네스는 보통 프로젝트 로컬 `.cursor/` 등.

## 멀티 런타임 데이터 격리

동일 머신에서 Claude Code·Cursor·Codex 등 **여러 harness 런타임**을 함께 쓸 때, 세션 요약·훅 로그·learned skills 같은 **persist 파일**이 한 경로를 공유하면 서로 덮어쓴다. 런타임별 저장 루트를 분리한다.

| 런타임 | 기본 data root | 분리 원칙 |
|--------|----------------|-----------|
| Claude Code | `~/.claude/` | Claude 전용 유지 |
| Cursor | `~/.cursor/` (skills, hooks.json) | Cursor 전용 유지 |
| Codex | `~/.codex/`, `~/.agents/skills/` | Codex 전용 유지 |
| Gemini CLI | `~/.gemini/` | Gemini 전용 유지 |

훅이 session summary·metrics·alias 파일을 쓰는 경우, **환경변수 또는 설정**으로 런타임별 출력 디렉터리를 명시한다. 한 IDE의 훅 출력이 다른 IDE 세션 파일과 같은 폴더를 쓰지 않게 한다.

## 필수 모듈: Doc Writer / Sync Docs

**모든 하네스에 반드시 포함.** 코드·entry file·rules **drift 방지**.

| 구성 | 파일 | 필수 |
|------|------|------|
| Agent | `doc-writer` (플랫폼별 agents/) | ✓ |
| Skill | `sync-docs` (`.agents/skills/` + 플랫폼 경로) | ✓ |
| Hook | `check-doc-sync.sh` — Cursor `afterFileEdit` | ✓ (Cursor) |
| Orchestrator | 마지막 Phase → sync-docs / doc-writer | ✓ (Pipeline/Fan-out) |

생성 시 사용자가 doc-writer를 요청하지 않아도 **기본 포함**. 생략 금지.

예시: `references/team-examples.md` 예시 6 · `references/component-templates.md` Doc Writer 섹션

---

## Skill → SubAgent 연결 심화 (Claude Code)

### `context` 옵션 패턴

Claude Code 서브에이전트(`Agent` 도구) 호출 시 **현재 컨텍스트를 어떻게 전달할지** 결정한다.

```markdown
# 오케스트레이터 스킬 지시 예시 (Agent 도구 파라미터)
Agent(
  subagent_type: "qa-agent",
  prompt: "다음 분석 결과 기반으로 QA를 수행: [이전 산출물 경로]",
  context: "fork"   ← 현재 컨텍스트를 복사해 서브에이전트로 전달
)
```

| context 옵션 | 설명 | 적합 상황 |
|-------------|------|----------|
| `fork` | 현재 컨텍스트 복사 전달 | 이전 분석 결과·히스토리 필요 |
| `empty` | 빈 컨텍스트로 시작 | 독립적 서브태스크, 토큰 절약 |
| 기본값 | 플랫폼 정책에 따라 다름 | 빠른 병렬 작업 |

**원칙:** 서브에이전트가 이전 단계 결과를 알아야 하면 `fork`, 완전히 독립적이면 `empty`.

> **주의:** `context` 옵션은 `Agent` 도구(서브에이전트 단독 호출)에 적용한다. `TeamCreate`는 `members` 배열로 팀을 구성하며 별도의 context 파라미터를 사용하지 않는다.

### SKILL.md frontmatter `context: fork` + `agent:` 패턴 (Claude Code)

스킬 자체가 **격리된 서브에이전트로 실행**되어야 할 때 SKILL.md frontmatter에 선언한다. 오케스트레이터가 `Agent` 도구를 명시적으로 호출하는 대신, 스킬이 트리거될 때 자동으로 포크된 컨텍스트에서 실행된다.

```markdown
---
name: deep-research
description: 코드베이스·웹에서 주제를 심층 조사. 리서치, 조사 요청 시 사용.
context: fork    ← 현재 컨텍스트를 복사한 격리 인스턴스에서 실행
agent: Explore   ← 실행에 사용할 에이전트 타입 (Explore = 읽기 전용)
---

Research {{topic}} thoroughly:
1. Search codebase and authoritative web sources
2. Cross-check conflicting claims
3. Return structured report with file:line citations
```

**호출:** `/deep-research authentication flow` — Explore 에이전트가 격리 컨텍스트에서 실행되어 메인 컨텍스트를 오염시키지 않는다.

| frontmatter 키 | 값 | 설명 |
|---------------|-----|------|
| `context` | `fork` | 현재 컨텍스트 복사 전달 (히스토리·결과 공유 필요 시) |
| `context` | `empty` | 빈 컨텍스트로 시작 (완전 격리, 토큰 절약) |
| `agent` | `Explore` / `Plan` / `{custom-name}` | 실행 에이전트 타입 |

> **`Agent` 도구 vs SKILL.md frontmatter:** 오케스트레이터가 프로그래밍적으로 서브에이전트를 제어할 때는 `Agent` 도구 파라미터로 `context`를 지정하고, 스킬 자체가 항상 격리 실행되어야 할 때는 SKILL.md frontmatter에 선언한다.

---

### Handoff Artifacts 패턴

`context:empty` 사용 시, 이전 에이전트의 결과를 파일로 전달:

```
오케스트레이터 작성                         서브에이전트 읽기
_workspace/analysis-result.json   →   "Read _workspace/analysis-result.json 후 QA 시작"
artifacts/qa-report.md            ←   서브에이전트가 작성
```

```markdown
# 오케스트레이터 스킬 지시 예시
1. 분석 결과를 `_workspace/analysis-result.json` 에 저장
2. QA 에이전트 생성:
   - context: empty
   - prompt: "`_workspace/analysis-result.json` 읽고 QA 수행, 결과는 `artifacts/qa-report.md`"
3. 완료 후 `artifacts/qa-report.md` 수집
```

---

## SubAgent 안티패턴

하네스 구성 시 아래 안티패턴은 반드시 피한다.

| 안티패턴 | 문제 | 대안 |
|---------|------|------|
| 오케스트레이터가 작업 직접 수행 | 단일 장애점, 병렬화 불가 | 역할 분리 → 전용 서브에이전트 |
| 서브에이전트가 새 서브에이전트 생성 (3단계+) | 컨텍스트 폭발, 디버깅 불가 | 최대 2레벨 계층 유지 |
| 서브에이전트 간 직접 통신 | 순환 의존, 레이스 컨디션 | 항상 오케스트레이터 경유 |
| 결과를 stdout 으로만 전달 | 컨텍스트 초과 시 유실 | `_workspace/` 파일 handoff |
| 하나의 스킬이 두 에이전트 역할 수행 | 책임 불명확, 재사용 불가 | 역할 1:1 스킬 분리 |
| 에이전트 정의에 에이전트 목록 기재 | Entry file 비대화 | CLAUDE.md = 트리거만, 목록 금지 |
