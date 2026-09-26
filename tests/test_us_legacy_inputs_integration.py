"""The legacy WIC take-up draw reaches real policyengine-us simulations.

Each test builds a tiny US household that stores its WIC take-up draw as
``would_claim_wic`` (the layout of the certified Populace default, see
PolicyEngine/microcosm#1026), loads it through one of the load paths, and
checks that a WIC-eligible person whose stored draw is ``False`` gets no WIC,
while the same person gets WIC when the mapping is switched off.

The household is one adult and two young children with no income, in Los
Angeles County: an infant (stored draw ``False``) and a two-year-old (stored
draw ``True``). Both children are WIC-eligible, which each test checks.
"""

from __future__ import annotations

import h5py
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

pytest.importorskip("policyengine_us")
pytest.importorskip("spm_calculator.policyengine_adapter")

import policyengine as pe  # noqa: E402
from policyengine.tax_benefit_models.us import legacy_inputs  # noqa: E402
from policyengine.tax_benefit_models.us.datasets import (  # noqa: E402
    PolicyEngineUSDataset,
    USYearData,
    create_datasets,
    ensure_datasets,
    load_datasets,
)
from policyengine.tax_benefit_models.us.legacy_inputs import (  # noqa: E402
    RENAMES_H5_DATASET,
    apply_legacy_input_renames,
    apply_legacy_input_renames_to_microsimulation,
    read_renames_record,
)
from policyengine.tax_benefit_models.us.model import (  # noqa: E402
    PolicyEngineUSLatest,
)

YEAR = 2024
LEGACY = "would_claim_wic"
LIVE = "takes_up_wic_if_eligible"
RENAME = {LEGACY: LIVE}
PERSON_IDS = [1, 2, 3]
#: The stored draw for the adult, the infant and the two-year-old.
DRAW = [False, False, True]
INFANT, TODDLER = 1, 2
GROUPS = ("household", "tax_unit", "spm_unit", "family", "marital_unit")
MONTHS = [f"{YEAR}-{month:02d}" for month in range(1, 13)]


def _frames() -> dict[str, pd.DataFrame]:
    """Native entity tables, with person links named ``person_<group>_id``."""
    person = pd.DataFrame(
        {
            "person_id": PERSON_IDS,
            "person_household_id": [1, 1, 1],
            "person_tax_unit_id": [1, 1, 1],
            "person_spm_unit_id": [1, 1, 1],
            "person_family_id": [1, 1, 1],
            "person_marital_unit_id": [1, 2, 3],
            "person_weight": [1.0, 1.0, 1.0],
            "age": [30, 0, 2],
            LEGACY: DRAW,
        }
    )
    frames = {"person": person}
    for group in GROUPS:
        count = 3 if group == "marital_unit" else 1
        frames[group] = pd.DataFrame(
            {f"{group}_id": range(1, count + 1), f"{group}_weight": [1.0] * count}
        )
    frames["household"]["state_code"] = ["CA"]
    frames["household"]["county_fips"] = ["06037"]
    return frames


def _in_memory_dataset(directory, frames=None) -> PolicyEngineUSDataset:
    frames = frames or _frames()
    return PolicyEngineUSDataset(
        name="legacy-wic-draw",
        description="Uncertified three-person WIC take-up fixture",
        filepath=str(directory / "input.h5"),
        year=YEAR,
        data=USYearData(
            **{
                entity: MicroDataFrame(frame, weights=f"{entity}_weight")
                for entity, frame in frames.items()
            }
        ),
    )


def _write_entity_tables(path) -> str:
    """Write the household in the certified Populace default's layout."""
    with pd.HDFStore(path, mode="w") as store:
        for entity, frame in _frames().items():
            store.put(entity, frame, format="table", data_columns=True)
        store.put("_time_period", pd.Series([YEAR]), format="table")
    return str(path)


def _write_variable_centric(path, draw_period=YEAR) -> str:
    """Write the household as a policyengine-core ``variable/period`` H5.

    The draw is stored for ``draw_period``; every other column for ``YEAR``.
    """
    with h5py.File(path, "w") as file:
        for entity, frame in _frames().items():
            for name in frame.columns:
                values = frame[name].to_numpy()
                if values.dtype.kind in {"O", "U"}:
                    values = np.asarray(values, dtype="S")
                period = draw_period if name == LEGACY else YEAR
                file.create_dataset(f"{name}/{period}", data=values)
    return str(path)


