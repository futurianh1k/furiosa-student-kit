# Qwen3-VL 8B Furiosa kernel overlay

This overlay is an experiment for `Qwen/Qwen3-VL-8B-Instruct`.

It does not modify the installed Furiosa SDK. Instead, run Python/Furiosa
commands with this directory on `PYTHONPATH`:

```bash
PYTHONPATH=/root/works/experiments/qwen3_vl_8b_overlay python experiments/qwen3_vl_8b_overlay/probe_qwen3_vl_8b_overlay.py
PYTHONPATH=/root/works/experiments/qwen3_vl_8b_overlay fxb build Qwen/Qwen3-VL-8B-Instruct ./qwen3-vl-8b-instruct-rngd-256-overlay.fxb -tp 8 --max-model-len 256 -O O0 --concurrency 1
```

The current experiment keeps the native registry fallback name
`qwen3_vl_32b_w16a16_txt_first_tokenwise`, but when the incoming HF config
matches Qwen3-VL 8B dimensions it routes that one kernel through the generic
naive Qwen3-VL text-first implementation. This specifically probes the earlier
failure at the optimized `hidden_states_pinned` layout hint.

If this passes, the next failing kernel should be patched in the same narrow
style before considering any Rust/native registry change.
