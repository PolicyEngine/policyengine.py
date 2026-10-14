"""Installed files are verified byte for byte against a wheel's RECORD.

Invariants:

- an untouched install verifies, including the console-script launchers an
  installer generates for the wheel's declared entry points;
- mutating any single installed file, or installing a file the wheel lacks
  (a launcher it does not declare or that is not in a scripts directory
  outside the site directory, a stray ``.pyc`` or ``INSTALLER`` outside
  where installers write them), fails verification;
- bytecode this interpreter would load instead of a verified source (any
  optimisation level, listed in the RECORD or not, timestamp or hash based)
  verifies only when it compiles from that source; caches the interpreter
  would ignore are inert and reported, never failed;
- the wheel itself verifies only when its members and its RECORD match, with
  RECORD listing itself with empty hash and size fields, and the optional
  RECORD.jws and RECORD.p7s signatures absent from RECORD. Changing, adding
  or removing other archive members fails, so a copied RECORD in a junk zip
  never names a wheel the files did not come from.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import marshal
import math
import os
import sys
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
    verify_wheel_archive,
)

DIST_INFO = "policyengine_uk-2.126.8.dist-info"
FILES = {
    "policyengine_uk/__init__.py": b"VERSION = '2.126.8'\n",
    "policyengine_uk/system.py": b"system = object()\n",
    "policyengine_uk/parameters/rate.yaml": b"values:\n  2027-04-06: 0.2\n",
    f"{DIST_INFO}/entry_points.txt": (
        b"[console_scripts]\npolicyengine-uk = policyengine_uk.cli:main\n\n"
        b"[gui_scripts]\npolicyengine-uk-gui = policyengine_uk.gui:main\n\n"
        b"[policyengine.plugins]\nnot-a-script = policyengine_uk.plugin\n"
    ),
}
LAUNCHERS = {
    "../../../bin/policyengine-uk": b"#!/venv/bin/python\nimport policyengine_uk\n",
    "../../../bin/policyengine-uk-gui": b"#!/venv/bin/python\n",
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")


def _line(path: str, data: bytes) -> str:
    return f"{path},sha256={_b64(data)},{len(data)}"


def write_wheel(path: Path, members: dict, record_lines: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
        archive.writestr(f"{DIST_INFO}/RECORD", "\n".join(record_lines) + "\n")
    return path


def build_wheel(tmp_path: Path, files=FILES, launchers=LAUNCHERS):
    """A wheel, an installed copy of it, and the installed RECORD lines.

    The install adds what installers add: INSTALLER, REQUESTED and a launcher
    in ``bin`` for each console and GUI script the wheel declares.
    """

    record = [_line(path, data) for path, data in files.items()]
    record.append(f"{DIST_INFO}/RECORD,,")
    wheel = write_wheel(
        tmp_path / "policyengine_uk-2.126.8-py3-none-any.whl", files, record
    )
    site = tmp_path / "venv" / "lib" / "python3.13" / "site-packages"
    for path, data in {**files, **launchers}.items():
        (site / path).parent.mkdir(parents=True, exist_ok=True)
        (site / path).write_bytes(data)
    installed = (
        record
        + [_line(path, data) for path, data in launchers.items()]
        + [
            f"{DIST_INFO}/INSTALLER,sha256={_b64(b'uv')},2",
            f"{DIST_INFO}/REQUESTED,,",
        ]
    )
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
    assert evidence["archive_members_verified"] == len(FILES)
    assert evidence["generated_launchers"] == sorted(LAUNCHERS)
    assert evidence["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()


@pytest.mark.parametrize("origin", ["directory", "editable", "vcs"])
def test_verified_wheel_allows_certification_of_a_direct_install(
    tmp_path, monkeypatch, origin
):
    from policyengine.provenance import receipt

    wheel, site, record = build_wheel(tmp_path)
    fake = fake_metadata(site, record)
    distribution = fake.distribution("policyengine-uk")
    direct_url = {"url": "file:///source"}
    if origin == "vcs":
        direct_url["vcs_info"] = {"vcs": "git", "commit_id": "a" * 40}
    else:
        direct_url["dir_info"] = {"editable": origin == "editable"}
    import json

    distribution.read_text = lambda name: json.dumps(direct_url)
    fake.distribution = lambda name: distribution
    fake.version = lambda name: "2.126.8"
    monkeypatch.setattr(receipt, "metadata", fake)
    # This fixture verifies installed files without loading a country package.
    monkeypatch.delitem(sys.modules, "policyengine_uk", raising=False)
    unverified = receipt.installed_package_identity("policyengine-uk")
    assert unverified.install_origin == origin
    assert not receipt._package_can_be_certified(unverified)
    verified = receipt.installed_package_identity("policyengine-uk", wheel_path=wheel)
    assert verified.install_origin == origin
    assert verified.wheel_sha256_evidence == "installed_record_verified"
    assert verified.wheel_sha256 == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert receipt._package_can_be_certified(verified)


def test_windows_launchers_are_recognised(tmp_path):
    launchers = {
        "../../Scripts/policyengine-uk.exe": b"MZ",
        "../../Scripts/policyengine-uk-gui-script.pyw": b"import x\n",
    }
    wheel, site, record = build_wheel(tmp_path, launchers=launchers)
    evidence = verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=fake_metadata(site, record)
    )
    assert evidence["problems"] == []
    assert evidence["generated_launchers"] == sorted(launchers)


@pytest.mark.parametrize(
    "path",
    [
        "../../../bin/not-a-script",  # a plugin entry point, not a script
        "../../../bin/undeclared",
        "../../../share/policyengine-uk",  # declared name, not a scripts dir
        "bin/policyengine-uk",  # inside site-packages
        "../site-packages/policyengine_uk/bin/policyengine-uk",  # resolves inside
        "policyengine_uk/injected.pyc",  # not in __pycache__
        "policyengine_uk/INSTALLER",  # not in .dist-info
    ],
)
def test_files_installers_do_not_write_fail(tmp_path, path):
    wheel, site, record = build_wheel(tmp_path)
    (site / path).parent.mkdir(parents=True, exist_ok=True)
    (site / path).write_bytes(b"x")
    evidence = verify_installed_against_wheel(
        "policyengine-uk",
        wheel,
        metadata=fake_metadata(site, record + [_line(path, b"x")]),
    )
    assert evidence["problems"] == [f"{path}: installed but not in the wheel"]


TAG = sys.implementation.cache_tag


def _pyc(
    source: bytes, *, mtime: int, size: int, flags: int = 0, optimize: int = 0
) -> bytes:
    """Bytecode for ``source`` with a header claiming ``mtime`` and ``size``."""

    code = compile(source, "system.py", "exec", dont_inherit=True, optimize=optimize)
    if flags:
        middle = importlib.util.source_hash(source)
    else:
        middle = mtime.to_bytes(4, "little") + size.to_bytes(4, "little")
    return (
        importlib.util.MAGIC_NUMBER
        + flags.to_bytes(4, "little")
        + middle
        + marshal.dumps(code)
    )


def _cache_path(site: Path, optimization: str = "") -> Path:
    return Path(
        importlib.util.cache_from_source(
            str(site / "policyengine_uk/system.py"), optimization=optimization
        )
    )


def _write_cache(site: Path, compiled_from: bytes, **kwargs) -> Path:
    """Write a cache for ``system.py`` whose header matches the installed file."""

    optimization = kwargs.pop("optimization", "")
    source = site / "policyengine_uk/system.py"
    stat = source.stat()
    path = _cache_path(site, optimization)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        _pyc(
            compiled_from,
            mtime=kwargs.pop("mtime", int(stat.st_mtime)),
            size=kwargs.pop("size", stat.st_size),
            optimize=int(optimization or 0),
            **kwargs,
        )
    )
    return path


def _verify(site, wheel, record, **kwargs):
    return verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=fake_metadata(site, record), **kwargs
    )


def _relative(site: Path, path: Path) -> str:
    return path.relative_to(site).as_posix()


SYSTEM = FILES["policyengine_uk/system.py"]
TAMPERED = b"import os\nsystem = os.system('x')\n"


@pytest.mark.parametrize("listed", [False, True], ids=["unlisted", "listed"])
@pytest.mark.parametrize("optimization", ["", "1", "2"])
def test_bytecode_compiled_from_the_source_verifies(tmp_path, listed, optimization):
    wheel, site, record = build_wheel(tmp_path)
    path = _write_cache(site, SYSTEM, optimization=optimization)
    if listed:
        record = record + [_line(_relative(site, path), path.read_bytes())]
    evidence = _verify(site, wheel, record)
    assert evidence["problems"] == []
    assert evidence["bytecode_verified"] == 1


@pytest.mark.parametrize("optimization", ["", "1", "2"])
def test_each_cache_is_compared_at_its_own_optimisation_level(tmp_path, optimization):
    """-O drops asserts and -OO docstrings, so each level compiles differently."""

    source = b'"""Docstring."""\nassert True\nsystem = object()\n'
    files = {**FILES, "policyengine_uk/system.py": source}
    wheel, site, record = build_wheel(tmp_path, files=files)
    _write_cache(site, source, optimization=optimization)
    evidence = _verify(site, wheel, record)
    assert evidence["problems"] == []
    assert evidence["bytecode_verified"] == 1
    for other in {"", "1", "2"} - {optimization}:
        _cache_path(site, optimization).rename(_cache_path(site, other))
        problems = _verify(site, wheel, record)["problems"]
        assert problems and "does not compile" in problems[0]
        _cache_path(site, other).rename(_cache_path(site, optimization))


@pytest.mark.parametrize("listed", [False, True], ids=["unlisted", "listed"])
@pytest.mark.parametrize(
    ("optimization", "flags"),
    [("", 0), ("1", 0), ("2", 0), ("", 0b01), ("", 0b11)],
    ids=["timestamp", "opt-1", "opt-2", "unchecked-hash", "checked-hash"],
)
def test_bytecode_that_would_run_instead_of_the_source_fails(
    tmp_path, listed, optimization, flags
):
    """Round-4 review H1: a planted cache runs, so it must be the wheel's code."""

    wheel, site, record = build_wheel(tmp_path)
    path = _write_cache(site, TAMPERED, optimization=optimization, flags=flags)
    if listed:
        record = record + [_line(_relative(site, path), path.read_bytes())]
    problems = _verify(site, wheel, record)["problems"]
    assert len(problems) == 1
    assert "does not compile from the verified source" in problems[0]


