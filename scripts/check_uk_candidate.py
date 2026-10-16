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
    python scripts/check_uk_candidate.py refresh-pr-checks --ledger ledger/
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
from functools import lru_cache
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
    ReplayQualificationRequest,
)
from policyengine.provenance.qualification_ledger import (  # noqa: E402
    LEDGER_BRANCH,
    LEDGER_REPOSITORY,
    LedgerInconsistency,
    attempt_directory,
    latest_receipts,
    pair_directory,
    published_receipt,
    read_json,
    rederive_publication,
    write_json,
)
from policyengine.provenance.uk_qualification import (  # noqa: E402
    ResolvedCandidate,
    WheelFile,
    accept_review,
    attempt_is_recoverable,
    attempt_is_waiting_for_replay,
    attempt_key,
    attempt_supersedes_receipt,
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
    requalification_target,
    resolve_candidate,
    stage_attempt,
    write_gate_results,
)

BUNDLE_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
CONFIG_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "qualification" / "uk.json"
TIMEOUT = 60
#: The pull request workflow that runs the test suite on a candidate.
CODE_CHANGES_WORKFLOW = ".github/workflows/pr_code_changes.yaml"


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
        core_version=args.core_version or None,
    )
    if args.pair_id and resolved.pair.pair_id != args.pair_id:
        # A requalification or recovery names one exact pair. Resolving any
        # other (a moved data tag, another core) must not qualify it instead.
        print(
            f"::error::resolved pair {resolved.pair.pair_id[:12]} "
            f"({resolved.pair.order_key}), not the requested {args.pair_id[:12]}"
        )
        set_output(action="mismatch", pair_id=resolved.pair.pair_id)
        return 1
    base_commit = git("rev-parse", "HEAD")
    resolved_at = utc_now()
    action, reason = candidate_action(
        resolved.pair,
        bundle,
        Path(args.ledger) if args.ledger else None,
        base_commit=base_commit,
        force=args.force,
        now=resolved_at,
        owner_is_failed=owner_run_failed,
    )
    key = attempt_key(
        resolved.pair,
        Path(args.ledger) if args.ledger else None,
        base_commit=base_commit,
        force=args.force,
        now=resolved_at,
        owner_is_failed=owner_run_failed,
    )
    payload = {
        "pair": resolved.pair.canonical_payload(),
        "pair_id": resolved.pair.pair_id,
        "model_wheel": resolved.model_wheel.__dict__,
        "core_wheel": resolved.core_wheel.__dict__,
        "manifest_uri": resolved.manifest_uri,
        "model_requires_core": resolved.model_requires_core,
        "base_commit": base_commit,
        "attempt_key": key,
        "branch": candidate_branch(resolved.pair),
        "action": action,
        "reason": reason,
        "force": bool(args.force),
        "previous_certificate": previous_certificate(bundle).canonical_payload(),
    }
    if action == "qualify" and args.ledger:
        pair_dir = pair_directory(Path(args.ledger), "uk", resolved.pair.pair_id)
        if (pair_dir / "qualification_receipt.json").exists():
            receipt = published_receipt(pair_dir)
            if receipt.verdict != "incomplete":
                # Forced work, or recovery of work already bound to this receipt.
                payload["supersedes_receipt_sha256"] = receipt.unreviewed_sha256
    write_json(Path(args.out), payload)
    print(
        f"{action}: {reason} (pair {resolved.pair.pair_id[:12]}, {resolved.pair.order_key})"
    )
    set_output(
        action=action,
        pair_id=resolved.pair.pair_id,
        branch=candidate_branch(resolved.pair),
        base_commit=base_commit,
        attempt_key=key,
    )
    return 0


def cmd_still_eligible(args: argparse.Namespace) -> int:
    """Whether a resolved candidate should still be qualified, against the
    ledger as it is now: run under the preparation lock, so two runs that
    resolved on different main commits never both stage an attempt."""

    payload = json.loads(Path(args.candidate).read_text())
    action, reason = candidate_action(
        CandidatePair.model_validate(payload["pair"]),
        json.loads(BUNDLE_PATH.read_text()),
        Path(args.ledger),
        base_commit=payload["base_commit"],
        force=bool(payload.get("force")),
        now=utc_now(),
        owner_is_failed=owner_run_failed,
    )
    print(f"{action}: {reason}")
    set_output(duplicate="false" if action == "qualify" else "true")
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
    stage_attempt(
        attempt,
        payload,
        harness,
        owner_run_id=os.environ.get("GITHUB_RUN_ID"),
        staged_at=utc_now(),
    )
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


