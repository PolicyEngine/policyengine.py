"""A researcher's flat file runs through the pinned US model, state by state."""

import logging

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

pytest.importorskip("policyengine_us")

import policyengine as pe  # noqa: E402
from policyengine.countries.us.data import US_STATE_FIPS  # noqa: E402
from policyengine.tax_benefit_models.us.flat_file import (  # noqa: E402
    LOCAL_GEOGRAPHY,
    STATE_LABELS,
    prepare_flat_file,
)

YEAR = 2024
NATIONAL_SPM = {"geography_kind": "national"}
MISSISSIPPI = 28
LOS_ANGELES_COUNTY = "06037"
GROUP_COLUMNS = (
    "household_id",
    "tax_unit_id",
    "spm_unit_id",
    "family_id",
    "marital_unit_id",
)


def survey() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5, 6, 7],
            "household_id": [1, 1, 2, 2, 2, 2, 3],
            "tax_unit_id": [1, 1, 2, 2, 2, 2, 3],
            "spm_unit_id": [1, 1, 2, 2, 2, 2, 3],
            "family_id": [1, 1, 2, 2, 2, 2, 3],
            "marital_unit_id": [1, 1, 2, 2, 4, 5, 6],
            "age": [35, 5, 41, 39, 12, 9, 67],
            "employment_income": [20000, 0, 45000, 10000, 0, 0, 12000],
            "household_weight": [1000, 1000, 500, 500, 500, 500, 2000],
        }
    )


def in_state(frame: pd.DataFrame, fips: int = 6) -> pd.DataFrame:
    return frame.assign(state_fips=fips)


class TestPreparedColumns:
    def test_leaves_the_input_alone(self):
        people = in_state(survey())
        before = people.copy()
        prepare_flat_file(people, year=YEAR, state="MS")
        pd.testing.assert_frame_equal(people, before)

    def test_bare_columns_take_the_year(self):
        prepared = prepare_flat_file(in_state(survey()), year=YEAR)
        assert f"age__{YEAR}" in prepared.columns
        assert "age" not in prepared.columns

    def test_a_period_stays_on_its_column(self):
        people = in_state(survey()).assign(is_household_head__ETERNITY=False)
        prepared = prepare_flat_file(people, year=YEAR)
        assert "is_household_head__ETERNITY" in prepared.columns

    def test_group_ids_move_onto_each_persons_row(self):
        prepared = prepare_flat_file(in_state(survey()), year=YEAR)
        for column in GROUP_COLUMNS:
            assert f"{column}__{YEAR}" not in prepared.columns
            assert (
                prepared[f"person_{column}__{YEAR}"].tolist()
                == survey()[column].tolist()
            )

    def test_an_export_with_many_id_columns_settles_on_one(self):
        people = in_state(survey()).rename(
            columns={"household_id": "household_id__ETERNITY"}
        )
        people[f"person_household_id__{YEAR}"] = people["household_id__ETERNITY"]
        prepared = prepare_flat_file(people, year=YEAR)
        ids = [column for column in prepared if "household_id" in column]
        assert ids == [f"person_household_id__{YEAR}"]

    def test_text_ids_become_integers_that_keep_the_groups(self):
        people = in_state(survey())
        people["household_id"] = people["household_id"].map(
            {1: "A-17", 2: "B-02", 3: "C-99"}
        )
        prepared = prepare_flat_file(people, year=YEAR)
        ids = prepared[f"person_household_id__{YEAR}"]
        assert pd.api.types.is_integer_dtype(ids)
        assert ids.tolist() == [0, 0, 1, 1, 1, 1, 2]

    def test_a_person_id_is_optional(self):
        people = in_state(survey()).drop(columns="person_id")
        prepared = prepare_flat_file(people, year=YEAR)
        assert prepared[f"person_id__{YEAR}"].nunique() == len(people)

    def test_unknown_columns_leave_with_a_log(self, caplog):
        people = in_state(survey()).assign(**{"survey_stratum": 3, "foo__bar__2024": 1})
        with caplog.at_level(logging.WARNING):
            prepared = prepare_flat_file(people, year=YEAR)
        assert "survey_stratum" in caplog.text
        assert "foo__bar__2024" in caplog.text
        assert not any("foo" in column for column in prepared)

    @pytest.mark.parametrize(
        "value, text",
        [
            (6037, LOS_ANGELES_COUNTY),
            (6037.0, LOS_ANGELES_COUNTY),
            ("6037", LOS_ANGELES_COUNTY),
            (LOS_ANGELES_COUNTY, LOS_ANGELES_COUNTY),
            (np.nan, ""),
            ("", ""),
        ],
    )
    def test_a_county_becomes_five_digit_text(self, value, text):
        people = in_state(survey()).assign(county_fips=value)
        prepared = prepare_flat_file(people, year=YEAR)
        assert set(prepared[f"county_fips__{YEAR}"]) == {text}


