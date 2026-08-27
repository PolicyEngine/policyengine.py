import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from policyengine.provenance import dataset_sources
from policyengine.provenance.dataset_materialization import (
    MaterializedDataset,
    resolve_bundle_dataset_plan,
)
from policyengine.provenance.dataset_sources import (
    materialize_dataset_source,
    parse_gs_uri,
    parse_hf_uri,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _materialized(country_id: str, dataset: str, path: str) -> MaterializedDataset:
    plan = resolve_bundle_dataset_plan(country_id, dataset)
    return MaterializedDataset(
        country_id=plan.country_id,
        dataset=plan.dataset,
        data_package_name=plan.data_package_name,
        repo_id=plan.repo_id,
        repo_type=plan.repo_type,
        revision=plan.revision,
        source_uri=plan.source_uri,
        expected_sha256=plan.expected_sha256,
        actual_sha256=plan.expected_sha256,
        path=Path(path),
        cache_hit=False,
        build_id=plan.build_id,
    )


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
    monkeypatch.setattr(
        "policyengine_core.tools.hugging_face.download_huggingface_dataset",
        download,
    )

    result = materialize_dataset_source(
        "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.77.0"
    )

    assert result == "/tmp/enhanced_cps_2024.h5"
    download.assert_called_once_with(
        "policyengine/policyengine-us-data",
        "enhanced_cps_2024.h5",
        version="1.77.0",
    )


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

    materialize = Mock(
        return_value=_materialized("us", "populace_us_2024", "/tmp/populace_us_2024.h5")
    )
    microsimulation = Mock()
    monkeypatch.setattr(us_datasets, "materialize_bundle_dataset", materialize)
    monkeypatch.setitem(
        sys.modules,
        "policyengine_us",
        SimpleNamespace(Microsimulation=microsimulation),
    )

    us_datasets.create_datasets(
        datasets=["populace_us_2024"],
        years=[],
    )

    materialize.assert_called_once_with(
        "us", "populace_us_2024", data_dir=Path("./data")
    )
    microsimulation.assert_called_once_with(dataset="/tmp/populace_us_2024.h5")


def test_uk_create_datasets_passes_materialized_source_to_country_package(
    monkeypatch,
):
    uk_datasets = _load_module_from_path(
        "_test_policyengine_uk_datasets",
        REPO_ROOT / "src/policyengine/tax_benefit_models/uk/datasets.py",
    )

    materialize = Mock(
        return_value=_materialized("uk", "populace_uk_2023", "/tmp/populace_uk_2023.h5")
    )
    microsimulation = Mock()
    monkeypatch.setattr(uk_datasets, "materialize_bundle_dataset", materialize)
    monkeypatch.setitem(
        sys.modules,
        "policyengine_uk",
        SimpleNamespace(Microsimulation=microsimulation),
    )

    uk_datasets.create_datasets(
        datasets=["populace_uk_2023"],
        years=[],
    )

    materialize.assert_called_once_with(
        "uk", "populace_uk_2023", data_dir=Path("./data")
    )
    microsimulation.assert_called_once_with(dataset="/tmp/populace_uk_2023.h5")
