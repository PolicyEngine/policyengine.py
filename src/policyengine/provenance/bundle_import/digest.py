from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .io import load_json
from .types import BundleImportError


def verify_bundle_digest(bundle_dir: Path, bundle: dict) -> None:
    expected = bundle.get("bundle_digest")
    if not isinstance(expected, str) or not expected.startswith("sha256:"):
        raise BundleImportError("bundle.json does not include bundle_digest.")
    actual = f"sha256:{bundle_directory_digest(bundle_dir)}"
    if actual != expected:
        raise BundleImportError(
            "bundle.json bundle_digest does not match bundle contents: "
            f"expected {expected}, got {actual}."
        )


def bundle_directory_digest(bundle_dir: Path) -> str:
    hasher = hashlib.sha256()
    for relative_path in bundle_files(bundle_dir):
        content = normalized_file_content(bundle_dir, relative_path)
        hasher.update(relative_path.as_posix().encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(content.encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def bundle_files(bundle_dir: Path) -> list[Path]:
    return sorted(
        path.relative_to(bundle_dir)
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    )


def normalized_file_content(bundle_dir: Path, relative_path: Path) -> str:
    path = bundle_dir / relative_path
    if relative_path.suffix == ".json":
        payload = load_json(path)
        if relative_path.as_posix() == "bundle.json":
            payload.pop("created_at", None)
            payload.pop("bundle_digest", None)
        elif relative_path.as_posix() == "validation-report.json":
            payload.pop("generated_at", None)
            checks = []
            for check in payload.get("checks", []):
                if not isinstance(check, dict):
                    checks.append(check)
                    continue
                check_payload = dict(check)
                check_payload.pop("command", None)
                check_payload.pop("started_at", None)
                check_payload.pop("ended_at", None)
                details = check_payload.get("details")
                if isinstance(details, dict):
                    details_payload = dict(details)
                    details_payload.pop("validated_on_platform", None)
                    details_payload.pop("bundle_dir", None)
                    check_payload["details"] = details_payload
                checks.append(check_payload)
            payload["checks"] = checks
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return path.read_text()


# Backward-compatible private name used by importer tests.
_bundle_directory_digest = bundle_directory_digest
