"""Install the local Furiosa kernel overlay when this directory is on PYTHONPATH."""

from __future__ import annotations

from pathlib import Path


def _prepend_overlay_kernel_path() -> None:
    overlay_kernels = Path(__file__).resolve().parent / "furiosa" / "kernels"
    if not overlay_kernels.is_dir():
        return

    try:
        import furiosa.kernels as kernels
    except Exception:
        return

    overlay_text = str(overlay_kernels)
    kernel_paths = getattr(kernels, "__path__", None)
    if kernel_paths is None or overlay_text in kernel_paths:
        return

    kernel_paths.insert(0, overlay_text)


_prepend_overlay_kernel_path()