def _run(dataset: PolicyEngineUSDataset):
    simulation = pe.Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        extra_variables={
            "person": ["is_wic_eligible", "wic_if_takes_up", LIVE, "wic"],
        },
    )
    simulation.run()
    return simulation


def _assert_children_are_wic_eligible(eligible, wic_if_takes_up):
    for child in (INFANT, TODDLER):
        assert eligible[child]
        assert wic_if_takes_up[child] > 0


def _person_outputs(simulation) -> pd.DataFrame:
    return pd.DataFrame(simulation.output_dataset.data.person).set_index("person_id")


@pytest.fixture(scope="module")
def mapped_run(tmp_path_factory):
    """Load path 1 over the in-memory household, with the mapping on."""
    return _run(_in_memory_dataset(tmp_path_factory.mktemp("mapped_run")))


@pytest.fixture(scope="module")
def mapped_managed(tmp_path_factory):
    """Load path 2 over the household's entity-table file, mapping on."""
    path = _write_entity_tables(
        tmp_path_factory.mktemp("mapped_managed") / "populace_layout.h5"
    )
    return pe.us.managed_microsimulation(dataset=path, allow_unmanaged=True)


# --- Load path 1: Simulation.run() over a policyengine.py dataset -------


def test_run_keeps_a_stored_false_draw(mapped_run):
    person = _person_outputs(mapped_run)

    _assert_children_are_wic_eligible(
        person["is_wic_eligible"].to_numpy(), person["wic_if_takes_up"].to_numpy()
    )
    assert person[LIVE].tolist() == DRAW
    assert person["wic"].iloc[INFANT] == 0
    assert person["wic"].iloc[TODDLER] == pytest.approx(
        person["wic_if_takes_up"].iloc[TODDLER]
    )
    assert mapped_run.output_dataset.metadata["legacy_input_renames"] == RENAME
    assert mapped_run.release_bundle["legacy_input_renames"] == RENAME


def test_run_over_a_core_h5_keeps_a_stored_false_draw(tmp_path):
    """Path 1 over a policyengine-core ``variable/period`` file.

    The dataset loader places a column the engine does not define by its
    length. Here the draw is as long as both the person and the marital-unit
    tables, so it is placed by its live input's entity instead of dropped.
    """
    path = _write_variable_centric(tmp_path / "core_layout.h5")
    dataset = PolicyEngineUSDataset(
        name="legacy-wic-draw-core",
        description="Uncertified three-person WIC take-up fixture",
        filepath=path,
        year=YEAR,
    )
    stored = pd.DataFrame(dataset.data.person)
    assert len(stored) == len(pd.DataFrame(dataset.data.marital_unit))
    assert stored[LEGACY].astype(bool).tolist() == DRAW

    person = _person_outputs(_run(dataset))

    _assert_children_are_wic_eligible(
        person["is_wic_eligible"].to_numpy(), person["wic_if_takes_up"].to_numpy()
    )
    assert person[LIVE].tolist() == DRAW
    assert person["wic"].iloc[INFANT] == 0
    assert person["wic"].iloc[TODDLER] > 0


def test_run_without_the_mapping_gives_every_eligible_person_wic(tmp_path, monkeypatch):
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {})
    simulation = _run(_in_memory_dataset(tmp_path))
    person = _person_outputs(simulation)

    _assert_children_are_wic_eligible(
        person["is_wic_eligible"].to_numpy(), person["wic_if_takes_up"].to_numpy()
    )
    # The default take-up is True, so the stored False is lost.
    assert person[LIVE].tolist() == [True, True, True]
    assert person["wic"].iloc[INFANT] > 0
    assert person["wic"].iloc[INFANT] == pytest.approx(
        person["wic_if_takes_up"].iloc[INFANT]
    )
    assert simulation.output_dataset.metadata["legacy_input_renames"] == {}
    assert simulation.release_bundle["legacy_input_renames"] == {}


