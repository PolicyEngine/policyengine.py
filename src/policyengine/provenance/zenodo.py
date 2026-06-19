"""Zenodo mirroring of certified releases.

Hugging Face hosts PolicyEngine's primary data artifacts, but it
publishes no preservation commitment: its DOIs are short URLs that die
with the repo. Zenodo publishes a preservation policy and mints real
DOIs, so a certified release mirrored there stays resolvable — and a
TRO citation can fall back to it — even if the primary host changes.

What gets deposited is the *certification record* of a release: the
bundled country manifest, the bundle TRACE TRO, and the country data
release manifest. These are small, license-unencumbered metadata files
that pin every artifact by sha256, so a future reader can verify any
copy of the data they obtain. The dataset bytes themselves are only
deposited on explicit request (``include_dataset=True``) and only when
the source Hugging Face repo is publicly readable — a private source
repo (the UK microdata, under UK Data Service licence) is refused
unconditionally, because mirroring it would republish data we do not
have the right to redistribute.

Deposits are created as drafts by default; ``publish=True`` publishes
and mints the DOI. Set deposit licensing deliberately before
publishing (the ``license`` argument, or Zenodo's web UI for drafts).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .manifest import (
    CountryReleaseManifest,
    DataReleaseManifest,
    DataReleaseManifestUnavailableError,
    PreservationMirror,
    get_data_release_manifest,
    get_release_manifest,
)
from .trace import canonical_json_bytes

ZENODO_API = "https://zenodo.org/api"
ZENODO_SANDBOX_API = "https://sandbox.zenodo.org/api"

_TIMEOUT_SECONDS = 120.0


class ZenodoDepositError(RuntimeError):
    """A Zenodo deposit step failed or was misconfigured."""


class PrivateSourceRepoError(RuntimeError):
    """Refused to mirror dataset bytes whose source repo is not public."""


@dataclass(frozen=True)
class ZenodoDeposit:
    """Outcome of mirroring one certified release to Zenodo."""

    deposit_id: str
    deposit_url: Optional[str]
    doi: Optional[str]
    concept_doi: Optional[str]
    published: bool
    mirrors: list[PreservationMirror] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "deposit_id": self.deposit_id,
            "deposit_url": self.deposit_url,
            "doi": self.doi,
            "concept_doi": self.concept_doi,
            "published": self.published,
            "mirrors": [mirror.model_dump(mode="json") for mirror in self.mirrors],
        }


def deposition_metadata(
    country_manifest: CountryReleaseManifest,
    data_release_manifest: Optional[DataReleaseManifest],
    *,
    license_id: Optional[str] = None,
) -> dict[str, Any]:
    """Zenodo deposition metadata describing a certified release.

    The description names the bundle, the data build, and the certified
    dataset hash so the deposit is self-describing without downloading
    any file. ``license_id`` is only applied when given — set it
    deliberately, especially when dataset bytes are included.
    """
    country_id = country_manifest.country_id
    bundle_id = country_manifest.bundle_id or (
        f"{country_id}-{country_manifest.policyengine_version}"
    )
    build_id = None
    if data_release_manifest is not None and data_release_manifest.build is not None:
        build_id = data_release_manifest.build.build_id
    certified = country_manifest.certified_data_artifact
    description_parts = [
        f"Certification record for the PolicyEngine {country_id} certified "
        f"release bundle {bundle_id}.",
        f"Model package: {country_manifest.model_package.name}=="
        f"{country_manifest.model_package.version}.",
        f"Data package: {country_manifest.data_package.name}=="
        f"{country_manifest.data_package.version}.",
    ]
    if build_id is not None:
        description_parts.append(f"Data build: {build_id}.")
    if certified is not None and certified.sha256 is not None:
        description_parts.append(
            f"Certified dataset {certified.dataset} sha256 {certified.sha256}."
        )
    description_parts.append(
        "The bundled TRACE Transparent Research Object pins every artifact "
        "by sha256; verify any copy with `policyengine trace-tro-verify`."
    )

    related_identifiers = []
    if certified is not None:
        from .trace import _dataset_location_from_uri

        https_location = _dataset_location_from_uri(certified.uri)
        if https_location.startswith("https://"):
            related_identifiers.append(
                {
                    "identifier": https_location,
                    "relation": "isAlternateIdentifier",
                }
            )

    metadata: dict[str, Any] = {
        "title": (
            f"PolicyEngine {country_id} certified release {bundle_id} "
            "(certification record)"
        ),
        "upload_type": "dataset",
        "description": " ".join(description_parts),
        "creators": [{"name": "PolicyEngine"}],
        "version": country_manifest.policyengine_version,
        "keywords": [
            "microsimulation",
            "tax-benefit",
            "replication",
            "TRACE",
            "provenance",
        ],
        "related_identifiers": related_identifiers,
    }
    if license_id is not None:
        metadata["license"] = license_id
    return metadata


def _bundled_tro_bytes(country_id: str) -> bytes:
    from importlib.resources import files

    resource = files("policyengine").joinpath(
        "data", "release_manifests", f"{country_id}.trace.tro.jsonld"
    )
    try:
        return resource.read_bytes()
    except FileNotFoundError as exc:
        raise ZenodoDepositError(
            f"No bundled TRACE TRO for '{country_id}'. Run "
            "scripts/generate_trace_tros.py before mirroring."
        ) from exc


def _parse_hf_uri(uri: str) -> Optional[tuple[str, str]]:
    """``hf://owner/repo/path@rev`` -> ``(repo_id, filename)``."""
    if not uri.startswith("hf://"):
        return None
    without_scheme = uri.removeprefix("hf://")
    if "@" in without_scheme:
        without_scheme, _ = without_scheme.rsplit("@", 1)
    parts = without_scheme.split("/", 2)
    if len(parts) != 3:
        return None
    return f"{parts[0]}/{parts[1]}", parts[2].rsplit("/", 1)[-1]


