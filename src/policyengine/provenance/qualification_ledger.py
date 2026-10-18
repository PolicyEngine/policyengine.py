"""The qualification ledger: durable evidence for every candidate attempt.

The ledger is the orphan branch ``uk-qualification-ledger`` of
PolicyEngine/policyengine.py. Each candidate pair owns one directory, so
concurrent qualifications never write the same file::

    <country>/<pair_id>/
        pair.json                       the CandidatePair
        qualification_receipt.json      the latest terminal receipt for the pair
        latest_attempt.json             which attempt that receipt came from
        attempts/<attempt_key>/
            harness.json                the candidate commit that ran it
            gates/<gate_id>.json        each gate's evidence
            replay/request.json         the request sent to the scorecard
            replay/status.json          the terminal status read back
            replay/receipt.json         the receipt bytes read back
            qualification_receipt.json  this attempt's receipt

Failed and incomplete attempts are kept: the ledger never deletes evidence.
A pair's published files are derived from its attempts and are trusted only
when the published receipt is one attempt's own receipt
(:func:`published_receipt`): concurrent publishes must never yield a receipt
that mixes two attempts.
A bundle certificate with basis ``qualified_exact_pair`` must point at a pair
whose latest receipt is promotable and matches the certificate exactly
(:func:`verify_certification_evidence`).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Optional

from policyengine.provenance.qualification import QualificationReceipt

LEDGER_REPOSITORY = "PolicyEngine/policyengine.py"
LEDGER_BRANCH = "uk-qualification-ledger"
RAW_LEDGER_URL = (
    f"https://raw.githubusercontent.com/{LEDGER_REPOSITORY}/{LEDGER_BRANCH}"
)

__all__ = [
    "LEDGER_BRANCH",
    "LEDGER_REPOSITORY",
    "LedgerInconsistency",
    "attempt_directory",
    "fetch_ledger_receipt",
    "latest_receipts",
    "pair_directory",
    "pending_attempts",
    "latest_attempt_receipt",
    "published_receipt",
    "rederive_publication",
    "verify_certification_evidence",
    "write_json",
]


class LedgerInconsistency(ValueError):
    """A pair's published receipt is not any one attempt's receipt."""


def write_json(path: Path, value: Any) -> None:
    """Write readable, deterministic JSON (digests are over the JSON value)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pair_directory(root: Path, country_id: str, pair_id: str) -> Path:
    return root / country_id / pair_id


def attempt_directory(
    root: Path, country_id: str, pair_id: str, attempt_key: str
) -> Path:
    if "/" in attempt_key or attempt_key in ("", ".", ".."):
        raise ValueError(f"Invalid attempt key {attempt_key!r}.")
    return pair_directory(root, country_id, pair_id) / "attempts" / attempt_key


def _matches_an_attempt(
    receipt: QualificationReceipt, attempt_receipts: Iterable[QualificationReceipt]
) -> bool:
    """Whether ``receipt`` is one attempt's receipt, a review acceptance aside.

    ``unreviewed_sha256`` covers every field but ``review``, so a receipt that
    joins one attempt's harness to another's replay or gates matches neither.
    """

    return any(
        attempt.unreviewed_sha256 == receipt.unreviewed_sha256
        for attempt in attempt_receipts
    )


def latest_attempt_receipt(
    pair_dir: Path,
) -> Optional[tuple[str, int, QualificationReceipt]]:
    """The receipt a pair publishes: its latest-staged attempt's current receipt.

    Attempts are ordered by the ``sequence`` in their ``staging.json`` (0 when
    absent); an attempt without a receipt yet does not count. Returns the
    attempt key, its sequence and its receipt, or None if no attempt has one.
    """

    latest: Optional[tuple[int, str, Path]] = None
    for path in pair_dir.glob("attempts/*/qualification_receipt.json"):
        stage = path.parent / "staging.json"
        sequence = int(read_json(stage)["sequence"]) if stage.exists() else 0
        candidate = (sequence, path.parent.name, path)
        if latest is None or candidate[:2] > latest[:2]:
            latest = candidate
    if latest is None:
        return None
    sequence, key, path = latest
    return key, sequence, QualificationReceipt.model_validate(read_json(path))


