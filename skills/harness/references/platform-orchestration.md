# Platform Orchestration — 협업 API & 패턴 매핑

> harness 6 패턴은 **설계는 동일**, **실행 API는 플랫폼별**이다.

## 플랫폼별 협업 모델

| 항목 | Claude Code | Cursor | Gemini CLI | Codex |
|------|-------------|--------|------------|-------|
| **팀 실행** | `TeamCreate` + `SendMessage` + `TaskCreate` | **Task** 도구 | Subagents (실험) + skill 체인 | **명시적 spawn** |
| **경량 위임** | `Agent` 도구 | Task (`subagent_type`) | skill 체인 | spawn + `.toml` agents |
| **팀원 통신** | `SendMessage` | 없음 → **파일 핸드오프** | 제한적 | 없음 → 부모 통합 |
| **작업 목록** | `TaskCreate` | `artifacts/task-board.md` | `artifacts/task-board.md` | CSV batch (실험) |
| **Handoff** | `_workspace/` | `artifacts/` | `artifacts/` | `artifacts/` |
| **역할 주입** | agent 자동 로드 | **Read(agent.md) → Task prompt** | skill 본문 | `developer_instructions` (TOML) |
| **오케스트레이터** | `.claude/skills/{domain}-orchestrator/` | `.cursor/skills/{domain}-orchestrator/` | `.gemini/skills/{domain}-orchestrator/` | `.agents/skills/{domain}-orchestrator/` |

## 6 패턴 × 플랫폼

| 패턴 | Claude | Cursor | Gemini | Codex |
|------|--------|--------|--------|-------|
| Pipeline | Team 순차 Task | Task 순차 | skill 순차 | spawn 순차 |
| Fan-out/Fan-in | 병렬 Team + SendMessage | 한 응답에 Task 병렬 | skill/subagent 병렬 | spawn 병렬 |
| Expert Pool | SendMessage to one | 조건부 Task 1건 | skill 1개 활성화 | spawn 1 agent |
| Producer-Reviewer | 2인 Team | 구현 Task → QA Task | 생성 skill → QA skill | spawn → spawn |
| Supervisor | 리더 + TaskCreate | 오케스트레이터 skill | orchestrator skill | 부모 + spawn |
| Hierarchical | 중첩 Team (제한) | Task 체인 | skill 위임 | `max_depth` (config.toml) |

## Claude Code — Fan-out 예시

```
TeamCreate → TaskCreate(T01-T03) → SendMessage(to: each) → Read _workspace/02_*.md → final_report.md
```

사전 요구: `.claude/settings.json` → `"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}` (템플릿: `references/component-templates.md` "Claude Settings")

## Cursor — Fan-out 예시

```
Read(.cursor/agents/{name}.md) → Task(subagent_type, prompt에 역할 삽입) × N 병렬
→ Read artifacts/02_*.md → artifacts/final-report.md
```

**필수:** Task 전 agent 파일 Read → prompt에 전문 삽입. `TeamCreate`/`SendMessage` 사용 금지.

## Gemini CLI — Fan-out 예시

```
/research 또는 orchestrator skill → web-researcher skill + academic-researcher skill (병렬 또는 순차)
→ artifacts/final-report.md
```

Subagents는 실험 기능. skill 체인 + `artifacts/`가 안정적 기본값.

## Codex — Fan-out 예시

```
"Spawn security-auditor and api-architect in parallel"
→ .codex/agents/*.toml → 부모가 결과 통합 → artifacts/final-report.md
```

**필수:** spawn은 사용자/부모가 **명시적으로** 요청. `.codex/config.toml`:

```toml
[agents]
max_threads = 6
max_depth = 1
```

## 실행 모드 선택 (플랫폼 공통)

```
에이전트 2명 이상?
├── Yes → 교차 검증·실시간 피드백 필요?
│         ├── Claude: Agent Team (TeamCreate)
│         ├── Cursor/Gemini/Codex: orchestrator + 병렬 Task/spawn/skill
│         └── No → Sub-agent (경량)
└── No → 단일 agent 또는 skill만
```

## 오케스트레이터 skill 공통 Phase

| Phase | 내용 |
|-------|------|
| 0 | handoff 디렉터리 확인 → **초기 / 부분 재실행 / 아카이브 후 새 실행** 분기 |
| 1 | input + task-board 작성 (아카이브 후 빈 handoff 디렉터리에 생성) |
| 2 | Fan-out (병렬 agent/spawn/task) |
| 3 | Fan-in (통합 + conflicts + final-report + handoff) |

**Phase 0 분기 조건 (플랫폼 공통):**

| 상황 | 조건 | 처리 |
|------|------|------|
| 초기 실행 | handoff 디렉터리 없음 | 신규 생성 후 Phase 1 |
| 부분 재실행 | handoff 있음 + `final-report.md` **없음** + 부분 수정 요청 | 해당 파일만 덮어쓰기 |
| 아카이브 후 새 실행 | handoff 있음 + `final-report.md` **있음** | 아카이브 후 Phase 1 |
| 강제 재시작 | handoff 있음 + 사용자 "새로 시작" 명시 | 아카이브 후 Phase 1 |

**아카이브 명령 (플랫폼별):**

```bash
# Claude Code: _workspace/ → _workspace_archive/{TS}/
ARCHIVE_TS=$(date +%Y%m%d_%H%M%S)
mkdir -p _workspace_archive
mv _workspace/ _workspace_archive/$ARCHIVE_TS/
ls -dt _workspace_archive/*/ 2>/dev/null | tail -n +4 | xargs -r rm -rf

# Cursor / Gemini / Codex: artifacts/ 파일 → artifacts/archive/{TS}/
ARCHIVE_TS=$(date +%Y%m%d_%H%M%S)
mkdir -p artifacts/archive/$ARCHIVE_TS
find artifacts/ -maxdepth 1 -not -name archive -not -name '.' | xargs -I{} mv {} artifacts/archive/$ARCHIVE_TS/
ls -dt artifacts/archive/*/ 2>/dev/null | tail -n +4 | xargs -r rm -rf
```

**보존 정책:** 아카이브 3개 초과 시 가장 오래된 것 자동 삭제.

Handoff 파일명 컨벤션: `00-input.md`, `02_{role}.md`, `task-board.md`, `conflicts.md`, `final-report.md`, `handoff.md`
