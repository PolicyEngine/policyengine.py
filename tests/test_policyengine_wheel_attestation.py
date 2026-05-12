from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / ".github" / "write_policyengine_wheel_attestation.py"

spec = importlib.util.spec_from_file_location(
    "write_policyengine_wheel_attestation",
    MODULE_PATH,
)
write_policyengine_wheel_attestation = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(write_policyengine_wheel_attestation)


def test_build_attestation_records_bundle_and_wheel_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        json.dumps(
            {
                "bundle_version": "4.4.3",
                "bundle_digest": "sha256:" + "a" * 64,
                "policyengine": {
                    "name": "policyengine",
                    "version": "4.4.3",
                    "role": "bundle_carrier",
                },
            }
        )
    )
    monkeypatch.setattr(
        write_policyengine_wheel_attestation, "BUNDLE_PATH", bundle_path
    )
    monkeypatch.setattr(
        write_policyengine_wheel_attestation,
        "_load_json_url",
        lambda _url: {
            "urls": [
                {
                    "packagetype": "bdist_wheel",
                    "filename": "policyengine-4.4.3-py3-none-any.whl",
                    "url": "https://files.pythonhosted.org/policyengine.whl",
                    "digests": {"sha256": "b" * 64},
                    "upload_time_iso_8601": "2026-05-12T00:00:00Z",
                }
            ]
        },
    )

    attestation = write_policyengine_wheel_attestation.build_attestation(
        version="4.4.3",
        retries=1,
        sleep_seconds=0,
    )

    assert attestation["bundle"]["version"] == "4.4.3"
    assert attestation["bundle"]["digest"] == "sha256:" + "a" * 64
    assert attestation["package"]["version"] == "4.4.3"
    assert attestation["package"]["sha256"] == "b" * 64
