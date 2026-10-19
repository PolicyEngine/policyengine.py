"""Tests for the identity of a dataset source.

A file derived from a dataset (such as a US year file) records
``dataset_source_identity(materialize_dataset(...))``, and a later request
compares it with ``requested_dataset_source_identity(...)``, which must not
download or read the source. These tests state the invariants that makes
safe, over a fixture bundle manifest whose datasets are tiny local files:

- **Agreement (differential).** For every way a dataset can be requested
  (the default, the default's URI, a bundle name, an explicit Hugging Face
  URI, a data release manifest name, and a local path given relative,
  absolute, with ``~`` or through a symlink), the identity of the request
  equals the identity of what ``materialize_dataset`` makes available.
- **Cheapness.** Identifying a request never downloads, opens, hashes or
  loads the source.
- **Sensitivity, bundle datasets.** A request's identity changes exactly
  when the bundle re-pins its entry (repository, path, revision or sha256),
  and not when any other entry changes.
- **Sensitivity, local files.** A local file's identity changes exactly when
  its resolved path, size or modification time changes. Bytes rewritten
  under the same size and modification time keep it: the intended blind spot
  of a ``stat()`` check, the quick check ``rsync`` makes by default.
- **Shapes.** Every identity produced has a shape
  ``is_dataset_source_identity`` accepts, and describing one never raises.
- **Checking again.** ``dataset_source_change`` reports a source file that
  is no longer the one snapshotted after materializing (device, inode, size
  or modification time), for every kind of source, and a bundle dataset's
  file whose bytes no longer hash to its verified sha256.
"""

from __future__ import annotations

import builtins
import hashlib
import io
import os
from pathlib import Path
from unittest.mock import patch

import h5py
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import policyengine.provenance.dataset_materialization as dataset_materialization
import policyengine.provenance.manifest as manifest_module
from policyengine.provenance.dataset_materialization import (
    dataset_source_change,
    dataset_source_identity,
    dataset_source_snapshot,
    describe_dataset_source_identity,
    is_dataset_source_identity,
    materialize_dataset,
    requested_dataset_source_identity,
)
from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    DataReleaseManifest,
    build_hf_uri,
)

DEFAULT_BYTES = b"default dataset"
OTHER_BYTES = b"other dataset, from another repository"
EXPLICIT_BYTES = b"explicit dataset"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest(**other_entry) -> CountryReleaseManifest:
    """A fixture US bundle: a default dataset and one from another repo."""
    other = {
        "path": "nested/tiny_other.h5",
        "repo_id": "fixture/other-repo",
        "repo_type": "dataset",
        "revision": "other-r9",
        "sha256": _sha256(OTHER_BYTES),
        **other_entry,
    }
    return CountryReleaseManifest.model_validate(
        {
            "country_id": "us",
            "policyengine_version": "0.0.0",
            "model_package": {"name": "policyengine-us", "version": "2.2.1"},
            "data_package": {
                "name": "fixture-data",
                "version": "0.1.0",
                "repo_id": "fixture/data",
                "repo_type": "model",
                "release_manifest_revision": "fixture-release",
            },
            "default_dataset": "tiny_default",
            "certified_data_artifact": {
                "dataset": "tiny_default",
                "uri": build_hf_uri("fixture/data", "tiny_default.h5", "r1"),
                "sha256": _sha256(DEFAULT_BYTES),
            },
            "datasets": {
                "tiny_default": {
                    "path": "tiny_default.h5",
                    "revision": "r1",
                    "sha256": _sha256(DEFAULT_BYTES),
                },
                "tiny_other": {key: value for key, value in other.items() if value},
            },
        }
    )


DATA_RELEASE = DataReleaseManifest.model_validate(
    {
        "schema_version": 1,
        "data_package": {"name": "fixture-data", "version": "0.1.0"},
        "artifacts": {
            "release_only": {
                "kind": "dataset",
                "path": "release_only.h5",
                "repo_id": "fixture/data",
                "revision": "release-r2",
            }
        },
    }
)


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.status_code = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.payload


