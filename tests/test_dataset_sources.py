import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from policyengine.bundle import BundleError
from policyengine.provenance import dataset_sources
from policyengine.provenance import manifest as manifest_module
from policyengine.provenance.dataset_sources import (
    materialize_dataset_source,
    parse_gs_uri,
    parse_hf_uri,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _install_hf_downloader(monkeypatch, download):
    core_module = ModuleType("policyengine_core")
    core_module.__path__ = []
    tools_module = ModuleType("policyengine_core.tools")
    tools_module.__path__ = []
    hf_module = ModuleType("policyengine_core.tools.hugging_face")
    hf_module.download_huggingface_dataset = download
    core_module.tools = tools_module
    tools_module.hugging_face = hf_module
    monkeypatch.setitem(sys.modules, "policyengine_core", core_module)
    monkeypatch.setitem(sys.modules, "policyengine_core.tools", tools_module)
    monkeypatch.setitem(
        sys.modules,
        "policyengine_core.tools.hugging_face",
        hf_module,
    )


@pytest.fixture
def bundle_managed_hf_download(monkeypatch, tmp_path):
    payload = b"bundle-managed dataset bytes"
    downloaded_path = tmp_path / "populace_uk_2023.h5"
    country_manifest = manifest_module.get_release_manifest("uk").model_copy(deep=True)
    dataset_name = country_manifest.default_dataset
    path_reference = country_manifest.datasets[dataset_name]
    dataset_uri = manifest_module.build_hf_uri(
        repo_id=path_reference.repo_id or country_manifest.data_package.repo_id,
        path_in_repo=path_reference.path,
        revision=(
            path_reference.revision
            or country_manifest.data_package.release_manifest_revision
            or country_manifest.data_package.version
        ),
    )
    certified_artifact = country_manifest.certified_data_artifact
    assert certified_artifact is not None
    assert certified_artifact.uri == dataset_uri

    def emit_downloaded_bytes(*args, **kwargs):
        downloaded_path.write_bytes(payload)
        return str(downloaded_path)

    download = Mock(side_effect=emit_downloaded_bytes)
    _install_hf_downloader(monkeypatch, download)
    monkeypatch.setattr(
        manifest_module,
        "get_release_manifest",
        Mock(return_value=country_manifest),
    )
    return SimpleNamespace(
        country_manifest=country_manifest,
        certified_artifact=certified_artifact,
        dataset_name=dataset_name,
        dataset_uri=dataset_uri,
        download=download,
        downloaded_path=downloaded_path,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_gs_uri_extracts_bucket_path_and_version():
    reference = parse_gs_uri("gs://policyengine-us-data/states/CA.h5@1.77.0")

    assert reference.bucket == "policyengine-us-data"
    assert reference.path == "states/CA.h5"
    assert reference.version == "1.77.0"


def test_parse_hf_uri_extracts_repo_path_and_revision():
    reference = parse_hf_uri(
        "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.77.0"
    )

    assert reference.repo_id == "policyengine/policyengine-us-data"
    assert reference.path == "enhanced_cps_2024.h5"
    assert reference.version == "1.77.0"


def test_materialize_dataset_source_downloads_gcs_uri(monkeypatch):
    download = Mock(return_value=(".datasets/enhanced_cps_2024.h5", "1.77.0"))
    monkeypatch.setattr(dataset_sources, "download_file_from_gcs", download)

    result = materialize_dataset_source(
        "gs://policyengine-us-data/enhanced_cps_2024.h5@1.77.0"
    )

    assert result == ".datasets/enhanced_cps_2024.h5"
    download.assert_called_once_with(
        "policyengine-us-data",
        "enhanced_cps_2024.h5",
        version="1.77.0",
    )


def test_materialize_dataset_source_downloads_hf_uri(monkeypatch):
    download = Mock(return_value="/tmp/enhanced_cps_2024.h5")
    _install_hf_downloader(monkeypatch, download)

    result = materialize_dataset_source(
        "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.77.0"
    )

    assert result == "/tmp/enhanced_cps_2024.h5"
    download.assert_called_once_with(
        "policyengine/policyengine-us-data",
        "enhanced_cps_2024.h5",
        version="1.77.0",
    )


def test_bundle_managed_materialization_accepts_matching_artifact_sha256(
    bundle_managed_hf_download,
):
    fixture = bundle_managed_hf_download
    fixture.country_manifest.datasets[fixture.dataset_name].sha256 = fixture.sha256
    fixture.certified_artifact.sha256 = "0" * 64

    result = materialize_dataset_source(
        fixture.dataset_uri,
        country_id="uk",
    )

    assert result == str(fixture.downloaded_path)
    assert fixture.downloaded_path.read_bytes() == fixture.payload
    fixture.download.assert_called_once()


def test_bundle_managed_materialization_rejects_certified_sha256_mismatch(
    bundle_managed_hf_download,
):
    fixture = bundle_managed_hf_download
    expected_sha256 = hashlib.sha256(b"expected dataset bytes").hexdigest()
    fixture.country_manifest.datasets[fixture.dataset_name].sha256 = None
    fixture.certified_artifact.sha256 = expected_sha256

    with pytest.raises(BundleError) as exc_info:
        materialize_dataset_source(
            fixture.dataset_uri,
            country_id="uk",
        )

    message = str(exc_info.value)
    assert fixture.sha256 in message
    assert expected_sha256 in message
    assert "Downloaded UK dataset populace_uk_2023 has sha256" in message
    fixture.download.assert_called_once()


def test_materialize_dataset_source_preserves_local_path():
    assert materialize_dataset_source("/tmp/enhanced_cps_2024.h5") == (
        "/tmp/enhanced_cps_2024.h5"
    )


def test_materialize_dataset_source_rejects_conflicting_versions():
    with pytest.raises(ValueError, match="Conflicting dataset versions"):
        materialize_dataset_source(
            "gs://policyengine-us-data/enhanced_cps_2024.h5@1.77.0",
            version="1.78.0",
        )


def test_us_create_datasets_passes_materialized_source_to_country_package(
    monkeypatch,
):
    us_datasets = _load_module_from_path(
        "_test_policyengine_us_datasets",
        REPO_ROOT / "src/policyengine/tax_benefit_models/us/datasets.py",
    )

    materialize = Mock(return_value="/tmp/enhanced_cps_2024.h5")
    microsimulation = Mock()
    monkeypatch.setattr(us_datasets, "materialize_dataset_source", materialize)
    monkeypatch.setitem(
        sys.modules,
        "policyengine_us",
        SimpleNamespace(Microsimulation=microsimulation),
    )

    us_datasets.create_datasets(
        datasets=["gs://policyengine-us-data/enhanced_cps_2024.h5@1.77.0"],
        years=[],
    )

    materialize.assert_called_once_with(
        "gs://policyengine-us-data/enhanced_cps_2024.h5@1.77.0",
        country_id="us",
    )
    microsimulation.assert_called_once_with(dataset="/tmp/enhanced_cps_2024.h5")


def test_uk_create_datasets_passes_materialized_source_to_country_package(
    monkeypatch,
):
    uk_datasets = _load_module_from_path(
        "_test_policyengine_uk_datasets",
        REPO_ROOT / "src/policyengine/tax_benefit_models/uk/datasets.py",
    )

    materialize = Mock(return_value="/tmp/enhanced_frs_2023_24.h5")
    microsimulation = Mock()
    monkeypatch.setattr(uk_datasets, "materialize_dataset_source", materialize)
    monkeypatch.setitem(
        sys.modules,
        "policyengine_uk",
        SimpleNamespace(Microsimulation=microsimulation),
    )

    uk_datasets.create_datasets(
        datasets=["gs://policyengine-uk-data-private/enhanced_frs_2023_24.h5@1.40.3"],
        years=[],
    )

    materialize.assert_called_once_with(
        "gs://policyengine-uk-data-private/enhanced_frs_2023_24.h5@1.40.3",
        country_id="uk",
    )
    microsimulation.assert_called_once_with(dataset="/tmp/enhanced_frs_2023_24.h5")
