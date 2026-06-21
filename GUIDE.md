# Harness Eval 환경 사용 가이드

> `dockers/skill-eval/` 컨테이너를 사용해 스킬·에이전트 품질을 평가하는 절차를 단계별로 설명합니다.

---

## 1. 환경 개요

| 구성 요소 | 내용 |
|---|---|
| 베이스 이미지 | Ubuntu 24.04 |
| Go | 1.25+ (SanityHarness CLI 빌드용) |
| Node.js | 20 LTS + `skillgrade` (npm 전역 설치) |
| Python | 3.x + `uv` (패키지 매니저) |
| ML 프레임워크 | **의도적 제외** — PyTorch / TensorFlow 없음 |
| 워크 디렉터리 | `/root/working` (← 리포 루트 마운트) |
| Eval 도구 루트 | `/opt/eval-tools/` |

### 설치된 Eval 도구 목록

| 도구 | 경로 | 용도 |
|---|---|---|
| `skillgrade` | npm 전역 | 스킬 파일 채점 |
| `SanityHarness` | `/opt/eval-tools/SanityHarness` | Go CLI — 기본 정합성 검증 |
| `SkillOpt` | `/opt/eval-tools/SkillOpt` | 스킬 품질 최적화 평가 |
| `SkillsBench` | `/opt/eval-tools/skillsbench` | 스킬 벤치마크 (uv sync 런타임) |
| `SWE-agent` | `/opt/eval-tools/SWE-agent` | 코딩 에이전트 Harness |
| `hal-harness` | `/opt/eval-tools/hal-harness` | LLM 에이전트 HAL 평가 |
| `AgentBench` | `/opt/eval-tools/AgentBench` | 범용 에이전트 벤치마크 |
| `OSWorld` | `/opt/eval-tools/OSWorld` | OS 조작 에이전트 평가 |
| `webarena` | `/opt/eval-tools/webarena` | 웹 에이전트 평가 |
| `tau-bench` | `/opt/eval-tools/tau-bench` | Tool-augmented LLM 평가 |
| `darwin-skill` | `/opt/eval-tools/darwin-skill` | 스킬 진화 평가 |
| `gbrain-evals` | `/opt/eval-tools/gbrain-evals` | GBrain 에이전트 평가 |

---

## 2. 사전 요구사항

```
□ Docker Desktop (또는 Docker Engine) 실행 중
□ docker compose v2 사용 가능
□ (선택) Ollama 로컬 실행 중 — API 키 없이 평가 시 필요
□ (선택) OpenAI / Anthropic API 키
```

---

## 3. 환경 초기 설정

### 3-1. `.env` 파일 생성

```bash
# dockers/skill-eval/ 디렉터리에서 실행
cp .env.example .env
```

`.env` 편집 — 사용할 백엔드만 채우면 됩니다.

```dotenv
# OpenAI 사용 시
OPENAI_API_KEY=sk-...

# Anthropic 사용 시
ANTHROPIC_API_KEY=sk-ant-...

# 로컬 Ollama 사용 시 (Windows Docker Desktop 기본값 — 변경 불필요)
OLLAMA_HOST=http://host.docker.internal:11434
AZURE_OPENAI_ENDPOINT=http://host.docker.internal:11434/v1
AZURE_OPENAI_API_KEY=ollama
AZURE_OPENAI_AUTH_MODE=openai_compatible
```

### 3-2. 이미지 빌드

```bash
# dockers/skill-eval/ 에서 실행
docker compose build
```

> 최초 빌드 시 Go / Node.js / 각종 git clone 으로 약 5~10분 소요됩니다.

---

## 4. 컨테이너 실행

```bash
# 백그라운드 실행 후 셸 진입
docker compose up -d
docker compose exec harness-eval bash

# 또는 한 번에 인터랙티브 실행
docker compose run --rm harness-eval bash
```

컨테이너 내부에서 현재 위치:

```
root@container:/root/working#   ← 리포 루트가 마운트된 상태
```

---

## 5. 환경 검증 (필수 첫 단계)

컨테이너 진입 직후 반드시 실행합니다.

```bash
harness-eval-verify
```

정상 출력 예시:

```
=== Harness Eval environment check ===
[python] Python 3.12.3
[node]   v20.x.x
[go]     go version go1.25.0 linux/amd64
[uv]     uv 0.x.x
[skillgrade] 1.x.x
[sanity] SanityHarness v0.x.x
[pip] pytest: 8.x.x
[pip] skillopt: 0.x.x
[pip] ollama: 0.x.x
[pip] swebench: 4.x.x
[pip] agentevals: 0.x.x
[pip] datasets: 2.x.x
[pip] docker: 7.x.x
[ml] blocked packages: none (ok)    ← torch/tensorflow 없음 확인
[tools] EVAL_TOOLS_DIR=/opt/eval-tools
  - skillsbench: ok
  - SkillOpt: ok
  - SanityHarness: ok
  - hal-harness: ok
  - SWE-agent: ok
  - darwin-skill: ok
  - gbrain-evals: ok
  - AgentBench: ok
  - OSWorld: ok
  - webarena: ok
  - tau-bench: ok
=== done ===
```

