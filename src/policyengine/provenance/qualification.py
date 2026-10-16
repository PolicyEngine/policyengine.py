"""Candidate qualification contracts and pure decision rules.

A *candidate* is a country model wheel, its core wheel and a data release
that are not yet certified together. Qualification:

1. prepares a policyengine.py commit whose packaged manifest, pins, lock and
   TRO certify the pair (the candidate commit, which is also what promotion
   merges);
2. runs mandatory local gates on that commit (:data:`REQUIRED_GATES`);
3. sends the replay corpus owner (policyengine-scorecard) an immutable
   :class:`ReplayQualificationRequest`, polls its :class:`ReplayStatus` and
   checks the :class:`ReplayReceipt` against the request
   (:func:`evaluate_replay_receipt`);
4. records a :class:`QualificationReceipt` whose verdict is a pure function of
   the gate results (:func:`qualification_verdict`).

Promotion then picks the newest promotable pair that strictly advances the
certified pair (:func:`select_promotion_target`), so a stale completion
cannot displace a newer accepted candidate.

The replay request, status and receipt mirror the JSON Schemas published by
policyengine-scorecard (vendored, unchanged, in
``policyengine/data/schemas/vendor/policyengine-scorecard/``). Their digests
are plain RFC 8785 over the document as sent, nulls included, which is what
the scorecard computes. W4's own receipts use the receipt-v1 rule of
:func:`policyengine.provenance.receipt.content_sha256` (nulls dropped).
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, ClassVar, Literal, Optional

from packaging.version import Version
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from policyengine.provenance.canonical import canonical_sha256
from policyengine.provenance.manifest import ArtifactPathReference
from policyengine.provenance.receipt import (
    GIT_SHA_PATTERN,
    SHA256_PATTERN,
    _Contract,
    content_sha256,
)

__all__ = [
    "BLOCKING_REPLAY_FLAGS",
    "REPLAY_POLICY_ID",
    "REQUIRED_GATES",
    "REVIEW_REPLAY_FLAGS",
    "CandidatePair",
    "GateResult",
    "QualificationHarness",
    "QualificationReceipt",
    "ReplayQualificationRequest",
    "ReplayReceipt",
    "ReplayStatus",
    "ReviewAcceptance",
    "dominates",
    "evaluate_replay_receipt",
    "qualification_verdict",
    "select_promotion_target",
]

# --- Gate results and verdicts ------------------------------------------

GateStatus = Literal["pass", "needs_review", "unavailable", "fail", "error"]
Verdict = Literal["qualified", "needs_review", "incomplete", "rejected"]

#: Every mandatory gate. A gate has no "skipped" status: a gate whose harness
#: is missing reports ``unavailable`` (the candidate is then incomplete, not
#: promotable), a gate that crashed while evaluating the candidate reports
#: ``error`` (the candidate is rejected), and a gate that never reported
#: leaves the qualification incomplete.
REQUIRED_GATES: tuple[str, ...] = (
    "installed_versions",
    "wheel_hashes",
    "core_compatibility",
    "data_access",
    "dataset_bytes",
    "supported_years",
    "budget_inputs",
    "reform_contract",
    "metrics_review",
    "reform_responsiveness",
    "replay",
)

_SEVERITY: dict[str, int] = {
    "pass": 0,
    "needs_review": 1,
    "unavailable": 2,
    "fail": 3,
    "error": 3,
}

#: The replay gate's policy (cos d1344): fail on the regressions a receipt
#: identifies, call a gap known only on base-side evidence, and send every
#: other flagged move to a named reviewer. Its text ships as
#: ``data/qualification/replay_policy.md`` and each receipt records its digest.
REPLAY_POLICY_ID = "d1344-replay-regressions-v1"
REPLAY_POLICY_FILE = "replay_policy.md"
#: Flags that fail whatever the row says.
BLOCKING_REPLAY_FLAGS: frozenset[str] = frozenset({"mapping"})
#: Flags that need review unless the row is a lost result or lost response.
REVIEW_REPLAY_FLAGS: frozenset[str] = frozenset(
    {"numerical", "structural", "coverage", "support", "inertness", "construction"}
)
#: The diff's numerical bound: a move needs at least max(this, 1% of the
#: base's absolute value) to be flagged.
REPLAY_ABSOLUTE_BOUND_GBP = 1_000_000.0
REPLAY_RELATIVE_BOUND = 0.01


@functools.cache
def _vendored_validator(name: str) -> Any:
    """A validator for one vendored policyengine-scorecard schema."""

    from importlib.resources import files

    import jsonschema

    schema = json.loads(
        (
            files("policyengine")
            / "data"
            / "schemas"
            / "vendor"
            / "policyengine-scorecard"
            / name
        ).read_text(encoding="utf-8")
    )
    validator = jsonschema.validators.validator_for(schema)
    validator.check_schema(schema)
    return validator(schema)


def conform_to_vendored_schema(document: Mapping[str, Any], name: str) -> None:
    """Raise ``ValueError`` unless ``document`` is valid against the vendored
    scorecard schema ``name``. The mirrors are a typed view; the schema decides
    what a received document may contain (no nulls where it allows none, no
    strings where it requires integers)."""

    error = next(iter(_vendored_validator(name).iter_errors(dict(document))), None)
    if error is not None:
        where = "/".join(str(part) for part in error.absolute_path) or "the document"
        raise ValueError(f"{name}: {error.message} (at {where})")


def replay_policy_sha256() -> str:
    """SHA-256 of the replay policy text this package applies."""

    from importlib.resources import files

    data = files("policyengine.data.qualification") / REPLAY_POLICY_FILE
    return hashlib.sha256(data.read_bytes()).hexdigest()


class GateResult(_Contract):
    """One mandatory qualification gate."""

    gate_id: str
    status: GateStatus
    summary: str = Field(min_length=1)
    evidence_sha256: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
        description="content_sha256 of the evidence JSON stored with the receipt.",
    )
    details: dict[str, Any] = Field(default_factory=dict)


def qualification_verdict(gates: Iterable[GateResult]) -> Verdict:
    """The verdict a set of gate results determines.

    - ``rejected`` if any gate failed or errored;
    - otherwise ``incomplete`` if any gate is unavailable or a required gate
      did not report;
    - otherwise ``needs_review`` if any gate needs review;
    - otherwise ``qualified``.

    Making any gate worse never makes the verdict better.
    """

    gates = list(gates)
    worst = max((_SEVERITY[gate.status] for gate in gates), default=0)
    if worst >= _SEVERITY["fail"]:
        return "rejected"
    reported = {gate.gate_id for gate in gates}
    if worst == _SEVERITY["unavailable"] or any(
        gate_id not in reported for gate_id in REQUIRED_GATES
    ):
        return "incomplete"
    if worst == _SEVERITY["needs_review"]:
        return "needs_review"
    return "qualified"


# --- What is qualified ----------------------------------------------------


class PinnedWheel(_Contract):
    name: str
    version: str
    wheel_sha256: str = Field(pattern=SHA256_PATTERN)


class PinnedData(_Contract):
    data_package: str
    release_version: str
    build_id: str
    repo_id: str
    repo_type: Literal["model", "dataset"]
    release_manifest_path: str
    release_manifest_revision: str
    release_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    dataset: str
    dataset_path: str
    dataset_revision: str
    dataset_sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=1)


class CandidatePair(_Contract):
    """The model, core and data that would be certified together.

    ``pair_id`` (its receipt-v1 digest) does not depend on the policyengine.py
    commit, so the candidate commit's manifest can name the pair it certifies.
    """

    country_id: Literal["uk"]
    model: PinnedWheel
    core: PinnedWheel
    data: PinnedData

    @property
    def pair_id(self) -> str:
        return content_sha256(self.canonical_payload())

    @property
    def order_key(self) -> tuple[str, str, str]:
        """(model version, data release, core version): what promotion orders."""

        return (self.model.version, self.data.release_version, self.core.version)


class QualificationHarness(_Contract):
    """The policyengine.py commit that carried and ran the qualification."""

    policyengine_version: str
    git_commit: str = Field(pattern=GIT_SHA_PATTERN)
    packaged_bundle_manifest_sha256: str = Field(pattern=SHA256_PATTERN)


class IssuedBy(_Contract):
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    workflow_run_id: int = Field(ge=1)
    run_attempt: int = Field(default=1, ge=1)
    run_url: str


class PreviousCertificate(_Contract):
    """The certified pair a candidate would replace."""

    bundle_version: str
    model_version: str
    core_version: str
    data_release_version: str
    dataset_sha256: str = Field(pattern=SHA256_PATTERN)
    certificate_sha256: str = Field(pattern=SHA256_PATTERN)
    qualification_pair_id: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    model_wheel_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    core_wheel_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    dataset_reference: Optional[ArtifactPathReference] = None
    dataset_name: Optional[str] = None
    release_manifest_reference: Optional[ArtifactPathReference] = None


class ReplayReference(_Contract):
    request_id: str = Field(pattern=SHA256_PATTERN)
    receipt_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    receipt_commit: Optional[str] = Field(default=None, pattern=GIT_SHA_PATTERN)


class ReviewAcceptance(_Contract):
    """A reviewer's acceptance of one exact needs-review receipt."""

    reviewer: str = Field(min_length=1)
    accepted_at: str
    accepted_receipt_sha256: str = Field(
        pattern=SHA256_PATTERN,
        description="unreviewed_sha256 of the receipt being accepted.",
    )
    explanation: str = Field(min_length=1)


