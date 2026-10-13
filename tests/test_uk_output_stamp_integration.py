"""A saved UK output is never reused after its year file is cut again.

These tests run, save, load and ensure UK simulations over a real
policyengine-uk engine, on the seven-person 2024 dataset of
``test_uk_year_file_data_year.py``. Each replays one way a saved output could
be reused although it holds results calculated from other data, or with
other package versions:

- the bundle re-pins a logical dataset name to another revision and sha256,
  and ``ensure_datasets`` cuts the year files again;
- a local source is rewritten in place, and the year files are cut again;
- policyengine-uk or policyengine-core is upgraded, before and after the
  year files are cut again;
- a year file is run with other versions than cut it, and those that cut it
  are installed again;
- the simulation's dataset is another year's file in the same folder;
- the output was saved by an earlier release, before the stamp existed;
- another process saves another output to the path while this one is loaded.

In each case ``Simulation.load()`` refuses the output, naming what changed,
and ``Simulation.ensure()`` calculates it again from the simulation's dataset
and then reuses it. ``test_uk_output_stamp.py`` states the check's invariants
without an engine.

Invariant exercised over generated outputs and datasets, with a stand-in for
the engine's run:

- **Ensure agrees with load.** ``Simulation.ensure()`` runs the simulation
  exactly when its output is missing or ``Simulation.load()`` would refuse
  it, and the output it saves is current exactly when the simulation's
  dataset keeps no year-file stamp or a well-formed one.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import h5py
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

pytest.importorskip("policyengine_uk")

import policyengine as pe  # noqa: E402
from policyengine.core import Simulation  # noqa: E402
from policyengine.core.scoping_strategy import RowFilterStrategy  # noqa: E402
from policyengine.core.simulation import _cache  # noqa: E402
from policyengine.provenance.dataset_materialization import (  # noqa: E402
    describe_dataset_source_identity,
    requested_dataset_source_identity,
)
from policyengine.tax_benefit_models.common.model_version import (  # noqa: E402
    output_dataset_filepath,
)
from policyengine.tax_benefit_models.uk import datasets as uk_datasets  # noqa: E402
from policyengine.tax_benefit_models.uk.datasets import (  # noqa: E402
    DATA_YEAR_KEY,
    MALFORMED_OUTPUT_STAMP,
    OUTPUT_STAMP_H5_DATASET,
    OUTPUT_STAMP_KEY,
    OUTPUT_STAMP_REVISION,
    UNREADABLE_YEAR_FILE_STAMP,
    UNSTAMPED_OUTPUT,
    YEAR_FILE_STAMP_KEY,
    YEAR_FILE_STAMP_REVISION,
    PolicyEngineUKDataset,
    ensure_datasets,
    input_year_file_stamp,
    installed_output_packages,
    installed_package_versions,
    load_datasets,
    output_stamp,
    output_stamp_problem,
    read_output_stamp,
    read_year_file_stamp,
    write_output_stamp,
    year_file_stamp,
)
from policyengine.utils.hashing import sha256_file  # noqa: E402
from tests.test_uk_year_file_data_year import (  # noqa: E402
    DATA_YEAR,
    EXTRA_VARIABLES,
    _assert_matches_direct,
    _direct,
    _tables,
    _with_weights,
    _write_source,
)
from tests.test_uk_year_file_stamp_integration import (  # noqa: E402
    BUNDLE_NAME,
    BUNDLE_URI,
    _assert_cut_again,
    _assert_reused,
    _ensure,
    _new_source,
    _pinned,
    _replacement_tables,
    _stored,
)

YEAR = 2026
KEY = f"tiny_uk_2024_{YEAR}"
#: The engine's run, kept before any test counts its calls.
RUN = type(pe.uk.model).run


@pytest.fixture(autouse=True)
def _no_outputs_kept_in_memory():
    """``ensure()`` keeps each output in memory under its simulation's id.

    These tests reuse an id to reach the output saved under it, as another
    process would.
    """
    _cache.clear()
    yield
    _cache.clear()


def _run_id() -> str:
    return f"uk-output-stamp-{uuid.uuid4().hex}"


def _simulation(dataset, run_id: str, **kwargs) -> Simulation:
    return Simulation(
        id=run_id,
        dataset=dataset,
        tax_benefit_model_version=pe.uk.model,
        extra_variables=EXTRA_VARIABLES,
        **kwargs,
    )


def _ensured(dataset, run_id: str, run=RUN, **kwargs) -> tuple[Simulation, int]:
    """Ensure a simulation's output with none kept in memory.

    Returns the simulation and how many times it was run.
    """
    _cache.clear()
    simulation = _simulation(dataset, run_id, **kwargs)
    with patch.object(
        type(pe.uk.model), "run", autospec=True, side_effect=run
    ) as counted:
        simulation.ensure()
    return simulation, counted.call_count


def _refusal(dataset, run_id: str) -> str | None:
    """Why ``load()`` refuses the saved output, or ``None`` when it loads."""
    simulation = _simulation(dataset, run_id)
    try:
        simulation.load()
    except ValueError as error:
        return str(error)
    return None


def _out_of_date(path, problem: str) -> str:
    return (
        f"Saved UK simulation output {path} is out of date: {problem}. Run the "
        "simulation again (Simulation.ensure() does so)."
    )


def _frames(simulation: Simulation) -> dict[str, pd.DataFrame]:
    return {
        name: pd.DataFrame(frame)
        for name, frame in simulation.output_dataset.data.entity_data.items()
    }


def _assert_same_output(first: Simulation, second: Simulation) -> None:
    for name, frame in _frames(first).items():
        pd.testing.assert_frame_equal(
            frame.reset_index(drop=True),
            _frames(second)[name].reset_index(drop=True),
            check_dtype=False,
            check_categorical=False,
        )


def _upgrade(patcher, package: str, version: str = "999.0.0") -> None:
    """Make ``package`` report ``version`` as installed, to year files and to
    outputs alike, as an upgrade would. The engine's code stays the same."""
    cut_with = installed_package_versions()
    calculated_with = installed_output_packages()
    patcher.setattr(
        uk_datasets,
        "installed_package_versions",
        lambda: {**cut_with, package: version},
    )
    patcher.setattr(
        uk_datasets,
        "installed_output_packages",
        lambda: {**calculated_with, package: version},
    )


