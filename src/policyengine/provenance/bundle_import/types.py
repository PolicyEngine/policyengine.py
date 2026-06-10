from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


class BundleImportError(RuntimeError):
    """Raised when a PolicyEngine bundle cannot be imported into policyengine.py."""


@dataclass(frozen=True)
class BundleImportResult:
    bundle_version: str
    countries: list[str]
    bundle_dir: Optional[Path]
    release_manifest_paths: list[Path]
    pyproject_path: Optional[Path]
    trace_tro_paths: list[Path]
    changelog_path: Optional[Path]


@dataclass(frozen=True)
class HuggingFaceReference:
    repo_type: str
    repo_id: str
    revision: str
    path: str


TroRegenerator = Callable[[str, Path], Path]
