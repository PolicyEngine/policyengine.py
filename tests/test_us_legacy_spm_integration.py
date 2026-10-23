"""Backward compatibility with legacy US SPM sources, in real model runs.

#597 keeps ACS group-quarters units out of the SPM measurement; #598 supplies
the certified SPM independence role for ASEC/PUF records. The tests use tiny
synthetic households in California:

- SPM unit 1: an ACS family (adult head, child), receiving housing assistance.
- SPM unit 2: an ACS institutional group-quarters child aged 16.
- SPM unit 3: an ACS noninstitutional group-quarters adult aged 70, receiving
  housing assistance.
- SPM unit 4: an ASEC adult head.
- SPM unit 5: an ASEC teen aged 16, alone in an SPM unit inside household 4,
  whom the certified independence list marks independent.

Without the declarations, units 2 and 5 have no classified adult and stop
every SPM calculation. Synthetic files are served under the registered legacy
source's identity by patching the materialiser, so nothing is downloaded.
"""

from __future__ import annotations

import importlib
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
from policyengine.tax_benefit_models.us.legacy_spm import (  # noqa: E402
    INDEPENDENCE_ROLE,
    RECORD_H5_DATASET,
    RECORD_KEY,
    UNIVERSE_VARIABLE,
    LegacySPMRecord,
    declarations,
    expected_profile,
    record,
    runs,
)
from policyengine.tax_benefit_models.us.legacy_spm.model_adapter import (  # noqa: E402
    FLOAT_INDICATORS,
    SPM_MEASUREMENT_VARIABLES,
)
from policyengine.tax_benefit_models.us.legacy_spm.registry import (  # noqa: E402
    POPULACE_US_2024_ACS_LOCAL_BUILD_O,
    POPULACE_US_2024_ACS_LOCAL_MICROCOSM_1263,
)
from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest  # noqa: E402

# The ``us`` package's ``model`` attribute is the model version, not the module.
us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")

BUILD_O = POPULACE_US_2024_ACS_LOCAL_BUILD_O
LIST_PIN = BUILD_O.independence_list
YEAR = 2026
ACS = "acs_2024_1yr"
OUTSIDE_UNITS = [2, 3]
MEASURED_UNITS = [1, 4, 5]
GROUP_QUARTERS_COUNTIES = {"06075", "06001"}
REFORM = {"gov.irs.credits.ctc.amount.base[0].amount": 3_000}
SPM_UNIT_OUTPUTS = [
    name for name in SPM_MEASUREMENT_VARIABLES if name != "person_in_poverty"
]
SPM_EXTRAS = {"spm_unit": SPM_UNIT_OUTPUTS, "person": ["person_in_poverty"]}
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
    """Tables in the legacy source's layout, with its record-type evidence."""
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


def _record() -> LegacySPMRecord:
    return LegacySPMRecord(
        profile=expected_profile(BUILD_O),
        outside_spm_units=2,
        included_spm_units=3,
        independence_list_people=2,
    )


