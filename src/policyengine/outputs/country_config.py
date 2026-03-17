"""Country configuration strategy — holds all country-specific parameters."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CountryConfig:
    """All country-specific parameters needed by compute functions.

    Individual compute functions read the fields they need from this
    config rather than accepting a ``country_id`` string and branching.
    """

    country_id: str
    income_variable: str
    programs: dict[str, dict] = field(default_factory=dict)
    budget_variables: dict[str, str] = field(default_factory=dict)
    poverty_variables: dict[str, str] = field(default_factory=dict)
    poverty_entity: str = "person"
    poverty_breakdowns: tuple[str, ...] = ()
    inequality_income_variable: str | None = None
    inequality_entity: str = "household"


US_CONFIG = CountryConfig(
    country_id="us",
    income_variable="household_net_income",
    programs={
        "income_tax": {"entity": "tax_unit", "is_tax": True},
        "employee_payroll_tax": {"entity": "person", "is_tax": True},
        "snap": {"entity": "spm_unit", "is_tax": False},
        "tanf": {"entity": "spm_unit", "is_tax": False},
        "ssi": {"entity": "spm_unit", "is_tax": False},
        "social_security": {"entity": "person", "is_tax": False},
    },
    budget_variables={
        "household_tax": "household",
        "household_benefits": "household",
        "household_net_income": "household",
        "household_state_income_tax": "tax_unit",
    },
    poverty_variables={
        "spm": "spm_unit_is_in_spm_poverty",
        "spm_deep": "spm_unit_is_in_deep_spm_poverty",
    },
    poverty_entity="person",
    poverty_breakdowns=("age", "gender", "race"),
    inequality_income_variable="household_net_income",
    inequality_entity="household",
)

UK_CONFIG = CountryConfig(
    country_id="uk",
    income_variable="equiv_hbai_household_net_income",
    programs={
        "income_tax": {"entity": "person", "is_tax": True},
        "national_insurance": {"entity": "person", "is_tax": True},
        "vat": {"entity": "household", "is_tax": True},
        "council_tax": {"entity": "household", "is_tax": True},
        "universal_credit": {"entity": "person", "is_tax": False},
        "child_benefit": {"entity": "person", "is_tax": False},
        "pension_credit": {"entity": "person", "is_tax": False},
        "income_support": {"entity": "person", "is_tax": False},
        "working_tax_credit": {"entity": "person", "is_tax": False},
        "child_tax_credit": {"entity": "person", "is_tax": False},
    },
    budget_variables={
        "household_tax": "household",
        "household_benefits": "household",
        "household_net_income": "household",
    },
    poverty_variables={
        "absolute_bhc": "in_poverty_bhc",
        "absolute_ahc": "in_poverty_ahc",
        "relative_bhc": "in_relative_poverty_bhc",
        "relative_ahc": "in_relative_poverty_ahc",
    },
    poverty_entity="person",
    poverty_breakdowns=("age", "gender"),
    inequality_income_variable="equiv_hbai_household_net_income",
    inequality_entity="household",
)
