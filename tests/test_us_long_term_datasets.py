import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import h5py
import pandas as pd
import pytest
from microdf import MicroDataFrame

import policyengine.tax_benefit_models.us.datasets as us_datasets_module
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
    load_long_term_datasets,
    load_managed_long_term_datasets,
)


def _simple_entity(entity: str, count: int = 1) -> MicroDataFrame:
    return MicroDataFrame(
        pd.DataFrame(
            {
                f"{entity}_id": list(range(1, count + 1)),
                f"{entity}_weight": [1_000.0] * count,
            }
        ),
        weights=f"{entity}_weight",
    )


def _write_us_h5(path: Path, year: int) -> None:
    person = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1],
                "household_id": [1],
                "tax_unit_id": [1],
                "spm_unit_id": [1],
                "family_id": [1],
                "marital_unit_id": [1],
                "person_weight": [1_000.0],
                "age": [70],
            }
        ),
        weights="person_weight",
    )
    household = MicroDataFrame(
        pd.DataFrame({"household_id": [1], "household_weight": [1_000.0]}),
        weights="household_weight",
    )
    PolicyEngineUSDataset(
        id=f"fixture_{year}",
        name=f"fixture-{year}",
        description="Long-term fixture",
        filepath=str(path),
        year=year,
        data=USYearData(
            person=person,
            household=household,
            tax_unit=_simple_entity("tax_unit"),
            spm_unit=_simple_entity("spm_unit"),
            family=_simple_entity("family"),
            marital_unit=_simple_entity("marital_unit"),
        ),
    )


def _write_core_h5(path: Path, year: int) -> None:
    values = {
        "person_id": [1, 2],
        "person_household_id": [10, 10],
        "person_tax_unit_id": [20, 20],
        "person_spm_unit_id": [30, 30],
        "person_family_id": [40, 40],
        "person_marital_unit_id": [50, 50],
        "age": [70, 68],
        "household_id": [10],
        "household_weight": [1_000.0],
        "state_code": ["CA"],
        "tax_unit_id": [20],
        "spm_unit_id": [30],
        "family_id": [40],
        "marital_unit_id": [50],
    }
    with h5py.File(path, "w") as h5_file:
        for variable, data in values.items():
            group = h5_file.create_group(variable)
            group.create_dataset(str(year), data=data)


def _write_metadata(path: Path, year: int, **overrides) -> None:
    metadata = {
        "year": year,
        "profile": {"name": "ss-payroll-tob"},
        "target_source": {"name": "trustees_2025_current_law"},
        "tax_assumption": {"name": "trustees-core-thresholds-v1"},
        "support_augmentation": {
            "name": "donor-backed-composite-v1",
            "target_year": 2100,
            "target_year_strategy": "fixed",
            "blueprint_base_weight_scale": 5.0,
            "sanitize_clone_non_target_income": True,
            "sanitize_worker_non_target_income": False,
        },
        "calibration_audit": {
            "calibration_quality": "exact",
            "validation_passed": True,
        },
        "policyengine_us": {
            "version": "1.691.10",
            "direct_url": {
                "vcs_info": {
                    "commit_id": "4fd79e6608bc2dac3a7fde0be37191cb4870bd85",
                    "vcs": "git",
                },
            },
            "git_dirty": False,
        },
    }
    for key, value in overrides.items():
        metadata[key] = value
    Path(f"{path}.metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_with_long_term_sha(
    sha256: str,
    version: str = "1.691.12",
    metadata_sha256=None,
):
    return SimpleNamespace(
        model_package=SimpleNamespace(version=version),
        datasets={
            "long_term_cps_2100": SimpleNamespace(
                sha256=sha256,
                metadata_sha256=metadata_sha256,
            )
        },
    )


def test__load_long_term_datasets__loads_h5_and_sidecar_metadata(tmp_path):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(h5_path, 2075)

    datasets = load_long_term_datasets(
        [2075],
        data_folder=str(tmp_path),
        required_profile="ss-payroll-tob",
        required_target_source="trustees_2025_current_law",
        required_tax_assumption="trustees-core-thresholds-v1",
        required_support_augmentation_profile="donor-backed-composite-v1",
        required_support_augmentation_target_year=2100,
        required_support_augmentation_target_year_strategy="fixed",
        required_support_augmentation_blueprint_base_weight_scale=5.0,
        require_support_augmentation_sanitize_clone_non_target_income=True,
        require_support_augmentation_sanitize_worker_non_target_income=False,
        minimum_calibration_quality="exact",
        require_validation_passed=True,
    )

    dataset = datasets["long_term_cps_2075"]
    assert dataset.year == 2075
    assert dataset.filepath == str(h5_path)
    assert dataset.metadata["profile"]["name"] == "ss-payroll-tob"
    assert dataset.metadata_filepath == f"{h5_path}.metadata.json"
    assert len(dataset.data.household) == 1


