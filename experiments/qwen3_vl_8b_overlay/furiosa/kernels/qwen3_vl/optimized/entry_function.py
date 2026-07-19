from __future__ import annotations

import importlib.util

from furiosa.tcl.kernel import Kernel
from furiosa.kernels.common.entry_function.hf_config import copy_and_update_hf_config
from furiosa.kernels.qwen3_vl._overlay_paths import find_package_file
from furiosa.kernels.qwen3_vl.common.model_config import QWEN3_VL_32B_CONFIG
from furiosa.kernels.qwen3_vl.naive.entry_function import (
    qwen3_vl_w16a16_txt_full_attention as _naive_txt_full_attention,
    qwen3_vl_w16a16_txt_full_attention_with_valid_length as _naive_txt_full_attention_with_valid_length,
    qwen3_vl_w16a16_txt_first_tokenwise as _naive_txt_first_tokenwise,
    qwen3_vl_w16a16_txt_last_tokenwise_with_lm_head as _naive_txt_last_tokenwise,
    qwen3_vl_w16a16_txt_mid_tokenwise as _naive_txt_mid_tokenwise,
    qwen3_vl_w16a16_txt_mid_tokenwise_with_deepstack as _naive_txt_mid_tokenwise_with_deepstack,
    qwen3_vl_w16a16_txt_text_pre as _naive_txt_text_pre,
    qwen3_vl_w16a16_vis_first_block as _naive_vis_first_block,
    qwen3_vl_w16a16_vis_last_block as _naive_vis_last_block,
    qwen3_vl_w16a16_vis_mid_block as _naive_vis_mid_block,
    qwen3_vl_w16a16_vis_mid_block_with_deepstack as _naive_vis_mid_block_with_deepstack,
)


def _load_original_entry_function():
    original_path = find_package_file(
        ("furiosa", "kernels", "qwen3_vl", "optimized"),
        "entry_function.py",
        __file__,
    )
    spec = importlib.util.spec_from_file_location(
        "_furiosa_original_qwen3_vl_optimized_entry_function",
        original_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load original entry_function.py at {original_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ORIGINAL = _load_original_entry_function()


def _load_hf_config(hf_config_overrides=None):
    return copy_and_update_hf_config(QWEN3_VL_32B_CONFIG, hf_config_overrides)


def _is_qwen3_vl_8b_config(hf_config: dict) -> bool:
    text_cfg = hf_config.get("text_config", {})
    vision_cfg = hf_config.get("vision_config", {})
    return (
        hf_config.get("model_type") == "qwen3_vl"
        and text_cfg.get("hidden_size") == 4096
        and text_cfg.get("intermediate_size") == 12288
        and text_cfg.get("num_hidden_layers") == 36
        and text_cfg.get("num_attention_heads") == 32
        and text_cfg.get("num_key_value_heads") == 8
        and text_cfg.get("head_dim") == 128
        and vision_cfg.get("out_hidden_size") == 4096
    )


def qwen3_vl_32b_w16a16_txt_first_tokenwise(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_txt_first_tokenwise(num_tokens, num_kv_cache_blocks, hf_config, **kwargs)
    return _ORIGINAL.qwen3_vl_32b_w16a16_txt_first_tokenwise(
        num_tokens, num_kv_cache_blocks, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_txt_mid_tokenwise(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_txt_mid_tokenwise(num_tokens, num_kv_cache_blocks, hf_config, **kwargs)
    return _ORIGINAL.qwen3_vl_32b_w16a16_txt_mid_tokenwise(
        num_tokens, num_kv_cache_blocks, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_txt_mid_tokenwise_with_deepstack(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_txt_mid_tokenwise_with_deepstack(
            num_tokens, num_kv_cache_blocks, hf_config, **kwargs
        )
    return _ORIGINAL.qwen3_vl_32b_w16a16_txt_mid_tokenwise_with_deepstack(
        num_tokens, num_kv_cache_blocks, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_txt_text_pre(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_txt_text_pre(num_tokens, num_kv_cache_blocks, hf_config, **kwargs)
    return _ORIGINAL.qwen3_vl_32b_w16a16_txt_text_pre(
        num_tokens, num_kv_cache_blocks, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_txt_last_tokenwise_with_lm_head(
    num_tokens: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_txt_last_tokenwise(num_tokens, hf_config, **kwargs)
    return _ORIGINAL.qwen3_vl_32b_w16a16_txt_last_tokenwise_with_lm_head(
        num_tokens, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_txt_full_attention(
    batch_size: int,
    attention_size: int,
    input_ids_size: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_txt_full_attention(
            batch_size, attention_size, input_ids_size, num_kv_cache_blocks, hf_config, **kwargs
        )
    return _ORIGINAL.qwen3_vl_32b_w16a16_txt_full_attention(
        batch_size, attention_size, input_ids_size, num_kv_cache_blocks, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_txt_full_attention_with_valid_length(
    batch_size: int,
    attention_size: int,
    input_ids_size: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_txt_full_attention_with_valid_length(
            batch_size, attention_size, input_ids_size, num_kv_cache_blocks, hf_config, **kwargs
        )
    return _ORIGINAL.qwen3_vl_32b_w16a16_txt_full_attention_with_valid_length(
        batch_size, attention_size, input_ids_size, num_kv_cache_blocks, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_vis_first_block(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_vis_first_block(batch_size, num_patches, hf_config, **kwargs)
    return _ORIGINAL.qwen3_vl_32b_w16a16_vis_first_block(
        batch_size, num_patches, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_vis_mid_block(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_vis_mid_block(batch_size, num_patches, hf_config, **kwargs)
    return _ORIGINAL.qwen3_vl_32b_w16a16_vis_mid_block(
        batch_size, num_patches, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_vis_mid_block_with_deepstack(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_vis_mid_block_with_deepstack(
            batch_size, num_patches, hf_config, **kwargs
        )
    return _ORIGINAL.qwen3_vl_32b_w16a16_vis_mid_block_with_deepstack(
        batch_size, num_patches, hf_config_overrides, **kwargs
    )


def qwen3_vl_32b_w16a16_vis_last_block(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    hf_config = _load_hf_config(hf_config_overrides)
    if _is_qwen3_vl_8b_config(hf_config):
        return _naive_vis_last_block(batch_size, num_patches, hf_config, **kwargs)
    return _ORIGINAL.qwen3_vl_32b_w16a16_vis_last_block(
        batch_size, num_patches, hf_config_overrides, **kwargs
    )
