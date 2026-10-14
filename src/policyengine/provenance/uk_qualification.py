"""Orchestration for qualifying a UK model/data candidate.

``scripts/check_uk_candidate.py`` is the command-line front end and
``.github/workflows/certify-uk-release.yaml`` runs it. The steps are:

``resolve``
    Find the candidate pair: the newest (or requested) policyengine-uk wheel
    from PyPI, the core it needs, and the newest (or requested) uk-data
    release at the data repository's current manifest revision. Decide
    whether to qualify it, or whether it is already certified, stale, or a
    duplicate of an attempt in the ledger.
``prepare``
    On a checkout of ``main``, certify the pair into the bundle manifest
    (exact ``==`` claim backed by the pair id when no publisher claim covers
    it), regenerate pins, ``uv.lock``, TROs, the certified-version test
    constants and household snapshots together, and commit that as the
    candidate commit on ``candidate/uk/<model>-<data>``.
``gates``
    Run the mandatory local gates on the candidate commit
    (:mod:`policyengine.provenance.uk_candidate`).
``request-replay`` / ``poll-replay``
    Send the scorecard an immutable replay request naming the candidate
    commit, and read back its terminal status and receipt.
``finalize``
    Record the qualification receipt in the ledger.
``promote``
    Pick the newest promotable pair that advances ``main`` and mark its
    candidate PR ready, closing superseded candidates.

Network, git and GitHub access are injected so every decision can be tested
offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Optional

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from policyengine.provenance.manifest import DataReleaseManifest
from policyengine.provenance.qualification import (
    REQUIRED_GATES,
    CandidatePair,
    GateResult,
    IssuedBy,
    PinnedData,
    PinnedWheel,
    PreviousCertificate,
    QualificationHarness,
    QualificationReceipt,
    ReplayQualificationRequest,
    ReplayReceipt,
    ReplayReference,
    ReplayStatus,
    ReviewAcceptance,
    dominates,
    evaluate_replay_receipt,
    qualification_verdict,
    replay_gate_while_pending,
    select_promotion_target,
)
from policyengine.provenance.qualification_ledger import (
    attempt_directory,
    pair_directory,
    read_json,
    write_json,
)
from policyengine.provenance.receipt import certificate_sha256

UK_MODEL_PACKAGE = "policyengine-uk"
CORE_PACKAGE = "policyengine-core"
UK_DATA_REPO_ID = "policyengine/policyengine-uk-data-private"
UK_DATA_REPO_TYPE: Literal["model"] = "model"
TOKEN_VARIABLES = ("HF_TOKEN", "HUGGING_FACE_TOKEN", "HUGGINGFACE_HUB_TOKEN")
#: The scorecard's certification recipe (policyengine-scorecard
#: pipeline/uk_replay_variants.py, isolate_certification_environment), which
#: expected_release_bundle must reproduce exactly. policyengine.py 6.x fetches
#: the data release manifest with requests, which ignores HF_HUB_OFFLINE; with
#: these proxies the fetch fails at once for a private or public data repo and
#: certify_data_release_compatibility falls back to the packaged certification.
PROXY_EXCEPTIONS = ("NO_PROXY", "no_proxy")
OFFLINE_VARIABLES = {
    "HF_HUB_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
}
NO_NETWORK = {
    name: "http://127.0.0.1:9"
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )
}


def certification_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """``environ`` as the scorecard isolates it before reading release_bundle."""

    env = {
        key: value
        for key, value in environ.items()
        if key not in TOKEN_VARIABLES and key not in PROXY_EXCEPTIONS
    }
    env.update(OFFLINE_VARIABLES)
    env.update(NO_NETWORK)
    return env


REPO_ROOT = Path(__file__).resolve().parents[3]

Action = Literal["qualify", "already_certified", "stale", "duplicate"]


# --- Resolution ------------------------------------------------------------


@dataclass(frozen=True)
class WheelFile:
    filename: str
    url: str
    sha256: str


@dataclass(frozen=True)
class ResolvedCandidate:
    """A candidate pair plus what is needed to fetch and certify it."""

    pair: CandidatePair
    model_wheel: WheelFile
    core_wheel: WheelFile
    manifest_uri: str
    model_requires_core: str


def _stable_versions(
    releases: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[Version]:
    versions = []
    for text, files in releases.items():
        try:
            version = Version(text)
        except InvalidVersion:
            continue
        if version.is_prerelease or version.is_devrelease:
            continue
        if not files or all(item.get("yanked") for item in files):
            continue
        versions.append(version)
    return sorted(versions)


def _wheel(files: Sequence[Mapping[str, Any]], name: str, version: str) -> WheelFile:
    wheels = [
        item
        for item in files
        if item.get("packagetype") == "bdist_wheel" and not item.get("yanked")
    ]
    if len(wheels) != 1:
        raise ValueError(
            f"{name} {version} must publish exactly one wheel; found {len(wheels)}."
        )
    entry = wheels[0]
    return WheelFile(
        filename=entry["filename"], url=entry["url"], sha256=entry["digests"]["sha256"]
    )


def core_requirement(requires_dist: Iterable[str]) -> str:
    """The model's ``policyengine-core`` specifier (unconditional requirements)."""

    for line in requires_dist or ():
        requirement = Requirement(line)
        if requirement.name.lower().replace("_", "-") != CORE_PACKAGE:
            continue
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        return str(requirement.specifier)
    raise ValueError("policyengine-uk declares no policyengine-core requirement.")


def choose_core_version(
    current_core: str,
    specifier: str,
    available: Sequence[Version],
) -> str:
    """Keep the certified core if the model accepts it; else the newest accepted."""

    spec = SpecifierSet(specifier)
    if Version(current_core) in spec:
        return current_core
    accepted = [version for version in available if version in spec]
    if not accepted:
        raise ValueError(
            f"No published policyengine-core release satisfies {specifier}."
        )
    return str(max(accepted))


