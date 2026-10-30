"""The years a country model supports a single-year dataset for (#729).

A supported year is one the installed country model projects its single-year
dataset to. ``supported_years`` builds the multi-year dataset with the
model's ``extend_single_year_dataset``, as the model's own ``Simulation``
does for a single-year file, and keeps the years from the data year onwards.
policyengine-core fills any other year by carrying the latest projected
inputs forward or uprating them, so ``create_datasets`` and
``ensure_datasets`` refuse such a year before creating any year file, unless
``allow_unsupported_years=True``.

Most tests stub the country model and the dataset, so they run without
either. One test per country runs the rule on the installed model with a tiny
dataset, and one per country runs it on the bundle's default dataset when
``POLICYENGINE_UK_DEFAULT_DATASET`` or ``POLICYENGINE_US_DEFAULT_DATASET``
names that file.
"""

from __future__ import annotations

import importlib
import inspect
import os
import pickle
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from policyengine.tax_benefit_models.uk import datasets as uk_datasets
from policyengine.tax_benefit_models.us import datasets as us_datasets

COUNTRY_DATASET_MODULES = {"uk": uk_datasets, "us": us_datasets}
COUNTRY_PACKAGES = {"uk": "policyengine_uk", "us": "policyengine_us"}
UK_PARAMETERS = object()


@pytest.fixture
def dataset_years():
    """The module under test, imported per test so each test fails alone."""

    return importlib.import_module("policyengine.provenance.dataset_years")


def _install_modules(monkeypatch, modules: dict[str, dict[str, object]]) -> None:
    """Serve stand-in modules under the given names for one test."""

    for module_name, attributes in modules.items():
        module = types.ModuleType(module_name)
        for attribute_name, value in attributes.items():
            setattr(module, attribute_name, value)
        monkeypatch.setitem(sys.modules, module_name, module)


def _stub_uk_model(monkeypatch, *, data_year, projected_years, multi_year=None):
    """Stand in for policyengine-uk; returns the extension's recorded calls."""

    extension_calls = []

    def load_single_year_dataset(file_path):
        return SimpleNamespace(time_period=str(data_year), file_path=file_path)

    def extend_single_year_dataset(dataset, parameters):
        extension_calls.append((dataset, parameters))
        if multi_year is not None:
            return multi_year
        return SimpleNamespace(years=list(projected_years))

    _install_modules(
        monkeypatch,
        {
            "policyengine_uk.data.dataset_schema": {
                "UKSingleYearDataset": load_single_year_dataset
            },
            "policyengine_uk.data.economic_assumptions": {
                "extend_single_year_dataset": extend_single_year_dataset
            },
            "policyengine_uk.system": {
                "system": SimpleNamespace(parameters=UK_PARAMETERS)
            },
        },
    )
    return extension_calls


def _stub_us_model(monkeypatch, *, data_year, projected_years, forecast_years):
    """Stand in for policyengine-us and spm-calculator; returns the
    extension's recorded calls."""

    extension_calls = []

    def load_single_year_dataset(file_path):
        return SimpleNamespace(time_period=str(data_year), file_path=file_path)

    def extend_single_year_dataset(*arguments, **keyword_arguments):
        extension_calls.append((arguments, keyword_arguments))
        return SimpleNamespace(years=list(projected_years))

    _install_modules(
        monkeypatch,
        {
            "policyengine_us.data.dataset_schema": {
                "USSingleYearDataset": load_single_year_dataset
            },
            "policyengine_us.data.economic_assumptions": {
                "extend_single_year_dataset": extend_single_year_dataset
            },
            "spm_calculator.rolling_forecast": {
                "load_forecast": lambda: SimpleNamespace(years=tuple(forecast_years))
            },
        },
    )
    return extension_calls


# --- The UK rule --------------------------------------------------------------


