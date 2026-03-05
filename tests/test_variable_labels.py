"""Tests for variable label extraction and storage."""

from policyengine.core.tax_benefit_model import TaxBenefitModel
from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion
from policyengine.core.variable import Variable
from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.us import us_latest
from tests.fixtures.variable_label_fixtures import (
    VAR_WITH_EMPTY_LABEL,
    VAR_WITH_LABEL,
    VAR_WITHOUT_LABEL,
    create_mock_openfisca_variable,
)


# ---------------------------------------------------------------------------
# Unit tests for Variable model
# ---------------------------------------------------------------------------


class TestVariableLabelField:
    """Tests for the Variable Pydantic model label field."""

    def _make_version(self) -> TaxBenefitModelVersion:
        model = TaxBenefitModel(id="test-model")
        return TaxBenefitModelVersion(
            model=model,
            version="1.0.0",
        )

    def test_label_defaults_to_none(self):
        """Variable.label should default to None when not provided."""
        version = self._make_version()
        var = Variable(
            id="test-var",
            name="income_tax",
            tax_benefit_model_version=version,
            entity="person",
        )
        assert var.label is None

    def test_label_stores_string(self):
        """Variable.label should accept and store a string value."""
        version = self._make_version()
        var = Variable(
            id="test-var",
            name="income_tax",
            label="Income tax",
            tax_benefit_model_version=version,
            entity="person",
        )
        assert var.label == "Income tax"

    def test_label_accepts_empty_string(self):
        """Variable.label should accept an empty string."""
        version = self._make_version()
        var = Variable(
            id="test-var",
            name="income_tax",
            label="",
            tax_benefit_model_version=version,
            entity="person",
        )
        assert var.label == ""


# ---------------------------------------------------------------------------
# Unit tests for getattr extraction pattern
# ---------------------------------------------------------------------------


class TestLabelExtraction:
    """Tests for the getattr(var_obj, 'label', None) extraction pattern."""

    def test_extracts_label_when_present(self):
        """getattr should return the label when the attribute exists."""
        assert getattr(VAR_WITH_LABEL, "label", None) == "Employment income"

    def test_returns_none_when_label_missing(self):
        """getattr should return None when the label attribute is absent."""
        assert getattr(VAR_WITHOUT_LABEL, "label", None) is None

    def test_returns_empty_string_when_label_empty(self):
        """getattr should return empty string when label is set to ''."""
        assert getattr(VAR_WITH_EMPTY_LABEL, "label", None) == ""

    def test_custom_label_value(self):
        """getattr should return any custom label string."""
        var = create_mock_openfisca_variable(
            name="council_tax",
            label="Council tax",
        )
        assert getattr(var, "label", None) == "Council tax"


# ---------------------------------------------------------------------------
# Integration tests against real US model
# ---------------------------------------------------------------------------


class TestUSVariableLabels:
    """Tests that US model variables carry labels from OpenFisca."""

    def test_employment_income_has_label(self):
        """employment_income should have a non-empty label."""
        var = next(
            (v for v in us_latest.variables if v.name == "employment_income"),
            None,
        )
        assert var is not None, "employment_income not found in US model"
        assert var.label is not None, "employment_income should have a label"
        assert len(var.label) > 0, "employment_income label should be non-empty"

    def test_income_tax_has_label(self):
        """income_tax should have a non-empty label."""
        var = next(
            (v for v in us_latest.variables if v.name == "income_tax"),
            None,
        )
        assert var is not None, "income_tax not found in US model"
        assert var.label is not None, "income_tax should have a label"
        assert len(var.label) > 0

    def test_majority_of_variables_have_labels(self):
        """Most US variables should have non-empty labels."""
        total = len(us_latest.variables)
        with_label = sum(
            1
            for v in us_latest.variables
            if v.label is not None and len(v.label) > 0
        )
        ratio = with_label / total
        assert ratio > 0.5, (
            f"Expected >50% of US variables to have labels, "
            f"got {with_label}/{total} ({ratio:.0%})"
        )

    def test_label_is_string_type(self):
        """Variable labels should be strings (not other types)."""
        for v in us_latest.variables[:100]:
            if v.label is not None:
                assert isinstance(v.label, str), (
                    f"Variable {v.name} label is {type(v.label)}, expected str"
                )


# ---------------------------------------------------------------------------
# Integration tests against real UK model
# ---------------------------------------------------------------------------


class TestUKVariableLabels:
    """Tests that UK model variables carry labels from OpenFisca."""

    def test_employment_income_has_label(self):
        """employment_income should have a non-empty label."""
        var = next(
            (v for v in uk_latest.variables if v.name == "employment_income"),
            None,
        )
        assert var is not None, "employment_income not found in UK model"
        assert var.label is not None, "employment_income should have a label"
        assert len(var.label) > 0

    def test_income_tax_has_label(self):
        """income_tax should have a non-empty label."""
        var = next(
            (v for v in uk_latest.variables if v.name == "income_tax"),
            None,
        )
        assert var is not None, "income_tax not found in UK model"
        assert var.label is not None, "income_tax should have a label"
        assert len(var.label) > 0

    def test_majority_of_variables_have_labels(self):
        """Most UK variables should have non-empty labels."""
        total = len(uk_latest.variables)
        with_label = sum(
            1
            for v in uk_latest.variables
            if v.label is not None and len(v.label) > 0
        )
        ratio = with_label / total
        assert ratio > 0.5, (
            f"Expected >50% of UK variables to have labels, "
            f"got {with_label}/{total} ({ratio:.0%})"
        )

    def test_label_is_string_type(self):
        """Variable labels should be strings (not other types)."""
        for v in uk_latest.variables[:100]:
            if v.label is not None:
                assert isinstance(v.label, str), (
                    f"Variable {v.name} label is {type(v.label)}, expected str"
                )
