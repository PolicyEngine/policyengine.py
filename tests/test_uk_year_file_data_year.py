"""UK year files reproduce a direct policyengine-uk run of their source.

policyengine-uk takes the first year of a dataset as observed data. Its State
Pension formulas split each person's reported State Pension against that
year's legislated rates and scale the share to the simulated year's rates,
which follow the triple lock. ``create_datasets`` cuts year files from the
projection policyengine-uk makes of the source, so each file keeps the
observed year and its tables, and ``run()`` rebuilds that projection. A year
file passed to policyengine-uk on its own would make the simulated year the
observed year, and the State Pension would follow the CPI uprating of its
reported amount instead (PolicyEngine/policyengine.py#556).

Each test writes a tiny 2024 dataset in policyengine-uk's own file format,
cuts year files from it with ``create_datasets``, and compares a
policyengine.py run of a year file with ``policyengine_uk.Microsimulation``
on the source file, record by record.

Invariants exercised:

- Differential: for any source dataset and any year the source projects to,
  every output of a policyengine.py run of the year file equals the direct
  policyengine-uk run of the source, record by record. Under region scoping
  this holds, for the records kept, for person and benefit-unit outputs.
  Outputs normalised over the whole dataset, such as business-rates
  incidence through ``shareholding``, deciles and relative poverty lines,
  become region-relative when rows are filtered. That is a separate issue
  (PolicyEngine/policyengine.py#567).
- Round trip: saving and loading a year file preserves its data year and
  the data year's tables.
- No aliasing: a run leaves the caller's dataset tables unchanged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

pytest.importorskip("policyengine_uk")

import policyengine as pe  # noqa: E402
from policyengine.core import Simulation  # noqa: E402
from policyengine.core.scoping_strategy import RowFilterStrategy  # noqa: E402
from policyengine.tax_benefit_models.uk.datasets import (  # noqa: E402
    DATA_YEAR_KEY,
    PolicyEngineUKDataset,
    UKYearData,
    create_datasets,
    ensure_datasets,
    load_datasets,
)
from policyengine.tax_benefit_models.uk.model import (  # noqa: E402
    _policyengine_uk_input,
)

DATA_YEAR = 2024
STATE_PENSION = [
    "basic_state_pension",
    "new_state_pension",
    "additional_state_pension",
    "state_pension",
]
PERSON_OUTPUTS = STATE_PENSION + ["state_pension_type", "income_tax"]
BENUNIT_OUTPUTS = ["pension_credit", "universal_credit"]
HOUSEHOLD_OUTPUTS = [
    "household_net_income",
    "hbai_household_net_income",
    "in_poverty_bhc",
    "in_poverty_ahc",
]
EXTRA_VARIABLES = {
    "person": PERSON_OUTPUTS,
    "benunit": BENUNIT_OUTPUTS,
    "household": HOUSEHOLD_OUTPUTS,
}


def _tables(
    ages=(70, 85, 78, 72, 40, 8, 90),
    genders=("FEMALE", "MALE", "MALE", "FEMALE", "MALE", "FEMALE", "FEMALE"),
    reported=(10_000.0, 9_000.0, 14_000.0, 13_500.0, 0.0, 0.0, 3_000.0),
) -> dict[str, pd.DataFrame]:
    """Seven people in four households, observed in 2024.

    The pensioners cover both State Pension types, below and above the
    flat-rate maximum (the excess is additional State Pension or a Protected
    Payment), and one Pension Credit claimant.
    """
    person = pd.DataFrame(
        {
            "person_id": [101, 102, 201, 202, 301, 302, 401],
            "person_benunit_id": [11, 11, 21, 22, 31, 31, 41],
            "person_household_id": [1, 1, 2, 2, 3, 3, 4],
            "age": list(ages),
            "gender": list(genders),
            "state_pension_reported": list(reported),
            "employment_income": [0.0, 0.0, 0.0, 0.0, 30_000.0, 0.0, 0.0],
            "private_pension_income": [2_000.0, 0.0, 5_000.0, 0.0, 0.0, 0.0, 0.0],
        }
    )
    benunit = pd.DataFrame({"benunit_id": [11, 21, 22, 31, 41]})
    household = pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4],
            "household_weight": [1_000.0, 2_000.0, 1_500.0, 500.0],
            "region": ["LONDON", "SCOTLAND", "WALES", "NORTH_EAST"],
            "tenure_type": [
                "OWNED_OUTRIGHT",
                "RENT_PRIVATELY",
                "RENT_FROM_COUNCIL",
                "RENT_PRIVATELY",
            ],
            "council_tax": [2_000.0, 1_500.0, 1_800.0, 1_200.0],
            "rent": [0.0, 9_000.0, 6_000.0, 7_000.0],
        }
    )
    return {"person": person, "benunit": benunit, "household": household}


def _write_source(path, tables=None) -> str:
    """Write ``tables`` as a policyengine-uk single-year (2024) dataset."""
    from policyengine_uk.data import UKSingleYearDataset

    tables = tables or _tables()
    UKSingleYearDataset(**tables, fiscal_year=DATA_YEAR).save(str(path))
    return str(path)


def _cut(source: str, directory, years) -> dict[str, PolicyEngineUKDataset]:
    return create_datasets(
        datasets=[source],
        years=list(years),
        data_folder=str(directory),
        allow_unmanaged=True,
    )


def _run(dataset: PolicyEngineUKDataset, **kwargs) -> Simulation:
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.uk.model,
        extra_variables=EXTRA_VARIABLES,
        **kwargs,
    )
    simulation.run()
    return simulation


def _direct(source: str):
    from policyengine_uk import Microsimulation

    return Microsimulation(dataset=source)


def _assert_matches_direct(
    simulation: Simulation,
    direct,
    year: int,
    entities=("person", "benunit", "household"),
) -> None:
    """Every requested output equals the direct run for the records kept."""
    output = simulation.output_dataset.data
    for entity in entities:
        variables = EXTRA_VARIABLES[entity]
        id_column = f"{entity}_id"
        frame = pd.DataFrame(getattr(output, entity))
        direct_ids = direct.calculate(id_column, year).values
        positions = pd.Index(direct_ids).get_indexer(frame[id_column])
        assert (positions >= 0).all()
        for variable in variables:
            expected = np.asarray(direct.calculate(variable, year).values)[positions]
            actual = frame[variable].to_numpy()
            if expected.dtype.kind in "fiub":
                np.testing.assert_allclose(
                    actual.astype(float),
                    expected.astype(float),
                    rtol=1e-6,
                    atol=1e-3,
                    err_msg=f"{entity}.{variable} in {year}",
                )
            else:
                assert list(actual.astype(str)) == list(expected.astype(str)), (
                    f"{entity}.{variable} in {year}"
                )


@pytest.fixture(scope="module")
def source(tmp_path_factory) -> str:
    return _write_source(tmp_path_factory.mktemp("source") / "tiny_uk_2024.h5")


@pytest.fixture(scope="module")
def year_files(source, tmp_path_factory) -> dict[str, PolicyEngineUKDataset]:
    return _cut(source, tmp_path_factory.mktemp("data"), [2024, 2025, 2026, 2028])


@pytest.fixture(scope="module")
def direct(source):
    return _direct(source)


@pytest.mark.parametrize("year", [2024, 2025, 2026, 2028])
def test_year_file_run_matches_direct_policyengine_uk_run(year_files, direct, year):
    simulation = _run(year_files[f"tiny_uk_2024_{year}"])

    _assert_matches_direct(simulation, direct, year)


def test_year_file_alone_would_not_match(year_files, direct):
    """The fixture exercises the fix: the 2026 tables as observed data differ.

    Passed to policyengine-uk on its own, the projected 2026 frame makes 2026
    the observed year, and the State Pension follows the CPI uprating of its
    reported amount. This is what the year file ran as before #556.
    """
    from policyengine_uk import Microsimulation
    from policyengine_uk.data import UKSingleYearDataset

    data = year_files["tiny_uk_2024_2026"].data
    alone = Microsimulation(
        dataset=UKSingleYearDataset(
            person=pd.DataFrame(data.person).copy(),
            benunit=pd.DataFrame(data.benunit).copy(),
            household=pd.DataFrame(data.household).copy(),
            fiscal_year=2026,
        )
    )
    direct_pension = direct.calculate("state_pension", 2026).values
    alone_pension = alone.calculate("state_pension", 2026).values
    receives = direct_pension > 0
    assert receives.sum() == 5
    # Every recipient's State Pension differs, and is lower: CPI grew less
    # than the State Pension rates between 2024 and 2026.
    assert (alone_pension[receives] < direct_pension[receives] - 1).all()


def test_projected_year_files_keep_their_data_year(year_files):
    projected = year_files["tiny_uk_2024_2026"]
    observed = year_files["tiny_uk_2024_2024"]

    assert projected.data_year == DATA_YEAR
    assert projected.data_year_data is not None
    assert observed.data_year == DATA_YEAR
    # The data year's own file holds its tables as `data`.
    assert observed.data_year_data is None
    # The data year's tables are the source's, untouched by the projection.
    pd.testing.assert_series_equal(
        pd.DataFrame(projected.data_year_data.person)["state_pension_reported"],
        pd.DataFrame(observed.data.person)["state_pension_reported"],
    )
    # The projected year's reported amount is uprated (by CPI).
    assert (
        pd.DataFrame(projected.data.person)["state_pension_reported"]
        > pd.DataFrame(observed.data.person)["state_pension_reported"]
    ).sum() == 5


def test_year_file_round_trips_its_data_year(year_files):
    saved = year_files["tiny_uk_2024_2026"]

    loaded = PolicyEngineUKDataset(
        name="reloaded",
        description="reloaded",
        filepath=saved.filepath,
        year=2026,
    )

    assert loaded.data_year == DATA_YEAR
    for entity in ("person", "benunit", "household"):
        pd.testing.assert_frame_equal(
            pd.DataFrame(getattr(loaded.data_year_data, entity)),
            pd.DataFrame(getattr(saved.data_year_data, entity)),
            check_categorical=False,
            check_dtype=False,
        )
        pd.testing.assert_frame_equal(
            pd.DataFrame(getattr(loaded.data, entity)),
            pd.DataFrame(getattr(saved.data, entity)),
            check_categorical=False,
            check_dtype=False,
        )


def test_scoped_run_matches_direct_run_for_the_records_kept(year_files, direct):
    simulation = _run(
        year_files["tiny_uk_2024_2026"],
        scoping_strategy=RowFilterStrategy(
            variable_name="region", variable_value="SCOTLAND"
        ),
    )

    kept = pd.DataFrame(simulation.output_dataset.data.person)["person_id"]
    assert sorted(kept) == [201, 202]
    # Household outputs can depend on dataset-wide normalisation, which row
    # filtering changes (PolicyEngine/policyengine.py#567).
    _assert_matches_direct(simulation, direct, 2026, entities=("person", "benunit"))


def test_run_leaves_the_callers_tables_unchanged(year_files):
    dataset = year_files["tiny_uk_2024_2026"]
    before = {
        name: pd.DataFrame(frame).copy()
        for name, frame in dataset.data.entity_data.items()
    }
    observed_before = {
        name: pd.DataFrame(frame).copy()
        for name, frame in dataset.data_year_data.entity_data.items()
    }

    _run(dataset)
    # policyengine-uk encodes enum columns in place on the tables of a
    # multi-year dataset it is given, which is what a projected run hands it.
    _run(
        dataset,
        scoping_strategy=RowFilterStrategy(
            variable_name="region", variable_value="WALES"
        ),
    )

    for name, frame in dataset.data.entity_data.items():
        pd.testing.assert_frame_equal(pd.DataFrame(frame), before[name])
    for name, frame in dataset.data_year_data.entity_data.items():
        pd.testing.assert_frame_equal(pd.DataFrame(frame), observed_before[name])


def test_dataset_built_in_memory_runs_as_observed_data(source):
    """A dataset without a data year is observed data for its own year.

    That is how policyengine-uk treats a single-year dataset, so the run
    equals policyengine-uk on the same tables.
    """
    from policyengine_uk import Microsimulation
    from policyengine_uk.data import UKSingleYearDataset

    tables = _tables()
    weighted = _with_weights(tables)
    dataset = PolicyEngineUKDataset(
        name="observed-2026",
        description="tables taken as observed in 2026",
        year=2026,
        data=weighted,
    )
    simulation = _run(dataset)
    direct = Microsimulation(
        dataset=UKSingleYearDataset(
            **{name: frame.copy() for name, frame in tables.items()},
            fiscal_year=2026,
        )
    )

    _assert_matches_direct(simulation, direct, 2026)


def _with_weights(tables: dict[str, pd.DataFrame]) -> UKYearData:
    household = tables["household"]
    weight = dict(zip(household["household_id"], household["household_weight"]))
    person = tables["person"].assign(
        person_weight=tables["person"]["person_household_id"].map(weight)
    )
    benunit_household = person.drop_duplicates("person_benunit_id").set_index(
        "person_benunit_id"
    )["person_household_id"]
    benunit = tables["benunit"].assign(
        benunit_weight=tables["benunit"]["benunit_id"]
        .map(benunit_household)
        .map(weight)
    )
    return UKYearData(
        person=MicroDataFrame(person, weights="person_weight"),
        benunit=MicroDataFrame(benunit, weights="benunit_weight"),
        household=MicroDataFrame(household, weights="household_weight"),
    )


def test_projected_dataset_needs_its_data_year_tables(year_files):
    projected = year_files["tiny_uk_2024_2026"]

    with pytest.raises(ValueError, match="no data_year_data"):
        PolicyEngineUKDataset(
            name="x",
            description="x",
            year=2026,
            data=projected.data,
            data_year=DATA_YEAR,
        )
    with pytest.raises(ValueError, match="after its year"):
        PolicyEngineUKDataset(
            name="x",
            description="x",
            year=2023,
            data=projected.data,
            data_year=DATA_YEAR,
            data_year_data=projected.data_year_data,
        )
    with pytest.raises(ValueError, match="no data_year"):
        PolicyEngineUKDataset(
            name="x",
            description="x",
            year=2026,
            data=projected.data,
            data_year_data=projected.data_year_data,
        )


def test_records_missing_from_the_data_year_are_refused(year_files):
    projected = year_files["tiny_uk_2024_2026"]
    observed = projected.data_year_data
    dropped = UKYearData(
        person=MicroDataFrame(
            pd.DataFrame(observed.person).iloc[1:], weights="person_weight"
        ),
        benunit=observed.benunit,
        household=observed.household,
    )
    dataset = PolicyEngineUKDataset(
        name="x",
        description="x",
        year=2026,
        data=projected.data,
        data_year=DATA_YEAR,
        data_year_data=dropped,
    )

    with pytest.raises(ValueError, match="1 person record"):
        _policyengine_uk_input(dataset)


def _write_legacy_year_file(dataset: PolicyEngineUKDataset) -> None:
    """Rewrite a year file as policyengine.py wrote it before #556."""
    legacy = PolicyEngineUKDataset(
        name="legacy",
        description="legacy",
        filepath=dataset.filepath,
        year=dataset.year,
        data=dataset.data,
    )
    legacy.save()
    with pd.HDFStore(dataset.filepath, mode="r") as store:
        assert f"/{DATA_YEAR_KEY}" not in store.keys()