def latest_data_release(tags: Iterable[str]) -> str:
    """The newest release tag that is a plain version (``1.58.0``)."""

    versions = []
    for tag in tags:
        if not re.fullmatch(r"\d+(\.\d+)*", tag):
            continue
        versions.append(Version(tag))
    if not versions:
        raise ValueError("The data repository has no version tags.")
    return str(max(versions))


def resolve_candidate(
    *,
    current_core: str,
    pypi_project: Callable[[str], Mapping[str, Any]],
    hf_revision_sha: Callable[[str, str], str],
    hf_tags: Callable[[str], Sequence[str]],
    hf_file: Callable[[str, str, str], bytes],
    model_version: Optional[str] = None,
    data_version: Optional[str] = None,
) -> ResolvedCandidate:
    """Resolve the candidate pair from PyPI and Hugging Face."""

    model_project = pypi_project(UK_MODEL_PACKAGE)
    releases = model_project["releases"]
    model_version = model_version or str(_stable_versions(releases)[-1])
    if model_version not in releases:
        raise ValueError(f"{UK_MODEL_PACKAGE} {model_version} is not on PyPI.")
    model_wheel = _wheel(releases[model_version], UK_MODEL_PACKAGE, model_version)
    model_release = pypi_project(f"{UK_MODEL_PACKAGE}/{model_version}")
    requires_core = core_requirement(model_release["info"].get("requires_dist") or [])

    core_project = pypi_project(CORE_PACKAGE)
    core_version = choose_core_version(
        current_core, requires_core, _stable_versions(core_project["releases"])
    )
    core_wheel = _wheel(
        core_project["releases"][core_version], CORE_PACKAGE, core_version
    )

    data_version = data_version or latest_data_release(hf_tags(UK_DATA_REPO_ID))
    manifest_revision = hf_revision_sha(UK_DATA_REPO_ID, "main")
    manifest_path = f"releases/{data_version}/release_manifest.json"
    manifest_bytes = hf_file(UK_DATA_REPO_ID, manifest_revision, manifest_path)
    manifest = DataReleaseManifest.model_validate_json(manifest_bytes)
    if manifest.data_package.version != data_version:
        raise ValueError(
            f"{manifest_path} describes {manifest.data_package.version}, not {data_version}."
        )
    dataset = manifest.default_datasets.get("national")
    if dataset is None or dataset not in manifest.artifacts:
        raise ValueError(
            f"uk-data {data_version} declares no national default dataset."
        )
    artifact = manifest.artifacts[dataset]
    if not artifact.sha256 or not artifact.size_bytes:
        raise ValueError(f"uk-data {data_version} {dataset} has no sha256 or size.")
    build_id = (
        manifest.build.build_id if manifest.build and manifest.build.build_id else None
    )
    if build_id is None:
        raise ValueError(f"uk-data {data_version} records no build id.")

    pair = CandidatePair(
        country_id="uk",
        model=PinnedWheel(
            name=UK_MODEL_PACKAGE,
            version=model_version,
            wheel_sha256=model_wheel.sha256,
        ),
        core=PinnedWheel(
            name=CORE_PACKAGE, version=core_version, wheel_sha256=core_wheel.sha256
        ),
        data=PinnedData(
            data_package=manifest.data_package.name,
            release_version=data_version,
            build_id=build_id,
            repo_id=UK_DATA_REPO_ID,
            repo_type=UK_DATA_REPO_TYPE,
            release_manifest_path=manifest_path,
            release_manifest_revision=manifest_revision,
            release_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            dataset=dataset,
            dataset_path=artifact.path,
            dataset_revision=artifact.revision,
            dataset_sha256=artifact.sha256,
            size_bytes=artifact.size_bytes,
        ),
    )
    return ResolvedCandidate(
        pair=pair,
        model_wheel=model_wheel,
        core_wheel=core_wheel,
        manifest_uri=(
            f"hf://{UK_DATA_REPO_TYPE}/{UK_DATA_REPO_ID}@{manifest_revision}/{manifest_path}"
        ),
        model_requires_core=requires_core,
    )


# --- Deciding what to do ------------------------------------------------------


def certified_order_key(bundle: Mapping[str, Any]) -> tuple[str, str, str]:
    """(model version, data release, core version) certified on a branch."""

    record = bundle["data_releases"]["uk"]
    return (
        record["model_package"]["version"],
        record["data_package"]["version"],
        bundle["packages"][CORE_PACKAGE]["version"],
    )


def previous_certificate(bundle: Mapping[str, Any]) -> PreviousCertificate:
    record = bundle["data_releases"]["uk"]
    reference = record["datasets"][record["default_dataset"]]
    data_package = record["data_package"]
    return PreviousCertificate(
        bundle_version=bundle["policyengine_version"],
        model_version=record["model_package"]["version"],
        core_version=bundle["packages"][CORE_PACKAGE]["version"],
        data_release_version=record["data_package"]["version"],
        dataset_sha256=record["certified_data_artifact"]["sha256"],
        certificate_sha256=certificate_sha256(record),
        qualification_pair_id=(record.get("certification") or {}).get(
            "qualification_pair_id"
        ),
        model_wheel_sha256=record["model_package"].get("sha256"),
        core_wheel_sha256=bundle["packages"][CORE_PACKAGE].get("sha256"),
        dataset_reference={
            **reference,
            "repo_id": reference.get("repo_id") or data_package["repo_id"],
            "repo_type": reference.get("repo_type")
            or data_package.get("repo_type", "model"),
        },
        dataset_name=record["default_dataset"],
        release_manifest_reference={
            "repo_id": data_package["repo_id"],
            "repo_type": data_package.get("repo_type", "model"),
            "path": data_package["release_manifest_path"],
            "revision": data_package["release_manifest_revision"],
        },
    )