def test__load_long_term_datasets__loads_policyengine_core_h5(tmp_path):
    h5_path = tmp_path / "2100.h5"
    _write_core_h5(h5_path, 2100)
    _write_metadata(h5_path, 2100)

    datasets = load_long_term_datasets(
        [2100],
        data_folder=str(tmp_path),
        required_profile="ss-payroll-tob",
        required_target_source="trustees_2025_current_law",
        required_tax_assumption="trustees-core-thresholds-v1",
        minimum_calibration_quality="exact",
        require_validation_passed=True,
    )

    dataset = datasets["long_term_cps_2100"]
    assert len(dataset.data.person) == 2
    assert len(dataset.data.household) == 1
    assert dataset.data.person["person_weight"].tolist() == [1_000.0, 1_000.0]
    assert dataset.data.tax_unit["tax_unit_weight"].tolist() == [1_000.0]
    assert dataset.data.household["state_code"].tolist() == ["CA"]


def test__load_long_term_datasets__rejects_metadata_contract_mismatch(tmp_path):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(h5_path, 2075, profile={"name": "age-only"})

    with pytest.raises(ValueError, match="profile.name"):
        load_long_term_datasets(
            [2075],
            data_folder=str(tmp_path),
            required_profile="ss-payroll-tob",
        )


