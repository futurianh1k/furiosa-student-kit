"""Qwen2.5-0.5B-Instruct 아티팩트를 append_buckets 포함해서 직접 빌드한다.

배경
----
허브의 기성 아티팩트(furiosa-ai/Qwen2.5-0.5B-Instruct)는 append 버킷 없이 빌드돼 있다.
근본 원인은 furiosa_llm/artifact/presets.py 의 QWEN_2_5_0D5B_PRESET 에
append_buckets 가 누락된 것 (다른 프리셋 - Llama 3.1/3.3, EXAONE, Qwen3 - 에는 전부 있음).

그 결과 런타임이 다음 두 기능을 자동으로 끈다 (alloutput.log 의 WARN 두 줄):
  - chunked prefill  : 긴 프롬프트를 잘라서 넣지 못함
  - prefix caching   : 공통 프롬프트 접두사 재사용 불가 → 요청마다 전체 재계산

이 스크립트는 프리셋의 나머지 3개 필드를 그대로 유지한 채 append_buckets 만 채워서
아티팩트를 다시 빌드한다.

사용법
------
  python build_qwen05b_artifact.py --dry-run   # 버킷 해석/검증만, 컴파일 안 함
  python build_qwen05b_artifact.py             # 실제 빌드 (오래 걸림)
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

# 베이스 모델(HF 원본). 허브의 furiosa-ai/... 은 이미 컴파일된 아티팩트라 재빌드 입력으로 쓰지 않는다.
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"

# alloutput.log 의 max_executable_len=4096 과 동일하게 맞춘다.
MAX_MODEL_LEN = 4096

# 로그의 Parallelism Config: tp=4. (dp=2 는 빌드 타임이 아니라 LLM() 로드 타임 파라미터라 여기 없음)
TENSOR_PARALLEL_SIZE = 4

# --- 버킷 정의 -------------------------------------------------------------
# 아래 3개는 QWEN_2_5_0D5B_PRESET (presets.py:70) 원본 값 그대로.
PREFILL_BUCKETS = ((1, 1024), (1, 2048), (1, 3072), (1, 4096))
DECODE_BUCKETS = ((128, 1024), (128, 2048), (128, 3072), (128, 4096))
TOKENWISE_SEQ_LENS = (128, 1024, 2048, 3072, 4096)

# append_buckets 만 새로 추가. 형식은 (batch_size, attention_size, input_ids_size) 3-튜플이고
# attention_size > input_ids_size 여야 한다 (types/config.py:53, resolver.py:106).
# 이 컨테이너는 cgroup 으로 CPU 15개 + /dev/shm 64MB(디스크 폴백) 제약이 있다.
# 파이프라인 1개당 컴파일 비용이 크고 워커 간 객체 전달이 디스크를 타므로,
# 34개(attn x input 전조합)는 과하다. 실사용에서 의미 있는 대표 조합 6개만 남긴다.
# 형식: (batch_size, attention_size, input_ids_size), attention_size > input_ids_size.
# attn 은 컨텍스트 구간(1024/2048/4096), input 은 한 번에 이어붙일 토큰 수(128/512).
APPEND_BUCKETS = (
    (1, 1024, 128),
    (1, 1024, 512),
    (1, 2048, 128),
    (1, 2048, 512),
    (1, 4096, 128),
    (1, 4096, 512),
)


def make_builder() -> ArtifactBuilder:
    # 생성 모델은 4개 버킷 필드를 전부 채우거나 전부 비워야 한다. 하나만 채우면
    # "Partial bucket configuration is not allowed" 로 죽는다 (resolver.py:71-83).
    bucket_config = BucketConfig(
        prefill_buckets=PREFILL_BUCKETS,
        decode_buckets=DECODE_BUCKETS,
        append_buckets=APPEND_BUCKETS,
        tokenwise_seq_lens=TOKENWISE_SEQ_LENS,
    )

    # ArtifactBuilder 생성자가 버킷 해석 + 검증까지 다 한다(컴파일은 .build() 에서).
    return ArtifactBuilder(
        MODEL_ID,
        name="qwen2.5-0.5b-instruct-append",
        model_config=ModelConfig(max_model_len=MAX_MODEL_LEN),
        parallel_config=ParallelConfig(tensor_parallel_size=TENSOR_PARALLEL_SIZE),
        bucket_config=bucket_config,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="버킷 해석/검증 결과만 출력하고 컴파일하지 않는다.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("./qwen2.5-0.5b-artifact"),
        help="빌드 산출물을 쓸 디렉터리 (default: ./qwen2.5-0.5b-artifact)",
    )
    # ★ 이 컨테이너의 실제 자원은 cgroup CPU 15개 (nproc 128 은 호스트 코어, 무의미).
    # 제약 두 가지가 설정을 지배한다:
    #  1) 워커당 CPU(=ray num_cpus=OMP 스레드) 는 15 를 넘으면 안 된다.
    #     넘으면 ray 가 그 액터를 아예 배치 못 해 0/N 에서 멈춘다.
    #  2) /dev/shm 이 64MB 라 ray 오브젝트 스토어가 디스크로 폴백한다. 워커가 많을수록
    #     워커 간 객체 전달(디스크 I/O)이 늘어 느려지므로, 워커는 적게 / CPU 는 크게 준다.
    # 두 단계(파이프라인 빌드 / 컴파일)는 순차라 각각 15 를 채워도 겹치지 않는다.
    parser.add_argument("--num-compile-workers", type=int, default=1)
    parser.add_argument("--num-cpu-per-compile-worker", type=int, default=12)   # 1 x 12
    parser.add_argument("--num-pipeline-builder-workers", type=int, default=1)
    parser.add_argument("--num-cpu-per-pipeline-build-worker", type=int, default=12)  # 1 x 12
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    builder = make_builder()
    buckets = builder._buckets  # ResolvedBuckets (공개 프로퍼티가 없어 내부 필드 사용)

    print("\n=== Resolved buckets ===")
    print(f"model             : {MODEL_ID}")
    print(f"max_model_len     : {builder._max_model_len}")
    print(f"tensor_parallel   : {TENSOR_PARALLEL_SIZE}")
    print(f"prefill_buckets   : {len(buckets.prefill_buckets)}")
    print(f"decode_buckets    : {len(buckets.decode_buckets)}")
    print(f"append_buckets    : {len(buckets.append_buckets)}   <-- 기성 아티팩트에는 0개")
    print(f"tokenwise_seq_lens: {list(buckets.tokenwise_seq_lens)}")

    print("\n--- append_buckets (batch, attention_size, input_ids_size) ---")
    for b in APPEND_BUCKETS:
        print(f"  {b}")

    if args.dry_run:
        print("\n[dry-run] 검증 통과. 컴파일은 하지 않았다.")
        return

    print(f"\n빌드 시작 → {args.output}")
    print(
        f"compile: {args.num_compile_workers} workers x {args.num_cpu_per_compile_worker} cpu, "
        f"pipeline: {args.num_pipeline_builder_workers} workers x "
        f"{args.num_cpu_per_pipeline_build_worker} cpu"
    )
    builder.build(
        args.output,
        num_compile_workers=args.num_compile_workers,
        num_cpu_per_compile_worker=args.num_cpu_per_compile_worker,
        num_pipeline_builder_workers=args.num_pipeline_builder_workers,
        num_cpu_per_pipeline_build_worker=args.num_cpu_per_pipeline_build_worker,
    )
    print("빌드 완료.")
    print(f'이제 이렇게 쓰면 된다:  LLM("{args.output}")')


if __name__ == "__main__":
    main()