class QualificationReceipt(_Contract):
    """The qualification outcome recorded in the ledger for one candidate."""

    SCHEMA_ID: ClassVar[str] = (
        "https://policyengine.org/schemas/candidate_qualification_receipt.v1.json"
    )

    schema_version: Literal[1]
    receipt_type: Literal["policyengine.candidate_qualification_receipt"]
    pair_id: str = Field(pattern=SHA256_PATTERN)
    pair: CandidatePair
    harness: QualificationHarness
    previous_certificate: Optional[PreviousCertificate] = None
    replay: Optional[ReplayReference] = None
    gates: list[GateResult]
    verdict: Verdict
    review: Optional[ReviewAcceptance] = None
    issued_by: IssuedBy
    completed_at: str = Field(description="ISO 8601 UTC, e.g. 2026-10-15T09:30:00Z.")

    @model_validator(mode="after")
    def _consistent(self) -> QualificationReceipt:
        if self.pair_id != self.pair.pair_id:
            raise ValueError("pair_id is not the digest of pair.")
        ids = [gate.gate_id for gate in self.gates]
        if len(ids) != len(set(ids)):
            raise ValueError("Each gate reports at most once.")
        expected = qualification_verdict(self.gates)
        if self.verdict != expected:
            raise ValueError(
                f"verdict {self.verdict!r} does not follow from the gates ({expected!r})."
            )
        if self.review is not None and self.verdict != "needs_review":
            raise ValueError("Only a needs-review verdict can be accepted on review.")
        return self

    @property
    def unreviewed_sha256(self) -> str:
        """Digest of the receipt without ``review``: what a review accepts."""

        payload = self.canonical_payload()
        payload.pop("review", None)
        return content_sha256(payload)

    @property
    def receipt_sha256(self) -> str:
        return content_sha256(self.canonical_payload())

    @property
    def promotable(self) -> bool:
        """Qualified, or needs review with an acceptance of exactly this receipt."""

        if self.verdict == "qualified":
            return True
        return (
            self.verdict == "needs_review"
            and self.review is not None
            and self.review.accepted_receipt_sha256 == self.unreviewed_sha256
        )