def _dataset(directory, *, declared=True, drop_units=(), teen_independent=True):
    """A year-file-like dataset; ``declared`` adds the stored declarations."""
    frames = {name: frame.copy() for name, frame in _source_frames().items()}
    person = frames["person"]
    person["person_weight"] = 1.0
    for entity in ("household", "spm_unit", "tax_unit", "family", "marital_unit"):
        person[f"{entity}_id"] = person.pop(f"person_{entity}_id")
    if declared:
        frames["spm_unit"][UNIVERSE_VARIABLE] = [
            "INCLUDED",
            "OUTSIDE",
            "OUTSIDE",
            "INCLUDED",
            "INCLUDED",
        ]
        person[INDEPENDENCE_ROLE] = [True, False, False, False, True, teen_independent]
    if drop_units:
        frames["person"] = person = person[
            ~person["spm_unit_id"].isin(drop_units)
        ].reset_index(drop=True)
        for entity in ("household", "spm_unit", "tax_unit", "family", "marital_unit"):
            kept = frames[entity][f"{entity}_id"].isin(set(person[f"{entity}_id"]))
            frames[entity] = frames[entity][kept].reset_index(drop=True)
    person.drop(columns=["RELSHIPP", "person_support_channel"], inplace=True)
    frames["household"].drop(columns="TYPEHUGQ", inplace=True)
    return PolicyEngineUSDataset(
        name="legacy-spm-source",
        description="Uncertified synthetic legacy-source households",
        filepath=str(directory / "input.h5"),
        year=YEAR,
        metadata={RECORD_KEY: _record().model_dump(mode="json")} if declared else {},
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
def declared_run(tmp_path_factory, provider_calls):
    """A reform run over the declared households, recording provider calls."""
    from policyengine_us.spm import CountyRequiringSPMProvider

    original = CountyRequiringSPMProvider._amounts

    def spy(self, year, adults, children, tenure, county):
        provider_calls.append((adults, children, county))
        return original(self, year, adults, children, tenure, county)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(CountyRequiringSPMProvider, "_amounts", spy)
        simulation = Simulation(
            dataset=_dataset(tmp_path_factory.mktemp("declared")),
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
    dataset = _dataset(
        tmp_path_factory.mktemp("reference"), declared=False, drop_units=(2,)
    )
    # The same certified role, so the independent teen's unit (5) is measured.
    dataset.data.person[INDEPENDENCE_ROLE] = [True, False, False, True, True]
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy=REFORM,
        extra_variables=SPM_EXTRAS,
    )
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
            dataset=_dataset(tmp_path_factory.mktemp("ordinary"), declared=False),
            tax_benefit_model_version=pe.us.model,
            policy=REFORM,
        )
        simulation.run()
    return simulation


def test_the_unmodified_model_cannot_measure_the_population(tmp_path):
    from spm_calculator.errors import SPMInputError

    simulation = Simulation(
        dataset=_dataset(tmp_path, declared=False),
        tax_benefit_model_version=pe.us.model,
    )
    with pytest.raises(SPMInputError) as error:
        simulation.run()
    assert error.value.code == "SPM_COMPOSITION_REQUIRED"


def test_outside_units_have_no_spm_values(declared_run):
    spm_unit = _frame(declared_run, "spm_unit")
    for name in SPM_UNIT_OUTPUTS:
        assert spm_unit.loc[OUTSIDE_UNITS, name].isna().all(), name
        assert spm_unit.loc[MEASURED_UNITS, name].notna().all(), name
    person = _frame(declared_run, "person")
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
    recorded = LegacySPMRecord.model_validate(
        declared_run.output_dataset.metadata[RECORD_KEY]
    )
    assert recorded.model_mode == "override"
    assert recorded.profile == expected_profile(BUILD_O)


def test_outside_units_never_reach_the_spm_provider(declared_run, provider_calls):
    assert provider_calls
    assert not {county for _, _, county in provider_calls} & GROUP_QUARTERS_COUNTIES
    assert all(adults >= 1 for adults, _, _ in provider_calls)


def test_measured_units_keep_the_canonical_spm_values(declared_run, measured_reference):
    declared = _frame(declared_run, "spm_unit")
    reference = _frame(measured_reference, "spm_unit")
    for name in SPM_UNIT_OUTPUTS:
        if name == "spm_unit_income_decile":
            continue  # ranks depend on which units are ranked
        np.testing.assert_array_equal(
            declared.loc[MEASURED_UNITS, name].to_numpy(dtype=float),
            reference.loc[MEASURED_UNITS, name].to_numpy(dtype=float),
            err_msg=name,
        )
    # The measured family's subsidy is capped through the installed formula;
    # the assisted group-quarters adult is not measured.
    assert declared.loc[1, "spm_unit_capped_housing_subsidy"] > 0
    assert reference.loc[3, "spm_unit_capped_housing_subsidy"] > 0
    assert np.isnan(declared.loc[3, "spm_unit_capped_housing_subsidy"])


