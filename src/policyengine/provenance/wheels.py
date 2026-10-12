"""Check that an installed distribution is byte-identical to a wheel.

A wheel's ``*.dist-info/RECORD`` lists every file in the archive with its
SHA-256. Verification has two halves, and both must hold:

1. **The wheel is what its RECORD says.** Every archive member is listed in
   the RECORD with the hash of its bytes, and every RECORD entry is an
   archive member: a one-to-one match. Only the RECORD itself (and a RECORD
   signature) is listed without a hash. Without this, a zip holding a copied
   RECORD would "verify" and its SHA-256 would name a wheel the installed
   files never came from.
2. **The installed files are the wheel's.** Every hashed file in the wheel's
   RECORD is installed with the same hash, and the bytes on disk hash to it.
   Nothing else is installed beyond what an installer adds: ``INSTALLER``,
   ``REQUESTED``, ``direct_url.json`` and ``uv_cache.json`` in the
   ``.dist-info`` directory, the rewritten ``RECORD``, bytecode caches, and
   the console and GUI script launchers it generates in the scripts
   directory, outside the site directory, for the entry points the wheel's
   ``entry_points.txt`` declares. Launchers are generated per environment
   (they embed the interpreter path), so they are named, not compared.
3. **The bytecode that runs is the wheel's.** The interpreter runs a
   ``__pycache__`` file instead of compiling its source, so every cache
   this interpreter would load for a verified ``.py`` file (at any
   optimisation level, listed in the RECORD or not, under
   ``sys.pycache_prefix`` when set) must compile from that source; see
   :func:`policyengine.provenance.bytecode.compiled_file`. A cache this
   interpreter would ignore (another Python's tag, a stale timestamp) is
   inert and only reported. A listed cache for this interpreter whose
   source is not a verified file is not the wheel's.

Not covered: files on disk that the installed RECORD does not list, other
than bytecode caches of verified sources, and anything outside the
distribution (other distributions, ``.pth`` files in the site directory).

A wheel with a ``*.data`` directory installs those files under other paths,
so it does not verify; none of the UK bundle's distributions has one.
"""

from __future__ import annotations

import base64
import configparser
import csv
import hashlib
import importlib.util
import io
import sys
import zipfile
from importlib import metadata as importlib_metadata
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from policyengine.provenance.bytecode import OPTIMIZATION_LEVELS, compiled_file
from policyengine.utils.hashing import sha256_file

__all__ = [
    "INSTALLER_FILES",
    "SCRIPT_DIRECTORIES",
    "parse_record",
    "record_digest_to_hex",
    "verify_installed_against_wheel",
    "verify_wheel_archive",
    "wheel_record",
]

#: Files an installer adds to a distribution that are not in the wheel RECORD.
INSTALLER_FILES = frozenset(
    {"INSTALLER", "REQUESTED", "direct_url.json", "uv_cache.json"}
)

#: Directories installers write entry-point launchers to (POSIX, Windows).
SCRIPT_DIRECTORIES = frozenset({"bin", "Scripts"})

#: Entry-point groups an installer turns into launchers.
SCRIPT_GROUPS = ("console_scripts", "gui_scripts")

#: Windows launcher suffixes, longest first.
_LAUNCHER_SUFFIXES = ("-script.pyw", "-script.py", ".exe")

_UNHASHED_RECORD_FILES = ("RECORD", "RECORD.jws", "RECORD.p7s")


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
        if path in entries:
            raise ValueError(f"RECORD lists {path} twice.")
        entries[path] = record_digest_to_hex(digest) if digest else None
    return entries


def _record_member(names: list[str], wheel_name: str) -> str:
    records = [
        name
        for name in names
        if name.endswith(".dist-info/RECORD") and name.count("/") == 1
    ]
    if len(records) != 1:
        raise ValueError(f"{wheel_name} has {len(records)} RECORD files.")
    return records[0]


def wheel_record(wheel_path: Path) -> dict[str, Optional[str]]:
    """The wheel's RECORD as ``{path: hex sha256 or None}`` (not verified)."""

    with zipfile.ZipFile(wheel_path) as archive:
        name = _record_member(archive.namelist(), wheel_path.name)
        return parse_record(archive.read(name).decode("utf-8"))


