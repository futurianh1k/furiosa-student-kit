"""실습 ③: Llama-3.1-8B-Instruct 아티팩트 빌드 — 독립 실행본

이 파일은 _kit/scripts/build_artifact.py 를 건드리지 않고, Llama 전용으로
모델 ID를 박아 넣은 자립 스크립트입니다. (원본은 Qwen2.5 레퍼런스로 동결)

이 실습의 교훈: 어떤 모델은 다운로드 자체가 막혀 있다(gated).
------------------------------------------------
Llama 는 프리셋(버킷)이 완비돼 있어 빌드 자체는 Qwen3 와 똑같이 단순하다.
진짜 관문은 "인증"이다. HF 토큰 없이 dry-run 하면 403 GatedRepoError 로 실패한다.

  1) https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct 에서 Access 요청(승인 필요)
  2) https://huggingface.co/settings/tokens 에서 토큰 발급
  3) huggingface-cli login   (또는  export HF_TOKEN=hf_xxx)   ← 토큰은 절대 코드/깃에 넣지 말 것

사용법
------
  bash ../_kit/scripts/check_resources.sh                # 0) 자원 먼저 (8B라 RAM 여유 확인)
  huggingface-cli login                                  #    (최초 1회) 토큰 로그인
  python build_llama.py --dry-run                        # 1) 버킷 해석만 확인
  python build_llama.py -o ./llama31-8b-artifact         # 2) 실제 빌드 (0.5B보다 오래 걸림)
  python ../_kit/scripts/verify_artifact.py --artifact ./llama31-8b-artifact | tee verify.log
"""

import argparse
import logging
import os
from pathlib import Path

from furiosa_llm.artifact import ArtifactBuilder, ModelConfig, ParallelConfig

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"  # 프리셋 완비 ✓, 하지만 gated


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
    ap.add_argument("-o", "--output", type=Path, default=Path("./llama31-8b-artifact"))
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--tensor-parallel-size", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="버킷 검증만, 컴파일 안 함")
    ap.add_argument("--workers", type=int, default=1, help="/dev/shm 이 작으면 1 권장")
    ap.add_argument("--cpu-per-worker", type=int, default=0, help="0이면 cgroup 실효CPU에서 자동 계산")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # 인증 힌트: 토큰이 전혀 안 잡히면 미리 알려준다(그래도 실제 판정은 다운로드가 함).
    if not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            or (Path.home() / ".cache/huggingface/token").is_file()):
        print("[주의] HF 토큰이 안 보입니다. gated 모델이라 403 이 날 수 있어요.")
        print("       huggingface-cli login  또는  export HF_TOKEN=hf_xxx  먼저 하세요.\n")

    eff = effective_cpus()
    cpu_per_worker = args.cpu_per_worker or max(1, eff - 1)
    if cpu_per_worker > eff:
        raise SystemExit(f"cpu-per-worker({cpu_per_worker}) > 실효 CPU({eff}). 빌드가 멈춥니다.")
    print(f"[자원] 실효 CPU={eff} (nproc 아님) → 워커당 CPU={cpu_per_worker}, 워커={args.workers}개")

    # Llama 는 프리셋이 완비돼 있으므로 BucketConfig 를 넘기지 않는다(자동 프리셋 적용).
    builder = ArtifactBuilder(
        MODEL_ID,
        model_config=ModelConfig(max_model_len=args.max_model_len),
        parallel_config=ParallelConfig(tensor_parallel_size=args.tensor_parallel_size),
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
        print("\n[dry-run] 여기까지 왔으면 인증·프리셋 통과. 컴파일하지 않음.")
        return

    print(f"\n빌드 시작 → {args.output}   (8B라 0.5B보다 오래 걸리고 RAM 을 더 씁니다)")
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
