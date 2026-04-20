"""Refresh a country release manifest in place.

The release manifest at ``data/release_manifests/{country}.json`` pins
three artifacts by content hash:

- the country model wheel (sha256 + PyPI download URL),
- the certified microdata artifact (sha256 + HF resolve URL),
- the data package metadata used to compute the build fingerprint.

When a country bumps its PyPI wheel or HF dataset, every one of those
pins has to move together, and the TRACE TRO sidecar at
``data/release_manifests/{country}.trace.tro.jsonld`` must be
regenerated so replication reviewers see the right hashes.

This module exposes the refresh as a library function:

.. code-block:: python

    from policyengine.provenance.bundle import refresh_release_bundle

    result = refresh_release_bundle(
        country="us",
        model_version="1.653.3",
        data_version="1.83.4",
    )
    print(result.summary())

``scripts/refresh_release_bundle.py`` is a thin argparse wrapper for
operational use. Network access is required (PyPI JSON API + HF HEAD
against the dataset URI). Private country data (UK) additionally
needs ``HUGGING_FACE_TOKEN``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    get_release_manifest,
)

# ---------------------------------------------------------------------------
# Paths inside the installed / source-tree wheel.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MANIFEST_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "release_manifests"
PYPROJECT = REPO_ROOT / "pyproject.toml"


# ---------------------------------------------------------------------------
# PyPI metadata resolution
# ---------------------------------------------------------------------------


def _pypi_wheel_metadata(package: str, version: str) -> dict:
    """Return ``{"url": ..., "sha256": ...}`` for the py3-none-any wheel
    of ``package==version`` on PyPI.

    Raises if PyPI reports no matching wheel, or if multiple matching
    wheels exist with different sha256s (i.e. the release is
    unambiguous).
    """
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    with urlopen(Request(url, headers={"User-Agent": "policyengine.py"})) as f:
        payload = json.load(f)
    wheels = [
        f
        for f in payload.get("urls", [])
        if f.get("packagetype") == "bdist_wheel"
        and "py3-none-any" in f.get("filename", "")
    ]
    if not wheels:
        raise ValueError(
            f"No py3-none-any wheel found on PyPI for {package}=={version}"
        )
    sha256s = {f["digests"]["sha256"] for f in wheels}
    if len(sha256s) > 1:
        raise ValueError(
            f"Multiple distinct py3-none-any wheels for {package}=={version}: {sha256s}"
        )
    wheel = wheels[0]
    return {"url": wheel["url"], "sha256": wheel["digests"]["sha256"]}


# ---------------------------------------------------------------------------
# Hugging Face dataset resolution
# ---------------------------------------------------------------------------


def _hf_dataset_sha256(repo_id: str, path: str, revision: str) -> str:
    """Fetch the dataset file's sha256 by streaming the resolve URL.

    Uses the ``HUGGING_FACE_TOKEN`` env var for private repos. Streams
    the file in 8 MiB chunks so memory usage stays flat.
    """
    url = f"https://huggingface.co/datasets/{repo_id}/resolve/{revision}/{path}"
    headers = {"User-Agent": "policyengine.py"}
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    hasher = hashlib.sha256()
    with urlopen(Request(url, headers=headers)) as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Refresh result
# ---------------------------------------------------------------------------


@dataclass
class RefreshResult:
    """What the refresh changed, for logs and PR bodies."""

    country: str
    old_model: str
    new_model: str
    old_data: str
    new_data: str
    old_wheel_sha256: str
    new_wheel_sha256: str
    old_dataset_sha256: str
    new_dataset_sha256: str
    manifest_path: Path
    pyproject_updated: bool

    def summary(self) -> str:
        lines = [
            f"Refreshed {self.country} release bundle:",
            f"  model:   {self.old_model} -> {self.new_model}",
            f"  data:    {self.old_data} -> {self.new_data}",
            f"  wheel sha256:   {self.old_wheel_sha256[:12]}... -> "
            f"{self.new_wheel_sha256[:12]}...",
            f"  dataset sha256: {self.old_dataset_sha256[:12]}... -> "
            f"{self.new_dataset_sha256[:12]}...",
            f"  manifest:       {self.manifest_path}",
        ]
        if self.pyproject_updated:
            lines.append("  pyproject.toml: pin updated")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core refresh function
# ---------------------------------------------------------------------------


def refresh_release_bundle(
    country: str,
    *,
    model_version: Optional[str] = None,
    data_version: Optional[str] = None,
    update_pyproject: bool = True,
    manifest_dir: Path = MANIFEST_DIR,
    pyproject_path: Path = PYPROJECT,
) -> RefreshResult:
    """Refresh a country's release manifest in place.

    Args:
        country: ``"us"`` or ``"uk"``.
        model_version: New country-package version, e.g. ``"1.653.3"``.
            If ``None``, keeps the existing pin.
        data_version: New data-package version, e.g. ``"1.83.4"``. If
            ``None``, keeps the existing pin.
        update_pyproject: When True, also bumps the country extra in
            ``pyproject.toml`` to ``model_version``.
        manifest_dir: Overridable for tests.
        pyproject_path: Overridable for tests.

    Returns a :class:`RefreshResult` with the before/after of every
    content-addressed pin.
    """
    manifest_path = manifest_dir / f"{country}.json"
    manifest_json = json.loads(manifest_path.read_text())
    current = CountryReleaseManifest.model_validate(manifest_json)

    old_model = current.model_package.version
    old_data = current.data_package.version
    old_wheel_sha256 = current.model_package.sha256 or ""
    old_dataset_sha256 = current.certified_data_artifact.sha256 or ""

    new_model = model_version or old_model
    new_data = data_version or old_data

    package_name = current.model_package.name  # "policyengine-us" / "policyengine-uk"

    # Only hit PyPI if the model actually changed. Keeps no-op
    # refreshes and data-only refreshes offline for the wheel pin.
    if new_model != old_model:
        wheel = _pypi_wheel_metadata(package_name, new_model)
        new_wheel_sha256 = wheel["sha256"]
        new_wheel_url = wheel["url"]
    else:
        new_wheel_sha256 = old_wheel_sha256
        new_wheel_url = current.model_package.wheel_url or ""

    # Dataset HF resolve URL inferred from the existing URI: we only
    # change the ``@{revision}`` tail.
    current_uri = current.certified_data_artifact.uri
    repo_id_match = re.match(r"hf://([^/]+/[^/]+)/(.+?)@(.+)", current_uri)
    if not repo_id_match:
        raise ValueError(
            f"Cannot parse current dataset URI {current_uri!r}; expected "
            f"'hf://{{owner}}/{{repo}}/{{path}}@{{revision}}'"
        )
    repo_id, dataset_path, _old_revision = repo_id_match.groups()

    # Only hit HF if the data version actually changed.
    if new_data != old_data:
        new_dataset_sha256 = _hf_dataset_sha256(repo_id, dataset_path, new_data)
    else:
        new_dataset_sha256 = old_dataset_sha256
    new_uri = f"hf://{repo_id}/{dataset_path}@{new_data}"

    # Mutate the manifest JSON in place (keep unknown fields untouched).
    manifest_json["model_package"]["version"] = new_model
    manifest_json["model_package"]["sha256"] = new_wheel_sha256
    manifest_json["model_package"]["wheel_url"] = new_wheel_url
    manifest_json["data_package"]["version"] = new_data
    manifest_json["certified_data_artifact"]["data_package"]["version"] = new_data
    manifest_json["certified_data_artifact"]["build_id"] = (
        f"{current.data_package.name}-{new_data}"
    )
    manifest_json["certified_data_artifact"]["uri"] = new_uri
    manifest_json["certified_data_artifact"]["sha256"] = new_dataset_sha256
    manifest_json["certification"]["data_build_id"] = (
        f"{current.data_package.name}-{new_data}"
    )
    manifest_json["certification"]["certified_for_model_version"] = new_model

    manifest_path.write_text(
        json.dumps(manifest_json, indent=2, sort_keys=False) + "\n"
    )

    pyproject_updated = False
    if update_pyproject and model_version is not None:
        pyproject_updated = _bump_pyproject_pin(pyproject_path, package_name, new_model)

    return RefreshResult(
        country=country,
        old_model=old_model,
        new_model=new_model,
        old_data=old_data,
        new_data=new_data,
        old_wheel_sha256=old_wheel_sha256,
        new_wheel_sha256=new_wheel_sha256,
        old_dataset_sha256=old_dataset_sha256,
        new_dataset_sha256=new_dataset_sha256,
        manifest_path=manifest_path,
        pyproject_updated=pyproject_updated,
    )


# ---------------------------------------------------------------------------
# pyproject.toml pin update (regex-based; avoids adding a TOML writer dep)
# ---------------------------------------------------------------------------


def _bump_pyproject_pin(
    pyproject_path: Path, package_name: str, new_version: str
) -> bool:
    """Update the ``{package_name}=={version}`` line under country
    extras. Returns True if a change was written.

    Only matches the exact ``"{package_name}==X.Y.Z"`` pin form that the
    release manifests produce; any looser pin (``>=``, ``~=``, extras
    markers) is left alone and signalled via the return value.
    """
    text = pyproject_path.read_text()
    pattern = rf'("{re.escape(package_name)}==)[^"]+(")'
    new_text, n = re.subn(pattern, rf"\g<1>{new_version}\g<2>", text)
    if n == 0:
        return False
    if new_text != text:
        pyproject_path.write_text(new_text)
        return True
    return False


# ---------------------------------------------------------------------------
# Trace TRO regeneration
# ---------------------------------------------------------------------------


def regenerate_trace_tro(country: str, manifest_dir: Path = MANIFEST_DIR) -> Path:
    """Regenerate ``{country}.trace.tro.jsonld`` from the country's
    release manifest + the live data-release manifest on HF.

    Thin wrapper around the same code path ``scripts/generate_trace_tros.py``
    uses; exposed here so the refresh function can chain
    ``refresh_release_bundle(...)`` with TRO regeneration in one call.
    """
    from policyengine.provenance.manifest import get_data_release_manifest
    from policyengine.provenance.trace import (
        build_trace_tro_from_release_bundle,
        serialize_trace_tro,
    )

    release = get_release_manifest(country)
    data_release = get_data_release_manifest(country)
    tro = build_trace_tro_from_release_bundle(release, data_release)
    out_path = manifest_dir / f"{country}.trace.tro.jsonld"
    out_path.write_bytes(serialize_trace_tro(tro))
    return out_path
