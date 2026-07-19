from __future__ import annotations

from pathlib import Path

import furiosa.kernels
import furiosa.kernels.qwen3_vl as qwen3_vl
from furiosa.kernels.qwen3_vl.common.model_config import QWEN3_VL_8B_CONFIG
from furiosa.kernels.qwen3_vl.naive.qwen3_vl_8b_w16a16 import (
    qwen3_vl_8b_w16a16_txt_first_tokenwise,
)
from furiosa.kernels.qwen3_vl.optimized.entry_function import (
    _is_qwen3_vl_8b_config,
    _load_hf_config,
    qwen3_vl_32b_w16a16_txt_first_tokenwise,
)


def _overrides_for_8b() -> dict:
    return {
        "text_config": QWEN3_VL_8B_CONFIG["text_config"],
        "vision_config": QWEN3_VL_8B_CONFIG["vision_config"],
    }


def main() -> None:
    overlay_root = Path(__file__).resolve().parent
    print(f"overlay_root={overlay_root}")
    print(f"furiosa.kernels.__path__={list(furiosa.kernels.__path__)}")
    print(f"qwen3_vl.__file__={qwen3_vl.__file__}")

    text_cfg = QWEN3_VL_8B_CONFIG["text_config"]
    vision_cfg = QWEN3_VL_8B_CONFIG["vision_config"]
    print(
        "8b_config="
        f"D={text_cfg['hidden_size']} "
        f"F={text_cfg['intermediate_size']} "
        f"L={text_cfg['num_hidden_layers']} "
        f"Hq={text_cfg['num_attention_heads']} "
        f"Hkv={text_cfg['num_key_value_heads']} "
        f"vision_out={vision_cfg['out_hidden_size']}"
    )

    direct_kernel = qwen3_vl_8b_w16a16_txt_first_tokenwise(
        num_tokens=4,
        num_kv_cache_blocks=1,
    )
    print(f"direct_8b_naive_txt_first={type(direct_kernel).__name__}")

    fallback_config = _load_hf_config(_overrides_for_8b())
    print(f"fallback_detects_8b={_is_qwen3_vl_8b_config(fallback_config)}")
    fallback_kernel = qwen3_vl_32b_w16a16_txt_first_tokenwise(
        num_tokens=4,
        num_kv_cache_blocks=1,
        hf_config_overrides=_overrides_for_8b(),
    )
    print(f"patched_32b_name_txt_first={type(fallback_kernel).__name__}")


if __name__ == "__main__":
    main()
