"""Check that an installed distribution is byte-identical to a wheel.

A wheel's ``*.dist-info/RECORD`` lists every file with its SHA-256. An
installed distribution keeps its own RECORD. The installed files match the
wheel when every hashed file in the wheel's RECORD is installed with the same
hash and the bytes on disk hash to it, and nothing else was installed beyond
the files an installer adds (``INSTALLER``, ``REQUESTED``, ``direct_url.json``,
compiled ``.pyc`` files and the rewritten ``RECORD``).
"""

from __future__ import annotations

import base64
import csv
import io
import zipfile
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

from policyengine.utils.hashing import sha256_file

__all__ = [
    "INSTALLER_FILES",
    "parse_record",
    "record_digest_to_hex",
    "verify_installed_against_wheel",
    "wheel_record",
]

#: Files an installer adds to a distribution that are not in the wheel RECORD.
INSTALLER_FILES = frozenset(
    {"INSTALLER", "REQUESTED", "direct_url.json", "uv_cache.json"}
)


def record_digest_to_hex(value: str) -> str:
    """Convert a RECORD ``sha256=<urlsafe base64, no padding>`` digest to hex."""

    algorithm, _, encoded = value.partition("=")
    if algorithm != "sha256":
        raise ValueError(f"Unsupported RECORD hash {algorithm!r}.")
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).hex()


def parse_record(text: str) -> dict[str, Optional[str]]:
    """``{path: hex sha256 or None}`` from a RECORD file."""

    entries: dict[str, Optional[str]] = {}
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        path, digest = row[0], (row[1] if len(row) > 1 else "")
        entries[path] = record_digest_to_hex(digest) if digest else None
    return entries


def wheel_record(wheel_path: Path) -> dict[str, Optional[str]]:
    with zipfile.ZipFile(wheel_path) as archive:
        names = [
            name for name in archive.namelist() if name.endswith(".dist-info/RECORD")
        ]
        if len(names) != 1:
            raise ValueError(f"{wheel_path.name} has {len(names)} RECORD files.")
        return parse_record(archive.read(names[0]).decode("utf-8"))


def verify_installed_against_wheel(
    name: str, wheel_path: Path, *, metadata: Any = importlib_metadata
) -> dict[str, Any]:
    """Compare an installed distribution with a wheel; never raises on mismatch.

    Returns evidence: the wheel's SHA-256, how many files were verified, any
    files installed beyond the wheel, and ``problems`` (empty when the
    installed files are exactly the wheel's).
    """

    expected = wheel_record(wheel_path)
    distribution = metadata.distribution(name)
    installed: dict[str, Optional[str]] = {}
    for file in distribution.files or []:
        installed[str(file)] = (
            record_digest_to_hex(f"{file.hash.mode}={file.hash.value}")
            if file.hash is not None
            else None
        )
    problems: list[str] = []
    verified = 0
    for path, digest in sorted(expected.items()):
        if digest is None:
            continue
        if installed.get(path, "absent") != digest:
            problems.append(f"{path}: installed RECORD differs from the wheel")
            continue
        located = Path(distribution.locate_file(path))
        if not located.is_file():
            problems.append(f"{path}: missing on disk")
            continue
        if sha256_file(located) != digest:
            problems.append(f"{path}: bytes differ from the wheel")
            continue
        verified += 1
    extra = sorted(
        path
        for path in installed
        if path not in expected
        and not path.endswith(".pyc")
        and Path(path).name not in INSTALLER_FILES
        and not path.endswith(".dist-info/RECORD")
    )
    problems.extend(f"{path}: installed but not in the wheel" for path in extra)
    return {
        "wheel": wheel_path.name,
        "wheel_sha256": sha256_file(wheel_path),
        "files_verified": verified,
        "unexpected_installed_files": extra,
        "problems": problems,
    }