def _serve(payload: bytes):
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return _Response(payload)

    return get, calls


def _refuse(*args, **kwargs):
    raise AssertionError("identifying a request downloaded or read its source")


def _with_manifest(manifest):
    """Patch every module that looks up the bundled US manifest."""
    return (
        patch.object(manifest_module, "get_release_manifest", lambda _: manifest),
        patch.object(
            dataset_materialization, "get_release_manifest", lambda _: manifest
        ),
        patch.object(
            manifest_module, "get_data_release_manifest", lambda _: DATA_RELEASE
        ),
    )


@pytest.fixture
def bundle(tmp_path):
    """The fixture bundle, with its datasets already on disk, verified."""
    manifest = _manifest()
    patchers = _with_manifest(manifest)
    for patcher in patchers:
        patcher.start()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "tiny_default.h5").write_bytes(DEFAULT_BYTES)
    (data_dir / "tiny_other.h5").write_bytes(OTHER_BYTES)
    try:
        yield manifest, data_dir
    finally:
        for patcher in patchers:
            patcher.stop()


def _local_file(tmp_path) -> Path:
    path = tmp_path / "sources" / "tiny_local.h5"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"local dataset")
    return path


#: Each way to request a dataset: (request, bytes served for a download).
#: ``{tmp}`` and ``{home}`` stand for the test's folders.
ROUTES = {
    "default": (None, None),
    "default URI": (build_hf_uri("fixture/data", "tiny_default.h5", "r1"), None),
    "bundle name": ("tiny_default", None),
    "bundle name in another repository": ("tiny_other", None),
    "explicit URI": ("hf://fixture/explicit/explicit.h5@pinned", EXPLICIT_BYTES),
    "explicit URI without a revision": (
        "hf://fixture/explicit/explicit.h5",
        EXPLICIT_BYTES,
    ),
    "explicit URI of a bundle dataset": (
        build_hf_uri("fixture/other-repo", "nested/tiny_other.h5", "other-r9"),
        OTHER_BYTES,
    ),
    "data release manifest name": ("release_only", EXPLICIT_BYTES),
    "absolute local path": ("{tmp}/sources/tiny_local.h5", None),
    "relative local path": ("sources/tiny_local.h5", None),
    "local path under ~": ("~/sources/tiny_local.h5", None),
    "symlinked local path": ("{tmp}/link.h5", None),
}


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_request_is_identified_as_what_it_materializes(
    bundle, tmp_path, monkeypatch, route
):
    """Agreement: identifying a request without materializing it gives the
    identity of what materializing it makes available."""
    _, data_dir = bundle
    _local_file(tmp_path)
    (tmp_path / "link.h5").symlink_to(tmp_path / "sources" / "tiny_local.h5")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    dataset, served = ROUTES[route]
    if dataset is not None:
        dataset = dataset.format(tmp=tmp_path)

    with (
        patch.object(dataset_materialization.requests, "get", _refuse),
        patch.object(dataset_materialization, "sha256_file", _refuse),
    ):
        requested = requested_dataset_source_identity("us", dataset)

    get, calls = _serve(served or b"")
    with patch.object(
        dataset_materialization.requests, "get", get if served else _refuse
    ):
        source = materialize_dataset(
            "us", dataset, allow_unmanaged=True, data_dir=data_dir
        )

    assert dataset_source_identity(source) == requested
    assert is_dataset_source_identity(requested)
    assert bool(calls) == bool(served)


