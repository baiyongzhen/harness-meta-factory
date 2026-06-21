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

```
.claude-plugin/
├── plugin.json          # 플러그인 Manifest
├── agents/              # 서브에이전트 정의
│   └── {agent-name}.md
├── skills/              # 스킬
│   └── {skill-name}/
│       └── SKILL.md
├── hooks/               # 이벤트 훅
│   └── {hook-name}.sh
├── commands/            # Slash Commands
│   └── {command}.md
└── bin/                 # 실행 파일 (PATH에 추가됨)
    └── {script-name}.sh
```

### `plugin.json` 구조

```json
{
  "name": "team-harness",
  "version": "1.2.0",
  "description": "백엔드 팀 하네스 플러그인",
  "components": {
    "agents": ["agents/*.md"],
    "skills": ["skills/*/SKILL.md"],
    "hooks": ["hooks/*.sh"],
    "commands": ["commands/*.md"]
  },
  "bin": ["bin/validate.sh"],
  "requires": {
    "claude-code": ">=1.5.0"
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

### 디렉터리 구조

```
cursor-plugin/
├── package.json          # npm 형식 Manifest
├── .cursor/
│   ├── rules/            # .mdc 규칙
│   └── skills/           # 스킬 정의
└── README.md
```

### `package.json`

```json
{
  "name": "@team/cursor-harness",
  "version": "1.0.0",
  "description": "팀 표준 하네스",
  "cursor": {
    "type": "plugin",
    "skills": [".cursor/skills/**/*.md"],
    "rules": [".cursor/rules/**/*.mdc"]
  }
}
```

> Cursor 플러그인은 npm 패키지로 배포하며 `npx @team/cursor-harness install` 형태로 설치.

---

## Gemini CLI — Extensions

### 디렉터리 구조

```
gemini-extension/
├── manifest.json         # Extension Manifest
├── skills/               # 스킬 정의
│   └── {skill}/
│       └── SKILL.md
└── commands/             # Commands (.toml)
    └── {command}.toml
```

### `manifest.json`

```json
{
  "name": "data-pipeline-harness",
  "version": "2.0.0",
  "description": "데이터 파이프라인 팀 Extension",
  "components": {
    "skills": "skills/",
    "commands": "commands/"
  },
  "geminiVersion": ">=1.3.0"
}
```

---

## Codex — `.codex-plugin/`

### 디렉터리 구조

```
.codex-plugin/
├── plugin.json           # Manifest
├── agents/               # 에이전트 정의
│   └── {agent}.md
└── commands/             # Commands
    └── {command}.md
```

### `plugin.json`

```json
{
  "name": "codex-team-harness",
  "version": "1.0.0",
  "description": "팀 Codex 플러그인",
  "components": {
    "agents": ["agents/*.md"],
    "commands": ["commands/*.md"]
  }
}
```

---

## 플랫폼 통합 패키징 전략

멀티플랫폼 프로젝트에서 단일 리포지터리로 모든 플랫폼 플러그인을 관리:

```
plugins/
├── claude/               # .claude-plugin/
│   ├── plugin.json
│   ├── agents/
│   └── skills/
├── cursor/               # Cursor Marketplace
│   ├── package.json
│   └── .cursor/
├── gemini/               # Gemini Extensions
│   ├── manifest.json
│   └── skills/
└── codex/                # .codex-plugin/
    ├── plugin.json
    └── agents/
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

- [ ] `plugin.json` / `package.json` 에 `version`, `description` 명시
- [ ] Claude: `bin/` 실행 파일에 `#!/bin/bash` + `chmod +x` 적용
- [ ] 멀티플랫폼: `plugins/` 디렉터리 구조로 통합 관리
- [ ] Breaking change 시 Major 버전 올림 + CHANGELOG 기록
- [ ] 설치 스크립트(`install.sh`) 또는 npm 지원 명시
- [ ] 선택: Codex `.codex-plugin/agents/` 에 Subagent 포함 가능
