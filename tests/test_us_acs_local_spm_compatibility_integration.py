"""The temporary ACS-local SPM compatibility in real policyengine-us runs.

#597 keeps ACS group-quarters units out of the SPM measurement; #598 supplies
the certified SPM independence role for ASEC/PUF records. Each test uses tiny
synthetic households in California:

- SPM unit 1: an ACS family (adult head, child), receiving housing assistance.
- SPM unit 2: an ACS institutional group-quarters child aged 16.
- SPM unit 3: an ACS noninstitutional group-quarters adult aged 70, receiving
  housing assistance.
- SPM unit 4: an ASEC adult head.
- SPM unit 5: an ASEC teen aged 16, alone in an SPM unit inside household 4,
  whom the certified independence list marks independent.

Without the compatibility, units 2 and 5 have no classified adult and stop
every SPM calculation.
"""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

pytest.importorskip("policyengine_us")
pytest.importorskip("spm_calculator.policyengine_adapter")

import policyengine as pe  # noqa: E402
from policyengine.core.run_record import (  # noqa: E402
    build_simulation_run_record_payloads,
)
from policyengine.core.simulation import Simulation, _cache  # noqa: E402
from policyengine.outputs.poverty import (  # noqa: E402
    Poverty,
    calculate_us_poverty_by_age,
    calculate_us_poverty_rates,
)
from policyengine.provenance.dataset_materialization import (  # noqa: E402
    DatasetSource,
    MaterializedDataset,
)
from policyengine.tax_benefit_models.us import datasets as us_datasets  # noqa: E402
from policyengine.tax_benefit_models.us.datasets import (  # noqa: E402
    PolicyEngineUSDataset,
    USYearData,
    create_datasets,
    ensure_datasets,
    load_datasets,
)
from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest  # noqa: E402
from policyengine.tax_benefit_models.us.spm_independence_role import (  # noqa: E402
    INDEPENDENCE_LIST,
    INDEPENDENCE_LIST_SHA256,
    INDEPENDENCE_ROLE,
)
from policyengine.tax_benefit_models.us.spm_measurement_scope import (  # noqa: E402
    ACS_LOCAL_SOURCE_SHA256,
    FLOAT_INDICATORS,
    OUTSIDE_SPM_MEASUREMENT,
    SCOPE_H5_DATASET,
    SCOPE_RECORD_KEY,
    SCOPE_RULE,
    SPM_MEASUREMENT_VARIABLES,
    SPMMeasurementScope,
)

YEAR = 2026
ACS = "acs_2024_1yr"
OUTSIDE_UNITS = [2, 3]
MEASURED_UNITS = [1, 4, 5]
GQ_COUNTIES = {"06075", "06001"}
REFORM = {"gov.irs.credits.ctc.amount.base[0].amount": 3_000}
SPM_EXTRAS = {
    "spm_unit": [
        name for name in SPM_MEASUREMENT_VARIABLES if name != "person_in_poverty"
    ],
    "person": ["person_in_poverty", INDEPENDENCE_ROLE],
}
ORDINARY = {
    "household": [
        "household_net_income",
        "household_benefits",
        "household_tax",
        "household_market_income",
    ],
    "tax_unit": [
        "income_tax",
        "employee_payroll_tax",
        "state_income_tax",
        "eitc",
        "ctc",
    ],
    "spm_unit": ["snap", "tanf"],
}


def _groups(count: int, key: str) -> pd.DataFrame:
    return pd.DataFrame(
        {f"{key}_id": range(1, count + 1), f"{key}_weight": [1.0] * count}
    )