def test_the_identities_of_each_route(bundle, tmp_path, monkeypatch):
    _local_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    local = tmp_path.resolve() / "sources" / "tiny_local.h5"
    status = local.stat()

    assert requested_dataset_source_identity("us") == {
        "uri": "hf://fixture/data/tiny_default.h5@r1",
        "sha256": _sha256(DEFAULT_BYTES),
    }
    assert requested_dataset_source_identity("us", "tiny_other") == {
        "uri": "hf://fixture/other-repo/nested/tiny_other.h5@other-r9",
        "sha256": _sha256(OTHER_BYTES),
    }
    # An explicit URI is not verified, even when it names a bundle dataset.
    assert requested_dataset_source_identity(
        "us", "hf://fixture/other-repo/nested/tiny_other.h5@other-r9"
    ) == {"uri": "hf://fixture/other-repo/nested/tiny_other.h5@other-r9"}
    assert requested_dataset_source_identity("us", "release_only") == {
        "uri": "hf://fixture/data/release_only.h5@release-r2"
    }
    assert requested_dataset_source_identity("us", "sources/tiny_local.h5") == {
        "path": str(local),
        "size": status.st_size,
        "mtime_ns": status.st_mtime_ns,
    }


def test_a_bundle_entry_without_a_revision_uses_the_release_revision():
    """It inherits the data package's repository and release revision, as
    ``_resolve_bundle_dataset`` does."""
    manifest = _manifest(revision=None, repo_id=None, repo_type=None)
    patchers = _with_manifest(manifest)
    with patchers[0], patchers[1], patchers[2]:
        assert requested_dataset_source_identity("us", "tiny_other") == {
            "uri": "hf://fixture/data/nested/tiny_other.h5@fixture-release",
            "sha256": _sha256(OTHER_BYTES),
        }


@pytest.mark.parametrize(
    "uri, error",
    [
        ("s3://bucket/x.h5", "Unsupported explicit dataset URI"),
        ("gs://bucket/x.h5", "Unsupported explicit dataset URI"),
        ("hf://owner/repo", "Invalid Hugging Face dataset URI"),
        ("hf://owner//x.h5@r", "Invalid Hugging Face dataset URI"),
    ],
)
def test_a_uri_materialize_refuses_is_refused_with_its_error(bundle, uri, error):
    _, data_dir = bundle

    with pytest.raises(dataset_materialization.DatasetMaterializationError) as early:
        requested_dataset_source_identity("us", uri)
    with patch.object(dataset_materialization.requests, "get", _refuse):
        with pytest.raises(
            dataset_materialization.DatasetMaterializationError
        ) as materializing:
            materialize_dataset("us", uri, allow_unmanaged=True, data_dir=data_dir)

    assert error in str(early.value)
    assert str(early.value) == str(materializing.value)


def test_a_bundle_entry_without_a_sha256_is_refused_as_materialize_does(tmp_path):
    manifest = _manifest()
    manifest.datasets["tiny_other"].sha256 = None
    patchers = _with_manifest(manifest)
    with patchers[0], patchers[1], patchers[2]:
        with pytest.raises(
            dataset_materialization.DatasetMaterializationError, match="sha256"
        ):
            requested_dataset_source_identity("us", "tiny_other")
        with pytest.raises(
            dataset_materialization.DatasetMaterializationError, match="sha256"
        ):
            materialize_dataset("us", "tiny_other", data_dir=tmp_path)


@pytest.mark.parametrize(
    "route",
    [
        "default",
        "bundle name",
        "explicit URI",
        "absolute local path",
        "relative local path",
    ],
)
def test_identifying_a_request_never_reads_the_source(
    bundle, tmp_path, monkeypatch, route
):
    """Cheapness: no download, no open, no hash, no H5 read of the source."""
    _, data_dir = bundle
    source = _local_file(tmp_path).resolve()
    monkeypatch.chdir(tmp_path)
    dataset, _ = ROUTES[route]
    if dataset is not None:
        dataset = dataset.format(tmp=tmp_path)
    real_open = builtins.open
    guarded = {source, (data_dir / "tiny_default.h5").resolve()}

    def open_anything_but_a_source(file, *args, **kwargs):
        if isinstance(file, (str, os.PathLike)) and Path(file).resolve() in guarded:
            _refuse()
        return real_open(file, *args, **kwargs)

    with (
        patch.object(builtins, "open", open_anything_but_a_source),
        patch.object(io, "open", open_anything_but_a_source),
        patch.object(h5py, "File", _refuse),
        patch.object(dataset_materialization, "sha256_file", _refuse),
        patch.object(dataset_materialization.requests, "get", _refuse),
    ):
        identity = requested_dataset_source_identity("us", dataset)

    assert is_dataset_source_identity(identity)