def test_run_over_a_region_keeps_a_stored_false_draw(tmp_path):
    """Regional runs simulate a scoped copy of the data; it keeps the draw."""
    from policyengine.core.scoping_strategy import RowFilterStrategy

    simulation = pe.Simulation(
        dataset=_in_memory_dataset(tmp_path),
        tax_benefit_model_version=pe.us.model,
        scoping_strategy=RowFilterStrategy(
            variable_name="state_code", variable_value="CA"
        ),
        extra_variables={"person": ["is_wic_eligible", "wic_if_takes_up", LIVE, "wic"]},
    )
    simulation.run()
    person = _person_outputs(simulation)

    _assert_children_are_wic_eligible(
        person["is_wic_eligible"].to_numpy(), person["wic_if_takes_up"].to_numpy()
    )
    assert person[LIVE].tolist() == DRAW
    assert person["wic"].iloc[INFANT] == 0
    assert simulation.release_bundle["legacy_input_renames"] == RENAME


def test_run_maps_the_baseline_of_a_reform_too(tmp_path, monkeypatch):
    """A reformed run builds its baseline from the data as well.

    policyengine-us reads baseline incomes from the baseline branch (for
    example for labor-supply responses), so an unmapped baseline would give
    every eligible person WIC there while the reform keeps the draw.
    """
    built = []
    build = PolicyEngineUSLatest._build_simulation_from_dataset

    def capture(self, country_simulation, dataset, system):
        applied = build(self, country_simulation, dataset, system)
        built.append(country_simulation)
        return applied

    monkeypatch.setattr(PolicyEngineUSLatest, "_build_simulation_from_dataset", capture)
    simulation = pe.Simulation(
        dataset=_in_memory_dataset(tmp_path),
        tax_benefit_model_version=pe.us.model,
        policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
        extra_variables={"person": [LIVE, "wic"]},
    )
    simulation.run()

    assert len(built) == 2
    baseline, reform = built
    assert baseline is reform.baseline
    for country_simulation in built:
        for month in MONTHS:
            np.testing.assert_array_equal(
                country_simulation.get_array(LIVE, month), DRAW
            )
        assert country_simulation.calculate("wic", YEAR).values[INFANT] == 0
    assert simulation.output_dataset.metadata["legacy_input_renames"] == RENAME


def test_run_leaves_data_that_stores_the_live_name_alone(tmp_path):
    frames = _frames()
    # A re-cut release: the live name, with a draw that differs from the
    # legacy column, so any mapping would be visible.
    frames["person"][LIVE] = [False, True, False]
    simulation = _run(_in_memory_dataset(tmp_path, frames))
    person = _person_outputs(simulation)

    assert person[LIVE].tolist() == [False, True, False]
    assert person["wic"].iloc[INFANT] > 0
    assert person["wic"].iloc[TODDLER] == 0
    assert simulation.output_dataset.metadata["legacy_input_renames"] == {}


def test_a_core_h5_with_a_part_year_draw_is_refused_by_run(tmp_path):
    """A draw stored for one month cannot stand for all twelve.

    ``managed_microsimulation`` refuses such a file (see the managed test
    below); ``Simulation.run()`` loads it through the dataset loader, which
    would otherwise read the first stored month for the whole year.
    """
    path = _write_variable_centric(tmp_path / "monthly.h5", draw_period=f"{YEAR}-01")

    with pytest.raises(ValueError, match="only yearly periods"):
        PolicyEngineUSDataset(
            name="legacy-wic-draw-monthly",
            description="Uncertified three-person WIC take-up fixture",
            filepath=path,
            year=YEAR,
        )


# --- Load path 2: managed_microsimulation() over the country loader ----


def _check_managed(microsim):
    for month in MONTHS:
        np.testing.assert_array_equal(microsim.calculate(LIVE, month).values, DRAW)
    eligible = microsim.calculate("is_wic_eligible", MONTHS[0]).values
    wic_if_takes_up = microsim.calculate("wic_if_takes_up", YEAR).values
    _assert_children_are_wic_eligible(eligible, wic_if_takes_up)
    wic = microsim.calculate("wic", YEAR).values
    assert wic[INFANT] == 0
    assert wic[TODDLER] == pytest.approx(wic_if_takes_up[TODDLER])


def test_managed_entity_table_file_keeps_a_stored_false_draw(mapped_managed):
    _check_managed(mapped_managed)
    # policyengine-us extends the stored year forward; each year is mapped.
    np.testing.assert_array_equal(
        mapped_managed.calculate(LIVE, "2026-07").values, DRAW
    )
    assert mapped_managed.policyengine_bundle["legacy_input_renames"] == RENAME
    assert LIVE in mapped_managed.input_variables


