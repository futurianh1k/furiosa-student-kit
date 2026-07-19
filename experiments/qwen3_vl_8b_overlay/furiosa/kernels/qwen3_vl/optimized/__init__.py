from __future__ import annotations

from furiosa.kernels.qwen3_vl._overlay_paths import extend_package_path

extend_package_path(__path__, ("furiosa", "kernels", "qwen3_vl", "optimized"), __file__)

from .entry_function import (
    qwen3_vl_32b_w16a16_txt_first_tokenwise,
    qwen3_vl_32b_w16a16_txt_mid_tokenwise,
    qwen3_vl_32b_w16a16_txt_mid_tokenwise_with_deepstack,
    qwen3_vl_32b_w16a16_txt_text_pre,
    qwen3_vl_32b_w16a16_txt_last_tokenwise_with_lm_head,
    qwen3_vl_32b_w16a16_txt_full_attention,
    qwen3_vl_32b_w16a16_txt_full_attention_with_valid_length,
    qwen3_vl_32b_w16a16_vis_first_block,
    qwen3_vl_32b_w16a16_vis_mid_block,
    qwen3_vl_32b_w16a16_vis_mid_block_with_deepstack,
    qwen3_vl_32b_w16a16_vis_last_block,
)

__all__ = [
    "qwen3_vl_32b_w16a16_txt_first_tokenwise",
    "qwen3_vl_32b_w16a16_txt_mid_tokenwise",
    "qwen3_vl_32b_w16a16_txt_mid_tokenwise_with_deepstack",
    "qwen3_vl_32b_w16a16_txt_text_pre",
    "qwen3_vl_32b_w16a16_txt_last_tokenwise_with_lm_head",
    "qwen3_vl_32b_w16a16_txt_full_attention",
    "qwen3_vl_32b_w16a16_txt_full_attention_with_valid_length",
    "qwen3_vl_32b_w16a16_vis_first_block",
    "qwen3_vl_32b_w16a16_vis_mid_block",
    "qwen3_vl_32b_w16a16_vis_mid_block_with_deepstack",
    "qwen3_vl_32b_w16a16_vis_last_block",
]
