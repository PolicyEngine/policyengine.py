"""UK year files are never reused after a re-pin, an edited source or an upgrade.

These tests run ``create_datasets``, ``ensure_datasets`` and ``load_datasets``
over a real policyengine-uk engine, on the seven-person 2024 dataset of
``test_uk_year_file_data_year.py``. Each replays one way a UK year file could
be reused although it holds data cut from something else:

- the bundle re-pins a logical dataset name to another revision and sha256
  (as releases of ``enhanced_frs_2024_25`` or ``populace_uk_2023`` do);
- a local source is rewritten in place;
- policyengine-uk or policyengine-core is upgraded;
- the source is replaced while the year files are cut;
- year files were cut by an earlier release, before the stamp existed.

In each case ``load_datasets`` refuses the old year files, naming what
changed, and ``ensure_datasets`` cuts them again from the source it resolves
to now, and then reuses them. ``test_uk_year_file_stamp.py`` states the
check's invariants without an engine.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import patch

import h5py
import pandas as pd
import pytest

pytest.importorskip("policyengine_uk")

import policyengine.provenance.dataset_materialization as dataset_materialization  # noqa: E402
import policyengine.provenance.manifest as manifest_module  # noqa: E402
from policyengine.provenance.dataset_materialization import (  # noqa: E402
    DatasetMaterializationError,
    describe_dataset_source_identity,
    requested_dataset_source_identity,
)
from policyengine.provenance.manifest import (  # noqa: E402
    ArtifactPathReference,
    get_release_manifest,
)
from policyengine.provenance.year_file_stamp import (  # noqa: E402
    YEAR_FILE_STAMP_H5_DATASET,
    read_year_file_stamp,
)
from policyengine.tax_benefit_models.uk import datasets as uk_datasets  # noqa: E402
from policyengine.tax_benefit_models.uk.datasets import (  # noqa: E402
    create_datasets,
    ensure_datasets,
    installed_package_versions,
    load_datasets,
    year_file_stamp,
    year_file_stamp_problem,
)
from policyengine.utils.hashing import sha256_file  # noqa: E402
from tests.test_uk_year_file_data_year import (  # noqa: E402
    DATA_YEAR,
    _tables,
    _write_source,
)

YEAR = 2026
#: Reported State Pension of the replacement source: every amount differs
#: from ``_tables()``'s.
REPLACED = (11_000.0, 9_500.0, 15_000.0, 12_500.0, 0.0, 0.0, 4_000.0)


def _replacement_tables() -> dict[str, pd.DataFrame]:
    return _tables(reported=REPLACED)


def _reported(dataset) -> list[float]:
    """The data year's reported State Pension, as stored in a year file."""
    observed = dataset.data_year_data if dataset.year > DATA_YEAR else dataset.data
    return pd.DataFrame(observed.person)["state_pension_reported"].tolist()


def _ensure(source: str, data_folder: Path, years=(YEAR,)):
    return ensure_datasets(
        datasets=[source],
        years=list(years),
        data_folder=str(data_folder),
        allow_unmanaged=True,
    )


def _assert_reused(source: str, data_folder: Path, years=(YEAR,)):
    """A current year file is loaded, never cut again."""

    def refuse(*args, **kwargs):
        raise AssertionError("a current year file was cut again")

    with patch.object(uk_datasets, "create_datasets", refuse):
        return _ensure(source, data_folder, years)


def _assert_cut_again(source: str, data_folder: Path, years=(YEAR,)):
    """An out-of-date year file is cut again, once."""
    with patch.object(
        uk_datasets, "create_datasets", wraps=uk_datasets.create_datasets
    ) as create:
        ensured = _ensure(source, data_folder, years)
    create.assert_called_once()
    return ensured


def _new_source(tmp_path: Path) -> str:
    """Write the tiny 2024 dataset as a local source."""
    folder = tmp_path / "sources"
    folder.mkdir()
    return _write_source(folder / "tiny_uk_2024.h5")


