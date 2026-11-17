"""Keep managed US data strict while supporting explicit local experiments.

The constructor tests use inert stubs and byte fixtures, not population data.
"""

import hashlib
import importlib
from contextlib import nullcontext
from importlib import metadata
from types import SimpleNamespace

import pytest

import policyengine.provenance.dataset_materialization as materialization
import policyengine.tax_benefit_models.common.model_version as common
from policyengine.provenance import loaded
from policyengine.provenance.manifest import get_release_manifest

us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")
us_datasets = importlib.import_module("policyengine.tax_benefit_models.us.datasets")


def refuse_certification(*args, **kwargs):
    raise ValueError("test incompatible bundled data")


@pytest.mark.parametrize("allow_unmanaged", [False, True])
@pytest.mark.parametrize("selection", [None, "name", "uri"])
def test_managed_selection_certifies_before_cache_or_download(
    monkeypatch, selection, allow_unmanaged
):
    manifest = get_release_manifest("us")
    selected = {"name": manifest.default_dataset, "uri": manifest.default_dataset_uri}
    monkeypatch.setattr(
        materialization, "_require_us_data_certification", refuse_certification
    )
    reuse = []
    monkeypatch.setattr(
        materialization, "_reuse_or_download_bundle_files", lambda *a: reuse.append(a)
    )

    with pytest.raises(ValueError, match="incompatible bundled data"):
        materialization.materialize_dataset(
            "us", selected.get(selection), allow_unmanaged=allow_unmanaged
        )

    assert reuse == []


def test_remote_unmanaged_source_keeps_certification(monkeypatch):
    monkeypatch.setattr(
        materialization, "_require_us_data_certification", refuse_certification
    )
    with pytest.raises(ValueError, match="incompatible bundled data"):
        materialization.materialize_dataset(
            "us", "hf://example/other/fixture.h5@revision", allow_unmanaged=True
        )


def test_local_source_requires_opt_in_and_avoids_unused_bundle(monkeypatch, tmp_path):
    path = tmp_path / "inert-local-fixture.bin"
    path.write_bytes(b"test source plumbing only")
    monkeypatch.setattr(
        materialization, "_require_us_data_certification", refuse_certification
    )
    with pytest.raises(ValueError, match="allow_unmanaged"):
        materialization.materialize_dataset("us", str(path))

    source = materialization.materialize_dataset("us", str(path), allow_unmanaged=True)
    assert source.path == str(path)
    assert source.bundle_dataset is None


@pytest.mark.parametrize(
    "name",
    [
        "create_datasets",
        "load_datasets",
        "load_long_term_datasets",
        "load_managed_long_term_datasets",
        "ensure_datasets",
    ],
)
def test_year_helpers_certify_before_cached_data(monkeypatch, name):
    monkeypatch.setattr(
        us_datasets, "_require_us_data_certification", refuse_certification
    )
    with pytest.raises(ValueError, match="incompatible bundled data"):
        getattr(us_datasets, name)(years=[2017])


@pytest.mark.parametrize("entry", ["run", "load", "release_bundle"])
def test_managed_simulation_and_cached_output_keep_guard(monkeypatch, entry):
    monkeypatch.setattr(
        us_model.PolicyEngineUSLatest,
        "require_data_certification",
        refuse_certification,
    )
    with pytest.raises(ValueError, match="incompatible bundled data"):
        if entry == "release_bundle":
            us_model.us_latest.release_bundle
        else:
            getattr(us_model.us_latest, entry)(None)


def test_only_us_defers_the_initial_certification(monkeypatch):
    cls = us_model.PolicyEngineUSLatest
    monkeypatch.setattr(
        common, "certify_data_release_compatibility", refuse_certification
    )
    monkeypatch.setattr(cls, "_load_region_registry", lambda self: None)
    monkeypatch.setattr(cls, "_load_system", lambda self: None)
    for name in ("_populate_entities", "_populate_variables", "_populate_parameters"):
        monkeypatch.setattr(cls, name, lambda *args: None)

    model = cls()
    assert model.data_certification is None
    assert cls.defer_data_certification is True
    assert common.MicrosimulationModelVersion.defer_data_certification is False


def test_uk_initialization_keeps_eager_certification(monkeypatch):
    pytest.importorskip("policyengine_uk")
    uk_model = importlib.import_module("policyengine.tax_benefit_models.uk.model")
    monkeypatch.setattr(
        common, "certify_data_release_compatibility", refuse_certification
    )
    with pytest.raises(ValueError, match="incompatible bundled data"):
        uk_model.PolicyEngineUKLatest()