def test_uk_years_run_from_the_data_year_to_the_projection_end(
    monkeypatch, dataset_years
):
    _stub_uk_model(monkeypatch, data_year=2024, projected_years=range(2024, 2033))

    assert dataset_years.supported_years("uk", "data.h5") == list(range(2024, 2033))


def test_uk_years_the_projection_holds_before_the_data_year_are_not_supported(
    monkeypatch, dataset_years
):
    _stub_uk_model(
        monkeypatch, data_year=2025, projected_years=[2023, 2024, 2025, 2026]
    )

    assert dataset_years.supported_years("uk", "data.h5") == [2025, 2026]


def test_uk_projection_is_built_as_policyengine_uk_simulation_builds_it(
    monkeypatch, dataset_years
):
    """The single-year file is extended with the system's parameters and the
    model's default projection end, as ``policyengine_uk.Simulation`` does."""

    extension_calls = _stub_uk_model(
        monkeypatch, data_year=2024, projected_years=[2024, 2025]
    )

    dataset_years.supported_years("uk", Path("source.h5"))

    ((extended_dataset, parameters),) = extension_calls
    assert extended_dataset.file_path == "source.h5"
    assert parameters is UK_PARAMETERS


def test_uk_projection_without_a_years_attribute_reads_its_datasets(
    monkeypatch, dataset_years
):
    multi_year = SimpleNamespace(datasets={2026: None, 2024: None, 2025: None})
    _stub_uk_model(
        monkeypatch, data_year=2024, projected_years=[], multi_year=multi_year
    )

    assert dataset_years.supported_years("uk", "data.h5") == [2024, 2025, 2026]


def _write_tiny_uk_dataset(path: Path, fiscal_year: int = 2024) -> Path:
    from policyengine_uk.data import UKSingleYearDataset

    UKSingleYearDataset(
        person=pd.DataFrame(
            {
                "person_id": [1],
                "person_benunit_id": [1],
                "person_household_id": [1],
                "age": [40],
            }
        ),
        benunit=pd.DataFrame({"benunit_id": [1]}),
        household=pd.DataFrame(
            {"household_id": [1], "household_weight": [1.0], "region": ["LONDON"]}
        ),
        fiscal_year=fiscal_year,
    ).save(str(path))
    return path


def test_uk_rule_on_the_installed_model_ends_at_its_default_projection_end(
    tmp_path, dataset_years
):
    pytest.importorskip("policyengine_uk")
    from policyengine_uk.data.capital_gains_projection import CGT_INDEX_PATH
    from policyengine_uk.data.economic_assumptions import PROJECTION_END_YEAR
    from policyengine_uk.system import system

    capital_gains_projection = system.parameters.get_child(CGT_INDEX_PATH).metadata[
        "projection"
    ]
    projection_end = min(
        PROJECTION_END_YEAR,
        capital_gains_projection.get("end_year", PROJECTION_END_YEAR),
    )
    path = _write_tiny_uk_dataset(tmp_path / "tiny_uk_2024.h5")

    assert dataset_years.supported_years("uk", path) == list(
        range(2024, projection_end + 1)
    )


# --- The US rule --------------------------------------------------------------


def test_us_years_end_at_the_policyengine_us_projection_end(monkeypatch, dataset_years):
    _stub_us_model(
        monkeypatch,
        data_year=2024,
        projected_years=range(2024, 2036),
        forecast_years=range(2022, 2041),
    )

    assert dataset_years.supported_years("us", "data.h5") == list(range(2022, 2036))


def test_us_years_after_the_last_spm_forecast_year_are_not_supported(
    monkeypatch, dataset_years
):
    """With policyengine-us#10227 the projection reaches 2036, but the SPM
    forecast of spm-calculator 1.0.0 ends in 2035."""

    _stub_us_model(
        monkeypatch,
        data_year=2024,
        projected_years=range(2024, 2037),
        forecast_years=range(2022, 2036),
    )

    assert dataset_years.supported_years("us", "data.h5") == list(range(2022, 2036))