# --- Sensitivity ---------------------------------------------------------

REPOSITORIES = st.sampled_from([None, "fixture/other-repo", "fixture/third-repo"])
PATHS = st.sampled_from(["nested/tiny_other.h5", "tiny_other.h5"])
REVISIONS = st.sampled_from([None, "other-r9", "other-r10"])
SHA256S = st.sampled_from([_sha256(OTHER_BYTES), _sha256(b"replacement")])


@st.composite
def entries(draw):
    return {
        "repo_id": draw(REPOSITORIES),
        "path": draw(PATHS),
        "revision": draw(REVISIONS),
        "sha256": draw(SHA256S),
    }


def _identity_under(manifest, dataset):
    patchers = _with_manifest(manifest)
    with patchers[0], patchers[1], patchers[2]:
        return requested_dataset_source_identity("us", dataset)


@settings(max_examples=150, deadline=None)
@given(first=entries(), second=entries())
def test_a_bundle_dataset_is_re_identified_exactly_when_re_pinned(first, second):
    """Re-pinning the requested entry (its repository, path, revision or
    sha256) changes its identity, and only that does."""

    def pinned(entry):
        return (
            entry["repo_id"] or "fixture/data",
            entry["path"],
            entry["revision"] or "fixture-release",
            entry["sha256"],
        )

    first_identity = _identity_under(_manifest(**first), "tiny_other")
    second_identity = _identity_under(_manifest(**second), "tiny_other")

    assert (first_identity == second_identity) == (pinned(first) == pinned(second))
    # The default dataset's identity does not move with another entry.
    assert _identity_under(_manifest(**first), None) == _identity_under(
        _manifest(**second), None
    )


SECOND = 1_000_000_000
#: Whole seconds, so a file system that keeps only seconds still keeps them.
MTIMES = st.integers(1, 2**31).map(lambda seconds: seconds * SECOND)
CONTENTS = st.binary(min_size=0, max_size=4)


@settings(max_examples=150, deadline=None)
@given(
    first=CONTENTS,
    second=CONTENTS,
    first_mtime=MTIMES,
    second_mtime=MTIMES,
)
def test_a_local_file_is_re_identified_when_its_size_or_mtime_changes(
    tmp_path_factory, first, second, first_mtime, second_mtime
):
    """Sensitivity: identities differ exactly when size or mtime does. Equal
    size and mtime over other bytes give equal identities: intended."""
    path = tmp_path_factory.mktemp("local") / "tiny_local.h5"

    path.write_bytes(first)
    os.utime(path, ns=(first_mtime, first_mtime))
    first_identity = requested_dataset_source_identity("us", str(path))
    path.write_bytes(second)
    os.utime(path, ns=(second_mtime, second_mtime))
    second_identity = requested_dataset_source_identity("us", str(path))

    assert (first_identity == second_identity) == (
        len(first) == len(second) and first_mtime == second_mtime
    )
    assert first_identity["mtime_ns"] == first_mtime
    assert first_identity["size"] == len(first)


def test_a_local_file_elsewhere_is_another_source(tmp_path):
    """Two files with one name, so one year-file name, are told apart."""
    first, second = tmp_path / "a" / "tiny.h5", tmp_path / "b" / "tiny.h5"
    for path in (first, second):
        path.parent.mkdir()
        path.write_bytes(b"same bytes")
        os.utime(path, ns=(SECOND, SECOND))

    assert requested_dataset_source_identity(
        "us", str(first)
    ) != requested_dataset_source_identity("us", str(second))


