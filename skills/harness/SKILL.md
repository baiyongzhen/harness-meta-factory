---
name: harness
description: "하네스를 구성한다. Claude Code, Cursor, Gemini CLI, Codex에 맞는 agents, rules, hooks, skills를 설계·생성하는 메타 스킬. (1) '하네스 구성해줘', 'Cursor/Claude/Gemini/Codex 하네스' 요청 시, (2) 도메인별 에이전트 팀 설계 시, (3) 기존 하네스 확장·수정·점검·동기화 — 에이전트 추가, 스킬 추가/수정, 아키텍처 변경, drift 감지, 하네스 유지보수 등 모든 하네스 변경 요청에 반드시 이 스킬을 사용할 것."
---

# Harness — Multi-Platform Agent Team & Skill Architect

도메인/프로젝트에 맞는 하네스를 **대상 AI 플랫폼**(Claude Code / Cursor / Gemini CLI / Codex)에 맞게 구성한다.

**핵심 원칙:**
1. **플랫폼별 경로**에 agents·skills·rules·hooks를 생성한다 (`references/platform-paths.md`).
2. **동일 설계, 다른 API** — 6 아키텍처 패턴은 공통, 오케스트레이션 API만 플랫폼별 (`references/platform-orchestration.md`).
3. **공통 skill+scripts** — `.agents/skills/`에 work skill, 플랫폼별 agents·hooks·rules만 분리 (`references/skill-writing-guide.md` §10).
4. **Entry file 포인터** — `CLAUDE.md/AGENTS.md/GEMINI.md`에 트리거 + 변경 이력만 (`references/platform-rules.md`).
5. **Doc Writer 필수** — 모든 하네스에 `doc-writer` agent + `sync-docs` skill. Pipeline 마지막 Phase는 문서 동기화.
6. **토큰 최적화** — SKILL.md 500줄 이내, references/ 조건부 로딩, 에이전트 모델 작업별 선택, handoff 파일 크기 관리. 구성 후 지속 감시·최적화 (`references/token-optimization.md`).
7. **하네스는 진화하는 시스템** — 피드백 반영, drift 감지, 지속 갱신 (`references/harness-evolution.md`).

## 플랫폼 감지

| 키워드 | 플랫폼 | Agents | Skills | Rules | Handoff |
|--------|--------|--------|--------|-------|---------|
| Claude, `.claude` | Claude Code | `.claude/agents/*.md` | `.claude/skills/` | `CLAUDE.md` | `_workspace/` |
| Cursor, `.cursor` | Cursor | `.cursor/agents/*.md` | `.cursor/skills/` | `.cursor/rules/*.mdc`, `AGENTS.md` | `artifacts/` |
| Gemini, `.gemini` | Gemini CLI | Subagents/skill roles | `.gemini/skills/` | `GEMINI.md` | `artifacts/` |
| Codex, `.codex` | Codex | `.codex/agents/*.toml` | `.agents/skills/` | `AGENTS.md` | `artifacts/` |

명시 없으면 **현재 IDE/환경** 기본값. 복수 플랫폼 → 공통 `.agents/skills/` + 플랫폼별 agents/hooks/rules.

상세: `references/platform-paths.md` · `references/platform-components.md` · `references/component-templates.md`

## 청사진 승인 게이트

1. **청사진** — 파일 생성 없이 설계안 (플랫폼·경로 트리·agent·skill·패턴·handoff·**doc-writer/sync-docs 필수**)
2. **구성** — 사용자 승인("이 구조로 만들어줘") 후 파일 생성

"바로 만들어줘"는 승인으로 보지 않는다.

## 워크플로우

### Phase 0: 현황 감사

1. **대상 플랫폼** 확정 (위 표)
2. 플랫폼별 경로 Read: agents/, skills/, entry file, hooks (`references/platform-hooks.md`)
3. 실행 모드 분기:

| 상황 | 처리 |
|------|------|
| 신규 구축 | Phase 1 진행 |
| 기존 확장 | 아래 Phase 선택 매트릭스 적용 |
| 운영/유지보수 | `references/harness-evolution.md` §5 |

