#!/usr/bin/env bash
# 빌드/병렬 작업을 시작하기 전에 반드시 먼저 실행하세요.
#
# 왜? 컨테이너(pod)에서 `nproc`는 "호스트"의 물리 코어 수를 보고할 수 있습니다.
# 여러분의 pod가 실제로 쓸 수 있는 CPU는 cgroup 이 정합니다. 이 둘을 혼동하면
# 있지도 않은 코어를 요청하게 되고, 빌드가 수십 배 느려지거나 아예 멈춥니다.
# (자세한 사고 경위: ../02_POSTMORTEM.md)
set -euo pipefail

echo "==================== 내 pod의 실제 자원 ===================="

# --- 실효 CPU (cgroup 우선) ---
if [[ -r /sys/fs/cgroup/cpu.max ]]; then                      # cgroup v2
  read -r quota period < /sys/fs/cgroup/cpu.max
  if [[ "$quota" == "max" ]]; then
    eff_cpu="$(nproc)"; src="cgroup v2 (제한 없음)"
  else
    eff_cpu=$(( quota / period )); [[ "$eff_cpu" -lt 1 ]] && eff_cpu=1
    src="cgroup v2 ($quota/$period)"
  fi
elif [[ -r /sys/fs/cgroup/cpu/cpu.cfs_quota_us ]]; then       # cgroup v1
  q=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us); p=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us)
  if [[ "$q" -le 0 ]]; then eff_cpu="$(nproc)"; src="cgroup v1 (제한 없음)"
  else eff_cpu=$(( q / p )); [[ "$eff_cpu" -lt 1 ]] && eff_cpu=1; src="cgroup v1 ($q/$p)"; fi
else
  eff_cpu="$(nproc)"; src="cgroup 정보 없음 → nproc"
fi

# --- /dev/shm (ray 오브젝트 스토어 성능에 직결) ---
shm_mb=$(df -m /dev/shm 2>/dev/null | awk 'NR==2{print $2}'); shm_mb=${shm_mb:-0}
# --- RAM ---
ram_g=$(free -g 2>/dev/null | awk '/Mem:/{print $2}')

printf "  실효 CPU   : %s개   (%s)\n" "$eff_cpu" "$src"
printf "  nproc(호스트): %s개   ← 이 숫자를 믿지 마세요\n" "$(nproc)"
printf "  /dev/shm   : %sMB\n" "$shm_mb"
printf "  RAM        : %sGB\n" "${ram_g:-?}"
echo "============================================================"

# --- 빌드 설정 권고 자동 산출 ---
worker_cpu=$(( eff_cpu > 1 ? eff_cpu - 1 : 1 ))   # 드라이버용 1코어 남김
echo ""
echo "▶ 이 pod에서의 아티팩트 빌드 권고값:"
printf "    --num-cpu-per-compile-worker        %s\n" "$worker_cpu"
printf "    --num-cpu-per-pipeline-build-worker  %s\n" "$worker_cpu"
echo "    --num-compile-workers 1   --num-pipeline-builder-workers 1"
if [[ "$shm_mb" -lt 1024 ]]; then
  echo "    (⚠ /dev/shm 이 작습니다: 워커는 1개로 두세요. 늘리면 디스크 I/O로 더 느려집니다.)"
fi
echo ""
echo "※ build_artifact.py 는 위 값을 자동 계산하므로, 보통은 그냥 실행하면 됩니다."