def test_re_pointing_a_symlink_re_identifies_the_source(tmp_path):
    first, second, link = tmp_path / "v1.h5", tmp_path / "v2.h5", tmp_path / "x.h5"
    for path in (first, second):
        path.write_bytes(b"same bytes")
        os.utime(path, ns=(SECOND, SECOND))
    link.symlink_to(first)
    before = requested_dataset_source_identity("us", str(link))
    link.unlink()
    link.symlink_to(second)

    assert requested_dataset_source_identity("us", str(link)) != before
    assert before["path"] == str(first.resolve())


# --- Shapes ---------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        {"uri": "hf://a/b/c.h5@r", "sha256": "a" * 64},
        {"uri": "hf://a/b/c.h5"},
        {"path": "/a/c.h5", "size": 0, "mtime_ns": -1},
    ],
)
def test_the_three_shapes_are_identities(value):
    assert is_dataset_source_identity(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "hf://a/b/c.h5",
        [],
        {},
        {"uri": None},
        {"uri": "hf://a/b/c.h5", "sha256": None},
        {"uri": "hf://a/b/c.h5", "revision": "r"},
        {"path": "/a/c.h5", "size": True, "mtime_ns": 1},
        {"path": "/a/c.h5", "size": 1, "mtime_ns": 1.0},
        {"path": "/a/c.h5", "size": 1},
        {"path": 1, "size": 1, "mtime_ns": 1},
        {"path": "/a/c.h5", "size": 1, "mtime_ns": 1, "sha256": "a"},
    ],
)
def test_other_values_are_not_identities(value):
    assert not is_dataset_source_identity(value)


IDENTITIES = st.one_of(
    st.builds(lambda uri: {"uri": uri}, st.text()),
    st.builds(lambda uri, sha: {"uri": uri, "sha256": sha}, st.text(), st.text()),
    st.builds(
        lambda path, size, mtime_ns: {"path": path, "size": size, "mtime_ns": mtime_ns},
        st.text(),
        st.integers(),
        st.integers(),
    ),
)


@settings(max_examples=300, deadline=None)
@given(identity=IDENTITIES)
def test_describing_an_identity_is_total(identity):
    described = describe_dataset_source_identity(identity)

    assert isinstance(described, str)
    assert identity.get("uri", identity.get("path")) in described


@pytest.mark.parametrize(
    "identity, described",
    [
        ({"uri": "hf://a/b/c.h5@r"}, "hf://a/b/c.h5@r"),
        (
            {"uri": "hf://a/b/c.h5@r", "sha256": "f" * 64},
            f"hf://a/b/c.h5@r (sha256 {'f' * 64})",
        ),
        (
            {"path": "/a/c.h5", "size": 3, "mtime_ns": 1_760_000_000_123_456_789},
            "/a/c.h5 (3 bytes, modified 2025-10-09T08:53:20.123456789Z)",
        ),
        (
            {"path": "/a/c.h5", "size": 3, "mtime_ns": -1},
            "/a/c.h5 (3 bytes, modified 1969-12-31T23:59:59.999999999Z)",
        ),
        (
            {"path": "/a/c.h5", "size": 3, "mtime_ns": 10**30},
            f"/a/c.h5 (3 bytes, modified at {10**30} ns since the epoch)",
        ),
    ],
)
def test_an_identity_is_described_in_words(identity, described):
    assert describe_dataset_source_identity(identity) == described


# --- Checking a materialized source again --------------------------------


def _replace(path: Path, payload: bytes) -> None:
    """Replace a file as a download does: a new file renamed over it."""
    temporary = path.with_name(f".{path.name}.download")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _materialized(dataset, data_dir, served=None):
    """Materialize ``dataset``, dated well before anything replaces it."""
    get, _ = _serve(served or b"")
    with patch.object(
        dataset_materialization.requests, "get", get if served else _refuse
    ):
        source = materialize_dataset(
            "us", dataset, allow_unmanaged=True, data_dir=data_dir
        )
    # Materialized long ago, so a replacement made now has a later
    # modification time, whatever the file system's timestamp resolution.
    os.utime(source.path, ns=(SECOND, SECOND))
    return source, dataset_source_identity(source), dataset_source_snapshot(source)