def test_a_timestamp_cache_with_the_check_source_bit_is_still_compared(tmp_path):
    """Round-5 review: importlib reads flags 2 as a timestamp cache."""

    wheel, site, record = build_wheel(tmp_path)
    path = _write_cache(site, TAMPERED, flags=0)
    data = bytearray(path.read_bytes())
    data[4:8] = (2).to_bytes(4, "little")
    path.write_bytes(bytes(data))
    problems = _verify(site, wheel, record)["problems"]
    assert problems == [
        f"{_relative(site, path)}: does not compile from the verified source"
    ]


def test_a_cache_with_unknown_header_flags_is_inert(tmp_path):
    """importlib refuses flag bits beyond 0b11 and compiles the source."""

    wheel, site, record = build_wheel(tmp_path)
    path = _write_cache(site, TAMPERED)
    data = bytearray(path.read_bytes())
    data[4:8] = (0b100).to_bytes(4, "little")
    path.write_bytes(bytes(data))
    evidence = _verify(site, wheel, record)
    assert evidence["problems"] == []
    assert evidence["inert_bytecode"] == [
        f"{_relative(site, path)}: unknown header flags"
    ]


def _with_nan_sign_flipped(code):
    return code.replace(
        co_consts=tuple(
            -constant
            if isinstance(constant, float) and math.isnan(constant)
            else constant
            for constant in code.co_consts
        )
    )


