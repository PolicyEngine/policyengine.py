from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "bundle.json"
PYPI_PROJECT = "policyengine"
PYPI_JSON_URL = "https://pypi.org/pypi/{name}/{version}/json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write a post-publish attestation for the policyengine wheel."
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--retries", type=int, default=12)
    parser.add_argument("--sleep-seconds", type=float, default=10.0)
    args = parser.parse_args()

    attestation = build_attestation(
        version=args.version,
        retries=args.retries,
        sleep_seconds=args.sleep_seconds,
    )
    args.output.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.output}.")
    return 0


def build_attestation(
    *,
    version: str,
    retries: int = 12,
    sleep_seconds: float = 10.0,
) -> dict[str, Any]:
    bundle = json.loads(BUNDLE_PATH.read_text())
    if bundle.get("bundle_version") != version:
        raise ValueError(
            "Vendored bundle_version does not match attested policyengine version: "
            f"{bundle.get('bundle_version')} != {version}."
        )
    if (bundle.get("policyengine") or {}).get("version") != version:
        raise ValueError(
            "Vendored policyengine package version does not match attested version."
        )

    wheel = _fetch_policyengine_wheel(version, retries, sleep_seconds)
    return {
        "schema_version": 1,
        "generated_at": _now_timestamp(),
        "source": "pypi",
        "bundle": {
            "version": bundle["bundle_version"],
            "digest": bundle.get("bundle_digest"),
        },
        "package": {
            "name": PYPI_PROJECT,
            "version": version,
            "filename": wheel.get("filename"),
            "wheel_url": wheel.get("url"),
            "sha256": wheel.get("digests", {}).get("sha256"),
            "uploaded_at": wheel.get("upload_time_iso_8601"),
        },
    }


def _fetch_policyengine_wheel(
    version: str,
    retries: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    url = PYPI_JSON_URL.format(
        name=urllib.parse.quote(PYPI_PROJECT),
        version=urllib.parse.quote(version),
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            payload = _load_json_url(url)
            wheel = _select_wheel(payload)
            sha256 = wheel.get("digests", {}).get("sha256")
            if not isinstance(sha256, str) or not sha256:
                raise ValueError(
                    f"PyPI wheel for {PYPI_PROJECT}=={version} has no sha256."
                )
            return wheel
        except Exception as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(sleep_seconds)
    raise RuntimeError(
        f"Could not attest {PYPI_PROJECT}=={version} from PyPI after "
        f"{retries} attempts."
    ) from last_error


def _load_json_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "policyengine.py"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _select_wheel(payload: dict[str, Any]) -> dict[str, Any]:
    wheels = [
        item
        for item in payload.get("urls", [])
        if item.get("packagetype") == "bdist_wheel"
    ]
    if not wheels:
        raise ValueError("No wheel distribution found on PyPI.")
    pure_python_wheels = [
        item for item in wheels if "py3-none-any" in str(item.get("filename", ""))
    ]
    selected = pure_python_wheels or wheels
    sha256s = {item.get("digests", {}).get("sha256") for item in selected}
    sha256s.discard(None)
    if len(sha256s) != 1:
        raise ValueError("PolicyEngine wheel selection is ambiguous.")
    return selected[0]


def _now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    sys.exit(main())