def test_managed_mapping_is_idempotent(mapped_managed):
    before = {
        month: mapped_managed.calculate(LIVE, month).values.copy() for month in MONTHS
    }

    assert apply_legacy_input_renames_to_microsimulation(mapped_managed) == RENAME

    for month in MONTHS:
        np.testing.assert_array_equal(
            mapped_managed.calculate(LIVE, month).values, before[month]
        )
    assert mapped_managed.input_variables.count(LIVE) == 1
    _check_managed(mapped_managed)


def test_managed_person_table_out_of_order_is_refused(mapped_managed):
    stored = mapped_managed.dataset.datasets[YEAR].person
    shuffled = stored.iloc[::-1].reset_index(drop=True)
    shuffled[LEGACY] = True
    before = mapped_managed.calculate(LIVE, MONTHS[0]).values.copy()

    with pytest.raises(ValueError, match="not in the simulation's person order"):
        apply_legacy_input_renames(mapped_managed, {YEAR: {"person": shuffled}})

    np.testing.assert_array_equal(
        mapped_managed.calculate(LIVE, MONTHS[0]).values, before
    )


def test_managed_without_the_mapping_gives_every_eligible_person_wic(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {})
    path = _write_entity_tables(tmp_path / "populace_layout.h5")
    microsim = pe.us.managed_microsimulation(dataset=path, allow_unmanaged=True)

    eligible = microsim.calculate("is_wic_eligible", MONTHS[0]).values
    wic_if_takes_up = microsim.calculate("wic_if_takes_up", YEAR).values
    _assert_children_are_wic_eligible(eligible, wic_if_takes_up)
    wic = microsim.calculate("wic", YEAR).values
    assert wic[INFANT] > 0
    assert wic[INFANT] == pytest.approx(wic_if_takes_up[INFANT])
    assert microsim.policyengine_bundle["legacy_input_renames"] == {}


def test_managed_reform_maps_its_baseline_too(tmp_path):
    path = _write_entity_tables(tmp_path / "populace_layout.h5")
    microsim = pe.us.managed_microsimulation(
        dataset=path,
        allow_unmanaged=True,
        reform={
            "gov.irs.credits.ctc.amount.base[0].amount": {
                "2024-01-01.2100-12-31": 3_000
            }
        },
    )

    # The baseline branch exists before the mapping runs, so it must be
    # mapped as well or reform-minus-baseline would include WIC.
    assert microsim.baseline is not None
    _check_managed(microsim)
    _check_managed(microsim.baseline)


def test_managed_variable_centric_file_keeps_a_stored_false_draw(tmp_path):
    path = _write_variable_centric(tmp_path / "core_layout.h5")
    microsim = pe.us.managed_microsimulation(dataset=path, allow_unmanaged=True)

    _check_managed(microsim)
    assert microsim.policyengine_bundle["legacy_input_renames"] == RENAME


def test_managed_core_h5_with_a_part_year_draw_is_refused(tmp_path):
    path = _write_variable_centric(tmp_path / "monthly.h5", draw_period=f"{YEAR}-01")

    with pytest.raises(ValueError, match="only yearly periods"):
        pe.us.managed_microsimulation(dataset=path, allow_unmanaged=True)


@pytest.fixture(scope="module")
def engine_microsim(tmp_path_factory):
    """A real managed Microsimulation the property below maps draws onto."""
    path = _write_entity_tables(
        tmp_path_factory.mktemp("engine_microsim") / "populace_layout.h5"
    )
    return pe.us.managed_microsimulation(dataset=path, allow_unmanaged=True)


@settings(max_examples=25, deadline=None)
@given(data=st.data())
def test_real_engine_takes_up_any_stored_draw_every_month(engine_microsim, data):
    """Draw preserved and idempotent, on the real policyengine-us engine.

    For any stored draw and any set of the dataset's years, the engine's
    take-up input equals the draw in every month of those years, and
    mapping it again changes nothing.
    """
    dataset_years = sorted(engine_microsim.dataset.datasets)
    years = data.draw(
        st.sets(st.sampled_from(dataset_years), min_size=1, max_size=3), label="years"
    )
    draws = {
        year: data.draw(
            st.lists(st.booleans(), min_size=3, max_size=3), label=f"draw {year}"
        )
        for year in sorted(years)
    }
    tables = {
        year: {"person": pd.DataFrame({"person_id": PERSON_IDS, LEGACY: draw})}
        for year, draw in draws.items()
    }

    for _ in range(2):
        assert apply_legacy_input_renames(engine_microsim, tables) == RENAME
        for year, draw in draws.items():
            for month in range(1, 13):
                # ``get_array`` reads the input the engine holds without
                # calculating anything. Calculating instead raised this
                # test's peak memory by about 1 GB for each new year.
                stored = engine_microsim.get_array(LIVE, f"{year}-{month:02d}")
                assert stored.dtype == bool
                np.testing.assert_array_equal(stored, draw)


