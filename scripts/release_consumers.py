"""Build the post-release dispatches for policyengine.py consumers.

Run by the NotifyConsumers job in ``.github/workflows/push.yaml`` after a
release is visible on PyPI::

    python scripts/release_consumers.py payload --version 6.2.7 > payload.json
    python scripts/release_consumers.py scorecard-request --version 6.2.7 > request.json

``payload`` is the ``policyengine-release`` repository dispatch (version,
certified UK bundle identity, qualification digests). ``scorecard-request``
is the scorecard's ``released_bundle`` replay request; it needs the release
installed (``pip install "policyengine[uk]==<version>"``) and
``HUGGING_FACE_TOKEN``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")

import requests  # noqa: E402

from policyengine.provenance.qualification_ledger import (
    fetch_ledger_receipt,  # noqa: E402
)
from policyengine.provenance.uk_qualification import (  # noqa: E402
    release_dispatch_payload,
    released_bundle_request,
)

BUNDLE_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
TIMEOUT = 60
TOKEN_VARIABLES = ("HF_TOKEN", "HUGGING_FACE_TOKEN", "HUGGINGFACE_HUB_TOKEN")


def _bundle() -> dict:
    return json.loads(BUNDLE_PATH.read_text())


def _pypi(path: str) -> dict:
    response = requests.get(f"https://pypi.org/pypi/{path}/json", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def _hf_file(repo_id: str, revision: str, path: str) -> bytes:
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    response = requests.get(
        f"https://huggingface.co/{repo_id}/resolve/{revision}/{path}",
        headers={"Authorization": f"Bearer {token}"} if token else {},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.content


def cmd_payload(args: argparse.Namespace) -> int:
    payload = release_dispatch_payload(
        _bundle(), version=args.version, fetch_receipt=fetch_ledger_receipt
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


def _installed(code: str, *, strip_tokens: bool) -> str:
    """Run ``code`` against the installed release, outside the checkout."""

    env = dict(os.environ)
    env.pop("POLICYENGINE_SKIP_COUNTRY_IMPORTS", None)
    if strip_tokens:
        for key in TOKEN_VARIABLES:
            env.pop(key, None)
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        cwd="/",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def cmd_scorecard_request(args: argparse.Namespace) -> int:
    release = _pypi(f"policyengine/{args.version}")
    wheels = [item for item in release["urls"] if item["packagetype"] == "bdist_wheel"]
    if len(wheels) != 1:
        raise SystemExit(f"policyengine {args.version} must publish exactly one wheel.")
    installed_version = _installed(
        "from importlib.metadata import version; print(version('policyengine'))",
        strip_tokens=False,
    )
    if installed_version != args.version:
        raise SystemExit(
            f"policyengine {installed_version} is installed, not {args.version}."
        )
    manifest_path = _installed(
        "from importlib.resources import files; "
        "print(files('policyengine').joinpath('data', 'bundle', 'manifest.json'))",
        strip_tokens=False,
    )
    release_bundle = json.loads(
        _installed(
            "import json, policyengine as pe; "
            "print(json.dumps(dict(pe.uk.uk_latest.release_bundle), sort_keys=True))",
            strip_tokens=True,
        ).splitlines()[-1]
    )
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY", "PolicyEngine/policyengine.py")
    run_id = os.environ.get("GITHUB_RUN_ID", "1")
    request = released_bundle_request(
        json.loads(Path(manifest_path).read_text()),
        version=args.version,
        wheel_sha256=wheels[0]["digests"]["sha256"],
        packaged_manifest_sha256=hashlib.sha256(
            Path(manifest_path).read_bytes()
        ).hexdigest(),
        release_bundle=release_bundle,
        hf_file=_hf_file,
        pypi_project=_pypi,
        requested_by={
            "repository": repository,
            "workflow_run_id": int(run_id),
            "run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
            "commit": os.environ.get("GITHUB_SHA", "0" * 40),
            "run_url": f"{server}/{repository}/actions/runs/{run_id}",
        },
    )
    print(
        json.dumps(
            {
                "event_type": "uk-replay-qualification-request",
                "client_payload": {"request": request.document()},
            },
            sort_keys=True,
        )
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    payload = commands.add_parser("payload")
    payload.add_argument("--version", required=True)
    payload.set_defaults(func=cmd_payload)
    scorecard = commands.add_parser("scorecard-request")
    scorecard.add_argument("--version", required=True)
    scorecard.set_defaults(func=cmd_scorecard_request)
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