def candidate_action(
    pair: CandidatePair,
    bundle: Mapping[str, Any],
    ledger_root: Optional[Path],
    *,
    base_commit: str,
    force: bool = False,
    now: Optional[str] = None,
    owner_is_failed: Optional[Callable[[str], bool]] = None,
) -> tuple[Action, str]:
    """Whether to qualify ``pair`` now, and why."""

    current = certified_order_key(bundle)
    record = bundle["data_releases"]["uk"]
    if pair.order_key == current and (
        record["certified_data_artifact"]["sha256"] == pair.data.dataset_sha256
    ):
        return "already_certified", f"{current} is already certified on main"
    if dominates(current, pair.order_key):
        return "stale", f"main certifies {current}, newer than {pair.order_key}"
    if force or ledger_root is None:
        return "qualify", "forced" if force else "no ledger"
    pair_dir = pair_directory(ledger_root, "uk", pair.pair_id)
    latest = pair_dir / "qualification_receipt.json"
    receipt = (
        QualificationReceipt.model_validate(read_json(latest))
        if latest.exists()
        else None
    )
    attempt = _latest_base_attempt(pair, ledger_root, base_commit)
    if (
        attempt is not None
        and attempt_is_recoverable(attempt, now=now, owner_is_failed=owner_is_failed)
        and (
            receipt is None
            or receipt.verdict == "incomplete"
            or attempt_supersedes_receipt(attempt, receipt)
        )
    ):
        return "qualify", "recoverable abandoned staged attempt"
    if receipt is not None and receipt.verdict != "incomplete":
        return "duplicate", f"pair already {receipt.verdict} in the ledger"
    if attempt is not None:
        return "duplicate", f"an attempt from base {base_commit[:12]} exists"
    return "qualify", "new pair, or an incomplete pair on a new base commit"


# --- Preparing the candidate commit -----------------------------------------

#: Test files that pin the certified UK pair literally. Promotion regenerates
#: them with the rest of the certification so the suite tests the new pair.
CERTIFIED_CONSTANT_FILES = (
    "tests/test_models.py",
    "tests/test_release_manifests.py",
    "tests/test_uk_regions.py",
)


def certified_constant_replacements(
    old_record: Mapping[str, Any], new_record: Mapping[str, Any]
) -> list[tuple[str, str]]:
    """Exact quoted-literal replacements from the old to the new certificate."""

    def values(record: Mapping[str, Any]) -> dict[str, Optional[str]]:
        certification = record.get("certification") or {}
        data = record.get("data_package") or {}
        return {
            "model": (record.get("model_package") or {}).get("version"),
            "built_with": certification.get("built_with_model_version"),
            "data": data.get("version"),
            "build_id": certification.get("data_build_id"),
            "revision": data.get("release_manifest_revision"),
        }

    old, new = values(old_record), values(new_record)
    pairs: list[tuple[str, str]] = []
    for key in ("build_id", "revision", "model", "built_with", "data"):
        before, after = old[key], new[key]
        if before and after and before != after:
            pairs.append((before, after))
    return pairs


def rewrite_certified_constants(
    repo_root: Path, replacements: Sequence[tuple[str, str]]
) -> list[str]:
    """Rewrite quoted occurrences of old certified values in the constant files.

    Only string-literal occurrences change: ``"2.125.1"``, ``"@1.58.0"``,
    ``"releases/1.58.0/release_manifest.json"`` and URIs ending ``@1.58.0``.
    Returns the files changed.
    """

    changed = []
    for relative in CERTIFIED_CONSTANT_FILES:
        path = repo_root / relative
        text = path.read_text()
        updated = text
        for old, new in replacements:
            pattern = re.compile(
                r'(?P<pre>["@/-])' + re.escape(old) + r'(?P<post>["/])'
            )
            updated = pattern.sub(
                lambda m: m.group("pre") + new + m.group("post"), updated
            )
        if updated != text:
            path.write_text(updated)
            changed.append(relative)
    return changed


def candidate_branch(pair: CandidatePair) -> str:
    """The pair's own branch.

    The pair id is part of the name: two pairs that share model and data
    versions (another core, another wheel, re-published bytes) must never
    share a branch, or one pair's qualification could promote the other's
    commit.
    """

    return (
        f"candidate/uk/{pair.model.version}-{pair.data.release_version}"
        f"-{pair.pair_id[:12]}"
    )


def attempt_key(
    pair: CandidatePair,
    ledger_root: Optional[Path],
    *,
    base_commit: str,
    force: bool = False,
    now: Optional[str] = None,
    owner_is_failed: Optional[Callable[[str], bool]] = None,
) -> str:
    """The ledger key of the attempt a qualification run would stage.

    Concurrent runs for the same pair and base deduplicate. Forced runs and
    recovery of abandoned stages use the next free key, preserving earlier
    evidence. A live replacement blocks further recovery on that base.
    """

    key = base_commit[:12]
    if ledger_root is None:
        return key
    attempt = _latest_base_attempt(pair, ledger_root, base_commit)
    recovering = attempt is not None and attempt_is_recoverable(
        attempt, now=now, owner_is_failed=owner_is_failed
    )
    if not force and not recovering:
        return key
    if not attempt_directory(ledger_root, "uk", pair.pair_id, key).exists():
        return key
    repeat = 2
    while attempt_directory(
        ledger_root, "uk", pair.pair_id, f"{key}-{repeat}"
    ).exists():
        repeat += 1
    return f"{key}-{repeat}"


def _latest_base_attempt(
    pair: CandidatePair, ledger_root: Path, base_commit: str
) -> Optional[Path]:
    base = base_commit[:12]
    parent = pair_directory(ledger_root, "uk", pair.pair_id) / "attempts"
    attempts = [
        path
        for path in parent.glob(f"{base}*")
        if path.is_dir() and re.fullmatch(re.escape(base) + r"(?:-\d+)?", path.name)
    ]

    def order(path: Path) -> tuple[int, int]:
        stage = path / "staging.json"
        sequence = int(read_json(stage)["sequence"]) if stage.exists() else 0
        repeat = int(path.name[len(base) + 1 :]) if path.name != base else 1
        return sequence, repeat

    return max(attempts, key=order, default=None)


def changelog_fragment(pair: CandidatePair, basis_note: str) -> str:
    return (
        f"Certify uk-data {pair.data.release_version} (`{pair.data.dataset}`) with "
        f"policyengine-uk {pair.model.version} and policyengine-core "
        f"{pair.core.version}, qualified automatically as pair "
        f"`{pair.pair_id[:12]}`. {basis_note}\n"
    )


