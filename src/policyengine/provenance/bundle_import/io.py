from __future__ import annotations

import json
from pathlib import Path

from .types import BundleImportError


def load_json(path: Path) -> dict:
    try:
        with path.open() as file:
            payload = json.load(file)
    except (OSError, ValueError) as exc:
        raise BundleImportError(f"Could not load JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BundleImportError(f"Expected JSON object in {path}.")
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def required_dict(payload: dict, key: str) -> dict:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise BundleImportError(f"Expected object at {key}.")
    return value


def required_string(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise BundleImportError(f"Expected non-empty string at {key}.")
    return value