def test_us_allowance_adds_2022_and_2023_before_the_data_year(
    monkeypatch, dataset_years
):
    _stub_us_model(
        monkeypatch,
        data_year=2024,
        projected_years=range(2024, 2031),
        forecast_years=range(2022, 2036),
    )

    assert dataset_years.US_EARLY_YEAR_ALLOWANCE == frozenset({2022, 2023})
    assert dataset_years.supported_years("us", "data.h5") == list(range(2022, 2031))


def test_us_years_before_the_data_year_outside_the_allowance_are_not_supported(
    monkeypatch, dataset_years
):
    _stub_us_model(
        monkeypatch,
        data_year=2024,
        projected_years=range(2019, 2031),
        forecast_years=range(2018, 2036),
    )

    assert dataset_years.supported_years("us", "data.h5") == list(range(2022, 2031))


def test_removing_the_us_allowance_is_a_change_to_one_constant(
    monkeypatch, dataset_years
):
    _stub_us_model(
        monkeypatch,
        data_year=2024,
        projected_years=range(2024, 2036),
        forecast_years=range(2022, 2036),
    )
    monkeypatch.setattr(dataset_years, "US_EARLY_YEAR_ALLOWANCE", frozenset())

    assert dataset_years.supported_years("us", "data.h5") == list(range(2024, 2036))


def test_us_projection_uses_the_models_default_end_year(monkeypatch, dataset_years):
    """``policyengine_us.Microsimulation`` passes the single-year dataset alone,
    so ``extend_single_year_dataset`` projects to its default end year."""

    extension_calls = _stub_us_model(
        monkeypatch,
        data_year=2024,
        projected_years=range(2024, 2036),
        forecast_years=range(2022, 2036),
    )

    dataset_years.supported_years("us", Path("source.h5"))

    ((arguments, keyword_arguments),) = extension_calls
    assert [dataset.file_path for dataset in arguments] == ["source.h5"]
    assert keyword_arguments == {}


def _write_tiny_us_dataset(path: Path, year: int = 2024) -> Path:
    person = pd.DataFrame(
        {
            "person_id": [1],
            "person_household_id": [1],
            "person_tax_unit_id": [1],
            "person_spm_unit_id": [1],
            "person_family_id": [1],
            "person_marital_unit_id": [1],
            "person_weight": [1.0],
            "age": [40],
            "employment_income": [30_000.0],
        }
    )
    frames = {"person": person}
    for group in ("household", "tax_unit", "spm_unit", "family", "marital_unit"):
        frames[group] = pd.DataFrame({f"{group}_id": [1], f"{group}_weight": [1.0]})
    frames["household"]["state_code"] = ["CA"]
    with pd.HDFStore(path, mode="w") as store:
        for entity, frame in frames.items():
            store.put(entity, frame, format="table", data_columns=True)
        store.put("_time_period", pd.Series([year]), format="table")
    return path


def test_us_rule_on_the_installed_model(tmp_path, dataset_years):
    pytest.importorskip("policyengine_us")
    from policyengine_us.data.economic_assumptions import _get_default_end_year
    from policyengine_us.system import system
    from spm_calculator.rolling_forecast import load_forecast

    last_year = min(_get_default_end_year(system), max(load_forecast().years))
    path = _write_tiny_us_dataset(tmp_path / "tiny_us_2024.h5")

    assert dataset_years.supported_years("us", path) == sorted(
        set(range(2024, last_year + 1)) | {2022, 2023}
    )


def test_an_unknown_country_is_refused(dataset_years):
    with pytest.raises(ValueError, match="Unknown country 'ca'"):
        dataset_years.supported_years("ca", "data.h5")


# --- The error ----------------------------------------------------------------