def test_load_datasets_refuses_a_year_file_without_a_data_year(source, tmp_path):
    created = _cut(source, tmp_path, [2026])
    _write_legacy_year_file(created["tiny_uk_2024_2026"])

    with pytest.raises(ValueError, match="no recorded data year"):
        load_datasets(datasets=[source], years=[2026], data_folder=str(tmp_path))


def test_ensure_datasets_regenerates_a_year_file_without_a_data_year(
    source, tmp_path, direct
):
    created = _cut(source, tmp_path, [2026])
    _write_legacy_year_file(created["tiny_uk_2024_2026"])

    ensured = ensure_datasets(
        datasets=[source],
        years=[2026],
        data_folder=str(tmp_path),
        allow_unmanaged=True,
    )

    dataset = ensured["tiny_uk_2024_2026"]
    assert dataset.data_year == DATA_YEAR
    reloaded = load_datasets(datasets=[source], years=[2026], data_folder=str(tmp_path))
    assert reloaded["tiny_uk_2024_2026"].data_year == DATA_YEAR
    _assert_matches_direct(_run(dataset), direct, 2026)


@settings(
    max_examples=6,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    ages=st.lists(st.integers(min_value=60, max_value=100), min_size=7, max_size=7),
    genders=st.lists(st.sampled_from(["MALE", "FEMALE"]), min_size=7, max_size=7),
    reported=st.lists(
        st.floats(min_value=0, max_value=25_000, allow_nan=False),
        min_size=7,
        max_size=7,
    ),
    year=st.integers(min_value=2025, max_value=2030),
)
def test_any_year_file_matches_the_direct_run(
    tmp_path_factory, ages, genders, reported, year
):
    """Differential invariant over random pensioners and projection years."""
    directory = tmp_path_factory.mktemp("random")
    source = _write_source(
        directory / "random_uk_2024.h5",
        _tables(ages=ages, genders=genders, reported=reported),
    )
    created = _cut(source, directory / "data", [year])

    simulation = _run(created[f"random_uk_2024_{year}"])

    _assert_matches_direct(simulation, _direct(source), year)
