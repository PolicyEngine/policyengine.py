"""Tests for policyengine.utils.parameter_labels module."""

from unittest.mock import MagicMock

from policyengine.utils.parameter_labels import (
    _find_breakdown_parent,
    _generate_bracket_label,
    _generate_breakdown_label,
    build_scale_lookup,
    generate_label_for_parameter,
)
from tests.fixtures.parameter_labels_fixtures import (
    PARAM_WITH_EXPLICIT_LABEL,
    PARAM_WITHOUT_LABEL_NO_PARENT,
    PARENT_WITH_BREAKDOWN_AND_LABEL,
    PARENT_WITH_BREAKDOWN_NO_LABEL,
    PARENT_WITHOUT_BREAKDOWN,
    SCALE_WITH_LABEL_MARGINAL,
    SCALE_WITH_LABEL_SINGLE_AMOUNT,
    SCALE_WITHOUT_LABEL,
    VARIABLE_WITH_FILING_STATUS_ENUM,
    VARIABLE_WITH_STATE_CODE_ENUM,
    create_mock_parameter,
    create_mock_parent_node,
    create_mock_scale,
    create_mock_system,
)


class TestGenerateLabelForParameter:
    """Tests for the generate_label_for_parameter function."""

    def test__given_parameter_has_explicit_label__then_returns_explicit_label(
        self,
    ):
        # Given
        param = PARAM_WITH_EXPLICIT_LABEL
        system = create_mock_system()
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result == "Tax rate"

    def test__given_parameter_without_label_and_no_parent__then_returns_none(
        self,
    ):
        # Given
        param = PARAM_WITHOUT_LABEL_NO_PARENT
        system = create_mock_system()
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result is None

    def test__given_bracket_parameter_with_scale_label__then_generates_bracket_label(
        self,
    ):
        # Given
        param = create_mock_parameter(name="gov.tax.rates[0].rate")
        system = create_mock_system()
        scale_lookup = {"gov.tax.rates": SCALE_WITH_LABEL_MARGINAL}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result == "Income tax rate (bracket 1 rate)"

    def test__given_breakdown_parameter_with_parent_label__then_generates_breakdown_label(
        self,
    ):
        # Given
        parent = PARENT_WITH_BREAKDOWN_AND_LABEL
        param = create_mock_parameter(
            name="gov.exemptions.personal.SINGLE",
            parent=parent,
        )
        system = create_mock_system(
            variables={"filing_status": VARIABLE_WITH_FILING_STATUS_ENUM}
        )
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result == "Personal exemption amount (Single)"

    def test__given_parameter_with_parent_but_no_breakdown__then_returns_none(
        self,
    ):
        # Given
        parent = PARENT_WITHOUT_BREAKDOWN
        param = create_mock_parameter(
            name="gov.exemptions.personal.value",
            parent=parent,
        )
        system = create_mock_system()
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result is None


