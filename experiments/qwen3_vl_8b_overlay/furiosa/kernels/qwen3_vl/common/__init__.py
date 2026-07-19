from __future__ import annotations

from furiosa.kernels.qwen3_vl._overlay_paths import extend_package_path

extend_package_path(__path__, ("furiosa", "kernels", "qwen3_vl", "common"), __file__)
