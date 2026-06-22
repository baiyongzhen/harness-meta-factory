# Component Templates — 플랫폼별 Agent / Skill / Hooks / Entry

> Phase 3–5에서 플랫폼별 파일 생성 시 이 템플릿을 사용한다.

## Cursor Agent (`.cursor/agents/{name}.md`)

```markdown
---
name: {name}
description: {one-line role for Task routing}
---

# {Title}

## Role
{specialty}

## Handoff
| Read | Write |
|------|-------|
| artifacts/00-input.md | artifacts/02_{artifact}.md |

## Principles
- {principle 1}
```

## Claude Agent (`.claude/agents/{name}.md`)

```markdown
---
name: {name}
description: {trigger description}
tools: Read, Grep, Glob, Write, Edit   # 선택 — 도구 접근 제한
model: opus                             # 선택 — 기본 opus 권장
skills:                                 # 선택 — 에이전트 시작 시 사전 로드할 스킬
  - {skill-name-1}
  - {skill-name-2}
---

# {Title}

## Role
{specialty}

## Team protocol (if team mode)
- SendMessage to: {peers}
- Output: _workspace/02_{artifact}.md
```

> **`skills:` frontmatter:** 나열된 스킬은 에이전트 시작 시 참조 자료로 자동 로드된다. 에이전트가 특정 방법론·패턴 문서를 항상 참조해야 할 때 사용한다.

## Codex Agent (`.codex/agents/{name}.toml`)

```toml
name = "{name}"
description = "{one-line role — used for spawn routing}"

# 선택 옵션
model = "gpt-5.4"                     # 기본값 생략 가능
model_reasoning_effort = "high"        # low | medium | high
sandbox_mode = "read-only"             # 쓰기 방지 (탐색 전용 에이전트에 권장)
nickname_candidates = ["Atlas", "Delta"] # 멀티 에이전트 식별용 별칭

[developer_instructions]
instructions = """
You are {role}. Read artifacts/00-input.md. Write artifacts/02_{artifact}.md.
Follow project AGENTS.md. Do not spawn subagents unless asked.
"""

# 특정 스킬 비활성화 (선택)
[[skills.config]]
path = ".agents/skills/{skill-name}/SKILL.md"
enabled = false
```

> **`sandbox_mode = "read-only"`**: 파일 수정 없이 탐색·분석만 하는 에이전트(PR 탐색, 코드 매핑 등)에 적용하여 의도치 않은 변경을 방지한다.  
> **`[[skills.config]]`**: 해당 에이전트에서만 특정 스킬을 비활성화할 때 사용한다.

## Skill (공통 — `.agents/skills/{name}/SKILL.md`)

```markdown
---
name: {name}
description: >
  {what it does}. Use when {trigger phrases}. Also for follow-up: rerun, update, partial redo.
---

# {Title}

## Steps
1. ...
```

Cursor/Gemini/Claude 경로에도 동일 SKILL.md 배치 (내용 동일, 경로만 다름).

## Orchestrator Skill (플랫폼별 handoff)

### Cursor (`.cursor/skills/{domain}-orchestrator/SKILL.md`)

```markdown
## Execution: Cursor Task (NOT TeamCreate)

| Agent | File | Output |
|-------|------|--------|
| {a} | `.cursor/agents/{a}.md` | `artifacts/02_{x}.md` |

## Phase 2 Fan-out
**Required:** Read(.cursor/agents/{name}.md) then Task(subagent_type, prompt with full agent text)
```

### Claude (`.claude/skills/{domain}-orchestrator/SKILL.md`)

```markdown
## Execution: Agent Team
TeamCreate → TaskCreate → SendMessage → collect _workspace/02_*.md
```

### Codex (`.agents/skills/{domain}-orchestrator/SKILL.md`)

```markdown
## Execution: explicit spawn
Ask user/parent to spawn: {agent-a}, {agent-b} in parallel.
Integrate artifacts/02_*.md → artifacts/final-report.md
```

## Cursor Rule (`.cursor/rules/project.mdc`)

```markdown
---
description: {project} coding rules
globs: ["**/*.{ext}"]
alwaysApply: true
---
# Rules
- {rule}
```

## Cursor Hooks (`.cursor/hooks.json`)

```json
{
  "hooks": {
    "sessionStart": [{ "command": "bash .cursor/hooks/session-context.sh 2>/dev/null || true" }],
    "beforeShellExecution": [{ "command": ".cursor/hooks/guard-shell.sh" }],
    "afterFileEdit": [
      { "command": "bash .cursor/hooks/check-doc-sync.sh 2>/dev/null || true" },
      { "command": "bash .cursor/hooks/lint-check.sh 2>/dev/null || true", "matcher": "**/*.py" }
    ],
    "subagentStart": [{ "command": "bash .cursor/hooks/log-subagent.sh 2>/dev/null || true" }],
    "subagentStop": [{ "command": "bash .cursor/hooks/log-subagent.sh 2>/dev/null || true" }]
  }
}
```

## Claude Hooks (`.claude/hooks/hooks.json`)

```json
{
  "hooks": {
    "SessionStart": [{ "matcher": "startup", "hooks": [{ "type": "command", "command": ".claude/hooks/session-context.sh" }] }],
    "PreToolUse": [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": ".claude/hooks/guard-shell.sh" }] }]
  }
}
```

## Entry Pointers

