"""Format checks on published tables. Synthetic data."""

import numpy as np
import pandas as pd
import pytest

from policyengine.disclosure import (
    AreaWeights,
    Release,
    estimate_change,
    validate_public,
)
from policyengine.disclosure.__main__ import main


def _public_table():
    """A release with reported, approximate, withheld and zero rows."""
    rng = np.random.default_rng(0)
    affected = {"A": 4, "B": 14, "C": 70, "D": 0, "E": 6}
    codes, deltas = [], []
    for code, count in affected.items():
        codes += [code] * 150
        deltas += list(rng.uniform(100.0, 900.0, count)) + [0.0] * (150 - count)
    n = len(codes)
    baseline = rng.uniform(20_000.0, 60_000.0, n)
    release = Release()
    release.add(
        estimate_change(
            level="constituency",
            reform="reform",
            year=2026,
            areas=AreaWeights.from_labels(codes, np.full(n, 100.0)),
            source_ids=np.arange(n),
            baseline=baseline,
            reformed=baseline + np.array(deltas),
        )
    )
    release.check()
    return release.to_public()


@pytest.fixture(scope="module")
def table():
    return _public_table()


@pytest.fixture
def frame(table):
    return pd.read_csv(
        pd.io.common.StringIO(table.to_frame().to_csv(index=False)),
        dtype=str,
        keep_default_na=False,
    )


def _first(frame, **where):
    mask = np.ones(len(frame), dtype=bool)
    for column, value in where.items():
        mask &= (frame[column] == value).to_numpy()
    return frame.index[mask][0]


def test_release_output_passes_as_a_table_a_frame_and_a_file(table, tmp_path):
    path = table.to_csv(tmp_path / "constituency.csv")

    assert set(table.to_frame()["tier"]) == {"reported", "approximate", "withheld"}
    assert validate_public(table) == []
    assert validate_public(table.to_frame()) == []
    assert validate_public(path) == []
    assert validate_public(tmp_path) == []


def test_a_private_audit_column_is_rejected(frame):
    frame["n_sources"] = "12"

    problems = validate_public(frame)

    assert any("private audit columns" in problem for problem in problems)


def test_an_unknown_column_is_rejected_but_an_area_name_is_allowed(frame):
    frame["area_name"] = "Somewhere"
    assert validate_public(frame) == []

    frame["household_count"] = "100"
    assert any("not allowed" in problem for problem in validate_public(frame))


def test_a_missing_column_is_rejected(frame):
    problems = validate_public(frame.drop(columns=["tier"]))

    assert any("missing columns" in problem for problem in problems)


def test_an_unknown_tier_is_rejected(frame):
    frame.loc[0, "tier"] = "fallback"

    assert any("unknown tier" in problem for problem in validate_public(frame))


@pytest.mark.parametrize("column", ["value", "lo", "hi", "direction", "support_band"])
def test_a_withheld_row_must_be_empty(frame, column):
    row = _first(frame, tier="withheld", outcome="average_change")
    frame.loc[row, column] = "10–29" if column == "support_band" else "5"

    assert any("withheld row has entries" in p for p in validate_public(frame))


def test_a_withheld_row_must_not_say_why_in_detail(frame):
    row = _first(frame, tier="withheld")
    frame.loc[row, "reason"] = "secondary"

    assert any("wrong reason" in problem for problem in validate_public(frame))


def test_a_band_with_a_hyphen_is_rejected(frame):
    row = _first(frame, tier="approximate")
    frame.loc[row, "support_band"] = "10-29"

    assert any("unknown support band" in p for p in validate_public(frame))


def test_an_unrounded_value_is_rejected(frame):
    row = _first(frame, tier="reported", outcome="average_change", area_code="C")
    frame.loc[row, ["value", "lo", "hi"]] = ["437.6213", "420.1182", "455.9921"]

    assert any("rounding" in p or "rounded" in p for p in validate_public(frame))


def test_a_value_outside_its_interval_is_rejected(frame):
    row = _first(frame, tier="reported", outcome="average_change", area_code="C")
    frame.loc[row, "lo"] = str(float(frame.loc[row, "hi"]) + 100)

    assert any("outside its interval" in p for p in validate_public(frame))


def test_a_duplicate_row_is_rejected(frame):
    doubled = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    assert any("duplicate" in problem for problem in validate_public(doubled))


def test_a_non_zero_value_cannot_have_a_band_under_ten(frame):
    row = _first(frame, tier="reported", outcome="average_change", area_code="C")
    frame.loc[row, "support_band"] = "<10"

    assert any("under 10" in problem for problem in validate_public(frame))


def test_a_zero_row_shows_the_households_it_was_measured_on(frame):
    zero = _first(frame, outcome="average_change", area_code="D")

    assert frame.loc[zero, "value"] == "0.0"
    assert frame.loc[zero, "direction"] == "no_change"
    assert frame.loc[zero, "support_band"] == "30+"


def test_a_direction_must_match_its_interval(frame):
    row = _first(frame, tier="reported", outcome="average_change", area_code="C")
    assert frame.loc[row, "direction"] == "gain"
    frame.loc[row, "direction"] = "too_close_to_call"

    assert any("direction does not match" in p for p in validate_public(frame))


def test_shares_must_add_to_one_and_stay_in_range(frame):
    row = _first(frame, outcome="share_no_change", area_code="C")
    frame.loc[row, "value"] = "0.5"
    frame.loc[row, ["lo", "hi"]] = ["0.4", "0.6"]

    assert any("do not add to one" in p for p in validate_public(frame))

    frame.loc[row, "hi"] = "1.4"
    assert any("outside 0 to 1" in problem for problem in validate_public(frame))


def test_no_change_needs_both_shares(frame):
    row = _first(frame, outcome="share_gaining", area_code="C")
    frame.loc[row, ["value", "lo", "hi", "support_band"]] = ""
    frame.loc[row, ["tier", "reason"]] = ["withheld", "disclosure_control"]

    assert any("without both shares" in p for p in validate_public(frame))


def test_a_directory_must_hold_only_checked_files(table, tmp_path):
    table.to_csv(tmp_path / "constituency.csv")
    pd.DataFrame({"constituency_code": ["A"], "average_gain": [12.34]}).to_csv(
        tmp_path / "old_seat_table.csv", index=False
    )
    (tmp_path / "notes.json").write_text("{}")

    problems = validate_public(tmp_path)

    assert problems == [
        "notes.json: not a disclosure table and not reviewed",
        "old_seat_table.csv: not a disclosure table and not reviewed",
    ]
    assert (
        validate_public(tmp_path, reviewed=["notes.json", "old_seat_table.csv"]) == []
    )
    assert validate_public(tmp_path / "missing") != []


def test_the_command_line_exits_with_the_number_of_problems(table, tmp_path, capsys):
    good = tmp_path / "good"
    good.mkdir()
    table.to_csv(good / "constituency.csv")
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "seat_values.csv").write_text("constituency_code,average_gain\nA,12.34\n")

    assert main(["validate", str(good)]) == 0
    assert main(["validate", str(good), str(bad)]) == 1
    assert main(["validate", str(bad), "--reviewed", "seat_values.csv"]) == 0
    output = capsys.readouterr().out
    assert "1 problem(s) found." in output
    assert "12.34" not in output
