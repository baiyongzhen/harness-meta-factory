# Platform Paths — Claude Code / Cursor / Gemini CLI / Codex

> Harness 구성 요소가 각 플랫폼에서 놓이는 경로. 하네스 생성 시 **대상 플랫폼 경로만** 사용한다.

## 한눈에 비교

| 구성 요소 | Claude Code | Cursor | Gemini CLI | Codex |
|-----------|-------------|--------|------------|-------|
| **Rules** | `CLAUDE.md` | `.cursor/rules/*.mdc` | `GEMINI.md` | `AGENTS.md` |
| **Commands** | skill 통합 (`.claude/commands/` 레거시) | skill 권장 (`.cursor/commands/` 레거시) | `.gemini/commands/*.toml` | `/skills`, `$skill-name` |
| **Hooks** | `.claude/hooks/hooks.json` | `.cursor/hooks.json` | `.gemini/settings.json` → hooks | `.codex/hooks.json` |
| **Sub agent** | `.claude/agents/*.md` | `.cursor/agents/*.md` | Subagents (실험) | `.codex/agents/*.toml` |
| **Skill** | `.claude/skills/` | `.cursor/skills/` + `.agents/skills/` | `.gemini/skills/` + `.agents/skills/` | `.agents/skills/` |
| **Handoff** | `_workspace/` | `artifacts/` | `artifacts/` | `artifacts/` |
| **Entry** | `CLAUDE.md` | `AGENTS.md` | `GEMINI.md` | `AGENTS.md` |

## 플랫폼 감지

사용자 프롬프트에서 대상 플랫폼을 추출한다. 명시 없으면 **현재 IDE/환경**을 기본값으로 사용한다.

| 키워드 | 플랫폼 |
|--------|--------|
| Claude, Claude Code, `.claude` | Claude Code |
| Cursor, `.cursor` | Cursor |
| Gemini, Gemini CLI, `.gemini` | Gemini CLI |
| Codex, OpenAI, `.codex` | Codex |

복수 플랫폼 요청 시: 공통 `SKILL.md` + `scripts/`는 `.agents/skills/`에 두고, 플랫폼별 agents·hooks·rules만 분리 생성한다.

## Claude Code

```
your-project/
├── CLAUDE.md
├── _workspace/
└── .claude/
    ├── settings.json          ← 환경변수·권한·모델 설정 (에이전트 팀 env 포함)
    ├── agents/{name}.md
    ├── skills/{name}/SKILL.md
    └── hooks/hooks.json
```

**`.claude/settings.json` 생성 조건:**
- 에이전트 팀(TeamCreate/SendMessage) 사용 시 → `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 필수
- 도구 접근 제한이 필요한 에이전트 포함 시 → `permissions` 설정
- 프로젝트 전용 환경변수(API 키 제외) 주입 시 → `env` 사용

> 템플릿: `references/component-templates.md` `.claude/settings.json`

## Cursor

```
your-project/
├── AGENTS.md
├── artifacts/
│   ├── 00-input.md
│   ├── task-board.md
│   ├── 02_*.md
│   ├── conflicts.md
│   ├── final-report.md
│   └── handoff.md
└── .cursor/
    ├── rules/*.mdc
    ├── agents/{name}.md
    ├── skills/{name}/SKILL.md
    ├── hooks.json
    └── hooks/
```

## Gemini CLI

```
your-project/
├── GEMINI.md
├── artifacts/
└── .gemini/
    ├── settings.json
    ├── commands/{name}.toml
    └── skills/{name}/SKILL.md
```

## Codex

```
your-project/
├── AGENTS.md
├── artifacts/
├── .agents/skills/{name}/SKILL.md
└── .codex/
    ├── config.toml
    ├── agents/{name}.toml
    └── hooks.json
```

## 멀티플랫폼 생성 전략

1. **공통** — `.agents/skills/{name}/SKILL.md` + `scripts/` (Agent Skills 오픈 표준)
2. **분리** — agents, hooks, rules, entry file (플랫폼별 형식)
3. **이식 금지** — Claude `CLAUDE.md` ≠ Cursor `AGENTS.md` + `.cursor/rules/`
4. **오케스트레이션** — 동일 6 패턴, API만 플랫폼별 (`references/platform-orchestration.md`)

## 이식 금지

| 하지 말 것 | 이유 |
|-----------|------|
| Cursor에 `TeamCreate`/`SendMessage` | Cursor API 없음 |
| Cursor에 `_workspace/` | `artifacts/` 사용 |
| Claude harness에 `.cursor/` 경로 | 런타임 불일치 |
| Codex에 `.claude/agents/`만 두기 | `.codex/agents/*.toml` 필요 |
| Gemini TOML commands를 Cursor `.md`에 복사 | 형식·경로 다름 |
