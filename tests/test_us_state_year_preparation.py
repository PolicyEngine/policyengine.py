"""Real, tiny country-model preparation agrees with national-then-filter."""

import pandas as pd
import pytest

from policyengine.provenance.dataset_materialization import DatasetSource
from policyengine.tax_benefit_models.us import datasets as dataset_module
from policyengine.tax_benefit_models.us.datasets import US_ENTITY_KEYS, create_datasets
from policyengine.tax_benefit_models.us.legacy_inputs import (
    RENAMES_RECORD_KEY,
    read_renames_record,
)
from policyengine.tax_benefit_models.us.state_preparation import (
    USStateYearArtifact,
    partition_certified_us_source,
    prepare_us_state_year,
)
from tests.us_partition_fixtures import write_source


@pytest.fixture(
    scope="module", params=[False, True], ids=["stored-wic", "missing-acs-wic"]
)
def prepared(tmp_path_factory, request):
    directory = tmp_path_factory.mktemp("state_year")
    source = write_source(directory / "source.h5", acs_wic_gaps=request.param)
    manifest = partition_certified_us_source(source, directory / "states")
    return directory, source, manifest


@pytest.mark.parametrize("year", [2025, 2026, 2027])
def test_state_first_equals_national_first_for_every_entity(
    prepared, monkeypatch, year
):
    directory, source, manifest = prepared
    monkeypatch.setattr(
        dataset_module,
        "materialize_dataset",
        lambda *args, **kwargs: DatasetSource(
            source_uri=source.source_uri,
            path=str(source.path),
            bundle_dataset=source,
        ),
    )
    national = next(
        iter(
            create_datasets(
                years=[year], data_folder=str(directory / "national")
            ).values()
        )
    )
    for state in ("CA", "UT"):
        partition = next(p for p in manifest.partitions if p.state_code == state)
        artifact = prepare_us_state_year(partition, year, directory / "prepared")
        assert (
            USStateYearArtifact.model_validate_json(artifact.model_dump_json())
            == artifact
        )
        people = pd.DataFrame(national.data.person)
        households = pd.DataFrame(national.data.household)
        household_ids = households.loc[
            households.state_fips == partition.state_fips, "household_id"
        ]
        selected_people = people.loc[people.person_household_id.isin(household_ids)]
        source_people = pd.read_hdf(partition.path, "person")
        if source_people.would_claim_wic.isna().any():
            # Source records remain missing; both preparation paths apply the
            # explicitly temporary ACS assumption before materializing outputs.
            assert source_people.person_support_channel.eq("acs_2024_1yr").all()
            assert selected_people.takes_up_wic_if_eligible.all()
        for entity in US_ENTITY_KEYS:
            frame = pd.DataFrame(national.data.entity_data[entity])
            ids = (
                selected_people.person_id
                if entity == "person"
                else selected_people[f"person_{entity}_id"]
            )
            expected = (
                frame.loc[frame[f"{entity}_id"].isin(ids)]
                .sort_values(f"{entity}_id")
                .reset_index(drop=True)
            )
            actual = (
                pd.read_hdf(artifact.path, entity)
                .sort_values(f"{entity}_id")
                .reset_index(drop=True)
            )
            pd.testing.assert_frame_equal(actual, expected)
        assert artifact.identity.package_versions["policyengine-us"]
        assert read_renames_record(artifact.path) == {
            "would_claim_wic": "takes_up_wic_if_eligible"
        }
        assert national.metadata[RENAMES_RECORD_KEY] == read_renames_record(
            artifact.path
        )


def test_partition_tampering_is_rejected_before_preparation(prepared):
    directory, _, manifest = prepared
    bad = manifest.partitions[0].model_copy(update={"sha256": "0" * 64})
    with pytest.raises(ValueError, match="SHA-256"):
        prepare_us_state_year(bad, 2025, directory / "tampered")
    assert not (directory / "tampered").exists()


def test_existing_output_is_not_overwritten(prepared):
    directory, _, manifest = prepared
    partition = manifest.partitions[1]
    prepare_us_state_year(partition, 2025, directory / "no_overwrite")
    with pytest.raises(FileExistsError):
        prepare_us_state_year(partition, 2025, directory / "no_overwrite")


def test_failed_year_write_removes_partial_file_and_preserves_input(
    prepared, monkeypatch
):
    from pathlib import Path

    from policyengine.utils.hashing import sha256_file

    directory, _, manifest = prepared
    partition = manifest.partitions[0]

    def fail_save(dataset):
        Path(dataset.filepath).write_bytes(b"fixture incomplete write")
        raise OSError("fixture write failure")

    monkeypatch.setattr(dataset_module.PolicyEngineUSDataset, "save", fail_save)
    with pytest.raises(OSError, match="fixture write failure"):
        prepare_us_state_year(partition, 2025, directory / "failed_year")
    assert not list((directory / "failed_year").iterdir())
    assert sha256_file(partition.path) == partition.sha256