### AGENTS.md (Cursor / Codex)

```markdown
## Harness: {domain}
**Trigger:** {domain} work → use `{domain}-orchestrator` skill.
**Change log:** | date | change | target | reason |
```

> ⚠️ 에이전트·스킬 목록·디렉터리 경로는 AGENTS.md에 넣지 않는다 — drift 원인이 된다.

### CLAUDE.md (Claude Code)

```markdown
## Harness: {domain}
**Trigger:** {domain} → `{domain}-orchestrator` skill.
**Change log:** (table)
```

### GEMINI.md (Gemini CLI)

```markdown
## Harness: {domain}
**Trigger:** /{command} or `{domain}-orchestrator` skill.
```

## artifacts/ README (Cursor/Gemini/Codex)

```markdown
# Artifacts
| File | Purpose |
|------|---------|
| 00-input.md | User request / scope |
| task-board.md | Task status |
| 02_*.md | Agent outputs |
| final-report.md | Integrated result |
| handoff.md | Next session context |
```

## Shared scripts (`.agents/skills/{name}/scripts/`)

```python
# validate_{domain}.py — run from skill: python .agents/skills/{name}/scripts/validate_{domain}.py
```

플랫폼별 skill 본문에서 동일 상대 경로로 호출 (Codex/Cursor/Gemini 모두 `.agents/skills/` 스캔).

---

## Doc Writer Agent (문서·하네스 동기화 — **필수**)

> Phase 3: 도메인 agent와 함께 **반드시** `doc-writer` 생성.

### Cursor (`.cursor/agents/doc-writer.md`)

```markdown
---
name: doc-writer
description: Sync AGENTS.md and .cursor/rules/ with current code and harness. Use after new endpoints, domains, or dependency changes.
---

# Doc Writer

## Role
Keep entry file and rules aligned with codebase and `.cursor/` harness.

## Owned files
| File | Trigger |
|------|---------|
| AGENTS.md | New endpoints, stack, structure |
| .cursor/rules/project.mdc | Architecture, conventions |
| .cursor/rules/new-domain.mdc | Domain add procedure |
| .cursor/rules/testing.mdc | Test strategy |
| .cursor/rules/security.mdc | Security requirements |

## Checklist (new endpoint)
- [ ] AGENTS.md API table updated
- [ ] project.mdc layer section updated

## Style
- Code blocks with language tags; tables minimal; examples from real project code
```

### Claude (`.claude/agents/doc-writer.md`)

동일 구조. Owned files: `CLAUDE.md`, `.claude/skills/` index (포인터만).

### Codex (`.codex/agents/doc-writer.toml`)

```toml
name = "doc-writer"
description = "Sync AGENTS.md with code after structural changes. Spawn after add-resource or refactor."

[developer_instructions]
instructions = """
Follow sync-docs skill. Update AGENTS.md API table, tech stack, directory tree from actual app/ files.
Do not duplicate full agent/skill lists in AGENTS.md — pointers only.
"""
```

---

## Sync Docs Skill (`.agents/skills/sync-docs/SKILL.md` — **필수**)

> Phase 4: 도메인 work skill과 함께 **반드시** 생성.

```markdown
---
name: sync-docs
description: >
  Sync entry file and rules with current code. Quality score 0-100 before/after report.
  Use when: doc sync, AGENTS.md update, rules drift, new domain/endpoint added, sync docs.
  Follow-up: partial file sync, re-run after code change.
---

# Sync Docs

## 1. Score current docs (0-100 each file)
| Criterion | Points |
|-----------|--------|
| Matches actual code | 30 |
| Actionable for AI | 25 |
| No redundant duplication | 20 |
| Latest API endpoints | 15 |
| Example code accuracy | 10 |

## 2. Sync entry file (platform-specific)
- Cursor/Codex: AGENTS.md — endpoints from app/, models, requirements.txt, dir tree
- Claude: CLAUDE.md — harness pointers + stack
- Gemini: GEMINI.md

## 3. Sync rules
- Cursor: `.cursor/rules/project.mdc`, `new-domain.mdc`, `testing.mdc`, `security.mdc`
- Claude/Gemini/Codex: equivalent rules file per platform-paths.md

## 4. Report
| File | Before | After | Grade |
|------|--------|-------|-------|
| ... | | | |
```

플랫폼별 경로는 `references/platform-paths.md` 참조. Cursor 예시는 `app/api/v1/endpoints/`, `app/models/` 등 FastAPI 레이아웃.

---

## Doc Sync Hook (Cursor — **필수**)

**`.cursor/hooks/check-doc-sync.sh`** — `afterFileEdit`에서 경로별 힌트:

- `app/models/*.py` → schema/service 누락, AGENTS.md 힌트
- `app/api/v1/endpoints/*.py` → router 등록, API 테이블 힌트
- `requirements.txt` / `pyproject.toml` → tech stack 힌트

**hooks.json 추가:**

```json
"afterFileEdit": [
  { "command": "bash .cursor/hooks/check-doc-sync.sh 2>/dev/null || true" }
]
```

## Pipeline orchestrator — 문서 Phase 스니펫 (**필수**)

모든 `{domain}-orchestrator`에 마지막 Phase 포함:

```markdown
| Phase | Assignee | Output |
|-------|----------|--------|
| N Doc sync | sync-docs / doc-writer | AGENTS.md, rules/*.mdc updated |
```