Runner = Callable[..., subprocess.CompletedProcess]


def _run(
    command: Sequence[str], *, cwd: Path, env: Optional[Mapping[str, str]] = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(command), cwd=cwd, env=dict(env) if env is not None else None, check=True
    )


def prepare_candidate_commit(
    repo_root: Path,
    resolved: ResolvedCandidate,
    *,
    python: str,
    run: Runner = _run,
    refresh_snapshots: bool = True,
) -> dict[str, Any]:
    """Certify the pair into the working tree and regenerate everything with it.

    The working tree must be a clean checkout of the base commit on the
    candidate branch. Returns what changed; the caller commits it.
    """

    pair = resolved.pair
    bundle_path = (
        repo_root / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
    )
    old_record = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    run(
        [
            python,
            "scripts/bundle.py",
            "certify-data",
            "--country",
            "uk",
            "--data-producer",
            "populace",
            "--manifest-uri",
            resolved.manifest_uri,
            "--model-version",
            pair.model.version,
            "--core-version",
            pair.core.version,
            "--qualified-pair-id",
            pair.pair_id,
            "--no-changelog",
        ],
        cwd=repo_root,
    )
    new_bundle = json.loads(bundle_path.read_text())
    new_record = new_bundle["data_releases"]["uk"]
    if new_record["model_package"].get("sha256") != pair.model.wheel_sha256:
        raise ValueError("The certified model wheel hash differs from the candidate's.")
    if new_record["certified_data_artifact"].get("sha256") != pair.data.dataset_sha256:
        raise ValueError("The certified dataset hash differs from the candidate's.")
    run(
        [
            "uv",
            "lock",
            "--no-config",
            "--no-sources",
            "--default-index",
            "https://pypi.org/simple",
            "--python",
            python,
        ],
        cwd=repo_root,
    )
    run([python, "scripts/release_lock.py"], cwd=repo_root)
    # Prepare the candidate's replacement sidecars before strict verification:
    # the committed sidecars still authenticate the previous data release.
    run(
        [python, "scripts/bundle.py", "generate", "--include-tros"],
        cwd=repo_root,
    )
    constants = rewrite_certified_constants(
        repo_root, certified_constant_replacements(old_record, new_record)
    )
    basis = new_record["certification"]["compatibility_basis"]
    basis_note = {
        "built_with_model_package": "The data was built with this model version.",
        "legacy_compatible_model_package": "The data publisher's compatibility claim covers this model version.",
        "qualified_exact_pair": "No publisher claim covers this model version, so the certificate is an exact claim backed by the qualification receipt.",
    }.get(basis, f"Compatibility basis: {basis}.")
    fragment = (
        repo_root
        / "changelog.d"
        / (f"certify-uk-{pair.model.version}-{pair.data.release_version}.changed.md")
    )
    fragment.write_text(changelog_fragment(pair, basis_note))
    if refresh_snapshots:
        run(
            [
                python,
                "-m",
                "pytest",
                "tests/test_household_calculator_snapshot.py",
                "-q",
            ],
            cwd=repo_root,
            env={**os.environ, "PE_UPDATE_SNAPSHOTS": "1"},
        )
    run(
        [python, "scripts/bundle.py", "check", "--include-tros", "--strict-tros"],
        cwd=repo_root,
    )
    return {
        "compatibility_basis": basis,
        "constant_files": constants,
        "changelog_fragment": str(fragment.relative_to(repo_root)),
    }


def packaged_manifest_sha256(repo_root: Path) -> str:
    path = repo_root / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Replay request -------------------------------------------------------