# --- Promotion order ------------------------------------------------------


def _versions(key: Sequence[str]) -> tuple[Version, ...]:
    return tuple(Version(part) for part in key)


def dominates(newer: Sequence[str], older: Sequence[str]) -> bool:
    """``newer`` is at least ``older`` in every component and differs from it."""

    a, b = _versions(newer), _versions(older)
    if len(a) != len(b):
        raise ValueError("Order keys must have the same length.")
    return a != b and all(x >= y for x, y in zip(a, b))


def select_promotion_target(
    receipts: Iterable[QualificationReceipt],
    current: Optional[Sequence[str]],
) -> Optional[QualificationReceipt]:
    """The promotable candidate to promote next, or ``None``.

    Eligible receipts are promotable and strictly advance ``current`` (model
    version, data release, core version). Among them the target is the one
    whose pair dominates every other eligible pair. If eligible pairs have no
    single newest member (a newer model with an older data release, say),
    nothing is promoted automatically. The result depends only on the set of
    receipts, never on the order they arrive in.
    """

    eligible: dict[tuple[str, ...], QualificationReceipt] = {}
    for receipt in receipts:
        if not receipt.promotable:
            continue
        key = tuple(receipt.pair.order_key)
        if current is not None and not dominates(key, current):
            continue
        incumbent = eligible.get(key)
        if incumbent is None or (receipt.completed_at, receipt.receipt_sha256) > (
            incumbent.completed_at,
            incumbent.receipt_sha256,
        ):
            eligible[key] = receipt
    keys = list(eligible)
    for key in keys:
        if all(other == key or dominates(key, other) for other in keys):
            return eligible[key]
    return None


# --- Replay interface (mirrors policyengine-scorecard schemas v1) ---------


