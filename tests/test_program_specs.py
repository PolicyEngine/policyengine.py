"""Tests for the structured program-spec mechanism (issue #326)."""

import pytest

from policyengine.core import TaxBenefitModelVersion, Variable
from policyengine.tax_benefit_models.us.programs import (
    US_PROGRAM_SPECS,
    ProgramSpec,
    ResolvedProgram,
    resolve_program_specs,
)


def _build_model(variables: dict[str, str]) -> TaxBenefitModelVersion:
    """Build a stub model with the given ``variable_name -> entity`` map."""
    model = TaxBenefitModelVersion(id="stub")
    for name, entity in variables.items():
        model.add_variable(
            Variable(
                id=f"stub:{name}",
                name=name,
                entity=entity,
                tax_benefit_model_version=model,
            )
        )
    return model


def test_resolve_derives_entity_from_metadata():
    model = _build_model(
        {
            "income_tax": "tax_unit",
            "snap": "spm_unit",
        }
    )
    specs = [
        ProgramSpec(name="income_tax", is_tax=True),
        ProgramSpec(name="snap", is_tax=False),
    ]

    resolved = resolve_program_specs(specs, model)

    assert resolved == [
        ResolvedProgram(name="income_tax", entity="tax_unit", is_tax=True),
        ResolvedProgram(name="snap", entity="spm_unit", is_tax=False),
    ]


def test_resolve_collects_all_unknowns_in_one_error():
    model = _build_model({"income_tax": "tax_unit"})
    specs = [
        ProgramSpec(name="income_tax", is_tax=True),
        ProgramSpec(name="payroll_tax", is_tax=True),  # unknown
        ProgramSpec(name="medicare", is_tax=False),  # unknown
    ]

    with pytest.raises(ValueError, match="2 unknown variables") as exc:
        resolve_program_specs(specs, model)

    msg = str(exc.value)
    assert "'payroll_tax'" in msg
    assert "'medicare'" in msg


def test_resolve_includes_fuzzy_match_suggestions():
    model = _build_model(
        {
            "employee_payroll_tax": "tax_unit",
            "medicare_cost": "person",
        }
    )
    specs = [
        ProgramSpec(name="payroll_tax", is_tax=True),
        ProgramSpec(name="medicare", is_tax=False),
    ]

    with pytest.raises(ValueError) as exc:
        resolve_program_specs(specs, model)

    msg = str(exc.value)
    assert "employee_payroll_tax" in msg
    assert "medicare_cost" in msg


def test_us_program_specs_has_no_duplicates():
    names = [s.name for s in US_PROGRAM_SPECS]
    assert len(names) == len(set(names)), (
        "US_PROGRAM_SPECS must not contain duplicate variable names"
    )