def test_ordinary_calculations_are_unchanged_for_everyone(
    declared_run, ordinary_reference
):
    for entity, names in ORDINARY.items():
        declared = _frame(declared_run, entity)
        reference = _frame(ordinary_reference, entity)
        assert declared.index.equals(reference.index)
        for name in names:
            np.testing.assert_array_equal(
                declared[name].to_numpy(), reference[name].to_numpy(), err_msg=name
            )
            assert np.isfinite(declared[name].to_numpy(dtype=float)).all(), name


def test_poverty_rates_cover_measured_people_only(declared_run):
    rates = calculate_us_poverty_rates(declared_run).dataframe
    # People 3 and 4 are outside; everyone has weight 1.
    assert rates["total_population"].tolist() == [4.0, 4.0]
    by_age = calculate_us_poverty_by_age(declared_run).dataframe
    child = by_age[by_age["filter_group"] == "child"].iloc[0]
    # Child 2 and teen 6 are measured; group-quarters teen 3 is not.
    assert child["total_population"] == 2.0


def test_a_group_with_nobody_measured_has_no_rate(declared_run):
    seniors = Poverty(
        simulation=declared_run,
        poverty_variable="spm_unit_is_in_spm_poverty",
        entity="person",
        filter_variable="age",
        filter_variable_geq=65,
    )
    seniors.run()
    # The only senior lives in group quarters, outside the measurement.
    assert seniors.total_population == 0.0
    assert seniors.rate is None


def test_poverty_flags_are_not_summed_onto_groups(declared_run):
    poverty = Poverty(
        simulation=declared_run,
        poverty_variable="spm_unit_is_in_spm_poverty",
        entity="household",
    )
    with pytest.raises(ValueError, match="summarise it for people"):
        poverty.run()


def test_the_declarations_reach_the_baseline_and_stay_private(tmp_path, monkeypatch):
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
    assert all(UNIVERSE_VARIABLE in policy.variables for policy in systems)

    systems.clear()
    undeclared = _dataset(tmp_path, declared=False, drop_units=(2,))
    undeclared.data.person[INDEPENDENCE_ROLE] = [True, False, False, True, True]
    unaffected = Simulation(dataset=undeclared, tax_benefit_model_version=pe.us.model)
    unaffected.run()
    assert UNIVERSE_VARIABLE not in systems[0].variables
    assert UNIVERSE_VARIABLE not in system.variables
    assert system.variables["spm_unit_is_in_spm_poverty"].value_type is bool
    assert _frame(unaffected, "spm_unit")["spm_unit_is_in_spm_poverty"].dtype == bool
    assert RECORD_KEY not in unaffected.output_dataset.metadata


@pytest.mark.parametrize("abolish_hud", [False, True])
def test_structural_resource_reforms_cannot_bypass_the_declarations(
    tmp_path, abolish_hud
):
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


def test_regional_filtering_keeps_the_declarations(tmp_path):
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


def test_a_declared_dataset_must_be_current_and_complete(tmp_path):
    stale = _dataset(tmp_path)
    stale.metadata[RECORD_KEY]["profile"]["adapter_revision"] = 0
    with pytest.raises(ValueError, match="out of date"):
        Simulation(dataset=stale, tax_benefit_model_version=pe.us.model).run()

    unreadable = _dataset(tmp_path)
    unreadable.metadata[RECORD_KEY] = None
    with pytest.raises(ValueError, match="unreadable"):
        Simulation(dataset=unreadable, tax_benefit_model_version=pe.us.model).run()

    missing_column = _dataset(tmp_path)
    missing_column.data.spm_unit = MicroDataFrame(
        pd.DataFrame(missing_column.data.spm_unit).drop(columns=[UNIVERSE_VARIABLE]),
        weights="spm_unit_weight",
    )
    with pytest.raises(ValueError, match="stores no"):
        Simulation(dataset=missing_column, tax_benefit_model_version=pe.us.model).run()