def _source_frames() -> dict[str, pd.DataFrame]:
    """Tables in the certified source layout, with its record-type evidence."""
    person = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5, 6],
            "person_household_id": [1, 1, 2, 3, 4, 4],
            "person_spm_unit_id": [1, 1, 2, 3, 4, 5],
            "person_tax_unit_id": [1, 1, 2, 3, 4, 5],
            "person_family_id": [1, 1, 2, 3, 4, 5],
            "person_marital_unit_id": [1, 2, 3, 4, 5, 6],
            "age": [40, 8, 16, 70, 30, 16],
            "employment_income": [30_000.0, 0, 0, 0, 50_000.0, 4_000.0],
            "is_household_head": [True, False, False, False, True, False],
            "person_support_channel": [ACS, ACS, ACS, ACS, "asec", "asec"],
            "RELSHIPP": [20.0, 25.0, 37.0, 38.0, np.nan, np.nan],
        }
    )
    household = _groups(4, "household")
    household["state_code"] = ["CA"] * 4
    household["county_fips"] = ["06037", "06075", "06001", "06037"]
    household["TYPEHUGQ"] = [1.0, 2.0, 3.0, np.nan]
    spm_unit = _groups(5, "spm_unit")
    spm_unit["housing_assistance"] = [6_000.0, 0.0, 5_000.0, 0.0, 0.0]
    return {
        "person": person,
        "household": household,
        "spm_unit": spm_unit,
        "tax_unit": _groups(5, "tax_unit"),
        "family": _groups(5, "family"),
        "marital_unit": _groups(6, "marital_unit"),
    }


def _scope_record() -> dict:
    return SPMMeasurementScope(
        rule=SCOPE_RULE,
        source_sha256=ACS_LOCAL_SOURCE_SHA256,
        outside_spm_units=2,
        measured_spm_units=3,
        independence_list_sha256=INDEPENDENCE_LIST_SHA256,
        independence_list_people=2,
    ).model_dump()


def _dataset(directory, *, scoped=True, drop_units=(), teen_independent=True):
    """A year-file-like dataset; ``scoped`` adds the stored compatibility."""
    frames = {name: frame.copy() for name, frame in _source_frames().items()}
    person = frames["person"]
    person["person_weight"] = 1.0
    for entity in ("household", "spm_unit", "tax_unit", "family", "marital_unit"):
        person[f"{entity}_id"] = person.pop(f"person_{entity}_id")
    if scoped:
        frames["spm_unit"][OUTSIDE_SPM_MEASUREMENT] = [False, True, True, False, False]
        person[INDEPENDENCE_ROLE] = [True, False, False, False, True, teen_independent]
    if drop_units:
        keep = ~person["spm_unit_id"].isin(drop_units)
        dropped = person.loc[~keep]
        frames["person"] = person = person.loc[keep].reset_index(drop=True)
        for entity in ("household", "spm_unit", "tax_unit", "family", "marital_unit"):
            ids = set(person[f"{entity}_id"])
            frames[entity] = frames[entity][frames[entity][f"{entity}_id"].isin(ids)]
            frames[entity] = frames[entity].reset_index(drop=True)
        assert len(dropped)
    for name in ("RELSHIPP", "person_support_channel"):
        person.drop(columns=name, inplace=True)
    frames["household"].drop(columns="TYPEHUGQ", inplace=True)
    return PolicyEngineUSDataset(
        name="acs-local-spm-compatibility",
        description="Uncertified synthetic ACS-local households",
        filepath=str(directory / "input.h5"),
        year=YEAR,
        metadata={SCOPE_RECORD_KEY: _scope_record()} if scoped else {},
        data=USYearData(
            **{
                entity: MicroDataFrame(frame, weights=f"{entity}_weight")
                for entity, frame in frames.items()
            }
        ),
    )


def _frame(simulation, entity) -> pd.DataFrame:
    return pd.DataFrame(getattr(simulation.output_dataset.data, entity)).set_index(
        f"{entity}_id"
    )


@pytest.fixture(scope="module")
def provider_calls():
    return []


