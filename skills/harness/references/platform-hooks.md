# 플랫폼별 훅 설계 가이드

> 에이전트 이벤트에 스크립트를 연결하는 확장 프레임워크. 가드레일·컨텍스트 주입·품질 게이트·감사 자동화에 사용.

## 이벤트 비교

| 이벤트 성격 | Claude Code | Cursor | Gemini CLI | Codex |
|------------|-------------|--------|------------|-------|
| 세션 시작 | `SessionStart` | `sessionStart` | `SessionStart` | `SessionStart` |
| 셸 실행 전 | `PreToolUse` (Bash) | `beforeShellExecution` | `BeforeTool` | `PreToolUse` (Bash) |
| 파일 편집 후 | `PostToolUse` (Write/Edit) | `afterFileEdit` | `AfterTool` | `PostToolUse` |
| 서브에이전트 | `PreToolUse` (Task) | `subagentStart/Stop` | — | `SubagentStart/Stop` |
| 세션 종료 | `Stop` | `stop` | `SessionEnd` | `Stop` |

> 위 표는 **대표 이벤트의 부분집합**이다. 각 플랫폼은 추가 이벤트를 지원한다(Cursor ~20종 `preToolUse`/`postToolUse` 등, Gemini `BeforeAgent`/`BeforeModel` 등). 플랫폼 공식 사양에서 전체 목록을 확인할 것.
> Gemini는 서브에이전트 전용 훅 이벤트가 없다(`—`). 서브에이전트 모니터링이 필요하면 **skill 체인 단계별 로깅**(각 단계 시작/종료 시 stdout 기록)으로 대체한다.

## 훅 용도 패턴

| 용도 | 이벤트 | 예시 |
|------|--------|------|
| 가드레일 | PreToolUse (Bash) / beforeShellExecution | `rm -rf`, `git push --force` 차단 |
| 컨텍스트 주입 | SessionStart / sessionStart | git 브랜치·변경 파일 주입 |
| 품질 게이트 | PostToolUse (Write) / afterFileEdit | `.py` 저장 후 lint, 문서 동기화 확인 |
| 감사·알림 | Stop / stop / SessionEnd | 세션 종료 시 Slack 웹훅 |
| 서브에이전트 감시 | SubagentStart/Stop | Task 시작·종료 로깅 |

---

## 플랫폼별 파일 위치 및 규약

### Claude Code

**파일:** `.claude/settings.json`의 `"hooks"` 키 + `.claude/hooks/*.sh`
> ⚠️ `hooks/hooks.json` 경로는 **플러그인 내부에서만** 유효. 일반 프로젝트 훅은 반드시 `settings.json`에 설정.

**exit code 규약:**
- `exit 0` — 성공 (허용)
- `exit 2` + deny JSON — **차단**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": ".claude/hooks/guard-shell.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": ".claude/hooks/lint-after-edit.sh" }]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": ".claude/hooks/notify.sh" }]
      }
    ]
  }
}
```

**guard-shell.sh 패턴:**
```bash
#!/usr/bin/env bash
input=$(cat)
command=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null)
if echo "$command" | grep -qE "git push --force|rm -rf /"; then
  echo '{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"Blocked by harness guard"}}'
  exit 2
