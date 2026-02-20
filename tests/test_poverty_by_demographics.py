"""Tests for poverty-by-demographics convenience functions.

Tests calculate_*_poverty_by_age, calculate_*_poverty_by_gender, and
calculate_us_poverty_by_race. These are thin wrappers that iterate over
demographic groups and delegate to the base poverty rate functions, so
we mock the base functions and verify delegation logic.
"""

from unittest.mock import patch

from policyengine.outputs.poverty import (
    AGE_GROUPS,
    RACE_GROUPS,
    calculate_uk_poverty_by_age,
    calculate_uk_poverty_by_gender,
    calculate_us_poverty_by_age,
    calculate_us_poverty_by_gender,
    calculate_us_poverty_by_race,
)
from tests.fixtures.poverty_by_demographics_fixtures import (
    AGE_GROUP_NAMES,
    EXPECTED_UK_BY_AGE_COUNT,
    EXPECTED_UK_BY_GENDER_COUNT,
    EXPECTED_US_BY_AGE_COUNT,
    EXPECTED_US_BY_GENDER_COUNT,
    EXPECTED_US_BY_RACE_COUNT,
    GENDER_GROUP_NAMES,
    RACE_GROUP_NAMES,
    make_mock_simulation,
    make_uk_mock_collection,
    make_us_mock_collection,
)

# ---------------------------------------------------------------------------
# UK poverty by age
# ---------------------------------------------------------------------------


