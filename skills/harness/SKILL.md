---
name: harness
description: "하네스를 구성한다. Claude Code, Cursor, Gemini CLI, Codex에 맞는 agents, rules, hooks, skills를 설계·생성하는 메타 스킬. (1) '하네스 구성해줘', 'Cursor/Claude/Gemini/Codex 하네스' 요청 시, (2) 도메인별 에이전트 팀 설계 시, (3) 기존 하네스 확장·수정·점검·동기화 — 에이전트 추가, 스킬 추가/수정, 아키텍처 변경, drift 감지, 하네스 유지보수 등 모든 하네스 변경 요청에 반드시 이 스킬을 사용할 것."
---

# Harness — Multi-Platform Agent Team & Skill Architect

도메인/프로젝트에 맞는 하네스를 **대상 AI 플랫폼**(Claude Code / Cursor / Gemini CLI / Codex)에 맞게 구성한다.

**핵심 원칙:**
1. **플랫폼별 경로**에 agents·skills·rules·hooks를 생성한다 (`references/platform-paths.md`).
2. **동일 설계, 다른 API** — 6 아키텍처 패턴은 공통, 오케스트레이션 API만 플랫폼별 (`references/platform-orchestration.md`).
3. **공통 skill+scripts** — `.agents/skills/` (Agent Skills 오픈 표준)에 work skill을 두고 플랫폼별 agents·hooks·rules만 분리. Scripts 통합 전략: `references/skill-writing-guide.md` §10.
4. **Entry file 포인터** — `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`에 트리거 + 변경 이력만 (목록 중복 금지). 플랫폼별 Rules 설계: `references/platform-rules.md`.
5. **Doc Writer 필수** — 모든 하네스에 `doc-writer` agent + `sync-docs` skill 포함. Pipeline 오케스트레이터 **마지막 Phase**는 문서 동기화. Cursor는 `check-doc-sync.sh` hook 필수.
6. **하네스는 진화하는 시스템** — 피드백 반영, drift 감지, 지속 갱신.

## 플랫폼 감지

| 키워드 | 플랫폼 | Agents | Skills | Rules | Handoff |
|--------|--------|--------|--------|-------|---------|
| Claude, `.claude` | Claude Code | `.claude/agents/*.md` | `.claude/skills/` | `CLAUDE.md` | `_workspace/` |
| Cursor, `.cursor` | Cursor | `.cursor/agents/*.md` | `.cursor/skills/` | `.cursor/rules/*.mdc`, `AGENTS.md` | `artifacts/` |
| Gemini, `.gemini` | Gemini CLI | Subagents/skill roles | `.gemini/skills/` | `GEMINI.md` | `artifacts/` |
| Codex, `.codex` | Codex | `.codex/agents/*.toml` | `.agents/skills/` | `AGENTS.md` | `artifacts/` |

명시 없으면 **현재 IDE/환경**을 기본값. 복수 플랫폼 → 공통 `.agents/skills/` + 플랫폼별 agents/hooks/rules.

상세: `references/platform-paths.md` · `references/platform-components.md` · `references/component-templates.md`

## 청사진 승인 게이트

1. **청사진** — 파일 생성 없이 설계안 (플랫폼·경로 트리·agent·skill·패턴·handoff·**doc-writer/sync-docs 필수**)
2. **구성** — 사용자 승인("이 구조로 만들어줘") 후 파일 생성

"바로 만들어줘"는 승인으로 보지 않는다.

## 워크플로우

### Phase 0: 현황 감사