def test_a_cache_whose_nan_constant_has_the_other_sign_fails(tmp_path):
    """Round-6 review H1: float.hex() writes both signs of NaN as "nan"."""

    source = b"import math\nvalue = 1e999 - 1e999\nsystem = math.copysign(1.0, value)\n"
    files = {**FILES, "policyengine_uk/system.py": source}
    wheel, site, record = build_wheel(tmp_path, files=files)
    path = _write_cache(site, source)
    code = compile(source, "system.py", "exec", dont_inherit=True, optimize=0)
    assert any(isinstance(c, float) and math.isnan(c) for c in code.co_consts)
    namespace: dict = {}
    exec(_with_nan_sign_flipped(code), namespace)
    assert namespace["system"] == -1.0  # it behaves differently
    data = path.read_bytes()
    path.write_bytes(data[:16] + marshal.dumps(_with_nan_sign_flipped(code)))
    problems = _verify(site, wheel, record)["problems"]
    assert problems == [
        f"{_relative(site, path)}: does not compile from the verified source"
    ]


def test_a_stale_cache_with_the_check_source_bit_is_inert(tmp_path):
    """Flags 2 is timestamp-based: a stale one is ignored, not compared."""

    wheel, site, record = build_wheel(tmp_path)
    path = _write_cache(site, TAMPERED, mtime=12345)
    data = bytearray(path.read_bytes())
    data[4:8] = (2).to_bytes(4, "little")
    path.write_bytes(bytes(data))
    evidence = _verify(site, wheel, record)
    assert evidence["problems"] == []
    assert evidence["inert_bytecode"] == [f"{_relative(site, path)}: stale timestamp"]


