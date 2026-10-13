"""Settings and public models of the disclosure layer."""

import ast
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from policyengine.disclosure import (
    AreaWeights,
    DisclosureSettings,
    PriorPublic,
    PublicRow,
    PublicTable,
    Release,
    estimate_change,
)
from policyengine.disclosure.schema import (
    BAND_10_TO_29,
    PUBLIC_COLUMNS,
    REASON_DISCLOSURE_CONTROL,
    REPORTED,
    WITHHELD,
)

PACKAGE = Path(__file__).parents[1] / "src" / "policyengine" / "disclosure"


@pytest.mark.parametrize(
    "loosened",
    [
        {"min_sources": 9},
        {"max_top_share": 0.6},
        {"min_n_eff": 9.9},
        {"change_tolerance": 0.0},
        {"change_tolerance": 1e-9},
        {"min_rest_share": 0.01},
        {"n_replicates": 50},
    ],
)
def test_settings_cannot_be_loosened(loosened):
    with pytest.raises(ValidationError):
        DisclosureSettings(**loosened)


def test_settings_are_validated_again_before_use():
    """``model_copy`` and ``model_construct`` skip validation; the layer does not."""
    copied = DisclosureSettings().model_copy(update={"min_sources": 1})
    constructed = DisclosureSettings.model_construct(min_sources=1)
    areas = AreaWeights.from_labels(["A"] * 20, [1.0] * 20)

    assert copied.min_sources == 1
    for settings in (copied, constructed):
        with pytest.raises(ValidationError):
            settings.revalidated()
        with pytest.raises(ValidationError):
            Release(settings)
        with pytest.raises(ValidationError):
            estimate_change(
                level="region",
                reform="r",
                year=2026,
                areas=areas,
                source_ids=range(20),
                baseline=[100.0] * 20,
                reformed=[200.0] * 20,
                settings=settings,
            )


def test_settings_can_be_raised_for_special_conditions():
    settings = DisclosureSettings(min_sources=30, min_n_eff=30.0)

    assert settings.min_sources == 30


def test_settings_are_frozen_and_reject_unknown_fields():
    settings = DisclosureSettings()

    with pytest.raises(ValidationError):
        settings.min_sources = 30
    with pytest.raises(ValidationError):
        DisclosureSettings(noise_key="secret")


def test_rounding_bases_must_be_powers_of_ten_for_known_outcomes():
    merged = DisclosureSettings(min_rounding_base={"average_change": 10.0})

    assert merged.min_rounding_base["average_change"] == 10.0
    assert merged.min_rounding_base["share_gaining"] == 0.001
    with pytest.raises(ValidationError):
        DisclosureSettings(min_rounding_base={"average_change": 5.0})
    with pytest.raises(ValidationError):
        DisclosureSettings(min_rounding_base={"median_change": 1.0})


def test_noise_distance_must_keep_clear_of_one():
    with pytest.raises(ValidationError):
        DisclosureSettings(noise_distance=(0.0, 0.1))
    with pytest.raises(ValidationError):
        DisclosureSettings(noise_distance=(0.2, 0.1))


def test_public_table_round_trips_through_json_with_a_withheld_row():
    table = PublicTable(
        rows=[
            PublicRow(
                level="region",
                area_code="A",
                reform="r",
                year=2026,
                outcome="average_change",
                value=120.0,
                lo=100.0,
                hi=140.0,
                direction="gain",
                tier=REPORTED,
                support_band=BAND_10_TO_29,
            ),
            PublicRow(
                level="region",
                area_code="B",
                reform="r",
                year=2026,
                outcome="average_change",
                tier=WITHHELD,
                reason=REASON_DISCLOSURE_CONTROL,
            ),
        ]
    )

    restored = PublicTable.model_validate_json(table.model_dump_json())

    assert restored == table
    assert list(table.to_frame().columns) == list(PUBLIC_COLUMNS)
    assert pd.isna(table.to_frame().loc[1, "value"])


def test_middle_support_band_uses_an_en_dash():
    assert BAND_10_TO_29 == "10–29"


def test_prior_public_reads_cells_from_a_frame():
    frame = pd.DataFrame(
        {
            "level": ["constituency"],
            "area_code": ["C1"],
            "reform": ["r"],
            "year": [2026],
            "outcome": ["average_change"],
            "value": [1.0],
        }
    )

    prior = PriorPublic.from_frame("2025 dashboard", frame)

    assert prior.cells == [("constituency", "C1", "r", 2026, "average_change")]
    with pytest.raises(ValueError, match="lacks columns"):
        PriorPublic.from_frame("bad", frame.drop(columns=["outcome"]))


def test_package_imports_nothing_from_the_rest_of_the_library():
    """The package must stay liftable into its own distribution."""
    for path in sorted(PACKAGE.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                # Relative imports stay inside the package.
                names = [node.module or ""] if node.level == 0 else []
            else:
                continue
            for name in names:
                assert not name.startswith("policyengine"), (path.name, name)
                assert not name.startswith("scipy"), (path.name, name)


def test_package_never_calls_the_builtin_hash():
    """``hash()`` is salted per process, so it cannot give stable factors."""
    for path in sorted(PACKAGE.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "hash", path.name