def _edit(source: str) -> None:
    """Rewrite a local source in place, with a modification time of its own
    whatever the file system's resolution."""
    before = requested_dataset_source_identity("uk", source)
    _write_source(Path(source), _replacement_tables())
    os.utime(source, ns=(before["mtime_ns"] + 10**9, before["mtime_ns"] + 10**9))
    assert requested_dataset_source_identity("uk", source) != before


def _partial_files(folder: Path) -> list[Path]:
    return sorted(Path(folder).glob(".*.partial"))


# --- What a run records --------------------------------------------------


def test_year_files_keep_their_stamp_in_memory_as_on_disk(tmp_path):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    identity = requested_dataset_source_identity("uk", source)

    created = _ensure(source, data_folder, years=(DATA_YEAR, YEAR))
    loaded = _assert_reused(source, data_folder, years=(DATA_YEAR, YEAR))

    for year in (DATA_YEAR, YEAR):
        key = f"tiny_uk_2024_{year}"
        on_disk = read_year_file_stamp(created[key].filepath)
        assert on_disk == year_file_stamp(identity, year)
        assert created[key].metadata == {YEAR_FILE_STAMP_KEY: on_disk}
        assert loaded[key].metadata == {YEAR_FILE_STAMP_KEY: on_disk}
        assert input_year_file_stamp(created[key]) == on_disk
        assert input_year_file_stamp(loaded[key]) == on_disk


