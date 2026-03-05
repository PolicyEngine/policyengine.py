"""Unit tests for Poverty.run() method.

Tests Poverty.run() in isolation using mock Simulation objects,
covering all filter combinations and edge cases.
"""

from unittest.mock import MagicMock

import pandas as pd
from microdf import MicroDataFrame

from policyengine.outputs.poverty import Poverty

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sim(poverty_values, weights, extra_columns=None):
    """Create a mock Simulation with person-level data."""
    sim = MagicMock()
    sim.id = "test-sim"

    data = {
        "person_id": list(range(len(poverty_values))),
        "person_weight": weights,
        "in_poverty": poverty_values,
    }
    if extra_columns:
        data.update(extra_columns)

    person_mdf = MicroDataFrame(
        pd.DataFrame(data),
        weights="person_weight",
    )

    sim.output_dataset.data.person = person_mdf

    def mock_get_variable(var_name):
        var_obj = MagicMock()
        var_obj.entity = "person"
        return var_obj

    sim.tax_benefit_model_version.get_variable.side_effect = mock_get_variable

    return sim


def _make_poverty(sim, poverty_variable, **kwargs):
    """Create a Poverty instance bypassing Pydantic validation.

    Uses model_construct() because the simulation field expects
    a real Simulation instance, but we use MagicMock in tests.
    """
    return Poverty.model_construct(
        simulation=sim,
        poverty_variable=poverty_variable,
        entity=kwargs.get("entity", "person"),
        filter_variable=kwargs.get("filter_variable"),
        filter_variable_eq=kwargs.get("filter_variable_eq"),
        filter_variable_leq=kwargs.get("filter_variable_leq"),
        filter_variable_geq=kwargs.get("filter_variable_geq"),
    )


# ---------------------------------------------------------------------------
# No filter
# ---------------------------------------------------------------------------


class TestPovertyRunNoFilter:
    """Tests for Poverty.run() with no demographic filter."""

    def test__given_mixed_poverty__then_calculates_correct_rate(self):
        """Given: 5 persons, 2 in poverty
        When: Running poverty with no filter
        Then: headcount=2, total=5, rate=0.4
        """
        sim = _make_sim(
            poverty_values=[True, True, False, False, False],
            weights=[1.0, 1.0, 1.0, 1.0, 1.0],
        )
        pov = _make_poverty(sim, "in_poverty")
        pov.run()

        assert pov.headcount == 2.0
        assert pov.total_population == 5.0
        assert pov.rate == 0.4

    def test__given_all_in_poverty__then_rate_is_one(self):
        """Given: All persons in poverty
        When: Running poverty
        Then: rate=1.0
        """
        sim = _make_sim(
            poverty_values=[True, True, True],
            weights=[1.0, 1.0, 1.0],
        )
        pov = _make_poverty(sim, "in_poverty")
        pov.run()

        assert pov.rate == 1.0

    def test__given_none_in_poverty__then_rate_is_zero(self):
        """Given: No persons in poverty
        When: Running poverty
        Then: headcount=0, rate=0.0
        """
        sim = _make_sim(
            poverty_values=[False, False, False],
            weights=[1.0, 1.0, 1.0],
        )
        pov = _make_poverty(sim, "in_poverty")
        pov.run()

        assert pov.headcount == 0.0
        assert pov.rate == 0.0


# ---------------------------------------------------------------------------
# Eq filter
# ---------------------------------------------------------------------------


class TestPovertyRunWithEqFilter:
    """Tests for Poverty.run() with filter_variable_eq."""

    def test__given_eq_filter__then_only_counts_matching_persons(self):
        """Given: 4 persons, 2 are children (1 in poverty), 2 are adults
        When: Filtering by is_child==True
        Then: headcount=1, total=2
        """
        sim = _make_sim(
            poverty_values=[True, False, True, False],
            weights=[1.0, 1.0, 1.0, 1.0],
            extra_columns={"is_child": [True, True, False, False]},
        )
        pov = _make_poverty(
            sim,
            "in_poverty",
            filter_variable="is_child",
            filter_variable_eq=True,
        )
        pov.run()

        assert pov.headcount == 1.0
        assert pov.total_population == 2.0
        assert pov.rate == 0.5


# ---------------------------------------------------------------------------
# Leq filter
# ---------------------------------------------------------------------------


class TestPovertyRunWithLeqFilter:
    """Tests for Poverty.run() with filter_variable_leq."""

    def test__given_leq_filter__then_only_counts_matching_persons(self):
        """Given: Ages [10, 15, 20, 65], poverty [T, F, T, F]
        When: Filtering by age <= 17 (children)
        Then: headcount=1, total=2
        """
        sim = _make_sim(
            poverty_values=[True, False, True, False],
            weights=[1.0, 1.0, 1.0, 1.0],
            extra_columns={"age": [10, 15, 20, 65]},
        )
        pov = _make_poverty(
            sim, "in_poverty", filter_variable="age", filter_variable_leq=17
        )
        pov.run()

        assert pov.headcount == 1.0
        assert pov.total_population == 2.0


# ---------------------------------------------------------------------------
# Geq filter
# ---------------------------------------------------------------------------


class TestPovertyRunWithGeqFilter:
    """Tests for Poverty.run() with filter_variable_geq."""

    def test__given_geq_filter__then_only_counts_matching_persons(self):
        """Given: Ages [10, 15, 65, 70], poverty [T, F, T, F]
        When: Filtering by age >= 65 (seniors)
        Then: headcount=1, total=2
        """
        sim = _make_sim(
            poverty_values=[True, False, True, False],
            weights=[1.0, 1.0, 1.0, 1.0],
            extra_columns={"age": [10, 15, 65, 70]},
        )
        pov = _make_poverty(
            sim, "in_poverty", filter_variable="age", filter_variable_geq=65
        )
        pov.run()

        assert pov.headcount == 1.0
        assert pov.total_population == 2.0


# ---------------------------------------------------------------------------
# Combined leq + geq filter
# ---------------------------------------------------------------------------


class TestPovertyRunWithCombinedFilter:
    """Tests for Poverty.run() with combined leq+geq filters."""

    def test__given_range_filter__then_only_counts_persons_in_range(self):
        """Given: Ages [10, 25, 50, 70], poverty [T, T, F, T]
        When: Filtering by 18 <= age <= 64 (adults)
        Then: headcount=1, total=2 (ages 25, 50)
        """
        sim = _make_sim(
            poverty_values=[True, True, False, True],
            weights=[1.0, 1.0, 1.0, 1.0],
            extra_columns={"age": [10, 25, 50, 70]},
        )
        pov = _make_poverty(
            sim,
            "in_poverty",
            filter_variable="age",
            filter_variable_geq=18,
            filter_variable_leq=64,
        )
        pov.run()

        assert pov.headcount == 1.0
        assert pov.total_population == 2.0
        assert pov.rate == 0.5


# ---------------------------------------------------------------------------
# Zero population
# ---------------------------------------------------------------------------


class TestPovertyRunZeroPopulation:
    """Tests for Poverty.run() with zero matching population."""

    def test__given_no_matching_persons__then_rate_is_zero(self):
        """Given: Filter matches no persons
        When: Running poverty
        Then: headcount=0, total=0, rate=0.0
        """
        sim = _make_sim(
            poverty_values=[True, True],
            weights=[1.0, 1.0],
            extra_columns={"age": [10, 15]},
        )
        pov = _make_poverty(
            sim,
            "in_poverty",
            filter_variable="age",
            filter_variable_geq=65,
        )
        pov.run()

        assert pov.headcount == 0.0
        assert pov.total_population == 0.0
        assert pov.rate == 0.0
