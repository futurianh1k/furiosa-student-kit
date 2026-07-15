"""Furiosa LLM artifact build helper - Codex-reviewed variant.

This file intentionally leaves the original ``build_artifact.py`` untouched.

Main differences from the original:
1. ``--workers`` participates in automatic CPU budgeting.
2. total requested CPU is validated: workers * cpu_per_worker <= effective CPUs.
3. private ``ArtifactBuilder`` attributes fail fast with a clear message if the
   installed ``furiosa_llm`` API changes.
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from furiosa_llm.artifact import (
    ArtifactBuilder,
    BucketConfig,
    ModelConfig,
    ParallelConfig,
)


QWEN25_05B_APPEND = (
    (1, 1024, 128), (1, 1024, 512),
    (1, 2048, 128), (1, 2048, 512),
    (1, 4096, 128), (1, 4096, 512),
)
QWEN25_05B_PREFILL = ((1, 1024), (1, 2048), (1, 3072), (1, 4096))
QWEN25_05B_DECODE = ((128, 1024), (128, 2048), (128, 3072), (128, 4096))
QWEN25_05B_TOKENWISE = (128, 1024, 2048, 3072, 4096)


def effective_cpus() -> int:
    """Return cgroup-limited CPUs. Do not trust host-level nproc/os.cpu_count."""
    v2 = Path("/sys/fs/cgroup/cpu.max")
    if v2.is_file():
        quota, period = v2.read_text().split()
        if quota == "max":
            return os.cpu_count() or 1
        return max(1, int(quota) // int(period))

    quota_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota_path.is_file() and period_path.is_file():
        quota = int(quota_path.read_text())
        period = int(period_path.read_text())
        if quota <= 0:
            return os.cpu_count() or 1
        return max(1, quota // period)

    return os.cpu_count() or 1


def positive_int(name: str, value: int) -> int:
    if value < 1:
        raise SystemExit(f"{name} must be >= 1, got {value}.")
    return value


def resolve_worker_cpu(workers: int, requested_cpu_per_worker: int, effective_cpu: int) -> int:
    positive_int("--workers", workers)
    if requested_cpu_per_worker < 0:
        raise SystemExit(f"--cpu-per-worker must be 0(auto) or >= 1, got {requested_cpu_per_worker}.")

    if requested_cpu_per_worker:
        cpu_per_worker = requested_cpu_per_worker
    else:
        # Keep one CPU for the driver, then divide the remaining budget across workers.
        cpu_per_worker = max(1, (effective_cpu - 1) // workers)

    total_cpu = workers * cpu_per_worker
    if total_cpu > effective_cpu:
        raise SystemExit(
            f"workers({workers}) * cpu-per-worker({cpu_per_worker}) = {total_cpu} "
            f"> effective CPUs({effective_cpu}). Reduce --workers or --cpu-per-worker."
        )
    return cpu_per_worker


def private_attr(obj: Any, attr: str) -> Any:
    if not hasattr(obj, attr):
        raise SystemExit(
            f"The installed furiosa_llm no longer exposes ArtifactBuilder.{attr}. "
            "This student helper relies on that internal field to show resolved buckets. "
            "Pin the known-good furiosa_llm version or update this script for the new API."
        )
    return getattr(obj, attr)


def make_bucket_config(fix_append: bool) -> BucketConfig:
    if not fix_append:
        return BucketConfig()

    return BucketConfig(
        prefill_buckets=QWEN25_05B_PREFILL,
        decode_buckets=QWEN25_05B_DECODE,
        append_buckets=QWEN25_05B_APPEND,
        tokenwise_seq_lens=QWEN25_05B_TOKENWISE,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True, help="HF model ID or local base-model path")
    parser.add_argument("-o", "--output", type=Path, default=Path("./artifact"))
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--tensor-parallel-size", type=int, default=4)
    parser.add_argument(
        "--fix-append",
        action="store_true",
        help="Fill missing Qwen2.5-0.5B append_buckets. Do not use for models with complete presets.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Resolve buckets without compiling")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Compile/pipeline worker count. Keep at 1 when /dev/shm is small.",
    )
    parser.add_argument(
        "--cpu-per-worker",
        type=int,
        default=0,
        help="CPUs per worker. 0 means auto-calculate from cgroup effective CPUs.",
    )
    args = parser.parse_args()

    positive_int("--max-model-len", args.max_model_len)
    positive_int("--tensor-parallel-size", args.tensor_parallel_size)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    effective_cpu = effective_cpus()
    cpu_per_worker = resolve_worker_cpu(args.workers, args.cpu_per_worker, effective_cpu)
    total_cpu = args.workers * cpu_per_worker
    mode = "manual" if args.cpu_per_worker else "auto"
    print(
        f"[resources] effective CPUs={effective_cpu} (not nproc) -> "
        f"workers={args.workers}, cpu_per_worker={cpu_per_worker} ({mode}), total={total_cpu}"
    )

    builder = ArtifactBuilder(
        args.model,
        model_config=ModelConfig(max_model_len=args.max_model_len),
        parallel_config=ParallelConfig(tensor_parallel_size=args.tensor_parallel_size),
        bucket_config=make_bucket_config(args.fix_append),
    )

    buckets = private_attr(builder, "_buckets")
    max_model_len = private_attr(builder, "_max_model_len")

    print("\n=== Resolved buckets ===")
    print(f"  model          : {args.model}")
    print(f"  max_model_len  : {max_model_len}")
    print(f"  prefill/decode : {len(buckets.prefill_buckets)} / {len(buckets.decode_buckets)}")
    print(f"  append_buckets : {len(buckets.append_buckets)}   (0 disables prefix caching)")
    total_pipelines = len(buckets.prefill_buckets) + len(buckets.decode_buckets) + len(buckets.append_buckets)
    print(f"  total pipelines: about {total_pipelines}")

    if args.dry_run:
        print("\n[dry-run] Bucket resolution passed. No compilation was run.")
        return

    print(f"\nBuild start -> {args.output}")
    builder.build(
        args.output,
        num_compile_workers=args.workers,
        num_cpu_per_compile_worker=cpu_per_worker,
        num_pipeline_builder_workers=args.workers,
        num_cpu_per_pipeline_build_worker=cpu_per_worker,
    )
    print(f'Build complete. Use: LLM("{args.output}")')


if __name__ == "__main__":
    main()