@pytest.fixture(scope="module")
def scoped_run(tmp_path_factory, provider_calls):
    """A reform run over the scoped households, recording provider calls."""
    from policyengine_us.spm import CountyRequiringSPMProvider

    original = CountyRequiringSPMProvider._amounts

    def spy(self, year, adults, children, tenure, county):
        provider_calls.append((adults, children, county))
        return original(self, year, adults, children, tenure, county)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(CountyRequiringSPMProvider, "_amounts", spy)
        simulation = Simulation(
            dataset=_dataset(tmp_path_factory.mktemp("scoped")),
            tax_benefit_model_version=pe.us.model,
            policy=REFORM,
            extra_variables=SPM_EXTRAS,
        )
        simulation.run()
    return simulation


@pytest.fixture(scope="module")
def measured_reference(tmp_path_factory):
    """The unmodified model on the households it can measure.

    Group-quarters unit 3 has an adult, so the unmodified model measures it;
    group-quarters child unit 2 cannot be measured and is dropped. A unit's SPM
    threshold depends only on its own members, tenure and county.
    """
    simulation = Simulation(
        dataset=_dataset(
            tmp_path_factory.mktemp("reference"), scoped=False, drop_units=(2,)
        ),
        tax_benefit_model_version=pe.us.model,
        policy=REFORM,
        extra_variables={
            "spm_unit": SPM_EXTRAS["spm_unit"],
            "person": ["person_in_poverty"],
        },
    )
    # The unmodified model has no stored role, so the independent teen's
    # unit (5) would raise; the reference supplies the same certified role.
    simulation.dataset.data.person[INDEPENDENCE_ROLE] = [True, False, False, True, True]
    simulation.run()
    return simulation


@pytest.fixture(scope="module")
def ordinary_reference(tmp_path_factory):
    """The unmodified model's ordinary outputs on the complete population."""
    original = PolicyEngineUSLatest.resolve_entity_variables

    def ordinary_only(self, simulation):
        return {
            entity: [name for name in names if name not in SPM_MEASUREMENT_VARIABLES]
            for entity, names in original(self, simulation).items()
        }

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(PolicyEngineUSLatest, "resolve_entity_variables", ordinary_only)
        simulation = Simulation(
            dataset=_dataset(tmp_path_factory.mktemp("ordinary"), scoped=False),
            tax_benefit_model_version=pe.us.model,
            policy=REFORM,
        )
        simulation.run()
    return simulation


def test_unmodified_model_cannot_measure_the_population(tmp_path):
    from spm_calculator.errors import SPMInputError

    simulation = Simulation(
        dataset=_dataset(tmp_path, scoped=False),
        tax_benefit_model_version=pe.us.model,
    )
    with pytest.raises(SPMInputError) as error:
        simulation.run()
    assert error.value.code == "SPM_COMPOSITION_REQUIRED"


def test_outside_units_have_no_spm_values(scoped_run):
    spm_unit = _frame(scoped_run, "spm_unit")
    for name in SPM_EXTRAS["spm_unit"]:
        assert spm_unit.loc[OUTSIDE_UNITS, name].isna().all(), name
        assert spm_unit.loc[MEASURED_UNITS, name].notna().all(), name
    person = _frame(scoped_run, "person")
    assert person["person_in_poverty"].isna().tolist() == [
        False,
        False,
        True,
        True,
        False,
        False,
    ]
    for name in FLOAT_INDICATORS - {"person_in_poverty"}:
        assert spm_unit[name].dtype.kind == "f"


def test_outside_units_never_reach_the_spm_provider(scoped_run, provider_calls):
    assert provider_calls
    assert not {county for _, _, county in provider_calls} & GQ_COUNTIES
    assert all(adults >= 1 for adults, _, _ in provider_calls)


def test_measured_units_keep_the_canonical_spm_values(scoped_run, measured_reference):
    scoped = _frame(scoped_run, "spm_unit")
    reference = _frame(measured_reference, "spm_unit")
    for name in SPM_EXTRAS["spm_unit"]:
        if name == "spm_unit_income_decile":
            continue  # ranks depend on which units are ranked
        np.testing.assert_array_equal(
            scoped.loc[MEASURED_UNITS, name].to_numpy(dtype=float),
            reference.loc[MEASURED_UNITS, name].to_numpy(dtype=float),
            err_msg=name,
        )
    # The measured family's housing subsidy is capped by the canonical
    # housing portion; the assisted group-quarters adult is not measured.
    assert scoped.loc[1, "spm_unit_capped_housing_subsidy"] > 0
    assert reference.loc[3, "spm_unit_spm_threshold"] > 0
    assert np.isnan(scoped.loc[3, "spm_unit_spm_threshold"])


