"""Qualify a UK model/data candidate before it can be promoted.

Run by ``.github/workflows/certify-uk-release.yaml``; every step also runs
locally. Network access: PyPI, Hugging Face (``HUGGING_FACE_TOKEN``) and, for
the replay and promotion steps, GitHub (``GH_TOKEN``).

Each attempt lives in one ledger directory, ``<ledger>/uk/<pair_id>/attempts/
<base commit[:12]>/``, which every step after ``resolve`` reads and writes::

    python scripts/check_uk_candidate.py resolve --out candidate.json \\
        [--model-version 2.126.8] [--data-version 1.58.0] [--ledger ledger/] [--force]
    python scripts/check_uk_candidate.py prepare --candidate candidate.json --skip-snapshots
    python scripts/check_uk_candidate.py stage --candidate candidate.json --ledger ledger/
    python scripts/check_uk_candidate.py gates --attempt <attempt dir>
    python scripts/check_uk_candidate.py request-replay --attempt <attempt dir> [--dispatch]
    python scripts/check_uk_candidate.py poll-replay --attempt <attempt dir> [--wait-minutes 340]
    python scripts/check_uk_candidate.py finalize --attempt <attempt dir> --ledger ledger/
    python scripts/check_uk_candidate.py waiting --ledger ledger/
    python scripts/check_uk_candidate.py promote --ledger ledger/ [--apply]
    python scripts/check_uk_candidate.py accept --ledger ledger/ --pair-id ... \\
        --receipt-sha256 ... --explanation "..." [--reviewer login]

Steps that the workflow branches on also write ``key=value`` lines to
``$GITHUB_OUTPUT`` when it is set.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")

import requests  # noqa: E402

from policyengine.provenance.qualification import (  # noqa: E402
    CandidatePair,
    IssuedBy,
    QualificationHarness,
    QualificationReceipt,
    ReplayQualificationRequest,
)
from policyengine.provenance.qualification_ledger import (  # noqa: E402
    LEDGER_BRANCH,
    LEDGER_REPOSITORY,
    attempt_directory,
    latest_receipts,
    pair_directory,
    read_json,
    write_json,
)
from policyengine.provenance.uk_qualification import (  # noqa: E402
    ResolvedCandidate,
    WheelFile,
    accept_review,
    attempt_is_waiting_for_replay,
    build_replay_request,
    candidate_action,
    candidate_branch,
    candidate_pr_body,
    expected_release_bundle,
    finalize_attempt,
    packaged_manifest_sha256,
    plan_promotion,
    prepare_candidate_commit,
    previous_certificate,
    read_replay,
    replay_dispatch_payload,
    resolve_candidate,
    stage_attempt,
    write_gate_results,
)

BUNDLE_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
CONFIG_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "qualification" / "uk.json"
TIMEOUT = 60


def utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text())


def hf_headers() -> dict[str, str]:
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def pypi_project(path: str) -> dict[str, Any]:
    response = requests.get(f"https://pypi.org/pypi/{path}/json", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def hf_revision_sha(repo_id: str, revision: str) -> str:
    response = requests.get(
        f"https://huggingface.co/api/models/{repo_id}/revision/{revision}",
        headers=hf_headers(),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return str(response.json()["sha"])


def hf_tags(repo_id: str) -> list[str]:
    response = requests.get(
        f"https://huggingface.co/api/models/{repo_id}/refs",
        headers=hf_headers(),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return [tag["name"] for tag in response.json().get("tags", [])]


def hf_file(repo_id: str, revision: str, path: str) -> bytes:
    response = requests.get(
        f"https://huggingface.co/{repo_id}/resolve/{revision}/{path}",
        headers=hf_headers(),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.content


def scorecard_file(repository: str):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.raw+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def fetch(ref: str, path: str) -> Optional[bytes]:
        response = requests.get(
            f"https://api.github.com/repos/{repository}/contents/{path}",
            params={"ref": ref},
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.content

    return fetch


def issued_by() -> IssuedBy:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY", LEDGER_REPOSITORY)
    run_id = int(os.environ.get("GITHUB_RUN_ID", "1"))
    return IssuedBy(
        repository=repository,
        workflow_run_id=run_id,
        run_attempt=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
        run_url=f"{server}/{repository}/actions/runs/{run_id}",
    )


def git(*args: str, cwd: Path = REPO_ROOT) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def set_output(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")


def resolved_from(payload: dict[str, Any]) -> ResolvedCandidate:
    return ResolvedCandidate(
        pair=CandidatePair.model_validate(payload["pair"]),
        model_wheel=WheelFile(**payload["model_wheel"]),
        core_wheel=WheelFile(**payload["core_wheel"]),
        manifest_uri=payload["manifest_uri"],
        model_requires_core=payload["model_requires_core"],
    )


def ledger_url(pair_id: str) -> str:
    return f"https://github.com/{LEDGER_REPOSITORY}/tree/{LEDGER_BRANCH}/uk/{pair_id}"


# --- Commands -----------------------------------------------------------------


def cmd_resolve(args: argparse.Namespace) -> int:
    bundle = json.loads(BUNDLE_PATH.read_text())
    resolved = resolve_candidate(
        current_core=bundle["packages"]["policyengine-core"]["version"],
        pypi_project=pypi_project,
        hf_revision_sha=hf_revision_sha,
        hf_tags=hf_tags,
        hf_file=hf_file,
        model_version=args.model_version or None,
        data_version=args.data_version or None,
    )
    base_commit = git("rev-parse", "HEAD")
    action, reason = candidate_action(
        resolved.pair,
        bundle,
        Path(args.ledger) if args.ledger else None,
        base_commit=base_commit,
        force=args.force,
    )
    payload = {
        "pair": resolved.pair.canonical_payload(),
        "pair_id": resolved.pair.pair_id,
        "model_wheel": resolved.model_wheel.__dict__,
        "core_wheel": resolved.core_wheel.__dict__,
        "manifest_uri": resolved.manifest_uri,
        "model_requires_core": resolved.model_requires_core,
        "base_commit": base_commit,
        "attempt_key": base_commit[:12],
        "branch": candidate_branch(resolved.pair),
        "action": action,
        "reason": reason,
        "previous_certificate": previous_certificate(bundle).canonical_payload(),
    }
    write_json(Path(args.out), payload)
    print(
        f"{action}: {reason} (pair {resolved.pair.pair_id[:12]}, {resolved.pair.order_key})"
    )
    set_output(
        action=action,
        pair_id=resolved.pair.pair_id,
        branch=candidate_branch(resolved.pair),
        base_commit=base_commit,
        attempt_key=base_commit[:12],
    )
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.candidate).read_text())
    prepared = prepare_candidate_commit(
        REPO_ROOT,
        resolved_from(payload),
        python=sys.executable,
        refresh_snapshots=not args.skip_snapshots,
    )
    write_json(Path(args.out), prepared)
    print(json.dumps(prepared, indent=2))
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    from importlib.metadata import version

    payload = json.loads(Path(args.candidate).read_text())
    harness = QualificationHarness(
        policyengine_version=version("policyengine"),
        git_commit=git("rev-parse", "HEAD"),
        packaged_bundle_manifest_sha256=packaged_manifest_sha256(REPO_ROOT),
    )
    attempt = attempt_directory(
        Path(args.ledger), "uk", payload["pair_id"], payload["attempt_key"]
    )
    stage_attempt(attempt, payload, harness)
    print(f"staged {attempt} at {harness.git_commit}")
    set_output(attempt=str(attempt), candidate_commit=harness.git_commit)
    return 0


def _attempt(
    args: argparse.Namespace,
) -> tuple[Path, dict[str, Any], QualificationHarness]:
    attempt = Path(args.attempt)
    payload = read_json(attempt / "candidate.json")
    harness = QualificationHarness.model_validate(read_json(attempt / "harness.json"))
    return attempt, payload, harness


def cmd_gates(args: argparse.Namespace) -> int:
    from policyengine.provenance import uk_candidate

    attempt, payload, harness = _attempt(args)
    if git("rev-parse", "HEAD") != harness.git_commit:
        raise SystemExit(
            "Gates must run on the candidate commit named in harness.json."
        )
    ledger_root = attempt.parents[3]
    results, evidence = uk_candidate.run_candidate_gates(
        resolved_from(payload),
        harness,
        config=config(),
        work_dir=Path(args.work_dir),
        previous_certificate=payload.get("previous_certificate"),
        ledger_root=ledger_root,
    )
    write_gate_results(attempt, results, evidence)
    for result in results:
        print(f"{result.gate_id:20s} {result.status:13s} {result.summary}")
    return 0


def cmd_request_replay(args: argparse.Namespace) -> int:
    attempt, payload, harness = _attempt(args)
    request = build_replay_request(
        CandidatePair.model_validate(payload["pair"]),
        harness,
        release_bundle=expected_release_bundle(sys.executable, cwd=REPO_ROOT),
        issued_by=issued_by(),
        attempt=args.replay_attempt,
        compare_to=config()["replay"]["compare_to"],
    )
    print(f"request_id {request.request_id}")
    if args.dispatch:
        settings = config()["replay"]
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{settings['repository']}/dispatches",
                "--method",
                "POST",
                "--input",
                "-",
            ],
            input=json.dumps(
                replay_dispatch_payload(request, event_type=settings["event_type"])
            ),
            text=True,
            check=True,
        )
        print(f"dispatched {settings['event_type']} to {settings['repository']}")
    # Recorded only once sent: an attempt with a request waits for its replay.
    write_json(attempt / "replay" / "request.json", request.document())
    set_output(request_id=request.request_id)
    return 0


def cmd_poll_replay(args: argparse.Namespace) -> int:
    attempt = Path(args.attempt)
    settings = config()["replay"]
    request = ReplayQualificationRequest.model_validate(
        read_json(attempt / "replay" / "request.json")
    )
    fetch = scorecard_file(settings["repository"])
    deadline = time.monotonic() + 60 * args.wait_minutes
    while True:
        gate, status, receipt = read_replay(
            request, fetch=fetch, state_ref=settings["state_ref"]
        )
        if (status is not None and status.terminal) or time.monotonic() >= deadline:
            break
        time.sleep(args.interval_seconds)
    write_json(attempt / "replay" / "replay.result.json", gate.canonical_payload())
    if status is not None:
        write_json(attempt / "replay" / "status.json", status.document())
    if receipt is not None:
        write_json(attempt / "replay" / "receipt.json", receipt.document())
    terminal = status is not None and status.terminal
    print(f"replay {gate.status}: {gate.summary}")
    set_output(replay_terminal="true" if terminal else "false")
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    attempt = Path(args.attempt)
    receipt = finalize_attempt(
        attempt, Path(args.ledger), issued_by=issued_by(), completed_at=utc_now()
    )
    payload = read_json(attempt / "candidate.json")
    body = candidate_pr_body(
        receipt, receipt.pair, ledger_url=ledger_url(receipt.pair_id)
    )
    if args.pr_body:
        Path(args.pr_body).write_text(body)
    print(f"verdict {receipt.verdict}; receipt {receipt.receipt_sha256}")
    set_output(
        verdict=receipt.verdict,
        receipt_sha256=receipt.receipt_sha256,
        branch=payload["branch"],
    )
    return 0


def cmd_waiting(args: argparse.Namespace) -> int:
    base = Path(args.ledger) / "uk"
    waiting = sorted(
        str(path)
        for path in base.glob("*/attempts/*")
        if path.is_dir() and attempt_is_waiting_for_replay(path)
    )
    for path in waiting:
        print(path)
    set_output(waiting=json.dumps(waiting))
    return 0


def _open_candidate_branches() -> list[str]:
    listing = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            LEDGER_REPOSITORY,
            "--state",
            "open",
            "--search",
            "head:candidate/uk/",
            "--json",
            "headRefName",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [item["headRefName"] for item in json.loads(listing)]


def cmd_promote(args: argparse.Namespace) -> int:
    bundle = json.loads(BUNDLE_PATH.read_text())
    receipts = latest_receipts(Path(args.ledger))
    branches = _open_candidate_branches() if args.apply else []
    plan = plan_promotion(receipts, bundle, branches)
    print(f"promotion: {plan.reason}")
    if plan.target is not None:
        print(f"target {plan.ready_branch} (pair {plan.target.pair_id[:12]})")
    for branch in plan.close_branches:
        print(f"superseded {branch}")
    if not args.apply:
        return 0
    for branch in plan.close_branches:
        subprocess.run(
            [
                "gh",
                "pr",
                "close",
                branch,
                "--repo",
                LEDGER_REPOSITORY,
                "--comment",
                f"Superseded: {plan.reason}. The ledger keeps this candidate's evidence.",
            ],
            check=False,
        )
    if plan.ready_branch is not None and plan.ready_branch in branches:
        subprocess.run(
            ["gh", "pr", "ready", plan.ready_branch, "--repo", LEDGER_REPOSITORY],
            check=False,
        )
        if config()["promotion"]["automatic"]:
            subprocess.run(
                [
                    "gh",
                    "pr",
                    "merge",
                    plan.ready_branch,
                    "--repo",
                    LEDGER_REPOSITORY,
                    "--auto",
                    "--squash",
                ],
                check=False,
            )
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    path = (
        pair_directory(Path(args.ledger), "uk", args.pair_id)
        / "qualification_receipt.json"
    )
    receipt = QualificationReceipt.model_validate(read_json(path))
    reviewed = accept_review(
        receipt,
        reviewer=args.reviewer or os.environ.get("GITHUB_ACTOR", ""),
        accepted_receipt_sha256=args.receipt_sha256,
        explanation=args.explanation,
        accepted_at=utc_now(),
    )
    write_json(path, reviewed.canonical_payload())
    write_json(
        path.parent / "reviews" / f"{reviewed.receipt_sha256}.json",
        reviewed.canonical_payload(),
    )
    print(
        f"accepted {args.pair_id[:12]} by {reviewed.review.reviewer}; promotable={reviewed.promotable}"
    )
    return 0


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    resolve = commands.add_parser("resolve")
    resolve.add_argument("--model-version")
    resolve.add_argument("--data-version")
    resolve.add_argument("--ledger")
    resolve.add_argument("--force", action="store_true")
    resolve.add_argument("--out", required=True)
    resolve.set_defaults(func=cmd_resolve)

    prepare = commands.add_parser("prepare")
    prepare.add_argument("--candidate", required=True)
    prepare.add_argument("--out", default="prepared.json")
    prepare.add_argument("--skip-snapshots", action="store_true")
    prepare.set_defaults(func=cmd_prepare)

    stage = commands.add_parser("stage")
    stage.add_argument("--candidate", required=True)
    stage.add_argument("--ledger", required=True)
    stage.set_defaults(func=cmd_stage)

    gates = commands.add_parser("gates")
    gates.add_argument("--attempt", required=True)
    gates.add_argument("--work-dir", default="qualification-work")
    gates.set_defaults(func=cmd_gates)

    request = commands.add_parser("request-replay")
    request.add_argument("--attempt", required=True)
    request.add_argument("--replay-attempt", type=int, default=1)
    request.add_argument("--dispatch", action="store_true")
    request.set_defaults(func=cmd_request_replay)

    poll = commands.add_parser("poll-replay")
    poll.add_argument("--attempt", required=True)
    poll.add_argument("--wait-minutes", type=float, default=0)
    poll.add_argument("--interval-seconds", type=float, default=300)
    poll.set_defaults(func=cmd_poll_replay)

    finalize = commands.add_parser("finalize")
    finalize.add_argument("--attempt", required=True)
    finalize.add_argument("--ledger", required=True)
    finalize.add_argument("--pr-body")
    finalize.set_defaults(func=cmd_finalize)

    waiting = commands.add_parser("waiting")
    waiting.add_argument("--ledger", required=True)
    waiting.set_defaults(func=cmd_waiting)

    promote = commands.add_parser("promote")
    promote.add_argument("--ledger", required=True)
    promote.add_argument("--apply", action="store_true")
    promote.set_defaults(func=cmd_promote)

    accept = commands.add_parser("accept")
    accept.add_argument("--ledger", required=True)
    accept.add_argument("--pair-id", required=True)
    accept.add_argument("--receipt-sha256", required=True)
    accept.add_argument("--explanation", required=True)
    accept.add_argument("--reviewer")
    accept.set_defaults(func=cmd_accept)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
