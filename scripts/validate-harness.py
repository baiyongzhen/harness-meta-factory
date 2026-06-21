#!/usr/bin/env python3
"""validate-harness.py — 하네스 파일 자동 검증 파이프라인
실행:
  docker compose run --rm harness-validate
  docker compose run --rm harness-test-validate
  python3 scripts/validate-harness.py --target tests/fastapi-jwt-keycloak-cursor
"""
import argparse
import os
import sys
import subprocess
import pathlib
import json
import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--target", default="", help="검증 대상 루트 (기본: /root/working)")
parser.add_argument("--platform", default="all",
                    choices=["claude","cursor","gemini","codex","all"],
                    help="검증할 플랫폼 (기본: all)")
args = parser.parse_args()

WORK = pathlib.Path("/root/working")
TARGET = (WORK / args.target) if args.target else WORK
PLATFORM = args.platform
TS = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = WORK / "eval-results" / TS
OUT.mkdir(parents=True, exist_ok=True)

PASS = 0
FAIL = 0
SKIP = 0

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")

def log(msg=""):
    print(f"[{ts()}] {msg}", flush=True)

def ok(msg):
    global PASS
    print(f"  OK  {msg}", flush=True)
    PASS += 1

def fail(msg):
    global FAIL
    print(f"  NG  {msg}", flush=True)
    FAIL += 1

def skip_it(msg):
    global SKIP
    print(f"  --  {msg} (skip)", flush=True)
    SKIP += 1

def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)

log(f"Target: {TARGET}")

# Step 0: 환경 검증
log("Step 0: 환경 검증")
result = run(["harness-eval-verify"])
(OUT / "env-check.log").write_text(result.stdout + result.stderr)
print(result.stdout, flush=True)
if result.returncode == 0:
    ok("환경 검증 완료")
else:
    fail("환경 검증 실패")

# Step 1: SKILL.md frontmatter 정합성
log()
log("Step 1: SKILL.md frontmatter 정합성 검사")

skill_paths = []
for rel in [".claude/skills", ".cursor/skills", ".gemini/skills", ".agents/skills"]:
    p = TARGET / rel
    if p.is_dir():
        skill_paths.append(p)

if not skill_paths:
    skip_it("스킬 디렉터리 없음")
else:
    sanity_lines = []
    for sp in skill_paths:
        files = list(sp.rglob("SKILL.md"))
        log(f"  {sp.relative_to(TARGET)}: SKILL.md {len(files)}개")
        for sf in files:
            content = sf.read_text(encoding="utf-8", errors="replace")
            has_name = "name:" in content
            has_desc = "description:" in content
            has_trigger = any(k in content for k in ["트리거", "trigger", "Use when", "사용"])
            has_followup = any(k in content for k in ["후속", "follow-up", "재실행", "update"])
            rel = str(sf.relative_to(TARGET))
            score = sum([has_name*20, has_desc*20, has_trigger*20, has_followup*15,
                        (len(content.splitlines()) <= 500)*15, 10])
            if has_name and has_desc:
                ok(f"frontmatter OK (score={score}): {rel}")
            else:
                missing = [k for k,v in [("name",has_name),("description",has_desc)] if not v]
                fail(f"MISSING [{','.join(missing)}]: {rel}")
            sanity_lines.append(f"{'PASS' if has_name and has_desc else 'FAIL'} score={score} {rel}")
    (OUT / "sanity.log").write_text("\n".join(sanity_lines))

# Step 2: skillgrade
log()
log("Step 2: skillgrade 채점")

if run(["which","skillgrade"]).returncode == 0:
    for sp in skill_paths:
        r = run(["skillgrade","score",str(sp),"--format","json"])
        key = str(sp.relative_to(TARGET)).replace("/","-").replace("\\","-")
        (OUT / f"skillgrade-{key}.json").write_text(r.stdout or r.stderr)
        ok(f"skillgrade: {sp.relative_to(TARGET)}")
else:
    skip_it("skillgrade 없음")

# Step 3: 구조 검증
log()
log("Step 3: 플랫폼 구조 검증")

def chkf(label, path):
    p = TARGET / path
    if p.is_file():
        ok(f"{label}: {path}")
        return 1
    else:
        fail(f"{label} 없음: {path}")
        return 0

def chkd(label, path):
    p = TARGET / path
    if p.is_dir():
        ok(f"{label}: {path}/")
        return 1
    else:
        fail(f"{label} 없음: {path}/")
        return 0

results = {}

if PLATFORM in ("cursor","all"):
    log("  [Cursor]")
    results["cursor"] = [
        chkf("entry", "AGENTS.md"),
        chkd("agents", ".cursor/agents"),
        chkd("skills", ".cursor/skills"),
        chkf("hooks.json", ".cursor/hooks.json"),
        chkf("check-doc-sync", ".cursor/hooks/check-doc-sync.sh"),
    ]

if PLATFORM in ("claude","all"):
    log("  [Claude Code]")
    results["claude"] = [
        chkf("entry", "CLAUDE.md"),
        chkd("agents", ".claude/agents"),
        chkd("skills", ".claude/skills"),
        chkf("hooks", ".claude/hooks/hooks.json"),
    ]

if PLATFORM in ("gemini","all"):
    log("  [Gemini CLI]")
    results["gemini"] = [
        chkf("entry", "GEMINI.md"),
        chkd("skills", ".gemini/skills"),
        chkf("settings", ".gemini/settings.json"),
    ]

if PLATFORM in ("codex","all"):
    log("  [Codex]")
    results["codex"] = [
        chkf("entry", "AGENTS.md"),
        chkd("agents", ".codex/agents"),
        chkf("config", ".codex/config.toml"),
        chkf("hooks", ".codex/hooks.json"),
    ]

# .agents/skills — 멀티플랫폼(all) 또는 명시 요청 시만 필수
# Cursor/Claude/Gemini 단독 모드에서는 선택 사항
if PLATFORM == "all" or (TARGET / ".agents/skills").is_dir():
    log("  [공통 .agents/skills]")
    results["common"] = [chkd("agents-skills", ".agents/skills")]
else:
    log("  [공통 .agents/skills] 단독 플랫폼 모드 — 건너뜀")
    results["common"] = [1]  # not required for single-platform harness

# Step 4: pytest
log()
log("Step 4: pytest")
tests_dir = WORK / "tests"
if tests_dir.is_dir() and args.target == "":
    r = subprocess.run([sys.executable,"-m","pytest","tests/","-v","--tb=short"],
                       cwd=WORK, capture_output=True, text=True)
    (OUT / "pytest.log").write_text(r.stdout + r.stderr)
    ok("pytest 완료") if r.returncode == 0 else fail("pytest 실패")
else:
    skip_it("tests/ 없음 또는 타겟 모드")

# 요약
log()
log("=" * 55)
log(f"검증 완료: PASS={PASS}  FAIL={FAIL}  SKIP={SKIP}")
log(f"결과 위치: {OUT}")
summary = {
    "timestamp": TS, "target": str(TARGET),
    "pass": PASS, "fail": FAIL, "skip": SKIP,
    "structure": {k: {"pass":sum(v),"fail":len(v)-sum(v)} for k,v in results.items()},
}
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
log(f"요약 JSON: {OUT / 'summary.json'}")
log("=" * 55)
sys.exit(0 if FAIL == 0 else 1)