def expected_release_bundle(python: str, *, cwd: Path) -> dict[str, Optional[str]]:
    """``dict(pe.uk.uk_latest.release_bundle)`` under packaged certification.

    Runs in a subprocess in the scorecard's certification environment (no
    tokens, no network for the release-manifest request), so the bundled
    certification is what is reported for a private or public data repo.
    """

    env = certification_environment(os.environ)
    output = subprocess.run(
        [
            python,
            "-c",
            # The CLI disables automatic country imports. Load the UK API
            # explicitly so the flag cannot leave pe.uk unset and unrelated
            # country models need not be initialized for this UK request.
            "import json; from policyengine.tax_benefit_models.uk import uk_latest; "
            "print(json.dumps(dict(uk_latest.release_bundle), sort_keys=True))",
        ],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    bundle: dict[str, Optional[str]] = json.loads(output.strip().splitlines()[-1])
    return bundle


def build_replay_request(
    pair: CandidatePair,
    harness: QualificationHarness,
    *,
    release_bundle: Mapping[str, Optional[str]],
    issued_by: IssuedBy,
    attempt: int = 1,
    compare_to: str = "latest_certified",
) -> ReplayQualificationRequest:
    """The immutable pre-promotion request for the scorecard."""

    return ReplayQualificationRequest.model_validate(
        {
            "schema": "policyengine.uk-replay-qualification-request/v1",
            "kind": "candidate",
            "attempt": attempt,
            "candidate": {
                "policyengine": {
                    "version": harness.policyengine_version,
                    "source": {
                        "git": {
                            "repository": "PolicyEngine/policyengine.py",
                            "commit": harness.git_commit,
                        }
                    },
                    "packaged_bundle_manifest_sha256": harness.packaged_bundle_manifest_sha256,
                },
                "policyengine_uk": {
                    "version": pair.model.version,
                    "wheel_sha256": pair.model.wheel_sha256,
                },
                "policyengine_core": {
                    "version": pair.core.version,
                    "wheel_sha256": pair.core.wheel_sha256,
                },
                "data": {
                    "build_id": pair.data.build_id,
                    "dataset": pair.data.dataset,
                    "repo_id": pair.data.repo_id,
                    "repo_type": pair.data.repo_type,
                    "revision": pair.data.dataset_revision,
                    "path": pair.data.dataset_path,
                    "sha256": pair.data.dataset_sha256,
                    "size_bytes": pair.data.size_bytes,
                    "release_manifest_sha256": pair.data.release_manifest_sha256,
                },
                "expected_release_bundle": dict(release_bundle),
            },
            "compare_to": compare_to,
            "requested_by": {
                "repository": issued_by.repository,
                "workflow_run_id": issued_by.workflow_run_id,
                "run_attempt": issued_by.run_attempt,
                "commit": harness.git_commit,
                "pair_id": pair.pair_id,
            },
        }
    )


def replay_dispatch_payload(
    request: ReplayQualificationRequest, *, event_type: str
) -> dict[str, Any]:
    return {"event_type": event_type, "client_payload": {"request": request.document()}}


def replay_state_paths(request_id: str) -> tuple[str, str]:
    base = f"requests/{request_id}"
    return f"{base}/STATUS.json", f"{base}/REPLAY_RECEIPT.json"


def read_replay(
    request: ReplayQualificationRequest,
    *,
    fetch: Callable[[str, str], Optional[bytes]],
    state_ref: str,
) -> tuple[GateResult, Optional[ReplayStatus], Optional[ReplayReceipt]]:
    """Read the scorecard's status and, when terminal, its receipt.

    ``fetch(ref, path)`` returns file bytes from the scorecard repository at
    a ref or commit, or ``None`` if absent.
    """

    status_path, receipt_path = replay_state_paths(request.request_id)
    raw_status = fetch(state_ref, status_path)
    if raw_status is None:
        return replay_gate_while_pending(None), None, None
    status = ReplayStatus.model_validate_json(raw_status)
    if not status.terminal:
        return replay_gate_while_pending(status), status, None
    assert status.receipt_commit is not None
    raw_receipt = fetch(status.receipt_commit, receipt_path)
    if raw_receipt is None:
        return (
            GateResult(
                gate_id="replay",
                status="fail",
                summary=(
                    f"Status names receipt commit {status.receipt_commit}, which has "
                    "no REPLAY_RECEIPT.json."
                ),
            ),
            status,
            None,
        )
    receipt = ReplayReceipt.from_document(json.loads(raw_receipt))
    return evaluate_replay_receipt(request, status, receipt), status, receipt


# --- Finalizing ---------------------------------------------------------------


def assemble_receipt(
    pair: CandidatePair,
    harness: QualificationHarness,
    gates: Sequence[GateResult],
    *,
    issued_by: IssuedBy,
    completed_at: str,
    previous: Optional[PreviousCertificate],
    replay: Optional[ReplayReference],
) -> QualificationReceipt:
    """A receipt whose verdict follows from the gates; missing gates count as missing."""

    ordered = sorted(
        gates,
        key=lambda gate: (
            REQUIRED_GATES.index(gate.gate_id)
            if gate.gate_id in REQUIRED_GATES
            else len(REQUIRED_GATES),
            gate.gate_id,
        ),
    )
    return QualificationReceipt(
        schema_version=1,
        receipt_type="policyengine.candidate_qualification_receipt",
        pair_id=pair.pair_id,
        pair=pair,
        harness=harness,
        previous_certificate=previous,
        replay=replay,
        gates=list(ordered),
        verdict=qualification_verdict(ordered),
        issued_by=issued_by,
        completed_at=completed_at,
    )


def accept_review(
    receipt: QualificationReceipt,
    *,
    reviewer: str,
    accepted_receipt_sha256: str,
    explanation: str,
    accepted_at: str,
) -> QualificationReceipt:
    """Attach a reviewer's acceptance of exactly this needs-review receipt."""

    if receipt.verdict != "needs_review":
        raise ValueError(
            f"Only needs-review receipts can be accepted, not {receipt.verdict}."
        )
    if accepted_receipt_sha256 != receipt.unreviewed_sha256:
        raise ValueError(
            "The acceptance names different receipt bytes "
            f"({accepted_receipt_sha256}, current {receipt.unreviewed_sha256})."
        )
    return receipt.model_copy(
        update={
            "review": ReviewAcceptance(
                reviewer=reviewer,
                accepted_at=accepted_at,
                accepted_receipt_sha256=accepted_receipt_sha256,
                explanation=explanation,
            )
        }
    )


# --- Attempt directories -----------------------------------------------------
#
# Every step of an attempt reads and writes one directory inside the ledger
# checkout (``<country>/<pair_id>/attempts/<base commit[:12]>/``), so a
# scheduled catch-up can finish an attempt whose replay outlasted its job with
# exactly the code path the job would have run.


def stage_attempt(
    attempt_dir: Path,
    candidate_payload: Mapping[str, Any],
    harness: QualificationHarness,
    *,
    owner_run_id: Optional[str] = None,
    staged_at: Optional[str] = None,
) -> None:
    payloads = {
        attempt_dir / "candidate.json": dict(candidate_payload),
        attempt_dir / "harness.json": harness.canonical_payload(),
    }
    for path, payload in payloads.items():
        if path.exists() and read_json(path) != payload:
            raise ValueError(f"A staged attempt's {path.name} is immutable.")
    staging_path = attempt_dir / "staging.json"
    if not staging_path.exists():
        # Persist staging order in the ledger, never infer it from finalization
        # time, commit hashes or filesystem mtimes. Legacy attempts precede
        # newly staged attempts and keep their existing receipt bytes.
        prior_orders = [
            int(read_json(path)["sequence"])
            for path in attempt_dir.parent.glob("*/staging.json")
        ]
        staged = _attempt_time(staged_at)
        stage = {
            "sequence": max(prior_orders, default=0) + 1,
            "owner_run_id": owner_run_id,
            "staged_at": staged.isoformat().replace("+00:00", "Z"),
            "expires_at": (staged + timedelta(hours=4))
            .isoformat()
            .replace("+00:00", "Z"),
        }
        supersedes = candidate_payload.get("supersedes_receipt_sha256")
        if supersedes:
            published = attempt_dir.parent.parent / "qualification_receipt.json"
            if (
                not published.exists()
                or QualificationReceipt.model_validate(
                    read_json(published)
                ).unreviewed_sha256
                != supersedes
            ):
                raise ValueError(
                    "Recovery must bind the exact receipt the forced attempt supersedes"
                )
            stage["supersedes_receipt_sha256"] = supersedes
        write_json(staging_path, stage)
    for path, payload in payloads.items():
        if not path.exists():
            write_json(path, payload)


def write_gate_results(
    attempt_dir: Path, results: Sequence[GateResult], evidence: Mapping[str, Any]
) -> None:
    for result in results:
        write_json(
            attempt_dir / "gates" / f"{result.gate_id}.result.json",
            result.canonical_payload(),
        )
    for gate_id, item in evidence.items():
        write_json(attempt_dir / "gates" / f"{gate_id}.json", item)


def load_gate_results(attempt_dir: Path) -> list[GateResult]:
    results = [
        GateResult.model_validate(read_json(path))
        for path in sorted((attempt_dir / "gates").glob("*.result.json"))
    ]
    replay = attempt_dir / "replay" / "replay.result.json"
    if replay.exists():
        results = [gate for gate in results if gate.gate_id != "replay"]
        results.append(GateResult.model_validate(read_json(replay)))
    return results


def finalize_attempt(
    attempt_dir: Path,
    ledger_root: Path,
    *,
    issued_by: IssuedBy,
    completed_at: str,
) -> QualificationReceipt:
    """Assemble and record the receipt for a staged attempt."""

    receipt_path = attempt_dir / "qualification_receipt.json"
    existing = None
    if receipt_path.exists():
        existing = QualificationReceipt.model_validate(read_json(receipt_path))
        if existing.verdict != "incomplete":
            # A terminal attempt is immutable, including its completion time.
            # Retry publication if an earlier run stopped after saving it.
            _publish_latest_attempt_receipt(attempt_dir, ledger_root, existing)
            return existing
    candidate = read_json(attempt_dir / "candidate.json")
    pair = CandidatePair.model_validate(candidate["pair"])
    harness = QualificationHarness.model_validate(
        read_json(attempt_dir / "harness.json")
    )
    gates = load_gate_results(attempt_dir)
    if not any(gate.gate_id == "replay" for gate in gates):
        gates.append(replay_gate_while_pending(None))
    previous = (
        PreviousCertificate.model_validate(candidate["previous_certificate"])
        if candidate.get("previous_certificate")
        else None
    )
    replay_reference = None
    request_path = attempt_dir / "replay" / "request.json"
    if request_path.exists():
        request = ReplayQualificationRequest.model_validate(read_json(request_path))
        status_path = attempt_dir / "replay" / "status.json"
        status = (
            ReplayStatus.model_validate(read_json(status_path))
            if status_path.exists()
            else None
        )
        replay_reference = ReplayReference(
            request_id=request.request_id,
            receipt_sha256=status.receipt_sha256 if status else None,
            receipt_commit=status.receipt_commit if status else None,
        )
    receipt = assemble_receipt(
        pair,
        harness,
        gates,
        issued_by=issued_by,
        completed_at=completed_at,
        previous=previous,
        replay=replay_reference,
    )
    # Pending receipts may advance to terminal when replay finishes. Preserve
    # every version under its digest; terminal attempt receipts never change.
    if existing is not None:
        snapshot = attempt_dir / "receipts" / f"{existing.receipt_sha256}.json"
        if not snapshot.exists():
            write_json(snapshot, existing.canonical_payload())
    snapshot = attempt_dir / "receipts" / f"{receipt.receipt_sha256}.json"
    if not snapshot.exists():
        write_json(snapshot, receipt.canonical_payload())
    write_json(receipt_path, receipt.canonical_payload())
    _publish_latest_attempt_receipt(attempt_dir, ledger_root, receipt)
    return receipt


def _publish_latest_attempt_receipt(
    attempt_dir: Path, ledger_root: Path, receipt: QualificationReceipt
) -> None:
    """Publish by staging order, repairing interrupted publication on retry."""

    pair = receipt.pair
    pair_dir = pair_directory(ledger_root, "uk", pair.pair_id)
    write_json(pair_dir / "pair.json", pair.canonical_payload())
    staging_path = attempt_dir / "staging.json"
    sequence = int(read_json(staging_path)["sequence"]) if staging_path.exists() else 0
    latest_path = pair_dir / "qualification_receipt.json"
    latest_attempt_path = pair_dir / "latest_attempt.json"
    latest_sequence = -1
    latest_attempt_key = None
    latest_pointer = (
        read_json(latest_attempt_path) if latest_attempt_path.exists() else None
    )
    if latest_path.exists():
        # Receipt identity is authoritative: a crash can leave a stale pointer.
        # Recover staging order from immutable receipts/snapshots, including
        # old ledgers and receipts with a receipt-bound acceptance.
        latest = QualificationReceipt.model_validate(read_json(latest_path))
        latest_sequence = 0
        previous_paths = [
            *pair_dir.glob("attempts/*/qualification_receipt.json"),
            *pair_dir.glob("attempts/*/receipts/*.json"),
        ]
        for previous_path in previous_paths:
            previous = QualificationReceipt.model_validate(read_json(previous_path))
            if previous.unreviewed_sha256 != latest.unreviewed_sha256:
                continue
            previous_attempt = (
                previous_path.parent.parent
                if previous_path.parent.name == "receipts"
                else previous_path.parent
            )
            previous_stage = previous_attempt / "staging.json"
            previous_sequence = (
                int(read_json(previous_stage)["sequence"])
                if previous_stage.exists()
                else 0
            )
            if previous_sequence >= latest_sequence:
                latest_sequence = previous_sequence
                latest_attempt_key = previous_attempt.name
    elif latest_pointer is not None:
        # Preserve the known order if only the publication pointer survived.
        latest_sequence = int(latest_pointer["sequence"])
        latest_attempt_key = latest_pointer["attempt_key"]
    same_attempt = latest_attempt_key == attempt_dir.name
    update_pending = (
        same_attempt
        and latest_path.exists()
        and QualificationReceipt.model_validate(read_json(latest_path)).verdict
        == "incomplete"
    )
    if (
        sequence > latest_sequence
        or update_pending
        or (same_attempt and not latest_path.exists())
    ):
        write_json(latest_path, receipt.canonical_payload())
        latest_attempt_key = attempt_dir.name
        latest_sequence = sequence
    expected_pointer = {"attempt_key": latest_attempt_key, "sequence": latest_sequence}
    if latest_attempt_key is not None and latest_pointer != expected_pointer:
        # Repair only the pointer when the published receipt already belongs
        # to the latest attempt, preserving any receipt-bound review acceptance.
        write_json(latest_attempt_path, expected_pointer)


def attempt_is_waiting_for_replay(attempt_dir: Path) -> bool:
    """A request was sent and the replay gate has not reached a terminal result."""

    if not (attempt_dir / "replay" / "request.json").exists():
        return False
    result = attempt_dir / "replay" / "replay.result.json"
    if not result.exists():
        return True
    return GateResult.model_validate(read_json(result)).status == "unavailable"


def _attempt_time(value: Optional[str]) -> datetime:
    instant = (
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value
        else datetime.now(UTC)
    )
    if instant.tzinfo is None:
        raise ValueError("Attempt timestamps must have a timezone")
    return instant.astimezone(UTC)


def attempt_is_recoverable(
    attempt_dir: Path,
    *,
    now: Optional[str] = None,
    owner_is_failed: Optional[Callable[[str], bool]] = None,
) -> bool:
    """An abandoned stage can be retried in a new immutable attempt directory.

    Sent requests retain the replay catch-up path. A live owner retains its
    stage until expiry; unknown GitHub status never implies owner failure.
    Older stages without ownership metadata are recoverable as unowned work.
    """

    if (attempt_dir / "replay" / "request.json").exists():
        return False
    receipt_path = attempt_dir / "qualification_receipt.json"
    if (
        receipt_path.exists()
        and QualificationReceipt.model_validate(read_json(receipt_path)).verdict
        != "incomplete"
    ):
        return False
    stage_path = attempt_dir / "staging.json"
    if not stage_path.exists() or not (attempt_dir / "candidate.json").exists():
        return False
    stage = read_json(stage_path)
    expires = stage.get("expires_at")
    if expires and _attempt_time(now) >= _attempt_time(expires):
        return True
    owner = stage.get("owner_run_id")
    if owner and owner_is_failed is not None and owner_is_failed(str(owner)):
        return True
    return not owner and not expires


def attempt_supersedes_receipt(
    attempt_dir: Path, receipt: QualificationReceipt
) -> bool:
    """Only explicitly authorized newer work may supersede a terminal receipt."""

    stage = attempt_dir / "staging.json"
    return (
        stage.exists()
        and read_json(stage).get("supersedes_receipt_sha256")
        == receipt.unreviewed_sha256
    )


# --- Promotion ----------------------------------------------------------------


@dataclass
class PromotionPlan:
    target: Optional[QualificationReceipt]
    ready_branch: Optional[str]
    close_branches: list[str] = field(default_factory=list)
    reason: str = ""
    #: The qualified commit the ready branch must still be at when promoted.
    ready_commit: Optional[str] = None


def plan_promotion(
    receipts: Iterable[QualificationReceipt],
    bundle: Mapping[str, Any],
    open_candidate_branches: Mapping[str, str],
) -> PromotionPlan:
    """What to do with candidate PRs given the ledger and ``main``'s certificate.

    ``open_candidate_branches`` maps each open candidate branch to its head
    commit. The target's branch is readied only while its head is exactly
    the commit the target's qualification ran on
    (``receipt.harness.git_commit``): the replayed and tested bytes are the
    promoted bytes. A branch that moved since is left alone and reported.
    """

    receipts = list(receipts)
    current = certified_order_key(bundle)
    target = select_promotion_target(receipts, current)
    branch_pairs = {}
    for receipt in receipts:
        branch_pairs[candidate_branch(receipt.pair)] = receipt.pair.order_key
    close = []
    for branch in open_candidate_branches:
        key = branch_pairs.get(branch)
        if key is None:
            continue
        if key == current or dominates(current, key):
            close.append(branch)
        elif target is not None and dominates(target.pair.order_key, key):
            close.append(branch)
    if target is None:
        return PromotionPlan(
            target=None,
            ready_branch=None,
            close_branches=sorted(close),
            reason=f"no promotable pair advances {current}",
        )
    branch = candidate_branch(target.pair)
    qualified_commit = target.harness.git_commit
    head = open_candidate_branches.get(branch)
    if head is None:
        return PromotionPlan(
            target=target,
            ready_branch=None,
            close_branches=sorted(close),
            reason=(
                f"{target.pair.order_key} advances {current}, but its branch "
                f"{branch} has no open pull request"
            ),
        )
    if head != qualified_commit:
        return PromotionPlan(
            target=target,
            ready_branch=None,
            close_branches=sorted(close),
            reason=(
                f"{target.pair.order_key} advances {current}, but {branch} is at "
                f"{head[:12]}, not the qualified commit {qualified_commit[:12]}; "
                "nothing is promoted"
            ),
        )
    return PromotionPlan(
        target=target,
        ready_branch=branch,
        ready_commit=qualified_commit,
        close_branches=sorted(close),
        reason=f"{target.pair.order_key} advances {current}",
    )


def candidate_pr_body(
    receipt: Optional[QualificationReceipt],
    pair: CandidatePair,
    *,
    ledger_url: str,
    prepared: Optional[Mapping[str, Any]] = None,
) -> str:
    """Markdown body for a candidate PR: the pair, the gates and the verdict."""

    lines = [
        f"Automated certification candidate for **policyengine-uk {pair.model.version}**, "
        f"**policyengine-core {pair.core.version}** and **uk-data {pair.data.release_version}** "
        f"(`{pair.data.dataset}`, sha256 `{pair.data.dataset_sha256[:16]}…`).",
        "",
        f"- Pair id: `{pair.pair_id}`",
        f"- Ledger: {ledger_url}",
    ]
    if prepared:
        lines.append(f"- Compatibility basis: `{prepared.get('compatibility_basis')}`")
    lines += ["", "| Gate | Status | Summary |", "|---|---|---|"]
    gates = {gate.gate_id: gate for gate in (receipt.gates if receipt else [])}
    for gate_id in REQUIRED_GATES:
        gate = gates.get(gate_id)
        if gate is None:
            lines.append(f"| `{gate_id}` | pending | |")
        else:
            summary = gate.summary.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| `{gate_id}` | {gate.status} | {summary} |")
    verdict = receipt.verdict if receipt else "pending"
    lines += [
        "",
        f"**Verdict: {verdict}.** Merging this PR promotes the pair. Until cos d1344 "
        "is ruled, promotion is a reviewed merge; the certification evidence test "
        "refuses an exact-pair certificate without a promotable ledger receipt.",
        "",
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)",
    ]
    return "\n".join(lines) + "\n"


