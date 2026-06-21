# Continuous Learning Templates

> Harness가 "learning 포함" 요청 시 생성하는 파일들의 완전한 템플릿.
> 플랫폼별 hook 등록은 `references/platform-learning.md` 참조.

---

## 생성 디렉터리 트리

```
{project-root}/
└── .agents/
    └── skills/
        └── continuous-learning/
            ├── SKILL.md
            ├── config.json
            └── scripts/
                ├── observe.py
                ├── instinct-cli.py
                └── compact-suggest.py
```

> 플랫폼별 경로 심링크:
> - Claude: `.claude/skills/continuous-learning/` → 동일 내용
> - Cursor: `.cursor/skills/continuous-learning/` → 동일 내용
> - Gemini: `.gemini/skills/continuous-learning/` → 동일 내용
> - Codex: `.agents/skills/` 그대로 사용

---

## continuous-learning/SKILL.md (생성 템플릿)

```markdown
---
name: continuous-learning
description: >
  세션 관찰에서 instinct를 추출·갱신한다. 트리거: "/continuous-learning", "학습",
  "evolve instincts", "instinct 보기", "학습 현황", "내가 배운 것", "compact 제안",
  "토큰 최적화". 세션 후 정기 실행으로 AI 동작을 점진적으로 개선.
---

# Continuous Learning

## 역할
세션의 tool 사용·사용자 수정·반복 패턴을 분석해 atomic instinct YAML로 저장한다.
confidence ≥ 0.7 instinct만 세션 컨텍스트에 주입 (토큰 최적화).

## 저장 경로
- 프로젝트: `$HARNESS_LEARNING_DIR/projects/{12-char-hash}/instincts/personal/`
- 글로벌: `$HARNESS_LEARNING_DIR/instincts/personal/`
- 기본 `HARNESS_LEARNING_DIR`: `~/.local/share/harness-meta-factory/`

## Phase 0: 관찰 데이터 로드
`instinct-cli.py status` 또는 직접 Read로 `observations.jsonl` 최근 200줄 로드.
없으면 "관찰 데이터 없음 — 먼저 세션을 진행하세요" 안내.

## Phase 1: 패턴 추출
observations에서 다음을 찾는다:
- **사용자 수정** — AI 출력을 사용자가 즉시 수정 → confidence +0.2 신호
- **반복 시퀀스** — 동일 tool 패턴 3회 이상 등장
- **에러→픽스 사이클** — Bash 실패 후 성공 패턴
- **도구 선호** — 같은 작업에 특정 tool 일관 선택

## Phase 2: Instinct 파일 생성·갱신
각 패턴마다:
1. ID 생성 (kebab-case, 영문)
2. 기존 파일 있으면 confidence·evidence 갱신
3. 없으면 신규 생성 (confidence 시작: 0.3)

**Instinct 파일 형식:**
```yaml
---
id: {kebab-id}
trigger: "when {context}"
confidence: 0.5
domain: {code-style|testing|git|security|architecture}
scope: {project|global}
project_id: {12-char-hash}
created: {ISO8601}
last_seen: {ISO8601}
evidence:
  - "{관찰 근거}"
---
# {Title}
## Action
{한 문장으로: 무엇을 어떻게}
```

## Phase 3: 승격 검토
동일 id가 2개 이상 프로젝트에서 confidence ≥ 0.8 → global instinct로 승격 제안.

## Phase 4: 결과 리포트
- 신규 instinct N개
- 갱신 instinct N개 (confidence 변화)
- 승격 후보 N개
- 현재 세션 주입 가능(≥0.7) instinct 목록

## Token Optimization
- `config.json`의 `inject_threshold` (기본 0.7) 이상만 세션에 주입
- 나머지는 파일로 관리, 요청 시 on-demand 로드
- compact 타이밍: Phase 전환(탐색→계획, 계획→구현) 시 제안
```

---

## config.json (생성 템플릿)

```json
{
  "version": "1.0",
  "storage": {
    "base_dir_env": "HARNESS_LEARNING_DIR",
    "default_base": "~/.local/share/harness-meta-factory",
    "project_id_env": "HARNESS_PROJECT_ID"
  },
  "observations": {
    "max_lines_per_session": 2000,
    "retention_days": 90
  },
  "instincts": {
    "inject_threshold": 0.7,
    "promote_threshold": 0.8,
    "promote_min_projects": 2
  },
  "compact": {
    "threshold_tokens": 150000,
    "repeat_interval_tokens": 60000
  }
}
```

---

## observe.py (생성 템플릿 — 전체)