# --- Both load paths agree ----------------------------------------------


def test_both_load_paths_give_the_same_take_up_and_wic(mapped_run, mapped_managed):
    """Differential: the two US load paths map the same draw identically."""
    run_person = _person_outputs(mapped_run).loc[PERSON_IDS]
    managed_ids = mapped_managed.calculate("person_id", YEAR).values.tolist()
    assert managed_ids == PERSON_IDS

    np.testing.assert_array_equal(
        run_person[LIVE].to_numpy(), mapped_managed.calculate(LIVE, YEAR).values
    )
    np.testing.assert_allclose(
        run_person["wic"].to_numpy(), mapped_managed.calculate("wic", YEAR).values
    )


# --- create_datasets(): extraction for ensure_datasets() ----------------


def _create_year_file(directory):
    """Cut the household's entity-table file into a year file."""
    source = _write_entity_tables(directory / "populace_layout.h5")
    created = create_datasets(
        datasets=[source],
        years=[YEAR],
        data_folder=str(directory / "data"),
        allow_unmanaged=True,
    )
    (dataset,) = created.values()
    return source, dataset


def test_create_datasets_extracts_the_draw_under_the_live_name(tmp_path):
    _, dataset = _create_year_file(tmp_path)
    person = pd.DataFrame(dataset.data.person)

    assert person[LIVE].tolist() == DRAW
    assert LEGACY not in person.columns
    assert dataset.metadata["legacy_input_renames"] == RENAME
    # The year file keeps the record, so reloading it keeps the chain.
    assert read_renames_record(dataset.filepath) == RENAME
    reloaded = PolicyEngineUSDataset(
        name=dataset.name,
        description=dataset.description,
        filepath=dataset.filepath,
        year=YEAR,
    )
    assert reloaded.metadata["legacy_input_renames"] == RENAME

    # The extracted data carries the live name, so a run reads it natively
    # and maps nothing itself. Its record still shows the rename applied
    # when the year file was cut.
    for input_dataset in (dataset, reloaded):
        simulation = _run(input_dataset)
        outputs = _person_outputs(simulation)
        assert outputs[LIVE].tolist() == DRAW
        assert outputs["wic"].iloc[INFANT] == 0
        assert outputs["wic"].iloc[TODDLER] > 0
        assert simulation.output_dataset.metadata["legacy_input_renames"] == RENAME
        assert simulation.release_bundle["legacy_input_renames"] == RENAME


def _cut_before_the_mapping(path):
    """Make a year file look like one ``create_datasets`` wrote before the fix.

    policyengine.py 6.0.0 to 6.1.1 stored neither name, since the engine
    skipped the legacy column, and wrote no record.
    """
    frames = {}
    with pd.HDFStore(path, mode="r") as store:
        for key in store.keys():
            frames[key.strip("/")] = store[key]
    frames["person"] = frames["person"].drop(columns=[LIVE])
    with pd.HDFStore(path, mode="w") as store:
        for key, frame in frames.items():
            store[key] = frame
    with h5py.File(path, "r") as file:
        assert RENAMES_H5_DATASET not in file