fi
echo '{"hookSpecificOutput":{"permissionDecision":"allow"}}'
exit 0
```

---

### Cursor

**파일:** `.cursor/hooks.json` + `.cursor/hooks/*.sh`

**특이사항:**
- `failClosed: true` — 스크립트 실패 시 원래 동작 자체 차단
- permission: `"deny"` / `"ask"` / `"allow"`

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "command": "bash .cursor/hooks/session-context.sh 2>/dev/null || true" }
    ],
    "beforeShellExecution": [
      {
        "command": ".cursor/hooks/guard-shell.sh",
        "matcher": "rm -rf|git push --force|git push -f|git reset --hard|chmod 777",
        "failClosed": true
      }
    ],
    "afterFileEdit": [
      { "command": "bash .cursor/hooks/check-doc-sync.sh 2>/dev/null || true" },
      { "command": "bash .cursor/hooks/lint-check.sh 2>/dev/null || true", "matcher": "Write|TabWrite" }
    ],
    "stop": [
      { "command": "bash .cursor/hooks/notify.sh 2>/dev/null || true" }
    ]
  }
}
```

**guard-shell.sh 패턴 (deny/ask/allow):**
```bash
#!/usr/bin/env bash
input=$(cat)
command=$(echo "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('command',''))" 2>/dev/null)
if echo "$command" | grep -qE "git push --force|rm -rf /"; then
  cat <<EOF
{"permission":"deny","user_message":"[guard-shell] BLOCKED: $command","agent_message":"Do not retry this command."}
EOF
  exit 2
fi
if echo "$command" | grep -qiE "DROP TABLE|DELETE FROM"; then
  echo '{"permission":"ask","user_message":"[guard-shell] WARNING: 실행할까요?"}'
  exit 0
fi
echo '{"permission":"allow"}'
exit 0
```

---

### Gemini CLI

**파일:** `.gemini/settings.json` + `.gemini/hooks/*.sh`

**황금 규칙:**
- `stdout` = JSON만 출력, 디버그는 `stderr`로
- `exit 0` = 성공, `exit 2` = **시스템 차단**

```json
{
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "write_file|replace",
        "hooks": [{
          "name": "block-secrets",
          "type": "command",
          "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/block-secrets.sh",
          "timeout": 5000
        }]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{
          "name": "inject-git-context",
          "type": "command",
          "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/git-context.sh"
        }]
      }
    ]
  }
}
```

**block-secrets.sh 패턴:**
```bash
#!/usr/bin/env bash
echo "checking tool input" >&2   # stderr only
input=$(cat)
if echo "$input" | grep -qE "AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{20,}"; then
  echo '{"decision":"deny","reason":"Potential API key detected"}'
  exit 2
fi
echo '{"decision":"allow"}'
exit 0
```

---

### Codex

**파일:** `.codex/hooks.json` 또는 `.codex/config.toml` `[hooks]` 테이블

**활성화:** 훅은 **기본 ON**. 끄려면 `.codex/config.toml`에 `[features] hooks = false`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [{ "type": "command", "command": "python3 .codex/hooks/session_start.py", "statusMessage": "Loading session notes" }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 .codex/hooks/pre_tool_use_policy.py", "statusMessage": "Checking Bash command" }]
      }
    ]
  }
}
```

**pre_tool_use_policy.py 패턴 (stdin JSON → stdout JSON):**
```python
#!/usr/bin/env python3
import json, re, sys

BLOCKED = [re.compile(r"git push --force"), re.compile(r"rm -rf /")]

def main() -> int:
    payload = json.load(sys.stdin)
    command = payload.get("command", "") or payload.get("tool_input", {}).get("command", "")
    for pattern in BLOCKED:
        if pattern.search(command):
            json.dump({"decision": "block", "message": f"Blocked: {command}"}, sys.stdout)
            return 2
    json.dump({"decision": "allow"}, sys.stdout)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## 하네스 훅 생성 체크리스트

**가드레일 (모든 하네스 권장):**
- [ ] `guard-shell.sh` (또는 `.py`) — 위험 명령 차단 패턴 정의
- [ ] 플랫폼 hook 파일에 `PreToolUse(Bash)` / `beforeShellExecution` 등록

**컨텍스트 주입 (선택):**
- [ ] `session-context.sh` — 세션 시작 시 git 상태·브랜치 주입
- [ ] `SessionStart` / `sessionStart` 이벤트에 등록

**품질 게이트 (Cursor 필수):**
- [ ] `check-doc-sync.sh` — `afterFileEdit`에 등록 (Doc Writer 연동)
- [ ] `lint-check.sh` — 언어별 linter 실행
