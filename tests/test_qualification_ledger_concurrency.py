"""Concurrent publishes never yield a receipt that mixes two attempts.

Round-6 review of #574: two attempts of one pair both write the pair's
published files. When the older attempt's replay finished after the newer
attempt had published, the publish script's cherry-pick merged the two
indented JSON receipts line by line into a valid-looking receipt: the newer
attempt's harness with the older attempt's passing replay. Promotion then
readied a commit whose replay never ran.

Invariants:

- after any interleaving of two publishes, the pair's published receipt is
  the current receipt of its latest-staged attempt, and every attempt's
  evidence is on the branch;
- without a rederive hook the publish fails rather than merging receipts;
- a published receipt that is not its latest attempt's own is refused by
  every reader (listing, promotion, acceptance, remote fetch).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from policyengine.provenance.canonical import canonical_sha256
from policyengine.provenance.qualification import (
    QualificationReceipt,
    ReplayReceipt,
    ReplayStatus,
    evaluate_replay_receipt,
)
from policyengine.provenance.qualification_ledger import (
    LedgerInconsistency,
    fetch_ledger_receipt,
    latest_receipts,
    published_receipt,
    read_json,
    rederive_publication,
    write_json,
)
from policyengine.provenance.uk_qualification import (
    accept_review,
    build_replay_request,
    candidate_branch,
    finalize_attempt,
    plan_promotion,
    previous_certificate,
    stage_attempt,
    write_gate_results,
)
from tests.qualification_fixtures import HARNESS, ISSUED, gates, golden, make_pair

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "qualification-ledger.sh"
CLI = ROOT / "scripts" / "check_uk_candidate.py"
BASE = json.loads(
    (ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json").read_text()
)
PAIR = make_pair(
    model="2.200.0", data=BASE["data_releases"]["uk"]["data_package"]["version"]
)
NEWER_HARNESS = HARNESS.model_copy(
    update={"git_commit": "b" * 40, "packaged_bundle_manifest_sha256": "8" * 64}
)
REDERIVE = f"{sys.executable} {CLI} rederive-ledger"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _run(*args, cwd, check=True, rederive=None):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.org",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.org",
        "GIT_TERMINAL_PROMPT": "0",
        "LEDGER_RETRY_DELAY": "0",
        "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1",
        "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT),
    }
    env.pop("LEDGER_REDERIVE", None)
    if rederive is not None:
        env["LEDGER_REDERIVE"] = rederive
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _request(harness):
    return build_replay_request(
        PAIR,
        harness,
        release_bundle=golden("qualification_request_golden")["candidate"][
            "expected_release_bundle"
        ],
        issued_by=ISSUED,
    )


def _complete_replay(attempt: Path, request) -> None:
    """Write a passing replay for ``request`` into ``attempt``."""

    document = golden("replay_receipt_golden")
    document["request_id"] = request.request_id
    execution = document["execution"]
    execution["packaged_bundle_manifest_sha256"] = (
        request.candidate.policyengine.packaged_bundle_manifest_sha256
    )
    execution["dataset_sha256"] = PAIR.data.dataset_sha256
    execution["release_bundle"] = request.candidate.expected_release_bundle
    execution["packages"]["policyengine"]["version"] = (
        request.candidate.policyengine.version
    )
    for key, package in (
        ("policyengine-uk", PAIR.model),
        ("policyengine-core", PAIR.core),
    ):
        execution["packages"][key]["version"] = package.version
        execution["packages"][key]["wheel_sha256"] = package.wheel_sha256
    document["diff"]["flag_counts"] = {
        key: 0 for key in document["diff"]["flag_counts"]
    }
    document["diff"]["flagged_rows"] = []
    document["receipt_sha256"] = canonical_sha256(
        {key: value for key, value in document.items() if key != "receipt_sha256"}
    )
    receipt = ReplayReceipt.from_document(document)
    status = ReplayStatus.model_validate(
        {
            "schema": "policyengine.uk-replay-status/v1",
            "request_id": request.request_id,
            "status": "complete",
            "receipt_sha256": receipt.receipt_sha256,
            "receipt_commit": "c" * 40,
            "history": [
                {
                    "status": "complete",
                    "at": "2026-10-15T10:00:00Z",
                    "run_url": "https://github.com/PolicyEngine/policyengine-scorecard/actions/runs/7",
                }
            ],
        }
    )
    gate = evaluate_replay_receipt(request, status, receipt)
    assert gate.status == "pass", gate
    write_json(attempt / "replay" / "request.json", request.document())
    write_json(attempt / "replay" / "status.json", status.document())
    write_json(attempt / "replay" / "receipt.json", receipt.document())
    write_json(attempt / "replay" / "replay.result.json", gate.canonical_payload())


def _stage(attempt: Path, harness, owner: str, staged_at: str) -> None:
    payload = {
        "pair": PAIR.canonical_payload(),
        "previous_certificate": previous_certificate(BASE).canonical_payload(),
        "branch": candidate_branch(PAIR),
    }
    stage_attempt(attempt, payload, harness, owner_run_id=owner, staged_at=staged_at)
    write_gate_results(attempt, [g for g in gates() if g.gate_id != "replay"], {})


def _origin(root: Path) -> Path:
    origin = root / "origin.git"
    _run("git", "init", "--quiet", "--bare", "-b", "main", str(origin), cwd=root)
    seed = root / "seed"
    _run("git", "clone", "--quiet", str(origin), str(seed), cwd=root)
    (seed / "seed").write_text("seed")
    _run("git", "add", "seed", cwd=seed)
    _run("git", "commit", "--quiet", "-m", "seed", cwd=seed)
    _run("git", "push", "--quiet", "origin", "HEAD:refs/heads/main", cwd=seed)
    return origin


def _ledger_clone(root: Path, origin: Path, name: str) -> Path:
    clone = root / name
    _run(
        "git", "clone", "--quiet", "--branch", "main", str(origin), str(clone), cwd=root
    )
    _run("bash", str(SCRIPT), "checkout", "ledger", cwd=clone)
    return clone


def _published(origin: Path, path: str) -> dict:
    shown = _run(
        "git", "show", f"uk-qualification-ledger:uk/{PAIR.pair_id}/{path}", cwd=origin
    )
    return json.loads(shown.stdout)


def _race(tmp_path: Path, *, older_publishes_last: bool, rederive):
    """Attempt A (older) and B (newer) of one pair publish concurrently.

    A is staged and published first. Each run then works in its own clone:
    B finalizes incomplete; A's replay completes and it finalizes qualified.
    """

    origin = _origin(tmp_path)
    seed = _ledger_clone(tmp_path, origin, "seed-ledger")
    pair_dir = seed / "ledger" / "uk" / PAIR.pair_id
    _stage(pair_dir / "attempts" / "a", HARNESS, "1", "2026-10-15T09:00:00Z")
    finalize_attempt(
        pair_dir / "attempts" / "a",
        seed / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-15T09:30:00Z",
    )
    _run("bash", str(SCRIPT), "publish", "ledger", "A incomplete", cwd=seed)

    clone_a = _ledger_clone(tmp_path, origin, "a")
    clone_b = _ledger_clone(tmp_path, origin, "b")
    attempt_a = clone_a / "ledger" / "uk" / PAIR.pair_id / "attempts" / "a"
    attempt_b = clone_b / "ledger" / "uk" / PAIR.pair_id / "attempts" / "b"
    _stage(attempt_b, NEWER_HARNESS, "2", "2026-10-15T10:01:00Z")
    receipt_b = finalize_attempt(
        attempt_b,
        clone_b / "ledger",
        issued_by=ISSUED.model_copy(update={"workflow_run_id": 2}),
        completed_at="2026-10-15T10:02:00Z",
    )
    assert receipt_b.verdict == "incomplete"
    _complete_replay(attempt_a, _request(HARNESS))
    receipt_a = finalize_attempt(
        attempt_a,
        clone_a / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-15T10:02:00Z",
    )
    assert receipt_a.verdict == "qualified"

    order = [(clone_b, "B"), (clone_a, "A")]
    if not older_publishes_last:
        order.reverse()
    first, second = order
    _run("bash", str(SCRIPT), "publish", "ledger", f"{first[1]}", cwd=first[0])
    result = _run(
        "bash",
        str(SCRIPT),
        "publish",
        "ledger",
        f"{second[1]}",
        cwd=second[0],
        check=False,
        rederive=rederive,
    )
    return origin, result, receipt_a, receipt_b


@pytest.mark.parametrize("older_publishes_last", [True, False])
def test_concurrent_attempts_publish_the_latest_attempts_receipt(
    tmp_path, older_publishes_last
):
    origin, result, receipt_a, receipt_b = _race(
        tmp_path, older_publishes_last=older_publishes_last, rederive=REDERIVE
    )
    assert result.returncode == 0, result.stdout
    published = QualificationReceipt.model_validate(
        _published(origin, "qualification_receipt.json")
    )
    # B was staged last, so B's receipt is published, whichever came last.
    assert published.unreviewed_sha256 == receipt_b.unreviewed_sha256
    assert published.harness.git_commit == "b" * 40
    assert _published(origin, "latest_attempt.json")["attempt_key"] == "b"
    files = _run(
        "git", "ls-tree", "-r", "--name-only", "uk-qualification-ledger", cwd=origin
    ).stdout.split()
    for key in ("a", "b"):
        assert f"uk/{PAIR.pair_id}/attempts/{key}/qualification_receipt.json" in files
    # Nothing qualified is published for B, so B's commit is never readied.
    plan = plan_promotion([published], BASE, {candidate_branch(PAIR): "b" * 40})
    assert plan.ready_commit is None


def test_without_a_rederive_hook_the_publish_fails_rather_than_merging(tmp_path):
    origin, result, _, receipt_b = _race(
        tmp_path, older_publishes_last=True, rederive=None
    )
    assert result.returncode != 0
    assert "conflicts with a concurrent publish" in result.stdout
    published = QualificationReceipt.model_validate(
        _published(origin, "qualification_receipt.json")
    )
    assert published.unreviewed_sha256 == receipt_b.unreviewed_sha256


def _ledger_with_attempts(root: Path):
    """A ledger pair with attempt A qualified (sequence 1) and B incomplete (2)."""

    ledger = root / "ledger"
    pair_dir = ledger / "uk" / PAIR.pair_id
    _stage(pair_dir / "attempts" / "a", HARNESS, "1", "2026-10-15T09:00:00Z")
    _complete_replay(pair_dir / "attempts" / "a", _request(HARNESS))
    receipt_a = finalize_attempt(
        pair_dir / "attempts" / "a",
        ledger,
        issued_by=ISSUED,
        completed_at="2026-10-15T09:30:00Z",
    )
    _stage(pair_dir / "attempts" / "b", NEWER_HARNESS, "2", "2026-10-15T10:01:00Z")
    receipt_b = finalize_attempt(
        pair_dir / "attempts" / "b",
        ledger,
        issued_by=ISSUED,
        completed_at="2026-10-15T10:02:00Z",
    )
    return ledger, pair_dir, receipt_a, receipt_b


def _hybrid(receipt_a, receipt_b) -> dict:
    """The round-6 merge: B's harness and identity with A's replay and gates."""

    hybrid = receipt_a.canonical_payload()
    hybrid["harness"] = receipt_b.harness.canonical_payload()
    hybrid["issued_by"] = receipt_b.issued_by.canonical_payload()
    QualificationReceipt.model_validate(hybrid)  # it is a valid-looking receipt
    return hybrid


def test_a_merged_receipt_is_refused_by_every_reader(tmp_path, monkeypatch):
    ledger, pair_dir, receipt_a, receipt_b = _ledger_with_attempts(tmp_path)
    assert published_receipt(pair_dir).unreviewed_sha256 == receipt_b.unreviewed_sha256
    write_json(pair_dir / "qualification_receipt.json", _hybrid(receipt_a, receipt_b))

    with pytest.raises(LedgerInconsistency, match="not the receipt of attempt b"):
        published_receipt(pair_dir)
    problems: list[str] = []
    assert latest_receipts(ledger, problems=problems) == []
    assert problems and PAIR.pair_id in problems[0]

    import importlib.util

    spec = importlib.util.spec_from_file_location("ledger_concurrency_cli", CLI)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    with pytest.raises(LedgerInconsistency):
        cli.cmd_accept(
            SimpleNamespace(
                ledger=str(ledger),
                pair_id=PAIR.pair_id,
                reviewer="r",
                receipt_sha256="0" * 64,
                explanation="x",
            )
        )

    assert (
        rederive_publication(pair_dir).unreviewed_sha256 == receipt_b.unreviewed_sha256
    )
    assert published_receipt(pair_dir).unreviewed_sha256 == receipt_b.unreviewed_sha256


def test_an_older_attempts_real_receipt_is_not_the_published_one(tmp_path):
    """A stale but genuine receipt is refused too: the latest attempt decides."""

    _, pair_dir, receipt_a, _ = _ledger_with_attempts(tmp_path)
    write_json(pair_dir / "qualification_receipt.json", receipt_a.canonical_payload())
    with pytest.raises(LedgerInconsistency):
        published_receipt(pair_dir)


def test_rederivation_keeps_a_review_acceptance_of_exactly_that_receipt(tmp_path):
    from tests.qualification_fixtures import make_receipt

    ledger = tmp_path / "ledger"
    pair_dir = ledger / "uk" / PAIR.pair_id
    _stage(pair_dir / "attempts" / "a", HARNESS, "1", "2026-10-15T09:00:00Z")
    receipt = make_receipt(pair=PAIR, gate_results=gates(metrics_review="needs_review"))
    assert receipt.verdict == "needs_review" and not receipt.promotable
    write_json(
        pair_dir / "attempts" / "a" / "qualification_receipt.json",
        receipt.canonical_payload(),
    )
    accepted = accept_review(
        receipt,
        reviewer="reviewer",
        accepted_receipt_sha256=receipt.unreviewed_sha256,
        explanation="expected",
        accepted_at="2026-10-15T11:00:00Z",
    )
    write_json(
        pair_dir / "reviews" / f"{accepted.receipt_sha256}.json",
        accepted.canonical_payload(),
    )
    # A published file a merge left unreadable is rewritten, keeping the review.
    write_json(pair_dir / "qualification_receipt.json", {"not": "a receipt"})
    rederived = rederive_publication(pair_dir)
    assert rederived.review is not None and rederived.promotable
    assert published_receipt(pair_dir) == rederived
    assert read_json(pair_dir / "latest_attempt.json") == {
        "attempt_key": "a",
        "sequence": read_json(pair_dir / "attempts" / "a" / "staging.json")["sequence"],
    }


class _Response:
    def __init__(self, text=None):
        self.status_code = 404 if text is None else 200
        self.text = text or ""

    def raise_for_status(self):
        return None


def _remote(files: dict):
    def get(url, timeout):
        # The longest matching suffix wins: an attempt's receipt URL also ends
        # with the pair's receipt path suffix.
        matches = [suffix for suffix in files if url.endswith(suffix)]
        if not matches:
            return _Response(None)
        value = files[max(matches, key=len)]
        return _Response(None if value is None else json.dumps(value))

    return get


def test_a_fetched_receipt_must_be_its_named_attempts_receipt(tmp_path):
    _, _, receipt_a, receipt_b = _ledger_with_attempts(tmp_path)
    pointer = {"attempt_key": "b", "sequence": 2}
    good = _remote(
        {
            f"{PAIR.pair_id}/qualification_receipt.json": receipt_b.canonical_payload(),
            "/latest_attempt.json": pointer,
            "/attempts/b/qualification_receipt.json": receipt_b.canonical_payload(),
        }
    )
    assert (
        fetch_ledger_receipt("uk", PAIR.pair_id, get=good).unreviewed_sha256
        == receipt_b.unreviewed_sha256
    )
    merged = _remote(
        {
            f"{PAIR.pair_id}/qualification_receipt.json": _hybrid(receipt_a, receipt_b),
            "/latest_attempt.json": pointer,
            "/attempts/b/qualification_receipt.json": receipt_b.canonical_payload(),
        }
    )
    with pytest.raises(LedgerInconsistency):
        fetch_ledger_receipt("uk", PAIR.pair_id, get=merged)
    unnamed = _remote(
        {f"{PAIR.pair_id}/qualification_receipt.json": receipt_b.canonical_payload()}
    )
    with pytest.raises(LedgerInconsistency, match="names no attempt"):
        fetch_ledger_receipt("uk", PAIR.pair_id, get=unnamed)
    assert fetch_ledger_receipt("uk", PAIR.pair_id, get=_remote({})) is None