def test_a_saved_output_records_what_it_was_calculated_from_and_with(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    year_file = read_year_file_stamp(dataset.filepath)
    run_id = _run_id()

    simulation = _simulation(dataset, run_id)
    simulation.run()

    stamp = {
        "packages": installed_output_packages(),
        "revision": OUTPUT_STAMP_REVISION,
        "year_file": year_file,
    }
    assert set(stamp["packages"]) == {"policyengine-core", "policyengine-uk"}
    assert None not in stamp["packages"].values()
    assert simulation.output_dataset.metadata == {OUTPUT_STAMP_KEY: stamp}
    path = output_dataset_filepath(simulation)
    assert not path.exists()
    simulation.save()
    assert read_output_stamp(path) == stamp
    with h5py.File(path, "r") as file:
        assert {DATA_YEAR_KEY, OUTPUT_STAMP_H5_DATASET, "person"} <= set(file)
    assert output_stamp_problem(path, year_file) is None
    assert _partial_files(path.parent) == []

    reloaded = _simulation(dataset, run_id)
    reloaded.load()
    assert reloaded.output_dataset.metadata == {OUTPUT_STAMP_KEY: stamp}
    assert reloaded.output_dataset.data_year == DATA_YEAR
    _assert_same_output(simulation, reloaded)


def test_a_run_records_the_output_revision_it_runs_under(tmp_path, monkeypatch):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    run_id = _run_id()

    with monkeypatch.context() as raised:
        raised.setattr(uk_datasets, "OUTPUT_STAMP_REVISION", OUTPUT_STAMP_REVISION + 1)
        simulation, runs = _ensured(dataset, run_id)
        assert runs == 1
        revision = simulation.output_dataset.metadata[OUTPUT_STAMP_KEY]["revision"]
        assert revision == OUTPUT_STAMP_REVISION + 1
        assert _refusal(dataset, run_id) is None

    path = output_dataset_filepath(simulation)
    assert _refusal(dataset, run_id) == _out_of_date(
        path,
        f"it was saved with output format revision {OUTPUT_STAMP_REVISION + 1}, "
        "and this version of policyengine.py reads only revision "
        f"{OUTPUT_STAMP_REVISION}",
    )


def test_saving_writes_the_stamp_the_run_recorded_not_one_made_then(tmp_path):
    """The year file is cut again between a run and its save: the output
    holds results from the old cut, and is stamped with the old cut."""
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    dataset = _ensure(source, data_folder)[KEY]
    old = read_year_file_stamp(dataset.filepath)
    run_id = _run_id()
    simulation = _simulation(dataset, run_id)
    simulation.run()

    _edit(source)
    recut = _assert_cut_again(source, data_folder)[KEY]
    new = read_year_file_stamp(recut.filepath)
    assert new != old
    # The simulation's dataset is reloaded from the new cut before the save.
    dataset.load()
    assert input_year_file_stamp(dataset) == new
    simulation.save()

    path = output_dataset_filepath(simulation)
    assert read_output_stamp(path) == output_stamp(old)
    assert _refusal(recut, run_id) is not None
    assert _ensured(recut, run_id)[1] == 1
    assert read_output_stamp(path) == output_stamp(new)


def test_a_loaded_output_saved_again_keeps_its_stamp(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    run_id = _run_id()
    first, runs = _ensured(dataset, run_id)
    assert runs == 1
    path = output_dataset_filepath(first)
    stamp = read_output_stamp(path)

    reloaded = _simulation(dataset, run_id)
    reloaded.load()
    reloaded.save()

    assert read_output_stamp(path) == stamp
    assert _refusal(dataset, run_id) is None


def test_an_output_is_saved_where_its_filepath_says(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    simulation = _simulation(dataset, _run_id())
    simulation.run()
    moved = tmp_path / "elsewhere" / "output.h5"
    simulation.output_dataset.filepath = str(moved)

    simulation.save()

    # The tables and the stamp go to one place.
    assert not output_dataset_filepath(simulation).exists()
    assert output_stamp_problem(moved, read_year_file_stamp(dataset.filepath)) is None
    with pd.HDFStore(moved, mode="r") as store:
        assert len(store["person"]) == 7


def test_a_scoped_run_records_the_stamp_of_the_year_file_it_filters(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]

    simulation = _simulation(
        dataset,
        _run_id(),
        scoping_strategy=RowFilterStrategy(
            variable_name="region", variable_value="SCOTLAND"
        ),
    )
    simulation.run()

    assert sorted(_frames(simulation)["person"]["person_id"]) == [201, 202]
    assert simulation.output_dataset.metadata[OUTPUT_STAMP_KEY] == output_stamp(
        read_year_file_stamp(dataset.filepath)
    )


def test_a_run_of_data_built_in_memory_records_no_year_file(tmp_path):
    data_folder = tmp_path / "data"
    data_folder.mkdir()
    built = PolicyEngineUKDataset(
        name="observed-2026",
        description="tables taken as observed in 2026",
        # Never written: it places the output beside the year files below.
        filepath=str(data_folder / "built.h5"),
        year=YEAR,
        data=_with_weights(_tables()),
    )
    run_id = _run_id()

    simulation, runs = _ensured(built, run_id)
    assert runs == 1
    path = output_dataset_filepath(simulation)
    assert read_output_stamp(path) == {
        "packages": installed_output_packages(),
        "revision": OUTPUT_STAMP_REVISION,
        "year_file": None,
    }
    assert _ensured(built, run_id)[1] == 0

    # The same id over a year file in that folder: the output is not its.
    dataset = _ensure(_new_source(tmp_path), data_folder)[KEY]
    assert output_dataset_filepath(_simulation(dataset, run_id)) == path
    assert _refusal(dataset, run_id) == _out_of_date(
        path,
        "it was calculated from data that kept no year-file stamp, and the "
        "simulation's dataset keeps one",
    )
    assert _ensured(dataset, run_id)[1] == 1
    assert _refusal(built, run_id) == _out_of_date(
        path,
        "it was calculated from a year file, and the simulation's dataset keeps "
        "no year-file stamp",
    )


def test_an_output_from_data_built_in_memory_is_not_reused_after_an_upgrade(
    tmp_path, monkeypatch
):
    built = PolicyEngineUKDataset(
        name="observed-2026",
        description="tables taken as observed in 2026",
        filepath=str(tmp_path / "built.h5"),
        year=YEAR,
        data=_with_weights(_tables()),
    )
    run_id = _run_id()
    simulation, _ = _ensured(built, run_id)
    path = output_dataset_filepath(simulation)
    calculated_with = installed_output_packages()["policyengine-uk"]

    _upgrade(monkeypatch, "policyengine-uk")

    assert _refusal(built, run_id) == _out_of_date(
        path,
        f"it was calculated with policyengine-uk {calculated_with}, and "
        "policyengine-uk 999.0.0 is installed",
    )
    assert _ensured(built, run_id)[1] == 1
    assert _ensured(built, run_id)[1] == 0


# --- Year files cut again ------------------------------------------------


def test_an_output_is_reused_while_its_year_file_is_current(tmp_path):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    run_id = _run_id()

    first, runs = _ensured(_ensure(source, data_folder)[KEY], run_id)
    assert runs == 1

    # Another process: the year file is loaded, and the output with it.
    second, runs = _ensured(_assert_reused(source, data_folder)[KEY], run_id)
    assert runs == 0
    _assert_same_output(first, second)
    _assert_matches_direct(second, _direct(source), YEAR)


def test_an_output_is_not_reused_after_its_local_source_is_edited(tmp_path):
    """The smoke-test workflow: rewrite a local dataset in place."""
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    run_id = _run_id()
    first_dataset = _ensure(source, data_folder)[KEY]
    old = requested_dataset_source_identity("uk", source)
    first, runs = _ensured(first_dataset, run_id)
    assert runs == 1
    path = output_dataset_filepath(first)

    _edit(source)
    new = requested_dataset_source_identity("uk", source)

    # Until the year file is cut again, a simulation over it holds the tables
    # the output was calculated from. ``load_datasets`` refuses the year file.
    year_file = data_folder / f"tiny_uk_2024_year_{YEAR}.h5"
    assert _refusal(_stored(year_file), run_id) is None
    with pytest.raises(ValueError, match="is out of date"):
        load_datasets(datasets=[source], years=[YEAR], data_folder=str(data_folder))

    second_dataset = _assert_cut_again(source, data_folder)[KEY]
    assert _refusal(second_dataset, run_id) == _out_of_date(
        path,
        "it was calculated from a year file cut from "
        f"{describe_dataset_source_identity(old)}, and the simulation's dataset "
        f"was cut from {describe_dataset_source_identity(new)}",
    )
    # The dataset loaded before still holds the old cut's tables, and the
    # output is still what a run of it would give.
    assert _refusal(first_dataset, run_id) is None

    second, runs = _ensured(second_dataset, run_id)
    assert runs == 1
    assert read_output_stamp(path) == output_stamp(read_year_file_stamp(year_file))
    assert read_output_stamp(path)["year_file"]["source"] == new
    # Calculated from the rewritten source, not the one the old output held.
    _assert_matches_direct(second, _direct(source), YEAR)
    assert list(_frames(second)["person"]["state_pension"]) != list(
        _frames(first)["person"]["state_pension"]
    )

    third, runs = _ensured(_assert_reused(source, data_folder)[KEY], run_id)
    assert runs == 0
    _assert_same_output(second, third)


def test_an_output_is_not_reused_after_the_bundle_re_pins_its_dataset(tmp_path):
    """A release of a UK dataset in miniature: the bundle points a logical
    name at a new revision and sha256, the year files are cut again under
    their old names, and outputs calculated from the old release are not
    reused, although they sit beside those year files under the same ids."""
    data_folder = tmp_path / "data"
    data_folder.mkdir()
    bundled = data_folder / f"{BUNDLE_NAME}.h5"
    _write_source(bundled)
    old_sha256 = sha256_file(bundled)
    key = f"{BUNDLE_NAME}_{YEAR}"
    run_id = _run_id()

    first, second, third = _pinned("release-1", old_sha256)
    with first, second, third:
        ensured = ensure_datasets(
            datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
        )
        before, runs = _ensured(ensured[key], run_id)
        assert runs == 1
        path = output_dataset_filepath(before)
        reloaded = load_datasets(
            datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
        )
        assert _ensured(reloaded[key], run_id)[1] == 0

    # The new release reports other State Pension amounts; its verified copy
    # replaces the old one, as a download would.
    _write_source(bundled, _replacement_tables())
    new_sha256 = sha256_file(bundled)
    assert new_sha256 != old_sha256

    first, second, third = _pinned("release-2", new_sha256)
    with first, second, third:
        recut = ensure_datasets(
            datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
        )
        assert _refusal(recut[key], run_id) == _out_of_date(
            path,
            f"it was calculated from a year file cut from {BUNDLE_URI}@release-1 "
            f"(sha256 {old_sha256}), and the simulation's dataset was cut from "
            f"{BUNDLE_URI}@release-2 (sha256 {new_sha256})",
        )
        after, runs = _ensured(recut[key], run_id)
        assert runs == 1
        _assert_matches_direct(after, _direct(str(bundled)), YEAR)
        reloaded = load_datasets(
            datasets=[BUNDLE_NAME], years=[YEAR], data_folder=str(data_folder)
        )
        again, runs = _ensured(reloaded[key], run_id)
        assert runs == 0
        _assert_same_output(after, again)
    assert read_output_stamp(path)["year_file"]["source"] == {
        "uri": f"{BUNDLE_URI}@release-2",
        "sha256": new_sha256,
    }


@pytest.mark.parametrize("package", ["policyengine-uk", "policyengine-core"])
def test_an_output_is_not_reused_after_a_package_upgrade(
    tmp_path, monkeypatch, package
):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    run_id = _run_id()
    dataset = _ensure(source, data_folder)[KEY]
    first, runs = _ensured(dataset, run_id)
    assert runs == 1
    path = output_dataset_filepath(first)
    before = installed_output_packages()[package]

    _upgrade(monkeypatch, package)

    # Before the year file is cut again: the versions that calculated the
    # output are not the ones installed.
    year_file = data_folder / f"tiny_uk_2024_year_{YEAR}.h5"
    stale = _out_of_date(
        path,
        f"it was calculated with {package} {before}, and {package} 999.0.0 is "
        "installed",
    )
    assert _refusal(dataset, run_id) == stale
    assert _refusal(_stored(year_file), run_id) == stale
    # A simulation over the old cut, opened directly, is run again once with
    # the new versions and then reused: it is what a run of that file gives.
    assert _ensured(_stored(year_file), run_id)[1] == 1
    assert _refusal(_stored(year_file), run_id) is None
    recorded = read_output_stamp(path)
    assert recorded["packages"][package] == "999.0.0"
    assert recorded["year_file"]["packages"][package] == before

    # ``ensure_datasets`` cuts the year file again, and the output is not the
    # new cut's.
    recut = _assert_cut_again(source, data_folder)[KEY]
    assert _refusal(recut, run_id) == _out_of_date(
        path,
        f"it was calculated from a year file cut with {package} {before}, and "
        f"the simulation's dataset was cut with {package} 999.0.0",
    )
    assert _ensured(recut, run_id)[1] == 1
    assert read_output_stamp(path)["year_file"]["packages"][package] == "999.0.0"
    assert _ensured(_assert_reused(source, data_folder)[KEY], run_id)[1] == 0


def test_an_output_is_not_reused_when_the_versions_that_cut_its_year_file_return(
    tmp_path, monkeypatch
):
    """A year file cut under one policyengine-uk is opened directly and run
    under another. With the first installed again, the output's year-file
    stamp names the installed versions, but the output was not calculated
    with them."""
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    run_id = _run_id()
    _ensure(source, data_folder)
    year_file = data_folder / f"tiny_uk_2024_year_{YEAR}.h5"
    cut_with = installed_package_versions()["policyengine-uk"]

    with monkeypatch.context() as upgraded:
        _upgrade(upgraded, "policyengine-uk")
        simulation, runs = _ensured(_stored(year_file), run_id)
        assert runs == 1
        path = output_dataset_filepath(simulation)
        recorded = read_output_stamp(path)
        assert recorded["packages"]["policyengine-uk"] == "999.0.0"
        assert recorded["year_file"]["packages"]["policyengine-uk"] == cut_with
        assert _refusal(_stored(year_file), run_id) is None

    # The year file is current again, and loads.
    dataset = _assert_reused(source, data_folder)[KEY]
    stale = _out_of_date(
        path,
        "it was calculated with policyengine-uk 999.0.0, and policyengine-uk "
        f"{cut_with} is installed",
    )
    assert _refusal(dataset, run_id) == stale
    assert _refusal(_stored(year_file), run_id) == stale
    assert _ensured(dataset, run_id)[1] == 1
    assert _ensured(dataset, run_id)[1] == 0


def test_an_output_is_not_reused_for_another_years_file(tmp_path):
    source = _new_source(tmp_path)
    datasets = _ensure(source, tmp_path / "data", years=(YEAR, 2028))
    run_id = _run_id()
    first, runs = _ensured(datasets[KEY], run_id)
    assert runs == 1
    path = output_dataset_filepath(first)

    # One id, the same folder, another year's file: the same output path.
    later = datasets["tiny_uk_2024_2028"]
    assert output_dataset_filepath(_simulation(later, run_id)) == path
    assert _refusal(later, run_id) == _out_of_date(
        path,
        f"it was calculated from the year file for {YEAR}, and the simulation's "
        "dataset is the one for 2028",
    )
    second, runs = _ensured(later, run_id)
    assert runs == 1
    _assert_matches_direct(second, _direct(source), 2028)


def test_raising_the_year_file_revision_makes_saved_outputs_out_of_date(
    tmp_path, monkeypatch
):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    run_id = _run_id()
    dataset = _ensure(source, data_folder)[KEY]
    first, _ = _ensured(dataset, run_id)
    path = output_dataset_filepath(first)

    monkeypatch.setattr(
        uk_datasets, "YEAR_FILE_STAMP_REVISION", YEAR_FILE_STAMP_REVISION + 1
    )

    # The dataset still holds the tables the output was calculated from.
    assert _refusal(dataset, run_id) is None
    # ``ensure_datasets`` cuts the year files again under the new revision.
    recut = _assert_cut_again(source, data_folder)[KEY]
    assert _refusal(recut, run_id) == _out_of_date(
        path,
        "it was calculated from a year file of year-file format revision "
        f"{YEAR_FILE_STAMP_REVISION}, and the simulation's dataset is of "
        f"revision {YEAR_FILE_STAMP_REVISION + 1}",
    )
    assert _ensured(recut, run_id)[1] == 1
    assert _ensured(_assert_reused(source, data_folder)[KEY], run_id)[1] == 0


# --- Outputs saved before the stamp, or not completely -------------------


def test_outputs_saved_by_an_earlier_release_are_calculated_again_once(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    run_id = _run_id()
    first, _ = _ensured(dataset, run_id)
    path = output_dataset_filepath(first)
    # As the release before wrote it: tables and data year, no stamp.
    with h5py.File(path, "a") as file:
        del file[OUTPUT_STAMP_H5_DATASET]

    assert _refusal(dataset, run_id) == _out_of_date(path, UNSTAMPED_OUTPUT)
    second, runs = _ensured(dataset, run_id)
    assert runs == 1
    _assert_same_output(first, second)
    assert _ensured(dataset, run_id)[1] == 0


def test_saving_an_output_that_records_no_stamp_is_refused(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    simulation = _simulation(dataset, _run_id())
    simulation.run()
    del simulation.output_dataset.metadata[OUTPUT_STAMP_KEY]

    with pytest.raises(ValueError, match="does not record what it was calculated"):
        simulation.save()
    # Refused before anything is written.
    assert not output_dataset_filepath(simulation).exists()
    assert _partial_files(tmp_path / "data") == []


@pytest.mark.parametrize("stop", ["in the tables", "at the stamp"])
def test_a_save_that_fails_leaves_the_saved_output_whole_and_current(
    tmp_path, monkeypatch, stop
):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    dataset = _ensure(source, data_folder)[KEY]
    run_id = _run_id()
    simulation, _ = _ensured(dataset, run_id)
    path = output_dataset_filepath(simulation)
    before = path.read_bytes()

    def stopped(*args, **kwargs):
        raise RuntimeError("stopped part-way")

    with monkeypatch.context() as patcher:
        if stop == "in the tables":
            put = pd.HDFStore.put

            def put_until_household(self, key, value, *args, **kwargs):
                if key == "household":
                    raise RuntimeError("stopped part-way")
                return put(self, key, value, *args, **kwargs)

            patcher.setattr(pd.HDFStore, "put", put_until_household)
        else:
            patcher.setattr(uk_datasets, "publish_year_file", stopped)
        with pytest.raises(RuntimeError, match="stopped part-way"):
            simulation.save()

    # The save wrote beside the path, so the output there is untouched.
    assert path.read_bytes() == before
    assert _partial_files(data_folder) == []
    assert _refusal(dataset, run_id) is None
    assert _ensured(dataset, run_id)[1] == 0


def test_a_first_save_that_fails_leaves_no_output_and_the_next_ensure_runs(
    tmp_path, monkeypatch
):
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    dataset = _ensure(source, data_folder)[KEY]
    run_id = _run_id()
    simulation = _simulation(dataset, run_id)
    simulation.run()
    path = output_dataset_filepath(simulation)

    def stopped(*args, **kwargs):
        raise RuntimeError("stopped before the stamp")

    with monkeypatch.context() as patcher:
        patcher.setattr(uk_datasets, "publish_year_file", stopped)
        with pytest.raises(RuntimeError, match="stopped before the stamp"):
            simulation.save()

    assert not path.exists()
    assert _partial_files(data_folder) == []
    with pytest.raises(FileNotFoundError):
        _simulation(dataset, run_id).load()
    assert _ensured(dataset, run_id)[1] == 1
    assert _refusal(dataset, run_id) is None


def test_a_missing_output_is_calculated_without_a_refusal(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    run_id = _run_id()

    with pytest.raises(FileNotFoundError):
        _simulation(dataset, run_id).load()
    assert _ensured(dataset, run_id)[1] == 1


# --- Another process saving to the same path ------------------------------


def test_an_output_replaced_while_it_is_loaded_is_checked_again(tmp_path, monkeypatch):
    """The output is checked, and then, before its tables are read, another
    process moves the output of another cut onto the path. The tables read
    are that other output's, so the check is made again, and refuses it."""
    source = _new_source(tmp_path)
    data_folder = tmp_path / "data"
    run_id = _run_id()
    first_dataset = _ensure(source, data_folder)[KEY]
    old = requested_dataset_source_identity("uk", source)
    first, _ = _ensured(first_dataset, run_id)
    path = output_dataset_filepath(first)
    ours = tmp_path / "ours.h5"
    shutil.copy(path, ours)

    # Another process's output: the same id over the year file cut again.
    _edit(source)
    new = requested_dataset_source_identity("uk", source)
    second_dataset = _assert_cut_again(source, data_folder)[KEY]
    second, runs = _ensured(second_dataset, run_id)
    assert runs == 1
    theirs = tmp_path / "theirs.h5"
    shutil.copy(path, theirs)
    os.replace(ours, path)
    assert _refusal(first_dataset, run_id) is None

    check = uk_datasets.output_stamp_problem
    checks = []

    def check_then_replace(*args, **kwargs):
        problem = check(*args, **kwargs)
        checks.append(problem)
        if len(checks) == 1:
            os.replace(theirs, path)
        return problem

    monkeypatch.setattr(uk_datasets, "output_stamp_problem", check_then_replace)
    refusal = _refusal(first_dataset, run_id)

    mismatch = (
        "it was calculated from a year file cut from "
        f"{describe_dataset_source_identity(new)}, and the simulation's dataset "
        f"was cut from {describe_dataset_source_identity(old)}"
    )
    assert checks == [None, mismatch]
    assert refusal == _out_of_date(path, mismatch)


# --- Ensure agrees with load ---------------------------------------------


def _stand_in_run(self, simulation):
    """What the engine's run records, without the engine.

    A fixed output stamped as ``PolicyEngineUKLatest.run`` stamps one: with
    the installed versions and the year-file stamp the simulation's dataset
    keeps.
    """
    simulation.output_dataset = PolicyEngineUKDataset(
        id=simulation.id,
        name=simulation.dataset.name,
        description=simulation.dataset.description,
        filepath=str(output_dataset_filepath(simulation)),
        year=simulation.dataset.year,
        is_output_dataset=True,
        data_year=DATA_YEAR,
        data=_with_weights(_tables()),
        metadata={
            OUTPUT_STAMP_KEY: output_stamp(input_year_file_stamp(simulation.dataset))
        },
    )


def _dataset_stamps() -> dict[str, object]:
    """Year-file stamps a simulation's dataset may keep, by name."""
    current = year_file_stamp({"uri": "hf://fixture/repo/tiny.h5"}, YEAR)
    packages = installed_package_versions()
    return {
        "none": None,
        "current": current,
        "another source": {
            **current,
            "source": {"uri": "hf://fixture/repo/tiny.h5@next"},
        },
        "another year": {**current, "year": YEAR + 1},
        "another policyengine-uk": {
            **current,
            "packages": {**packages, "policyengine-uk": "0.0.1"},
        },
        "another revision": {**current, "revision": YEAR_FILE_STAMP_REVISION + 1},
        "unreadable": UNREADABLE_YEAR_FILE_STAMP,
        "malformed": {**current, "year": str(YEAR)},
    }


DATASET_STAMPS = st.sampled_from(sorted(_dataset_stamps()))
#: The stamps of :func:`_dataset_stamps` that are none or well formed, and so
#: name the tables a run reads. Whether a year file is the one for the source
#: and year requested, cut with the installed versions, is ``load_datasets``'
#: check, not the output's.
NAMES_ITS_TABLES = (
    "none",
    "current",
    "another source",
    "another year",
    "another policyengine-uk",
    "another revision",
)
#: What is at the output's path: an output saved by a run over a dataset
#: keeping the named stamp, or one of these.
SAVED = st.one_of(
    DATASET_STAMPS,
    st.sampled_from(
        [
            "missing",
            "no stamp",
            "no data year",
            "another output revision",
            "other versions",
            "malformed stamp",
            "not hdf5",
        ]
    ),
)


def _stand_in_dataset(directory: Path, stamp) -> PolicyEngineUKDataset:
    return PolicyEngineUKDataset(
        name="stand-in",
        description="A dataset keeping a given year-file stamp",
        # Never written: it places the output in ``directory``.
        filepath=str(directory / "input.h5"),
        year=YEAR,
        data=_with_weights(_tables()),
        metadata={} if stamp is None else {YEAR_FILE_STAMP_KEY: stamp},
    )


def _save_as(path: Path, saved: str, directory: Path, run_id: str) -> None:
    """Put at ``path`` what ``saved`` names (see :data:`SAVED`)."""
    stamps = _dataset_stamps()
    if saved == "missing":
        return
    if saved == "not hdf5":
        path.write_text("not an H5 file")
        return
    simulation = _simulation(
        _stand_in_dataset(directory, stamps.get(saved, stamps["current"])), run_id
    )
    _stand_in_run(None, simulation)
    if saved == "no data year":
        simulation.output_dataset.data_year = None
    simulation.save()
    recorded = read_output_stamp(path)
    if saved == "no stamp" or saved == "no data year":
        with h5py.File(path, "a") as file:
            del file[OUTPUT_STAMP_H5_DATASET]
    elif saved == "another output revision":
        write_output_stamp(path, {**recorded, "revision": OUTPUT_STAMP_REVISION + 1})
    elif saved == "other versions":
        write_output_stamp(
            path,
            {
                **recorded,
                "packages": {**recorded["packages"], "policyengine-uk": "0.0.1"},
            },
        )
    elif saved == "malformed stamp":
        write_output_stamp(path, {"revision": OUTPUT_STAMP_REVISION})


@settings(max_examples=150, deadline=None)
@given(saved=SAVED, kept=DATASET_STAMPS)
def test_ensure_runs_exactly_when_load_would_refuse(saved, kept):
    with tempfile.TemporaryDirectory() as directory:
        _check_ensure_agrees_with_load(Path(directory), saved, kept)


def _check_ensure_agrees_with_load(directory: Path, saved: str, kept: str) -> None:
    stamps = _dataset_stamps()
    dataset_stamp = stamps[kept]
    run_id = _run_id()
    dataset = _stand_in_dataset(directory, dataset_stamp)
    path = output_dataset_filepath(_simulation(dataset, run_id))
    _save_as(path, saved, directory, run_id)

    missing = saved == "missing"
    problem = None if missing else output_stamp_problem(path, dataset_stamp)
    # The check is the one the engine-free tests state: current exactly when
    # the output was saved by a run over the stamp the dataset keeps, and
    # that stamp is none or well formed.
    assert (problem is None and not missing) == (
        saved == kept and kept in NAMES_ITS_TABLES
    )

    if missing:
        with pytest.raises(FileNotFoundError):
            _simulation(dataset, run_id).load()
    else:
        refusal = _refusal(dataset, run_id)
        assert refusal == (None if problem is None else _out_of_date(path, problem))

    simulation, runs = _ensured(dataset, run_id, run=_stand_in_run)
    assert runs == (1 if missing or problem is not None else 0)
    assert simulation.output_dataset is not None
    assert simulation.output_dataset.metadata[OUTPUT_STAMP_KEY] == output_stamp(
        dataset_stamp
    )
    assert read_output_stamp(path) == output_stamp(dataset_stamp)

    # What ensure leaves is current exactly when the dataset keeps no stamp
    # or a well-formed one: a stamp that is unreadable or malformed names no
    # tables, so an output calculated from such a year file is calculated
    # again every time.
    current = kept in NAMES_ITS_TABLES
    assert (output_stamp_problem(path, dataset_stamp) is None) == current
    assert _ensured(dataset, run_id, run=_stand_in_run)[1] == (0 if current else 1)


def test_the_refusal_names_the_output_and_why(tmp_path):
    source = _new_source(tmp_path)
    dataset = _ensure(source, tmp_path / "data")[KEY]
    run_id = _run_id()
    first, _ = _ensured(dataset, run_id)
    path = output_dataset_filepath(first)
    write_output_stamp(path, {"revision": OUTPUT_STAMP_REVISION})

    with pytest.raises(
        ValueError,
        match=re.escape(
            f"Saved UK simulation output {path} is out of date: "
            f"{MALFORMED_OUTPUT_STAMP}. Run the simulation again "
            "(Simulation.ensure() does so)."
        ),
    ):
        _simulation(dataset, run_id).load()