**기존 확장 시 Phase 선택 매트릭스:**

| 변경 유형 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|----------|---------|---------|---------|---------|---------|---------|
| 에이전트 추가 | 건너뜀 | 배치 결정만 | 필수 (3-0) | 전용 스킬 필요 시 (4-0) | 오케스트레이터 수정 | 필수 |
| 스킬 추가/수정 | 건너뜀 | 건너뜀 | 건너뜀 | 필수 (4-0) | 연결 변경 시 | 필수 |
| 아키텍처 변경 | 건너뜀 | 필수 | 영향받는 에이전트 (3-0) | 영향받는 스킬 (4-0) | 필수 | 필수 |

4. entry file ↔ 실제 파일 drift 감지 후 실행 계획 확인

### Phase 1: 도메인 분석

1. 도메인/프로젝트·핵심 작업 유형 파악
2. 기존 에이전트/스킬과의 충돌·중복 분석
3. 코드베이스 탐색 — 기술 스택, 데이터 모델, 주요 모듈
4. **사용자 숙련도 감지** — 맥락 단서로 기술 수준 파악, 커뮤니케이션 톤 조절

### Phase 2: 팀 아키텍처 설계

#### 2-1. 실행 모드 선택

에이전트 팀/병렬 협업이 최우선 기본값.

| 플랫폼 | 팀/병렬 API |
|--------|-------------|
| Claude Code | Agent 도구(팀원 spawn) + `SendMessage` + `TaskCreate` |
| Cursor | **Task** (agent 이름/`/name` 호출) + `artifacts/` |
| Gemini CLI | orchestrator skill + skill 체인 / Subagents |
| Codex | **명시적 spawn** + `.codex/agents/*.toml` |

| 모드 | 언제 |
|------|------|
| **팀/병렬** (기본) | 2+ agent, 교차 검증 필요 |
| **서브** (대안) | 결과만 반환, 팀 통신 불필요 |
| **하이브리드** | Phase별 특성 다를 때 |

> 상세: `references/platform-orchestration.md` · `references/agent-design-patterns.md`

#### 2-2. 아키텍처 패턴 선택

**파이프라인** / **팬아웃·팬인** / **전문가 풀** / **생성-검증** / **감독자** / **계층적 위임**

> 패턴별 설계 기준·예시: `references/agent-design-patterns.md`

#### 2-3. 에이전트 분리 기준

전문성·병렬성·컨텍스트·재사용성 4축으로 판단. 상세 기준표: `references/agent-design-patterns.md` "에이전트 분리 기준"

### Phase 3: 에이전트 정의 생성

#### 3-0. 기존 에이전트 중복 검토

신규 에이전트 생성 전 대상 플랫폼 agents/ 디렉터리와 중복 검토.

**모든 에이전트는 플랫폼별 정의 파일 필수** (prompt에 역할만 삽입하고 파일 없이 진행 금지):

| 플랫폼 | 경로 | 형식 |
|--------|------|------|
| Claude | `.claude/agents/{name}.md` | Markdown + frontmatter |
| Cursor | `.cursor/agents/{name}.md` | Markdown + frontmatter |
| Gemini | `.gemini/skills/{name}/SKILL.md` | skill role |
| Codex | `.codex/agents/{name}.toml` | TOML + developer_instructions |

템플릿: `references/component-templates.md`

**작성 규칙:**
- 필수 섹션: 역할, 원칙, 입출력(handoff), 에러 핸들링. Claude 팀 모드: `## 팀 통신 프로토콜`
- Claude Code 모델 선택: 탐색 `haiku` / 일반 코딩 `sonnet` / 아키텍처·보안 `opus` (`references/agent-design-patterns.md` "모델 선택 가이드")
- Cursor: Task 전 `Read(.cursor/agents/{name}.md)` → prompt 삽입
- **코드 작성 에이전트:** `## 코딩 원칙 — Search-First` 섹션 포함 필수 (`references/search-first-workflow.md` §7)
- **Doc Writer (필수):** 모든 하네스에 `doc-writer` agent 포함 (`references/component-templates.md`)
- **QA 에이전트:** `general-purpose` 타입 사용, incremental QA (`references/qa-agent-guide.md`)