`[ml] blocked packages: none (ok)` 가 반드시 출력되어야 합니다.
`MISSING` 항목이 있으면 **6. 트러블슈팅**을 참고하세요.

---

## 6. 개별 Eval 도구 사용 절차

### 6-1. `skillgrade` — 스킬 파일 채점

스킬 SKILL.md 파일의 구조·내용 품질을 Node.js 기반으로 채점합니다.

```bash
# 단일 스킬 파일 채점
skillgrade score /root/working/projects/fastapi-taskboard-harness/.cursor/skills/refactor/SKILL.md

# 디렉터리 내 모든 SKILL.md 일괄 채점
skillgrade score /root/working/.cursor/skills/

# JSON 출력 (CI 파이프라인용)
skillgrade score /root/working/.cursor/skills/ --format json | jq .
```

출력 예시:

```json
{
  "file": "refactor/SKILL.md",
  "score": 82,
  "grades": {
    "structure": "A",
    "clarity": "B+",
    "examples": "B"
  },
  "suggestions": ["Add more concrete examples", "Clarify trigger conditions"]
}
```

---

### 6-2. `sanity` — 기본 정합성 검증 (SanityHarness)

Go CLI로 빌드된 바이너리. SKILL.md / 설정 파일의 정합성을 빠르게 검사합니다.

```bash
# 버전 확인
sanity version

# 단일 파일 검증
sanity check /root/working/.cursor/skills/brainstorming/SKILL.md

# 디렉터리 전체 검증
sanity check /root/working/.cursor/skills/

# 상세 보고서 출력
sanity check /root/working/.cursor/skills/ --verbose --report sanity-report.json
```

출력 예시:

```
✓ brainstorming/SKILL.md  — passed (3 checks)
✗ refactor/SKILL.md       — FAIL: missing 'description' field
  Line 1: expected frontmatter key 'description'

Summary: 1 passed, 1 failed
```

---

### 6-3. `SkillOpt` — 스킬 품질 최적화 평가

SkillOpt는 스킬을 실제 LLM으로 평가하며 개선 방향을 제안합니다.

#### Ollama 로컬 모델로 평가 (API 키 불필요)

```bash
cd /opt/eval-tools/SkillOpt

# 의존성 설치 (최초 1회)
pip install -e . --quiet

# 스킬 평가 실행 (llama3.2 예시)
python eval_only.py \
  --skill_path /root/working/.cursor/skills/brainstorming/SKILL.md \
  --optimizer_model llama3.2 \
  --target_model llama3.2 \
  --backend openai_compatible \
  --endpoint http://host.docker.internal:11434/v1 \
  --output_dir /root/working/eval-results/skillopt/
```

#### OpenAI 모델로 평가

```bash
python eval_only.py \
  --skill_path /root/working/.cursor/skills/refactor/SKILL.md \
  --optimizer_model gpt-4o-mini \
  --target_model gpt-4o-mini \
  --backend openai_chat \
  --output_dir /root/working/eval-results/skillopt/
```

결과 파일 확인:

```bash
cat /root/working/eval-results/skillopt/results.json | jq .score
```

---

### 6-4. `SkillsBench` — 스킬 벤치마크

uv 기반으로 런타임에 의존성을 설치하고 벤치마크를 실행합니다.

```bash
cd /opt/eval-tools/skillsbench

# 의존성 동기화 (최초 1회)
uv sync

# 전체 벤치마크 실행
uv run python -m skillsbench \
  --skills-dir /root/working/.cursor/skills/ \
  --model ollama/llama3.2 \
  --output /root/working/eval-results/skillsbench/

# 특정 카테고리만
uv run python -m skillsbench \
  --skills-dir /root/working/.cursor/skills/ \
  --category refactor \
  --model ollama/llama3.2
```

---

### 6-5. `SWE-bench` (swebench) — 코딩 에이전트 평가

실제 GitHub 이슈 해결 능력을 측정합니다. Docker 소켓이 마운트되어 있어 샌드박스 컨테이너 생성이 가능합니다.

```bash
# Python 패키지로 직접 사용
python3 - <<'PY'
from swebench.harness.run_evaluation import main
main(
    dataset_name="princeton-nlp/SWE-bench_Lite",
    split="test",
    instance_ids=["django__django-11099"],   # 특정 이슈만 테스트
    predictions_path="/root/working/eval-results/swe-predictions.jsonl",
    max_workers=1,
    run_id="local-test-01",
)
PY

# sb-cli 사용 (간편 인터페이스)
sb-cli run \
  --predictions /root/working/eval-results/swe-predictions.jsonl \
  --split lite \
  --instance django__django-11099
```