1. **대상 플랫폼** 확정 (위 표)
2. 플랫폼별 경로 Read: agents/, skills/, entry file, hooks 파일 (있으면) — 훅 파일 위치·이벤트 규약: `references/platform-hooks.md`
3. 실행 모드 분기:
   - **신규 구축** → Phase 1
   - **기존 확장** → Phase 선택 매트릭스
   - **운영/유지보수** → Phase 7 § 7-5

   **기존 확장 시 Phase 선택 매트릭스:**
   | 변경 유형 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
   |----------|---------|---------|---------|---------|---------|---------|
   | 에이전트 추가 | 건너뜀 (Phase 0 결과 활용) | 배치 결정만 | 필수 (3-0 포함) | 전용 스킬 필요 시 (4-0 포함) | 오케스트레이터 수정 | 필수 |
   | 스킬 추가/수정 | 건너뜀 | 건너뜀 | 건너뜀 | 필수 (4-0 포함) | 연결 변경 시 | 필수 |
   | 아키텍처 변경 | 건너뜀 | 필수 | 영향받는 에이전트만 (3-0 포함) | 영향받는 스킬만 (4-0 포함) | 필수 | 필수 |
3. entry file와 실제 파일 drift 감지
4. 감사 결과 요약 + 실행 계획 확인

### Phase 1: 도메인 분석
1. 사용자 요청에서 도메인/프로젝트 파악
2. 핵심 작업 유형 식별 (생성, 검증, 편집, 분석 등)
3. Phase 0 감사 결과를 기반으로 기존 에이전트/스킬과의 충돌/중복 분석
4. 프로젝트 코드베이스 탐색 — 기술 스택, 데이터 모델, 주요 모듈 파악
5. **사용자 숙련도 감지** — 대화의 맥락 단서(사용 용어, 질문 수준)로 기술 수준을 파악하고, 이후 커뮤니케이션 톤을 조절한다. 코딩 경험이 적은 사용자에게는 "assertion", "JSON schema" 같은 용어를 설명 없이 쓰지 않는다.

### Phase 2: 팀 아키텍처 설계

#### 2-1. 실행 모드 선택

**에이전트 팀/병렬 협업이 최우선 기본값.** 2명 이상 협업 시 플랫폼별 API:

| 플랫폼 | 팀/병렬 API |
|--------|-------------|
| Claude Code | `TeamCreate` + `SendMessage` + `TaskCreate` |
| Cursor | **Task** (`subagent_type`) + `artifacts/` |
| Gemini CLI | orchestrator skill + skill 체인 / Subagents |
| Codex | **명시적 spawn** + `.codex/agents/*.toml` |

| 모드 | 언제 | Claude | Cursor/Codex/Gemini |
|------|------|--------|---------------------|
| **팀/병렬** (기본) | 2+ agent, 교차 검증 | TeamCreate | Task(Cursor) / spawn(Codex) / skill 체인(Gemini) |
| **서브** (대안) | 결과만 반환 | `Agent` | Task 1건 / spawn 1건 |
| **하이브리드** | Phase별 특성 다름 | Phase별 모드 명시 | 동일 |

> 상세: `references/platform-orchestration.md` · `references/agent-design-patterns.md`

#### 2-2. 아키텍처 패턴 선택

1. 작업을 전문 영역으로 분해
2. 에이전트 팀 구조 결정 (아키텍처 패턴은 `references/agent-design-patterns.md` 참조)
   - **파이프라인**: 순차 의존 작업
   - **팬아웃/팬인**: 병렬 독립 작업
   - **전문가 풀**: 상황별 선택 호출
   - **생성-검증**: 생성 후 품질 검수
   - **감독자**: 중앙 에이전트가 상태 관리 및 동적 분배
   - **계층적 위임**: 상위 에이전트가 하위에 재귀적 위임

#### 2-3. 에이전트 분리 기준

전문성·병렬성·컨텍스트·재사용성 4축으로 판단한다. 상세 기준표는 `references/agent-design-patterns.md`의 "에이전트 분리 기준" 참조. 기존 에이전트와의 중복·재사용 검토는 Phase 3-0에서 다룬다.

### Phase 3: 에이전트 정의 생성

#### 3-0. 기존 에이전트 중복 검토