def test_create_stamps_each_year_file_with_its_source_and_packages(tmp_path):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"

    created = create_datasets(
        datasets=[source],
        years=[DATA_YEAR, YEAR],
        data_folder=str(data_folder),
        allow_unmanaged=True,
    )

    identity = requested_dataset_source_identity("uk", source)
    status = Path(source).resolve().stat()
    assert identity == {
        "path": str(Path(source).resolve()),
        "size": status.st_size,
        "mtime_ns": status.st_mtime_ns,
    }
    for year in (DATA_YEAR, YEAR):
        path = created[f"tiny_uk_2024_{year}"].filepath
        assert read_year_file_stamp(path) == {
            "packages": installed_package_versions(),
            "revision": 1,
            "source": identity,
        }
        assert read_year_file_stamp(path) == year_file_stamp(identity)
        assert year_file_stamp_problem(path, identity) is None
    # The real versions, not a fixture's.
    assert all(installed_package_versions().values())

    reused = _assert_reused(source, data_folder, (DATA_YEAR, YEAR))
    assert reused[f"tiny_uk_2024_{YEAR}"].data_year == DATA_YEAR
    assert _reported(reused[f"tiny_uk_2024_{YEAR}"]) == list(
        _tables()["person"]["state_pension_reported"]
    )


def test_an_edited_local_source_cuts_its_year_files_again(tmp_path):
    """The smoke-test workflow: rewrite a local dataset in place."""
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    first = _ensure(source, data_folder)
    old = requested_dataset_source_identity("uk", source)
    assert _reported(first[f"tiny_uk_2024_{YEAR}"]) == list(
        _tables()["person"]["state_pension_reported"]
    )

    _write_source(Path(source), _replacement_tables())
    # A modification time of its own, whatever the file system's resolution.
    os.utime(source, ns=(old["mtime_ns"] + 10**9, old["mtime_ns"] + 10**9))
    new = requested_dataset_source_identity("uk", source)
    assert new != old

    path = data_folder / f"tiny_uk_2024_year_{YEAR}.h5"
    reason = (
        f"it was cut from {describe_dataset_source_identity(old)}, and the "
        f"requested source is {describe_dataset_source_identity(new)}"
    )
    assert year_file_stamp_problem(path, new) == reason
    with pytest.raises(ValueError, match=re.escape(reason)):
        load_datasets(datasets=[source], years=[YEAR], data_folder=str(data_folder))

    second = _assert_cut_again(source, data_folder)
    assert _reported(second[f"tiny_uk_2024_{YEAR}"]) == list(REPLACED)
    assert read_year_file_stamp(path)["source"] == new
    reloaded = _assert_reused(source, data_folder)
    assert _reported(reloaded[f"tiny_uk_2024_{YEAR}"]) == list(REPLACED)


@pytest.mark.parametrize("package", ["policyengine-uk", "policyengine-core"])
def test_a_package_upgrade_cuts_the_year_files_again(tmp_path, monkeypatch, package):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    _ensure(source, data_folder)
    cut_with = installed_package_versions()

    monkeypatch.setattr(
        uk_datasets,
        "installed_package_versions",
        lambda: {**cut_with, package: "999.0.0"},
    )
    reason = (
        f"it was cut with {package} {cut_with[package]}, and {package} 999.0.0 "
        "is installed"
    )
    with pytest.raises(ValueError, match=re.escape(reason)):
        load_datasets(datasets=[source], years=[YEAR], data_folder=str(data_folder))

    _assert_cut_again(source, data_folder)
    path = data_folder / f"tiny_uk_2024_year_{YEAR}.h5"
    assert read_year_file_stamp(path)["packages"][package] == "999.0.0"
    _assert_reused(source, data_folder)


BUNDLE_NAME = "tiny_uk_bundle"
BUNDLE_URI = f"hf://fixture/tiny-uk-bundle/{BUNDLE_NAME}.h5"


def _pinned(revision: str, sha256: str):
    """Patch the bundled UK manifest to pin ``BUNDLE_NAME`` as given, and
    refuse every download: a verified copy is already in the data folder."""
    manifest = get_release_manifest("uk").model_copy(deep=True)
    manifest.datasets[BUNDLE_NAME] = ArtifactPathReference(
        path=f"{BUNDLE_NAME}.h5",
        repo_id="fixture/tiny-uk-bundle",
        repo_type="dataset",
        revision=revision,
        sha256=sha256,
    )

    def refuse(*args, **kwargs):
        raise AssertionError("a bundle dataset was downloaded")

    return (
        patch.object(manifest_module, "get_release_manifest", lambda _: manifest),
        patch.object(
            dataset_materialization, "get_release_manifest", lambda _: manifest
        ),
        patch.object(dataset_materialization.requests, "get", refuse),
    )