def test_saved_outputs_are_reused_only_under_the_same_declarations(tmp_path):
    _cache.clear()
    dataset = _dataset(tmp_path)
    # A run record binds the input file's bytes, so write it first.
    dataset.save()
    simulation = Simulation(
        id="legacy-spm", dataset=dataset, tax_benefit_model_version=pe.us.model
    )
    simulation.ensure()
    with h5py.File(simulation.output_dataset.filepath, "r") as file:
        assert RECORD_H5_DATASET in file
    recorded = simulation.release_bundle[RECORD_KEY]
    assert recorded["profile"] == _record().model_dump(mode="json")["profile"]
    payloads = build_simulation_run_record_payloads(simulation)
    assert payloads["results"][RECORD_KEY] == recorded

    _cache.clear()
    restored = Simulation(
        id=simulation.id, dataset=dataset, tax_benefit_model_version=pe.us.model
    )
    restored.load()
    assert restored.output_dataset.metadata[RECORD_KEY] == recorded

    undeclared = Simulation(
        id=simulation.id,
        dataset=_dataset(tmp_path, declared=False),
        tax_benefit_model_version=pe.us.model,
    )
    with pytest.raises(ValueError, match="does not need"):
        undeclared.load()


# --- Legacy source files: year files, raw runs, managed simulations -------


def _write_source(path) -> str:
    with pd.HDFStore(path, mode="w") as store:
        for entity, frame in _source_frames().items():
            store.put(entity, frame, format="table", data_columns=True)
        store.put("_time_period", pd.Series([2024]), format="table")
    return str(path)


def _write_list(path) -> Path:
    pd.DataFrame(
        {
            "person_id": [5, 6],
            "person_spm_unit_id": [4, 5],
            "is_spm_independence_role": [True, True],
        }
    ).to_csv(path, index=False)
    return path


def _bundle_source(path, sha256) -> DatasetSource:
    uri = f"hf://policyengine/populace-us/{Path(path).name}"
    return DatasetSource(
        source_uri=uri,
        path=str(path),
        bundle_dataset=MaterializedDataset(
            data_package_name="microcosm-data",
            repo_type="dataset",
            revision="synthetic",
            source_uri=uri,
            sha256=sha256,
            path=path,
        ),
    )


@pytest.fixture
def legacy_files(tmp_path, monkeypatch):
    """Serve the synthetic source and list as the registered certified files."""
    source = _write_source(tmp_path / "populace_us_2024_acs_local.h5")
    independence_list = _write_list(tmp_path / "source_spm_person_independence.csv")
    requests = []

    def materialize(country, dataset=None, **kwargs):
        requests.append(dataset)
        if dataset == LIST_PIN.bundle_dataset:
            return _bundle_source(independence_list, LIST_PIN.sha256)
        return _bundle_source(source, BUILD_O.source_sha256)

    for module in (us_datasets, us_model, declarations):
        monkeypatch.setattr(module, "materialize_dataset", materialize)
    # The bundle now certifies the microcosm#1263 rebuild. These tests serve
    # the synthetic file as Build O, which stays registered, so the bundle's
    # ACS-local name and URI resolve to Build O's hash here.
    managed = us_datasets._managed_source_sha256
    bundle_sha256 = _bundle_acs_local_sha256()

    def build_o_identity(dataset):
        sha256 = managed(dataset)
        return BUILD_O.source_sha256 if sha256 == bundle_sha256 else sha256

    monkeypatch.setattr(us_datasets, "_managed_source_sha256", build_o_identity)
    return SimpleSources(source=source, requests=requests)


def _bundle_acs_local_sha256() -> str:
    from policyengine.provenance.manifest import get_release_manifest

    return get_release_manifest("us").datasets["populace_us_2024_acs_local"].sha256


class SimpleSources:
    def __init__(self, source, requests):
        self.source = source
        self.requests = requests