def test_the_error_names_the_year_the_country_and_the_supported_years(
    dataset_years,
):
    error = dataset_years.UnsupportedDatasetYearError(
        "us", "populace_us_2024", [2036], range(2022, 2036)
    )

    assert isinstance(error, ValueError)
    assert error.country_id == "us"
    assert error.dataset == "populace_us_2024"
    assert error.years == [2036]
    assert error.supported_years == list(range(2022, 2036))
    message = str(error)
    assert message.startswith(
        "US dataset 'populace_us_2024' is not supported for year 2036. "
        "Supported years: 2022–2035."
    )
    assert "allow_unsupported_years=True" in message


def test_the_error_lists_each_unsupported_year_and_each_run_of_supported_years(
    dataset_years,
):
    error = dataset_years.UnsupportedDatasetYearError(
        "uk", "data.h5", [2040, 2021, 2040], [2025, 2022, 2023]
    )

    assert error.years == [2021, 2040]
    assert error.supported_years == [2022, 2023, 2025]
    assert str(error).startswith(
        "UK dataset 'data.h5' is not supported for years 2021, 2040. "
        "Supported years: 2022–2023, 2025."
    )


def test_the_error_says_when_no_year_is_supported(dataset_years):
    error = dataset_years.UnsupportedDatasetYearError("uk", "data.h5", [2030], [])

    assert "Supported years: none." in str(error)


def test_the_error_keeps_its_contents_through_pickling(dataset_years):
    error = dataset_years.UnsupportedDatasetYearError(
        "us", "populace_us_2024", [2036], range(2022, 2036)
    )

    restored = pickle.loads(pickle.dumps(error))

    assert type(restored) is dataset_years.UnsupportedDatasetYearError
    assert str(restored) == str(error)
    assert (
        restored.country_id,
        restored.dataset,
        restored.years,
        restored.supported_years,
    ) == ("us", "populace_us_2024", [2036], list(range(2022, 2036)))


def test_the_function_and_error_are_exported_from_provenance(dataset_years):
    from policyengine import provenance

    assert provenance.supported_years is dataset_years.supported_years
    assert (
        provenance.UnsupportedDatasetYearError
        is dataset_years.UnsupportedDatasetYearError
    )


# --- The refusal --------------------------------------------------------------


def test_the_refusal_names_only_the_unsupported_years(monkeypatch, dataset_years):
    monkeypatch.setattr(
        dataset_years, "supported_years", lambda country_id, dataset_path: [2024, 2025]
    )

    with pytest.raises(dataset_years.UnsupportedDatasetYearError) as refusal:
        dataset_years.refuse_unsupported_years(
            "uk", "data", "data.h5", [2025, 2026, 2023]
        )

    assert refusal.value.years == [2023, 2026]
    assert refusal.value.supported_years == [2024, 2025]
    dataset_years.refuse_unsupported_years("uk", "data", "data.h5", [2024, 2025])


def test_the_refusal_reads_no_dataset_when_no_year_is_requested(
    monkeypatch, dataset_years
):
    def refuse_to_compute(country_id, dataset_path):
        raise AssertionError("supported years were computed for no year")

    monkeypatch.setattr(dataset_years, "supported_years", refuse_to_compute)

    dataset_years.refuse_unsupported_years("us", "data", "missing.h5", [])


# --- create_datasets and ensure_datasets ----------------------------------------


class ReachedCreation(Exception):
    """Raised by the stand-in Microsimulation: creation began."""


@pytest.fixture
def country_microsimulation(monkeypatch, request):
    """A stand-in country package whose Microsimulation records its calls."""

    country_id = request.param
    microsimulation = Mock(side_effect=ReachedCreation)
    monkeypatch.setitem(
        sys.modules,
        COUNTRY_PACKAGES[country_id],
        SimpleNamespace(Microsimulation=microsimulation),
    )
    return country_id, microsimulation


def _source_file(path: Path) -> str:
    """A local source; its contents are never read because the rule is stubbed."""

    path.write_bytes(b"source dataset")
    return str(path)