### Phase 4: 스킬 생성

| 플랫폼 | work skill | orchestrator |
|--------|------------|--------------|
| Claude | `.claude/skills/{name}/` | `.claude/skills/{domain}-orchestrator/` |
| Cursor | `.cursor/skills/{name}/` + `.agents/skills/{name}/` | `.cursor/skills/{domain}-orchestrator/` |
| Gemini | `.gemini/skills/{name}/` + `.agents/skills/{name}/` | `.gemini/skills/{domain}-orchestrator/` |
| Codex | `.agents/skills/{name}/` | `.agents/skills/{domain}-orchestrator/` |

**필수 규칙:**
- **멀티플랫폼:** work skill + `scripts/`는 `.agents/skills/`에 1회 작성 후 플랫폼 경로 배치
- **Sync Docs (필수):** `sync-docs` skill 반드시 생성
- **Commands vs Skill:** 단순 단축키 → Commands, 다단계 워크플로 → Skill (`references/platform-commands.md`)
- **코드 작성 스킬:** Step 1에 Search-First 사전 조사 삽입 (`references/search-first-workflow.md` §7)

#### 4-0. 기존 스킬 중복 검토

신규 스킬 생성 전 기존 스킬과 중복 여부 확인. 중복 분류 기준: `references/skill-writing-guide.md` "스킬 재사용 설계"

#### 4-1. 스킬 작성 핵심 규칙

- description을 **pushy**하게 — 트리거 상황·경계 조건 명시
- SKILL.md 본문 **500줄 이내**, 초과분은 `references/`로 분리 + 포인터 명시
- Why를 설명 / Lean하게 유지 / 일반화 / 명령형 어조
- references/ 파일은 **조건부 로딩** — "X일 때만 이 파일을 읽어라" 포인터 명시 (불필요한 파일 로드 방지)

> 상세 작성 패턴·Progressive Disclosure·스키마·Scripts 전략: `references/skill-writing-guide.md`
> 토큰 비용 관리 전략 (모델 선택·컨텍스트 최적화·지속 모니터링): `references/token-optimization.md`

### Phase 5: 통합 및 오케스트레이션

오케스트레이터는 `{domain}-orchestrator` skill.
- Claude 템플릿: `references/orchestrator-template.md`
- Cursor/Codex/Gemini: `references/platform-orchestration.md` + `references/component-templates.md`
- **Cursor에 Claude 팀 API(`SendMessage`/`TaskCreate`) 금지**
- **모든 Pipeline/Fan-out 오케스트레이터 마지막 Phase: `sync-docs`/`doc-writer` 호출 필수**

#### 5-0. 오케스트레이터 패턴

| 패턴 | 흐름 | 참조 |
|------|------|------|
| **에이전트 팀** (기본·Claude 전용) | Agent(팀원 spawn) → TaskCreate → SendMessage → 수집 | `references/orchestrator-template.md` 템플릿 A |
| **서브 에이전트** (대안) | Agent(run_in_background) × N → 수집 | 템플릿 B |
| **하이브리드** | Phase별 모드 혼합, 각 Phase 상단에 모드 명시 | 템플릿 C |

> ⚠️ 에이전트 팀 사전 요구: `.claude/settings.json`에 `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` 설정 필요. 템플릿: `references/component-templates.md` "Claude Settings"

#### 5-1. 데이터 전달 프로토콜

| 전략 | 방식 | 적합한 경우 |
|------|------|-----------|
| **메시지 기반** | `SendMessage` | 실시간 조율, 피드백 (팀 모드) |
| **태스크 기반** | `TaskCreate`/`TaskUpdate` | 진행 추적, 의존 관계 (팀 모드) |
| **파일 기반** | 약속 경로에 파일 읽기/쓰기 | 대용량·구조화 산출물 (팀+서브) |
| **반환값 기반** | `Agent` 반환 메시지 | 서브 에이전트 결과 수집 |

**Handoff 경로 및 아카이브:**

