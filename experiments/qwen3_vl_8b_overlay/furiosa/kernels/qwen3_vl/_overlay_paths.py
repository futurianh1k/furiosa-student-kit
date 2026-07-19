from __future__ import annotations

from pathlib import Path
import sys
from typing import MutableSequence, Sequence


def extend_package_path(
    package_path: MutableSequence[str],
    package_parts: Sequence[str],
    current_file: str,
) -> None:
    here = Path(current_file).resolve().parent
    for base_text in sys.path:
        base = Path(base_text or ".").resolve()
        candidate = base.joinpath(*package_parts)
        if candidate == here:
            continue
        if candidate.is_dir() and (candidate / "__init__.py").exists():
            candidate_text = str(candidate)
            if candidate_text not in package_path:
                package_path.append(candidate_text)


def find_package_file(
    package_parts: Sequence[str],
    filename: str,
    current_file: str,
) -> Path:
    here = Path(current_file).resolve().parent
    for base_text in sys.path:
        base = Path(base_text or ".").resolve()
        candidate_dir = base.joinpath(*package_parts)
        if candidate_dir == here:
            continue
        candidate = candidate_dir / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find {filename!r} for package {package_parts!r}")