def published_receipt(pair_dir: Path) -> QualificationReceipt:
    """A pair's published receipt, verified against the attempts it derives from.

    It must be the current receipt of the pair's latest-staged attempt
    (:func:`latest_attempt_receipt`), up to a review acceptance, which is added
    afterwards. Raises :class:`LedgerInconsistency` otherwise, for instance
    after a textual merge of two attempts' receipts.
    """

    receipt = QualificationReceipt.model_validate(
        read_json(pair_dir / "qualification_receipt.json")
    )
    latest = latest_attempt_receipt(pair_dir)
    if latest is None:
        raise LedgerInconsistency(
            f"{pair_dir.name}: a qualification receipt is published but no "
            "attempt has one"
        )
    key, _, attempt = latest
    if not _matches_an_attempt(receipt, [attempt]):
        raise LedgerInconsistency(
            f"{pair_dir.name}: the published qualification receipt "
            f"({receipt.unreviewed_sha256}) is not the receipt of attempt {key}, "
            "the latest staged"
        )
    return receipt


def rederive_publication(pair_dir: Path) -> Optional[QualificationReceipt]:
    """Rewrite a pair's published files from its attempts.

    Writes ``qualification_receipt.json`` (the latest-staged attempt's
    receipt), ``latest_attempt.json`` and ``pair.json``. A review acceptance of
    exactly that receipt is kept, from the published receipt if it validates or
    from ``reviews/``, the latest acceptance first. Used after a concurrent
    publish, so that git never decides these files by merging two attempts.
    """

    latest = latest_attempt_receipt(pair_dir)
    if latest is None:
        return None
    key, sequence, receipt = latest
    published = pair_dir / "qualification_receipt.json"
    accepted: list[QualificationReceipt] = []
    for source in [published, *sorted(pair_dir.glob("reviews/*.json"))]:
        if not source.exists():
            continue
        try:
            candidate = QualificationReceipt.model_validate(read_json(source))
        except ValueError:
            continue
        if (
            candidate.review is not None
            and candidate.promotable
            and candidate.unreviewed_sha256 == receipt.unreviewed_sha256
        ):
            accepted.append(candidate)
    if accepted:
        receipt = max(accepted, key=lambda item: item.review.accepted_at)
    write_json(published, receipt.canonical_payload())
    write_json(
        pair_dir / "latest_attempt.json", {"attempt_key": key, "sequence": sequence}
    )
    write_json(pair_dir / "pair.json", receipt.pair.canonical_payload())
    return receipt


def latest_receipts(
    root: Path,
    country_id: str = "uk",
    *,
    problems: Optional[list[str]] = None,
) -> list[QualificationReceipt]:
    """Every pair's latest terminal receipt in a checked-out ledger.

    A pair whose published receipt is not one of its attempts' receipts is
    left out, and the reason is appended to ``problems`` when given.
    """

    base = root / country_id
    if not base.is_dir():
        return []
    receipts = []
    for path in sorted(base.glob("*/qualification_receipt.json")):
        try:
            receipts.append(published_receipt(path.parent))
        except LedgerInconsistency as error:
            if problems is not None:
                problems.append(str(error))
    return receipts


def pending_attempts(root: Path, country_id: str = "uk") -> list[Path]:
    """Attempts that sent a replay request and have no receipt yet."""

    base = root / country_id
    if not base.is_dir():
        return []
    return sorted(
        path.parent.parent
        for path in base.glob("*/attempts/*/replay/request.json")
        if not (path.parent.parent / "qualification_receipt.json").exists()
    )


