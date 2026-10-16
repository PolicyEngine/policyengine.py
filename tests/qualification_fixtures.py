"""Shared builders for qualification tests (no network, no credentials)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from policyengine.provenance.qualification import (
    REQUIRED_GATES,
    CandidatePair,
    GateResult,
    IssuedBy,
    PinnedData,
    PinnedWheel,
    QualificationHarness,
    QualificationReceipt,
    qualification_verdict,
)

FIXTURES = Path(__file__).parent / "fixtures" / "uk_replay"
VENDORED_SCHEMAS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "policyengine"
    / "data"
    / "schemas"
    / "vendor"
    / "policyengine-scorecard"
)


def sha(char: str) -> str:
    return char * 64


def make_pair(
    model="2.126.8", data="1.58.0", core="3.33.0", dataset_sha=None
) -> CandidatePair:
    return CandidatePair(
        country_id="uk",
        model=PinnedWheel(name="policyengine-uk", version=model, wheel_sha256=sha("a")),
        core=PinnedWheel(name="policyengine-core", version=core, wheel_sha256=sha("b")),
        data=PinnedData(
            data_package="policyengine-uk-data",
            release_version=data,
            build_id=f"policyengine-uk-data-{data}",
            repo_id="policyengine/policyengine-uk-data-private",
            repo_type="model",
            release_manifest_path=f"releases/{data}/release_manifest.json",
            release_manifest_revision="f" * 40,
            release_manifest_sha256=sha("c"),
            dataset="enhanced_frs_2024_25",
            dataset_path="enhanced_frs_2024_25.h5",
            dataset_revision=data,
            dataset_sha256=dataset_sha or sha("d"),
            size_bytes=128369110,
        ),
    )


HARNESS = QualificationHarness(
    policyengine_version="6.2.6",
    git_commit="e" * 40,
    packaged_bundle_manifest_sha256=sha("9"),
)
ISSUED = IssuedBy(
    repository="PolicyEngine/policyengine.py",
    workflow_run_id=1,
    run_url="https://github.com/PolicyEngine/policyengine.py/actions/runs/1",
)


def gates(status="pass", **overrides) -> list[GateResult]:
    return [
        GateResult(
            gate_id=gate_id, status=overrides.get(gate_id, status), summary=gate_id
        )
        for gate_id in REQUIRED_GATES
    ]


def make_receipt(
    pair=None, gate_results=None, completed_at="2026-10-15T09:00:00Z", review=None
) -> QualificationReceipt:
    pair = pair or make_pair()
    gate_results = gate_results if gate_results is not None else gates()
    return QualificationReceipt(
        schema_version=1,
        receipt_type="policyengine.candidate_qualification_receipt",
        pair_id=pair.pair_id,
        pair=pair,
        harness=HARNESS,
        gates=gate_results,
        verdict=qualification_verdict(gate_results),
        review=review,
        issued_by=ISSUED,
        completed_at=completed_at,
    )


def jq(expression: str, data) -> str:
    """Apply ``expression`` to ``data`` with the real jq, printing strings
    raw as gh's ``--jq`` does, so fakes of gh evaluate the code's own jq
    rather than guess at it (round 6 of #635: a fake that picked fields by
    name let a wrong source path pass). GitHub's ubuntu runners ship jq; a
    machine without it fails these tests rather than skipping them."""

    binary = shutil.which("jq")
    assert binary, "jq is required to evaluate the code's jq expressions"
    return subprocess.run(
        [binary, "-r", expression],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def golden(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