def _stub_supported_years(monkeypatch, dataset_years, supported_by_path):
    computed_for = []

    def supported_years(country_id, dataset_path):
        computed_for.append((country_id, str(dataset_path)))
        return supported_by_path[str(dataset_path)]

    monkeypatch.setattr(dataset_years, "supported_years", supported_years)
    return computed_for


@pytest.mark.parametrize("country_microsimulation", ["uk", "us"], indirect=True)
@pytest.mark.parametrize("helper_name", ["create_datasets", "ensure_datasets"])
def test_an_unsupported_year_is_refused_before_any_year_file_is_created(
    tmp_path, monkeypatch, dataset_years, country_microsimulation, helper_name
):
    country_id, microsimulation = country_microsimulation
    source = _source_file(tmp_path / "tiny.h5")
    computed_for = _stub_supported_years(
        monkeypatch, dataset_years, {source: [2024, 2025]}
    )
    data_folder = tmp_path / "data"
    helper = getattr(COUNTRY_DATASET_MODULES[country_id], helper_name)

    with pytest.raises(dataset_years.UnsupportedDatasetYearError) as refusal:
        helper(
            datasets=[source],
            years=[2025, 2026],
            data_folder=str(data_folder),
            allow_unmanaged=True,
        )

    assert refusal.value.country_id == country_id
    assert refusal.value.dataset == source
    assert refusal.value.years == [2026]
    assert refusal.value.supported_years == [2024, 2025]
    assert computed_for == [(country_id, source)]
    microsimulation.assert_not_called()
    assert not list(data_folder.glob("*_year_*.h5"))


@pytest.mark.parametrize("country_microsimulation", ["uk", "us"], indirect=True)
def test_every_dataset_is_checked_before_any_year_file_is_created(
    tmp_path, monkeypatch, dataset_years, country_microsimulation
):
    country_id, microsimulation = country_microsimulation
    supported_source = _source_file(tmp_path / "supported.h5")
    unsupported_source = _source_file(tmp_path / "unsupported.h5")
    _stub_supported_years(
        monkeypatch,
        dataset_years,
        {supported_source: [2024, 2025, 2026], unsupported_source: [2024, 2025]},
    )

    with pytest.raises(dataset_years.UnsupportedDatasetYearError) as refusal:
        COUNTRY_DATASET_MODULES[country_id].create_datasets(
            datasets=[supported_source, unsupported_source],
            years=[2026],
            data_folder=str(tmp_path / "data"),
            allow_unmanaged=True,
        )

    assert refusal.value.dataset == unsupported_source
    microsimulation.assert_not_called()


@pytest.mark.parametrize("country_microsimulation", ["uk", "us"], indirect=True)
@pytest.mark.parametrize("helper_name", ["create_datasets", "ensure_datasets"])
def test_a_supported_year_goes_on_to_creation(
    tmp_path, monkeypatch, dataset_years, country_microsimulation, helper_name
):
    country_id, microsimulation = country_microsimulation
    source = _source_file(tmp_path / "tiny.h5")
    _stub_supported_years(monkeypatch, dataset_years, {source: [2024, 2025, 2026]})
    helper = getattr(COUNTRY_DATASET_MODULES[country_id], helper_name)

    with pytest.raises(ReachedCreation):
        helper(
            datasets=[source],
            years=[2025, 2026],
            data_folder=str(tmp_path / "data"),
            allow_unmanaged=True,
        )

    microsimulation.assert_called_once()