# --- Release dispatch to consumers ----------------------------------------------


def release_bundle_identity(
    bundle: Mapping[str, Any], country_id: str = "uk"
) -> dict[str, Any]:
    """The certified pair a release carries, as consumers verify it."""

    record = bundle["data_releases"][country_id]
    certification = record.get("certification") or {}
    model_package = bundle["countries"][country_id]["model_package"]
    return {
        "model_version": record["model_package"]["version"],
        "model_wheel_sha256": record["model_package"].get("sha256"),
        "core_version": bundle["packages"][CORE_PACKAGE]["version"],
        "data_release_version": record["data_package"]["version"],
        "dataset": record["default_dataset"],
        "dataset_sha256": record["certified_data_artifact"].get("sha256"),
        "certificate_sha256": certificate_sha256(record),
        "compatibility_basis": certification.get("compatibility_basis"),
        "model_package": model_package,
    }


def release_dispatch_payload(
    bundle: Mapping[str, Any],
    *,
    version: str,
    repository: str = "PolicyEngine/policyengine.py",
    fetch_receipt: Optional[
        Callable[[str, str], Optional[QualificationReceipt]]
    ] = None,
) -> dict[str, Any]:
    """``policyengine-release`` repository dispatch for consumers.

    ``client_payload.version`` stays the first field, as the existing
    sim-api and api updaters read only it.
    """

    if bundle.get("policyengine_version") != version:
        raise ValueError(
            f"The bundle manifest is for {bundle.get('policyengine_version')}, not {version}."
        )
    identity = release_bundle_identity(bundle)
    qualification = None
    certification = bundle["data_releases"]["uk"].get("certification") or {}
    pair_id = certification.get("qualification_pair_id")
    if pair_id:
        receipt = fetch_receipt("uk", pair_id) if fetch_receipt is not None else None
        qualification = {
            "uk": {
                "pair_id": pair_id,
                "verdict": receipt.verdict if receipt is not None else None,
                # needs_review pairs are promotable only with an acceptance of
                # exactly that receipt; consumers refuse promotable=false.
                "promotable": receipt.promotable if receipt is not None else None,
                "receipt_sha256": receipt.receipt_sha256
                if receipt is not None
                else None,
            }
        }
    return {
        "event_type": "policyengine-release",
        "client_payload": {
            "version": version,
            "bundle": {"uk": identity},
            "qualification": qualification,
            "release_url": f"https://github.com/{repository}/releases/tag/{version}",
        },
    }


