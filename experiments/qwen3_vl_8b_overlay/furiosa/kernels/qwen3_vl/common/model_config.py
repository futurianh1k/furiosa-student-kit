from __future__ import annotations

import json
from pathlib import Path

from furiosa.kernels.qwen3_vl._overlay_paths import find_package_file


def _read_json(filename: str) -> dict:
    local = Path(__file__).resolve().parent / filename
    if local.is_file():
        return json.loads(local.read_text())

    original = find_package_file(
        ("furiosa", "kernels", "qwen3_vl", "common"),
        filename,
        __file__,
    )
    return json.loads(original.read_text())


QWEN3_VL_32B_CONFIG = _read_json("Qwen--Qwen3-VL-32B-Instruct.json")
QWEN3_VL_8B_CONFIG = _read_json("Qwen--Qwen3-VL-8B-Instruct.json")

# Vision rope size is determined by input bucket, so use the same large
# constant as the installed Furiosa Qwen3-VL kernels.
VISION_ROPE_MAX_POSITION_EMBEDDINGS = 131072
