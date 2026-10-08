"""Partition correctness on all six native entities, without network access."""

import pandas as pd
import pytest

from policyengine.tax_benefit_models.us.datasets import US_ENTITY_KEYS
from policyengine.tax_benefit_models.us.state_preparation import (
    USPartitionManifest,
    _load_native,
    partition_certified_us_source,
)
from policyengine.utils.hashing import sha256_file
from tests.us_partition_fixtures import write_source


def test_complete_disjoint_round_trip_preserves_native_inputs(tmp_path):
    source = write_source(tmp_path / "source.h5", include_nulls=True)
    manifest = partition_certified_us_source(source, tmp_path / "states")
    assert len(manifest.partitions) == 51
    assert (
        USPartitionManifest.model_validate_json(manifest.model_dump_json()) == manifest
    )
    for entity in US_ENTITY_KEYS:
        combined = pd.concat(
            [_load_native(part.path)[0][entity] for part in manifest.partitions]
        )
        original = _load_native(source.path)[0][entity]
        id_column = f"{entity}_id"
        pd.testing.assert_frame_equal(
            combined.sort_values(id_column), original.sort_values(id_column)
        )
    assert sha256_file(source.path) == source.sha256
    for partition in manifest.partitions:
        assert pd.read_hdf(partition.path, "_time_period").iloc[0] == 2024
        assert pd.read_hdf(partition.path, "_fixture_metadata").iloc[0] == "preserve-me"
        assert sha256_file(partition.path) == partition.sha256


@pytest.mark.parametrize(
    "failure",
    [
        "hash",
        "unknown_state",
        "missing_state",
        "dangling_link",
        "cross_state_group",
        "missing_person",
    ],
)
def test_invalid_source_does_not_publish_partial_files(tmp_path, failure):
    source = write_source(tmp_path / "source.h5")
    with pd.HDFStore(source.path, "a") as store:
        if failure == "hash":
            frame = store["household"]
            frame["household_weight"] *= 2
            store["household"] = frame
        if failure == "unknown_state":
            frame = store["household"]
            frame.loc[frame.index[0], "state_fips"] = 99
            store["household"] = frame
        elif failure == "missing_state":
            frame = store["household"]
            frame.loc[frame.index[0], "state_fips"] = None
            store["household"] = frame
        elif failure in {"dangling_link", "cross_state_group", "missing_person"}:
            frame = store["person"]
            if failure == "missing_person":
                frame = frame.iloc[1:]
            else:
                frame.loc[frame.index[0], "person_tax_unit_id"] = (
                    999999
                    if failure == "dangling_link"
                    else frame.iloc[1].person_tax_unit_id
                )
            store["person"] = frame
    if failure != "hash":
        source = source.model_copy(update={"sha256": sha256_file(source.path)})
    with pytest.raises(ValueError):
        partition_certified_us_source(source, tmp_path / "states")
    assert not list((tmp_path / "states").glob("*.h5"))
    assert not list((tmp_path / "states").glob("*.partial"))


def test_write_failure_cleans_only_its_own_files(tmp_path, monkeypatch):
    import policyengine.tax_benefit_models.us.state_preparation as module

    source = write_source(tmp_path / "source.h5")
    output = tmp_path / "states"
    output.mkdir()
    sentinel = output / "unrelated.txt"
    sentinel.write_text("keep")
    original = module._write_partition
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("fixture disk failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_write_partition", fail_second)
    with pytest.raises(OSError, match="fixture disk failure"):
        partition_certified_us_source(source, output)
    assert sentinel.read_text() == "keep"
    assert not list(output.glob("*.h5"))