def test_a_cache_linked_from_two_sources_must_match_each(tmp_path):
    """Round-5 review: one cache standing for two sources is checked for both.

    Two wheel sources of equal length and modification time but different
    code share one cache through a link; the interpreter would run the
    first's code for both.
    """

    other = b"system = 'abcdef'\n"
    assert len(other) == len(SYSTEM)
    files = {**FILES, "policyengine_uk/other.py": other}
    wheel, site, record = build_wheel(tmp_path, files=files)
    first = site / "policyengine_uk/other.py"  # checked first (sorted)
    second = site / "policyengine_uk/system.py"
    stat = first.stat()
    os.utime(second, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    cache = Path(importlib.util.cache_from_source(str(first)))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(_pyc(other, mtime=int(stat.st_mtime), size=stat.st_size))
    linked = Path(importlib.util.cache_from_source(str(second)))
    linked.symlink_to(cache.name)
    problems = _verify(site, wheel, record)["problems"]
    assert problems == [
        f"{_relative(site, linked)}: does not compile from the verified source"
    ]


def test_an_unreadable_cache_is_inert(tmp_path):
    """Round-5 review: the interpreter ignores a cache it cannot read."""

    wheel, site, record = build_wheel(tmp_path)
    path = _write_cache(site, TAMPERED)
    path.chmod(0)
    try:
        evidence = _verify(site, wheel, record)
    finally:
        path.chmod(0o644)
    if os.geteuid() == 0:  # pragma: no cover - root can read anything
        pytest.skip("root reads unreadable files")
    assert evidence["problems"] == []
    assert any("unreadable" in item for item in evidence["inert_bytecode"])


def test_bytecode_the_interpreter_would_ignore_is_inert(tmp_path):
    wheel, site, record = build_wheel(tmp_path)
    stale = _write_cache(site, TAMPERED, mtime=12345)
    foreign = site / "policyengine_uk/__pycache__/system.cpython-27.pyc"
    foreign.write_bytes(b"anything")
    record = record + [_line(_relative(site, foreign), b"anything")]
    evidence = _verify(site, wheel, record)
    assert evidence["problems"] == []
    assert evidence["bytecode_verified"] == 0
    assert evidence["inert_bytecode"] == [
        f"{_relative(site, foreign)}: another interpreter's cache",
        f"{_relative(site, stale)}: stale timestamp",
    ]


def test_a_listed_cache_of_a_file_the_wheel_lacks_fails(tmp_path):
    wheel, site, record = build_wheel(tmp_path)
    path = f"policyengine_uk/__pycache__/injected.{TAG}.pyc"
    (site / path).parent.mkdir(parents=True, exist_ok=True)
    (site / path).write_bytes(b"pyc")
    problems = _verify(site, wheel, record + [_line(path, b"pyc")])["problems"]
    assert problems == [
        f"{path}: caches policyengine_uk/injected.py, which is not in the wheel"
    ]


def test_unreadable_bytecode_fails(tmp_path):
    wheel, site, record = build_wheel(tmp_path)
    path = _write_cache(site, SYSTEM)
    path.write_bytes(path.read_bytes()[:16] + b"\xff\x00garbage")
    problems = _verify(site, wheel, record)["problems"]
    assert problems == [f"{_relative(site, path)}: unreadable bytecode"]


def test_bytecode_under_a_pycache_prefix_is_checked(tmp_path, monkeypatch):
    wheel, site, record = build_wheel(tmp_path)
    monkeypatch.setattr(sys, "pycache_prefix", str(tmp_path / "prefix"))
    path = _write_cache(site, TAMPERED)
    assert str(path).startswith(str(tmp_path / "prefix"))
    problems = _verify(site, wheel, record)["problems"]
    assert problems == [f"{path}: does not compile from the verified source"]


def test_without_a_cache_tag_only_listed_caches_are_classified(tmp_path):
    wheel, site, record = build_wheel(tmp_path)
    _write_cache(site, TAMPERED)
    evidence = _verify(site, wheel, record, cache_tag=None)
    assert evidence["problems"] == []


@settings(max_examples=25, deadline=None)
@given(
    source=st.sampled_from(
        [
            b"system = object()\n",
            b"system = object() \n",  # same code, different bytes
            b"system = 1\n",
            b"system = object\n",
            b"def system():\n    return 1\n",
            b"def system():\n    return 2\n",
        ]
    )
)
def test_cache_verifies_exactly_when_it_compiles_to_the_same_code(
    tmp_path_factory, source
):
    """Differential: the verdict equals comparing the two compiled modules."""

    wheel, site, record = build_wheel(tmp_path_factory.mktemp("cache"))
    _write_cache(site, source)
    same = marshal.dumps(
        compile(source, "x", "exec", dont_inherit=True)
    ) == marshal.dumps(compile(SYSTEM, "x", "exec", dont_inherit=True))
    assert (_verify(site, wheel, record)["problems"] == []) == same


def test_a_listed_launcher_missing_on_disk_is_not_exempt(tmp_path):
    """Round-4 review L9: a launcher is exempt only where it actually is."""

    wheel, site, record = build_wheel(tmp_path)
    (site / "../../../bin/policyengine-uk").unlink()
    problems = _verify(site, wheel, record)["problems"]
    assert problems == ["../../../bin/policyengine-uk: installed but not in the wheel"]


def test_a_junk_wheel_with_a_copied_record_does_not_verify(tmp_path):
    """Round-2 review N4: the RECORD alone proves nothing about the archive."""

    wheel, site, record = build_wheel(tmp_path)
    junk = write_wheel(
        tmp_path / "junk-2.126.8-py3-none-any.whl",
        {"policyengine_uk/__init__.py": b"import os; os.system('x')\n"},
        [line for line in record if line.split(",")[0] in FILES or "RECORD" in line],
    )
    evidence = verify_installed_against_wheel(
        "policyengine-uk", junk, metadata=fake_metadata(site, record)
    )
    assert any(
        "bytes differ from the wheel's RECORD" in p for p in evidence["problems"]
    )
    assert any("not in the wheel" in p for p in evidence["problems"])


ARCHIVE_EDITS = ["change", "add", "remove", "unhash", "hash record"]


@settings(max_examples=40, deadline=None)
@given(
    edit=st.sampled_from(ARCHIVE_EDITS),
    index=st.integers(0, len(FILES) - 1),
    extra=st.binary(min_size=1, max_size=8),
)
def test_any_edit_to_the_archive_fails(tmp_path_factory, edit, index, extra):
    directory = tmp_path_factory.mktemp("archive")
    members = dict(FILES)
    record = [_line(path, data) for path, data in FILES.items()]
    record.append(f"{DIST_INFO}/RECORD,,")
    target = list(FILES)[index]
    if edit == "change":
        members[target] = members[target] + extra
    elif edit == "add":
        members["policyengine_uk/smuggled.py"] = extra
    elif edit == "remove":
        del members[target]
    elif edit == "unhash":
        record[index] = f"{target},,"
    elif edit == "hash record":
        record[-1] = f"{DIST_INFO}/RECORD,sha256={_b64(extra)},{len(extra)}"
    wheel = write_wheel(directory / "w-1-py3-none-any.whl", members, record)
    assert verify_wheel_archive(wheel)["problems"]


def test_a_duplicated_member_fails(tmp_path):
    import warnings

    record = [_line(path, data) for path, data in FILES.items()]
    record.append(f"{DIST_INFO}/RECORD,,")
    wheel = tmp_path / "w-1-py3-none-any.whl"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # zipfile warns about the duplicate
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, data in FILES.items():
                archive.writestr(name, data)
            archive.writestr("policyengine_uk/system.py", b"system = object()\n")
            archive.writestr(f"{DIST_INFO}/RECORD", "\n".join(record) + "\n")
    problems = verify_wheel_archive(wheel)["problems"]
    assert "policyengine_uk/system.py: the wheel holds it twice" in problems


def test_an_untouched_archive_verifies(tmp_path):
    wheel, _, _ = build_wheel(tmp_path)
    archive = verify_wheel_archive(wheel)
    assert archive["problems"] == []
    assert archive["members_verified"] == len(FILES)
    assert archive["scripts"] == {"policyengine-uk", "policyengine-uk-gui"}


@pytest.mark.parametrize("signature", [None, "RECORD.jws", "RECORD.p7s"])
def test_record_must_list_itself(tmp_path, signature):
    members = dict(FILES)
    if signature is not None:
        members[f"{DIST_INFO}/{signature}"] = b"signature"
    record = [_line(path, data) for path, data in FILES.items()]
    wheel = write_wheel(tmp_path / "w-1-py3-none-any.whl", members, record)
    assert verify_wheel_archive(wheel)["problems"] == [
        f"{DIST_INFO}/RECORD: RECORD does not list itself"
    ]


@pytest.mark.parametrize(
    "fields",
    ["", ",", ",0", f"sha256={_b64(b'not RECORD')},", ",,extra"],
)
def test_record_self_entry_needs_empty_hash_and_size(tmp_path, fields):
    record = [_line(path, data) for path, data in FILES.items()]
    record.append(f"{DIST_INFO}/RECORD,{fields}")
    wheel = write_wheel(tmp_path / "w-1-py3-none-any.whl", FILES, record)
    if fields == ",":
        assert verify_wheel_archive(wheel)["problems"] == []
    else:
        assert verify_wheel_archive(wheel)["problems"] == [
            f"{DIST_INFO}/RECORD: RECORD needs empty hash and size fields"
        ]


@pytest.mark.parametrize("signature", ["RECORD.jws", "RECORD.p7s"])
@pytest.mark.parametrize("listed", [None, "unhashed", "hashed"])
def test_record_signatures_are_absent_from_record(tmp_path, signature, listed):
    path = f"{DIST_INFO}/{signature}"
    data = b"signature"
    members = {**FILES, path: data}
    record = [_line(path, data) for path, data in FILES.items()]
    record.append(f"{DIST_INFO}/RECORD,,")
    if listed is not None:
        record.append(_line(path, data) if listed == "hashed" else f"{path},,")
    wheel = write_wheel(tmp_path / "w-1-py3-none-any.whl", members, record)
    assert verify_wheel_archive(wheel)["problems"] == (
        [] if listed is None else [f"{path}: signature files must not be in RECORD"]
    )


def test_a_wheel_needs_exactly_one_record(tmp_path):
    wheel = tmp_path / "w-1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("x.py", b"x")
    with pytest.raises(ValueError, match="0 RECORD"):
        verify_wheel_archive(wheel)
    with pytest.raises(ValueError, match="twice"):
        parse_record("a.py,,\na.py,,\n")


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


def test_an_installed_record_that_differs_from_the_wheel_is_reported(tmp_path):
    """Round-9 review: the installed RECORD must list the wheel's digests even
    when the bytes on disk still match the wheel."""

    wheel, site, record = build_wheel(tmp_path)
    path = "policyengine_uk/system.py"
    edited = [
        _line(path, b"something else") if line.startswith(f"{path},") else line
        for line in record
    ]
    problems = _verify(site, wheel, edited)["problems"]
    assert problems == [f"{path}: installed RECORD differs from the wheel"]