class TestCalculateUkPovertyByAge:
    """Tests for calculate_uk_poverty_by_age."""

    @patch("policyengine.outputs.poverty.calculate_uk_poverty_rates")
    def test__given_simulation__then_returns_12_records(self, mock_rates):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_uk_mock_collection(sim)

        # When
        result = calculate_uk_poverty_by_age(sim)

        # Then
        assert len(result.outputs) == EXPECTED_UK_BY_AGE_COUNT

    @patch("policyengine.outputs.poverty.calculate_uk_poverty_rates")
    def test__given_simulation__then_calls_base_once_per_age_group(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_uk_mock_collection(sim)

        # When
        calculate_uk_poverty_by_age(sim)

        # Then
        assert mock_rates.call_count == len(AGE_GROUPS)

    @patch("policyengine.outputs.poverty.calculate_uk_poverty_rates")
    def test__given_simulation__then_filter_variable_set_to_group_name(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.side_effect = lambda *a, **kw: make_uk_mock_collection(sim)

        # When
        result = calculate_uk_poverty_by_age(sim)

        # Then
        filter_vars = {o.filter_variable for o in result.outputs}
        assert filter_vars == set(AGE_GROUP_NAMES)

    @patch("policyengine.outputs.poverty.calculate_uk_poverty_rates")
    def test__given_simulation__then_passes_correct_filter_kwargs(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_uk_mock_collection(sim)

        # When
        calculate_uk_poverty_by_age(sim)

        # Then — verify that the child group passes age <= 17
        calls = mock_rates.call_args_list
        child_call = calls[0]  # "child" is first in AGE_GROUPS
        assert child_call.kwargs["filter_variable"] == "age"
        assert child_call.kwargs["filter_variable_leq"] == 17


# ---------------------------------------------------------------------------
# US poverty by age
# ---------------------------------------------------------------------------


class TestCalculateUsPovertyByAge:
    """Tests for calculate_us_poverty_by_age."""

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_returns_6_records(self, mock_rates):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_us_mock_collection(sim)

        # When
        result = calculate_us_poverty_by_age(sim)

        # Then
        assert len(result.outputs) == EXPECTED_US_BY_AGE_COUNT

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_filter_variable_set_to_group_name(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.side_effect = lambda *a, **kw: make_us_mock_collection(sim)

        # When
        result = calculate_us_poverty_by_age(sim)

        # Then
        filter_vars = {o.filter_variable for o in result.outputs}
        assert filter_vars == set(AGE_GROUP_NAMES)


# ---------------------------------------------------------------------------
# UK poverty by gender
# ---------------------------------------------------------------------------


class TestCalculateUkPovertyByGender:
    """Tests for calculate_uk_poverty_by_gender."""

    @patch("policyengine.outputs.poverty.calculate_uk_poverty_rates")
    def test__given_simulation__then_returns_8_records(self, mock_rates):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_uk_mock_collection(sim)

        # When
        result = calculate_uk_poverty_by_gender(sim)

        # Then
        assert len(result.outputs) == EXPECTED_UK_BY_GENDER_COUNT

    @patch("policyengine.outputs.poverty.calculate_uk_poverty_rates")
    def test__given_simulation__then_filter_variable_set_to_gender_names(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.side_effect = lambda *a, **kw: make_uk_mock_collection(sim)

        # When
        result = calculate_uk_poverty_by_gender(sim)

        # Then
        filter_vars = {o.filter_variable for o in result.outputs}
        assert filter_vars == set(GENDER_GROUP_NAMES)

    @patch("policyengine.outputs.poverty.calculate_uk_poverty_rates")
    def test__given_simulation__then_passes_is_male_filter(self, mock_rates):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_uk_mock_collection(sim)

        # When
        calculate_uk_poverty_by_gender(sim)

        # Then — first call is "male" group
        male_call = mock_rates.call_args_list[0]
        assert male_call.kwargs["filter_variable"] == "is_male"
        assert male_call.kwargs["filter_variable_eq"] is True


# ---------------------------------------------------------------------------
# US poverty by gender
# ---------------------------------------------------------------------------


class TestCalculateUsPovertyByGender:
    """Tests for calculate_us_poverty_by_gender."""

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_returns_4_records(self, mock_rates):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_us_mock_collection(sim)

        # When
        result = calculate_us_poverty_by_gender(sim)

        # Then
        assert len(result.outputs) == EXPECTED_US_BY_GENDER_COUNT

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_filter_variable_set_to_gender_names(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.side_effect = lambda *a, **kw: make_us_mock_collection(sim)

        # When
        result = calculate_us_poverty_by_gender(sim)

        # Then
        filter_vars = {o.filter_variable for o in result.outputs}
        assert filter_vars == set(GENDER_GROUP_NAMES)


# ---------------------------------------------------------------------------
# US poverty by race
# ---------------------------------------------------------------------------


class TestCalculateUsPovertyByRace:
    """Tests for calculate_us_poverty_by_race."""

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_returns_8_records(self, mock_rates):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_us_mock_collection(sim)

        # When
        result = calculate_us_poverty_by_race(sim)

        # Then
        assert len(result.outputs) == EXPECTED_US_BY_RACE_COUNT

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_calls_base_once_per_race_group(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_us_mock_collection(sim)

        # When
        calculate_us_poverty_by_race(sim)

        # Then
        assert mock_rates.call_count == len(RACE_GROUPS)

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_filter_variable_set_to_race_names(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.side_effect = lambda *a, **kw: make_us_mock_collection(sim)

        # When
        result = calculate_us_poverty_by_race(sim)

        # Then
        filter_vars = {o.filter_variable for o in result.outputs}
        assert filter_vars == set(RACE_GROUP_NAMES)

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_passes_race_filter_with_correct_eq_value(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_us_mock_collection(sim)

        # When
        calculate_us_poverty_by_race(sim)

        # Then — first call is "white" group
        white_call = mock_rates.call_args_list[0]
        assert white_call.kwargs["filter_variable"] == "race"
        assert white_call.kwargs["filter_variable_eq"] == "WHITE"

    @patch("policyengine.outputs.poverty.calculate_us_poverty_rates")
    def test__given_simulation__then_dataframe_has_correct_row_count(
        self, mock_rates
    ):
        # Given
        sim = make_mock_simulation()
        mock_rates.return_value = make_us_mock_collection(sim)

        # When
        result = calculate_us_poverty_by_race(sim)

        # Then
        assert len(result.dataframe) == EXPECTED_US_BY_RACE_COUNT