class TestGenerateBreakdownLabel:
    """Tests for the _generate_breakdown_label function."""

    def test__given_parent_has_label_and_enum_match__then_returns_label_with_enum_value(
        self,
    ):
        # Given
        parent = PARENT_WITH_BREAKDOWN_AND_LABEL
        param = create_mock_parameter(
            name="gov.exemptions.personal.JOINT",
            parent=parent,
        )
        system = create_mock_system(
            variables={"filing_status": VARIABLE_WITH_FILING_STATUS_ENUM}
        )

        # When
        result = _generate_breakdown_label(param, system)

        # Then
        assert result == "Personal exemption amount (Joint)"

    def test__given_parent_has_no_label__then_returns_none(self):
        # Given
        parent = PARENT_WITH_BREAKDOWN_NO_LABEL
        param = create_mock_parameter(
            name="gov.exemptions.personal.SINGLE",
            parent=parent,
        )
        system = create_mock_system(
            variables={"filing_status": VARIABLE_WITH_FILING_STATUS_ENUM}
        )

        # When
        result = _generate_breakdown_label(param, system)

        # Then
        assert result is None

    def test__given_enum_key_not_found__then_returns_label_with_raw_key(self):
        # Given
        parent = PARENT_WITH_BREAKDOWN_AND_LABEL
        param = create_mock_parameter(
            name="gov.exemptions.personal.UNKNOWN_STATUS",
            parent=parent,
        )
        system = create_mock_system(
            variables={"filing_status": VARIABLE_WITH_FILING_STATUS_ENUM}
        )

        # When
        result = _generate_breakdown_label(param, system)

        # Then
        assert result == "Personal exemption amount (UNKNOWN_STATUS)"

    def test__given_variable_not_in_system__then_returns_label_with_raw_key(
        self,
    ):
        # Given
        parent = PARENT_WITH_BREAKDOWN_AND_LABEL
        param = create_mock_parameter(
            name="gov.exemptions.personal.SINGLE",
            parent=parent,
        )
        system = create_mock_system(variables={})

        # When
        result = _generate_breakdown_label(param, system)

        # Then
        assert result == "Personal exemption amount (SINGLE)"

    def test__given_state_code_enum__then_returns_label_with_state_code(self):
        # Given
        parent = create_mock_parent_node(
            name="gov.enrollment.by_state",
            label="Enrollment by state",
            breakdown=["state_code"],
        )
        param = create_mock_parameter(
            name="gov.enrollment.by_state.CA",
            parent=parent,
        )
        system = create_mock_system(
            variables={"state_code": VARIABLE_WITH_STATE_CODE_ENUM}
        )

        # When
        result = _generate_breakdown_label(param, system)

        # Then
        assert result == "Enrollment by state (CA)"

    def test__given_multiple_breakdown_vars__then_uses_first_match(self):
        # Given
        parent = create_mock_parent_node(
            name="gov.rates.by_status_and_state",
            label="Rate by status and state",
            breakdown=["filing_status", "state_code"],
        )
        param = create_mock_parameter(
            name="gov.rates.by_status_and_state.SINGLE",
            parent=parent,
        )
        system = create_mock_system(
            variables={
                "filing_status": VARIABLE_WITH_FILING_STATUS_ENUM,
                "state_code": VARIABLE_WITH_STATE_CODE_ENUM,
            }
        )

        # When
        result = _generate_breakdown_label(param, system)

        # Then
        assert result == "Rate by status and state (Single)"


class TestGenerateBracketLabel:
    """Tests for the _generate_bracket_label function."""

    def test__given_valid_bracket_param_with_scale_label__then_returns_bracket_label(
        self,
    ):
        # Given
        param_name = "gov.tax.rates[0].rate"
        scale_lookup = {"gov.tax.rates": SCALE_WITH_LABEL_MARGINAL}

        # When
        result = _generate_bracket_label(param_name, scale_lookup)

        # Then
        assert result == "Income tax rate (bracket 1 rate)"

    def test__given_bracket_index_greater_than_zero__then_uses_one_indexed_bracket_number(
        self,
    ):
        # Given
        param_name = "gov.tax.rates[2].threshold"
        scale_lookup = {"gov.tax.rates": SCALE_WITH_LABEL_MARGINAL}

        # When
        result = _generate_bracket_label(param_name, scale_lookup)

        # Then
        assert result == "Income tax rate (bracket 3 threshold)"

    def test__given_single_amount_scale_type__then_uses_tier_instead_of_bracket(
        self,
    ):
        # Given
        param_name = "gov.tax.amounts[0].amount"
        scale_lookup = {"gov.tax.amounts": SCALE_WITH_LABEL_SINGLE_AMOUNT}

        # When
        result = _generate_bracket_label(param_name, scale_lookup)

        # Then
        assert result == "Tax amount (tier 1 amount)"

    def test__given_scale_without_label__then_returns_none(self):
        # Given
        param_name = "gov.tax.rates[0].rate"
        scale_lookup = {"gov.tax.rates": SCALE_WITHOUT_LABEL}

        # When
        result = _generate_bracket_label(param_name, scale_lookup)

        # Then
        assert result is None

    def test__given_scale_not_in_lookup__then_returns_none(self):
        # Given
        param_name = "gov.tax.rates[0].rate"
        scale_lookup = {}

        # When
        result = _generate_bracket_label(param_name, scale_lookup)

        # Then
        assert result is None

    def test__given_invalid_bracket_format__then_returns_none(self):
        # Given
        param_name = "gov.tax.rates.rate"  # No bracket notation
        scale_lookup = {"gov.tax.rates": SCALE_WITH_LABEL_MARGINAL}

        # When
        result = _generate_bracket_label(param_name, scale_lookup)

        # Then
        assert result is None

    def test__given_threshold_field__then_includes_threshold_in_label(self):
        # Given
        param_name = "gov.tax.rates[1].threshold"
        scale_lookup = {"gov.tax.rates": SCALE_WITH_LABEL_MARGINAL}

        # When
        result = _generate_bracket_label(param_name, scale_lookup)

        # Then
        assert result == "Income tax rate (bracket 2 threshold)"


