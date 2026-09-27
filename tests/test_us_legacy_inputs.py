"""Unit and property tests for the US legacy input rename.

The certified US default release stores the WIC take-up draw as
``would_claim_wic``, which policyengine-us 2.x renamed to
``takes_up_wic_if_eligible`` (PolicyEngine/microcosm#1026). These tests state
the mapping's invariants over generated inputs, using lightweight fakes of the
slice of a country simulation the mapping touches, and run the draw through
both stored-table readers (the multi-year entity tables and a
policyengine-core ``variable/period`` H5):

- **Draw preserved.** For any stored boolean draw and any set of dataset years,
  the live input equals the stored draw for every month of every year.
- **No-op when it does not apply.** Nothing is set when the engine defines the
  legacy name, when the engine lacks the live name, or when the data already
  stores the live name.
- **Order check.** A stored table that is not in the simulation's order is
  refused, and nothing is set.
- **Idempotence.** Applying the mapping twice gives the same inputs as once.

``test_us_legacy_inputs_integration.py`` runs the same mapping inside real
policyengine-us simulations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import h5py
import numpy as np
import pandas as pd
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from policyengine.tax_benefit_models.us import legacy_inputs
from policyengine.tax_benefit_models.us.legacy_inputs import (
    LEGACY_INPUT_RENAMES,
    RENAMES_H5_DATASET,
    apply_legacy_input_renames,
    apply_legacy_input_renames_to_microsimulation,
    check_yearly_periods,
    pending_legacy_input_renames,
    read_renames_record,
    stored_entity_tables,
    write_renames_record,
)

LEGACY = "would_claim_wic"
LIVE = "takes_up_wic_if_eligible"


def _variable(period="month", entity="person", value_type=bool):
    return SimpleNamespace(
        entity=SimpleNamespace(key=entity),
        definition_period=period,
        value_type=value_type,
    )


def _variables(*names, period="month"):
    return {name: _variable(period) for name in names}


class FakeSimulation:
    """The slice of a country simulation the mapping reads and writes."""

    def __init__(self, variables, ids, *, dataset=None, input_variables=()):
        self.tax_benefit_system = SimpleNamespace(variables=variables)
        self.populations = {"person": SimpleNamespace(ids=np.asarray(ids))}
        self.dataset = dataset
        self.input_variables = list(input_variables)
        self.branches = {}
        self.inputs: dict[tuple[str, str], np.ndarray] = {}

    def set_input(self, variable, period, values):
        self.inputs[(variable, period)] = np.array(values, copy=True)


def _person(ids, draw, **columns):
    return pd.DataFrame({"person_id": list(ids), LEGACY: list(draw), **columns})


def _tables(person_by_year):
    return {year: {"person": person} for year, person in person_by_year.items()}


def _months(year):
    return [f"{year}-{month:02d}" for month in range(1, 13)]


def _snapshot(simulation):
    return {key: value.tolist() for key, value in simulation.inputs.items()}


# --- Strategies ------------------------------------------------------

YEARS = st.lists(st.integers(2015, 2040), min_size=1, max_size=4, unique=True)
IDS = st.lists(st.integers(-(10**9), 10**9), min_size=1, max_size=30, unique=True).map(
    np.asarray
)
#: The same boolean draw can be stored as bool, integer or float 0/1.
DRAW_DTYPE = st.sampled_from([bool, np.int8, np.int64, np.float64])


@st.composite
def stored_draws(draw):
    """Simulation IDs, dataset years, and each year's stored boolean draw."""
    ids = draw(IDS)
    years = draw(YEARS)
    dtype = draw(DRAW_DTYPE)
    draws = {
        year: np.asarray(
            draw(st.lists(st.booleans(), min_size=len(ids), max_size=len(ids)))
        ).astype(dtype)
        for year in years
    }
    return ids, draws


# --- Invariant: draw preserved ---------------------------------------