class _Mirror(BaseModel):
    """Closed, immutable mirror of a scorecard JSON Schema object."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    def document(self) -> dict[str, Any]:
        """The JSON document exactly as the scorecard schema spells it."""

        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class _Open(_Mirror):
    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)


_SHA1 = GIT_SHA_PATTERN
_VERSION = r"^[0-9]+(\.[0-9]+)*([a-z0-9.+-]*)$"


class GitSource(_Mirror):
    repository: Literal["PolicyEngine/policyengine.py"]
    commit: str = Field(pattern=_SHA1)


class PypiSource(_Mirror):
    wheel_sha256: str = Field(pattern=SHA256_PATTERN)


class WrapperSource(_Mirror):
    git: Optional[GitSource] = None
    pypi: Optional[PypiSource] = None

    @model_validator(mode="after")
    def _one_source(self) -> WrapperSource:
        if (self.git is None) == (self.pypi is None):
            raise ValueError("The wrapper source is exactly one of git or pypi.")
        return self


class RequestWrapper(_Mirror):
    version: str = Field(pattern=_VERSION)
    source: WrapperSource
    packaged_bundle_manifest_sha256: str = Field(pattern=SHA256_PATTERN)


class RequestPackage(_Mirror):
    version: str = Field(pattern=_VERSION)
    wheel_sha256: str = Field(pattern=SHA256_PATTERN)


class RequestData(_Mirror):
    build_id: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    repo_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    repo_type: Literal["model", "dataset"]
    revision: str = Field(min_length=1)
    path: str = Field(min_length=1, pattern=r"^[^/][^\\]*$")
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=1)
    release_manifest_sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("path")
    @classmethod
    def _no_parent_segments(cls, path: str) -> str:
        # The schema says ^(?!.*(^|/)\.\.(/|$))[^/][^\\]*$; pydantic's regex
        # engine has no look-ahead, so the '..' rule is checked here.
        if ".." in path.split("/"):
            raise ValueError("data.path must not contain '..' segments.")
        return path


class RequestCandidate(_Mirror):
    policyengine: RequestWrapper
    policyengine_uk: RequestPackage
    policyengine_core: RequestPackage
    data: RequestData
    expected_release_bundle: dict[str, Optional[str]]

    @field_validator("expected_release_bundle")
    @classmethod
    def _required_bundle_fields(
        cls, bundle: dict[str, Optional[str]]
    ) -> dict[str, Optional[str]]:
        for key in (
            "policyengine_version",
            "model_version",
            "certified_data_build_id",
            "certified_data_artifact_sha256",
            "default_dataset_uri",
        ):
            if not bundle.get(key):
                raise ValueError(f"expected_release_bundle needs {key}.")
        return bundle


class RequestedBy(_Open):
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    workflow_run_id: Optional[int] = Field(default=None, ge=1)
    run_attempt: Optional[int] = Field(default=None, ge=1)
    commit: str = Field(pattern=_SHA1)


class ReplayQualificationRequest(_Mirror):
    """``policyengine.uk-replay-qualification-request/v1``."""

    schema_id: Literal["policyengine.uk-replay-qualification-request/v1"] = Field(
        alias="schema"
    )
    kind: Literal["candidate", "released_bundle"]
    attempt: int = Field(ge=1)
    candidate: RequestCandidate
    compare_to: str = Field(min_length=1)
    requested_by: RequestedBy

    @model_validator(mode="after")
    def _released_bundles_come_from_pypi(self) -> ReplayQualificationRequest:
        if (
            self.kind == "released_bundle"
            and self.candidate.policyengine.source.pypi is None
        ):
            raise ValueError("A released_bundle request names the PyPI wheel.")
        return self

    @property
    def request_id(self) -> str:
        """Plain RFC 8785 SHA-256 of the request document, as the scorecard computes."""

        return canonical_sha256(self.document())


class StatusEvent(_Mirror):
    status: Literal["queued", "running", "complete", "rejected", "failed"]
    at: str
    run_url: str = Field(
        pattern=r"^https://github\.com/PolicyEngine/policyengine-scorecard/actions/runs/[0-9]+"
    )


class ReplayStatus(_Mirror):
    """``policyengine.uk-replay-status/v1`` (``requests/<id>/STATUS.json``)."""

    schema_id: Literal["policyengine.uk-replay-status/v1"] = Field(alias="schema")
    request_id: str = Field(pattern=SHA256_PATTERN)
    status: Literal["queued", "running", "complete", "rejected", "failed"]
    history: list[StatusEvent] = Field(min_length=1)
    receipt_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    receipt_commit: Optional[str] = Field(default=None, pattern=_SHA1)

    @model_validator(mode="after")
    def _terminal_names_receipt(self) -> ReplayStatus:
        if self.terminal and (
            self.receipt_sha256 is None or self.receipt_commit is None
        ):
            raise ValueError("A terminal status names its receipt digest and commit.")
        return self

    @property
    def terminal(self) -> bool:
        return self.status in ("complete", "rejected", "failed")


class Rejection(_Mirror):
    code: Literal[
        "schema_invalid",
        "artifact_hash_mismatch",
        "release_bundle_mismatch",
        "incompatible_pair",
        "data_access_failed",
        "no_supported_years",
    ]
    detail: str = Field(min_length=1)


class InstalledPackage(_Mirror):
    version: str = Field(min_length=1)
    record_sha256: str = Field(pattern=SHA256_PATTERN)
    wheel_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)


class ExecutedPackages(_Mirror):
    policyengine: InstalledPackage
    policyengine_uk: InstalledPackage = Field(alias="policyengine-uk")
    policyengine_core: InstalledPackage = Field(alias="policyengine-core")


class Execution(_Mirror):
    packages: ExecutedPackages
    packaged_bundle_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    release_bundle: dict[str, Optional[str]]
    dataset_sha256: str = Field(pattern=SHA256_PATTERN)
    requirements_sha256: str = Field(pattern=SHA256_PATTERN)
    python: str = Field(pattern=r"^3\.[0-9]+\.[0-9]+$")
    platform: str = Field(min_length=1)
    runner: str = Field(min_length=1)


class UnsupportedYear(_Mirror):
    year: int
    reason: Literal["before_data_year", "after_extension_end"]


class MeasureYear(_Mirror):
    measure_key: str = Field(min_length=1)
    year: int


#: The name the inert lists used before scorecard#183 shared the definition.
InertMeasureYear = MeasureYear


def _unique(values: Optional[Sequence[Any]], name: str) -> None:
    """The schema's ``uniqueItems``."""

    if values is None:
        return
    keys = [
        value.model_dump_json() if isinstance(value, BaseModel) else repr(value)
        for value in values
    ]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name} lists an item twice.")


class EventResult(_Mirror):
    registry_sha256: str = Field(pattern=SHA256_PATTERN)
    supported_years: list[int]
    unsupported_years: list[UnsupportedYear]
    run_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    staging_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    comparison_provenance_sha256: str = Field(pattern=SHA256_PATTERN)
    artifacts: int = Field(ge=0)
    full_supported_grid_complete: bool
    inert_measure_years: list[MeasureYear]
    #: Staging's lists (scorecard#183): the full event grid less what was
    #: computed, and the full grid less the supported years. Older receipts
    #: omit them.
    missing_measure_years: Optional[list[MeasureYear]] = None
    unsupported_measure_years: Optional[list[MeasureYear]] = None

    @model_validator(mode="after")
    def _unique_items(self) -> EventResult:
        for name in (
            "supported_years",
            "inert_measure_years",
            "missing_measure_years",
            "unsupported_measure_years",
        ):
            _unique(getattr(self, name), name)
        return self


class BaseEvent(_Mirror):
    """The comparison base's own grid record for one event (scorecard#183),
    read from the base's staging and run manifests that the diff verified."""

    staging_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    run_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    supported_years: list[int]
    full_supported_grid_complete: bool
    inert_measure_years: list[MeasureYear]
    missing_measure_years: list[MeasureYear]
    unsupported_measure_years: list[MeasureYear]

    @model_validator(mode="after")
    def _unique_items(self) -> BaseEvent:
        for name in (
            "supported_years",
            "inert_measure_years",
            "missing_measure_years",
            "unsupported_measure_years",
        ):
            _unique(getattr(self, name), name)
        return self


class Corpus(_Mirror):
    corpus_version: str = Field(min_length=1)
    events: dict[str, EventResult] = Field(min_length=1)


class IntegrityFailure(_Mirror):
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    event: Optional[str] = None
    measure_key: Optional[str] = None
    year: Optional[int] = None


class Integrity(_Mirror):
    status: Literal["complete", "incomplete", "failed", "not_run"]
    failures: list[IntegrityFailure]


FlagKind = Literal[
    "numerical",
    "structural",
    "coverage",
    "mapping",
    "support",
    "inertness",
    "construction",
]


