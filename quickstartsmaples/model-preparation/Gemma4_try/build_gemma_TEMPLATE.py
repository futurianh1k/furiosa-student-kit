"""실습 ④ (심화·도전): Gemma 4 12B 아티팩트 빌드 — "벽 진단판"

★ 검증 결론 (2026-07-15, 딥리서치 + Codex + 로컬 직접 실행 3중 확인):
  이 실습은 "버킷을 못 채워서" 막히는 게 아니라, **Furiosa가 Gemma 아키텍처를
  아예 구현하지 않아서** 막힌다. 즉 BucketConfig(버킷)로는 절대 해결 불가.
  이 파일은 그 벽을 코드로 '직접 확인'하도록 만든 진단판이다.
  (Gemma4_try = 도전. "안 될 수도 있다"가 정상 — 어디서 왜 막히는지 기록이 목표.)

원래 템플릿의 잘못된 전제 2가지 (교정)
--------------------------------------
  · 오류 1 "Gemma는 gated"      → Gemma **4** 는 Apache-2.0·**ungated** (HF 토큰 불필요).
                                   gated는 Gemma 3 까지. (아래 MODEL_ID 주석 참고)
  · 오류 2 "프리셋만 없다 →      → 아니다. furiosa.models 에 Gemma 구현 클래스가 없어
     버킷 4종 채우면 빌드된다"      버킷을 완벽히 채워도 .build() 가 이렇게 실패한다:
       ValueError: unsupported model: the class
       'Gemma4UnifiedForConditionalGeneration' not available in furiosa.models
     (실제 model_type 은 'gemma' 가 아니라 'gemma4_unified')

★ 함정: get_optimized_cls 는 .build() 시점(builder.py:219)에만 돈다.
  → `--dry-run`(버킷만 해석)은 **통과**한다. dry-run 통과는 거짓 양성!
    진짜 벽은 실제 빌드에서만 드러난다. 그래서 이 파일은 빌드 전에 아키텍처
    지원을 스스로 검사해(fail-fast) 긴 컴파일 낭비 없이 벽을 보여준다.

두 갭의 구분 (핵심 교훈)
  (a) 프리셋만 없음  → BucketConfig 로 해결 가능. 대상: Mistral / Phi3 / GptOss / Qwen3-VL
                       (이들은 furiosa.models 에 '구현은 있고' 프리셋만 없다)
  (b) 구현 자체 없음 → 어떤 버킷으로도 해결 불가. 대상: **Gemma (여기 해당)**

★ '진짜 버킷 설계' 실습을 하고 싶다면 → (a) 부류로 바꿔라: Mistral / Phi3 / GptOss /
  Qwen3-VL. 그건 버킷을 직접 설계해야 하고 '실제로 빌드된다'.
  (Codex 는 같은 이유로 Qwen3-VL-8B 로 선회함: docs/modeldev/2026-07-15_codex_gemma4_build_plan.md)

사용법
------
  bash ../_kit/scripts/check_resources.sh       # 0) 자원 확인
  python build_gemma_TEMPLATE.py --dry-run      # 1) 버킷 해석(통과함) — 하지만 아래 참고
  python build_gemma_TEMPLATE.py -o ./out       # 2) 아키텍처 검사에서 fail-fast(벽 확인)
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

# Gemma 4 12B: Apache-2.0, ungated(토큰 불필요), 멀티모달·encoder-free, model_type=gemma4_unified.
# 아키텍처 클래스명(= furiosa.models 에서 찾는 이름). config.json 의 architectures[0].
MODEL_ID = "google/gemma-4-12B"
HF_ARCH_CLASS = "Gemma4UnifiedForConditionalGeneration"

# ─────────────────────────────────────────────────────────────────────────────
# 버킷 4종 — "설계 예시"로 채워 둠 (Gemma 4 12B 텍스트 백본: 48층/hidden3840/16heads/
# KV8/head_dim256/vocab262144/sliding_window1024 기준, max_model_len=4096 가정).
# 형식(2026.3.0 확인): prefill/decode = (batch, attention_size) 2-튜플;
#                      append = (batch, attention_size, input_ids_size) 3-튜플, attn > input;
#                      tokenwise = int 시퀀스. 이 값들은 '구조적으로 유효'해서 dry-run 은
# 통과하지만, 아키텍처 미구현 때문에 실제 빌드는 성공하지 못한다(위 설명 참고).
# ─────────────────────────────────────────────────────────────────────────────
GEMMA_PREFILL = tuple((1, x) for x in range(128, 4096 + 1, 128))
GEMMA_DECODE = ((1, 1024), (1, 2048), (1, 4096))
GEMMA_APPEND = (
    (1, 512, 128), (1, 512, 256),
    (1, 1024, 128), (1, 1024, 512),
    (1, 2048, 512), (1, 2048, 1024),
    (1, 4096, 512), (1, 4096, 1024),
)
GEMMA_TOKENWISE = (1, 2, 4, 8, 16, 32, 64, 128, 256, 384, 512, 1024)


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


def resolve_arch_class(model_id: str, fallback: str) -> str:
    """HF config.json 에서 실제 아키텍처 클래스명을 알아낸다(가능하면). 실패 시 fallback."""
    try:
        from transformers import AutoConfig
        cfg = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
        archs = getattr(cfg, "architectures", None)
        if archs:
            return archs[0]
    except Exception as e:  # 네트워크/미설치/gated 등 — fallback 사용
        print(f"[참고] HF config 로드 실패({type(e).__name__}) → 알려진 클래스명으로 검사")
    return fallback


def assert_furiosa_supports(arch_class: str) -> None:
    """빌드 전에 Furiosa 가 이 아키텍처를 '구현'했는지 검사하고, 없으면 fail-fast.

    Furiosa 내부(optimum/modeling.py get_models_lang_class)는
    `getattr(furiosa.models, <HF아키텍처클래스명>)` 로 구현체를 찾는다.
    이 검사는 그 로직을 그대로 흉내내, 긴 컴파일을 시작하기 전에 벽을 알려준다.
    """
    try:
        import furiosa.models as fm
    except Exception as e:
        print(f"[경고] furiosa.models import 실패({e}) — 지원 검사 생략, 그대로 진행")
        return
    available = sorted(n for n in dir(fm) if n.endswith(("ForCausalLM", "ForConditionalGeneration")))
    if not hasattr(fm, arch_class):
        bar = "=" * 74
        raise SystemExit(
            f"\n{bar}\n"
            f"[벽] Furiosa 가 이 아키텍처를 구현하지 않았습니다: {arch_class}\n"
            f"     furiosa.models 에 있는 클래스: {available}\n"
            f"     → 이건 '프리셋(버킷) 부재'가 아니라 '아키텍처 구현 부재'입니다.\n"
            f"       BucketConfig 를 아무리 완벽히 채워도 해결되지 않습니다.\n"
            f"     실제 .build() 는 다음으로 실패합니다:\n"
            f"       ValueError: unsupported model: the class '{arch_class}'\n"
            f"                   not available in furiosa.models\n"
            f"     지금 빌드하면 시간만 낭비되므로 여기서 멈춥니다(fail-fast).\n"
            f"\n"
            f"     '버킷 직접 설계'를 실제로 실습하려면 → 구현은 있고 프리셋만 없는\n"
            f"     모델로 바꾸세요: Mistral / Phi3 / GptOss / Qwen3-VL (실제로 빌드됨).\n"
            f"     Furiosa 가 Gemma 를 지원하려면: furiosa.models 에 Gemma 구현(텍스트\n"
            f"     디코더 + 멀티모달용 비전/오디오 투영)과 presets.py 프리셋이 추가돼야 함.\n"
            f"{bar}"
        )
    print(f"[확인] furiosa.models 에 {arch_class} 있음 → 아키텍처 지원 OK, 계속 진행")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=Path("./gemma-artifact"))
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument(
        "--tensor-parallel-size", type=int, default=4,
        help="2026.3.0 에서는 4 또는 8 만 허용(1/2 불가). 12B 는 8 권장.",
    )
    ap.add_argument("--dry-run", action="store_true", help="버킷 검증만 (아키텍처 검사도 생략됨)")
    ap.add_argument("--workers", type=int, default=1, help="/dev/shm 이 작으면 1 권장")
    ap.add_argument("--cpu-per-worker", type=int, default=0, help="0이면 cgroup 실효CPU에서 자동 계산")
    ap.add_argument(
        "--skip-arch-check", action="store_true",
        help="아키텍처 지원 검사를 건너뛰고 곧장 빌드(진짜 ValueError 를 보고 싶을 때).",
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # 버킷 4종이 채워졌는지 (이 파일은 예시로 채워둠 → 통과)
    if not (GEMMA_PREFILL and GEMMA_DECODE and GEMMA_APPEND and GEMMA_TOKENWISE):
        raise SystemExit("GEMMA_PREFILL/DECODE/APPEND/TOKENWISE 4종을 모두 채우세요.")

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

    b_pre, b_dec, b_app = len(GEMMA_PREFILL), len(GEMMA_DECODE), len(GEMMA_APPEND)
    print("\n=== Resolved buckets (설계 예시) ===")
    print(f"  model          : {MODEL_ID}  (arch: {HF_ARCH_CLASS})")
    print(f"  prefill/decode : {b_pre} / {b_dec}")
    print(f"  append_buckets : {b_app}   (attention_size > input_ids_size 규칙 준수)")

    if args.dry_run:
        print("\n[dry-run] 버킷은 구조적으로 유효합니다. **하지만 이 통과는 거짓 양성입니다.**")
        print("  아키텍처 검사/컴파일은 안 했습니다. 실제 빌드는 아키텍처 미구현으로 실패합니다.")
        print("  벽을 확인하려면 --dry-run 없이 실행하세요.")
        return

    # ★ 빌드 전에 아키텍처 지원을 검사 → Gemma 는 여기서 fail-fast (벽 확인)
    if not args.skip_arch_check:
        arch = resolve_arch_class(MODEL_ID, HF_ARCH_CLASS)
        assert_furiosa_supports(arch)  # Gemma 면 SystemExit 로 멈춤(명확한 설명 출력)

    # 아래는 '지원되는 모델로 바꿨을 때'만 도달한다. Gemma 로는 도달 불가.
    builder = ArtifactBuilder(
        MODEL_ID,
        model_config=ModelConfig(max_model_len=args.max_model_len),
        parallel_config=ParallelConfig(tensor_parallel_size=args.tensor_parallel_size),
        bucket_config=bucket_config,
    )
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