| 플랫폼 | 현재 실행 | 아카이브 |
|--------|----------|---------|
| Claude | `_workspace/` | `_workspace_archive/{YYYYMMDD_HHMMSS}/` |
| Cursor/Gemini/Codex | `artifacts/` | `artifacts/archive/{YYYYMMDD_HHMMSS}/` |

보존 정책: 3개 초과 시 가장 오래된 것 자동 삭제. 아카이브 명령: `references/platform-orchestration.md`

#### 5-2. 에러 핸들링

핵심: 1회 재시도 후 재실패 시 해당 결과 없이 진행(보고서에 누락 명시), 상충 데이터는 출처 병기.

> 에러 유형별 전략표: `references/orchestrator-template.md` "에러 핸들링"

#### 5-3. 팀 크기 가이드라인

| 작업 규모 | 권장 팀원 수 | 팀원당 작업 수 |
|----------|------------|--------------|
| 소규모 (5~10개 작업) | 2~3명 | 3~5개 |
| 중규모 (10~20개 작업) | 3~5명 | 4~6개 |
| 대규모 (20개+ 작업) | 5~7명 | 4~5개 |

#### 5-4. Entry file 포인터 등록

| 플랫폼 | 파일 | 내용 |
|--------|------|------|
| Claude | `CLAUDE.md` | 트리거 + 변경 이력 |
| Cursor | `AGENTS.md` | 트리거 + 변경 이력 |
| Gemini | `GEMINI.md` | 트리거 + `/command` (선택) |
| Codex | `AGENTS.md` | 트리거 + spawn 힌트 |

에이전트/스킬 목록·디렉터리 구조는 entry file에 **넣지 않는다**. 템플릿: `references/component-templates.md` "Entry Pointers"

#### 5-5. 후속 작업 지원

**Phase 0 분기 결정표:**

| 상황 | 판단 조건 | 처리 |
|------|----------|------|
| 초기 실행 | handoff 디렉터리 없음 | 새 디렉터리 생성 후 Phase 1 |
| 부분 재실행 | handoff 있음 + 완료 마커 없음 + 부분 수정 요청 | 해당 에이전트만 재호출 |
| 새 실행 (완료 후) | handoff 있음 + `final-report.md` 존재 | 아카이브 후 Phase 1 재시작 |
| 강제 재시작 | handoff 있음 + "새로 시작" 명시 | 아카이브 후 Phase 1 재시작 |

아카이브 명령: `references/platform-orchestration.md`. 오케스트레이터 description에 후속 키워드 포함 필수 — "다시 실행", "재실행", "업데이트", "수정", "보완", "이전 결과 기반으로"

### Phase 6: 검증 및 테스트

> 상세 방법론: `references/skill-testing-guide.md`

| 검증 항목 | 확인 내용 |
|----------|----------|
| **토큰 감사** | SKILL.md 줄 수 확인 (500줄 초과 없는지), handoff 파일 크기 (200줄 초과 있는지), 불필요한 references/ 전체 로드 여부 (`references/token-optimization.md` §5) |
| **스킬 크기** | 모든 SKILL.md 본문 **500줄 이내** — 초과 시 세부 내용을 `references/`로 분리하고 포인터 명시 |
| **구조** | 파일 위치, frontmatter(name·description 필수), 참조 일관성, 커맨드 미생성 |
| **실행 모드** | 팀: 통신 경로·의존성 / 서브: 입출력·run_in_background / 하이브리드: Phase 경계 전달 |
| **스킬 테스트** | 현실적 프롬프트 2~3개, With vs Without 비교, 피드백 일반화 |
| **트리거 검증** | Should-trigger 8~10개 + Should-NOT-trigger 8~10개 (경계 모호 쿼리 포함) |
| **드라이런** | Phase 순서·dead link·입출력 매칭·에러 폴백 |
| **테스트 시나리오** | 오케스트레이터에 `## 테스트 시나리오` 섹션 추가 (정상 1 + 에러 1 이상) |

### Phase 7: 하네스 진화

하네스는 진화하는 시스템이다. 매 실행 후 피드백을 수집하고 반영한다.

> 피드백 반영 경로, 변경 이력 관리, 운영·유지보수 워크플로우: `references/harness-evolution.md`