@settings(max_examples=200, deadline=None)
@given(case=stored_draws())
def test_live_input_equals_the_stored_draw_every_month_of_every_year(case):
    ids, draws = case
    simulation = FakeSimulation(_variables(LIVE, "person_id"), ids)

    applied = apply_legacy_input_renames(
        simulation,
        _tables({year: _person(ids, draw) for year, draw in draws.items()}),
    )

    assert applied == {LEGACY: LIVE}
    assert set(simulation.inputs) == {
        (LIVE, month) for year in draws for month in _months(year)
    }
    for year, draw in draws.items():
        for month in _months(year):
            values = simulation.inputs[(LIVE, month)]
            assert values.dtype == bool
            assert values.tolist() == draw.astype(bool).tolist()
    assert simulation.input_variables == [LIVE]


# --- Invariant: no-op when it does not apply --------------------------


@settings(max_examples=200, deadline=None)
@given(
    case=stored_draws(),
    reason=st.sampled_from(
        ["engine_defines_legacy", "engine_lacks_live", "data_stores_live"]
    ),
)
def test_nothing_is_set_when_the_rename_does_not_apply(case, reason):
    ids, draws = case
    person_by_year = {year: _person(ids, draw) for year, draw in draws.items()}
    if reason == "data_stores_live":
        for person in person_by_year.values():
            person[LIVE] = ~person[LEGACY].astype(bool)
    names = {
        "engine_defines_legacy": (LEGACY, LIVE),
        "engine_lacks_live": ("person_id",),
        "data_stores_live": (LIVE,),
    }[reason]
    simulation = FakeSimulation(_variables(*names), ids, input_variables=["age"])

    assert apply_legacy_input_renames(simulation, _tables(person_by_year)) == {}
    assert simulation.inputs == {}
    assert simulation.input_variables == ["age"]


@settings(max_examples=100, deadline=None)
@given(case=stored_draws(), data=st.data())
def test_only_years_whose_data_lacks_the_live_name_are_mapped(case, data):
    ids, draws = case
    live_years = data.draw(st.sets(st.sampled_from(sorted(draws))))
    person_by_year = {year: _person(ids, draw) for year, draw in draws.items()}
    for year in live_years:
        person_by_year[year][LIVE] = True
    simulation = FakeSimulation(_variables(LIVE), ids)

    applied = apply_legacy_input_renames(simulation, _tables(person_by_year))

    mapped_years = set(draws) - live_years
    assert applied == ({LEGACY: LIVE} if mapped_years else {})
    assert set(simulation.inputs) == {
        (LIVE, month) for year in mapped_years for month in _months(year)
    }


# --- Invariant: order check -------------------------------------------


@settings(max_examples=200, deadline=None)
@given(case=stored_draws(), data=st.data())
def test_a_table_out_of_simulation_order_is_refused_and_nothing_is_set(case, data):
    ids, draws = case
    years = sorted(draws)
    bad_year = data.draw(st.sampled_from(years))
    stored_ids = np.asarray(
        data.draw(
            st.one_of(
                # The same people in another order.
                st.permutations(ids.tolist()),
                # A person the simulation does not have.
                st.just([*ids.tolist()[:-1], int(ids.max()) + 1]),
                # A person missing, or one too many.
                st.just(ids.tolist()[:-1]),
                st.just([*ids.tolist(), int(ids.max()) + 1]),
            )
        )
    )
    assume(not np.array_equal(stored_ids, ids))
    person_by_year = {}
    for year in years:
        row_ids = stored_ids if year == bad_year else ids
        person_by_year[year] = _person(row_ids, np.ones(len(row_ids), dtype=bool))
    simulation = FakeSimulation(_variables(LIVE), ids)

    with pytest.raises(ValueError, match="not in the simulation's person order"):
        apply_legacy_input_renames(simulation, _tables(person_by_year))
    # Aligned years are checked and set together, so none was set either.
    assert simulation.inputs == {}
    assert simulation.input_variables == []


def test_a_table_without_ids_is_refused():
    simulation = FakeSimulation(_variables(LIVE), [1, 2])
    person = pd.DataFrame({LEGACY: [True, False]})
    with pytest.raises(ValueError, match="no person_id column"):
        apply_legacy_input_renames(simulation, _tables({2024: person}))
    assert simulation.inputs == {}