def test_the_snapshot_is_the_files_size_and_mtime(bundle):
    """Not its device or inode, which some file systems do not keep stable."""
    _, data_dir = bundle
    source, _, snapshot = _materialized("tiny_default", data_dir)
    status = os.stat(source.path)

    assert snapshot == {"size": status.st_size, "mtime_ns": status.st_mtime_ns}


@pytest.mark.parametrize(
    "dataset, served",
    [
        ("tiny_default", None),
        ("hf://fixture/explicit/explicit.h5@pinned", EXPLICIT_BYTES),
        ("{tmp}/sources/tiny_local.h5", None),
    ],
)
def test_an_untouched_source_has_not_changed(bundle, tmp_path, dataset, served):
    _, data_dir = bundle
    _local_file(tmp_path)
    source, identity, snapshot = _materialized(
        dataset.format(tmp=tmp_path), data_dir, served
    )

    assert dataset_source_change(source, identity, snapshot) is None


@pytest.mark.parametrize(
    "dataset, served",
    [
        ("tiny_default", None),
        ("hf://fixture/explicit/explicit.h5@pinned", EXPLICIT_BYTES),
        ("{tmp}/sources/tiny_local.h5", None),
    ],
)
def test_a_source_replaced_after_its_snapshot_has_changed(
    bundle, tmp_path, dataset, served
):
    """Another process materializing another release, or another file with
    the same name, into the same folder. An explicit URI is caught too,
    although nothing verifies its contents."""
    _, data_dir = bundle
    _local_file(tmp_path)
    source, identity, snapshot = _materialized(
        dataset.format(tmp=tmp_path), data_dir, served
    )

    _replace(Path(source.path), b"another release")

    assert dataset_source_change(source, identity, snapshot) == (
        f"{source.path} was replaced or modified (its size or modification "
        "time changed)"
    )
    Path(source.path).unlink()
    assert dataset_source_change(source, identity, snapshot).endswith(
        "no longer exists"
    )


def test_a_bundle_file_swapped_out_and_back_has_changed(bundle):
    """Its bytes hash to the verified sha256 again, but it is not the file
    that was loaded: another release was materialized over it, then the
    pinned release downloaded again."""
    _, data_dir = bundle
    source, identity, snapshot = _materialized("tiny_default", data_dir)
    path = Path(source.path)

    _replace(path, b"another release")
    _replace(path, DEFAULT_BYTES)

    # The pinned release downloaded again has its bytes, but a modification
    # time of its own.
    assert _sha256(path.read_bytes()) == identity["sha256"]
    assert dataset_source_change(source, identity, snapshot) is not None


def test_a_bundle_file_replaced_before_its_snapshot_has_changed(bundle):
    """Replaced after verification but before the snapshot, so the snapshot
    matches; the sha256 does not."""
    _, data_dir = bundle
    source, identity, _ = _materialized("tiny_default", data_dir)
    _replace(Path(source.path), b"another release")
    snapshot = dataset_source_snapshot(source)

    assert dataset_source_change(source, identity, snapshot) == (
        f"{source.path} has sha256 {_sha256(b'another release')}, not the "
        f"verified {_sha256(DEFAULT_BYTES)}"
    )


def test_an_explicit_download_records_the_sha256_of_its_bytes(bundle):
    _, data_dir = bundle
    source, _, _ = _materialized(
        "hf://fixture/explicit/explicit.h5@pinned", data_dir, EXPLICIT_BYTES
    )

    assert source.downloaded_sha256 == _sha256(EXPLICIT_BYTES)
    assert Path(source.path).read_bytes() == EXPLICIT_BYTES