class TestRefusals:
    def test_no_rows(self):
        with pytest.raises(ValueError, match="no rows"):
            prepare_flat_file(survey().iloc[:0], year=YEAR, state="MS")

    @pytest.mark.parametrize("column", GROUP_COLUMNS)
    def test_a_missing_group_names_its_column(self, column):
        people = in_state(survey()).drop(columns=column)
        with pytest.raises(ValueError, match=column):
            prepare_flat_file(people, year=YEAR)

    def test_a_blank_id(self):
        people = in_state(survey()).astype({"household_id": float})
        people.loc[0, "household_id"] = np.nan
        with pytest.raises(ValueError, match="blanks"):
            prepare_flat_file(people, year=YEAR)

    def test_a_person_on_two_rows(self):
        people = in_state(survey()).assign(person_id=1)
        with pytest.raises(ValueError, match="one row per person"):
            prepare_flat_file(people, year=YEAR)

    def test_no_age(self):
        with pytest.raises(ValueError, match="age"):
            prepare_flat_file(in_state(survey()).drop(columns="age"), year=YEAR)

    def test_an_age_only_from_later_years(self):
        people = in_state(survey()).rename(columns={"age": f"age__{YEAR + 1}"})
        with pytest.raises(ValueError, match="age"):
            prepare_flat_file(people, year=YEAR)

    def test_a_variable_given_twice(self):
        people = in_state(survey()).assign(**{f"age__{YEAR}": 40})
        with pytest.raises(ValueError, match="more than once"):
            prepare_flat_file(people, year=YEAR)

    def test_no_state(self):
        with pytest.raises(ValueError, match="California"):
            prepare_flat_file(survey(), year=YEAR)

    def test_a_state_that_does_not_exist(self):
        with pytest.raises(ValueError, match="99"):
            prepare_flat_file(in_state(survey(), 99), year=YEAR)

    @pytest.mark.parametrize("state", ["ZZ", 99, ""])
    def test_a_requested_state_that_does_not_exist(self, state):
        with pytest.raises(ValueError, match="postal code"):
            prepare_flat_file(survey(), year=YEAR, state=state)

    def test_a_household_across_states(self):
        people = in_state(survey())
        people.loc[0, "state_fips"] = MISSISSIPPI
        with pytest.raises(ValueError, match="span"):
            prepare_flat_file(people, year=YEAR)

    def test_a_county_outside_its_state(self):
        people = in_state(survey(), MISSISSIPPI).assign(county_fips=LOS_ANGELES_COUNTY)
        with pytest.raises(ValueError, match="outside"):
            prepare_flat_file(people, year=YEAR)

    def test_a_label_that_disagrees_with_the_state(self):
        people = in_state(survey(), MISSISSIPPI).assign(state_code="CA")
        with pytest.raises(ValueError, match="state_code"):
            prepare_flat_file(people, year=YEAR)

    def test_a_malformed_county(self):
        people = in_state(survey()).assign(county_fips="Los Angeles")
        with pytest.raises(ValueError, match="county_fips"):
            prepare_flat_file(people, year=YEAR)


class TestMovingToAState:
    def test_a_file_may_start_with_no_state(self):
        prepared = prepare_flat_file(survey(), year=YEAR, state="MS")
        assert set(prepared[f"state_fips__{YEAR}"]) == {MISSISSIPPI}

    def test_postal_code_and_fips_agree(self):
        pd.testing.assert_frame_equal(
            prepare_flat_file(survey(), year=YEAR, state="ms"),
            prepare_flat_file(survey(), year=YEAR, state=MISSISSIPPI),
        )

    def test_every_year_moves(self):
        people = in_state(survey()).assign(
            **{f"state_fips__{year}": 6 for year in (YEAR, YEAR + 1, YEAR + 2)}
        )
        people = people.drop(columns="state_fips")
        prepared = prepare_flat_file(people, year=YEAR, state="MS")
        columns = [column for column in prepared if column.startswith("state_fips")]
        assert len(columns) == 3
        assert set(prepared[columns].to_numpy().ravel()) == {MISSISSIPPI}

    def test_stale_geography_leaves(self):
        stale = {f"{name}__{YEAR}": "x" for name in (*STATE_LABELS, *LOCAL_GEOGRAPHY)}
        stale.pop(f"county_fips__{YEAR}")
        prepared = prepare_flat_file(
            survey().assign(**stale, county_fips=LOS_ANGELES_COUNTY),
            year=YEAR,
            state="MS",
        )
        for name in (*STATE_LABELS, *LOCAL_GEOGRAPHY):
            assert not any(column.startswith(f"{name}__") for column in prepared)