class TestBuildScaleLookup:
    """Tests for the build_scale_lookup function."""

    def test__given_system_with_scales__then_returns_dict_of_scales_by_name(
        self,
    ):
        # Given
        from policyengine_core.parameters import ParameterScale

        scale1 = MagicMock(spec=ParameterScale)
        scale1.name = "gov.tax.rates"
        scale2 = MagicMock(spec=ParameterScale)
        scale2.name = "gov.benefit.amounts"

        system = MagicMock()
        system.parameters.get_descendants.return_value = [scale1, scale2]

        # When
        result = build_scale_lookup(system)

        # Then
        assert "gov.tax.rates" in result
        assert "gov.benefit.amounts" in result
        assert result["gov.tax.rates"] == scale1
        assert result["gov.benefit.amounts"] == scale2

    def test__given_system_with_no_scales__then_returns_empty_dict(self):
        # Given
        from policyengine_core.parameters import Parameter as CoreParameter

        # Create a mock that is NOT a ParameterScale
        param = MagicMock(spec=CoreParameter)
        param.name = "gov.tax.rate"

        system = MagicMock()
        system.parameters.get_descendants.return_value = [param]

        # When
        result = build_scale_lookup(system)

        # Then
        assert result == {}


class TestIntegrationWithRealEnums:
    """Integration tests using real-like enum scenarios."""

    def test__given_head_of_household_status__then_generates_readable_label(
        self,
    ):
        # Given
        parent = create_mock_parent_node(
            name="gov.pr.exemptions.personal",
            label="Puerto Rico personal exemption",
            breakdown=["filing_status"],
        )
        param = create_mock_parameter(
            name="gov.pr.exemptions.personal.HEAD_OF_HOUSEHOLD",
            parent=parent,
        )
        system = create_mock_system(
            variables={"filing_status": VARIABLE_WITH_FILING_STATUS_ENUM}
        )
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result == "Puerto Rico personal exemption (Head of household)"

    def test__given_complex_bracket_path__then_extracts_correct_scale_name(
        self,
    ):
        # Given
        scale = create_mock_scale(
            name="gov.territories.pr.tax.income.tax_rate.amount",
            label="Puerto Rico tax rate",
            scale_type="marginal_rate",
        )
        param = create_mock_parameter(
            name="gov.territories.pr.tax.income.tax_rate.amount[0].rate"
        )
        system = create_mock_system()
        scale_lookup = {"gov.territories.pr.tax.income.tax_rate.amount": scale}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result == "Puerto Rico tax rate (bracket 1 rate)"


class TestFindBreakdownParent:
    """Tests for the _find_breakdown_parent function."""

    def test__given_direct_child__then_returns_parent(self):
        # Given
        parent = create_mock_parent_node(
            name="gov.snap.max_allotment",
            label="SNAP max allotment",
            breakdown=["snap_region", "range(1, 9)"],
        )
        param = create_mock_parameter(
            name="gov.snap.max_allotment.CONTIGUOUS_US",
            parent=parent,
        )

        # When
        result = _find_breakdown_parent(param)

        # Then
        assert result == parent

    def test__given_nested_child__then_returns_breakdown_ancestor(self):
        # Given
        breakdown_parent = create_mock_parent_node(
            name="gov.snap.max_allotment",
            label="SNAP max allotment",
            breakdown=["snap_region", "range(1, 9)"],
        )
        intermediate = create_mock_parent_node(
            name="gov.snap.max_allotment.CONTIGUOUS_US",
            parent=breakdown_parent,
        )
        param = create_mock_parameter(
            name="gov.snap.max_allotment.CONTIGUOUS_US.1",
            parent=intermediate,
        )

        # When
        result = _find_breakdown_parent(param)

        # Then
        assert result == breakdown_parent

    def test__given_no_breakdown_in_ancestry__then_returns_none(self):
        # Given
        parent = create_mock_parent_node(
            name="gov.tax.rate",
            label="Tax rate",
        )
        param = create_mock_parameter(
            name="gov.tax.rate.value",
            parent=parent,
        )

        # When
        result = _find_breakdown_parent(param)

        # Then
        assert result is None


