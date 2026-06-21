# 플랫폼별 Slash Commands 설계 가이드

> Slash Commands는 재사용 가능한 프롬프트 단축키. 스킬과의 적합 영역이 다르므로 목적에 따라 선택.

## Commands vs Skill 선택 기준

| 상황 | Commands 사용 | Skill 사용 |
|------|--------------|-----------|
| 단일 프롬프트로 해결 | ✅ `/fix-lint` | ❌ 과도 |
| 다단계 워크플로 | ❌ 표현 어려움 | ✅ Phase 절차 |
| 파일 주입 + 셸 실행 조합 | ✅ Gemini `!{}` / `@{}` | ✅ scripts 포함 스킬 |
| 인자가 필요한 반복 작업 | ✅ `{{args}}` 파라미터 | ✅ 복잡한 경우 |
| 스킬 진입점 호출 | ✅ `/run-skill` → skill 로드 | — |

---

## 플랫폼별 상태 및 경로

| 플랫폼 | 지원 여부 | 저장 위치 | 형식 | 트리거 |
|--------|-----------|-----------|------|--------|
| **Claude Code** | Skills 우선 권장 | `.claude/commands/*.md` | Markdown | `/command-name` |
| **Cursor** | Skills/`@` 우선 | `.cursor/commands/*.md` | Markdown | `/command-name` |
| **Gemini CLI** | ✅ 동적 기능 풍부 | `.gemini/commands/*.toml` | TOML | `/command-name` |
| **Codex** | ✅ 자동 트리거 | `.codex/commands/*.md` | Markdown | `$command-name` |

---

## Claude Code — `.claude/commands/`

### 구조

```
.claude/
└── commands/
    ├── commit.md        # /commit
    ├── review.md        # /review
    └── fix-lint.md      # /fix-lint
```

### 기본 Command 예시

```markdown
---
description: 변경사항 리뷰 후 Conventional Commit 생성
---

# /commit

다음 순서로 커밋을 생성하세요:
1. `git diff --staged` 로 변경사항 확인
2. Conventional Commits 형식 적용: `type(scope): desc`
3. Breaking change 있으면 `!` 표시 및 BREAKING CHANGE 푸터 추가
4. 커밋 메시지 출력 후 확인 요청
```

### `disable-model-invocation` — 순수 프롬프트 텍스트 삽입

```markdown
---
description: 코드 리뷰 체크리스트 삽입
disable-model-invocation: true   # 명령 실행 없이 텍스트만 채팅에 붙여넣기
---

아래 기준으로 리뷰해주세요:
- [ ] Null 안전성 확인
- [ ] 예외 처리 누락 여부
- [ ] 성능: N+1 쿼리 없는지
```

### `argument-hint` — 인자 안내

```markdown
---
description: 특정 스킬 실행
argument-hint: "skill-name [--dry-run]"
---

다음 스킬을 로드하여 실행하세요: $ARGUMENTS
```

---

## Cursor — `.cursor/commands/`

### 구조

```
.cursor/
└── commands/
    ├── review.md        # /review
    └── deploy.md        # /deploy
```

### 예시

```markdown
---
description: PR 제출 전 검토
---

# /review

1. `git diff main` 으로 변경사항 목록 출력
2. 각 파일에 대해 보안·성능·테스트 누락 여부 코멘트
3. 체크리스트 형식으로 요약 출력
```

> Cursor에서는 복잡한 워크플로는 Skills(`@skill-name`)로, 단순 체크리스트·템플릿 삽입은 Commands로 구분.

---

## Gemini CLI — `.gemini/commands/*.toml`

### 핵심 기능: 동적 컨텍스트 주입

Gemini Commands는 `{{args}}`, `@{file}`, `!{shell}` 세 가지 삽입 패턴을 지원.

### `.toml` 기본 구조

```toml
name = "analyze"
description = "파일 분석 후 요약"
prompt = """
다음 파일을 분석하고 요약해주세요:
{{args}}
"""
```

### `@{file}` — 파일 내용 주입

```toml
name = "review-spec"
description = "스펙 파일 리뷰"
prompt = """
아래 스펙 기준으로 코드가 구현되었는지 검토하세요:

## 스펙:
@{docs/spec.md}

## 검토 기준:
- 스펙 커버리지: 누락된 기능 있는지
- API 시그니처: 스펙과 일치하는지
- 예외 처리: 스펙에 명시된 오류 케이스 처리 여부
"""
```

### `!{shell}` — 셸 명령 결과 주입

```toml
name = "fix-lint"
description = "린트 오류 자동 수정"
prompt = """
다음 린트 오류를 수정하세요:

!{ruff check src/ 2>&1}

규칙:
1. 오류 코드 설명 + 수정 방법 제시
2. 자동 수정 가능하면 코드 직접 변경
"""
```

### 조합 예시: 테스트 실패 분석

```toml
name = "debug-test"
description = "실패한 테스트 분석 및 수정"
prompt = """
## 실패한 테스트
!{pytest {{args}} -x 2>&1 | head -50}

## 관련 소스
@{src/}

실패 원인 분석 후 수정안 제시.
"""
```

### `allow_tools` — 허용 도구 제한

```toml
name = "safe-review"
description = "읽기 전용 리뷰 (수정 없음)"
allow_tools = ["ReadFile", "ListDirectory"]   # 쓰기 도구 제외
prompt = """
@{src/} 코드 품질 리뷰. 수정 없이 의견만 출력.
"""
```

---

## Codex — `.codex/commands/`

### 구조

```
.codex/
└── commands/
    ├── commit.md        # $commit
    └── review.md        # $review
```

### `allow_implicit_invocation: false` — 수동 트리거만

```markdown
---
description: 스테이징 배포 실행
allow_implicit_invocation: false   # 명시적 $deploy 호출 시만 실행
---

# $deploy

1. 테스트 통과 확인: `pytest`
2. 도커 빌드: `docker build -t app:staging .`
3. 스테이징 배포: `kubectl apply -f k8s/staging/`
4. 헬스체크: `curl https://staging.example.com/health`
```

> `allow_implicit_invocation: false` 없으면 AI가 자동 판단으로 실행 — 부작용 있는 명령(배포·삭제)은 반드시 설정.

---

## 하네스 Commands 체크리스트

- [ ] 단순 프롬프트 단축키 → Commands, 다단계 절차 → Skill
- [ ] Gemini: `!{shell}` 주입으로 실시간 컨텍스트(lint 결과·테스트 출력) 삽입 활용
- [ ] Gemini: `@{file}` 주입으로 스펙·컨텍스트 파일 자동 삽입
- [ ] Codex 부작용 명령(배포·DB 변경): `allow_implicit_invocation: false` 필수
- [ ] Claude: 체크리스트·가이드 텍스트 삽입에 `disable-model-invocation: true` 활용
- [ ] `/run-skill` 패턴: Command가 Skill 로드의 진입점 역할 가능