def test_ordinary_calculations_are_unchanged_for_everyone(
    scoped_run, ordinary_reference
):
    for entity, names in ORDINARY.items():
        scoped = _frame(scoped_run, entity)
        reference = _frame(ordinary_reference, entity)
        assert scoped.index.equals(reference.index)
        for name in names:
            np.testing.assert_array_equal(
                scoped[name].to_numpy(), reference[name].to_numpy(), err_msg=name
            )
            assert np.isfinite(scoped[name].to_numpy(dtype=float)).all(), name


def test_poverty_rates_cover_measured_people_only(scoped_run):
    rates = calculate_us_poverty_rates(scoped_run).dataframe.set_index("poverty_type")
    # People 3 and 4 are outside; everyone has weight 1.
    assert rates["total_population"].tolist() == [4.0, 4.0]
    children = calculate_us_poverty_by_age(scoped_run).dataframe
    child = children[children["filter_group"] == "child"].iloc[0]
    # Child 2 and teen 6 are measured; group-quarters teen 3 is not.
    assert child["total_population"] == 2.0


def test_poverty_flags_are_not_summed_onto_groups(scoped_run):
    poverty = Poverty(
        simulation=scoped_run,
        poverty_variable="spm_unit_is_in_spm_poverty",
        entity="household",
    )
    with pytest.raises(ValueError, match="summarise it for people"):
        poverty.run()


def test_the_scope_reaches_the_baseline_and_stays_private(tmp_path, monkeypatch):
    from policyengine_us.system import system

    systems = []
    original = PolicyEngineUSLatest._build_simulation_from_dataset

    def capture(self, country_simulation, dataset, tax_benefit_system):
        systems.append(tax_benefit_system)
        return original(self, country_simulation, dataset, tax_benefit_system)

    monkeypatch.setattr(PolicyEngineUSLatest, "_build_simulation_from_dataset", capture)
    Simulation(
        dataset=_dataset(tmp_path), tax_benefit_model_version=pe.us.model, policy=REFORM
    ).run()
    assert len(systems) == 2
    assert all(OUTSIDE_SPM_MEASUREMENT in policy.variables for policy in systems)

    systems.clear()
    unscoped = Simulation(
        dataset=_dataset(tmp_path, scoped=False, drop_units=(2,)),
        tax_benefit_model_version=pe.us.model,
    )
    unscoped.dataset.data.person[INDEPENDENCE_ROLE] = [True, False, False, True, True]
    unscoped.run()
    assert OUTSIDE_SPM_MEASUREMENT not in systems[0].variables
    assert OUTSIDE_SPM_MEASUREMENT not in system.variables
    assert system.variables["spm_unit_is_in_spm_poverty"].value_type is bool
    assert _frame(unscoped, "spm_unit")["spm_unit_is_in_spm_poverty"].dtype == bool


@pytest.mark.parametrize("abolish_hud", [False, True])
def test_structural_resource_reforms_cannot_bypass_the_scope(tmp_path, abolish_hud):
    simulation = Simulation(
        dataset=_dataset(tmp_path),
        tax_benefit_model_version=pe.us.model,
        policy={
            "gov.contrib.congress.tlaib.end_child_poverty_act.in_effect": True,
            "gov.hud.abolition": abolish_hud,
        },
        extra_variables={"spm_unit": ["spm_unit_benefits"]},
    )
    simulation.run()
    spm_unit = _frame(simulation, "spm_unit")
    for name in (
        "spm_unit_benefits",
        "spm_unit_net_income",
        "spm_unit_is_in_spm_poverty",
    ):
        assert spm_unit.loc[OUTSIDE_UNITS, name].isna().all(), name
        assert spm_unit.loc[MEASURED_UNITS, name].notna().all(), name