def test_year_files_carry_the_declarations_for_every_year(tmp_path, legacy_files):
    data_folder = str(tmp_path / "data")
    years = [2025, 2026, 2027]
    created = create_datasets(
        datasets=["populace_us_2024_acs_local"], years=years, data_folder=data_folder
    )
    assert legacy_files.requests == [
        "populace_us_2024_acs_local",
        LIST_PIN.bundle_dataset,
    ]
    for year in years:
        dataset = created[f"populace_us_2024_acs_local_{year}"]
        spm_unit = pd.DataFrame(dataset.data.spm_unit).set_index("spm_unit_id")
        person = pd.DataFrame(dataset.data.person).set_index("person_id")
        assert spm_unit[UNIVERSE_VARIABLE].tolist() == [
            "INCLUDED",
            "OUTSIDE",
            "OUTSIDE",
            "INCLUDED",
            "INCLUDED",
        ]
        # ACS: household head, as the model computes; ASEC: the list.
        assert person[INDEPENDENCE_ROLE].tolist() == [
            True,
            False,
            False,
            False,
            True,
            True,
        ]
        assert LegacySPMRecord.model_validate(dataset.metadata[RECORD_KEY]) == _record()

    (loaded,) = load_datasets(
        datasets=["populace_us_2024_acs_local"], years=[YEAR], data_folder=data_folder
    ).values()
    simulation = Simulation(dataset=loaded, tax_benefit_model_version=pe.us.model)
    simulation.run()
    spm_unit = _frame(simulation, "spm_unit")
    assert spm_unit.loc[OUTSIDE_UNITS, "spm_unit_net_income"].isna().all()
    assert spm_unit.loc[MEASURED_UNITS, "spm_unit_net_income"].notna().all()


@pytest.mark.parametrize("corruption", ["delete", "garbage", "revision"])
def test_out_of_date_year_files_are_cut_again(
    tmp_path, legacy_files, monkeypatch, corruption
):
    data_folder = tmp_path / "data"
    create_datasets(
        datasets=["populace_us_2024_acs_local"],
        years=[YEAR],
        data_folder=str(data_folder),
    )
    path = data_folder / f"populace_us_2024_acs_local_year_{YEAR}.h5"
    if corruption == "revision":
        monkeypatch.setattr(record, "ADAPTER_REVISION", record.ADAPTER_REVISION + 1)
    else:
        with h5py.File(path, "a") as file:
            del file[RECORD_H5_DATASET]
            if corruption == "garbage":
                file.create_dataset(
                    RECORD_H5_DATASET,
                    data="{not json",
                    dtype=h5py.string_dtype("utf-8"),
                )
    with pytest.raises(ValueError, match="out of date"):
        load_datasets(
            datasets=["populace_us_2024_acs_local"],
            years=[YEAR],
            data_folder=str(data_folder),
        )
    legacy_files.requests.clear()
    (regenerated,) = ensure_datasets(
        datasets=["populace_us_2024_acs_local"],
        years=[YEAR],
        data_folder=str(data_folder),
    ).values()
    assert legacy_files.requests == [
        "populace_us_2024_acs_local",
        LIST_PIN.bundle_dataset,
    ]
    regenerated_record = LegacySPMRecord.model_validate(
        regenerated.metadata[RECORD_KEY]
    )
    assert regenerated_record.profile.adapter_revision == record.ADAPTER_REVISION


def test_a_run_straight_over_a_legacy_source_derives_the_declarations(
    tmp_path, legacy_files, monkeypatch
):
    source_hash = runs.sha256_file(Path(legacy_files.source))
    monkeypatch.setattr(
        runs,
        "legacy_spm_source",
        lambda sha256: BUILD_O if sha256 == source_hash else None,
    )
    raw = PolicyEngineUSDataset(
        name="raw-legacy-source",
        description="The synthetic legacy source file itself",
        filepath=legacy_files.source,
        year=2024,
    )
    _cache.clear()
    simulation = Simulation(
        id="raw-legacy",
        dataset=raw,
        tax_benefit_model_version=pe.us.model,
        policy=REFORM,
    )
    simulation.ensure()
    spm_unit = _frame(simulation, "spm_unit")
    assert spm_unit.loc[OUTSIDE_UNITS, "spm_unit_net_income"].isna().all()
    assert spm_unit.loc[MEASURED_UNITS, "spm_unit_net_income"].notna().all()
    assert (
        LegacySPMRecord.model_validate(
            simulation.output_dataset.metadata[RECORD_KEY]
        ).independence_list_people
        == 2
    )

    _cache.clear()
    restored = Simulation(
        id=simulation.id,
        dataset=raw,
        tax_benefit_model_version=pe.us.model,
        policy=REFORM,
    )
    restored.load()
    assert restored.output_dataset.metadata[RECORD_KEY]["model_mode"] == "override"