def _member_sha256(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry_point_scripts(text: str) -> frozenset[str]:
    parser = configparser.ConfigParser(delimiters=("=",), interpolation=None)
    parser.optionxform = str  # type: ignore[assignment,method-assign]
    parser.read_string(text)
    return frozenset(
        name.strip()
        for group in SCRIPT_GROUPS
        if parser.has_section(group)
        for name in parser.options(group)
    )


def verify_wheel_archive(wheel_path: Path) -> dict[str, Any]:
    """Check a wheel's members against its own RECORD; never raises on mismatch.

    Returns ``record`` (``{path: hex sha256 or None}``), ``scripts`` (entry
    point names an installer turns into launchers), ``members_verified`` and
    ``problems`` (empty when members and RECORD match one to one). A wheel
    without exactly one top-level ``*.dist-info/RECORD`` raises ``ValueError``.
    """

    problems: list[str] = []
    with zipfile.ZipFile(wheel_path) as archive:
        members = [info.filename for info in archive.infolist() if not info.is_dir()]
        record_name = _record_member(members, wheel_path.name)
        dist_info = record_name.rsplit("/", 1)[0]
        seen: set[str] = set()
        for name in members:
            if name in seen:
                problems.append(f"{name}: the wheel holds it twice")
            seen.add(name)
        record = parse_record(archive.read(record_name).decode("utf-8"))
        unhashed = {f"{dist_info}/{name}" for name in _UNHASHED_RECORD_FILES}
        verified = 0
        for name in sorted(seen):
            if name in unhashed:
                if record.get(name) is not None:
                    problems.append(f"{name}: RECORD hashes a file it cannot hash")
                continue
            if name not in record:
                problems.append(f"{name}: in the wheel but not in its RECORD")
            elif record[name] is None:
                problems.append(f"{name}: RECORD gives no hash")
            elif _member_sha256(archive, name) != record[name]:
                problems.append(f"{name}: bytes differ from the wheel's RECORD")
            else:
                verified += 1
        problems.extend(
            f"{path}: in the wheel's RECORD but not in the wheel"
            for path in sorted(record)
            if path not in seen
        )
        entry_points = f"{dist_info}/entry_points.txt"
        scripts: frozenset[str] = frozenset()
        if entry_points in seen:
            try:
                scripts = _entry_point_scripts(
                    archive.read(entry_points).decode("utf-8")
                )
            except (configparser.Error, UnicodeDecodeError) as exc:
                problems.append(f"{entry_points}: unreadable ({type(exc).__name__})")
    return {
        "record": record,
        "scripts": scripts,
        "members_verified": verified,
        "problems": problems,
    }


def _launcher_name(path: str) -> Optional[str]:
    """The entry point a generated launcher path is for, if it is one."""

    parts = PurePosixPath(path.replace("\\", "/")).parts
    if len(parts) < 2 or parts[0] != ".." or parts[-2] not in SCRIPT_DIRECTORIES:
        return None
    name = parts[-1]
    for suffix in _LAUNCHER_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _launcher_located(distribution: Any, path: str) -> bool:
    """Whether a launcher exists in a scripts directory outside the site root."""

    site = Path(distribution.locate_file("")).resolve()
    located = Path(distribution.locate_file(path)).resolve()
    return (
        located.is_file()
        and located.parent.name in SCRIPT_DIRECTORIES
        and site not in located.parents
        and located != site
    )


def _installer_file(path: str) -> bool:
    """Whether an installed path is one an installer writes in ``.dist-info``."""

    location = PurePosixPath(path)
    return location.parent.name.endswith(".dist-info") and (
        location.name in INSTALLER_FILES or location.name == "RECORD"
    )


def _cache_entry(path: str) -> Optional[tuple[str, str, str]]:
    """``(source path, cache tag, optimisation)`` for a ``__pycache__`` path."""

    location = PurePosixPath(path)
    if location.parent.name != "__pycache__" or location.suffix != ".pyc":
        return None
    parts = location.name[: -len(".pyc")].split(".")
    optimization = ""
    if len(parts) == 3 and parts[2].startswith("opt-"):
        optimization = parts.pop()[len("opt-") :]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    module, tag = parts
    return str(location.parent.parent / f"{module}.py"), tag, optimization


def _verify_bytecode(
    distribution: Any,
    sources: list[str],
    installed: dict[str, Optional[str]],
    cache_tag: Optional[str],
) -> dict[str, Any]:
    """Check every bytecode cache this interpreter would load for ``sources``."""

    problems: list[str] = []
    # One check per cache *and* the source it stands for: a cache reached
    # through a link can stand for several sources, and must match each.
    checked: dict[tuple[Path, str, str], str] = {}
    inert: list[str] = []
    verified = set(sources)

    def check(pyc: Path, source: str, optimization: str, label: str) -> None:
        key = (pyc.resolve(), source, optimization)
        if key in checked:
            return
        result = compiled_file(
            pyc, Path(distribution.locate_file(source)), optimization
        )
        checked[key] = result.status
        if result.status == "inert":
            inert.append(f"{label}: {result.detail}")
        elif result.status != "matches":
            problems.append(f"{label}: {result.detail}")

    site = Path(distribution.locate_file(""))

    def label(pyc: Path) -> str:
        try:
            return pyc.relative_to(site).as_posix()
        except ValueError:  # under sys.pycache_prefix
            return str(pyc)

    if cache_tag is not None:
        for source in sources:
            located = Path(distribution.locate_file(source))
            for optimization in OPTIMIZATION_LEVELS:
                pyc = Path(
                    importlib.util.cache_from_source(
                        str(located), optimization=optimization
                    )
                )
                if pyc.is_file():
                    check(pyc, source, optimization, label(pyc))
    for path in sorted(installed):
        entry = _cache_entry(path)
        if entry is None:
            continue
        source, tag, optimization = entry
        if tag != cache_tag:
            inert.append(f"{path}: another interpreter's cache")
            continue
        if source not in verified:
            problems.append(f"{path}: caches {source}, which is not in the wheel")
            continue
        pyc = Path(distribution.locate_file(path))
        if not pyc.is_file():
            continue
        check(pyc, source, optimization, path)
    return {
        "verified": sum(1 for status in checked.values() if status == "matches"),
        "inert": sorted(inert),
        "problems": sorted(problems),
    }


def verify_installed_against_wheel(
    name: str,
    wheel_path: Path,
    *,
    metadata: Any = importlib_metadata,
    cache_tag: Optional[str] = sys.implementation.cache_tag,
) -> dict[str, Any]:
    """Compare an installed distribution with a wheel; never raises on mismatch.

    Returns evidence: the wheel's SHA-256, how many archive members,
    installed files and bytecode caches were verified, the launchers
    exempted, inert bytecode caches, any files installed beyond the wheel,
    and ``problems`` (empty only when the wheel matches its RECORD and the
    installed files and the bytecode that would run are exactly the wheel's).
    ``cache_tag`` is the interpreter's bytecode cache tag (``cpython-313``).
    """

    archive = verify_wheel_archive(wheel_path)
    expected: dict[str, Optional[str]] = archive["record"]
    problems: list[str] = list(archive["problems"])
    distribution = metadata.distribution(name)
    installed: dict[str, Optional[str]] = {}
    for file in distribution.files or []:
        installed[str(file)] = (
            record_digest_to_hex(f"{file.hash.mode}={file.hash.value}")
            if file.hash is not None
            else None
        )
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
    launchers = sorted(
        path
        for path in installed
        if path not in expected
        and _launcher_name(path) in archive["scripts"]
        and _launcher_located(distribution, path)
    )
    extra = sorted(
        path
        for path in installed
        if path not in expected
        and path not in launchers
        and not _installer_file(path)
        and _cache_entry(path) is None
    )
    problems.extend(f"{path}: installed but not in the wheel" for path in extra)
    sources = sorted(
        path
        for path, digest in expected.items()
        if digest is not None and path.endswith(".py") and not path.startswith("..")
    )
    bytecode = _verify_bytecode(distribution, sources, installed, cache_tag)
    problems.extend(bytecode["problems"])
    return {
        "wheel": wheel_path.name,
        "wheel_sha256": sha256_file(wheel_path),
        "archive_members_verified": archive["members_verified"],
        "files_verified": verified,
        "bytecode_verified": bytecode["verified"],
        "inert_bytecode": bytecode["inert"],
        "generated_launchers": launchers,
        "unexpected_installed_files": extra,
        "problems": problems,
    }
