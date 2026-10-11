"""Installed files are verified byte for byte against a wheel's RECORD.

Invariant: an untouched install verifies, and mutating any single installed
file, or installing a file the wheel lacks, fails verification.
"""

from __future__ import annotations

import base64
import hashlib
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance.wheels import (
    parse_record,
    record_digest_to_hex,
    verify_installed_against_wheel,
)

FILES = {
    "policyengine_uk/__init__.py": b"VERSION = '2.126.8'\n",
    "policyengine_uk/system.py": b"system = object()\n",
    "policyengine_uk/parameters/rate.yaml": b"values:\n  2027-04-06: 0.2\n",
}
DIST_INFO = "policyengine_uk-2.126.8.dist-info"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")


def build_wheel(tmp_path: Path, files=FILES):
    """A wheel, an installed copy of it, and the installed RECORD lines."""

    record = [f"{path},sha256={_b64(data)},{len(data)}" for path, data in files.items()]
    record.append(f"{DIST_INFO}/RECORD,,")
    wheel = tmp_path / "policyengine_uk-2.126.8-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
        archive.writestr(f"{DIST_INFO}/RECORD", "\n".join(record) + "\n")
    site = tmp_path / "site"
    for path, data in files.items():
        (site / path).parent.mkdir(parents=True, exist_ok=True)
        (site / path).write_bytes(data)
    installed = record + [
        f"{DIST_INFO}/INSTALLER,sha256={_b64(b'uv')},2",
        f"{DIST_INFO}/REQUESTED,,",
    ]
    return wheel, site, installed


class _File(str):
    pass


def fake_metadata(site: Path, record_lines):
    def distribution(name):
        files = []
        for line in record_lines:
            path, digest, *_ = line.split(",")
            item = _File(path)
            item.hash = (
                SimpleNamespace(mode="sha256", value=digest.split("=", 1)[1])
                if digest
                else None
            )
            files.append(item)
        return SimpleNamespace(files=files, locate_file=lambda path: site / path)

    return SimpleNamespace(distribution=distribution)


def test_record_hash_decoding():
    data = b"hello"
    assert (
        record_digest_to_hex(f"sha256={_b64(data)}") == hashlib.sha256(data).hexdigest()
    )
    assert parse_record(f"a.py,sha256={_b64(data)},5\nRECORD,,\n") == {
        "a.py": hashlib.sha256(data).hexdigest(),
        "RECORD": None,
    }
    with pytest.raises(ValueError):
        record_digest_to_hex("md5=abc")


def test_untouched_install_verifies(tmp_path):
    wheel, site, record = build_wheel(tmp_path)
    evidence = verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=fake_metadata(site, record)
    )
    assert evidence["problems"] == []
    assert evidence["files_verified"] == len(FILES)
    assert evidence["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()


@settings(max_examples=30, deadline=None)
@given(index=st.integers(0, len(FILES) - 1), extra=st.binary(min_size=1, max_size=8))
def test_any_mutated_installed_file_fails(tmp_path_factory, index, extra):
    wheel, site, record = build_wheel(tmp_path_factory.mktemp("wheel"))
    target = site / list(FILES)[index]
    target.write_bytes(target.read_bytes() + extra)
    assert verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=fake_metadata(site, record)
    )["problems"]


def test_extra_installed_file_fails(tmp_path):
    wheel, site, record = build_wheel(tmp_path)
    (site / "policyengine_uk" / "injected.py").write_bytes(b"x = 1\n")
    record = record + [f"policyengine_uk/injected.py,sha256={_b64(b'x = 1')},6"]
    evidence = verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=fake_metadata(site, record)
    )
    assert any("injected.py" in problem for problem in evidence["problems"])
