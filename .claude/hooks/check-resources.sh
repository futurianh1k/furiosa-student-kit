#!/usr/bin/env bash
# SessionStart 훅: 컨테이너의 "실효" CPU/공유메모리를 측정해 세션 시작 시 모델 컨텍스트에
# 주입한다. nproc(호스트 코어)를 믿고 병렬/빌드 설정을 잘못 잡는 실수를 방지하는 것이 목적.
# 측정값이 기록된 기준선(memory)과 다르면 "메모리를 갱신하라"는 지시를 함께 넣는다.
#
# 관련: docs/furiosa-artifact-build-postmortem.md,
#       ~/.claude/projects/-root-works/memory/container-cpu-shm-limits.md
set -euo pipefail

# --- 기록된 기준선 (memory 파일의 값과 일치시켜 둔다) ---
BASELINE_CPU=15
BASELINE_SHM_MB=64

# --- 실효 CPU 측정 (cgroup 우선, 없으면 nproc) ---
eff_cpu=""
if [[ -r /sys/fs/cgroup/cpu.max ]]; then                      # cgroup v2
  read -r quota period < /sys/fs/cgroup/cpu.max || true
  if [[ "${quota:-max}" == "max" || -z "${quota:-}" ]]; then
    eff_cpu="$(nproc)"                                         # 제한 없음 → 물리 코어
  else
    eff_cpu=$(( quota / period ))
    [[ "$eff_cpu" -lt 1 ]] && eff_cpu=1
  fi
elif [[ -r /sys/fs/cgroup/cpu/cpu.cfs_quota_us ]]; then       # cgroup v1
  q=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us)
  p=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us)
  if [[ "$q" -le 0 ]]; then eff_cpu="$(nproc)"; else eff_cpu=$(( q / p )); [[ "$eff_cpu" -lt 1 ]] && eff_cpu=1; fi
else
  eff_cpu="$(nproc)"
fi

host_cpu="$(nproc)"

# --- /dev/shm 크기 측정 (MB) ---
shm_mb=$(df -m /dev/shm 2>/dev/null | awk 'NR==2{print $2}')
shm_mb=${shm_mb:-0}

# --- 기준선과 비교 → 안내 문구 구성 ---
note="Container resource check (measured at session start): effective CPUs=${eff_cpu} (host nproc=${host_cpu}), /dev/shm=${shm_mb}MB."
note+=" Use these MEASURED values for any parallel/build sizing — never trust nproc alone."
if [[ "$eff_cpu" != "$BASELINE_CPU" || "$shm_mb" != "$BASELINE_SHM_MB" ]]; then
  note+=" WARNING: these differ from the recorded baseline (CPU=${BASELINE_CPU}, shm=${BASELINE_SHM_MB}MB) in memory 'container-cpu-shm-limits'."
  note+=" The environment changed — update that memory file and BASELINE_CPU/BASELINE_SHM_MB in .claude/hooks/check-resources.sh to the measured values."
fi

# JSON 출력 (jq 로 안전하게 이스케이프). 없으면 조용히 통과.
if command -v jq >/dev/null 2>&1; then
  jq -cn --arg ctx "$note" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
fi