# --- Invariant: idempotence -------------------------------------------


@settings(max_examples=200, deadline=None)
@given(case=stored_draws())
def test_applying_twice_gives_the_same_inputs_as_once(case):
    ids, draws = case
    tables = _tables({year: _person(ids, draw) for year, draw in draws.items()})
    once = FakeSimulation(_variables(LIVE), ids)
    twice = FakeSimulation(_variables(LIVE), ids)

    applied_once = apply_legacy_input_renames(once, tables)
    apply_legacy_input_renames(twice, tables)
    applied_twice = apply_legacy_input_renames(twice, tables)

    assert applied_once == applied_twice == {LEGACY: LIVE}
    assert _snapshot(once) == _snapshot(twice)
    assert once.input_variables == twice.input_variables == [LIVE]


# --- Examples ---------------------------------------------------------


def test_the_register_holds_only_the_wic_take_up_rename():
    assert LEGACY_INPUT_RENAMES == {LEGACY: LIVE}


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        ((LIVE,), {LEGACY: LIVE}),
        ((LEGACY, LIVE), {}),
        ((LEGACY,), {}),
        ((), {}),
    ],
)
def test_pending_renames_follow_what_the_engine_defines(names, expected):
    assert pending_legacy_input_renames(_variables(*names)) == expected


def test_pending_renames_ignore_anything_but_a_variable_mapping():
    assert pending_legacy_input_renames(MagicMock()) == {}
    assert pending_legacy_input_renames(None) == {}


def test_register_changes_take_effect_without_reloading(monkeypatch):
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {})
    simulation = FakeSimulation(_variables(LIVE), [1])
    assert (
        apply_legacy_input_renames(simulation, _tables({2024: _person([1], [0])})) == {}
    )
    assert simulation.inputs == {}


def test_a_yearly_live_input_is_set_once_per_year():
    simulation = FakeSimulation(_variables(LIVE, period="year"), [1, 2])
    apply_legacy_input_renames(
        simulation, _tables({2024: _person([1, 2], [True, False])})
    )
    assert list(simulation.inputs) == [(LIVE, "2024")]


def test_an_unsupported_definition_period_is_refused():
    simulation = FakeSimulation(_variables(LIVE, period="eternity"), [1])
    with pytest.raises(ValueError, match="'eternity' is not supported"):
        apply_legacy_input_renames(simulation, _tables({2024: _person([1], [True])}))
    assert simulation.inputs == {}


@pytest.mark.parametrize(
    ("draw", "message"),
    [
        ([True, None], "missing values"),
        ([1.0, np.nan], "missing values"),
        ([0, 2], "not boolean"),
        (["False", "True"], "not boolean"),
    ],
)
def test_a_draw_that_is_not_a_complete_boolean_is_refused(draw, message):
    simulation = FakeSimulation(_variables(LIVE), [1, 2])
    with pytest.raises(ValueError, match=message):
        apply_legacy_input_renames(simulation, _tables({2024: _person([1, 2], draw)}))
    assert simulation.inputs == {}


def test_a_non_boolean_live_input_keeps_the_stored_values():
    variables = {LIVE: _variable(value_type=float)}
    simulation = FakeSimulation(variables, [1, 2])
    apply_legacy_input_renames(simulation, _tables({2024: _person([1, 2], [0.5, 2])}))
    assert simulation.inputs[(LIVE, "2024-06")].tolist() == [0.5, 2.0]


def test_the_live_input_entity_selects_the_stored_table():
    variables = {LIVE: _variable(entity="spm_unit")}
    simulation = FakeSimulation(variables, [1])
    simulation.populations["spm_unit"] = SimpleNamespace(ids=np.asarray([7, 8]))
    tables = {
        2024: {
            "person": _person([1], [False]),
            "spm_unit": pd.DataFrame({"spm_unit_id": [7, 8], LEGACY: [True, False]}),
        }
    }
    apply_legacy_input_renames(simulation, tables)
    assert simulation.inputs[(LIVE, "2024-01")].tolist() == [True, False]


