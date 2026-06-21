# Harness Eval 기술 검증 환경
# docs/102.Eval (01~04) — TensorFlow / PyTorch 미포함
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    GIT_LFS_SKIP_SMUDGE=1 \
    EVAL_TOOLS_DIR=/opt/eval-tools \
    GOPATH=/root/go \
    PATH="/usr/local/go/bin:/root/.local/bin:/root/go/bin:${PATH}" \
    WORKDIR=/root/working

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ---------------------------------------------------------------------------
# 1. 시스템 패키지
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    git \
    git-lfs \
    jq \
    unzip \
    make \
    build-essential \
    pkg-config \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    docker.io \
    bubblewrap \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# 2. Go 1.25+ — SanityHarness
# ---------------------------------------------------------------------------
ARG GO_VERSION=1.25.0
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" \
    | tar -C /usr/local -xz \
    && go version

# ---------------------------------------------------------------------------
# 3. Node.js 20 LTS — skillgrade
# ---------------------------------------------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g skillgrade \
    && node --version

# ---------------------------------------------------------------------------
# 4. uv — SkillsBench (런타임 uv sync용, 빌드 시 sync 하지 않음)
# ---------------------------------------------------------------------------
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && uv --version

# ---------------------------------------------------------------------------
# 5. Python 패키지 (PyPI, ML 프레임워크 제외)
# ---------------------------------------------------------------------------
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    && python3 -m pip uninstall -y \
        torch torchvision torchaudio tensorflow tensorflow-cpu tensorflow-intel \
        2>/dev/null || true

# TensorFlow / PyTorch 미설치 검증
RUN python3 - <<'PY'
import importlib.util
import sys

blocked = ("torch", "tensorflow", "tensorflow_cpu", "torchvision", "torchaudio")
found = [name for name in blocked if importlib.util.find_spec(name)]
if found:
    print(f"ERROR: blocked packages installed: {found}", file=sys.stderr)
    sys.exit(1)
print("OK: no torch/tensorflow packages")
PY

# ---------------------------------------------------------------------------
# 6. OSS Eval 저장소 (shallow clone만 — pip/uv install은 런타임)
#    제외: openai/evals, bfcl-eval pip (TF/torch 의존)
#    skillopt 는 requirements.txt 로 설치 (기본 의존성만, extras 미사용)
# ---------------------------------------------------------------------------
RUN mkdir -p "${EVAL_TOOLS_DIR}" \
    && git clone --depth 1 https://github.com/benchflow-ai/skillsbench.git "${EVAL_TOOLS_DIR}/skillsbench" \
    && git clone --depth 1 https://github.com/microsoft/SkillOpt.git "${EVAL_TOOLS_DIR}/SkillOpt" \
    && git clone --depth 1 https://github.com/lemon07r/SanityHarness.git "${EVAL_TOOLS_DIR}/SanityHarness" \
    && git clone --depth 1 https://github.com/princeton-pli/hal-harness.git "${EVAL_TOOLS_DIR}/hal-harness" \
    && git clone --depth 1 https://github.com/SWE-agent/SWE-agent.git "${EVAL_TOOLS_DIR}/SWE-agent" \
    && git clone --depth 1 https://github.com/alchaincyf/darwin-skill.git "${EVAL_TOOLS_DIR}/darwin-skill" \
    && git clone --depth 1 https://github.com/garrytan/gbrain-evals.git "${EVAL_TOOLS_DIR}/gbrain-evals" \
    && git clone --depth 1 https://github.com/THUDM/AgentBench.git "${EVAL_TOOLS_DIR}/AgentBench" \
    && git clone --depth 1 https://github.com/xlang-ai/OSWorld.git "${EVAL_TOOLS_DIR}/OSWorld" \
    && git clone --depth 1 https://github.com/web-arena-x/webarena.git "${EVAL_TOOLS_DIR}/webarena" \
    && git clone --depth 1 https://github.com/sierra-research/tau-bench.git "${EVAL_TOOLS_DIR}/tau-bench"

# SanityHarness (Go CLI)
WORKDIR ${EVAL_TOOLS_DIR}/SanityHarness
RUN go build -o /usr/local/bin/sanity ./cmd/sanity \
    && sanity version

# ---------------------------------------------------------------------------
# 7. 환경 검증 스크립트
# ---------------------------------------------------------------------------
RUN cat >/usr/local/bin/harness-eval-verify <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "=== Harness Eval environment check ==="
echo "[python] $(python3 --version)"
echo "[node]   $(node --version)"
echo "[go]     $(go version)"
echo "[uv]     $(uv --version)"
command -v skillgrade >/dev/null && echo "[skillgrade] $(skillgrade --version 2>/dev/null || echo ok)"
command -v sanity >/dev/null && echo "[sanity] $(sanity version 2>/dev/null | head -1 || echo ok)"
python3 - <<'PY'
import importlib
import importlib.util

for name in ("pytest", "skillopt", "ollama", "swebench", "agentevals", "datasets", "docker"):
    try:
        m = importlib.import_module(name)
        print(f"[pip] {name}: {getattr(m, '__version__', 'ok')}")
    except Exception as e:
        print(f"[pip] {name}: MISSING ({e})")

blocked = ("torch", "tensorflow", "tensorflow_cpu")
found = [n for n in blocked if importlib.util.find_spec(n)]
print(f"[ml] blocked packages: {'none (ok)' if not found else found}")
PY
echo "[tools] EVAL_TOOLS_DIR=${EVAL_TOOLS_DIR:-/opt/eval-tools}"
for d in skillsbench SkillOpt SanityHarness hal-harness SWE-agent darwin-skill gbrain-evals AgentBench OSWorld webarena tau-bench; do
  [[ -d "${EVAL_TOOLS_DIR:-/opt/eval-tools}/$d" ]] && echo "  - $d: ok" || echo "  - $d: missing"
done
echo "=== done ==="
EOF
RUN chmod +x /usr/local/bin/harness-eval-verify

WORKDIR /root/working
CMD ["/bin/bash"]
