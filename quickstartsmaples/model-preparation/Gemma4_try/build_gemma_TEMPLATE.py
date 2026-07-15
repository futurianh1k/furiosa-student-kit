"""실습 ④ (심화·도전): Gemma 아티팩트 빌드 — 스캐폴드(정답 없음)

이 파일은 **완성본이 아니라 뼈대**입니다. 파일명에 TEMPLATE 이 붙은 이유이고,
폴더 이름이 Gemma4_try("try")인 이유입니다. 아래 TODO 를 여러분이 직접 채워야
빌드가 됩니다. (원본 _kit/scripts/build_artifact.py 는 건드리지 마세요.)

두 개의 벽
----------
  벽 1: gated 다운로드      → 실습 ③ Llama 처럼 HF 토큰 로그인이 먼저 필요하다.
  벽 2: **프리셋이 없다**    → presets.py 에 gemma 가 없어서, 버킷을 비워두면
                              "No bucket configuration ... no matching bucket preset
                              for model_type=gemma" 로 실패한다. 4종 버킷을 전부
                              직접 정의해야 한다(부분 지정 금지).

무엇을 참고하나
--------------
  - 버킷 4종의 의미/형식: ../_kit/01_GUIDE.md
  - 값 잡는 감각: 실습 ①의 _kit/scripts/build_artifact.py 안 QWEN25_05B_* 상수,
    그리고 furiosa 의 presets.py 안 LLAMA_3_1_8B_PRESET 을 Gemma 크기에 맞게 조정
  - 규칙: append_buckets 는 (batch, attention_size, input_ids_size) 이고
          attention_size > input_ids_size 여야 한다.

절차
----
  bash ../_kit/scripts/check_resources.sh
  huggingface-cli login                          # gated → 토큰 로그인
  python build_gemma_TEMPLATE.py --dry-run       # "no matching preset" 없이 버킷이 해석되면 성공
  python build_gemma_TEMPLATE.py -o ./gemma-artifact
  python ../_kit/scripts/verify_artifact.py --artifact ./gemma-artifact | tee verify.log

성공/실패 기준
-------------
  - dry-run 에서 append_buckets 가 0보다 크고 에러가 없으면 설계 성공.
  - 빌드가 0/N 에서 멈추면 → 버킷 값이 아니라 자원 문제(워커 CPU ≤ 실효 CPU).
  - 이 실습은 "안 될 수도 있다"가 정상. 어디서 왜 막히는지 기록하는 게 목표.
"""

import argparse
import logging
import os
from pathlib import Path

from furiosa_llm.artifact import (
    ArtifactBuilder,
    BucketConfig,
    ModelConfig,
    ParallelConfig,
)

# TODO(1): 실제로 쓸 Gemma 모델 ID 로 바꾸세요 (gated 이므로 로그인 필요).
MODEL_ID = "google/gemma-3-1b-it"  # ← 예시. 접근 가능한/원하는 변형으로 교체하세요.

# ─────────────────────────────────────────────────────────────────────────────
# TODO(2): 프리셋이 없으므로 4종 버킷을 "전부" 직접 채우세요. 아래는 빈 뼈대입니다.
#          비워둔 채로 dry-run 하면 의도적으로 실패합니다(그게 벽 2의 확인 방법).
#          형식은 실습 ①의 QWEN25_05B_* 와 presets.py 의 LLAMA_3_1_8B_PRESET 참고.
# ─────────────────────────────────────────────────────────────────────────────
GEMMA_PREFILL = ()   # 예: ((1, 1024), (1, 2048), (1, 3072), (1, 4096))
GEMMA_DECODE = ()    # 예: ((128, 1024), (128, 2048), (128, 3072), (128, 4096))
GEMMA_APPEND = ()    # 예: ((1, 1024, 128), (1, 2048, 512), ...)  # attn > input
GEMMA_TOKENWISE = () # 예: (128, 1024, 2048, 3072, 4096)


def effective_cpus() -> int:
    """이 컨테이너가 실제로 쓸 수 있는 CPU 수 (cgroup). nproc 이 아니다!"""
    v2 = Path("/sys/fs/cgroup/cpu.max")
    if v2.is_file():
        quota, period = v2.read_text().split()
        if quota == "max":
            return os.cpu_count() or 1
        return max(1, int(quota) // int(period))
    q = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    p = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if q.is_file() and p.is_file():
        qi, pi = int(q.read_text()), int(p.read_text())
        if qi <= 0:
            return os.cpu_count() or 1
        return max(1, qi // pi)
    return os.cpu_count() or 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=Path("./gemma-artifact"))
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--tensor-parallel-size", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="버킷 검증만, 컴파일 안 함")
    ap.add_argument("--workers", type=int, default=1, help="/dev/shm 이 작으면 1 권장")
    ap.add_argument("--cpu-per-worker", type=int, default=0, help="0이면 cgroup 실효CPU에서 자동 계산")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # 뼈대를 안 채웠으면 친절히 멈춘다(그래도 벽 2의 원리는 dry-run 로그로 직접 보세요).
    if not (GEMMA_PREFILL and GEMMA_DECODE and GEMMA_APPEND and GEMMA_TOKENWISE):
        raise SystemExit(
            "TODO(2) 미완성: GEMMA_PREFILL/DECODE/APPEND/TOKENWISE 4종을 모두 채우세요. "
            "부분 지정은 금지입니다. (참고: _kit/01_GUIDE.md, presets.py)"
        )

    if not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            or (Path.home() / ".cache/huggingface/token").is_file()):
        print("[주의] HF 토큰이 안 보입니다. Gemma 는 gated 라 403 이 날 수 있어요.")
        print("       huggingface-cli login 먼저 하세요.\n")

    eff = effective_cpus()
    cpu_per_worker = args.cpu_per_worker or max(1, eff - 1)
    if cpu_per_worker > eff:
        raise SystemExit(f"cpu-per-worker({cpu_per_worker}) > 실효 CPU({eff}). 빌드가 멈춥니다.")
    print(f"[자원] 실효 CPU={eff} (nproc 아님) → 워커당 CPU={cpu_per_worker}, 워커={args.workers}개")

    bucket_config = BucketConfig(
        prefill_buckets=GEMMA_PREFILL,
        decode_buckets=GEMMA_DECODE,
        append_buckets=GEMMA_APPEND,
        tokenwise_seq_lens=GEMMA_TOKENWISE,
    )
    builder = ArtifactBuilder(
        MODEL_ID,
        model_config=ModelConfig(max_model_len=args.max_model_len),
        parallel_config=ParallelConfig(tensor_parallel_size=args.tensor_parallel_size),
        bucket_config=bucket_config,
    )

    b = builder._buckets
    print("\n=== Resolved buckets ===")
    print(f"  model          : {MODEL_ID}")
    print(f"  max_model_len  : {builder._max_model_len}")
    print(f"  prefill/decode : {len(b.prefill_buckets)} / {len(b.decode_buckets)}")
    print(f"  append_buckets : {len(b.append_buckets)}   (0이면 prefix caching 이 꺼진다!)")
    total = len(b.prefill_buckets) + len(b.decode_buckets) + len(b.append_buckets)
    print(f"  → 총 파이프라인 약 {total}개")

    if args.dry_run:
        print("\n[dry-run] 'no matching preset' 없이 여기까지 왔으면 버킷 설계 성공. 컴파일 안 함.")
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
