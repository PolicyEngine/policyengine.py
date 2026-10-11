"""Installed files are verified byte for byte against a wheel's RECORD.

Invariants:

- an untouched install verifies, including the console-script launchers an
  installer generates for the wheel's declared entry points;
- mutating any single installed file, or installing a file the wheel lacks
  (a launcher it does not declare, a stray ``.pyc`` or ``INSTALLER`` outside
  where installers write them), fails verification;
- the wheel itself verifies only when its members and its RECORD match one to
  one: changing, adding or removing any archive member fails, so a copied
  RECORD in a junk zip never names a wheel the files did not come from.
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


def test_compiled_bytecode_in_pycache_is_allowed(tmp_path):
    wheel, site, record = build_wheel(tmp_path)
    path = "policyengine_uk/__pycache__/system.cpython-313.pyc"
    (site / path).parent.mkdir(parents=True, exist_ok=True)
    (site / path).write_bytes(b"pyc")
    evidence = verify_installed_against_wheel(
        "policyengine-uk",
        wheel,
        metadata=fake_metadata(site, record + [_line(path, b"pyc")]),
    )
    assert evidence["problems"] == []


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


def test_an_untouched_archive_verifies(tmp_path):
    wheel, _, _ = build_wheel(tmp_path)
    archive = verify_wheel_archive(wheel)
    assert archive["problems"] == []
    assert archive["members_verified"] == len(FILES)
    assert archive["scripts"] == {"policyengine-uk", "policyengine-uk-gui"}


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