def test_an_existing_input_variable_list_is_not_duplicated():
    simulation = FakeSimulation(_variables(LIVE), [1], input_variables=[LIVE])
    apply_legacy_input_renames(simulation, _tables({2024: _person([1], [False])}))
    assert simulation.input_variables == [LIVE]


# --- Country Microsimulation entry point ------------------------------


def _multi_year_dataset(person_by_year):
    """The shape of policyengine-us's USMultiYearDataset that is read."""
    return SimpleNamespace(
        datasets={
            year: SimpleNamespace(person=person, household=pd.DataFrame())
            for year, person in person_by_year.items()
        }
    )


def test_microsimulation_and_its_existing_branches_are_all_mapped():
    person_by_year = {
        2024: _person([3, 1, 2], [False, True, False]),
        2025: _person([3, 1, 2], [True, True, False]),
    }
    dataset = _multi_year_dataset(person_by_year)
    microsimulation = FakeSimulation(_variables(LIVE), [3, 1, 2], dataset=dataset)
    baseline = FakeSimulation(_variables(LIVE), [3, 1, 2], dataset=dataset)
    microsimulation.branches = {"baseline": baseline}
    baseline.branches = {"loop": microsimulation}

    applied = apply_legacy_input_renames_to_microsimulation(microsimulation)

    assert applied == {LEGACY: LIVE}
    for simulation in (microsimulation, baseline):
        assert len(simulation.inputs) == 24
        assert simulation.inputs[(LIVE, "2024-03")].tolist() == [False, True, False]
        assert simulation.inputs[(LIVE, "2025-11")].tolist() == [True, True, False]


def test_microsimulation_with_an_unrecognised_engine_or_dataset_is_left_alone():
    assert apply_legacy_input_renames_to_microsimulation(MagicMock()) == {}
    simulation = FakeSimulation(_variables(LIVE), [1], dataset=object())
    assert apply_legacy_input_renames_to_microsimulation(simulation) == {}
    assert simulation.inputs == {}


@settings(max_examples=100, deadline=None)
@given(case=stored_draws(), branch_count=st.integers(0, 2))
def test_microsimulation_draw_is_preserved_on_every_branch(case, branch_count):
    """Draw preserved, through the country Microsimulation entry point."""
    ids, draws = case
    dataset = _multi_year_dataset(
        {year: _person(ids, draw) for year, draw in draws.items()}
    )
    microsimulation = FakeSimulation(_variables(LIVE), ids, dataset=dataset)
    for index in range(branch_count):
        microsimulation.branches[f"branch_{index}"] = FakeSimulation(
            _variables(LIVE), ids, dataset=dataset
        )

    applied = apply_legacy_input_renames_to_microsimulation(microsimulation)

    assert applied == {LEGACY: LIVE}
    for simulation in (microsimulation, *microsimulation.branches.values()):
        assert set(simulation.inputs) == {
            (LIVE, month) for year in draws for month in _months(year)
        }
        for year, draw in draws.items():
            for month in _months(year):
                assert (
                    simulation.inputs[(LIVE, month)].tolist()
                    == draw.astype(bool).tolist()
                )


def test_multi_year_tables_are_returned_as_stored():
    person = _person([1], [True], age=[40])
    tables = stored_entity_tables(
        _multi_year_dataset({2024: person}), {"person": {LEGACY: LIVE}}
    )
    # Only the requested entities, and the stored frames themselves.
    assert list(tables) == [2024]
    assert list(tables[2024]) == ["person"]
    assert tables[2024]["person"] is person


def _core_dataset(path, data_format, time_period="2024"):
    return SimpleNamespace(
        file_path=path, data_format=data_format, time_period=time_period
    )


def _write_h5(path, arrays):
    with h5py.File(path, "w") as file:
        for key, values in arrays.items():
            file[key] = values
    return path


# --- Variable-centric (policyengine-core ``variable/period``) files ------