def test__load_long_term_datasets__rejects_empty_metadata_when_contract_required(
    tmp_path,
):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    Path(f"{h5_path}.metadata.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="profile.name"):
        load_long_term_datasets(
            [2075],
            data_folder=str(tmp_path),
            required_profile="ss-payroll-tob",
        )


def test__load_long_term_datasets__rejects_support_contract_mismatch(tmp_path):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(
        h5_path,
        2075,
        support_augmentation={
            "name": "donor-backed-composite-v1",
            "target_year": 2100,
            "target_year_strategy": "fixed",
            "blueprint_base_weight_scale": 5.0,
            "sanitize_clone_non_target_income": False,
            "sanitize_worker_non_target_income": False,
        },
    )

    with pytest.raises(
        ValueError,
        match="support_augmentation.sanitize_clone_non_target_income",
    ):
        load_long_term_datasets(
            [2075],
            data_folder=str(tmp_path),
            require_support_augmentation_sanitize_clone_non_target_income=True,
        )


def test__load_managed_long_term_datasets__loads_bundled_local_mirror(
    monkeypatch,
    tmp_path,
):
    h5_path = tmp_path / "2100.h5"
    _write_us_h5(h5_path, 2100)
    _write_metadata(
        h5_path,
        2100,
        policyengine_us={"version": "1.700.0"},
    )
    dataset_uri = "hf://policyengine/policyengine-us-data/long_term/2100.h5@abc123"

    monkeypatch.setattr(
        us_datasets_module,
        "get_release_manifest",
        lambda country_id: _manifest_with_long_term_sha(
            _sha256(h5_path),
            version="1.700.0",
        ),
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_managed_dataset_reference",
        lambda country_id, dataset: dataset_uri,
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_local_managed_dataset_source",
        lambda country_id, uri: str(h5_path),
    )

    datasets = load_managed_long_term_datasets(
        [2100],
        required_profile="ss-payroll-tob",
        required_target_source="trustees_2025_current_law",
        required_tax_assumption="trustees-core-thresholds-v1",
        minimum_calibration_quality="exact",
        require_validation_passed=True,
    )

    dataset = datasets["long_term_cps_2100"]
    assert dataset.filepath == str(h5_path)
    assert dataset.metadata["policyengine_bundle"] == {
        "managed_by": "policyengine.py",
        "runtime_dataset": "long_term_cps_2100",
        "runtime_dataset_uri": dataset_uri,
    }


def test__load_managed_long_term_datasets__defaults_to_manifest_model_version(
    monkeypatch,
    tmp_path,
):
    h5_path = tmp_path / "2100.h5"
    _write_us_h5(h5_path, 2100)
    _write_metadata(h5_path, 2100, policyengine_us={"version": "1.691.10"})
    dataset_uri = "hf://policyengine/policyengine-us-data/long_term/2100.h5@abc123"

    monkeypatch.setattr(
        us_datasets_module,
        "get_release_manifest",
        lambda country_id: _manifest_with_long_term_sha(_sha256(h5_path)),
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_managed_dataset_reference",
        lambda country_id, dataset: dataset_uri,
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_local_managed_dataset_source",
        lambda country_id, uri: str(h5_path),
    )

    with pytest.raises(ValueError, match="policyengine_us.version"):
        load_managed_long_term_datasets([2100])


def test__load_managed_long_term_datasets__checks_manifest_sha256(
    monkeypatch,
    tmp_path,
):
    h5_path = tmp_path / "2100.h5"
    _write_us_h5(h5_path, 2100)
    _write_metadata(h5_path, 2100, policyengine_us={"version": "1.691.12"})
    dataset_uri = "hf://policyengine/policyengine-us-data/long_term/2100.h5@abc123"

    monkeypatch.setattr(
        us_datasets_module,
        "get_release_manifest",
        lambda country_id: _manifest_with_long_term_sha("0" * 64),
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_managed_dataset_reference",
        lambda country_id, dataset: dataset_uri,
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_local_managed_dataset_source",
        lambda country_id, uri: str(h5_path),
    )

    with pytest.raises(ValueError, match="sha256"):
        load_managed_long_term_datasets([2100])


def test__load_managed_long_term_datasets__checks_metadata_sha256(
    monkeypatch,
    tmp_path,
):
    h5_path = tmp_path / "2100.h5"
    _write_us_h5(h5_path, 2100)
    _write_metadata(h5_path, 2100, policyengine_us={"version": "1.691.12"})
    dataset_uri = "hf://policyengine/policyengine-us-data/long_term/2100.h5@abc123"

    monkeypatch.setattr(
        us_datasets_module,
        "get_release_manifest",
        lambda country_id: _manifest_with_long_term_sha(
            _sha256(h5_path),
            metadata_sha256="0" * 64,
        ),
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_managed_dataset_reference",
        lambda country_id, dataset: dataset_uri,
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_local_managed_dataset_source",
        lambda country_id, uri: str(h5_path),
    )

    with pytest.raises(ValueError, match="metadata"):
        load_managed_long_term_datasets([2100])


def test__load_managed_long_term_datasets__requires_local_mirror(
    monkeypatch,
):
    dataset_uri = "hf://policyengine/policyengine-us-data/long_term/2100.h5@abc123"
    monkeypatch.setattr(
        us_datasets_module,
        "get_release_manifest",
        lambda country_id: _manifest_with_long_term_sha("0" * 64),
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_managed_dataset_reference",
        lambda country_id, dataset: dataset_uri,
    )
    monkeypatch.setattr(
        us_datasets_module,
        "resolve_local_managed_dataset_source",
        lambda country_id, uri: uri,
    )

    with pytest.raises(FileNotFoundError, match="no local mirror exists"):
        load_managed_long_term_datasets([2100])


def test__load_long_term_datasets__rejects_policyengine_us_version_mismatch(
    tmp_path,
):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(h5_path, 2075)

    with pytest.raises(ValueError, match="policyengine_us.version"):
        load_long_term_datasets(
            [2075],
            data_folder=str(tmp_path),
            required_policyengine_us_version="1.691.3",
        )


def test__load_long_term_datasets__rejects_policyengine_us_git_sha_mismatch(
    tmp_path,
):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(h5_path, 2075)

    with pytest.raises(ValueError, match="policyengine_us.git_sha"):
        load_long_term_datasets(
            [2075],
            data_folder=str(tmp_path),
            required_policyengine_us_git_sha="a" * 40,
        )


def test__load_long_term_datasets__rejects_dirty_policyengine_us_build(
    tmp_path,
):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(
        h5_path,
        2075,
        policyengine_us={"version": "1.691.10", "git_dirty": True},
    )

    with pytest.raises(ValueError, match="policyengine_us.git_dirty"):
        load_long_term_datasets(
            [2075],
            data_folder=str(tmp_path),
            require_policyengine_us_clean_build=True,
        )


def test__load_long_term_datasets__can_require_runtime_policyengine_us_match(
    monkeypatch,
    tmp_path,
):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(h5_path, 2075)
    monkeypatch.setattr(
        us_datasets_module,
        "_runtime_policyengine_us_metadata",
        lambda: {
            "version": "1.691.10",
            "direct_url": {
                "vcs_info": {
                    "commit_id": "4fd79e6608bc2dac3a7fde0be37191cb4870bd85",
                    "vcs": "git",
                },
            },
        },
    )

    datasets = load_long_term_datasets(
        [2075],
        data_folder=str(tmp_path),
        require_runtime_policyengine_us_match=True,
    )

    assert datasets["long_term_cps_2075"].metadata["policyengine_us"]["version"] == (
        "1.691.10"
    )


def test__load_long_term_datasets__can_require_runtime_policyengine_us_hash_match(
    monkeypatch,
    tmp_path,
):
    h5_path = tmp_path / "2075.h5"
    _write_us_h5(h5_path, 2075)
    _write_metadata(
        h5_path,
        2075,
        policyengine_us={
            "version": "1.691.12",
            "package_tree_sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        us_datasets_module,
        "_runtime_policyengine_us_metadata",
        lambda: {
            "version": "1.691.12",
            "package_tree_sha256": "b" * 64,
        },
    )

    with pytest.raises(ValueError, match="package_tree_sha256"):
        load_long_term_datasets(
            [2075],
            data_folder=str(tmp_path),
            require_runtime_policyengine_us_match=True,
        )