@pytest.mark.parametrize("country_microsimulation", ["uk", "us"], indirect=True)
@pytest.mark.parametrize("helper_name", ["create_datasets", "ensure_datasets"])
def test_the_opt_out_creates_an_unsupported_year_without_the_check(
    tmp_path, monkeypatch, dataset_years, country_microsimulation, helper_name
):
    country_id, microsimulation = country_microsimulation
    source = _source_file(tmp_path / "tiny.h5")

    def refuse_to_compute(country_id, dataset_path):
        raise AssertionError("the opt-out still computed supported years")

    monkeypatch.setattr(dataset_years, "supported_years", refuse_to_compute)
    helper = getattr(COUNTRY_DATASET_MODULES[country_id], helper_name)

    with pytest.raises(ReachedCreation):
        helper(
            datasets=[source],
            years=[2040],
            data_folder=str(tmp_path / "data"),
            allow_unmanaged=True,
            allow_unsupported_years=True,
        )

    microsimulation.assert_called_once()


@pytest.mark.parametrize("country_id", ["uk", "us"])
@pytest.mark.parametrize("allow_unsupported_years", [False, True])
def test_ensure_datasets_passes_the_opt_out_to_create_datasets(
    tmp_path, monkeypatch, country_id, allow_unsupported_years
):
    module = COUNTRY_DATASET_MODULES[country_id]
    create_datasets = Mock(return_value={"created": None})
    monkeypatch.setattr(module, "create_datasets", create_datasets)
    source = _source_file(tmp_path / "tiny.h5")

    module.ensure_datasets(
        datasets=[source],
        years=[2026],
        data_folder=str(tmp_path / "data"),
        allow_unmanaged=True,
        allow_unsupported_years=allow_unsupported_years,
    )

    create_datasets.assert_called_once_with(
        datasets=[source],
        years=[2026],
        data_folder=str(tmp_path / "data"),
        allow_unmanaged=True,
        allow_unsupported_years=allow_unsupported_years,
    )


# --- The UK provenance code uses the same rule ----------------------------------


def test_the_uk_qualification_check_projects_with_the_public_rule(
    monkeypatch, dataset_years
):
    from policyengine.provenance import uk_candidate

    computed_for = _stub_supported_years(
        monkeypatch, dataset_years, {"candidate.h5": [2024, 2025]}
    )
    default_projection = (
        inspect.signature(uk_candidate.supported_years)
        .parameters["projected_years"]
        .default
    )

    assert default_projection(Path("candidate.h5")) == [2024, 2025]
    assert computed_for == [("uk", "candidate.h5")]


def test_execution_receipts_project_with_the_public_rule(monkeypatch, dataset_years):
    from policyengine.provenance import receipt

    computed_for = _stub_supported_years(
        monkeypatch, dataset_years, {"run.h5": [2024, 2025, 2026]}
    )
    uncached_projection = receipt._projected_years.__wrapped__

    assert uncached_projection("run.h5", "0" * 64, "2.151.0") == (2024, 2025, 2026)
    assert computed_for == [("uk", "run.h5")]


# --- The bundle's default datasets on the pinned models -------------------------

#: What ``supported_years`` returns for each bundle default dataset under the
#: pinned policyengine-uk 2.151.0, policyengine-us 2.2.1 and spm-calculator
#: 1.0.0 (measured 30 Oct 2026).
PINNED_DEFAULT_DATASET_YEARS = {
    "uk": list(range(2024, 2033)),
    "us": list(range(2022, 2036)),
}


@pytest.mark.parametrize("country_id", ["uk", "us"])
def test_the_default_dataset_is_supported_for_the_pinned_years(
    country_id, dataset_years
):
    """Runs only with the bundle's default dataset file, named by
    POLICYENGINE_UK_DEFAULT_DATASET or POLICYENGINE_US_DEFAULT_DATASET."""

    variable = f"POLICYENGINE_{country_id.upper()}_DEFAULT_DATASET"
    path = os.environ.get(variable)
    if not path:
        pytest.skip(f"set {variable} to the bundle's default {country_id} dataset")
    pytest.importorskip(COUNTRY_PACKAGES[country_id])

    assert (
        dataset_years.supported_years(country_id, path)
        == PINNED_DEFAULT_DATASET_YEARS[country_id]
    )