def test_a_measured_unit_without_an_adult_still_raises(tmp_path):
    from spm_calculator.errors import SPMInputError

    simulation = Simulation(
        dataset=_dataset(tmp_path, teen_independent=False),
        tax_benefit_model_version=pe.us.model,
    )
    with pytest.raises(SPMInputError) as error:
        simulation.run()
    assert error.value.code == "SPM_COMPOSITION_REQUIRED"


def test_saved_outputs_are_reused_only_under_the_same_scope(tmp_path):
    _cache.clear()
    dataset = _dataset(tmp_path)
    # A run record binds the input file's bytes, so write it first.
    dataset.save()
    simulation = Simulation(
        id="acs-local-scope", dataset=dataset, tax_benefit_model_version=pe.us.model
    )
    simulation.ensure()
    with h5py.File(simulation.output_dataset.filepath, "r") as file:
        assert SCOPE_H5_DATASET in file
    assert simulation.release_bundle[SCOPE_RECORD_KEY] == _scope_record()
    payloads = build_simulation_run_record_payloads(simulation)
    assert payloads["results"][SCOPE_RECORD_KEY] == _scope_record()

    _cache.clear()
    restored = Simulation(
        id=simulation.id, dataset=dataset, tax_benefit_model_version=pe.us.model
    )
    restored.load()
    assert restored.output_dataset.metadata[SCOPE_RECORD_KEY] == _scope_record()

    unscoped = Simulation(
        id=simulation.id,
        dataset=_dataset(tmp_path, scoped=False),
        tax_benefit_model_version=pe.us.model,
    )
    with pytest.raises(ValueError, match="different SPM measurement scope"):
        unscoped.load()


# --- create_datasets(): the year files the executor loads ---------------


def _write_source(path) -> str:
    with pd.HDFStore(path, mode="w") as store:
        for entity, frame in _source_frames().items():
            store.put(entity, frame, format="table", data_columns=True)
        store.put("_time_period", pd.Series([2024]), format="table")
    return str(path)


@pytest.fixture
def certified_sources(tmp_path, monkeypatch):
    """Serve the synthetic source and list as the certified bundle files."""
    source = _write_source(tmp_path / "populace_us_2024_acs_local.h5")
    independence_list = tmp_path / "source_spm_person_independence.csv"
    pd.DataFrame(
        {
            "person_id": [5, 6],
            "person_spm_unit_id": [4, 5],
            "is_spm_independence_role": [True, True],
        }
    ).to_csv(independence_list, index=False)
    requests = []

    def materialize(country, dataset=None, **kwargs):
        requests.append(dataset)
        path, sha256 = {
            "populace_us_2024_acs_local": (source, ACS_LOCAL_SOURCE_SHA256),
            INDEPENDENCE_LIST: (str(independence_list), INDEPENDENCE_LIST_SHA256),
        }[dataset]
        return DatasetSource(
            source_uri=f"hf://policyengine/populace-us/{Path(path).name}",
            path=path,
            bundle_dataset=MaterializedDataset(
                data_package_name="microcosm-data",
                repo_type="dataset",
                revision="synthetic",
                source_uri=f"hf://policyengine/populace-us/{Path(path).name}",
                sha256=sha256,
                path=path,
            ),
        )

    monkeypatch.setattr(us_datasets, "materialize_dataset", materialize)
    return requests


