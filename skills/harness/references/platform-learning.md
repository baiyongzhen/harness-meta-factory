# Platform Learning — Continuous Learning & Token Optimization

> Harness가 생성하는 **continuous-learning** 모듈의 플랫폼별 설계 가이드.
> 사용자 요청에 "learning 포함" / "학습 기능" / "continuous learning"이 있을 때 이 파일을 읽는다.

## 개요

| 레이어 | 역할 |
|--------|------|
| **observe.py** (hook 스크립트) | 매 tool 이벤트를 `$HARNESS_LEARNING_DIR` (기본: `~/.local/share/harness-meta-factory/`) JSONL에 기록 |
| **continuous-learning** (skill) | AI가 observations를 읽고 atomic instinct YAML을 생성·갱신 |
| **instinct-cli.py** (관리 스크립트) | 파일 관리 (status / prune / export) |
| **compact-suggest.py** (hook 스크립트) | 컨텍스트 토큰 수 감시 → compact 타이밍 제안 |

---

## 플랫폼별 Hook 이벤트 매핑

| 이벤트 성격 | Claude Code | Cursor | Gemini CLI | Codex |
|------------|-------------|--------|------------|-------|
| 모든 tool 실행 전 | `PreToolUse` | 없음 ⚠️ | `BeforeTool` | `PreToolUse` |
| 모든 tool 실행 후 | `PostToolUse` | 없음 ⚠️ | `AfterTool` | `PostToolUse` |
| 파일 편집 후 | PostToolUse (Write/Edit) | `afterFileEdit` | AfterTool | PostToolUse |
| 셸 실행 전 | PreToolUse (Bash) | `beforeShellExecution` | BeforeTool | PreToolUse (Bash) |
| 서브에이전트 종료 | — | `subagentStop` | — | `SubagentStop` |
| 세션 종료 | `Stop` | `stop` | `SessionEnd` | `Stop` |
| 컨텍스트 크기 정보 | PreToolUse payload | 없음 | BeforeTool payload | PreToolUse payload |

> **Cursor 주의:** 전 tool에 대한 PreToolUse/PostToolUse가 없다.
> `afterFileEdit` + `subagentStop` + `stop`으로 부분 관찰만 가능.
> → 세션 종료 시 handoff.md에 학습 요약 기록하는 방식으로 보완.

---

## 저장 경로

| 경로 | 우선순위 | 설명 |
|------|---------|------|
| `$HARNESS_LEARNING_DIR` | 1 | 환경변수로 명시 시 우선 |
| `$XDG_DATA_HOME/harness-meta-factory` | 2 | POSIX 표준 data dir |
| `~/.local/share/harness-meta-factory` | 3 | XDG 기본값 |

> `.claude/` 내부는 **사용하지 않는다** — 런타임의 민감 경로 가드에 걸릴 수 있다.

### 디렉터리 구조

```
$HARNESS_LEARNING_DIR/          (기본: ~/.local/share/harness-meta-factory/)
├── projects.json               # hash → name/path 레지스트리
├── observations.jsonl          # 프로젝트 감지 실패 시 글로벌 fallback
├── instincts/personal/         # 글로벌 instinct
├── evolved/                    # 진화된 skill/agent/command
└── projects/
    └── {12-char-hash}/
        ├── project.json        # id, name, root, remote
        ├── observations.jsonl
        └── instincts/personal/ # 프로젝트 scoped instinct
```

### 프로젝트 ID 생성

```python
# 우선순위: env var > git remote URL > git repo root > "global"
import hashlib, subprocess, os

def get_project_id():
    if env := os.environ.get("HARNESS_PROJECT_ID"):
        return env
    for cmd in [
        ["git", "remote", "get-url", "origin"],
        ["git", "rev-parse", "--show-toplevel"],
    ]:
        try:
            val = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
            if val:
                return hashlib.sha256(val.encode()).hexdigest()[:12]
        except Exception:
            pass
    return "global"
```

---

## 플랫폼별 Hook 등록

### Claude Code — `.claude/hooks/hooks.json`

```json
{
  "hooks": {
    "PreToolUse":  [{"matcher": "*", "hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py pre"}]}],
    "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py post"}]}],
    "Stop":        [{"matcher": "*", "hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop"}]}]
  }
}
```

compact-suggest는 PreToolUse (Edit/Write)에 추가:
```json
{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/compact-suggest.py"}]}
```

### Cursor — `.cursor/hooks.json`

```json
{
  "hooks": {
    "afterFileEdit":        [{"command": "python3 .agents/skills/continuous-learning/scripts/observe.py post 2>/dev/null || true"}],
    "subagentStop":         [{"command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop 2>/dev/null || true"}],
    "stop":                 [{"command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop 2>/dev/null || true"}],
    "beforeShellExecution": [{"command": "python3 .agents/skills/continuous-learning/scripts/observe.py pre 2>/dev/null || true"}]
  }
}
```

