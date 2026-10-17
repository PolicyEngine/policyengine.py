"""Tests for the UK area lists shipped with the package."""

import csv
import re
from collections import Counter
from unittest.mock import patch

import pytest

from policyengine.countries.uk.regions import build_uk_region_registry
from policyengine.data.uk_geography_assets import (
    LOCAL_AUTHORITY_ASSET_SPEC,
    UK_AREA_LIST_FILES,
    packaged_uk_area_list_path,
)

GSS_CODE = re.compile(r"^[A-Z]\d{8}$")

# The 17 districts abolished on 1 April 2023, when Cumberland, Westmorland and
# Furness, North Yorkshire and Somerset became unitary authorities.
ABOLISHED_2023_DISTRICTS = {
    "E07000026",
    "E07000027",
    "E07000028",
    "E07000029",
    "E07000030",
    "E07000031",
    "E07000163",
    "E07000164",
    "E07000165",
    "E07000166",
    "E07000167",
    "E07000168",
    "E07000169",
    "E07000187",
    "E07000188",
    "E07000189",
    "E07000246",
}
NEW_2023_UNITARIES = {"E06000063", "E06000064", "E06000065", "E06000066"}


def _rows(geography_type: str) -> list[dict]:
    with open(packaged_uk_area_list_path(geography_type), encoding="utf-8") as file:
        return list(csv.DictReader(file))


@pytest.mark.parametrize("geography_type", sorted(UK_AREA_LIST_FILES))
def test_area_list_rows_are_well_formed(geography_type):
    rows = _rows(geography_type)
    codes = [row["code"] for row in rows]

    assert len(codes) == len(set(codes))
    assert all(GSS_CODE.match(code) for code in codes)
    assert all(row["name"].strip() and row["name"] != row["code"] for row in rows)
    hexes = [(int(row["x"]), int(row["y"])) for row in rows]
    assert len(hexes) == len(set(hexes)), "two areas share a hex"


def test_local_authority_list_is_the_april_2023_frame():
    codes = {row["code"] for row in _rows("local_authority")}

    assert len(codes) == 361
    assert Counter(code[0] for code in codes) == {"E": 296, "W": 22, "S": 32, "N": 11}
    assert "N09000011" in codes  # Ards and North Down
    assert NEW_2023_UNITARIES <= codes
    assert not ABOLISHED_2023_DISTRICTS & codes


def test_constituency_list_is_the_2024_frame_including_northern_ireland():
    codes = [row["code"] for row in _rows("constituency")]

    assert len(codes) == 650
    assert Counter(code[:3] for code in codes) == {
        "E14": 543,
        "S14": 57,
        "W07": 32,
        "N05": 18,
    }


def test_weight_matrix_lookup_stays_paired_with_its_matrix():
    # The legacy local-authority matrix indexes areas by the row order of the
    # CSV it was built with, so the packaged list must not replace it.
    assert (
        LOCAL_AUTHORITY_ASSET_SPEC.lookup_csv_filename == "local_authorities_2021.csv"
    )
    assert UK_AREA_LIST_FILES["local_authority"] != (
        LOCAL_AUTHORITY_ASSET_SPEC.lookup_csv_filename
    )


def test_unknown_geography_type_has_no_packaged_list():
    with pytest.raises(ValueError, match="No packaged UK area list"):
        packaged_uk_area_list_path("ward")


def test_registry_builds_every_area_without_network():
    # Before the lists were packaged, these regions came from a GCS download
    # that silently returned no areas when it failed.
    with patch(
        "policyengine_core.tools.google_cloud.download_gcs_file",
        side_effect=AssertionError("network access"),
    ):
        registry = build_uk_region_registry(
            include_constituencies=True,
            include_local_authorities=True,
        )

    assert len(registry.get_by_type("national")) == 1
    assert len(registry.get_by_type("country")) == 4
    assert len(registry.get_by_type("constituency")) == 650
    assert len(registry.get_by_type("local_authority")) == 361
    assert registry.get("local_authority/N09000011").label == "Ards and North Down"