@pytest.mark.parametrize(
    "dataset, served, payload, kind",
    [
        ("tiny_default", None, DEFAULT_BYTES, "verified"),
        (
            "hf://fixture/explicit/explicit.h5@pinned",
            EXPLICIT_BYTES,
            EXPLICIT_BYTES,
            "downloaded",
        ),
    ],
)
def test_a_downloaded_file_replaced_within_one_timestamp_tick_has_changed(
    bundle, dataset, served, payload, kind
):
    """Same size, same modification time, other bytes: as when another
    download of the same size finishes within one tick of a coarse file
    system. The sha256 it was verified against, or downloaded with, catches
    it."""
    _, data_dir = bundle
    source, identity, snapshot = _materialized(dataset, data_dir, served)
    other = bytes(reversed(payload))
    assert len(other) == len(payload) and other != payload

    _replace(Path(source.path), other)
    os.utime(source.path, ns=(snapshot["mtime_ns"], snapshot["mtime_ns"]))

    assert dataset_source_snapshot(source) == snapshot
    assert dataset_source_change(source, identity, snapshot) == (
        f"{source.path} has sha256 {_sha256(other)}, not the {kind} {_sha256(payload)}"
    )


@settings(max_examples=100, deadline=None)
@given(other=st.binary(min_size=0, max_size=24), keep_mtime=st.booleans())
def test_a_replaced_explicit_download_has_changed_whatever_its_metadata(
    tmp_path_factory, other, keep_mtime
):
    """For a downloaded file, any other bytes are a change, even at the
    same size and modification time."""
    data_dir = tmp_path_factory.mktemp("data")
    get, _ = _serve(EXPLICIT_BYTES)
    with patch.object(dataset_materialization.requests, "get", get):
        source = materialize_dataset(
            "us",
            "hf://fixture/explicit/explicit.h5@pinned",
            allow_unmanaged=True,
            data_dir=data_dir,
        )
    os.utime(source.path, ns=(SECOND, SECOND))
    identity, snapshot = (
        dataset_source_identity(source),
        dataset_source_snapshot(source),
    )

    _replace(Path(source.path), other)
    if keep_mtime:
        os.utime(source.path, ns=(SECOND, SECOND))

    assert (dataset_source_change(source, identity, snapshot) is None) == (
        other == EXPLICIT_BYTES and keep_mtime
    )


def test_a_local_file_rewritten_before_its_snapshot_has_changed(tmp_path):
    """Its identity was read before the rewrite, the snapshot after."""
    path = _local_file(tmp_path)
    os.utime(path, ns=(SECOND, SECOND))
    source = materialize_dataset("us", str(path), allow_unmanaged=True)
    identity = dataset_source_identity(source)
    os.utime(path, ns=(2 * SECOND, 2 * SECOND))
    snapshot = dataset_source_snapshot(source)

    assert dataset_source_change(source, identity, snapshot) == (
        f"{describe_dataset_source_identity(identity)} is now "
        f"{describe_dataset_source_identity(requested_dataset_source_identity('us', str(path)))}"
    )


@settings(max_examples=100, deadline=None)
@given(
    first=CONTENTS,
    second=CONTENTS,
    first_mtime=MTIMES,
    second_mtime=MTIMES,
    replace=st.booleans(),
)
def test_a_local_source_has_changed_exactly_when_its_size_or_mtime_has(
    tmp_path_factory, first, second, first_mtime, second_mtime, replace
):
    """Rewritten in place or replaced: changed exactly when the size or the
    modification time moved. Other bytes restored to the same size and time
    are not noticed: the intended, documented gap."""
    path = tmp_path_factory.mktemp("local") / "tiny_local.h5"
    path.write_bytes(first)
    os.utime(path, ns=(first_mtime, first_mtime))
    source = materialize_dataset("us", str(path), allow_unmanaged=True)
    identity = dataset_source_identity(source)
    snapshot = dataset_source_snapshot(source)

    if replace:
        _replace(path, second)
    else:
        path.write_bytes(second)
    os.utime(path, ns=(second_mtime, second_mtime))

    assert (dataset_source_change(source, identity, snapshot) is None) == (
        len(first) == len(second) and first_mtime == second_mtime
    )
