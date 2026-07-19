from __future__ import annotations

from furiosa.tcl.kernel import Kernel
from furiosa.kernels.common.entry_function.hf_config import copy_and_update_hf_config
from furiosa.kernels.qwen3_vl.common.model_config import (
    QWEN3_VL_8B_CONFIG as _DEFAULT_HF_CONFIG,
)
from furiosa.kernels.qwen3_vl.naive.entry_function import (
    qwen3_vl_w16a16_txt_first_tokenwise,
    qwen3_vl_w16a16_txt_mid_tokenwise,
    qwen3_vl_w16a16_txt_mid_tokenwise_with_deepstack,
    qwen3_vl_w16a16_txt_text_pre,
    qwen3_vl_w16a16_txt_last_tokenwise_with_lm_head,
    qwen3_vl_w16a16_txt_full_attention,
    qwen3_vl_w16a16_txt_full_attention_with_valid_length,
    qwen3_vl_w16a16_vis_first_block,
    qwen3_vl_w16a16_vis_mid_block,
    qwen3_vl_w16a16_vis_mid_block_with_deepstack,
    qwen3_vl_w16a16_vis_last_block,
)


def _load_hf_config(hf_config_overrides=None):
    return copy_and_update_hf_config(_DEFAULT_HF_CONFIG, hf_config_overrides)


def qwen3_vl_8b_w16a16_txt_first_tokenwise(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_txt_first_tokenwise(
        num_tokens,
        num_kv_cache_blocks,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_txt_mid_tokenwise(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_txt_mid_tokenwise(
        num_tokens,
        num_kv_cache_blocks,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_txt_mid_tokenwise_with_deepstack(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_txt_mid_tokenwise_with_deepstack(
        num_tokens,
        num_kv_cache_blocks,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_txt_text_pre(
    num_tokens: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_txt_text_pre(
        num_tokens,
        num_kv_cache_blocks,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_txt_last_tokenwise_with_lm_head(
    num_tokens: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_txt_last_tokenwise_with_lm_head(
        num_tokens,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_txt_full_attention(
    batch_size: int,
    attention_size: int,
    input_ids_size: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_txt_full_attention(
        batch_size,
        attention_size,
        input_ids_size,
        num_kv_cache_blocks,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_txt_full_attention_with_valid_length(
    batch_size: int,
    attention_size: int,
    input_ids_size: int,
    num_kv_cache_blocks: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_txt_full_attention_with_valid_length(
        batch_size,
        attention_size,
        input_ids_size,
        num_kv_cache_blocks,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_vis_first_block(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_vis_first_block(
        batch_size,
        num_patches,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_vis_mid_block(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_vis_mid_block(
        batch_size,
        num_patches,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_vis_mid_block_with_deepstack(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_vis_mid_block_with_deepstack(
        batch_size,
        num_patches,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )


def qwen3_vl_8b_w16a16_vis_last_block(
    batch_size: int,
    num_patches: int,
    hf_config_overrides=None,
    **kwargs,
) -> Kernel:
    return qwen3_vl_w16a16_vis_last_block(
        batch_size,
        num_patches,
        _load_hf_config(hf_config_overrides),
        **kwargs,
    )
