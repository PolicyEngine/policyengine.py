from __future__ import annotations

import urllib.parse
from typing import Any, Optional

from .types import BundleImportError, HuggingFaceReference


def parse_hf_reference_if_present(value: Any) -> Optional[HuggingFaceReference]:
    if not isinstance(value, str):
        return None
    try:
        return parse_hf_reference(value)
    except BundleImportError:
        return None


def parse_hf_reference(uri: str) -> HuggingFaceReference:
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != "hf":
        raise BundleImportError(f"Expected hf:// URI, got {uri!r}.")
    repo_type, rest = hf_repo_type_and_reference(parsed)
    repo_id, revision, path = parse_hf_reference_parts(rest)
    return HuggingFaceReference(
        repo_type=repo_type,
        repo_id=repo_id,
        revision=revision,
        path=path,
    )


def hf_repo_type_and_reference(
    parsed: urllib.parse.ParseResult,
) -> tuple[str, str]:
    if parsed.netloc in {"model", "dataset", "space"}:
        return parsed.netloc, parsed.path.lstrip("/")
    return "model", f"{parsed.netloc}{parsed.path}"


def parse_hf_reference_parts(rest: str) -> tuple[str, str, str]:
    if "@" not in rest:
        raise BundleImportError(
            "HF URIs must include an immutable revision, for example "
            "hf://model/org/repo@version/path."
        )

    repo_id, revision_and_path = rest.split("@", 1)
    if "/" in revision_and_path:
        revision, path = revision_and_path.split("/", 1)
        if repo_id and revision and path:
            return repo_id, revision, path

    repo_and_path, revision = rest.rsplit("@", 1)
    parts = repo_and_path.split("/")
    if len(parts) < 3:
        raise BundleImportError(
            "Legacy HF URIs must use hf://org/repo/path@revision form."
        )
    repo_id = "/".join(parts[:2])
    path = "/".join(parts[2:])
    if not repo_id or not revision or not path:
        raise BundleImportError(f"Incomplete HF URI reference: {rest!r}.")
    return repo_id, revision, path