class FlagCounts(_Mirror):
    numerical: int = Field(ge=0)
    structural: int = Field(ge=0)
    coverage: int = Field(ge=0)
    mapping: int = Field(ge=0)
    support: int = Field(ge=0)
    inertness: int = Field(ge=0)
    construction: int = Field(ge=0)


class FlaggedRow(_Mirror):
    event: str = Field(min_length=1)
    measure_key: str = Field(min_length=1)
    year: int
    level: Literal["source_row", "measure_year", "head"]
    key: str = Field(min_length=1)
    flags: list[FlagKind] = Field(min_length=1)
    base_gbp: Optional[float] = None
    head_gbp: Optional[float] = None


class Diff(_Mirror):
    base_variant_id: str = Field(min_length=1)
    diff_sha256: str = Field(pattern=SHA256_PATTERN)
    flag_counts: FlagCounts
    flagged_rows: list[FlaggedRow]
    #: Per event the base replayed in the current layout (scorecard#183). A
    #: legacy-layout base, or an event the base did not replay, has no entry.
    base_events: Optional[dict[str, BaseEvent]] = None


class ResultsLocation(_Mirror):
    repository: Literal["PolicyEngine/policyengine-scorecard"]
    ref: str = Field(min_length=1)
    commit: Optional[str] = Field(default=None, pattern=_SHA1)
    path: str = Field(min_length=1)
    manifest_sha256: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
        description="Digest of NAMESPACE_MANIFEST.json for the sealed result namespace.",
    )


class ReplayReceipt(_Mirror):
    """``policyengine.uk-replay-receipt/v1`` (``requests/<id>/REPLAY_RECEIPT.json``).

    Nullable members are kept as ``null`` in :meth:`document`, because the
    scorecard's ``receipt_sha256`` covers them.
    """

    schema_id: Literal["policyengine.uk-replay-receipt/v1"] = Field(alias="schema")
    request_id: str = Field(pattern=SHA256_PATTERN)
    status: Literal["complete", "rejected", "failed"]
    rejection: Optional[Rejection]
    variant_id: Optional[str]
    variant_identity_sha256: Optional[str] = Field(pattern=SHA256_PATTERN)
    execution: Optional[Execution]
    corpus: Optional[Corpus]
    integrity: Integrity
    diff: Optional[Diff]
    results: ResultsLocation
    receipt_sha256: str = Field(pattern=SHA256_PATTERN)

    _received: Optional[dict[str, Any]] = PrivateAttr(default=None)

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> ReplayReceipt:
        """Parse a received receipt, keeping its bytes for digest checks.

        It must satisfy both the mirror and the vendored schema.
        """

        receipt = cls.model_validate(dict(document))
        conform_to_vendored_schema(document, "replay_receipt.v1.json")
        receipt._received = dict(document)
        return receipt

    def document(self) -> dict[str, Any]:
        """The received document if there is one, else this model's spelling."""

        if self._received is not None:
            return dict(self._received)
        top = self.model_dump(mode="json", by_alias=True, exclude_none=False)
        for key in ("rejection", "execution", "corpus", "diff", "results", "integrity"):
            value = getattr(self, key)
            top[key] = value.document() if value is not None else None
        return top

    @property
    def computed_receipt_sha256(self) -> str:
        """Plain RFC 8785 SHA-256 of the receipt without ``receipt_sha256``."""

        document = self.document()
        document.pop("receipt_sha256", None)
        return canonical_sha256(document)

    @model_validator(mode="after")
    def _status_shape(self) -> ReplayReceipt:
        if self.status == "rejected":
            if (
                self.rejection is None
                or self.corpus is not None
                or self.diff is not None
                or self.variant_id is not None
                or self.variant_identity_sha256 is not None
                or self.execution is not None
                or self.integrity.status != "not_run"
            ):
                raise ValueError(
                    "A rejected receipt has a rejection, no variant, execution, "
                    "corpus or diff, and integrity not_run."
                )
        elif self.status == "complete":
            if (
                self.rejection is not None
                or self.variant_id is None
                or self.variant_identity_sha256 is None
                or self.execution is None
                or self.results.manifest_sha256 is None
            ):
                raise ValueError(
                    "A complete receipt has a variant and its identity, an "
                    "execution and a sealed results manifest."
                )
        # A failed receipt can come from a step before the candidate's
        # identity was known (for example a download error).
        elif self.rejection is not None or self.integrity.status != "failed":
            raise ValueError(
                "A failed receipt has no rejection and a failed integrity."
            )
        if self.status == "complete" and (
            self.integrity.status not in ("complete", "incomplete")
            or self.corpus is None
        ):
            raise ValueError("A complete receipt has a corpus and a run integrity.")
        return self


def _is_the_gap(row: FlaggedRow, gap: Mapping[str, Any]) -> bool:
    """Whether a coverage row is scorecard's own record of a mixed known gap.

    Where one side is inert and the other missing, scorecard compares an
    inert artifact (identical worlds, a total of exactly £0) with none, and
    writes a coverage row with £0 on the inert side and nothing on the
    other. Any other shape at a known gap is judged as usual.
    """

    if gap["candidate"] == "inert" and gap["why"] == "missing in the base":
        return row.base_gbp is None and row.head_gbp == 0
    if gap["candidate"] == "missing" and gap["why"] == "inert in the base":
        return row.head_gbp is None and row.base_gbp == 0
    return False


