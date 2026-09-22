"""Annual producer artifacts must replace, rather than extend, base-year inputs."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

import policyengine.provenance.dataset_materialization as materialization
from policyengine.provenance.manifest import CountryReleaseManifest


def annual_manifest():
    return CountryReleaseManifest.model_validate(
        {
            "country_id": "us",
            "policyengine_version": "6.0.0",
            "model_package": {"name": "policyengine-us", "version": "2.2.1"},
            "data_package": {
                "name": "microcosm-data",
                "version": "0.1.0",
                "repo_id": "policyengine/populace-us",
                "repo_type": "dataset",
            },
            "default_dataset": "populace_us_2024",
            "datasets": {
                f"populace_us_{year}": {
                    "path": f"annual/populace_us_{year}.h5",
                    "revision": "annual-release",
                    "sha256": str(year % 10) * 64,
                }
                for year in (2024, 2025)
            },
            "dataset_years": {
                "populace_us_2024": {
                    "2024": "populace_us_2024",
                    "2025": "populace_us_2025",
                }
            },
        }
    )


def test_annual_mapping_round_trips_and_selects_pinned_year(monkeypatch, tmp_path):
    manifest = annual_manifest()
    assert manifest.dataset_years["populace_us_2024"][2025] == "populace_us_2025"
    assert (
        CountryReleaseManifest.model_validate_json(manifest.model_dump_json())
        == manifest
    )
    monkeypatch.setattr(
        materialization, "get_release_manifest", lambda country: manifest
    )
    use = Mock()
    monkeypatch.setattr(materialization, "_use_bundle_dataset", use)

    materialization.materialize_dataset("us", year=2025, data_dir=tmp_path)

    assert use.call_args.args[:2] == ("us", "populace_us_2025")


def test_annual_family_rejects_uncovered_year_before_download(monkeypatch):
    monkeypatch.setattr(
        materialization, "get_release_manifest", lambda country: annual_manifest()
    )
    use = Mock()
    monkeypatch.setattr(materialization, "_use_bundle_dataset", use)
    with pytest.raises(ValueError, match="2026.*coverage"):
        materialization.materialize_dataset("us", year=2026)
    use.assert_not_called()


@pytest.mark.parametrize("change", ["unknown", "no_digest", "no_revision", "not_h5"])
def test_annual_manifest_rejects_unpinned_or_unknown_artifact(change):
    payload = annual_manifest().model_dump(mode="json")
    if change == "unknown":
        payload["dataset_years"]["populace_us_2024"]["2025"] = "absent"
    else:
        reference = payload["datasets"]["populace_us_2025"]
        reference[
            {"no_digest": "sha256", "no_revision": "revision", "not_h5": "path"}[change]
        ] = "other.csv" if change == "not_h5" else None
    with pytest.raises(ValidationError):
        CountryReleaseManifest.model_validate(payload)


@pytest.mark.parametrize(
    "years, error",
    [
        (
            {2024: "populace_us_2024", 2026: "populace_us_2025"},
            "contiguous",
        ),
        ({2025: "populace_us_2025"}, "earliest year.*family"),
        (
            {2024: "populace_us_2025", 2025: "populace_us_2024"},
            "earliest year.*family",
        ),
    ],
)
def test_annual_manifest_rejects_incomplete_family_history(years, error):
    payload = annual_manifest().model_dump(mode="json")
    payload["dataset_years"]["populace_us_2024"] = years

    with pytest.raises(ValidationError, match=error):
        CountryReleaseManifest.model_validate(payload)


def test_annual_manifest_accepts_base_only_family():
    payload = annual_manifest().model_dump(mode="json")
    payload["dataset_years"]["populace_us_2024"] = {2024: "populace_us_2024"}

    manifest = CountryReleaseManifest.model_validate(payload)

    assert manifest.dataset_years == {"populace_us_2024": {2024: "populace_us_2024"}}


def test_managed_source_cache_separates_revisions_and_digests(tmp_path):
    first = annual_manifest()
    second = first.model_copy(deep=True)
    second.datasets[second.default_dataset].revision = "another-release"
    third = first.model_copy(deep=True)
    third.datasets[third.default_dataset].sha256 = "a" * 64
    destinations = {
        materialization._resolve_bundle_dataset(
            "us", data_dir=tmp_path, manifest=manifest
        ).destination
        for manifest in (first, second, third)
    }
    assert len(destinations) == 3


def _annual_source(tmp_path, year):
    import pandas as pd

    from policyengine.provenance.dataset_materialization import DatasetSource
    from tests.fixtures.filtering_fixtures import create_us_test_dataset

    original = create_us_test_dataset()
    original.data.person["employment_income"] = [12345.6789012345] * 6
    original.filepath = str(tmp_path / f"annual-{year}.h5")
    original.save()
    with pd.HDFStore(original.filepath, "a") as store:
        store["_time_period"] = pd.Series([year])
    return original, DatasetSource(
        source_uri=f"hf://example/repo/annual-{year}.h5@release", path=original.filepath
    )


def test_annual_ensure_fetches_selected_year_and_preserves_exact_inputs(
    monkeypatch, tmp_path
):
    import pandas as pd

    import policyengine.tax_benefit_models.us.datasets as us_datasets

    original, source = _annual_source(tmp_path, 2025)
    monkeypatch.setattr(
        us_datasets, "get_release_manifest", lambda country: annual_manifest()
    )
    materialize = Mock(return_value=source)
    monkeypatch.setattr(us_datasets, "materialize_dataset", materialize)
    result = us_datasets.ensure_datasets(years=[2025], data_folder=str(tmp_path))
    assert list(result) == ["populace_us_2024_2025"]
    result = result["populace_us_2024_2025"]
    assert result.filepath == original.filepath
    assert result.year == 2025
    for entity, frame in original.data.entity_data.items():
        pd.testing.assert_frame_equal(
            pd.DataFrame(result.data.entity_data[entity]),
            pd.DataFrame(frame),
            check_exact=True,
        )
    assert materialize.call_count == 1
    assert materialize.call_args.kwargs["year"] == 2025


@pytest.mark.parametrize("stored_year", [2024, None])
def test_annual_ensure_rejects_wrong_or_missing_file_year(
    monkeypatch, tmp_path, stored_year
):
    import pandas as pd

    import policyengine.tax_benefit_models.us.datasets as us_datasets

    original, source = _annual_source(tmp_path, 2024)
    if stored_year is None:
        with pd.HDFStore(original.filepath, "a") as store:
            del store["_time_period"]
    monkeypatch.setattr(
        us_datasets, "get_release_manifest", lambda country: annual_manifest()
    )
    monkeypatch.setattr(us_datasets, "materialize_dataset", Mock(return_value=source))
    with pytest.raises(ValueError, match="_time_period"):
        us_datasets.ensure_datasets(years=[2025], data_folder=str(tmp_path))


def test_derived_cache_identity_includes_model_and_spm(monkeypatch, tmp_path):
    import policyengine.tax_benefit_models.us.datasets as us_datasets

    manifest = annual_manifest()
    monkeypatch.setattr(us_datasets, "get_release_manifest", lambda country: manifest)
    uri = "hf://policyengine/populace-us/annual/populace_us_2024.h5@annual-release"
    variants = (
        {"model": "one", "spm": "first"},
        {"model": "two", "spm": "first"},
        {"model": "one", "spm": "second"},
    )
    assert (
        len(
            {
                us_datasets._derived_dataset_path(uri, 2025, str(tmp_path), runtime)
                for runtime in variants
            }
        )
        == 3
    )


def test_annual_coverage_guards_external_periods_but_permits_formula_lookbacks():
    from policyengine.tax_benefit_models.us.model import _AnnualDatasetCoverage

    class Base:
        default_calculation_period = 2025

        def calculate(self, variable, period=None, **kwargs):
            if variable == "lookback":
                return self.calculate("previous", 2023)
            return period

        def calculate_add(self, variable, period=None, **kwargs):
            return self.calculate(variable, period)

        calculate_divide = calculate_add

    class Managed(_AnnualDatasetCoverage, Base):
        _annual_years = (2024, 2025)

    sim = Managed()
    assert sim.calculate("lookback", 2024) == 2023
    assert sim.calculate("monthly", "2025-01") == "2025-01"
    for method in (sim.calculate, sim.calculate_add, sim.calculate_divide):
        with pytest.raises(ValueError, match="coverage"):
            method("outside", 2026)
        with pytest.raises(ValueError, match="coverage"):
            method("span", "year:2025:2")
    # The context must reset after returning and after a rejected call.
    with pytest.raises(ValueError, match="coverage"):
        sim.calculate("previous", 2023)
    sim.default_calculation_period = 2026
    with pytest.raises(ValueError, match="coverage"):
        sim.calculate("implicit")


def test_certification_preserves_and_validates_producer_annual_map():
    from policyengine.provenance.certification import build_country_manifest_payload
    from policyengine.provenance.manifest import DataReleaseManifest

    country = annual_manifest()
    producer = DataReleaseManifest(
        schema_version=1,
        data_package={"name": "microcosm-data", "version": "0.1.0"},
        default_datasets={"national": country.default_dataset},
        artifacts={
            name: {
                "kind": "dataset",
                "repo_id": country.data_package.repo_id,
                **reference.model_dump(exclude_none=True),
            }
            for name, reference in country.datasets.items()
        },
        metadata={"dataset_years": country.model_dump(mode="json")["dataset_years"]},
    )
    kwargs = dict(
        country="us",
        manifest=producer,
        uri_parts={
            "repo_id": country.data_package.repo_id,
            "repo_type": "dataset",
            "path": "releases/test/release_manifest.json",
            "revision": "release",
        },
        policyengine_version="6.0.0",
        model_package="policyengine-us",
        model_version="2.2.1",
        model_wheel={},
    )
    payload = build_country_manifest_payload(**kwargs)
    assert (
        CountryReleaseManifest.model_validate(payload).dataset_years
        == country.dataset_years
    )
    producer.metadata["dataset_years"][country.default_dataset]["2025"] = "missing"
    with pytest.raises(ValidationError):
        build_country_manifest_payload(**kwargs)


def test_managed_annual_uses_exact_multiyear_inputs_and_preserves_explicit_default(
    monkeypatch, tmp_path
):
    import importlib
    import sys
    from types import SimpleNamespace

    import pandas as pd

    us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")
    originals, sources = {}, {}
    for year in (2024, 2025):
        originals[year], sources[year] = _annual_source(tmp_path, year)
    materialize = Mock(side_effect=lambda *args, **kwargs: sources[kwargs["year"]])
    monkeypatch.setattr(
        us_model, "get_release_manifest", lambda country: annual_manifest()
    )
    monkeypatch.setattr(us_model, "materialize_dataset", materialize)

    class FakeMicrosimulation:
        def __init__(self, dataset, spm, **kwargs):
            self.dataset = dataset
            self.default_calculation_period = dataset.time_period
            self.spm_config = dict(spm)
            self.calc = self.calculate

        def calculate(self, variable, period=None, **kwargs):
            return period

    monkeypatch.setitem(
        sys.modules,
        "policyengine_us",
        SimpleNamespace(Microsimulation=FakeMicrosimulation),
    )
    sim = us_model.managed_microsimulation(default_calculation_period=2025)
    assert sim.default_calculation_period == 2025
    assert sim.dataset.years == [2024, 2025]
    assert materialize.call_count == 2
    for year, single in sim.dataset.datasets.items():
        pd.testing.assert_frame_equal(
            single.person, pd.DataFrame(originals[year].data.person), check_exact=True
        )
    assert set(sim.policyengine_bundle["annual_datasets"]) == {"2024", "2025"}
    assert sim.policyengine_bundle["annual_input_bytes"] > 0
    assert sim.calc(variable_name="age", period=2025) == 2025
    with pytest.raises(ValueError, match="coverage"):
        sim.calc("age", 2026)
    materialize.reset_mock()
    with pytest.raises(ValueError, match="coverage"):
        us_model.managed_microsimulation(default_calculation_period=2026)
    materialize.assert_not_called()


@pytest.mark.parametrize("dataset", ["populace_us_2024", "populace_us_2025"])
@pytest.mark.parametrize("regional", [False, True])
def test_real_managed_microsimulation_uses_each_annual_input_without_extension(
    monkeypatch, tmp_path, dataset, regional
):
    import hashlib
    import importlib
    from pathlib import Path

    import pandas as pd
    import policyengine_us
    from policyengine_us.data import economic_assumptions

    import policyengine.tax_benefit_models.us.datasets as us_datasets
    from policyengine.core import Simulation
    from policyengine.core.scoping_strategy import RowFilterStrategy
    from policyengine.provenance.dataset_materialization import DatasetSource

    us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")
    sources = {}
    for year, incomes, weights in (
        (2024, [10_000.0, 20_000.0], [3.0, 7.0]),
        (2025, [20_000.0, 10_000.0], [5.0, 1.0]),
    ):
        frames = {
            "person": pd.DataFrame(
                {
                    "person_id": [1, 2],
                    **{
                        f"person_{entity}_id": [1, 2]
                        for entity in (
                            "household",
                            "tax_unit",
                            "spm_unit",
                            "family",
                            "marital_unit",
                        )
                    },
                    "age": [40, 70],
                    "employment_income": incomes,
                }
            ),
            "household": pd.DataFrame(
                {
                    "household_id": [1, 2],
                    "household_weight": weights,
                    "state_fips": [39, 39],
                    "county_fips": ["39049", "39049"],
                }
            ),
            **{
                entity: pd.DataFrame({f"{entity}_id": [1, 2]})
                for entity in ("tax_unit", "spm_unit", "family", "marital_unit")
            },
        }
        path = tmp_path / f"population-{year}.h5"
        with pd.HDFStore(path, "w") as store:
            for entity, frame in frames.items():
                store[entity] = frame
            store["_time_period"] = pd.Series([year])
        sources[year] = DatasetSource(
            source_uri=f"hf://policyengine/populace-us/annual/populace_us_{year}.h5@annual-release",
            path=str(path),
        )
    manifest = annual_manifest()
    original_hashes = {
        year: hashlib.sha256(Path(source.path).read_bytes()).hexdigest()
        for year, source in sources.items()
    }
    for year, digest in original_hashes.items():
        manifest.datasets[f"populace_us_{year}"].sha256 = digest
    monkeypatch.setattr(us_model, "get_release_manifest", lambda country: manifest)
    monkeypatch.setattr(
        us_model, "materialize_dataset", lambda *args, **kwargs: sources[kwargs["year"]]
    )
    extension = Mock(
        side_effect=AssertionError("Annual inputs must not be uprated again")
    )
    monkeypatch.setattr(economic_assumptions, "extend_single_year_dataset", extension)
    sim = us_model.managed_microsimulation(
        dataset=dataset, default_calculation_period=2025
    )
    # Current income uses 2025 inputs and weights: 5*20,000 + 1*10,000.
    assert sim.calc("employment_income_before_lsr", map_to="person").sum() == 110_000
    # Ohio uses prior-year income but current weights: 5*10,000 + 1*20,000.
    # Explicit artifact selection must retain the same history as its family.
    assert (
        sim.calc("oh_homestead_exemption_total_income", map_to="tax_unit").sum()
        == 70_000
    )
    assert sim.calc("age", 2025, map_to="person").count() == 6
    extension.assert_not_called()
    with pytest.raises(ValueError, match="coverage"):
        sim.calc("employment_income_before_lsr", 2024)
    with pytest.raises(ValueError, match="coverage"):
        sim.calc("employment_income_before_lsr", 2026)

    monkeypatch.setattr(us_datasets, "get_release_manifest", lambda country: manifest)
    materialize = Mock(side_effect=lambda *args, **kwargs: sources[kwargs["year"]])
    monkeypatch.setattr(us_datasets, "materialize_dataset", materialize)
    annual = next(
        iter(us_datasets.ensure_datasets(datasets=[dataset], years=[2025]).values())
    )
    assert [call.kwargs["year"] for call in materialize.call_args_list] == [2025]
    monkeypatch.setattr(
        us_model.PolicyEngineUSLatest,
        "resolve_entity_variables",
        lambda self, simulation: {
            "tax_unit": ["oh_homestead_exemption_total_income"],
            "person": ["employment_income", "employment_income_before_lsr"],
        },
    )
    country_instances = []

    class CaptureMicrosimulation(policyengine_us.Microsimulation):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            country_instances.append(self)

    monkeypatch.setattr(policyengine_us, "Microsimulation", CaptureMicrosimulation)
    ordinary = Simulation(
        dataset=annual,
        tax_benefit_model_version=us_model.us_latest,
        policy={"gov.irs.credits.ctc.amount.base[0].amount": 3000},
        scoping_strategy=RowFilterStrategy(
            variable_name="household_weight", variable_value=5
        )
        if regional
        else None,
    )
    ordinary.run()
    prior_income = sim.calc(
        "oh_homestead_exemption_total_income", 2025, map_to="tax_unit"
    )
    if regional:
        prior_income = prior_income[
            sim.calc("household_id", 2025, map_to="tax_unit") == 1
        ]
    assert (
        ordinary.output_dataset.data.tax_unit[
            "oh_homestead_exemption_total_income"
        ].sum()
        == prior_income.sum()
    )
    assert ordinary.output_dataset.data.household["household_id"].tolist() == (
        [1] if regional else [1, 2]
    )
    assert ordinary.output_dataset.data.person[
        "employment_income_before_lsr"
    ].sum() == (100_000 if regional else 110_000)
    baseline = country_instances[-1].baseline
    assert baseline is not None
    assert (
        baseline.calc(
            "oh_homestead_exemption_total_income", 2025, map_to="tax_unit"
        ).sum()
        == prior_income.sum()
    )
    assert original_hashes == {
        year: hashlib.sha256(Path(source.path).read_bytes()).hexdigest()
        for year, source in sources.items()
    }
    if not regional and dataset == "populace_us_2024":
        ordinary.save()
        restored = Simulation(
            id=ordinary.id, dataset=annual, tax_benefit_model_version=us_model.us_latest
        )
        restored.load()
        assert (
            restored.output_dataset.metadata["annual_input_sources"]
            == annual.metadata["annual_input_sources"]
        )
        import json

        import h5py

        with h5py.File(ordinary.output_dataset.filepath, "a") as stream:
            receipt = json.loads(stream["policyengine_spm"].asstr()[()])
            receipt["annual_input_sources"]["2024"]["sha256"] = "f" * 64
            del stream["policyengine_spm"]
            stream.create_dataset(
                "policyengine_spm",
                data=json.dumps(receipt),
                dtype=h5py.string_dtype("utf-8"),
            )
        with pytest.raises(ValueError, match="different annual input pins"):
            restored.load()
        annual.metadata["annual_input_sources"]["2024"]["sha256"] = "b" * 64
        with pytest.raises(ValueError, match="pins changed"):
            ordinary.save()


def test_annual_region_filter_keeps_weights_and_rejects_positional_replacement(
    monkeypatch, tmp_path
):
    import importlib

    from policyengine.core import Simulation
    from policyengine.core.scoping_strategy import (
        RowFilterStrategy,
        WeightReplacementStrategy,
    )
    from policyengine.tax_benefit_models.us.datasets import _annual_dataset

    us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")
    _, source = _annual_source(tmp_path, 2025)
    dataset = _annual_dataset(source, "populace_us_2024", 2025)
    scoped = RowFilterStrategy(variable_name="state_fips", variable_value=6).apply(
        entity_data=dataset.data.entity_data,
        group_entities=us_model.US_GROUP_ENTITIES,
        year=2025,
    )
    assert scoped["household"]["household_id"].tolist() == [1, 2]
    assert scoped["household"]["household_weight"].tolist() == [1000.0, 1000.0]
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=us_model.us_latest,
        scoping_strategy=WeightReplacementStrategy(
            weight_matrix_bucket="test",
            weight_matrix_key="weights.h5",
            lookup_csv_bucket="test",
            lookup_csv_key="lookup.csv",
            region_code="CA",
        ),
    )
    with pytest.raises(ValueError, match="positional weight replacement"):
        us_model.us_latest.run(simulation)


def test_annual_schema_and_ids_must_match_before_engine_construction(
    monkeypatch, tmp_path
):
    import importlib
    import sys
    from types import SimpleNamespace

    import pandas as pd

    us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")
    _, first = _annual_source(tmp_path, 2024)
    _, second = _annual_source(tmp_path, 2025)
    with pd.HDFStore(second.path, "a") as store:
        person = store["person"]
        person.loc[0, "person_id"] = 999
        store["person"] = person
    monkeypatch.setattr(
        us_model, "get_release_manifest", lambda country: annual_manifest()
    )
    monkeypatch.setattr(
        us_model,
        "materialize_dataset",
        lambda *args, **kwargs: {2024: first, 2025: second}[kwargs["year"]],
    )
    constructor = Mock()
    monkeypatch.setitem(
        sys.modules, "policyengine_us", SimpleNamespace(Microsimulation=constructor)
    )
    with pytest.raises(ValueError, match="schema, rows or IDs"):
        us_model.managed_microsimulation(years=[2025])
    constructor.assert_not_called()


def test_ensure_ignores_basename_only_legacy_cache(monkeypatch, tmp_path):
    import policyengine.tax_benefit_models.us.datasets as us_datasets

    (tmp_path / "populace_us_2024_year_2025.h5").write_bytes(b"stale unversioned cache")
    create = Mock(return_value={"fresh": object()})
    monkeypatch.setattr(us_datasets, "create_datasets", create)
    result = us_datasets.ensure_datasets(years=[2025], data_folder=str(tmp_path))
    assert list(result) == ["fresh"]
    create.assert_called_once()


def test_annual_family_default_uri_keeps_logical_return_key(monkeypatch, tmp_path):
    import policyengine.tax_benefit_models.us.datasets as us_datasets

    manifest = annual_manifest()
    _, source = _annual_source(tmp_path, 2025)
    monkeypatch.setattr(us_datasets, "get_release_manifest", lambda country: manifest)
    monkeypatch.setattr(us_datasets, "materialize_dataset", Mock(return_value=source))
    result = us_datasets.ensure_datasets(
        datasets=[
            "hf://policyengine/populace-us/annual/populace_us_2024.h5@annual-release"
        ],
        years=[2025],
        data_folder=str(tmp_path),
    )
    assert list(result) == ["populace_us_2024_2025"]


def test_annual_metadata_does_not_certify_unsupported_country_loader():
    payload = annual_manifest().model_dump(mode="json")
    payload["country_id"] = "uk"
    with pytest.raises(ValidationError, match="only the US"):
        CountryReleaseManifest.model_validate(payload)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"years": [2025]},
        {"years": [2025], "dataset": "populace_us_2025"},
        {
            "years": [2025],
            "dataset": "hf://policyengine/populace-us/annual/populace_us_2025.h5@annual-release",
        },
        {"default_calculation_period": "2025-06"},
        {},
    ],
)
def test_selected_years_load_history_but_never_future(monkeypatch, tmp_path, kwargs):
    import importlib
    import sys
    from types import SimpleNamespace

    us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")

    class FixedDate(us_model.datetime.date):
        @classmethod
        def today(cls):
            return cls(2025, 9, 19)

    monkeypatch.setattr(us_model.datetime, "date", FixedDate)
    manifest = annual_manifest()
    for year in (2026, 2027):
        manifest.datasets[f"populace_us_{year}"] = manifest.datasets[
            "populace_us_2025"
        ].model_copy(update={"path": f"annual/populace_us_{year}.h5"})
        manifest.dataset_years[manifest.default_dataset][year] = f"populace_us_{year}"
    sources = {year: _annual_source(tmp_path, year)[1] for year in (2024, 2025)}
    materialize = Mock(side_effect=lambda *args, **kwargs: sources[kwargs["year"]])
    monkeypatch.setattr(us_model, "get_release_manifest", lambda country: manifest)
    monkeypatch.setattr(us_model, "materialize_dataset", materialize)

    class FakeMicrosimulation:
        def __init__(self, dataset, spm, **kwargs):
            self.dataset = dataset
            self.default_calculation_period = dataset.time_period
            self.spm_config = dict(spm)
            self.calc = self.calculate

        def calculate(self, variable, period=None, **kwargs):
            return period

    monkeypatch.setitem(
        sys.modules,
        "policyengine_us",
        SimpleNamespace(Microsimulation=FakeMicrosimulation),
    )
    sim = us_model.managed_microsimulation(**kwargs)
    assert [call.kwargs["year"] for call in materialize.call_args_list] == [2024, 2025]
    assert sim.default_calculation_period == kwargs.get(
        "default_calculation_period", 2025
    )
    assert sim.policyengine_bundle["annual_selected_years"] == [2025]
    assert sim.policyengine_bundle["annual_loaded_years"] == [2024, 2025]
    assert set(sim.policyengine_bundle["annual_input_bytes_by_year"]) == {
        "2024",
        "2025",
    }
    with pytest.raises(ValueError, match="coverage"):
        sim.calc("age", 2024)
    with pytest.raises(ValueError, match="coverage"):
        sim.calc("age", 2026)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"years": []},
        {"years": [True]},
        {"years": [2025.0]},
        {"years": [2026]},
        {"years": [2025], "default_calculation_period": 2024},
        {"dataset": "populace_us_2025", "years": [2024]},
        {"default_calculation_period": "eternity"},
    ],
)
def test_invalid_selected_years_fail_before_download(monkeypatch, kwargs):
    import importlib

    us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")
    monkeypatch.setattr(
        us_model, "get_release_manifest", lambda country: annual_manifest()
    )
    materialize = Mock()
    monkeypatch.setattr(us_model, "materialize_dataset", materialize)
    with pytest.raises(ValueError):
        us_model.managed_microsimulation(**kwargs)
    materialize.assert_not_called()


def test_annual_history_pins_and_runtime_invalidate_reused_simulation_id(
    monkeypatch, tmp_path
):
    import policyengine.tax_benefit_models.us.datasets as us_datasets
    from policyengine.core import Simulation

    _, source = _annual_source(tmp_path, 2025)
    manifest = annual_manifest()
    monkeypatch.setattr(us_datasets, "get_release_manifest", lambda country: manifest)
    monkeypatch.setattr(us_datasets, "materialize_dataset", Mock(return_value=source))
    first = next(iter(us_datasets.ensure_datasets(years=[2025]).values()))
    first_key = Simulation(id="same-run", dataset=first).storage_id
    manifest.datasets["populace_us_2024"].sha256 = "a" * 64
    second = next(iter(us_datasets.ensure_datasets(years=[2025]).values()))
    second_key = Simulation(id="same-run", dataset=second).storage_id
    assert first.id != second.id
    assert first_key != second_key
    monkeypatch.setattr(
        us_datasets, "_derived_cache_identity", lambda: {"model": "another-source"}
    )
    assert Simulation(id="same-run", dataset=second).storage_id != second_key


def test_ordinary_annual_run_rejects_missing_or_changed_history(monkeypatch, tmp_path):
    import importlib

    import policyengine.tax_benefit_models.us.datasets as us_datasets

    model = importlib.import_module("policyengine.tax_benefit_models.us.model")
    _, source = _annual_source(tmp_path, 2025)
    manifest = annual_manifest()
    monkeypatch.setattr(us_datasets, "get_release_manifest", lambda country: manifest)
    monkeypatch.setattr(model, "get_release_manifest", lambda country: manifest)
    monkeypatch.setattr(us_datasets, "materialize_dataset", Mock(return_value=source))
    dataset = next(iter(us_datasets.ensure_datasets(years=[2025]).values()))
    download = Mock()
    monkeypatch.setattr(model, "materialize_dataset", download)
    del dataset.metadata["annual_input_sources"]["2024"]
    with pytest.raises(ValueError, match="history differs"):
        model._ordinary_annual_inputs(dataset, dataset)
    download.assert_not_called()