def test_a_re_pinned_bundle_dataset_cuts_its_year_files_again(tmp_path):
    """A release of a UK dataset in miniature: the bundle points a logical
    name at a new revision and sha256, and year files cut from the old
    release are not reused, although their names are unchanged."""
    data_folder = tmp_path / "data"
    data_folder.mkdir()
    # ``materialize_dataset`` keeps a verified copy at the artifact's name in
    # the data folder, and downloads only when that copy's sha256 differs.
    bundled = data_folder / f"{BUNDLE_NAME}.h5"
    _write_source(bundled)
    old_sha256 = sha256_file(bundled)
    old = {"uri": f"{BUNDLE_URI}@release-1", "sha256": old_sha256}
    path = data_folder / f"{BUNDLE_NAME}_year_{YEAR}.h5"

    first, second, third = _pinned("release-1", old_sha256)
    with first, second, third:
        ensured = ensure_datasets(
            datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
        )
        assert ensured[f"{BUNDLE_NAME}_{YEAR}"].filepath == str(path)
        assert read_year_file_stamp(path)["source"] == old
        assert requested_dataset_source_identity("uk", BUNDLE_NAME) == old

        def refuse(*args, **kwargs):
            raise AssertionError("a current year file was cut again")

        with patch.object(uk_datasets, "create_datasets", refuse):
            ensure_datasets(
                datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
            )

    # The new release reports other State Pension amounts; its verified copy
    # replaces the old one, as a download would.
    _write_source(bundled, _replacement_tables())
    new_sha256 = sha256_file(bundled)
    assert new_sha256 != old_sha256

    first, second, third = _pinned("release-2", new_sha256)
    with first, second, third:
        reason = (
            f"it was cut from {BUNDLE_URI}@release-1 (sha256 {old_sha256}), and "
            f"the requested source is {BUNDLE_URI}@release-2 (sha256 {new_sha256})"
        )
        assert (
            year_file_stamp_problem(
                path, requested_dataset_source_identity("uk", BUNDLE_NAME)
            )
            == reason
        )
        with pytest.raises(ValueError, match=re.escape(reason)):
            load_datasets(
                datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
            )
        with patch.object(
            uk_datasets, "create_datasets", wraps=uk_datasets.create_datasets
        ) as create:
            recut = ensure_datasets(
                datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
            )
        create.assert_called_once()
        assert _reported(recut[f"{BUNDLE_NAME}_{YEAR}"]) == list(REPLACED)
        assert read_year_file_stamp(path)["source"] == {
            "uri": f"{BUNDLE_URI}@release-2",
            "sha256": new_sha256,
        }


def test_a_source_replaced_while_cut_leaves_the_year_files_unstamped(tmp_path):
    """Another process replaces the source while the year files are cut, so
    no stamp may claim they were cut from what is there now."""
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    original = Path(source).stat().st_mtime_ns
    save = uk_datasets.PolicyEngineUKDataset.save

    def save_then_replace_the_source(self):
        save(self)
        _write_source(Path(source), _replacement_tables())
        os.utime(source, ns=(original + 10**9, original + 10**9))

    with patch.object(
        uk_datasets.PolicyEngineUKDataset, "save", save_then_replace_the_source
    ):
        with pytest.raises(DatasetMaterializationError) as raised:
            create_datasets(
                datasets=[source],
                years=[DATA_YEAR, YEAR],
                data_folder=str(data_folder),
                allow_unmanaged=True,
            )

    assert "changed while they were cut" in str(raised.value)
    assert "They were left unstamped" in str(raised.value)
    for year in (DATA_YEAR, YEAR):
        path = data_folder / f"tiny_uk_2024_year_{year}.h5"
        assert path.exists()
        assert read_year_file_stamp(path) is None
    # Cut again, from the replacement, and stamped with its identity.
    recut = _assert_cut_again(source, data_folder, (DATA_YEAR, YEAR))
    assert _reported(recut[f"tiny_uk_2024_{YEAR}"]) == list(REPLACED)
    assert read_year_file_stamp(data_folder / f"tiny_uk_2024_year_{YEAR}.h5")[
        "source"
    ] == requested_dataset_source_identity("uk", source)


def test_year_files_from_an_earlier_release_are_cut_again_once(tmp_path):
    """Year files cut before the stamp record their data year but no stamp."""
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    _ensure(source, data_folder, (DATA_YEAR, YEAR))
    for year in (DATA_YEAR, YEAR):
        with h5py.File(data_folder / f"tiny_uk_2024_year_{year}.h5", "a") as file:
            del file[YEAR_FILE_STAMP_H5_DATASET]

    with pytest.raises(ValueError, match="it has no stamp of the source dataset"):
        load_datasets(
            datasets=[source], years=[DATA_YEAR, YEAR], data_folder=str(data_folder)
        )
    _assert_cut_again(source, data_folder, (DATA_YEAR, YEAR))
    _assert_reused(source, data_folder, (DATA_YEAR, YEAR))