def test_year_files_carry_the_compatibility_for_every_year(tmp_path, certified_sources):
    data_folder = str(tmp_path / "data")
    years = [2025, 2026, 2027]
    created = create_datasets(
        datasets=["populace_us_2024_acs_local"], years=years, data_folder=data_folder
    )
    assert certified_sources == ["populace_us_2024_acs_local", INDEPENDENCE_LIST]
    for year in years:
        dataset = created[f"populace_us_2024_acs_local_{year}"]
        spm_unit = pd.DataFrame(dataset.data.spm_unit).set_index("spm_unit_id")
        person = pd.DataFrame(dataset.data.person).set_index("person_id")
        assert spm_unit[OUTSIDE_SPM_MEASUREMENT].to_dict() == {
            1: False,
            2: True,
            3: True,
            4: False,
            5: False,
        }
        # ACS: household head, as the model computes; ASEC: the list.
        assert person[INDEPENDENCE_ROLE].tolist() == [
            True,
            False,
            False,
            False,
            True,
            True,
        ]
        record = SPMMeasurementScope.model_validate(dataset.metadata[SCOPE_RECORD_KEY])
        assert (record.outside_spm_units, record.independence_list_people) == (2, 2)

    (loaded,) = load_datasets(
        datasets=["populace_us_2024_acs_local"], years=[2026], data_folder=data_folder
    ).values()
    simulation = Simulation(
        dataset=loaded,
        tax_benefit_model_version=pe.us.model,
        extra_variables={"person": [INDEPENDENCE_ROLE]},
    )
    simulation.run()
    spm_unit = _frame(simulation, "spm_unit")
    assert spm_unit.loc[OUTSIDE_UNITS, "spm_unit_net_income"].isna().all()
    assert spm_unit.loc[MEASURED_UNITS, "spm_unit_net_income"].notna().all()
    assert simulation.output_dataset.metadata[SCOPE_RECORD_KEY] == record.model_dump()


def test_year_files_cut_without_the_scope_are_regenerated(tmp_path, certified_sources):
    data_folder = tmp_path / "data"
    create_datasets(
        datasets=["populace_us_2024_acs_local"],
        years=[YEAR],
        data_folder=str(data_folder),
    )
    path = data_folder / f"populace_us_2024_acs_local_year_{YEAR}.h5"
    with h5py.File(path, "a") as file:
        del file[SCOPE_H5_DATASET]
    with pytest.raises(ValueError, match="without its SPM measurement scope"):
        load_datasets(
            datasets=["populace_us_2024_acs_local"],
            years=[YEAR],
            data_folder=str(data_folder),
        )
    certified_sources.clear()
    (regenerated,) = ensure_datasets(
        datasets=["populace_us_2024_acs_local"],
        years=[YEAR],
        data_folder=str(data_folder),
    ).values()
    assert certified_sources == ["populace_us_2024_acs_local", INDEPENDENCE_LIST]
    assert SCOPE_RECORD_KEY in regenerated.metadata


def test_other_sources_get_no_compatibility(tmp_path, monkeypatch):
    source = _write_source(tmp_path / "other.h5")
    created = create_datasets(
        datasets=[source],
        years=[YEAR],
        data_folder=str(tmp_path / "data"),
        allow_unmanaged=True,
    )
    (dataset,) = created.values()
    assert SCOPE_RECORD_KEY not in dataset.metadata
    assert OUTSIDE_SPM_MEASUREMENT not in pd.DataFrame(dataset.data.spm_unit).columns
    assert INDEPENDENCE_ROLE not in pd.DataFrame(dataset.data.person).columns


def test_regional_filtering_keeps_the_scope(tmp_path):
    from policyengine.core.scoping_strategy import RowFilterStrategy

    simulation = Simulation(
        dataset=_dataset(tmp_path),
        tax_benefit_model_version=pe.us.model,
        scoping_strategy=RowFilterStrategy(
            variable_name="county_fips", variable_value=["06037", "06075"]
        ),
    )
    simulation.run()
    spm_unit = _frame(simulation, "spm_unit")
    assert spm_unit.index.tolist() == [1, 2, 4, 5]
    assert spm_unit["spm_unit_net_income"].isna().tolist() == [
        False,
        True,
        False,
        False,
    ]
    assert simulation.output_dataset.metadata[SCOPE_RECORD_KEY] == _scope_record()
