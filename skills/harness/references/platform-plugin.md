# 플랫폼별 Plugin / Extension 설계 가이드

> Plugin(Extension)은 skills·agents·hooks·commands를 하나의 배포 단위로 묶어 버전 관리·공유·설치를 가능하게 함.

## Plugin 개요

| 특성 | 설명 |
|------|------|
| 목적 | 하네스 구성 요소(skills/agents/hooks/commands)를 배포 단위로 패키징 |
| 사용 시점 | 팀 간 공유, 마켓플레이스 배포, 버전 관리가 필요할 때 |
| 기본 구성 | `plugin.json` (Manifest) + 구성 요소 파일들 |

---

## Claude Code — `.claude-plugin/`

### 디렉터리 구조

> `plugin.json`만 `.claude-plugin/` 안에 둔다. 구성 요소 디렉터리(`agents/`, `skills/`, `hooks/`, `commands/`)는 **플러그인 루트**에 배치하며 관례 경로로 자동 발견된다.

```
my-plugin/                  # 플러그인 루트
├── .claude-plugin/
│   └── plugin.json         # 플러그인 Manifest (이 안에는 plugin.json만)
├── agents/                 # 서브에이전트 정의
│   └── {agent-name}.md
├── skills/                 # 스킬
│   └── {skill-name}/
│       └── SKILL.md
├── hooks/                  # 이벤트 훅
│   └── {hook-name}.sh
├── commands/               # Slash Commands
│   └── {command}.md
└── bin/                    # 실행 파일 (PATH에 추가됨)
    └── {script-name}.sh
```

### `plugin.json` 구조

> `components`·`requires` 필드는 **존재하지 않는다.** 구성 요소는 관례 디렉터리에서 자동 발견되며, 다른 플러그인 의존은 `dependencies`로 선언한다. (비관례 경로일 때만 `agents`/`skills`/`hooks`/`commands` 키로 경로를 override.)

```json
{
  "name": "team-harness",
  "version": "1.2.0",
  "description": "백엔드 팀 하네스 플러그인",
  "author": { "name": "backend-team" },
  "dependencies": {
    "shared-harness": ">=1.0.0"
  }
}
```

### `bin/` 디렉터리 — PATH 추가

`bin/`에 있는 실행 파일은 플러그인 설치 시 **PATH에 자동 추가**되어 훅·스킬·서브에이전트에서 직접 호출 가능.

```bash
# bin/validate-schema.sh
#!/bin/bash
# 플러그인 설치 후 어디서나 호출 가능
python scripts/validate-openapi.py "$@"
```

---

## Cursor — Marketplace 형식

> Cursor 플러그인은 **npm 패키지가 아니다.** `.cursor-plugin/plugin.json` manifest를 포함한 **Git 저장소**를 Marketplace에 등록/설치한다. `package.json`의 `cursor` 필드 방식은 사용하지 않는다.

### 디렉터리 구조

```
my-cursor-plugin/          # Git 저장소 루트
├── .cursor-plugin/
│   └── plugin.json        # 플러그인 Manifest
├── .cursor/
│   ├── rules/            # .mdc 규칙
│   ├── agents/           # 서브에이전트
│   └── skills/           # 스킬 정의
└── README.md
```

### `.cursor-plugin/plugin.json`

```json
{
  "name": "cursor-harness",
  "version": "1.0.0",
  "description": "팀 표준 하네스"
}
```

> 배포: Git 저장소를 Marketplace에 등록하면 사용자가 저장소 URL로 설치한다. 구성 요소(`.cursor/skills/`, `.cursor/rules/`, `.cursor/agents/`)는 관례 경로에서 자동 발견.

---

## Gemini CLI — Extensions

### 디렉터리 구조

```
gemini-extension/
├── gemini-extension.json # Extension Manifest (이름 고정)
├── skills/               # 스킬 정의
│   └── {skill}/
│       └── SKILL.md
└── commands/             # Commands (.toml) — commands/ 하위 디렉터리로 자동 발견
    └── {command}.toml
```

### `gemini-extension.json`

> manifest 파일 이름은 **`gemini-extension.json`** (`manifest.json` 아님). `components` 필드는 없으며, commands는 `commands/` 하위 디렉터리에서 자동 발견된다.

```json
{
  "name": "data-pipeline-harness",
  "version": "2.0.0",
  "description": "데이터 파이프라인 팀 Extension"
}
```

---

## Codex — `.codex-plugin/`

### 디렉터리 구조

> Codex 에이전트는 **`.toml`** 형식이다. 플러그인 내부에서 `.md`로 두면 Codex가 에이전트를 인식하지 못한다. 또한 Codex에는 **별도 commands 폴더가 없다** — 반복 워크플로 단축키는 `skills/`(`$skill-name`)로 제공한다.

```
.codex-plugin/
├── plugin.json           # Manifest
├── agents/               # 에이전트 정의
│   └── {agent}.toml
└── skills/               # 단축 워크플로 (commands 폴더 없음)
    └── {skill}/
        └── SKILL.md
```

### `plugin.json`

```json
{
  "name": "codex-team-harness",
  "version": "1.0.0",
  "description": "팀 Codex 플러그인"
}
```

---

## 플랫폼 통합 패키징 전략

멀티플랫폼 프로젝트에서 단일 리포지터리로 모든 플랫폼 플러그인을 관리:

```
plugins/
├── claude/               # 루트에 .claude-plugin/plugin.json + 루트 컴포넌트 디렉터리
│   ├── .claude-plugin/plugin.json
│   ├── agents/
│   └── skills/
├── cursor/               # Cursor Marketplace (Git 저장소)
│   ├── .cursor-plugin/plugin.json
│   └── .cursor/
├── gemini/               # Gemini Extensions
│   ├── gemini-extension.json
│   └── skills/
└── codex/                # .codex-plugin/
    ├── plugin.json
    └── agents/{name}.toml
```

**공유 스킬:** 내용이 동일하면 심볼릭 링크 또는 빌드 스크립트로 중복 제거.

---

## 버전 관리 전략

| 버전 타입 | 변경 내용 | 예시 |
|----------|----------|------|
| **Patch** (x.x.+1) | 버그 수정, 문서 보완 | 1.0.1 |
| **Minor** (x.+1.0) | 신규 스킬/에이전트 추가 | 1.1.0 |
| **Major** (+1.0.0) | 기존 스킬 인터페이스 변경, 필수 설정 추가 | 2.0.0 |

**CHANGELOG 패턴:**

```markdown
## [2.0.0] - 2026-06-21
### Breaking
- `analyze-skill`: `output_format` 파라미터 필수화

## [1.1.0] - 2026-06-01
### Added
- `security-check` 스킬 추가
```

---

## Plugin 체크리스트

- [ ] manifest(`plugin.json` / `.cursor-plugin/plugin.json` / `gemini-extension.json`)에 `version`, `description` 명시
- [ ] Claude: 컴포넌트 디렉터리는 **루트**, `plugin.json`만 `.claude-plugin/`. `bin/` 실행 파일에 `#!/bin/bash` + `chmod +x`
- [ ] Cursor: npm 아님 — Git 저장소 + `.cursor-plugin/plugin.json`로 Marketplace 배포
- [ ] Codex: 에이전트는 `.toml`(`.md` 아님), commands 폴더 없음(skills로 대체)
- [ ] 멀티플랫폼: `plugins/` 디렉터리 구조로 통합 관리
- [ ] Breaking change 시 Major 버전 올림 + CHANGELOG 기록
