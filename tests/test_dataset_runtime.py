import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from policyengine.provenance.dataset_materialization import (
    MaterializedDataset,
    _resolve_bundle_dataset,
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
    plan = _resolve_bundle_dataset(country_id, dataset)
    return MaterializedDataset(
        data_package_name=plan.data_package_name,
        repo_type=plan.repo_type,
        revision=plan.revision,
        source_uri=plan.source_uri,
        sha256=plan.sha256,
        path=Path(path),
    )


def test_us_create_datasets_passes_verified_bundle_source_to_country_package(
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

    us_datasets.create_datasets(datasets=["populace_us_2024"], years=[])

    materialize.assert_called_once_with(
        "us",
        "populace_us_2024",
        data_dir=Path("./data"),
    )
    microsimulation.assert_called_once_with(dataset="/tmp/populace_us_2024.h5")


def test_uk_create_datasets_passes_verified_bundle_source_to_country_package(
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

    uk_datasets.create_datasets(datasets=["populace_uk_2023"], years=[])

    materialize.assert_called_once_with(
        "uk",
        "populace_uk_2023",
        data_dir=Path("./data"),
    )
    microsimulation.assert_called_once_with(dataset="/tmp/populace_uk_2023.h5")


def test_uk_create_datasets_defaults_to_certified_bundle_dataset(monkeypatch):
    uk_datasets = _load_module_from_path(
        "_test_policyengine_uk_default_create_datasets",
        REPO_ROOT / "src/policyengine/tax_benefit_models/uk/datasets.py",
    )
    materialize = Mock(
        return_value=_materialized(
            "uk",
            "enhanced_frs_2024_25",
            "/tmp/enhanced_frs_2024_25.h5",
        )
    )
    microsimulation = Mock()
    monkeypatch.setattr(uk_datasets, "materialize_bundle_dataset", materialize)
    monkeypatch.setitem(
        sys.modules,
        "policyengine_uk",
        SimpleNamespace(Microsimulation=microsimulation),
    )

    uk_datasets.create_datasets(years=[])

    materialize.assert_called_once_with(
        "uk",
        "enhanced_frs_2024_25",
        data_dir=Path("./data"),
    )
    microsimulation.assert_called_once_with(dataset="/tmp/enhanced_frs_2024_25.h5")


def test_uk_load_datasets_defaults_to_certified_bundle_dataset(monkeypatch):
    uk_datasets = _load_module_from_path(
        "_test_policyengine_uk_default_load_datasets",
        REPO_ROOT / "src/policyengine/tax_benefit_models/uk/datasets.py",
    )
    resolve = Mock(
        return_value=(
            "hf://policyengine/policyengine-uk-data-private/"
            "enhanced_frs_2024_25.h5@1.56.16"
        )
    )
    monkeypatch.setattr(uk_datasets, "resolve_dataset_reference", resolve)

    assert uk_datasets.load_datasets(years=[]) == {}

    resolve.assert_called_once_with("uk", "enhanced_frs_2024_25")


def test_uk_ensure_datasets_defaults_to_certified_bundle_dataset(monkeypatch):
    uk_datasets = _load_module_from_path(
        "_test_policyengine_uk_default_ensure_datasets",
        REPO_ROOT / "src/policyengine/tax_benefit_models/uk/datasets.py",
    )
    load = Mock(return_value={})
    monkeypatch.setattr(uk_datasets, "load_datasets", load)

    assert uk_datasets.ensure_datasets(years=[]) == {}

    load.assert_called_once_with(
        datasets=["enhanced_frs_2024_25"],
        years=[],
        data_folder="./data",
    )