class TestNestedBreakdownLabels:
    """Tests for nested breakdown label generation."""

    def test__given_nested_breakdown_with_enum_and_range__then_generates_full_label(
        self,
    ):
        # Given
        breakdown_parent = create_mock_parent_node(
            name="gov.snap.max_allotment",
            label="SNAP max allotment",
            breakdown=["snap_region", "range(1, 9)"],
            breakdown_labels=["SNAP region", "Household size"],
        )
        intermediate = create_mock_parent_node(
            name="gov.snap.max_allotment.CONTIGUOUS_US",
            parent=breakdown_parent,
        )
        param = create_mock_parameter(
            name="gov.snap.max_allotment.CONTIGUOUS_US.1",
            parent=intermediate,
        )
        system = create_mock_system()
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        # Without snap_region enum in system, uses breakdown_label for first dimension too
        assert result == "SNAP max allotment (SNAP region CONTIGUOUS_US, Household size 1)"

    def test__given_breakdown_labels_for_range__then_includes_semantic_label(
        self,
    ):
        # Given
        parent = create_mock_parent_node(
            name="gov.benefits.amount",
            label="Benefit amount",
            breakdown=["range(1, 5)"],
            breakdown_labels=["Number of dependants"],
        )
        param = create_mock_parameter(
            name="gov.benefits.amount.3",
            parent=parent,
        )
        system = create_mock_system()
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result == "Benefit amount (Number of dependants 3)"

    def test__given_enum_with_breakdown_label__then_prefers_enum_value(self):
        # Given
        parent = create_mock_parent_node(
            name="gov.exemptions.personal",
            label="Personal exemption",
            breakdown=["filing_status"],
            breakdown_labels=["Filing status"],
        )
        param = create_mock_parameter(
            name="gov.exemptions.personal.SINGLE",
            parent=parent,
        )
        system = create_mock_system(
            variables={"filing_status": VARIABLE_WITH_FILING_STATUS_ENUM}
        )
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        # Enum value "Single" is used, not "Filing status SINGLE"
        assert result == "Personal exemption (Single)"

    def test__given_three_level_nesting__then_generates_all_dimensions(self):
        # Given
        breakdown_parent = create_mock_parent_node(
            name="gov.irs.sales_tax",
            label="State sales tax",
            breakdown=["state_code", "range(1, 7)", "range(1, 20)"],
            breakdown_labels=["State", "Income bracket", "Exemption count"],
        )
        level1 = create_mock_parent_node(
            name="gov.irs.sales_tax.CA",
            parent=breakdown_parent,
        )
        level2 = create_mock_parent_node(
            name="gov.irs.sales_tax.CA.3",
            parent=level1,
        )
        param = create_mock_parameter(
            name="gov.irs.sales_tax.CA.3.5",
            parent=level2,
        )
        system = create_mock_system(
            variables={"state_code": VARIABLE_WITH_STATE_CODE_ENUM}
        )
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        assert result == "State sales tax (CA, Income bracket 3, Exemption count 5)"

    def test__given_missing_breakdown_labels__then_uses_raw_values(self):
        # Given
        breakdown_parent = create_mock_parent_node(
            name="gov.snap.max_allotment",
            label="SNAP max allotment",
            breakdown=["snap_region", "range(1, 9)"],
            # No breakdown_labels provided
        )
        intermediate = create_mock_parent_node(
            name="gov.snap.max_allotment.CONTIGUOUS_US",
            parent=breakdown_parent,
        )
        param = create_mock_parameter(
            name="gov.snap.max_allotment.CONTIGUOUS_US.1",
            parent=intermediate,
        )
        system = create_mock_system()
        scale_lookup = {}

        # When
        result = generate_label_for_parameter(param, system, scale_lookup)

        # Then
        # Falls back to raw values when no breakdown_labels
        assert result == "SNAP max allotment (CONTIGUOUS_US, 1)"
