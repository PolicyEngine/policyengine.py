"""The qualification ledger: durable evidence for every candidate attempt.

The ledger is the orphan branch ``uk-qualification-ledger`` of
PolicyEngine/policyengine.py. Each candidate pair owns one directory, so
concurrent qualifications never write the same file::

    <country>/<pair_id>/
        pair.json                       the CandidatePair
        qualification_receipt.json      the latest terminal receipt for the pair
        attempts/<attempt_key>/
            harness.json                the candidate commit that ran it
            gates/<gate_id>.json        each gate's evidence
            replay/request.json         the request sent to the scorecard
            replay/status.json          the terminal status read back
            replay/receipt.json         the receipt bytes read back
            qualification_receipt.json  this attempt's receipt

Failed and incomplete attempts are kept: the ledger never deletes evidence.
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
    "attempt_directory",
    "fetch_ledger_receipt",
    "latest_receipts",
    "pair_directory",
    "pending_attempts",
    "verify_certification_evidence",
    "write_json",
]


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


def latest_receipts(root: Path, country_id: str = "uk") -> list[QualificationReceipt]:
    """Every pair's latest terminal receipt in a checked-out ledger."""

    base = root / country_id
    if not base.is_dir():
        return []
    receipts = []
    for path in sorted(base.glob("*/qualification_receipt.json")):
        receipts.append(QualificationReceipt.model_validate(read_json(path)))
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
    """Read a pair's latest receipt from the published ledger branch."""

    if get is None:
        import requests

        get = requests.get
    response = get(
        f"{RAW_LEDGER_URL}/{country_id}/{pair_id}/qualification_receipt.json",
        timeout=30,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return QualificationReceipt.model_validate_json(response.text)


def verify_certification_evidence(
    record: Mapping[str, Any],
    receipt: Optional[QualificationReceipt],
) -> list[str]:
    """Problems with a bundle certification record's qualification evidence.

    Records on any basis other than ``qualified_exact_pair`` need no ledger
    evidence and return no problems. A qualified exact pair needs a
    promotable receipt for exactly the model wheel, core, data release and
    dataset bytes the record certifies.
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
    expected: Iterable[tuple[str, Any, Any]] = (
        (
            "model version",
            pair.model.version,
            certification.get("certified_for_model_version"),
        ),
        ("model version in bundle", pair.model.version, model.get("version")),
        (
            "model wheel sha256",
            pair.model.wheel_sha256,
            model.get("sha256", pair.model.wheel_sha256),
        ),
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
        ("dataset sha256", pair.data.dataset_sha256, artifact.get("sha256")),
        ("data build id", pair.data.build_id, certification.get("data_build_id")),
    )
    for label, qualified, certified in expected:
        if qualified != certified:
            problems.append(
                f"{label}: qualified {qualified!r}, certified {certified!r}"
            )
    return problems
