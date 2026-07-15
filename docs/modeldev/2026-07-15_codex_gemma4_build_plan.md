# Gemma4 12B on Furiosa RNGD Build Plan

Date: 2026-07-15
Author: Codex
Status: Deferred in favor of Qwen3-VL 8B bring-up

## Summary

The original goal was to fill `quickstartsmaples/model-preparation/Gemma4_try/build_gemma_TEMPLATE.py`
and attempt to build a Gemma4 12B artifact for one Furiosa RNGD NPU with 48GB HBM.

After reviewing Hugging Face, the Gemma 4 technical report, Furiosa-LLM docs, and the
local Furiosa SDK, the recommended path is not to start with Gemma4. The main blocker is
architecture support: Gemma4 is not listed in Furiosa's supported model architectures, and
the installed local `furiosa.models` package does not expose a Gemma/Gemma4 implementation.

The Gemma4 work should therefore be treated as a future architecture-support investigation,
not as a normal bucket-filling exercise.

## Findings

- `google/gemma-4-12B` is a multimodal model using a Gemma4 unified architecture.
- The 12B variant is roughly feasible from a raw weight-memory perspective on 48GB HBM
  for short-context experiments, but that is not enough for Furiosa execution.
- Current Furiosa supported model documentation lists EXAONE, Llama, Solar, Qwen2.5,
  Qwen3, Qwen3-MoE, and Qwen3-VL. Gemma/Gemma4 is not listed.
- The installed SDK contains optimized architecture modules for Qwen3-VL, Qwen3,
  Qwen3-MoE, Llama, EXAONE, and others, but no Gemma module.
- Furiosa multimodal serving currently supports image/video parsing paths, but the local
  model implementations decide which modalities actually run. Audio is not a practical
  Gemma4 target in the current stack.

## Recommended Plan If Resumed

1. Keep `Gemma4_try/build_gemma_TEMPLATE.py` as a student challenge template rather than
   turning it into a promised working build.
2. Add explicit fail-fast diagnostics:
   - print the HF model architecture and model type,
   - check whether Furiosa can resolve an optimized model class,
   - explain that missing architecture support cannot be fixed by bucket config alone.
3. If Furiosa later adds Gemma4 support, start with:
   - `tensor_parallel_size=8`,
   - `max_model_len=4096`,
   - batch 1,
   - text-only validation before any multimodal request.
4. Use FXB as the primary build path:
   - `fxb build google/gemma-4-12B-it ./gemma4-12b-test.fxb --dry-run -tp 8 --max-model-len 4096 -O O0`
5. Only after dry-run succeeds, attempt a real build with conservative concurrency:
   - `--concurrency 1`

## Decision

Defer Gemma4 12B and begin with `Qwen/Qwen3-VL-8B-Instruct`, because Qwen3-VL is present
in the local Furiosa SDK and listed in the current Furiosa supported model documentation.

## References

- https://huggingface.co/google/gemma-4-12B
- https://arxiv.org/abs/2607.02770
- https://developer.furiosa.ai/latest/en/furiosa_llm/
- https://developer.furiosa.ai/latest/en/furiosa_llm/supported_models.html
- https://developer.furiosa.ai/latest/en/furiosa_llm/fxb.html