```python
#!/usr/bin/env python3
"""Harness continuous-learning observer hook.
Reads JSON event from stdin and appends to observations.jsonl.
Compatible: Claude Code, Codex (PreToolUse/PostToolUse/Stop),
            Cursor (afterFileEdit/subagentStop/stop),
            Gemini CLI (BeforeTool/AfterTool/SessionEnd).

Usage: python3 observe.py [pre|post|stop]
"""
import json, sys, os, hashlib, subprocess
from pathlib import Path
from datetime import datetime, timezone


def get_project_id() -> str:
    if pid := os.environ.get("HARNESS_PROJECT_ID"):
        return pid
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


def get_data_dir() -> Path:
    if d := os.environ.get("HARNESS_LEARNING_DIR"):
        return Path(d)
    xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "harness-meta-factory"


def load_config(base: Path) -> dict:
    cfg_path = Path(__file__).parent.parent / "config.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> None:
    phase = sys.argv[1] if len(sys.argv) > 1 else "unknown"

    raw = sys.stdin.read().strip()
    event: dict = {}
    if raw:
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            event = {"raw": raw[:512]}

    project_id = get_project_id()
    data_dir = get_data_dir()
    cfg = load_config(data_dir)
    max_lines = cfg.get("observations", {}).get("max_lines_per_session", 2000)

    if project_id == "global":
        obs_dir = data_dir / "observations"
    else:
        obs_dir = data_dir / "projects" / project_id / "observations"

    obs_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "phase": phase,
        "hook_event": os.environ.get("HOOK_EVENT", ""),
        "tool": event.get("tool_name") or event.get("tool") or "",
        "result_ok": event.get("success") if "success" in event else None,
        "event": event,
    }

    obs_file = obs_dir / "observations.jsonl"
    with open(obs_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Rolling limit: trim if over max_lines
    try:
        lines = obs_file.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_lines:
            obs_file.write_text(
                "\n".join(lines[-max_lines:]) + "\n", encoding="utf-8"
            )
    except Exception:
        pass


if __name__ == "__main__":
    main()
```

---

## instinct-cli.py (생성 템플릿 — 전체)

```python
#!/usr/bin/env python3
"""Harness instinct CLI.
Commands: status | prune [--days N] | export [output.json]

Usage:
  python3 instinct-cli.py status
  python3 instinct-cli.py prune --days 30
  python3 instinct-cli.py export instincts.json
"""
import argparse, json, os, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta


def get_data_dir() -> Path:
    if d := os.environ.get("HARNESS_LEARNING_DIR"):
        return Path(d)
    xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "harness-meta-factory"


def iter_instinct_files(data_dir: Path):
    for f in sorted((data_dir / "instincts" / "personal").glob("*.yaml")):
        yield f, "global"
    for proj_dir in sorted(data_dir.glob("projects/*/instincts/personal")):
        project_id = proj_dir.parts[-3]
        for f in sorted(proj_dir.glob("*.yaml")):
            yield f, project_id


def parse_confidence(text: str) -> float:
    for line in text.splitlines():
        if line.strip().startswith("confidence:"):
            try:
                return float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    return 0.0


def cmd_status(args) -> None:
    data_dir = get_data_dir()
    items = list(iter_instinct_files(data_dir))
    if not items:
        print("No instincts found.")
        print("Run /continuous-learning after a session to evolve observations.")
        return

    current_scope = None
    for f, scope in items:
        if scope != current_scope:
            label = "global" if scope == "global" else f"project:{scope}"
            print(f"\n[{label}]")
            current_scope = scope
        conf = parse_confidence(f.read_text(encoding="utf-8"))
        inject = "*" if conf >= 0.7 else " "
        print(f"  {inject} {f.stem:<45} confidence={conf:.1f}")

    total = len(items)
    inject_count = sum(1 for f, _ in items if parse_confidence(f.read_text(encoding="utf-8")) >= 0.7)
    print(f"\nTotal: {total} instincts  |  Injected (>=0.7): {inject_count}")


def cmd_prune(args) -> None:
    data_dir = get_data_dir()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    pruned = 0

    for obs_file in sorted(data_dir.rglob("observations.jsonl")):
        try:
            lines = obs_file.read_text(encoding="utf-8").splitlines()
            kept = []
            for line in lines:
                try:
                    rec = json.loads(line)
                    ts = datetime.fromisoformat(rec.get("ts", "1970-01-01T00:00:00+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        kept.append(line)
                    else:
                        pruned += 1
                except Exception:
                    kept.append(line)
            obs_file.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        except Exception:
            pass

    print(f"Pruned {pruned} observations older than {args.days} days.")


def cmd_export(args) -> None:
    data_dir = get_data_dir()
    result = []
    for f, scope in iter_instinct_files(data_dir):
        result.append({
            "file": str(f),
            "scope": scope,
            "content": f.read_text(encoding="utf-8"),
            "confidence": parse_confidence(f.read_text(encoding="utf-8")),
        })
    out = Path(args.output)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(result)} instincts -> {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Harness instinct manager")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="List instincts with confidence")

    prune_p = sub.add_parser("prune", help="Remove old observations")
    prune_p.add_argument("--days", type=int, default=30,
                         help="Remove observations older than N days (default: 30)")

    exp_p = sub.add_parser("export", help="Export instincts to JSON")
    exp_p.add_argument("output", nargs="?", default="instincts-export.json")

    args = parser.parse_args()
    {
        "status": cmd_status,
        "prune":  cmd_prune,
        "export": cmd_export,
    }.get(args.cmd, lambda _: parser.print_help())(args)


if __name__ == "__main__":
    main()
```