def fetch_ledger_receipt(
    country_id: str,
    pair_id: str,
    *,
    get: Optional[Callable[..., Any]] = None,
) -> Optional[QualificationReceipt]:
    """Read a pair's latest receipt from the published ledger branch.

    The receipt must be the receipt of the attempt ``latest_attempt.json``
    names (a review acceptance aside), as :func:`published_receipt` requires
    of a checked-out ledger; otherwise :class:`LedgerInconsistency` is raised.
    """

    if get is None:
        import requests

        get = requests.get
    base = f"{RAW_LEDGER_URL}/{country_id}/{pair_id}"
    response = get(f"{base}/qualification_receipt.json", timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    receipt = QualificationReceipt.model_validate_json(response.text)
    pointer_response = get(f"{base}/latest_attempt.json", timeout=30)
    if pointer_response.status_code == 404:
        raise LedgerInconsistency(
            f"{pair_id}: the published receipt names no attempt (no latest_attempt.json)"
        )
    pointer_response.raise_for_status()
    attempt_key = json.loads(pointer_response.text).get("attempt_key")
    if not isinstance(attempt_key, str) or not attempt_key or "/" in attempt_key:
        raise LedgerInconsistency(f"{pair_id}: latest_attempt.json is malformed")
    attempt_response = get(
        f"{base}/attempts/{attempt_key}/qualification_receipt.json", timeout=30
    )
    if attempt_response.status_code == 404:
        raise LedgerInconsistency(
            f"{pair_id}: attempt {attempt_key} has no qualification receipt"
        )
    attempt_response.raise_for_status()
    attempt = QualificationReceipt.model_validate_json(attempt_response.text)
    if not _matches_an_attempt(receipt, [attempt]):
        raise LedgerInconsistency(
            f"{pair_id}: the published qualification receipt is not attempt "
            f"{attempt_key}'s receipt"
        )
    return receipt


def verify_certification_evidence(
    record: Mapping[str, Any],
    receipt: Optional[QualificationReceipt],
) -> list[str]:
    """Problems with a bundle certification record's qualification evidence.

    Records on any basis other than ``qualified_exact_pair`` need no ledger
    evidence and return no problems. A qualified exact pair needs a
    promotable receipt for exactly the model wheel (its hash must be stated),
    core, data release and dataset the record certifies, including the
    default dataset's reference (repository, path, revision and bytes), which
    is what the runtime resolves.
    """

    certification = record.get("certification") or {}
    if certification.get("compatibility_basis") != "qualified_exact_pair":
        return []
    pair_id = certification.get("qualification_pair_id")
    if not pair_id:
        return ["qualified_exact_pair certificate names no qualification_pair_id"]
    if receipt is None:
        return [f"no qualification receipt in the ledger for pair {pair_id}"]

    problems: list[str] = []
    if receipt.pair_id != pair_id:
        problems.append("ledger receipt is for a different pair")
    if not receipt.promotable:
        problems.append(
            f"ledger receipt verdict is {receipt.verdict} without an accepted review"
        )
    pair = receipt.pair
    model = record.get("model_package") or {}
    data = record.get("data_package") or {}
    artifact = record.get("certified_data_artifact") or {}
    reference = (record.get("datasets") or {}).get(record.get("default_dataset")) or {}
    expected: Iterable[tuple[str, Any, Any]] = (
        (
            "model version",
            pair.model.version,
            certification.get("certified_for_model_version"),
        ),
        ("model version in bundle", pair.model.version, model.get("version")),
        ("model wheel sha256", pair.model.wheel_sha256, model.get("sha256")),
        (
            "core version",
            pair.core.version,
            certification.get("certified_for_core_version"),
        ),
        ("data release", pair.data.release_version, data.get("version")),
        (
            "release manifest revision",
            pair.data.release_manifest_revision,
            data.get("release_manifest_revision"),
        ),
        ("default dataset", pair.data.dataset, record.get("default_dataset")),
        ("certified dataset", pair.data.dataset, artifact.get("dataset")),
        ("dataset sha256", pair.data.dataset_sha256, artifact.get("sha256")),
        # The reference the runtime actually resolves and downloads.
        ("dataset reference repo", pair.data.repo_id, reference.get("repo_id")),
        ("dataset reference path", pair.data.dataset_path, reference.get("path")),
        (
            "dataset reference revision",
            pair.data.dataset_revision,
            reference.get("revision"),
        ),
        ("dataset reference sha256", pair.data.dataset_sha256, reference.get("sha256")),
        ("data build id", pair.data.build_id, certification.get("data_build_id")),
    )
    for label, qualified, certified in expected:
        if qualified != certified:
            problems.append(
                f"{label}: qualified {qualified!r}, certified {certified!r}"
            )
    return problems