def test_a_managed_simulation_of_a_legacy_source_applies_the_declarations(
    legacy_files,
):
    simulation = pe.us.managed_microsimulation(dataset="populace_us_2024_acs_local")
    thresholds = simulation.calculate("spm_unit_spm_threshold", YEAR).values
    assert np.isnan(thresholds[[1, 2]]).all()
    assert np.isfinite(thresholds[[0, 3, 4]]).all()
    in_poverty = simulation.calculate("spm_unit_is_in_spm_poverty", YEAR).values
    assert np.isnan(in_poverty[[1, 2]]).all()
    recorded = LegacySPMRecord.model_validate(
        simulation.policyengine_bundle[RECORD_KEY]
    )
    assert recorded.model_mode == "override"
    assert recorded.outside_spm_units == 2


def test_year_files_load_by_the_sources_uri_as_well_as_its_name(tmp_path, legacy_files):
    """The region registry names the source by URI; that form must work too."""
    from policyengine.provenance.manifest import resolve_dataset_reference

    data_folder = str(tmp_path / "data")
    create_datasets(
        datasets=["populace_us_2024_acs_local"], years=[YEAR], data_folder=data_folder
    )
    uri = resolve_dataset_reference("us", "populace_us_2024_acs_local")
    (loaded,) = load_datasets(
        datasets=[uri], years=[YEAR], data_folder=data_folder
    ).values()
    assert LegacySPMRecord.model_validate(loaded.metadata[RECORD_KEY]) == _record()

    legacy_files.requests.clear()
    (ensured,) = ensure_datasets(
        datasets=[uri], years=[YEAR], data_folder=data_folder
    ).values()
    assert legacy_files.requests == []  # current, so nothing is cut again
    assert ensured.metadata[RECORD_KEY] == loaded.metadata[RECORD_KEY]


def test_a_year_without_a_declaration_is_refused_not_guessed(legacy_files):
    """The source stores 2024 onwards; an earlier year has no declaration."""
    from spm_calculator.errors import SPMInputError

    simulation = pe.us.managed_microsimulation(dataset="populace_us_2024_acs_local")
    with pytest.raises(SPMInputError) as error:
        simulation.calculate("spm_unit_spm_threshold", 2023)
    assert error.value.code == "SPM_UNIVERSE_REQUIRED"


def test_other_sources_get_no_declarations(tmp_path):
    source = _write_source(tmp_path / "other.h5")
    created = create_datasets(
        datasets=[source],
        years=[YEAR],
        data_folder=str(tmp_path / "data"),
        allow_unmanaged=True,
    )
    (dataset,) = created.values()
    assert RECORD_KEY not in dataset.metadata
    assert UNIVERSE_VARIABLE not in pd.DataFrame(dataset.data.spm_unit).columns
    assert INDEPENDENCE_ROLE not in pd.DataFrame(dataset.data.person).columns


# --- The microcosm#1263 rebuild: scope rule, roles stored -------------------

REBUILD = POPULACE_US_2024_ACS_LOCAL_MICROCOSM_1263
#: The roles the rebuilt source stores: ACS head, ASEC head and the ASEC teen
#: who heads their own SPM unit.
REBUILD_ROLES = [True, False, False, False, True, True]