@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@given(st.integers(min_value=1, max_value=99_999))
def test_any_county_code_reads_the_same_as_text_or_number(code):
    """County codes survive whichever form read_csv left them in."""
    from_number = prepare_flat_file(
        in_state(survey(), 6).assign(county_fips=code), year=YEAR, state="CA"
    )
    from_text = prepare_flat_file(
        in_state(survey(), 6).assign(county_fips=f"{code:05d}"), year=YEAR, state="CA"
    )
    pd.testing.assert_frame_equal(from_number, from_text)


@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.sampled_from(sorted(US_STATE_FIPS)),
    st.sampled_from(sorted(US_STATE_FIPS)),
)
def test_moving_a_file_twice_lands_where_moving_it_once_does(first, second):
    """Preparation forgets the old state entirely, and keeps everything else."""
    once = prepare_flat_file(survey(), year=YEAR, state=second)
    twice = prepare_flat_file(
        prepare_flat_file(survey(), year=YEAR, state=first),
        year=YEAR,
        state=second,
    )
    pd.testing.assert_frame_equal(once[sorted(once)], twice[sorted(twice)])


@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@given(st.sampled_from(sorted(US_STATE_FIPS)))
def test_a_prepared_file_prepares_to_itself(state):
    """Preparing a file with its own state changes nothing."""
    prepared = prepare_flat_file(survey(), year=YEAR, state=state)
    again = prepare_flat_file(prepared, year=YEAR)
    pd.testing.assert_frame_equal(prepared[sorted(prepared)], again[sorted(again)])


@pytest.mark.parametrize("state", ["CA", "MS", "MN"])
def test_the_recipe_runs_a_csv_through_a_state(tmp_path, state):
    path = tmp_path / "your_survey.csv"
    survey().to_csv(path, index=False)
    people = pd.read_csv(path, dtype={"county_fips": str})

    sim = pe.us.flat_file_microsimulation(
        people, year=YEAR, state=state, spm=NATIONAL_SPM
    )

    assert set(sim.calculate("state_code", YEAR).values) == {state}
    assert set(sim.calculate("state_code", YEAR + 1).values) == {state}
    assert 0 <= sim.calculate("is_snap_eligible", f"{YEAR}-01").mean() <= 1
    assert sim.calculate("spm_unit_spm_threshold", YEAR).sum() > 0
    assert sim.populations["household"].count == 3
    assert sim.populations["marital_unit"].count == 5
    assert sim.policyengine_bundle["runtime_dataset"] == "flat_file"
    assert sim.policyengine_bundle["spm"]["geography_kind"] == "national"


def test_stale_geography_changes_nothing_after_a_move():
    """A file with stale geography runs as one that never had it."""
    stale = survey().assign(
        county_fips=LOS_ANGELES_COUNTY,
        zip_code="90001",
        state_code="CA",
        congressional_district_geoid=634,
    )
    arms = [
        pe.us.flat_file_microsimulation(people, year=YEAR, state="MS", spm=NATIONAL_SPM)
        for people in (stale, survey())
    ]
    for variable, period in [
        ("state_income_tax", YEAR),
        ("household_net_income", YEAR),
        ("is_snap_eligible", f"{YEAR}-01"),
    ]:
        first, second = (arm.calculate(variable, period).values for arm in arms)
        assert np.array_equal(first, second), variable


def test_a_county_keyed_rule_runs_after_a_move():
    people = survey().assign(county_fips=LOS_ANGELES_COUNTY)
    sim = pe.us.flat_file_microsimulation(people, year=YEAR, state="MN")
    assert set(sim.calculate("county", YEAR).values) == {"AITKIN_COUNTY_MN"}
    sim.calculate("mn_ccap_provider_rate", f"{YEAR}-01")


def test_a_file_keeps_its_own_states():
    fips = {1: 6, 2: MISSISSIPPI, 3: 36}
    people = survey().assign(state_fips=survey()["household_id"].map(fips))
    sim = pe.us.flat_file_microsimulation(people, year=YEAR, spm=NATIONAL_SPM)
    assert sim.calculate("state_code", YEAR).values.tolist() == ["CA", "MS", "NY"]


def test_keywords_reach_the_simulation():
    reform = {"gov.irs.credits.ctc.amount.base[0].amount": {"2024-01-01": 9000}}
    sim = pe.us.flat_file_microsimulation(
        survey(), year=YEAR, state="MS", spm=NATIONAL_SPM, reform=reform
    )
    reformed = sim.calculate("ctc", YEAR).sum()
    assert reformed > sim.baseline.calculate("ctc", YEAR).sum()


def test_a_dataset_is_refused():
    with pytest.raises(ValueError, match="people"):
        pe.us.flat_file_microsimulation(survey(), year=YEAR, dataset="other.h5")