@settings(max_examples=50, deadline=None)
@given(case=stored_draws())
def test_variable_centric_draw_is_preserved_every_month_of_every_year(case):
    """Draw preserved, through a file the engine reads as ``variable/period``."""
    ids, draws = case
    with tempfile.TemporaryDirectory() as directory:
        path = _write_h5(
            Path(directory) / "core.h5",
            {
                f"person_id/{min(draws)}": ids,
                **{f"{LEGACY}/{year}": draw for year, draw in draws.items()},
            },
        )
        dataset = _core_dataset(path, "time_period_arrays", str(min(draws)))
        simulation = FakeSimulation(_variables(LIVE), ids, dataset=dataset)

        applied = apply_legacy_input_renames_to_microsimulation(simulation)

    assert applied == {LEGACY: LIVE}
    for year, draw in draws.items():
        for month in _months(year):
            values = simulation.inputs[(LIVE, month)]
            assert values.dtype == bool
            assert values.tolist() == draw.astype(bool).tolist()


def test_variable_centric_file_is_read_by_year(tmp_path):
    path = _write_h5(
        tmp_path / "core.h5",
        {
            "person_id/2024": [5, 6],
            f"{LEGACY}/2024": [True, False],
            f"{LEGACY}/2025": [False, False],
            "age/2024": [30, 1],
        },
    )

    tables = stored_entity_tables(
        _core_dataset(path, "time_period_arrays"), {"person": {LEGACY: LIVE}}
    )

    assert sorted(tables) == [2024, 2025]
    # Only the IDs and the legacy draw are read.
    pd.testing.assert_frame_equal(
        tables[2024]["person"],
        pd.DataFrame({"person_id": [5, 6], LEGACY: [True, False]}),
    )
    # A year without its own IDs is aligned to the first stored IDs, as
    # policyengine-core builds the population from them.
    assert tables[2025]["person"]["person_id"].tolist() == [5, 6]


def test_a_year_storing_its_own_ids_is_checked_against_them(tmp_path):
    """Order check, for a year that stores its own person IDs.

    policyengine-core builds the population from the first period's IDs.
    A later year that stores the same people in another order would attach
    each value to the wrong person, so it is refused and nothing is set.
    """
    path = _write_h5(
        tmp_path / "core.h5",
        {
            "person_id/2024": [5, 6],
            "person_id/2025": [6, 5],
            f"{LEGACY}/2025": [True, False],
        },
    )
    dataset = _core_dataset(path, "time_period_arrays")

    tables = stored_entity_tables(dataset, {"person": {LEGACY: LIVE}})
    assert tables[2025]["person"]["person_id"].tolist() == [6, 5]

    simulation = FakeSimulation(_variables(LIVE), [5, 6], dataset=dataset)
    with pytest.raises(ValueError, match="not in the simulation's person order"):
        apply_legacy_input_renames_to_microsimulation(simulation)
    assert simulation.inputs == {}


@pytest.mark.parametrize("live_period", ["2024", "2025", "2024-01"])
def test_variable_centric_file_storing_the_live_name_is_not_read(tmp_path, live_period):
    # Data that stores the live name for any period loads it natively, even
    # for a period the legacy draw would not be read for.
    path = _write_h5(
        tmp_path / "recut.h5",
        {
            "person_id/2024": [5, 6],
            f"{LEGACY}/2024": [True, False],
            f"{LEGACY}/2024-02": [True, False],
            f"{LIVE}/{live_period}": [False, True],
        },
    )
    dataset = _core_dataset(path, "time_period_arrays")
    assert stored_entity_tables(dataset, {"person": {LEGACY: LIVE}}) == {}

    simulation = FakeSimulation(_variables(LIVE), [5, 6], dataset=dataset)
    assert apply_legacy_input_renames_to_microsimulation(simulation) == {}
    assert simulation.inputs == {}


def test_flat_variable_file_is_read_for_the_dataset_period(tmp_path):
    path = _write_h5(tmp_path / "flat.h5", {"person_id": [5, 6], LEGACY: [False, True]})

    tables = stored_entity_tables(
        _core_dataset(path, "arrays"), {"person": {LEGACY: LIVE}}
    )

    assert tables[2024]["person"][LEGACY].tolist() == [False, True]