## 산출물 체크리스트

**공통**
- [ ] 대상 플랫폼 확정 + `references/platform-paths.md` 경로 준수
- [ ] **`doc-writer` agent + `sync-docs` skill (필수)**
- [ ] orchestrator skill 1개 — **마지막 Phase: 문서 동기화 (sync-docs)**
- [ ] work skill(s) + description pushy + 후속 키워드
- [ ] **모든 SKILL.md 본문 500줄 이내** — 초과 시 `references/`로 분리 + 포인터 명시
- [ ] `.agents/skills/` 공통 skill (멀티플랫폼 시)
- [ ] entry file 포인터 + 변경 이력 (`references/platform-rules.md` 형식 준수)
- [ ] handoff 디렉터리 (`_workspace/` 또는 `artifacts/`)
- [ ] commands 폴더: 단순 단축키만 생성 — 다단계 워크플로는 skill 우선 (`references/platform-commands.md`)
- [ ] 트리거 검증 + 테스트 프롬프트 2~3개

**Claude Code**
- [ ] `.claude/settings.json` — 에이전트 팀 사용 시 `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` 필수, 권한 제한 에이전트 포함 시 `permissions` 추가 (`references/component-templates.md` "Claude Settings")
- [ ] `.claude/agents/*.md` + `.claude/skills/` ( **`doc-writer` + `sync-docs` 포함** )
- [ ] 팀 모드(Agent spawn + SendMessage/TaskCreate) 또는 단독 Agent (orchestrator에 명시)
- [ ] `CLAUDE.md` 포인터

**Cursor**
- [ ] `.cursor/agents/*.md` + `.cursor/skills/` ( **`doc-writer` 포함** )
- [ ] `.cursor/rules/*.mdc` — `alwaysApply`/`globs`/Intelligent/Manual 방식 적용 (`references/platform-rules.md`) + `AGENTS.md`
- [ ] `.cursor/hooks.json` — guard-shell + **`check-doc-sync.sh` (afterFileEdit, 필수)**
- [ ] `artifacts/` + Task 전 Read(agent)→prompt
- [ ] Claude 팀 API(`SendMessage`/`TaskCreate`) **미사용**

**Gemini CLI**
- [ ] `.gemini/skills/` + `GEMINI.md` ( **`sync-docs` 필수**; `doc-writer`는 skill role로 구현 — `references/team-examples.md` 예시 6 )
- [ ] `.gemini/commands/*.toml` — `!{shell}` 주입 활용 (`references/platform-commands.md`)
- [ ] `artifacts/`

**Codex**
- [ ] `.codex/agents/*.toml` + `.agents/skills/` ( **`doc-writer.toml` + `sync-docs` 필수** )
- [ ] `AGENTS.md` + `.codex/config.toml` (max_threads/depth)
- [ ] orchestrator에 **명시적 spawn** 지시
- [ ] `artifacts/`

## 참고

- **플랫폼 경로:** `references/platform-paths.md`
- **플랫폼 오케스트레이션 + 아카이브 명령:** `references/platform-orchestration.md`
- **플랫폼 구성요소 + SubAgent 안티패턴:** `references/platform-components.md`
- **플랫폼 템플릿:** `references/component-templates.md`
- **훅 설계:** `references/platform-hooks.md`
- **Rules 설계:** `references/platform-rules.md`
- **Commands 설계:** `references/platform-commands.md`
- **Plugin / Extension 패키징·배포:** `references/platform-plugin.md`
- **Search-First 코딩 워크플로우:** `references/search-first-workflow.md`
- **토큰 최적화·지속 모니터링:** `references/token-optimization.md`
- **하네스 진화·유지보수:** `references/harness-evolution.md`
- 하네스 패턴: `references/agent-design-patterns.md`
- 예시: `references/team-examples.md`
- Claude orchestrator: `references/orchestrator-template.md`
- 스킬 작성 (Scripts §10 포함): `references/skill-writing-guide.md`
- 스킬 테스트: `references/skill-testing-guide.md`
- QA 에이전트: `references/qa-agent-guide.md`