@lru_cache(maxsize=256)
def owner_run_failed(run_id: str) -> bool:
    """Only a confirmed failed terminal run relinquishes its unexpired stage."""

    result = subprocess.run(
        [
            "gh",
            "run",
            "view",
            run_id,
            "--repo",
            LEDGER_REPOSITORY,
            "--json",
            "status,conclusion",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return False
    try:
        state = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return state.get("status") == "completed" and state.get("conclusion") in {
        "failure",
        "cancelled",
        "timed_out",
        "startup_failure",
        "action_required",
        "stale",
    }


def cmd_recoverable(args: argparse.Namespace) -> int:
    now = utc_now()
    for pair_dir in sorted((Path(args.ledger) / "uk").glob("*")):
        receipt = pair_dir / "qualification_receipt.json"
        stages = list((pair_dir / "attempts").glob("*/staging.json"))
        if not stages:
            continue
        attempt = max(stages, key=lambda path: int(read_json(path)["sequence"])).parent
        if receipt.exists():
            try:
                terminal = published_receipt(pair_dir)
            except LedgerInconsistency as error:
                print(f"::warning::{error}", file=sys.stderr)
                continue
            if terminal.verdict != "incomplete" and not attempt_supersedes_receipt(
                attempt, terminal
            ):
                continue
        if attempt_is_recoverable(attempt, now=now, owner_is_failed=owner_run_failed):
            print(json.dumps(read_json(attempt / "candidate.json")))
    return 0


def cmd_requalify(args: argparse.Namespace) -> int:
    """Print the promotion target's pair when it must be requalified: its
    qualification compared against an earlier certificate, or was built on
    an earlier main commit than the one checked out."""

    bundle = json.loads(BUNDLE_PATH.read_text())
    problems: list[str] = []
    receipts = latest_receipts(Path(args.ledger), problems=problems)
    for problem in problems:
        print(f"::warning::{problem}", file=sys.stderr)
    pair = requalification_target(
        receipts, bundle, Path(args.ledger), git("rev-parse", "HEAD")
    )
    if pair is not None:
        print(json.dumps({"pair": pair.canonical_payload(), "pair_id": pair.pair_id}))
    return 0


#: The most open candidate pull requests the listing reads; gh stops a search
#: at its limit (30 by default), so reaching this one is an error.
PULL_REQUEST_LIMIT = 1000


def _candidate_pull_requests() -> list[dict[str, Any]]:
    """Open candidate pull requests to main from this repository's own branches.

    ``head:candidate/uk/`` matches by prefix, and a fork's pull request can
    carry the same branch name, so only same-repository ones are candidates
    (a listing without the field counts as a fork's). Only pull requests to
    main are (round 6 of #635): GitHub allows one open pull request per head
    and base, so each candidate branch then has at most one. The search reads
    up to ``PULL_REQUEST_LIMIT`` pull requests, forks included, and refuses
    to go on if it reaches the limit, since one it did not read could be the
    target.
    """

    listing = json.loads(
        subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                LEDGER_REPOSITORY,
                "--state",
                "open",
                "--base",
                "main",
                "--search",
                "head:candidate/uk/",
                "--limit",
                str(PULL_REQUEST_LIMIT),
                "--json",
                "number,baseRefName,headRefName,headRefOid,isDraft,isCrossRepository",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    if len(listing) >= PULL_REQUEST_LIMIT:
        raise SystemExit(
            f"::error::{len(listing)} open pull requests match candidate/uk/; "
            "one beyond the listing could be the target"
        )
    return [
        item
        for item in listing
        if item.get("isCrossRepository") is False and item.get("baseRefName") == "main"
    ]


#: Whether a pull request's base was ever changed: GraphQL records a change
#: a person makes as a BaseRefChangedEvent and one GitHub makes when the base
#: branch is merged and deleted as an AutomaticBaseChangeSucceededEvent
#: (round 8 of #635). Its timeline's totalCount ignores the type filter, so
#: the nodes are read.
BASE_CHANGES_QUERY = (
    "query($owner: String!, $name: String!, $number: Int!) { repository(owner:"
    " $owner, name: $name) { pullRequest(number: $number) { timelineItems("
    "itemTypes: [BASE_REF_CHANGED_EVENT, AUTOMATIC_BASE_CHANGE_SUCCEEDED_EVENT],"
    " first: 1) { nodes { __typename } pageInfo { hasNextPage } } } } }"
)


def _base_changed(number: Any) -> Optional[bool]:
    """Whether pull request ``number``'s base was ever changed; None if that
    cannot be read."""

    owner, name = LEDGER_REPOSITORY.split("/")
    result = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={BASE_CHANGES_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={number}",
            "--jq",
            ".data.repository.pullRequest.timelineItems"
            " | (.nodes | length > 0) or .pageInfo.hasNextPage",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    answer = result.stdout.strip() if result.returncode == 0 else ""
    return {"true": True, "false": False}.get(answer)


def _shared_branch_pull_requests(
    branch: str, commit: str, pull_request: str
) -> Optional[list[str]]:
    """Why runs at ``commit`` may not all be the candidate's own pull
    request's, against main: the pull requests from this repository's
    ``branch`` that make them ambiguous; None if they cannot all be read.

    Any other pull request from the candidate branch runs the same workflows
    with the same commit, branch and repository as the candidate's own,
    ``pull_request`` (round 6 of #635), and GitHub's run records say neither
    which pull request started a run nor which base it tested. A pull
    request's current base does not settle it either: a base change keeps
    the earlier runs (round 7), and a base branch renamed into main records
    no event at all (round 9). So every other pull request from the branch
    that is open, or was closed or merged at this commit, counts, whatever
    its base, and so does the candidate's own if its base was ever changed.

    What it cannot see: a base renamed into main after running at the
    commit on the candidate's own pull request, including one prepare's
    lookup adopted as the candidate's after the rename (round 10). Renaming
    a branch into main is an admin's deliberate act, outside what promotion
    guards against (``_promote``). The REST listing filtered by
    ``head=<owner>:<branch>`` holds only this repository's pull requests,
    all of them (paginated), so a fork's with the same branch name can
    neither shadow nor crowd them out.
    """

    owner = LEDGER_REPOSITORY.split("/")[0]
    result = subprocess.run(
        [
            "gh",
            "api",
            "-X",
            "GET",
            f"repos/{LEDGER_REPOSITORY}/pulls",
            "-f",
            f"head={owner}:{branch}",
            "-f",
            "state=all",
            "-f",
            "per_page=100",
            "--paginate",
            "--jq",
            ".[] | {number, state, merged: (.merged_at != null), base: .base.ref,"
            " head_sha: .head.sha} | tojson",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        listing = [json.loads(line) for line in result.stdout.splitlines() if line]
    except json.JSONDecodeError:
        return None
    shared = sorted(
        f"#{pr.get('number')} (to {pr.get('base')}, "
        f"{'merged' if pr.get('merged') else pr.get('state')})"
        for pr in listing
        if str(pr.get("number")) != pull_request
        and (pr.get("state") == "open" or pr.get("head_sha") == commit)
    )
    changed = _base_changed(pull_request)
    if changed is None:
        return None
    if changed:
        shared.append(f"#{pull_request} (the candidate's own, after a base change)")
    return shared


#: A run is re-run until it has made this many attempts in all, so a genuine
#: failure is not retried until a flaky test happens to pass. The first
#: attempt of a qualified_exact_pair candidate's runs fails by design (its
#: ledger receipt is published after they start), so this leaves the re-run
#: that sees the receipt and two more for flakes. A candidate whose newest
#: run is still unsuccessful at the cap fails the promote run visibly.
MAX_RUN_ATTEMPTS = 4


def _newest_runs(runs: list[dict[str, Any]]) -> dict[tuple[Any, Any], dict[str, Any]]:
    """The newest run of each workflow (``path``) and event."""

    newest: dict[tuple[Any, Any], dict[str, Any]] = {}
    for run in runs:
        key = (run.get("path"), run.get("event"))
        if key not in newest or run.get("id", 0) > newest[key].get("id", 0):
            newest[key] = run
    return newest


#: The results refresh re-runs. GitHub re-runs a run only within 30 days of
#: its first attempt.
RERUN_CONCLUSIONS = frozenset({"failure", "timed_out", "cancelled"})
RERUN_WINDOW = datetime.timedelta(days=30)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _commit_runs(commit: str) -> Optional[list[dict[str, Any]]]:
    """Every workflow run GitHub lists at ``commit``; None if unreadable."""

    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{LEDGER_REPOSITORY}/actions/runs?head_sha={commit}&per_page=100",
            "--paginate",
            "--jq",
            ".workflow_runs[] | {id, head_sha, head_branch,"
            " head_repository: .head_repository.full_name, path, event, status,"
            " conclusion, check_suite_id, run_attempt, created_at} | tojson",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return [json.loads(line) for line in result.stdout.splitlines() if line]
    except json.JSONDecodeError:
        return None


def _own_runs(
    runs: list[dict[str, Any]], commit: str, branch: str
) -> list[dict[str, Any]]:
    """The runs of this repository's candidate branch at ``commit``.

    The runs listing for a commit also holds runs of any other pull request
    at that commit, a fork's included (round 5 of #635); only runs from this
    repository on the candidate branch are the candidate's. Runs of another
    pull request from the candidate branch itself look the same, so refresh
    and promotion first check there is none
    (``_shared_branch_pull_requests``).
    """

    return [
        run
        for run in runs
        if run.get("head_sha") == commit
        and run.get("head_branch") == branch
        and run.get("head_repository") == LEDGER_REPOSITORY
    ]


def _candidate_runs(commit: str, branch: str) -> Optional[list[dict[str, Any]]]:
    """``_own_runs`` of the runs listed at ``commit``; None if unreadable."""

    runs = _commit_runs(commit)
    return None if runs is None else _own_runs(runs, commit, branch)


def _rerun_due(run: dict[str, Any], now: datetime.datetime) -> bool:
    """Whether refresh re-runs this finished run: it failed, timed out or was
    cancelled, has attempts left, and GitHub will still re-run it."""

    if run.get("status") != "completed" or run.get("conclusion") not in (
        RERUN_CONCLUSIONS
    ):
        return False
    if int(run.get("run_attempt") or 1) >= MAX_RUN_ATTEMPTS:
        return False
    created = run.get("created_at")
    if isinstance(created, str) and created:
        started = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
        if now - started > RERUN_WINDOW:
            return False
    return True


def cmd_refresh_pr_checks(args: argparse.Namespace) -> int:
    """Re-run a candidate's unsuccessful newest runs once its receipt is out.

    The PR workflow does not subscribe to edits or ready_for_review events,
    and the run of the code-changes workflow on the candidate's own tree is
    dispatched once, by ``prepare``. So for each workflow and event the
    newest of the candidate's own runs (``_candidate_runs``) is re-run when
    ``_rerun_due``: a failed or timed-out one by its failed jobs, a
    cancelled one (a job timeout cancels the run) in full. Older runs a
    newer one replaced are left alone, and so is every run of a candidate
    whose runs may have tested another base (``_shared_branch_pull_requests``):
    promotion refuses it anyway, and re-runs would retest that base and
    spend the attempts. GITHUB_TOKEN may
    re-run existing runs with actions: write.
    """

    pull_requests = {pr["headRefName"]: pr for pr in _candidate_pull_requests()}
    now = _now()
    for receipt in latest_receipts(Path(args.ledger)):
        branch = candidate_branch(receipt.pair)
        head = receipt.harness.git_commit
        pull_request = pull_requests.get(branch)
        if (
            not receipt.promotable
            or pull_request is None
            or pull_request["headRefOid"] != head
        ):
            continue
        shared = _shared_branch_pull_requests(branch, head, str(pull_request["number"]))
        if shared is None:
            print(f"::warning::could not read the pull requests from {branch}")
            continue
        if shared:
            print(
                f"::warning::not re-running {branch}'s runs: they may have "
                f"tested another base, from pull requests {', '.join(shared)}"
            )
            continue
        listed = _candidate_runs(head, branch)
        if listed is None:
            print(f"::warning::could not read the runs of {branch} at {head}")
            continue
        runs = [
            run
            for run in listed
            if run["event"] in ("pull_request", "workflow_dispatch")
        ]
        for run in _newest_runs(runs).values():
            if not _rerun_due(run, now):
                continue
            rerun = subprocess.run(
                ["gh", "run", "rerun", str(run["id"]), "--repo", LEDGER_REPOSITORY]
                + ([] if run["conclusion"] == "cancelled" else ["--failed"]),
                check=False,
            )
            if rerun.returncode != 0:
                # GitHub refuses some re-runs (a run older than 30 days, one
                # cancelled before it had jobs); the steps after refresh must
                # still run, so this one is reported and the rest go on.
                print(
                    f"::warning::GitHub did not re-run {run['conclusion']} run "
                    f"{run['id']} ({run.get('path')}, {run['event']}) at {head}"
                )
                continue
            print(
                f"Re-running {run['conclusion']} run {run['id']} "
                f"({run.get('path')}, {run['event']}) at {head}"
            )
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    bundle = json.loads(BUNDLE_PATH.read_text())
    problems: list[str] = []
    receipts = latest_receipts(Path(args.ledger), problems=problems)
    for problem in problems:
        # Such a pair is left out of the plan until its files are rederived.
        print(f"::warning::{problem}")
    pull_requests = _candidate_pull_requests() if args.apply else []
    branches = {pr["headRefName"]: pr["headRefOid"] for pr in pull_requests}
    # Every write to a pull request goes by number: gh looks a branch name up
    # among a limited listing, which a fork's pull request can shadow.
    numbers = {pr["headRefName"]: str(pr["number"]) for pr in pull_requests}
    plan = plan_promotion(receipts, bundle, branches)
    print(f"promotion: {plan.reason}")
    if plan.target is not None:
        print(
            f"target {plan.ready_branch or 'not promotable now'} "
            f"(pair {plan.target.pair_id[:12]}, commit {plan.ready_commit})"
        )
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
                numbers.get(branch, branch),
                "--repo",
                LEDGER_REPOSITORY,
                "--comment",
                f"Superseded: {plan.reason}. The ledger keeps this candidate's evidence.",
            ],
            check=False,
        )
    # Only the plan's target may be ready, and only while _promote finds it
    # on current main: any other ready candidate (left by a run that could
    # not undo it, or by older code) goes back to draft.
    returned = [
        _set_ready(str(pr["number"]), False)
        for pr in sorted(pull_requests, key=lambda pr: pr["number"])
        if not pr["isDraft"] and pr["headRefName"] != plan.ready_branch
    ]
    safe = True
    if plan.ready_branch is not None and plan.ready_commit is not None:
        safe = _promote(
            plan.ready_branch,
            plan.ready_commit,
            automatic=config()["promotion"]["automatic"],
            pull_request=numbers.get(plan.ready_branch, plan.ready_branch),
        )
    return 0 if all(returned) and safe else 1


def _set_ready(pull_request: str, ready: bool) -> bool:
    """Mark a candidate's pull request (a branch or a number) ready or draft;
    whether that worked.

    A draft that stays ready could be merged onto a moved main, so a failed
    return to draft is reported as an error for the run to fail on.
    """

    done = (
        subprocess.run(
            ["gh", "pr", "ready", pull_request, "--repo", LEDGER_REPOSITORY]
            + ([] if ready else ["--undo"]),
            check=False,
        ).returncode
        == 0
    )
    if not done and not ready:
        print(f"::error::could not return {pull_request} to draft")
    return done


def _promote(
    branch: str, commit: str, *, automatic: bool, pull_request: Optional[str] = None
) -> bool:
    """Make main exactly the qualified commit, or change nothing.

    The qualified commit's parent is the main commit it was built on. Only
    while main is still that commit does a merge of the candidate equal the
    qualified tree, so only then is its pull request readied; otherwise it
    is kept draft (no merge can combine it with other code) and the catch-up
    requalifies it on current main. With automatic promotion the pull
    request stays draft until every check on the commit's own tree has
    passed, and main is then moved to the commit by a push leased on that
    parent: if main is anything else at that instant, nothing changes.
    GitHub then records the pull request as merged.

    Returns False when a return to draft failed, which leaves a ready pull
    request that a merge could combine with other code, when the candidate
    waits on runs refresh will not re-run again, or when its runs may have
    tested another base (``_shared_branch_pull_requests``); either way the
    promote run fails so someone sees it. ``pull_request`` names the
    candidate's pull request for readiness changes (its number; the branch
    by default).

    What it guards against: mistakes by people who can write to this
    repository, and anything people who cannot can do (forks' pull requests,
    whatever branch names they use, and pull requests opened from the
    candidate branch by anyone who can read it, which make promotion refuse
    rather than accept). Whatever else happens, main
    only ever becomes the exact qualified commit, built on main as it is at
    the push, after the dispatched run on that commit's own tree passed.
    It does not try to resist deliberate disguise by people who can write
    here, such as renaming another branch into main or retargeting pull
    requests so that a run against another base looks like the candidate's:
    main is not protected, so they could push it directly. The pull request
    checks it also requires are as trustworthy as those people.
    """

    target = pull_request or branch

    fetched = subprocess.run(
        ["git", "fetch", "origin", f"refs/heads/{branch}"],
        check=False,
        capture_output=True,
        text=True,
    )
    head = _git_out("rev-parse", "FETCH_HEAD") if fetched.returncode == 0 else ""
    parent = _git_out("rev-parse", f"{commit}^") if head == commit else ""
    listed = _git_out("ls-remote", "origin", "refs/heads/main").split()
    main = listed[0] if listed else ""
    if head != commit or not parent or parent != main:
        print(
            f"not promotable now: {branch} is not the qualified commit "
            f"{commit[:12]} built on current main; it is requalified on current main"
        )
        return _set_ready(target, False)
    if not automatic:
        _set_ready(target, True)
        return True
    shared = _shared_branch_pull_requests(branch, commit, target)
    if shared is None:
        print(
            f"automatic promotion waits for {branch}: the pull requests from it "
            "could not be read"
        )
        return _set_ready(target, False)
    if shared:
        # Their runs and the candidate's cannot be told apart, and they stay
        # at this commit after the pull requests close: only a new candidate
        # commit (and, if the candidate's own was one, a new pull request to
        # main, which prepare opens) leaves them behind.
        print(
            f"::error::{branch} is not promoted: runs at its commit may have "
            f"tested another base, from pull requests {', '.join(shared)}, and "
            "GitHub does not record which pull request or base a run is for; "
            "close them and requalify the pair"
        )
        _set_ready(target, False)
        return False
    waiting, stranded = _unfinished_checks(commit, branch)
    if waiting:
        print(f"automatic promotion waits for {branch}: " + "; ".join(waiting))
        if stranded:
            # Refresh will not re-run these again, and nothing else moves
            # the candidate while main stays put: say so in the run's result.
            print(
                f"::error::{branch} waits on runs refresh will not re-run; re-run "
                "or re-dispatch them by hand, or requalify the pair: "
                + "; ".join(stranded)
            )
        # A pull request a person or an interrupted run left ready goes back
        # to draft until every check on its own tree has passed.
        return _set_ready(target, False) and not stranded
    _set_ready(target, True)
    pushed = subprocess.run(
        [
            "git",
            "push",
            f"--force-with-lease=refs/heads/main:{parent}",
            "origin",
            f"{commit}:refs/heads/main",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if pushed.returncode != 0:
        print(
            f"automatic promotion skipped: main is no longer {parent[:12]}; "
            "the pair is requalified on current main"
        )
        return _set_ready(target, False)
    print(f"promoted {branch} at {commit[:12]} to main")
    return True


def _git_out(*args: str) -> str:
    result = subprocess.run(["git", *args], check=False, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def _unfinished_checks(commit: str, branch: str) -> tuple[list[str], list[str]]:
    """Why the qualified commit's checks do not yet show its own tree passing,
    and which of the runs it waits on refresh will not re-run.

    Pull request runs test the candidate merged with main as it was then;
    the run of the code-changes workflow that the qualification dispatches on
    the candidate branch tests the commit's own tree, and must exist. Only
    the candidate's own runs count (``_own_runs``): a run of a pull request
    from another branch or a fork at the same commit neither blocks nor
    passes it (``_promote`` has already refused a candidate whose branch has
    another pull request sharing its runs). For each workflow and event,
    the newest own run must have
    finished successfully, and for each check name the newest check must
    have finished as success, skipped or neutral. Checks of any run that is
    not a newest own run (one a newer run replaced, or another pull
    request's) are not counted at all; checks outside any workflow run (an
    app's) are. A run still registering its jobs, no checks, or an
    unreadable list waits. A finished, unsuccessful newest own run that
    refresh will not re-run (``_rerun_due``) is stranded.
    """

    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{LEDGER_REPOSITORY}/commits/{commit}/check-runs?per_page=100",
            "--paginate",
            "--jq",
            ".check_runs[] | {id, name, status, conclusion,"
            " check_suite_id: .check_suite.id} | tojson",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    checks: Optional[list[dict[str, Any]]] = None
    if result.returncode == 0:
        try:
            checks = [json.loads(line) for line in result.stdout.splitlines() if line]
        except json.JSONDecodeError:
            checks = None
    runs = _commit_runs(commit)
    if checks is None or runs is None:
        return ["the checks could not be read"], []
    newest_runs = _newest_runs(_own_runs(runs, commit, branch))
    excluded_suites = {run.get("check_suite_id") for run in runs} - {
        run.get("check_suite_id") for run in newest_runs.values()
    }
    counted = [
        check for check in checks if check.get("check_suite_id") not in excluded_suites
    ]
    newest_checks: dict[Any, dict[str, Any]] = {}
    for check in counted:
        name = check.get("name")
        if name not in newest_checks or check.get("id", 0) > newest_checks[name].get(
            "id", 0
        ):
            newest_checks[name] = check
    problems = [
        f"workflow {path} ({event}) is {run.get('conclusion') or run.get('status')}"
        for (path, event), run in newest_runs.items()
        if run.get("status") != "completed" or run.get("conclusion") != "success"
    ]
    problems += [
        f"check {name} is {check.get('conclusion') or check.get('status')}"
        for name, check in newest_checks.items()
        if check.get("status") != "completed"
        or check.get("conclusion") not in ("success", "skipped", "neutral")
    ]
    if (CODE_CHANGES_WORKFLOW, "workflow_dispatch") not in newest_runs:
        problems.append(
            f"no {CODE_CHANGES_WORKFLOW} run on the candidate's own tree yet"
        )
    if not counted:
        problems.append("no checks reported yet")
    now = _now()
    stranded = sorted(
        f"workflow {path} ({event}) is {run.get('conclusion')} after "
        f"{run.get('run_attempt') or 1} attempt(s)"
        for (path, event), run in newest_runs.items()
        if run.get("status") == "completed"
        and run.get("conclusion") != "success"
        and not _rerun_due(run, now)
    )
    return sorted(problems), stranded


def cmd_accept(args: argparse.Namespace) -> int:
    pair_dir = pair_directory(Path(args.ledger), "uk", args.pair_id)
    path = pair_dir / "qualification_receipt.json"
    # Accept only a receipt that is an attempt's own, never a merged one.
    receipt = published_receipt(pair_dir)
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
    resolve.add_argument("--core-version")
    resolve.add_argument("--pair-id")
    resolve.add_argument("--ledger")
    resolve.add_argument("--force", action="store_true")
    resolve.add_argument("--out", required=True)
    resolve.set_defaults(func=cmd_resolve)

    still_eligible = commands.add_parser("still-eligible")
    still_eligible.add_argument("--candidate", required=True)
    still_eligible.add_argument("--ledger", required=True)
    still_eligible.set_defaults(func=cmd_still_eligible)

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

    refresh = commands.add_parser("refresh-pr-checks")
    refresh.add_argument("--ledger", required=True)
    refresh.set_defaults(func=cmd_refresh_pr_checks)

    recoverable = commands.add_parser("recoverable")
    recoverable.add_argument("--ledger", required=True)
    recoverable.set_defaults(func=cmd_recoverable)

    requalify = commands.add_parser("requalify")
    requalify.add_argument("--ledger", required=True)
    requalify.set_defaults(func=cmd_requalify)

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

    rederive = commands.add_parser("rederive-ledger")
    rederive.add_argument("ledger")
    rederive.set_defaults(func=cmd_rederive_ledger)
    return parser


def cmd_rederive_ledger(args: argparse.Namespace) -> int:
    """Recompute every pair's published files from its attempts.

    Called by .github/qualification-ledger.sh after a concurrent publish
    changed a pair's published files on both sides.
    """

    for pair_dir in sorted((Path(args.ledger) / "uk").glob("*")):
        if pair_dir.is_dir():
            rederive_publication(pair_dir)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