def evaluate_replay_receipt(
    request: ReplayQualificationRequest,
    status: ReplayStatus,
    receipt: ReplayReceipt,
) -> GateResult:
    """The ``replay`` gate for a terminal replay status and its receipt.

    The receipt must answer this exact request, be the bytes the status
    names, and report an execution of exactly the requested artifacts. Its
    contents are then judged by policy ``d1344-replay-regressions-v1``
    (``data/qualification/replay_policy.md``):

    - fail on rejected or failed replays, mapping flags, lost results
      (a base value with no candidate value), lost responses (a measure-year
      the candidate lists as inert, or a measure-year total of exactly £0
      against a base at least the diff's bound away) and incomplete grids,
      unless a gap is known: the base's own record (``diff.base_events``)
      lists the same measure-year as inert, or missing and supported. A
      known gap does not block, and neither do the rows by which scorecard
      records a mixed one (``_is_the_gap``, and the base-only inertness
      where the candidate is missing and the base inert); a material value
      at a known gap still fails;
    - send every other flagged move to review.

    Unsupported years are reported, never failed on their own. The gate's
    details record the policy id, the policy text's SHA-256, the known gaps
    and the rows that record them, the regressions and the review items.

    The receipt is read as a whole: a receipt that contradicts itself fails
    (failures listed under a complete integrity, ``flag_counts`` that differ
    from its rows' flags, supported years with no artifacts, nothing
    replayed at all) or contradicts the request (a comparison base other
    than the ``compare_to`` asked for).
    """

    request_id = request.request_id
    problems: list[str] = []
    if status.request_id != request_id or receipt.request_id != request_id:
        problems.append("status or receipt answers a different request")
    if not status.terminal:
        problems.append(f"replay is still {status.status}")
    if status.status != receipt.status and status.terminal:
        problems.append("status and receipt disagree on the outcome")
    if receipt.computed_receipt_sha256 != receipt.receipt_sha256:
        problems.append("receipt_sha256 does not match the receipt bytes")
    if status.receipt_sha256 != receipt.receipt_sha256:
        problems.append("status names different receipt bytes")

    details: dict[str, Any] = {
        "request_id": request_id,
        "receipt_sha256": receipt.receipt_sha256,
        "receipt_commit": status.receipt_commit,
        "status": receipt.status,
        "integrity": receipt.integrity.status,
        "policy": REPLAY_POLICY_ID,
        "policy_sha256": replay_policy_sha256(),
        "known_gaps": [],
        "regressions": [],
        "review_items": [],
    }

    def fail_early(kind: str, summary: str, **extra: Any) -> GateResult:
        """A failure decided before the receipt's contents are judged; the
        policy record lists it as the regression."""

        return GateResult(
            gate_id="replay",
            status="fail",
            summary=summary,
            details={
                **details,
                **extra,
                "regressions": [{"kind": kind, "why": summary}],
            },
        )

    if problems:
        return fail_early(
            "unbound",
            "Replay receipt is not bound to this request: " + "; ".join(problems),
            binding_problems=problems,
        )
    if receipt.status == "rejected":
        assert receipt.rejection is not None
        return fail_early(
            "rejected",
            f"Replay rejected the candidate ({receipt.rejection.code}): "
            f"{receipt.rejection.detail}",
            rejection=receipt.rejection.document(),
        )

    execution = receipt.execution
    if execution is None:
        codes = sorted({failure.code for failure in receipt.integrity.failures})
        return fail_early(
            "failed",
            "Replay failed before the candidate was identified: "
            + (", ".join(codes) or "no failure codes"),
            integrity_failures=[
                failure.document() for failure in receipt.integrity.failures
            ],
        )
    candidate = request.candidate
    mismatches: list[str] = []
    packages = {
        "policyengine": (
            execution.packages.policyengine,
            candidate.policyengine.version,
            (
                candidate.policyengine.source.pypi.wheel_sha256
                if candidate.policyengine.source.pypi is not None
                else None
            ),
        ),
        "policyengine-uk": (
            execution.packages.policyengine_uk,
            candidate.policyengine_uk.version,
            candidate.policyengine_uk.wheel_sha256,
        ),
        "policyengine-core": (
            execution.packages.policyengine_core,
            candidate.policyengine_core.version,
            candidate.policyengine_core.wheel_sha256,
        ),
    }
    for name, (installed, version, wheel) in packages.items():
        if installed.version != version:
            mismatches.append(f"{name} {installed.version} ran, not {version}")
        if wheel is not None and installed.wheel_sha256 != wheel:
            mismatches.append(
                f"{name} wheel hash is missing from the receipt"
                if installed.wheel_sha256 is None
                else f"{name} wheel hash differs from the request"
            )
    if (
        execution.packaged_bundle_manifest_sha256
        != candidate.policyengine.packaged_bundle_manifest_sha256
    ):
        mismatches.append("packaged bundle manifest differs from the request")
    if execution.dataset_sha256 != candidate.data.sha256:
        mismatches.append("dataset bytes differ from the request")
    if execution.release_bundle != candidate.expected_release_bundle:
        mismatches.append("release bundle differs from the expected release bundle")
    if mismatches:
        return fail_early(
            "unbound",
            "Replay ran something other than the candidate: " + "; ".join(mismatches),
            execution_mismatches=mismatches,
        )

    if receipt.status == "failed" or receipt.integrity.status == "failed":
        codes = sorted({failure.code for failure in receipt.integrity.failures})
        return fail_early(
            "failed",
            "Replay integrity failed: " + (", ".join(codes) or "no failure codes"),
            integrity_failures=[f.document() for f in receipt.integrity.failures],
        )
    corpus = receipt.corpus
    assert corpus is not None
    incomplete_events = sorted(
        name
        for name, event in corpus.events.items()
        if not event.full_supported_grid_complete
    )
    unsupported = sorted(
        (name, item.year, item.reason)
        for name, event in corpus.events.items()
        for item in event.unsupported_years
    )
    inert = sorted(
        (name, item.measure_key, item.year)
        for name, event in corpus.events.items()
        for item in event.inert_measure_years
    )
    details.update(
        {
            "corpus_version": corpus.corpus_version,
            "events": sorted(corpus.events),
            "unsupported_years": [list(item) for item in unsupported],
            "inert_measure_years": [list(item) for item in inert],
        }
    )
    # A receipt whose parts disagree is not evidence of anything.
    contradictions: list[str] = []
    if receipt.integrity.failures:
        codes = sorted({failure.code for failure in receipt.integrity.failures})
        contradictions.append(
            f"integrity is complete but lists failures ({', '.join(codes)})"
        )
    replayed = 0
    for name, event in sorted(corpus.events.items()):
        replayed += event.artifacts
        listed_missing = {
            (item.measure_key, item.year) for item in event.missing_measure_years or ()
        } - {
            (item.measure_key, item.year)
            for item in event.unsupported_measure_years or ()
        }
        if event.full_supported_grid_complete and (
            event.inert_measure_years or listed_missing
        ):
            contradictions.append(
                f"{name} is complete but lists inert or missing measure-years"
            )
        if event.supported_years and event.artifacts == 0:
            contradictions.append(f"{name} has supported years but no artifacts")
        if not event.supported_years and not event.unsupported_years:
            contradictions.append(f"{name} names no years at all")
    if replayed == 0:
        contradictions.append("no measure-year was replayed")
    counts = receipt.diff.flag_counts.document() if receipt.diff is not None else {}
    rows = receipt.diff.flagged_rows if receipt.diff is not None else []
    row_counts: dict[str, int] = {}
    for row in rows:
        for kind in row.flags:
            row_counts[kind] = row_counts.get(kind, 0) + 1
    # Scorecard's counters are tallies of its rows' flags, so any difference,
    # either way, is a receipt that contradicts itself.
    for kind in sorted(set(row_counts) | {kind for kind, n in counts.items() if n}):
        seen, counted = row_counts.get(kind, 0), counts.get(kind, 0)
        if seen != counted:
            contradictions.append(
                f"{seen} flagged row(s) carry {kind} but flag_counts says {counted}"
            )
    details["flag_counts"] = counts
    details["flagged_row_counts"] = row_counts
    if receipt.diff is not None:
        details["base_variant_id"] = receipt.diff.base_variant_id
        details["diff_sha256"] = receipt.diff.diff_sha256
    if request.compare_to != "latest_certified":
        base = receipt.diff.base_variant_id if receipt.diff is not None else None
        if base != request.compare_to:
            contradictions.append(
                f"the request asked for a comparison with {request.compare_to}, "
                f"but the receipt compares with {base}"
            )
    if contradictions:
        return fail_early(
            "contradiction",
            "Replay receipt contradicts itself or the request: "
            + "; ".join(contradictions),
            contradictions=contradictions,
        )
    # A gap is known only where the base's own grid record (scorecard#183)
    # lists the same measure-year as inert, or missing and supported, for the
    # same event. A legacy-layout base, or an event the base did not replay,
    # has no record, so none of its gaps are known.
    base_events = (receipt.diff.base_events or {}) if receipt.diff is not None else {}

    def pairs(items: Optional[Sequence[MeasureYear]]) -> set[tuple[str, int]]:
        return {(item.measure_key, item.year) for item in items or ()}

    def missing_supported(record: Any) -> Optional[set[tuple[str, int]]]:
        if record.missing_measure_years is None:
            return None
        return pairs(record.missing_measure_years) - pairs(
            record.unsupported_measure_years
        )

    known_gaps: list[dict[str, Any]] = []
    for name, event in sorted(corpus.events.items()):
        base = base_events.get(name)
        if base is None:
            continue
        base_inert = pairs(base.inert_measure_years)
        base_missing = missing_supported(base) or set()
        event_inert = pairs(event.inert_measure_years)
        for measure_key, year in sorted(
            event_inert | (missing_supported(event) or set())
        ):
            if (measure_key, year) in base_inert:
                why = "inert in the base"
            elif (measure_key, year) in base_missing:
                why = "missing in the base"
            else:
                continue
            known_gaps.append(
                {
                    "event": name,
                    "measure_key": measure_key,
                    "year": year,
                    "candidate": "inert"
                    if (measure_key, year) in event_inert
                    else "missing",
                    "why": why,
                    "base_staging_manifest_sha256": base.staging_manifest_sha256,
                }
            )
    gaps_at = {
        (gap["event"], gap["measure_key"], gap["year"]): gap for gap in known_gaps
    }
    known = set(gaps_at)
    listed_inert = set(inert)
    candidate_inert = {where for where in listed_inert if where not in known}
    regressions: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []

    def item(kind: str, row: Any = None, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {"kind": kind}
        if row is not None:
            record.update(
                event=row.event,
                measure_key=row.measure_key,
                year=row.year,
                level=row.level,
                key=row.key,
                flags=sorted(row.flags),
                base_gbp=row.base_gbp,
                head_gbp=row.head_gbp,
            )
        record.update(fields)
        return record

    for event, measure_key, year in sorted(candidate_inert):
        regressions.append(
            item(
                "lost_response",
                event=event,
                measure_key=measure_key,
                year=year,
                why="inert in the candidate",
            )
        )
    for name in incomplete_events:
        event = corpus.events[name]
        missing = missing_supported(event)
        if missing is None:
            regressions.append(
                item(
                    "incomplete",
                    event=name,
                    why="the supported grid is incomplete and the receipt does "
                    "not list its missing measure-years",
                )
            )
            continue
        gaps = pairs(event.inert_measure_years) | missing
        unknown = sorted(gap for gap in gaps if (name, *gap) not in known)
        if not gaps or unknown:
            regressions.append(
                item(
                    "incomplete",
                    event=name,
                    why="the supported grid is incomplete and not every inert "
                    "or missing measure-year in it is a known gap",
                    measure_years=[list(gap) for gap in unknown],
                )
            )
    if receipt.integrity.status == "incomplete" and not incomplete_events:
        regressions.append(
            item("incomplete", why="integrity is incomplete with no incomplete event")
        )
    gap_rows: list[dict[str, Any]] = []
    for row in rows:
        flags = set(row.flags)
        where = (row.event, row.measure_key, row.year)
        gap = gaps_at.get(where)
        lost = False
        if gap is not None and "coverage" in flags and _is_the_gap(row, gap):
            # Scorecard's own expression of a mixed known gap: one side has no
            # artifact and the other an inert one (identical worlds, £0).
            flags.discard("coverage")
        if flags & BLOCKING_REPLAY_FLAGS:
            regressions.append(item("mapping", row))
            lost = True
        if "coverage" in flags and row.base_gbp is not None and row.head_gbp is None:
            regressions.append(item("lost_result", row))
            lost = True
        if (
            gap is not None
            and "coverage" in flags
            and row.base_gbp is None
            and row.head_gbp not in (None, 0)
        ):
            # The candidate's record lists the measure-year as inert or
            # missing, so it cannot also hold a value for it.
            regressions.append(
                item(
                    "contradiction",
                    row,
                    why="a candidate value for a measure-year its record lists "
                    "as a gap",
                )
            )
            lost = True
        zero_total = (
            row.level == "measure_year"
            and row.head_gbp == 0
            and row.base_gbp is not None
            and abs(row.base_gbp)
            >= max(REPLAY_ABSOLUTE_BOUND_GBP, REPLAY_RELATIVE_BOUND * abs(row.base_gbp))
        )
        if zero_total and where in known:
            # A base whose own record lists the measure-year as a gap cannot
            # also hold a material value for it: the receipt contradicts
            # itself, so the gap does not excuse the loss.
            regressions.append(
                item(
                    "lost_response",
                    row,
                    why="£0 against a material base value, though the base's "
                    "record lists the measure-year as a gap",
                )
            )
            lost = True
        elif where in listed_inert and zero_total:
            # The candidate's own inert list decides: a lost response above.
            lost = True
        elif zero_total:
            regressions.append(item("lost_response", row, why="£0 against the base"))
            lost = True
        if where in listed_inert or (
            gap is not None
            and gap["candidate"] == "missing"
            and gap["why"] == "inert in the base"
        ):
            # The candidate's inert list decides its inertness (a lost response
            # above, or a known gap). Where the candidate is missing and the
            # base inert, the base-only inertness is the known gap itself. The
            # row's other flags are judged as usual.
            flags = flags - {"inertness"}
        if gap is not None and flags != set(row.flags):
            # A row the known gap accounts for, in whole or in part.
            gap_rows.append(item("known_gap_row", row))
        if not lost and flags & REVIEW_REPLAY_FLAGS:
            if "coverage" in flags and row.base_gbp is None:
                kind = (
                    "coverage_gain"
                    if row.head_gbp is not None
                    else "coverage_without_values"
                )
            elif flags == {"inertness"}:
                kind = "base_only_inertness"
            else:
                kind = "flagged_move"
            review_items.append(item(kind, row))
    details.update(
        {
            "policy": REPLAY_POLICY_ID,
            "policy_sha256": replay_policy_sha256(),
            "known_gaps": known_gaps,
            "known_gap_rows": gap_rows,
            "regressions": regressions,
            "review_items": review_items,
        }
    )

    def tally(records: Sequence[dict[str, Any]]) -> str:
        kinds: dict[str, int] = {}
        for record in records:
            kinds[record["kind"]] = kinds.get(record["kind"], 0) + 1
        return ", ".join(f"{kind} {n}" for kind, n in sorted(kinds.items()))

    if regressions:
        return GateResult(
            gate_id="replay",
            status="fail",
            summary="Replay regressions: " + tally(regressions),
            details=details,
        )
    if review_items:
        return GateResult(
            gate_id="replay",
            status="needs_review",
            summary="Replay moves need review: " + tally(review_items),
            details=details,
        )
    if receipt.diff is None:
        return GateResult(
            gate_id="replay",
            status="needs_review",
            summary="Replay completed but reported no diff against a certified variant.",
            details=details,
        )
    return GateResult(
        gate_id="replay",
        status="pass",
        summary=f"Replayed {len(corpus.events)} event(s) with no flags against {receipt.diff.base_variant_id}.",
        details=details,
    )


def replay_gate_while_pending(status: Optional[ReplayStatus]) -> GateResult:
    """Gate result for a replay that has not reached a terminal status."""

    state = status.status if status is not None else "not yet queued"
    return GateResult(
        gate_id="replay",
        status="unavailable",
        summary=f"Replay is {state}; the candidate stays incomplete until it finishes.",
        details={"status": state},
    )


def mirror_from_document(model: type[_Mirror], document: Mapping[str, Any]) -> Any:
    """Parse a scorecard document into its mirror model."""

    return model.model_validate(dict(document))