def test_ensure_datasets_regenerates_a_year_file_cut_before_the_mapping(tmp_path):
    source, dataset = _create_year_file(tmp_path)
    _cut_before_the_mapping(dataset.filepath)
    data_folder = str(tmp_path / "data")

    # The stale file has lost the draw: a run over it gives the infant WIC.
    stale = PolicyEngineUSDataset(
        name="stale", description="stale", filepath=dataset.filepath, year=YEAR
    )
    assert LIVE not in pd.DataFrame(stale.data.person).columns
    assert _person_outputs(_run(stale))["wic"].iloc[INFANT] > 0

    with pytest.raises(ValueError, match="no record of the renamed stored inputs"):
        load_datasets(datasets=[source], years=[YEAR], data_folder=data_folder)

    (regenerated,) = ensure_datasets(
        datasets=[source],
        years=[YEAR],
        data_folder=data_folder,
        allow_unmanaged=True,
    ).values()

    assert regenerated.filepath == dataset.filepath
    assert read_renames_record(dataset.filepath) == RENAME
    assert pd.DataFrame(regenerated.data.person)[LIVE].tolist() == DRAW
    # The regenerated file is current, so it is reused from now on.
    (loaded,) = load_datasets(
        datasets=[source], years=[YEAR], data_folder=data_folder
    ).values()
    assert pd.DataFrame(loaded.data.person)[LIVE].tolist() == DRAW
    simulation = _run(loaded)
    assert _person_outputs(simulation)["wic"].iloc[INFANT] == 0
    assert simulation.release_bundle["legacy_input_renames"] == RENAME


# --- Saved outputs and run records keep the record ----------------------


def _saved_run(directory, simulation_id):
    simulation = pe.Simulation(
        id=simulation_id,
        dataset=_in_memory_dataset(directory),
        tax_benefit_model_version=pe.us.model,
        extra_variables={"person": [LIVE, "wic"]},
    )
    simulation.run()
    simulation.save()
    return simulation


def _reloaded(simulation):
    restored = pe.Simulation(
        id=simulation.id,
        dataset=simulation.dataset,
        tax_benefit_model_version=pe.us.model,
        extra_variables=simulation.extra_variables,
    )
    restored.load()
    return restored


def test_a_saved_output_keeps_the_renames_it_applied(tmp_path):
    simulation = _saved_run(tmp_path, "legacy-wic-saved")

    restored = _reloaded(simulation)

    assert restored.output_dataset.metadata["legacy_input_renames"] == RENAME
    assert restored.release_bundle["legacy_input_renames"] == RENAME
    assert _person_outputs(restored)["wic"].iloc[INFANT] == 0


def test_an_output_saved_before_the_mapping_is_not_reused(tmp_path):
    """A saved output without the record predates the fix, so its WIC is wrong.

    ``load()`` refuses it, and ``ensure()`` runs the simulation again.
    """
    from policyengine.core.simulation import _cache
    from policyengine.tax_benefit_models.us.legacy_inputs import RENAMES_H5_DATASET

    simulation = _saved_run(tmp_path, "legacy-wic-stale")
    path = simulation.output_dataset.filepath
    # Make the file look like one saved before the mapping existed: no
    # record, and the full-take-up WIC every eligible person got then.
    with h5py.File(path, "a") as stream:
        del stream[RENAMES_H5_DATASET]
    stale = pd.DataFrame(pd.read_hdf(path, "person"))
    stale["wic"] = stale["wic"].where(stale["person_id"] != 2, 999.0)
    stale.to_hdf(path, key="person", format="fixed")

    with pytest.raises(ValueError, match="predates the mapping"):
        _reloaded(simulation)

    _cache.clear()
    rerun = pe.Simulation(
        id=simulation.id,
        dataset=simulation.dataset,
        tax_benefit_model_version=pe.us.model,
        extra_variables=simulation.extra_variables,
    )
    rerun.ensure()
    assert _person_outputs(rerun)["wic"].iloc[INFANT] == 0
    assert rerun.release_bundle["legacy_input_renames"] == RENAME
    # The recomputed output was saved with its record, so it loads again.
    assert _reloaded(rerun).release_bundle["legacy_input_renames"] == RENAME
    _cache.clear()


def test_an_output_without_the_record_is_not_saved(tmp_path):
    simulation = _run(_in_memory_dataset(tmp_path))
    del simulation.output_dataset.metadata["legacy_input_renames"]

    with pytest.raises(ValueError, match="run again before saving"):
        simulation.save()


def test_the_run_record_binds_the_renames_applied(tmp_path):
    from policyengine.core.run_record import build_simulation_run_record_payloads

    dataset = _in_memory_dataset(tmp_path)
    # A run record binds the bytes of the input and output files.
    dataset.save()
    simulation = _run(dataset)
    simulation.save()

    payloads = build_simulation_run_record_payloads(simulation)

    assert payloads["results"]["legacy_input_renames"] == RENAME
