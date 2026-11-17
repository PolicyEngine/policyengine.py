"""Keep managed US data strict while supporting explicit local experiments.

The constructor tests use inert stubs and byte fixtures, not population data.
"""

import hashlib
import importlib
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
