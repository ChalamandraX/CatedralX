"""Canonical external paths used by CatedralX components."""
from __future__ import annotations

import os
from pathlib import Path


def canonical_state_path() -> Path:
    """Return the single configured state path, outside the repository."""
    configured = os.environ.get("CATEDRALX_STATE_PATH")
    candidate = (
        Path(configured).expanduser()
        if configured
        else (
            Path.home()
            / ".local"
            / "state"
            / "chalamandra"
            / "catedralx"
            / "hormonas.json"
        )
    )
    resolved = candidate.resolve()
    repo_root = Path(__file__).resolve().parents[2]
    if resolved == repo_root or repo_root in resolved.parents:
        raise ValueError(
            "CATEDRALX_STATE_PATH debe estar fuera del repositorio de CatedralX."
        )
    return resolved