---

## compact-suggest.py (생성 템플릿 — 전체)

```python
#!/usr/bin/env python3
"""Strategic compact suggestion hook.
Reads PreToolUse / PostToolUse payload from stdin.
Extracts context token count and prints additionalContext
when threshold is reached.

Claude Code: outputs {"additionalContext": "..."} → injected into context
Other platforms: outputs plain text suggestion

Environment variables:
  COMPACT_THRESHOLD  (default: 150000)
  COMPACT_INTERVAL   (default: 60000)
"""
import json, os, sys
from pathlib import Path


def load_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8")).get("compact", {})
    except Exception:
        return {}


def extract_tokens(payload: dict) -> int:
    usage = payload.get("usage") or payload.get("context_usage") or {}
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit(0)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    cfg = load_config()
    threshold = int(os.environ.get("COMPACT_THRESHOLD", cfg.get("threshold_tokens", 150000)))
    interval  = int(os.environ.get("COMPACT_INTERVAL",  cfg.get("repeat_interval_tokens", 60000)))

    tokens = extract_tokens(payload)
    if tokens < threshold:
        sys.exit(0)

    overage   = tokens - threshold
    intervals = overage // interval
    level     = "threshold reached" if intervals == 0 else f"+{intervals} interval(s) over threshold"

    message = (
        f"[compact-suggest] Context: {tokens:,} tokens ({level}). "
        "Consider /compact at the next logical phase boundary "
        "(e.g. after planning, before implementation, or between features). "
        "See platform-learning.md for compact timing guidelines."
    )

    # Claude Code hook expects JSON output with additionalContext
    try:
        print(json.dumps({"additionalContext": message}))
    except Exception:
        print(message)


if __name__ == "__main__":
    main()
```

---

## 플랫폼별 Hook 등록 (전체 파일 기준)

Harness가 continuous-learning 모듈 추가 시 각 플랫폼 hook 파일에 병합:

### Claude Code — `.claude/hooks/hooks.json` (병합)

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "*",         "hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py pre 2>/dev/null"}]},
      {"matcher": "Edit|Write","hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/compact-suggest.py 2>/dev/null"}]}
    ],
    "PostToolUse": [
      {"matcher": "*", "hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py post 2>/dev/null"}]}
    ],
    "Stop": [
      {"matcher": "*", "hooks": [{"type": "command", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop 2>/dev/null"}]}
    ]
  }
}
```

### Cursor — `.cursor/hooks.json` (병합)

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

### Gemini CLI — `.gemini/settings.json` (병합)

```json
{
  "hooks": {
    "BeforeTool": {"command": "python3 .agents/skills/continuous-learning/scripts/observe.py pre 2>/dev/null"},
    "AfterTool":  {"command": "python3 .agents/skills/continuous-learning/scripts/observe.py post 2>/dev/null"},
    "SessionEnd": {"command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop 2>/dev/null"}
  }
}
```

### Codex — `.codex/hooks.json` (병합)

```json
{
  "hooks": {
    "PreToolUse":  [{"matcher": "*", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py pre 2>/dev/null"}],
    "PostToolUse": [{"matcher": "*", "command": "python3 .agents/skills/continuous-learning/scripts/observe.py post 2>/dev/null"}],
    "Stop":        [{"command": "python3 .agents/skills/continuous-learning/scripts/observe.py stop 2>/dev/null"}]
  }
}
```

---

## 멀티런타임 데이터 격리

동일 머신에서 여러 플랫폼(Claude + Cursor + Codex)이 동시에 돌 때:

| 플랫폼 | HARNESS_PROJECT_ID 확인 |
|--------|------------------------|
| Claude Code | 환경변수 or git remote hash |
| Cursor | 환경변수 or git remote hash |
| Gemini | 환경변수 or git remote hash |
| Codex | 환경변수 or git remote hash |

모든 플랫폼이 같은 `HARNESS_LEARNING_DIR` + 같은 `project_id`를 공유하므로
데이터 중복 없이 **cross-platform instinct 학습**이 가능하다.
(Claude에서 관찰한 패턴을 Cursor에서도 사용 가능)

> 충돌 방지: 파일 쓰기는 단순 JSONL append이므로 동시 쓰기 시 줄 단위 race condition 가능.
> 동시 세션이 빈번하면 `obs_file = obs_dir / f"observations-{platform}.jsonl"` 분리 권장.