@pytest.fixture
def rebuild_files(tmp_path, monkeypatch):
    """Serve a synthetic source as the bundle's certified ACS-local file."""
    frames = _source_frames()
    frames["person"][INDEPENDENCE_ROLE] = REBUILD_ROLES
    path = tmp_path / "populace_us_2024_acs_local.h5"
    with pd.HDFStore(path, mode="w") as store:
        for entity, frame in frames.items():
            store.put(entity, frame, format="table", data_columns=True)
        store.put("_time_period", pd.Series([2024]), format="table")
    requests = []

    def materialize(country, dataset=None, **kwargs):
        requests.append(dataset)
        return _bundle_source(path, REBUILD.source_sha256)

    for module in (us_datasets, us_model, declarations):
        monkeypatch.setattr(module, "materialize_dataset", materialize)
    return SimpleSources(source=str(path), requests=requests)


def test_the_bundle_certifies_the_rebuild():
    assert _bundle_acs_local_sha256() == REBUILD.source_sha256


def test_the_rebuilds_year_files_carry_its_scope_and_keep_its_roles(
    tmp_path, rebuild_files
):
    from policyengine.provenance.manifest import resolve_dataset_reference

    data_folder = str(tmp_path / "data")
    created = create_datasets(
        datasets=["populace_us_2024_acs_local"], years=[YEAR], data_folder=data_folder
    )
    # No independence list is fetched: the source stores the roles.
    assert rebuild_files.requests == ["populace_us_2024_acs_local"]
    (dataset,) = created.values()
    spm_unit = pd.DataFrame(dataset.data.spm_unit).set_index("spm_unit_id")
    person = pd.DataFrame(dataset.data.person).set_index("person_id")
    assert spm_unit[UNIVERSE_VARIABLE].tolist() == [
        "INCLUDED",
        "OUTSIDE",
        "OUTSIDE",
        "INCLUDED",
        "INCLUDED",
    ]
    assert person[INDEPENDENCE_ROLE].tolist() == REBUILD_ROLES
    assert LegacySPMRecord.model_validate(
        dataset.metadata[RECORD_KEY]
    ) == LegacySPMRecord(
        profile=expected_profile(REBUILD),
        outside_spm_units=2,
        included_spm_units=3,
    )

    # The region registry names the file by URI.
    uri = resolve_dataset_reference("us", "populace_us_2024_acs_local")
    (loaded,) = load_datasets(
        datasets=[uri], years=[YEAR], data_folder=data_folder
    ).values()
    simulation = Simulation(
        dataset=loaded,
        tax_benefit_model_version=pe.us.model,
        extra_variables=SPM_EXTRAS,
    )
    simulation.run()
    spm_unit = _frame(simulation, "spm_unit")
    assert spm_unit.loc[OUTSIDE_UNITS, "spm_unit_spm_threshold"].isna().all()
    assert spm_unit.loc[OUTSIDE_UNITS, "spm_unit_is_in_spm_poverty"].isna().all()
    assert spm_unit.loc[MEASURED_UNITS, "spm_unit_spm_threshold"].notna().all()
    assert spm_unit.loc[MEASURED_UNITS, "spm_unit_net_income"].notna().all()
    assert simulation.output_dataset.metadata[RECORD_KEY]["model_mode"] == "override"


def test_a_managed_simulation_of_the_rebuild_masks_group_quarters(rebuild_files):
    simulation = pe.us.managed_microsimulation(dataset="populace_us_2024_acs_local")
    thresholds = simulation.calculate("spm_unit_spm_threshold", YEAR).values
    assert np.isnan(thresholds[[1, 2]]).all()
    assert np.isfinite(thresholds[[0, 3, 4]]).all()
    in_poverty = simulation.calculate("spm_unit_is_in_spm_poverty", YEAR).values
    assert np.isnan(in_poverty[[1, 2]]).all()
    recorded = LegacySPMRecord.model_validate(
        simulation.policyengine_bundle[RECORD_KEY]
    )
    assert recorded.model_mode == "override"
    assert recorded.outside_spm_units == 2
    assert recorded.independence_list_people is None