def _assert_source_repo_public(session: Any, repo_id: str) -> None:
    """Refuse to proceed unless the Hub repo is openly readable.

    Checked against both repo types because the registry hosts datasets
    in both. This is the licence gate: private *and gated* repos (UK Data
    Service microdata) must never have their bytes re-deposited,
    regardless of caller flags.

    A repo qualifies as openly readable only when the metadata endpoint
    returns HTTP 200 *and* its ``gated`` flag is falsey. Hugging Face
    enforces gating at the byte-download layer, so a gated repo's
    metadata returns 200 while its files are access-walled — treating a
    200 alone as "public" would let gated bytes through. The ``gated``
    field is ``false`` for open repos and a truthy string
    (``"auto"``/``"manual"``) when access is restricted.

    Definitive private/absent signals (401/403/404) refuse. Anything
    else (429, 5xx, network error) means visibility could not be
    confirmed: rather than risk depositing restricted data, refuse with
    a retryable error instead of silently treating it as public.
    """
    statuses: list[str] = []
    for repo_type in ("datasets", "models"):
        try:
            response = session.get(
                f"https://huggingface.co/api/{repo_type}/{repo_id}",
                timeout=_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # network failure: cannot confirm visibility
            statuses.append(f"{repo_type}:error")
            last_error = exc
            continue
        last_error = None
        statuses.append(f"{repo_type}:{response.status_code}")
        if response.status_code == 200:
            try:
                gated = response.json().get("gated", False)
            except Exception:
                gated = False
            if gated:
                raise PrivateSourceRepoError(
                    f"Source repo {repo_id} is gated (gated={gated!r}): its "
                    "files are access-walled even though metadata is public. "
                    "Refusing to mirror its dataset bytes; the certification "
                    "record (manifests and TRO) can still be mirrored without "
                    "the data."
                )
            return

    if any(s.endswith((":401", ":403", ":404")) for s in statuses):
        raise PrivateSourceRepoError(
            f"Source repo {repo_id} is not publicly readable (private or "
            f"not found; saw {statuses}). Refusing to mirror its dataset "
            "bytes: redistribution rights cannot be assumed. The "
            "certification record (manifests and TRO) can still be mirrored "
            "without the data."
        )
    raise ZenodoDepositError(
        f"Could not verify that source repo {repo_id} is openly readable "
        f"(HF returned {statuses}). Refusing to mirror dataset bytes rather "
        "than risk depositing restricted data; retry, or omit "
        "--include-dataset to mirror just the certification record."
    ) from last_error


def _default_dataset_fetcher(session: Any) -> Callable[[str], bytes]:
    def fetch(url: str) -> bytes:
        response = session.get(url, timeout=_TIMEOUT_SECONDS)
        if response.status_code != 200:
            raise ZenodoDepositError(
                f"Failed to download dataset from {url}: HTTP {response.status_code}"
            )
        return response.content

    return fetch


def _expect(response: Any, expected: tuple[int, ...], step: str) -> dict[str, Any]:
    if response.status_code not in expected:
        raise ZenodoDepositError(
            f"Zenodo {step} failed with HTTP {response.status_code}: "
            f"{getattr(response, 'text', '')[:500]}"
        )
    try:
        return response.json()
    except Exception:
        return {}


def mirror_release_to_zenodo(
    country_id: str,
    *,
    token: Optional[str] = None,
    base_url: str = ZENODO_API,
    session: Any = None,
    publish: bool = False,
    include_dataset: bool = False,
    dataset_fetcher: Optional[Callable[[str], bytes]] = None,
    data_release_manifest: Optional[DataReleaseManifest] = None,
    license_id: Optional[str] = None,
) -> ZenodoDeposit:
    """Deposit a certified release's certification record on Zenodo.

    Deposits the bundled country manifest, the bundle TRACE TRO, and
    the country data release manifest (when available). With
    ``include_dataset=True`` the certified dataset bytes are deposited
    too — but only when their source Hugging Face repo is publicly
    readable; :class:`PrivateSourceRepoError` is raised otherwise.

    The deposit is left as a draft unless ``publish=True``, which mints
    the DOI recorded on every returned :class:`PreservationMirror`.
    ``base_url=ZENODO_SANDBOX_API`` targets the Zenodo sandbox for
    rehearsals. The token comes from the argument or ``ZENODO_TOKEN``.
    """
    token = token or os.environ.get("ZENODO_TOKEN")
    if not token:
        raise ZenodoDepositError(
            "No Zenodo token: pass token= or set ZENODO_TOKEN. Create one "
            "at https://zenodo.org/account/settings/applications/ with "
            "deposit:write and deposit:actions scopes."
        )
    if session is None:
        import requests

        session = requests.Session()
    headers = {"Authorization": f"Bearer {token}"}

    country_manifest = get_release_manifest(country_id)
    if data_release_manifest is None:
        try:
            data_release_manifest = get_data_release_manifest(country_id)
        except DataReleaseManifestUnavailableError:
            data_release_manifest = None

    files: list[tuple[str, bytes]] = [
        (
            f"{country_id}.bundle_manifest.json",
            canonical_json_bytes(country_manifest.model_dump(mode="json")),
        ),
        (f"{country_id}.trace.tro.jsonld", _bundled_tro_bytes(country_id)),
    ]
    if data_release_manifest is not None:
        files.append(
            (
                f"{country_id}.data_release_manifest.json",
                canonical_json_bytes(data_release_manifest.model_dump(mode="json")),
            )
        )

    if include_dataset:
        certified = country_manifest.certified_data_artifact
        if certified is None:
            raise ZenodoDepositError(
                f"Country manifest for '{country_id}' pins no certified "
                "dataset artifact; nothing to include."
            )
        parsed = _parse_hf_uri(certified.uri)
        if parsed is None:
            raise ZenodoDepositError(
                f"Cannot parse certified dataset URI {certified.uri!r} as a "
                "Hugging Face reference."
            )
        repo_id, filename = parsed
        _assert_source_repo_public(session, repo_id)
        from .trace import _dataset_location_from_uri

        fetch = dataset_fetcher or _default_dataset_fetcher(session)
        files.append((filename, fetch(_dataset_location_from_uri(certified.uri))))

    created = _expect(
        session.post(
            f"{base_url}/deposit/depositions",
            json={},
            headers=headers,
            timeout=_TIMEOUT_SECONDS,
        ),
        (200, 201),
        "deposition creation",
    )
    deposit_id = str(created.get("id"))
    links = created.get("links") or {}
    bucket = links.get("bucket")
    deposit_url = links.get("html")
    if not bucket:
        raise ZenodoDepositError("Zenodo deposition response has no bucket link.")

    for name, content in files:
        _expect(
            session.put(
                f"{bucket}/{name}",
                data=content,
                headers=headers,
                timeout=_TIMEOUT_SECONDS,
            ),
            (200, 201),
            f"upload of {name}",
        )

    metadata = deposition_metadata(
        country_manifest, data_release_manifest, license_id=license_id
    )
    _expect(
        session.put(
            f"{base_url}/deposit/depositions/{deposit_id}",
            json={"metadata": metadata},
            headers=headers,
            timeout=_TIMEOUT_SECONDS,
        ),
        (200,),
        "metadata update",
    )

    doi: Optional[str] = None
    concept_doi: Optional[str] = None
    record_url: Optional[str] = None
    if publish:
        published_payload = _expect(
            session.post(
                f"{base_url}/deposit/depositions/{deposit_id}/actions/publish",
                headers=headers,
                timeout=_TIMEOUT_SECONDS,
            ),
            (200, 202),
            "publish",
        )
        doi = published_payload.get("doi")
        concept_doi = published_payload.get("conceptdoi")
        record_url = (published_payload.get("links") or {}).get("record_html")

    deposited_at = datetime.now(timezone.utc).isoformat()
    file_base = record_url or deposit_url or f"{base_url}/deposit/{deposit_id}"
    mirrors = [
        PreservationMirror(
            kind="zenodo",
            url=f"{file_base}/files/{name}",
            doi=doi,
            sha256=hashlib.sha256(content).hexdigest(),
            deposited_at=deposited_at,
        )
        for name, content in files
    ]

    return ZenodoDeposit(
        deposit_id=deposit_id,
        deposit_url=deposit_url,
        doi=doi,
        concept_doi=concept_doi,
        published=publish,
        mirrors=mirrors,
    )