def local_factory_fixture(monkeypatch, tmp_path, *, mutate=False):
    """Return an explicit local source and a constructor that never loads it."""
    import policyengine_us

    path = tmp_path / "inert-local-fixture.bin"
    path.write_bytes(b"test source plumbing only")
    sim = SimpleNamespace(spm_config={})

    def constructor(**kwargs):
        assert kwargs["dataset"] == str(path)
        if mutate:
            path.write_bytes(b"different fixture bytes")
        return sim

    monkeypatch.setattr(policyengine_us, "Microsimulation", constructor)
    monkeypatch.setattr(us_model, "resolve_spm_selection", lambda spm: {})
    monkeypatch.setattr(
        us_model, "apply_legacy_input_renames_to_microsimulation", lambda sim: {}
    )
    monkeypatch.setattr(
        us_model.PolicyEngineUSLatest,
        "require_data_certification",
        refuse_certification,
    )
    return path, sim


def test_local_factory_records_actual_runtime_without_certificate(
    monkeypatch, tmp_path
):
    path, expected = local_factory_fixture(monkeypatch, tmp_path)
    sim = us_model.managed_microsimulation(dataset=str(path), allow_unmanaged=True)
    receipt = sim.policyengine_bundle

    assert sim is expected
    assert receipt["compatibility_basis"] == "unverified_explicit_local_unmanaged"
    assert receipt["certified_by"] is None
    assert receipt["runtime_packages"] == {
        name: metadata.version(name)
        for name in (
            "policyengine",
            "policyengine-us",
            "policyengine-core",
            "spm-calculator",
        )
    }
    assert (
        receipt["runtime_dataset_sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert not any(key.startswith("certified_data") for key in receipt)


def test_local_factory_refuses_source_changes_during_construction(
    monkeypatch, tmp_path
):
    path, _ = local_factory_fixture(monkeypatch, tmp_path, mutate=True)
    with pytest.raises(ValueError, match="changed during construction"):
        us_model.managed_microsimulation(dataset=str(path), allow_unmanaged=True)


def test_local_provenance_refuses_installed_loaded_drift(monkeypatch, tmp_path):
    path = tmp_path / "inert-local-fixture.bin"
    path.write_bytes(b"fixture")
    original = loaded.loaded_versions()
    monkeypatch.setattr(
        loaded, "loaded_versions", lambda: {**original, "policyengine-us": "changed"}
    )
    source = materialization.DatasetSource(source_uri=str(path), path=str(path))
    with pytest.raises(ValueError, match="changed after import"):
        us_model._unmanaged_local_runtime_provenance(source)


@pytest.mark.parametrize("period", [True, 2017, "2017-01", "２０17", "0000", "2017:2"])
def test_native_clock_requires_one_canonical_annual_period(period):
    with pytest.raises(ValueError, match="four-digit annual period"):
        us_model.managed_microsimulation(native_input_period=period)


@pytest.mark.parametrize(
    "source", [None, "populace_us_2024", "hf://example/fixture.h5@v1"]
)
def test_native_clock_rejects_managed_and_remote_sources(source):
    with pytest.raises(ValueError, match="explicit local unmanaged file"):
        us_model.managed_microsimulation(
            dataset=source, allow_unmanaged=True, native_input_period="2017"
        )


def test_native_clock_requires_existing_local_opt_in(tmp_path):
    path = tmp_path / "fixture.bin"
    with pytest.raises(ValueError, match="explicit local unmanaged file"):
        us_model.managed_microsimulation(
            dataset=str(path), allow_unmanaged=True, native_input_period="2017"
        )
    path.write_bytes(b"fixture")
    with pytest.raises(ValueError, match="explicit local unmanaged file"):
        us_model.managed_microsimulation(dataset=str(path), native_input_period="2017")


@pytest.mark.parametrize(
    "options",
    [
        {"dataset_end_year": 2017},
        {"scoping_strategy": object()},
        {"default_input_period": "2015"},
        {"default_calculation_period": "2015"},
    ],
)
def test_native_clock_rejects_projection_scoping_and_conflicting_defaults(
    tmp_path, options
):
    path = tmp_path / "fixture.bin"
    path.write_bytes(b"fixture")
    with pytest.raises(ValueError, match="cannot project or scope|must match"):
        us_model.managed_microsimulation(
            dataset=str(path),
            allow_unmanaged=True,
            native_input_period="2017",
            **options,
        )


def test_native_descriptor_reaches_first_constructor_with_declared_clock(
    monkeypatch, tmp_path
):
    import policyengine_us
    from policyengine_core.data import Dataset as CoreDataset

    path, expected = local_factory_fixture(monkeypatch, tmp_path)
    arrays = {
        "annual_lookback_fixture": {"2015": SimpleNamespace(shape=(1,))},
        "monthly_fixture": {"2017-01": SimpleNamespace(shape=(1,))},
    }
    descriptor = SimpleNamespace(
        data_format=CoreDataset.TIME_PERIOD_ARRAYS,
        time_period="2015",
        load=lambda: nullcontext(arrays),
    )
    monkeypatch.setattr(CoreDataset, "from_file", lambda path: descriptor)
    calls = []

    def constructor(**kwargs):
        calls.append(kwargs)
        assert kwargs["dataset"] is descriptor
        assert descriptor.time_period == "2017"
        assert kwargs["default_input_period"] == "2017"
        assert kwargs["default_calculation_period"] == "2017"
        return expected

    monkeypatch.setattr(policyengine_us, "Microsimulation", constructor)
    sim = us_model.managed_microsimulation(
        dataset=str(path), allow_unmanaged=True, native_input_period="2017"
    )
    assert len(calls) == 1
    assert sim.policyengine_bundle["native_input_period"] == "2017"
    assert list(arrays["annual_lookback_fixture"]) == ["2015"]
    assert list(arrays["monthly_fixture"]) == ["2017-01"]


@pytest.mark.parametrize(
    "data_format, arrays, message",
    [
        ("arrays", {}, "TIME_PERIOD_ARRAYS"),
        ("time_period_arrays", {}, "cannot be empty"),
        ("time_period_arrays", {"fixture": {}}, "period arrays"),
        (
            "time_period_arrays",
            {"fixture": {"2017": SimpleNamespace(shape=())}},
            "must be a vector",
        ),
        (
            "time_period_arrays",
            {"fixture": {"year:2017:2": SimpleNamespace(shape=(1,))}},
            "Unsupported native input period",
        ),
    ],
)
def test_native_descriptor_rejects_other_layouts(
    monkeypatch, data_format, arrays, message
):
    from policyengine_core.data import Dataset as CoreDataset

    descriptor = SimpleNamespace(
        data_format=data_format, time_period="2015", load=lambda: nullcontext(arrays)
    )
    monkeypatch.setattr(CoreDataset, "from_file", lambda path: descriptor)
    with pytest.raises(ValueError, match=message):
        us_model._native_local_dataset(
            SimpleNamespace(path="inert-fixture.bin"), "2017"
        )
    assert descriptor.time_period == "2015"


@pytest.mark.parametrize("cached_certification", [None, "old_test_certificate"])
def test_trace_export_requires_current_certification_before_builder(
    monkeypatch, cached_certification
):
    """A cached or absent certificate cannot substitute for runtime validation."""
    from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion

    model = us_model.PolicyEngineUSLatest.model_construct(
        data_certification=cached_certification
    )
    calls = []

    def refuse(self):
        calls.append("certification")
        raise ValueError("test incompatible current runtime")

    def unexpected_builder(self):
        pytest.fail("An uncertified export reached the bundle TRACE builder")

    monkeypatch.setattr(
        us_model.PolicyEngineUSLatest, "require_data_certification", refuse
    )
    monkeypatch.setattr(
        TaxBenefitModelVersion, "trace_tro", property(unexpected_builder)
    )
    with pytest.raises(ValueError, match="incompatible current runtime"):
        _ = model.trace_tro
    assert calls == ["certification"]


def test_trace_export_uses_newly_validated_certificate(monkeypatch):
    """The builder receives the fresh synthetic certificate, not manifest fallback."""
    from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion

    model = us_model.PolicyEngineUSLatest.model_construct(data_certification=None)
    fresh_test_certificate = object()
    calls = []

    def certify(self):
        calls.append("certification")
        self.data_certification = fresh_test_certificate
        return fresh_test_certificate

    def builder(self):
        calls.append("TRACE")
        assert self.data_certification is fresh_test_certificate
        return {"synthetic_fixture_only": True}

    monkeypatch.setattr(
        us_model.PolicyEngineUSLatest, "require_data_certification", certify
    )
    monkeypatch.setattr(TaxBenefitModelVersion, "trace_tro", property(builder))
    assert model.trace_tro == {"synthetic_fixture_only": True}
    assert calls == ["certification", "TRACE"]


def test_automatic_run_record_fallback_refuses_before_output_write(
    monkeypatch, tmp_path
):
    """Automatic provenance lookup propagates refusal before recording anything."""
    from policyengine.core.run_record import write_simulation_run_record

    model = us_model.PolicyEngineUSLatest.model_construct(data_certification=None)

    def refuse(self):
        raise ValueError("test incompatible current runtime")

    monkeypatch.setattr(
        us_model.PolicyEngineUSLatest, "require_data_certification", refuse
    )
    output = tmp_path / "must-not-be-created"
    simulation = SimpleNamespace(tax_benefit_model_version=model)
    with pytest.raises(ValueError, match="incompatible current runtime"):
        write_simulation_run_record(simulation, output)
    assert not output.exists()