> Cursor는 full tool observation 불가. `afterFileEdit` + `stop` 기반 부분 학습.

### Gemini CLI — `.gemini/settings.json`

```json
{
  "hooks": {
    "BeforeTool": {"command": "python3 .agents/skills/continuous-learning/scripts/observe.py pre"},
    "AfterTool":  {"command": "python3 .agents/skills/continuous-learning/scripts/observe.py post"},
    "SessionEnd": {"command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop"}
  }
}
```

### Codex — `.codex/hooks.json`

```json
{
  "hooks": {
    "PreToolUse":  [{"matcher": "*", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py pre"}],
    "PostToolUse": [{"matcher": "*", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py post"}],
    "Stop":        [{"command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop"}]
  }
}
```

---

## Instinct 모델

Instinct = 한 번에 하나의 패턴·행동을 기술하는 원자 단위.

```yaml
# .harness-learning/projects/{hash}/instincts/personal/prefer-functional-style.yaml
---
id: prefer-functional-style
trigger: "when writing new Python functions"
confidence: 0.7
domain: code-style
scope: project          # project | global
project_id: a1b2c3d4e5f6
project_name: my-fastapi
created: 2026-06-21T06:00:00Z
last_seen: 2026-06-21T08:00:00Z
evidence:
  - "Observed 3 functional pattern preferences"
  - "User corrected class-based approach on 2026-06-21"
---

# Prefer Functional Style

## Action
Use functional patterns over classes when appropriate.
```

### Confidence 규칙

| 점수 | 의미 | 세션 주입 |
|------|------|-----------|
| 0.3 | 잠정적 — 1회 관찰 | 주입 안 함 |
| 0.5 | 보통 — 3회 이상 | rules에만 |
| 0.7 | 강함 — 반복 확인 | **세션 컨텍스트에 주입** |
| 0.9 | 거의 확실 | 핵심 동작으로 고정 |

> **토큰 최적화:** confidence ≥ 0.7 instinct만 세션 컨텍스트에 주입.
> 낮은 confidence는 파일에만 저장, 필요 시 on-demand로 로드.

### Scope 결정

| 패턴 유형 | Scope |
|----------|-------|
| 언어·프레임워크 컨벤션 | project |
| 파일 구조 선호 | project |
| 보안·범용 best practice | global |
| git 워크플로우 | global |
| 도구 사용 패턴 | global |

**Auto-promote 기준:** 동일 id가 2개 이상 프로젝트에서 confidence ≥ 0.8 → global로 승격.

---

## Token Optimization — Strategic Compact

### 언제 compact 제안하는가

| Phase 전환 | Compact? |
|-----------|----------|
| 탐색 → 계획 | Yes |
| 계획 → 구현 | Yes (계획이 파일에 저장된 후) |
| 디버깅 → 다음 기능 | Yes |
| 구현 도중 | No |
| 실패한 접근 후 | Yes |

### compact-suggest 동작

- PreToolUse (Edit/Write) 시 hook payload의 `usage` 필드에서 토큰 수 추출
- 기본 임계값: 150,000 tokens (환경변수 `COMPACT_THRESHOLD`로 조정)
- 임계값 초과 시 `additionalContext`에 compact 권고 메시지 출력
- 60,000 토큰마다 반복 (환경변수 `COMPACT_INTERVAL`)

> Cursor는 hook payload에 토큰 정보가 없어 compact-suggest 미지원.
> 대신 orchestrator `handoff.md`에 "세션 컨텍스트 요약" 섹션 기록을 권장.

---

## Cursor 한계 보완 전략

Cursor에서 full tool observation 없이 학습하는 방법:

1. **orchestrator handoff.md 활용** — 각 세션 종료 시 "이번 세션에서 발견한 패턴 3가지"를 handoff.md에 기록
2. **stop hook** — 세션 종료 시 `observe.py stop` 실행, handoff 내용을 JSONL에 append
3. **manual evolve** — 사용자가 `/continuous-learning` 트리거 시 AI가 직접 패턴 추출

이 방식으로 "파일 변경·서브에이전트 완료·세션 종료" 기준 학습 가능.

---

## 플랫폼별 관찰 완성도

| 플랫폼 | 관찰 완성도 | 비고 |
|--------|------------|------|
| Claude Code | **~100%** | PreToolUse/PostToolUse 전 이벤트 |
| Codex | **~100%** | 동일 |
| Gemini CLI | **~90%** | BeforeTool/AfterTool |
| Cursor | **~40%** | afterFileEdit + stop만 |

상세 스크립트·템플릿: `references/continuous-learning-templates.md`