신규 에이전트 생성 전, **대상 플랫폼 agents/** 디렉터리와 중복 검토.

**모든 에이전트는 플랫폼별 정의 파일 필수.** prompt에 역할 직접 삽입만 하고 파일 없이 진행 금지.

| 플랫폼 | 경로 | 형식 |
|--------|------|------|
| Claude | `.claude/agents/{name}.md` | Markdown + frontmatter |
| Cursor | `.cursor/agents/{name}.md` | Markdown + frontmatter |
| Gemini | `.gemini/skills/{name}/` (Subagents는 실험 기능 — skill role로 구현) | SKILL.md |
| Codex | `.codex/agents/{name}.toml` | TOML + developer_instructions |

템플릿: `references/component-templates.md`

**Claude Code:** 작업 복잡도에 따라 모델 선택 — 탐색/검색은 `haiku`, 일반 코딩은 `sonnet`, 아키텍처·보안·복잡한 추론은 `opus`. 비용 최적화 상세: `references/agent-design-patterns.md` "모델 선택 가이드". **Cursor:** Task 전 `Read(.cursor/agents/{name}.md)` → prompt 삽입. **Codex:** spawn은 orchestrator skill에서 명시적 지시.

필수 섹션: 역할, 원칙, 입출력(handoff), 에러 핸들링. Claude 팀 모드: `## 팀 통신 프로토콜`.

**Doc Writer (필수):** 모든 하네스에 `doc-writer` agent 생성. 도메인 agent와 별도. 템플릿: `references/component-templates.md` · 예시: `references/team-examples.md` 예시 6.

**QA 에이전트 포함 시 필수 사항:**
- QA 에이전트는 `general-purpose` 타입을 사용하라 (`Explore`는 읽기 전용이므로 검증 스크립트 실행 불가)
- QA의 핵심은 "존재 확인"이 아니라 **"경계면 교차 비교"** — API 응답과 프론트 훅을 동시에 읽고 shape을 비교
- QA는 전체 완성 후 1회가 아니라, **각 모듈 완성 직후 점진적으로 실행** (incremental QA)
- 상세 가이드: `references/qa-agent-guide.md` 참조

### Phase 4: 스킬 생성

| 플랫폼 | work skill | orchestrator |
|--------|------------|--------------|
| Claude | `.claude/skills/{name}/` | `.claude/skills/{domain}-orchestrator/` |
| Cursor | `.cursor/skills/{name}/` + `.agents/skills/{name}/` | `.cursor/skills/{domain}-orchestrator/` |
| Gemini | `.gemini/skills/{name}/` + `.agents/skills/{name}/` | `.gemini/skills/{domain}-orchestrator/` |
| Codex | `.agents/skills/{name}/` | `.agents/skills/{domain}-orchestrator/` |

**멀티플랫폼:** work skill + `scripts/`는 `.agents/skills/`에 1회 작성 후 플랫폼 경로에 동일 내용 배치.

**Sync Docs (필수):** `sync-docs` skill을 반드시 생성 (`.agents/skills/sync-docs/` + 플랫폼 경로). 도메인 work skill과 별도.

**Commands vs Skill 판단:** 단순 프롬프트 단축키는 Commands(`.claude/commands/`, `.gemini/commands/*.toml` 등), 다단계 워크플로는 Skill. 상세: `references/platform-commands.md`

상세 작성: `references/skill-writing-guide.md` (Scripts 통합 전략 §10 포함)

#### 4-0. 기존 스킬 중복 검토

신규 스킬 생성 전, 대상 플랫폼 skills/ 경로(`.claude/skills/` · `.cursor/skills/` · `.agents/skills/` 등)의 기존 스킬과 중복 여부를 확인한다. 하네스를 반복 구축하다 보면 기능이 겹치는 스킬이 다른 이름으로 누적되기 쉽다.

> 중복 분류 기준과 일반화 패턴은 `references/skill-writing-guide.md`의 "스킬 재사용 설계" 참조.

#### 4-1. 스킬 구조

```
skill-name/
├── SKILL.md (필수)
│   ├── YAML frontmatter (name, description 필수)
│   └── Markdown 본문
└── Bundled Resources (선택)
    ├── scripts/    - 반복/결정적 작업용 실행 코드
    ├── references/ - 조건부 로딩하는 참조 문서
    └── assets/     - 출력에 사용되는 파일 (템플릿, 이미지 등)
```

#### 4-2. Description 작성 — 적극적 트리거 유도

description은 스킬의 유일한 트리거 메커니즘이다. Claude는 트리거를 보수적으로 판단하는 경향이 있으므로, description을 **적극적("pushy")**으로 작성한다.

**나쁜 예:** `"PDF 문서를 처리하는 스킬"`
**좋은 예:** `"PDF 파일 읽기, 텍스트/테이블 추출, 병합, 분할, 회전, 워터마크, 암호화, OCR 등 모든 PDF 작업을 수행. .pdf 파일을 언급하거나 PDF 산출물을 요청하면 반드시 이 스킬을 사용할 것."`

핵심: 스킬이 하는 일 + 구체적 트리거 상황을 모두 기술하고, 유사하지만 트리거하면 안 되는 경우와 구분되도록 작성.

#### 4-3. 본문 작성 원칙

| 원칙 | 설명 |
|------|------|
| **Why를 설명하라** | "ALWAYS/NEVER" 같은 강압적 지시 대신, 왜 그렇게 해야 하는지 이유를 전달한다. LLM은 이유를 이해하면 엣지 케이스에서도 올바르게 판단한다. |
| **Lean하게 유지** | 컨텍스트 윈도우는 공공재다. SKILL.md 본문은 500줄 이내를 목표로, 무게를 벌지 않는 내용은 삭제하거나 references/로 이동한다. |
| **일반화하라** | 특정 예시에만 맞는 좁은 규칙보다, 원리를 설명하여 다양한 입력에 대응할 수 있게 한다. 오버피팅 금지. |
| **반복 코드는 번들링** | 테스트 실행에서 에이전트들이 공통으로 작성하는 스크립트가 발견되면 `scripts/`에 미리 번들링한다. |
| **명령형으로 작성** | "~한다", "~하라" 형태의 명령형/지시형 어조를 사용한다. |

#### 4-4. Progressive Disclosure (단계적 정보 공개)

스킬은 3단계 로딩 시스템으로 컨텍스트를 관리한다:

| 단계 | 로딩 시점 | 크기 목표 |
|------|----------|----------|
| **Metadata** (name + description) | 항상 컨텍스트에 존재 | ~100단어 |
| **SKILL.md 본문** | 스킬 트리거 시 | <500줄 |
| **references/** | 필요할 때만 | 무제한 (스크립트는 로딩 없이 실행 가능) |

**크기 관리 규칙:**
- SKILL.md가 500줄에 근접하면 세부 내용을 references/로 분리하고, 본문에 "언제 이 파일을 읽으라"는 포인터를 남긴다
- 300줄 이상의 reference 파일에는 상단에 **목차(ToC)**를 포함한다
- 도메인/프레임워크별 변형이 있으면 references/ 하위에 도메인별로 분리하여, 관련 파일만 로드한다

```
cloud-deploy/
├── SKILL.md (워크플로우 + 선택 가이드)
└── references/
    ├── aws.md    ← AWS 선택 시만 로드
    ├── gcp.md
    └── azure.md
```

#### 4-5. 스킬-에이전트 연결 원칙

- 에이전트 1개 ↔ 스킬 1~N개 (1:1 또는 1:다)
- 여러 에이전트가 공유하는 스킬도 가능
- 스킬은 "어떻게 하는가"를 담고, 에이전트는 "누가 하는가"를 담는다

> 상세 작성 패턴, 예시, 데이터 스키마 표준은 `references/skill-writing-guide.md` 참조.

### Phase 5: 통합 및 오케스트레이션

오케스트레이터는 `{domain}-orchestrator` skill. Claude 템플릿: `references/orchestrator-template.md`. **Cursor/Codex/Gemini:** `references/platform-orchestration.md` + `references/component-templates.md`의 플랫폼별 orchestrator 섹션 사용. Cursor에 TeamCreate/SendMessage 금지.

**모든 Pipeline/Fan-out 오케스트레이터에 문서 Phase 필수** — 마지막 Phase에서 `sync-docs` / `doc-writer` 호출. 단독 Expert Pool만 쓰는 하네스도 `sync-docs` skill은 포함.

Phase 2-1 실행 모드에 따라:

#### 5-0. 오케스트레이터 패턴 (모드별)

**에이전트 팀 패턴 (기본 · Claude Code 전용):**
> ⚠️ **사전 요구:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 환경변수가 설정되어 있어야 TeamCreate/SendMessage가 활성화된다.

오케스트레이터가 `TeamCreate`로 팀을 구성하고, `TaskCreate`로 작업을 할당한다. 팀원들은 `SendMessage`로 직접 통신하며 자체 조율한다. 리더(오케스트레이터)는 진행 상황을 모니터링하고 결과를 종합한다.

```
[오케스트레이터/리더]
    ├── TeamCreate(team_name, members)
    ├── TaskCreate(tasks with dependencies)
    ├── 팀원들이 자체 조율 (SendMessage)
    ├── 결과 수집 및 종합
    └── 팀 정리
```

**서브 에이전트 패턴 (대안):**
오케스트레이터가 `Agent` 도구로 서브 에이전트를 직접 호출한다. 병렬 실행은 `run_in_background: true`, 결과는 메인에게만 반환된다. 팀 통신이 불필요하고 오버헤드를 줄이고 싶을 때 사용.

```
[오케스트레이터]
    ├── Agent(agent-1, run_in_background=true)
    ├── Agent(agent-2, run_in_background=true)
    ├── 결과 대기 및 수집
    └── 통합 산출물 생성
```

**하이브리드 패턴:**
Phase마다 다른 모드를 섞어 구성한다. 자주 쓰이는 조합:
- **병렬 수집(서브) → 합의 통합(팀)**: Phase 2에서 서브 에이전트로 독립 자료를 병렬 수집 → Phase 3에서 팀을 만들어 토론·합의 기반 통합
- **팀 생성(팀) → 검증(서브)**: Phase 2에서 팀이 초안 생성 → Phase 3에서 단일 서브 에이전트가 독립 검증
- **Phase 간 팀 재구성**: 각 Phase마다 `TeamDelete` 후 새 `TeamCreate`, 사이에 서브 에이전트 호출 삽입

하이브리드 선택 시 오케스트레이터의 각 Phase 섹션 상단에 해당 Phase의 실행 모드를 명시한다 (예: `**실행 모드:** 에이전트 팀`).

#### 5-1. 데이터 전달 프로토콜

오케스트레이터 내에 에이전트 간 데이터 전달 방식을 명시한다:

| 전략 | 방식 | 적용 모드 | 적합한 경우 |
|------|------|----------|-----------|
| **메시지 기반** | `SendMessage`로 팀원 간 직접 통신 | 팀 | 실시간 조율, 피드백 교환, 가벼운 상태 전달 |
| **태스크 기반** | `TaskCreate`/`TaskUpdate`로 작업 상태 공유 | 팀 | 진행상황 추적, 의존 관계 관리, 작업 자체 요청 |
| **파일 기반** | 약속된 경로에 파일을 쓰고 읽음 | 팀 + 서브 | 대용량 데이터, 구조화된 산출물, 감사 추적 필요 |
| **반환값 기반** | `Agent` 도구의 반환 메시지 | 서브 | 서브 에이전트 결과를 메인이 직접 수집 |

**권장 조합 (팀 모드):** 태스크 기반(조율) + 파일 기반(산출물) + 메시지 기반(실시간 소통)
**권장 조합 (서브 모드):** 반환값 기반(결과 수집) + 파일 기반(대용량 산출물)
**하이브리드:** 각 Phase의 실행 모드에 맞춰 해당 조합 적용

파일 기반 handoff:
- **Claude:** `_workspace/` — `{phase}_{agent}_{artifact}.md`
- **Cursor/Gemini/Codex:** `artifacts/` — `00-input.md`, `02_*.md`, `task-board.md`, `final-report.md`, `handoff.md`

#### 5-2. 에러 핸들링

오케스트레이터 내에 에러 처리 방침을 포함한다. 핵심 원칙: 1회 재시도 후 재실패 시 해당 결과 없이 진행(보고서에 누락 명시), 상충 데이터는 삭제하지 않고 출처 병기.

> 에러 유형별 전략표와 구현 상세는 `references/orchestrator-template.md`의 "에러 핸들링" 참조.

#### 5-3. 팀 크기 가이드라인

| 작업 규모 | 권장 팀원 수 | 팀원당 작업 수 |
|----------|------------|--------------|
| 소규모 (5~10개 작업) | 2~3명 | 3~5개 |
| 중규모 (10~20개 작업) | 3~5명 | 4~6개 |
| 대규모 (20개+ 작업) | 5~7명 | 4~5개 |

> 팀원이 많을수록 조율 오버헤드가 커진다. 3명의 집중된 팀원이 5명의 산만한 팀원보다 낫다.

#### 5-4. Entry file 포인터 등록

| 플랫폼 | 파일 | 템플릿 |
|--------|------|--------|
| Claude | `CLAUDE.md` | 트리거 + 변경 이력 |
| Cursor | `AGENTS.md` | 트리거 + 변경 이력 |
| Gemini | `GEMINI.md` | 트리거 + `/command` (선택) |
| Codex | `AGENTS.md` | 트리거 + spawn 힌트 |

에이전트/스킬 목록·디렉터리 구조는 entry file에 **넣지 않는다** (중복·drift 원인).

**Entry 템플릿:**

````markdown
## 하네스: {도메인명}

**목표:** {하네스의 핵심 목표 한 줄}

**트리거:** {도메인} 관련 작업 요청 시 `{orchestrator-skill-name}` 스킬을 사용하라. 단순 질문은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| {YYYY-MM-DD} | 초기 구성 | 전체 | - |
````

**Entry file에 넣지 않는 것:** 에이전트 목록, 스킬 목록, 디렉터리 트리 — 파일 시스템·orchestrator skill에서 관리.

#### 5-5. 후속 작업 지원

Handoff 디렉터리 확인 (Phase 0):
- **Claude:** `_workspace/`
- **Cursor/Gemini/Codex:** `artifacts/`

분기: 없음→초기 / 부분 수정→해당 agent만 / 새 입력→archive 후 재시작.

**1. 오케스트레이터 description에 후속 키워드 포함:**
초기 생성 키워드만으로는 후속 요청이 트리거되지 않는다. description에 반드시 포함할 후속 표현:
- "다시 실행", "재실행", "업데이트", "수정", "보완"
- "{도메인}의 {부분작업}만 다시"
- "이전 결과 기반으로", "결과 개선"

**2. 오케스트레이터 Phase 0/1 컨텍스트 확인:**
- handoff 존재 + 부분 수정 → 해당 agent만 재호출
- handoff 존재 + 새 입력 → archive 후 재시작
- handoff 없음 → 초기 실행

**3. 에이전트 정의에 재호출 지침 포함:**
각 에이전트 `.md` 파일에 "이전 산출물이 있을 때의 행동"을 명시한다:
- 이전 결과 파일이 존재하면 읽고 개선점을 반영
- 사용자 피드백이 주어지면 해당 부분만 수정

> 오케스트레이터 템플릿의 "Phase 0: 컨텍스트 확인" 섹션 참조: `references/orchestrator-template.md`

### Phase 6: 검증 및 테스트

생성된 하네스를 검증한다. 상세 테스트 방법론은 `references/skill-testing-guide.md` 참조.

#### 6-1. 구조 검증

- 모든 에이전트 파일이 올바른 위치에 있는지 확인
- 스킬의 frontmatter(name, description) 검증
- 에이전트 간 참조 일관성 확인
- 커맨드가 생성되지 않았는지 확인

#### 6-2. 실행 모드별 검증

- **에이전트 팀**: 팀원 간 통신 경로, 작업 의존성, 팀 크기 적정성 확인
- **서브 에이전트**: 각 에이전트의 입출력 연결, `run_in_background` 설정, 반환값 수집 로직 확인
- **하이브리드**: 각 Phase의 실행 모드가 오케스트레이터에 명시되었는지, Phase 경계에서 데이터 전달이 끊기지 않는지 확인 (팀 → 서브 전환 시 팀의 산출물이 서브의 입력으로 연결되는지)

#### 6-3. 스킬 실행 테스트

각 스킬에 현실적인 테스트 프롬프트 2~3개를 작성하고, With-skill vs Without-skill 병렬 비교 실행 후 정성적+정량적으로 평가한다. 문제 발견 시 피드백을 **일반화**하여 수정(특정 예시에만 맞는 좁은 수정 금지) → 재테스트 반복. 공통 반복 코드는 `scripts/`에 번들링한다.

> 상세 방법론(프롬프트 작성, assertion 채점, 에이전트 활용): `references/skill-testing-guide.md`

#### 6-4. 트리거 검증

- **Should-trigger** 쿼리 8~10개 (공식/캐주얼, 명시/암시적 표현 포함)
- **Should-NOT-trigger** 쿼리 8~10개 — 키워드는 유사하지만 다른 스킬이 적합한 **경계 모호 쿼리** ("피보나치 작성"처럼 무관한 쿼리는 테스트 가치 없음)
- 기존 스킬과의 트리거 충돌 확인

#### 6-5. 드라이런 테스트

- Phase 순서 논리성, 데이터 전달 경로 dead link, 에이전트 입출력 매칭, 에러 폴백 경로 확인

#### 6-6. 테스트 시나리오 작성

- 오케스트레이터 스킬에 `## 테스트 시나리오` 섹션 추가 (정상 흐름 1개 + 에러 흐름 1개 이상)

### Phase 7: 하네스 진화

하네스는 한 번 만들고 끝나는 정적 산출물이 아니다. 사용자 피드백에 따라 계속 진화하는 시스템이다.

#### 7-1. 실행 후 피드백 수집

매 하네스 실행 완료 후 피드백 기회를 제공한다 ("결과 개선할 부분이 있나요?", "워크플로우 바꾸고 싶은 점이 있나요?"). 피드백이 없으면 넘어간다. 강요하지 않되, 반드시 기회는 제공한다.

#### 7-2. 피드백 반영 경로

피드백 유형에 따라 수정 대상이 다르다:

| 피드백 유형 | 수정 대상 | 예시 |
|-----------|----------|------|
| 결과물 품질 | 해당 에이전트의 스킬 | "분석이 너무 피상적" → 스킬에 깊이 기준 추가 |
| 에이전트 역할 | 에이전트 정의 `.md` | "보안 검토도 필요" → 새 에이전트 추가 |
| 워크플로우 순서 | 오케스트레이터 스킬 | "검증을 먼저 해야" → Phase 순서 변경 |
| 팀 구성 | 오케스트레이터 + 에이전트 | "이 둘은 합쳐도 될 듯" → 에이전트 병합 |
| 트리거 누락 | 스킬 description | "이 표현으로 하면 작동 안 함" → description 확장 |

#### 7-3. 변경 이력

모든 변경은 **entry file 변경 이력**에 기록 (CLAUDE.md / AGENTS.md / GEMINI.md).

```markdown
**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-05 | 초기 구성 | 전체 | - |
| 2026-04-07 | QA 에이전트 추가 | agents/qa.md | 산출물 품질 검증 부족 피드백 |
| 2026-04-10 | 톤 가이드 추가 | skills/content-creator | "너무 딱딱하다" 피드백 |
```

이 이력을 통해 하네스가 어떤 방향으로 진화했는지 추적하고, 퇴행(regression)을 방지한다.

#### 7-4. 진화 트리거

사용자가 명시적으로 "하네스 수정해줘"라고 할 때만이 아니라, 다음 상황에서도 진화를 제안한다:
- 같은 유형의 피드백이 2회 이상 반복될 때
- 에이전트가 반복적으로 실패하는 패턴이 발견될 때
- 사용자가 오케스트레이터를 우회하여 수동으로 작업하는 것이 관찰될 때

#### 7-5. 운영/유지보수 워크플로우

기존 하네스의 점검·수정·동기화를 체계적으로 수행한다. Phase 0에서 "운영/유지보수" 분기로 진입했을 때 이 워크플로우를 따른다.

**Step 1: 현황 감사** — 대상 플랫폼 agents/, skills/, entry file drift 확인
**Step 2: 점진적 추가/수정**
**Step 3: entry file 변경 이력 갱신**
**Step 4: 변경 검증** (Phase 6 기준)

## 산출물 체크리스트

**공통**
- [ ] 대상 플랫폼 확정 + `references/platform-paths.md` 경로 준수
- [ ] **`doc-writer` agent + `sync-docs` skill (필수)**
- [ ] orchestrator skill 1개 — **마지막 Phase: 문서 동기화 (sync-docs)**
- [ ] work skill(s) + description pushy + 후속 키워드
- [ ] `.agents/skills/` 공통 skill (멀티플랫폼 시)
- [ ] entry file 포인터 + 변경 이력 (`references/platform-rules.md` 형식 준수)
- [ ] handoff 디렉터리 (`_workspace/` 또는 `artifacts/`)
- [ ] commands 폴더: 단순 단축키만 생성 — 다단계 워크플로는 skill 우선 (`references/platform-commands.md`)
- [ ] 트리거 검증 + 테스트 프롬프트 2~3개

**Claude Code**
- [ ] `.claude/agents/*.md` + `.claude/skills/` ( **`doc-writer` + `sync-docs` 포함** )
- [ ] TeamCreate/SendMessage 사용 시 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 환경변수 설정 확인
- [ ] TeamCreate/SendMessage 또는 Agent (orchestrator에 명시)
- [ ] `CLAUDE.md` 포인터

**Cursor**
- [ ] `.cursor/agents/*.md` + `.cursor/skills/` ( **`doc-writer` 포함** )
- [ ] `.cursor/rules/*.mdc` — `alwaysApply`/`globs`/Intelligent/Manual 방식 적용 (`references/platform-rules.md`) + `AGENTS.md`
- [ ] `.cursor/hooks.json` — guard-shell + **`check-doc-sync.sh` (afterFileEdit, 필수)**
- [ ] `artifacts/` + Task 전 Read(agent)→prompt
- [ ] TeamCreate/SendMessage **미사용**

**Gemini CLI**
- [ ] `.gemini/skills/` + `GEMINI.md` ( **`sync-docs` 필수**; `doc-writer`는 독립 에이전트 파일 없이 skill role로 구현 — `references/team-examples.md` 예시 6 참조 )
- [ ] `.gemini/commands/*.toml` — `!{shell}` 주입으로 실시간 컨텍스트 삽입 활용 (`references/platform-commands.md`)
- [ ] `artifacts/`

**Codex**
- [ ] `.codex/agents/*.toml` + `.agents/skills/` ( **`doc-writer.toml` + `sync-docs` 필수** )
- [ ] `AGENTS.md` + `.codex/config.toml` (max_threads/depth)
- [ ] orchestrator에 **명시적 spawn** 지시
- [ ] `artifacts/`

## 참고

- **플랫폼 경로:** `references/platform-paths.md`
- **플랫폼 오케스트레이션:** `references/platform-orchestration.md`
- **플랫폼 구성요소 + SubAgent 안티패턴:** `references/platform-components.md`
- **플랫폼 템플릿:** `references/component-templates.md`
- **훅 설계 (이벤트·가드레일·컨텍스트 주입·예시):** `references/platform-hooks.md`
- **Rules 설계 (CLAUDE.md·AGENTS.md·GEMINI.md·Cursor .mdc):** `references/platform-rules.md`
- **Commands 설계 (Slash Commands·Gemini `!{shell}`·Codex 자동트리거):** `references/platform-commands.md`
- **Plugin / Extension 패키징·배포:** `references/platform-plugin.md`
- 하네스 패턴: `references/agent-design-patterns.md`
- 예시: `references/team-examples.md`
- Claude orchestrator: `references/orchestrator-template.md`
- 스킬 작성 (Scripts §10 포함): `references/skill-writing-guide.md`
- 스킬 테스트: `references/skill-testing-guide.md`
- QA 에이전트: `references/qa-agent-guide.md`