def test_variable_centric_file_with_a_non_yearly_draw_is_refused(tmp_path):
    path = _write_h5(
        tmp_path / "monthly.h5", {"person_id/2024": [5], f"{LEGACY}/2024-01": [True]}
    )
    with pytest.raises(ValueError, match="only yearly periods"):
        stored_entity_tables(
            _core_dataset(path, "time_period_arrays"), {"person": {LEGACY: LIVE}}
        )


def test_variable_centric_file_with_a_mislengthed_draw_is_refused(tmp_path):
    path = _write_h5(
        tmp_path / "short.h5", {"person_id/2024": [5, 6], f"{LEGACY}/2024": [True]}
    )
    with pytest.raises(ValueError, match="length differs"):
        stored_entity_tables(
            _core_dataset(path, "time_period_arrays"), {"person": {LEGACY: LIVE}}
        )


def test_variable_centric_file_without_the_columns_yields_no_tables(tmp_path):
    path = _write_h5(tmp_path / "none.h5", {"person_id/2024": [5]})
    assert (
        stored_entity_tables(
            _core_dataset(path, "time_period_arrays"), {"person": {LEGACY: LIVE}}
        )
        == {}
    )


def test_core_dataset_objects_are_probed_without_loading_keys(tmp_path):
    """policyengine-core's ``Dataset`` loads unknown attributes as H5 keys.

    Probing it with ``getattr(dataset, "datasets", None)`` raises the H5
    ``KeyError`` instead of returning ``None``, which crashed
    ``managed_microsimulation`` on every variable-centric file.
    """
    core_data = pytest.importorskip("policyengine_core.data")
    path = _write_h5(
        tmp_path / "core.h5",
        {"person_id/2024": [5, 6], f"{LEGACY}/2024": [True, False]},
    )
    dataset = core_data.Dataset.from_file(str(path), "2024")
    with pytest.raises(KeyError):
        getattr(dataset, "datasets", None)

    tables = stored_entity_tables(dataset, {"person": {LEGACY: LIVE}})

    assert tables[2024]["person"][LEGACY].tolist() == [True, False]
    simulation = FakeSimulation(_variables(LIVE), [5, 6], dataset=dataset)
    assert apply_legacy_input_renames_to_microsimulation(simulation) == {LEGACY: LIVE}
    assert simulation.inputs[(LIVE, "2024-01")].tolist() == [True, False]


# --- The record a US file keeps -----------------------------------------

RECORDS = st.dictionaries(st.text(min_size=1), st.text(min_size=1), max_size=4)


@settings(max_examples=50, deadline=None)
@given(record=RECORDS, replaced=RECORDS)
def test_a_stored_record_reads_back_as_written(record, replaced):
    """Round trip: a file's record reads back exactly, and a new one replaces it."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "output.h5"
        _write_h5(path, {"person_id": [5, 6]})
        assert read_renames_record(path) is None

        write_renames_record(path, record)
        assert read_renames_record(path) == record

        write_renames_record(path, replaced)
        assert read_renames_record(path) == replaced
        with h5py.File(path, "r") as file:
            assert file["person_id"][()].tolist() == [5, 6]


def test_a_missing_or_foreign_file_has_no_record(tmp_path):
    assert read_renames_record(tmp_path / "missing.h5") is None
    text = tmp_path / "notes.txt"
    text.write_text("not an H5 file")
    assert read_renames_record(text) is None


def test_the_record_is_stored_as_utf8_json(tmp_path):
    path = _write_h5(tmp_path / "output.h5", {"person_id": [5]})
    write_renames_record(path, {LEGACY: LIVE})
    with h5py.File(path, "r") as file:
        assert file[RENAMES_H5_DATASET].asstr()[()] == f'{{"{LEGACY}": "{LIVE}"}}'


@pytest.mark.parametrize("period", ["2024-01", "2024-01-01", "ETERNITY", "month"])
def test_a_part_year_period_is_refused(period):
    with pytest.raises(ValueError, match="only yearly periods"):
        check_yearly_periods(LEGACY, ["2024", period], "source.h5")


def test_yearly_periods_are_accepted():
    check_yearly_periods(LEGACY, ["2024", 2025, np.int64(2026)], "source.h5")
    check_yearly_periods(LEGACY, [], "source.h5")
