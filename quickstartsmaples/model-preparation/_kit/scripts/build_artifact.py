"""Furiosa LLM 아티팩트 빌드 - 학생 실습용 (자원 자동 측정 버전)

이 스크립트의 핵심 교육 포인트
------------------------------
1. 워커 CPU 수를 하드코딩하지 않고 **cgroup 실효 CPU 를 직접 측정**해서 정한다.
   → "nproc(호스트 코어)를 믿지 말고 측정하라"는 이 수업의 교훈을 코드가 구현한다.
2. append_buckets 가 없으면 런타임이 chunked prefill / prefix caching 을 끈다.
   Qwen2.5-0.5B 프리셋에는 이게 빠져 있어 직접 채워야 한다(--fix-append).
   다른 모델(Llama, Qwen3 등)은 프리셋에 이미 있어 그냥 빌드하면 된다.

사용법
------
  # 0) 먼저 자원 확인
  bash check_resources.sh

  # 1) 버킷 해석/검증만 (컴파일 안 함) — 항상 먼저 이걸로 확인
  python build_artifact.py --model Qwen/Qwen2.5-0.5B-Instruct --fix-append --dry-run

  # 2) 실제 빌드 (워커 CPU 는 자동으로 pod 에 맞춰짐)
  python build_artifact.py --model Qwen/Qwen2.5-0.5B-Instruct --fix-append -o ./out

  # 프리셋에 append 가 이미 있는 모델은 --fix-append 없이:
  python build_artifact.py --model meta-llama/Llama-3.1-8B-Instruct -o ./out
"""

import argparse
import logging
from pathlib import Path

from furiosa_llm.artifact import (
    ArtifactBuilder,
    BucketConfig,
    ModelConfig,
    ParallelConfig,
)


def effective_cpus() -> int:
    """이 컨테이너가 실제로 쓸 수 있는 CPU 수 (cgroup). nproc 이 아니다!"""
    v2 = Path("/sys/fs/cgroup/cpu.max")
    if v2.is_file():
        quota, period = v2.read_text().split()
        if quota == "max":
            import os
            return os.cpu_count() or 1
        return max(1, int(quota) // int(period))
    q = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    p = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if q.is_file() and p.is_file():
        qi, pi = int(q.read_text()), int(p.read_text())
        if qi <= 0:
            import os
            return os.cpu_count() or 1
        return max(1, qi // pi)
    import os
    return os.cpu_count() or 1


# Qwen2.5-0.5B 프리셋에 누락된 append_buckets. (batch, attention_size, input_ids_size),
# attention_size > input_ids_size. 작은 pod 에서는 전조합(34개)이 과하니 대표 6개만.
QWEN25_05B_APPEND = (
    (1, 1024, 128), (1, 1024, 512),
    (1, 2048, 128), (1, 2048, 512),
    (1, 4096, 128), (1, 4096, 512),
)
# 나머지 3개 필드는 프리셋 원본값(부분 지정은 금지되므로 4개를 함께 넣어야 한다).
QWEN25_05B_PREFILL = ((1, 1024), (1, 2048), (1, 3072), (1, 4096))
QWEN25_05B_DECODE = ((128, 1024), (128, 2048), (128, 3072), (128, 4096))
QWEN25_05B_TOKENWISE = (128, 1024, 2048, 3072, 4096)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="HF 모델 ID 또는 로컬 경로 (베이스 모델)")
    ap.add_argument("-o", "--output", type=Path, default=Path("./artifact"))
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--tensor-parallel-size", type=int, default=4)
    ap.add_argument(
        "--fix-append", action="store_true",
        help="Qwen2.5-0.5B 처럼 프리셋에 append_buckets 가 없는 모델용. 버킷을 직접 채운다.",
    )
    ap.add_argument("--dry-run", action="store_true", help="버킷 검증만, 컴파일 안 함")
    ap.add_argument(
        "--workers", type=int, default=1,
        help="파이프라인/컴파일 워커 수. /dev/shm 이 작으면 1 권장 (기본 1).",
    )
    ap.add_argument(
        "--cpu-per-worker", type=int, default=0,
        help="워커당 CPU. 0(기본)이면 cgroup 실효CPU에서 자동 계산. 실효CPU를 넘기면 안 된다.",
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # --- 자원 측정 → 워커 CPU 자동 결정 (이 스크립트의 핵심) ---
    eff = effective_cpus()
    cpu_per_worker = args.cpu_per_worker or max(1, eff - 1)  # 드라이버용 1 남김
    if cpu_per_worker > eff:
        raise SystemExit(
            f"cpu-per-worker({cpu_per_worker}) > 실효 CPU({eff}). "
            f"이 값이 실효 CPU 를 넘으면 ray 가 워커를 배치하지 못해 빌드가 멈춥니다."
        )
    print(f"[자원] 실효 CPU={eff} (nproc 아님) → 워커당 CPU={cpu_per_worker}, 워커={args.workers}개")

    # --- 버킷 설정 ---
    if args.fix_append:
        bucket_config = BucketConfig(
            prefill_buckets=QWEN25_05B_PREFILL,
            decode_buckets=QWEN25_05B_DECODE,
            append_buckets=QWEN25_05B_APPEND,
            tokenwise_seq_lens=QWEN25_05B_TOKENWISE,
        )
    else:
        bucket_config = BucketConfig()  # 비우면 모델별 프리셋 자동 적용

    builder = ArtifactBuilder(
        args.model,
        model_config=ModelConfig(max_model_len=args.max_model_len),
        parallel_config=ParallelConfig(tensor_parallel_size=args.tensor_parallel_size),
        bucket_config=bucket_config,
    )

    b = builder._buckets
    print("\n=== Resolved buckets ===")
    print(f"  model          : {args.model}")
    print(f"  max_model_len  : {builder._max_model_len}")
    print(f"  prefill/decode : {len(b.prefill_buckets)} / {len(b.decode_buckets)}")
    print(f"  append_buckets : {len(b.append_buckets)}   (0이면 prefix caching 이 꺼진다!)")
    total = len(b.prefill_buckets) + len(b.decode_buckets) + len(b.append_buckets)
    print(f"  → 총 파이프라인 약 {total}개")

    if args.dry_run:
        print("\n[dry-run] 검증 통과. 컴파일하지 않음.")
        return

    print(f"\n빌드 시작 → {args.output}")
    builder.build(
        args.output,
        num_compile_workers=args.workers,
        num_cpu_per_compile_worker=cpu_per_worker,
        num_pipeline_builder_workers=args.workers,
        num_cpu_per_pipeline_build_worker=cpu_per_worker,
    )
    print(f'빌드 완료. 사용:  LLM("{args.output}")')


if __name__ == "__main__":
    main()