def released_bundle_request(
    bundle: Mapping[str, Any],
    *,
    version: str,
    wheel_sha256: str,
    packaged_manifest_sha256: str,
    release_bundle: Mapping[str, Optional[str]],
    hf_file: Callable[[str, str, str], bytes],
    pypi_project: Callable[[str], Mapping[str, Any]],
    requested_by: Mapping[str, Any],
) -> ReplayQualificationRequest:
    """``released_bundle`` replay request for a published policyengine release."""

    record = bundle["data_releases"]["uk"]
    data_package = record["data_package"]
    manifest_bytes = hf_file(
        data_package["repo_id"],
        data_package["release_manifest_revision"],
        data_package["release_manifest_path"],
    )
    manifest = DataReleaseManifest.model_validate_json(manifest_bytes)
    dataset = record["default_dataset"]
    artifact = manifest.artifacts[dataset]
    reference = record["datasets"][dataset]
    if reference.get("sha256") != artifact.sha256:
        raise ValueError(
            "The release manifest's dataset hash differs from the bundle's."
        )
    core_version = bundle["packages"][CORE_PACKAGE]["version"]
    core_wheel = _wheel(
        pypi_project(CORE_PACKAGE)["releases"][core_version], CORE_PACKAGE, core_version
    )
    return ReplayQualificationRequest.model_validate(
        {
            "schema": "policyengine.uk-replay-qualification-request/v1",
            "kind": "released_bundle",
            "attempt": 1,
            "candidate": {
                "policyengine": {
                    "version": version,
                    "source": {"pypi": {"wheel_sha256": wheel_sha256}},
                    "packaged_bundle_manifest_sha256": packaged_manifest_sha256,
                },
                "policyengine_uk": {
                    "version": record["model_package"]["version"],
                    "wheel_sha256": record["model_package"]["sha256"],
                },
                "policyengine_core": {
                    "version": core_version,
                    "wheel_sha256": core_wheel.sha256,
                },
                "data": {
                    "build_id": record["certified_data_artifact"].get("build_id")
                    or record["build_id"],
                    "dataset": dataset,
                    "repo_id": reference.get("repo_id") or data_package["repo_id"],
                    "repo_type": reference.get("repo_type")
                    or data_package.get("repo_type", "model"),
                    "revision": reference["revision"],
                    "path": reference["path"],
                    "sha256": reference["sha256"],
                    "size_bytes": artifact.size_bytes,
                    "release_manifest_sha256": hashlib.sha256(
                        manifest_bytes
                    ).hexdigest(),
                },
                "expected_release_bundle": dict(release_bundle),
            },
            "compare_to": "latest_certified",
            "requested_by": dict(requested_by),
        }
    )
