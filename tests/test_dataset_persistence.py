"""Dataset persistence semantics: construction never writes to disk.

Regression tests for the production incident where a region-scoped
simulation silently truncated the shared national dataset file it was
derived from. Root cause: constructing a dataset with ``data=`` used to
auto-save to ``filepath``, and region scoping built its filtered copy with
``filepath=<source file>`` — so constructing the scoped copy overwrote the
shared file with one region's rows. The next request on the same (reused)
container then either crashed ("No households found matching state_fips=N")
or computed a "national" result on one state's data.

These tests reproduce the mechanism at the dataset level (no microsimulation)
and pin the invariant: constructing a dataset never writes; persistence is
explicit via ``save()``; and region scoping produces a filepath-less
in-memory copy.
"""

import pytest

from policyengine.core.scoping_strategy import RowFilterStrategy
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)

# Mirrors policyengine.tax_benefit_models.us.model.US_GROUP_ENTITIES without
# importing the model module (which eagerly instantiates the certified model).
US_GROUP_ENTITIES = ["household", "tax_unit", "spm_unit", "family", "marital_unit"]


def _scope_us(source, state_fips):
    """Build a region-scoped copy the way ``PolicyEngineUSModel.run`` does.

    Filters ``source`` to one state and constructs the scoped dataset with
    ``filepath=None`` (the post-fix convention: an in-memory derived copy
    that can never be persisted back over its source file).
    """
    scoped_data = RowFilterStrategy(
        variable_name="state_fips", variable_value=state_fips
    ).apply(
        entity_data=source.data.entity_data,
        group_entities=US_GROUP_ENTITIES,
        year=source.year,
    )
    return PolicyEngineUSDataset(
        id=f"{source.id}_scoped",
        name=source.name,
        description=source.description,
        filepath=None,
        year=source.year,
        data=USYearData(
            **{key: scoped_data[key] for key in ["person", *US_GROUP_ENTITIES]}
        ),
    )


def test__construct_with_data__does_not_write_to_filepath(us_test_dataset, tmp_path):
    """Constructing a dataset with ``data=`` must not touch ``filepath``.

    Under the old autosave behaviour this assertion failed: construction
    truncated and rewrote the file.
    """
    source_path = tmp_path / "national.h5"
    us_test_dataset.filepath = str(source_path)
    us_test_dataset.save()
    original_bytes = source_path.read_bytes()

    # Construct another dataset pointing at the same file but carrying a
    # filtered subset — exactly the shape of the region-scoping bug.
    filtered = RowFilterStrategy(variable_name="state_fips", variable_value=6).apply(
        entity_data=us_test_dataset.data.entity_data,
        group_entities=US_GROUP_ENTITIES,
        year=us_test_dataset.year,
    )
    PolicyEngineUSDataset(
        id="scoped",
        name="scoped",
        description="scoped",
        filepath=str(source_path),
        year=us_test_dataset.year,
        data=USYearData(**{k: filtered[k] for k in ["person", *US_GROUP_ENTITIES]}),
    )

    assert source_path.read_bytes() == original_bytes


def test__sequential_region_scopes__leave_shared_source_intact(
    us_test_dataset, tmp_path
):
    """Two region-scoped runs sharing one file must not corrupt each other.

    Reproduces the reused-Modal-container sequence: the fixture has states 6
    (two households) and 34 (one household). Under the bug, scoping state 6
    rewrote the shared file to only-state-6 rows, so scoping state 34 next
    found zero households. After the fix the shared file is immutable and
    both scopes succeed.
    """
    source_path = tmp_path / "national.h5"
    us_test_dataset.filepath = str(source_path)
    us_test_dataset.save()
    original_bytes = source_path.read_bytes()

    expected_households = {6: 2, 34: 1}
    for state_fips, n_households in expected_households.items():
        source = PolicyEngineUSDataset(
            name="national",
            description="national",
            filepath=str(source_path),
            year=2024,
        )  # autoloads from the shared file
        scoped = _scope_us(source, state_fips)

        assert len(scoped.data.household) == n_households
        # The shared file must never change across scoped runs.
        assert source_path.read_bytes() == original_bytes


def test__save_without_filepath__raises(us_test_dataset):
    """A filepath-less (in-memory / scoped) dataset cannot be silently saved."""
    scoped = _scope_us(us_test_dataset, 6)
    assert scoped.filepath is None
    with pytest.raises(ValueError, match="no filepath"):
        scoped.save()


def test__uk_save_without_filepath__raises(uk_test_dataset):
    uk_test_dataset.filepath = None
    with pytest.raises(ValueError, match="no filepath"):
        uk_test_dataset.save()


def test__construct_with_filepath_only__autoloads(us_test_dataset, tmp_path):
    """Load-on-construction still works (persistence direction unchanged)."""
    source_path = tmp_path / "roundtrip.h5"
    us_test_dataset.filepath = str(source_path)
    us_test_dataset.save()

    loaded = PolicyEngineUSDataset(
        name="loaded",
        description="loaded",
        filepath=str(source_path),
        year=2024,
    )
    assert loaded.data is not None
    assert len(loaded.data.household) == len(us_test_dataset.data.household)


def test__construct_with_no_filepath_and_no_data__is_inert(tmp_path):
    """No filepath and no data: construction neither loads nor writes."""
    ds = PolicyEngineUSDataset(
        name="empty", description="empty", filepath=None, year=2024
    )
    assert ds.data is None
    assert ds.filepath is None
    # Nothing was written anywhere we can point at.
    assert list(tmp_path.iterdir()) == []