---

### 6-6. `hal-harness` — HAL 에이전트 평가

```bash
cd /opt/eval-tools/hal-harness

# 의존성 설치
pip install -e . --quiet

# 평가 실행 예시
python run.py \
  --agent_name my-agent \
  --benchmark swebench_lite \
  --model gpt-4o-mini \
  --output_path /root/working/eval-results/hal/
```

---

### 6-7. `agentevals` — 범용 에이전트 평가

```bash
python3 - <<'PY'
from agentevals import TrajectoryEval

evaluator = TrajectoryEval(model="openai/gpt-4o-mini")

result = evaluator.evaluate(
    trajectory=[
        {"role": "user", "content": "List files in /tmp"},
        {"role": "assistant", "content": "ls /tmp", "tool_call": "shell"},
        {"role": "tool", "content": "file1.txt  file2.txt"},
        {"role": "assistant", "content": "The /tmp directory contains: file1.txt, file2.txt"},
    ],
    task="List files in /tmp directory"
)
print(f"Score: {result.score}")
print(f"Feedback: {result.feedback}")
PY
```

---

### 6-8. `tau-bench` — Tool-Augmented LLM 평가

```bash
cd /opt/eval-tools/tau-bench

pip install -e . --quiet

python run.py \
  --model gpt-4o-mini \
  --env retail \
  --num-trials 5 \
  --output /root/working/eval-results/tau-bench/
```

---

## 7. pytest 통합 테스트

컨테이너 내부에서 리포 루트의 pytest 테스트를 그대로 실행할 수 있습니다.

```bash
# 리포 루트는 /root/working 에 마운트됨
cd /root/working

# 전체 테스트
pytest -v

# 특정 프로젝트만
pytest projects/fastapi-taskboard-harness/ -v

# 커버리지 포함
pytest --cov=. --cov-report=html projects/ -v
```

---

## 8. 전체 평가 파이프라인 예시

아래 스크립트를 `/root/working/run-eval-pipeline.sh` 로 저장하고 실행합니다.

```bash
#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="/root/working/.cursor/skills"
OUT_DIR="/root/working/eval-results/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

echo "▶ Step 1: 환경 검증"
harness-eval-verify | tee "$OUT_DIR/env-check.log"

echo ""
echo "▶ Step 2: sanity 정합성 검사"
sanity check "$SKILL_DIR" --report "$OUT_DIR/sanity.json" || true

echo ""
echo "▶ Step 3: skillgrade 채점"
skillgrade score "$SKILL_DIR" --format json > "$OUT_DIR/skillgrade.json" || true
cat "$OUT_DIR/skillgrade.json" | jq '.[] | {file, score}'

echo ""
echo "▶ Step 4: pytest 단위 테스트"
cd /root/working
pytest -v --tb=short 2>&1 | tee "$OUT_DIR/pytest.log" || true

echo ""
echo "▶ 평가 완료: $OUT_DIR"
ls -lh "$OUT_DIR"
```

실행:

```bash
chmod +x /root/working/run-eval-pipeline.sh
/root/working/run-eval-pipeline.sh
```

---

## 9. 트러블슈팅

### 빌드 실패: Go 버전 없음

```
# ARG GO_VERSION 확인
grep GO_VERSION dockers/skill-eval/Dockerfile
# go.dev/dl 에서 유효한 버전인지 확인 후 수정
```

### `harness-eval-verify` 에서 MISSING 패키지

```bash
# 컨테이너 내부에서 수동 설치
pip install --break-system-packages <패키지명>
```

### Docker 소켓 권한 오류 (SWE-bench / SkillsBench)

```bash
# 호스트에서 소켓 권한 확인
ls -la /var/run/docker.sock
# 컨테이너 내부에서 확인
docker ps
```

### Ollama 연결 실패

```bash
# 호스트에서 Ollama 실행 여부 확인
curl http://localhost:11434/api/tags

# 컨테이너 내부에서 확인
curl http://host.docker.internal:11434/api/tags

# 모델 목록 확인
ollama list
```

### `[ml] blocked packages` 에 torch/tensorflow 표시

이미지를 다시 빌드해야 합니다.

```bash
docker compose down
docker compose build --no-cache
```

---

## 10. 컨테이너 종료

```bash
# 컨테이너 내부에서
exit

# 호스트에서 정리
docker compose down
```

결과물은 `/root/working/eval-results/` (= 리포 루트의 `eval-results/`) 에 남습니다.
