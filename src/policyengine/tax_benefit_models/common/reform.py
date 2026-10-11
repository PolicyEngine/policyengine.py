"""Compile a simple reform dict into country-model inputs or parameter values.

Accepted shapes for the agent-facing API:

.. code-block:: python

    # Scalar — applied from Jan 1 of ``year`` (the simulation year).
    reform = {"gov.irs.deductions.salt.cap": 0}

    # With explicit effective date(s).
    reform = {"gov.irs.deductions.salt.cap": {"2026-01-01": 0}}

    # With an inclusive start and end date.
    reform = {
        "gov.hmrc.income_tax.rates.uk[0].rate": {
            "2027-04-06.2028-04-05": 0.21,
        },
    }

    # Multiple parameters.
    reform = {
        "gov.irs.deductions.salt.cap": 0,
        "gov.irs.credits.ctc.amount.base[0].amount": 2500,
    }

**Indexed parameters.** Many PolicyEngine parameters are *breakdown*
entries keyed by a bracket index (age group, filing status, etc.).
Their paths end with ``[N].amount`` / ``[N].threshold``. For example
the CTC base amount in 2026 is
``gov.irs.credits.ctc.amount.base[0].amount`` (not ``...base``);
the top-bracket SS wage base is ``gov.ssa.payroll.cap``. If a reform
dict uses the bracket-head path instead of ``[0].amount`` the
``ValueError`` will list the close match.

The parameter-value compiler accepts ``YYYY-MM-DD`` as an effective date
with no end date, or ``YYYY-MM-DD.YYYY-MM-DD`` as an inclusive interval.
Other keys, including bare years, are rejected: policyengine-uk interprets
a bare year as one fiscal year, while policyengine-core interprets it as
an effective year continuing onward. Use ``2027-04-06.2028-04-05`` for one
UK fiscal year, or ``2027-01-01`` for an effective date.

The low-level :func:`compile_reform` returns ``{param_path: {period: value}}``
without interpreting period keys. Parameter-value routes convert values
to explicit intervals before passing them to the country model.

Scalar reforms default to ``{year}-01-01`` so a caller running
mid-year does not accidentally get a blended partial-year result.
Unknown parameter paths raise ``ValueError`` with a close-match
suggestion; pass ``model_version`` to enable the check.
"""

from __future__ import annotations

import datetime
import re
from collections.abc import Mapping
from difflib import get_close_matches
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from policyengine.core.dynamic import Dynamic
    from policyengine.core.policy import Policy
    from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion


def compile_reform(
    reform: Optional[Mapping[str, Any]],
    *,
    year: Optional[int] = None,
    model_version: Optional[TaxBenefitModelVersion] = None,
) -> Optional[dict[str, dict[str, Any]]]:
    """Compile a simple reform dict to the core reform-dict format.

    Args:
        reform: Flat mapping from parameter path to either a scalar
            (applied from ``{year}-01-01``) or a ``{effective_date: value}``
            mapping.
        year: Simulation year. Used as the default effective date for
            scalar values so a mid-year call still targets the whole year.
        model_version: If provided, parameter paths are validated
            against ``model_version.parameters_by_name`` and unknown
            paths raise with a close-match suggestion.
    """
    if not reform:
        return None

    default_date = f"{year}-01-01" if year is not None else "1900-01-01"

    if model_version is not None:
        valid = set(model_version.parameters_by_name)
        unknown = [path for path in reform if path not in valid]
        if unknown:
            lines = [
                f"Reform contains parameter paths not defined on "
                f"{model_version.model.id} {model_version.version}:",
            ]
            for path in unknown:
                suggestions = get_close_matches(path, valid, n=1, cutoff=0.7)
                hint = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
                lines.append(f"  - '{path}'{hint}")
            raise ValueError("\n".join(lines))

    compiled: dict[str, dict[str, Any]] = {}
    for parameter_path, spec in reform.items():
        if isinstance(spec, Mapping):
            compiled[parameter_path] = {str(k): v for k, v in spec.items()}
        else:
            compiled[parameter_path] = {default_date: spec}
    return compiled


def _reform_dict_to_parameter_values(
    reform: Mapping[str, Any],
    *,
    year: Optional[int],
    model_version: TaxBenefitModelVersion,
) -> list:
    """Compile a flat reform dict into a list of ``ParameterValue`` objects.

    Uses :func:`compile_reform` for path validation and effective-date
    defaulting, then materialises each effective date or inclusive interval
    as a ``ParameterValue`` bound to a
    ``Parameter(name=path, tax_benefit_model_version=model_version)``.
    """
    from policyengine.core.parameter import Parameter
    from policyengine.core.parameter_value import ParameterValue

    compiled = compile_reform(reform, year=year, model_version=model_version)
    if compiled is None:
        return []

    parameter_values: list[ParameterValue] = []
    for path, date_to_value in compiled.items():
        for effective_date, value in date_to_value.items():
            try:
                if not re.fullmatch(
                    r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
                    r"(?:\.[0-9]{4}-[0-9]{2}-[0-9]{2})?",
                    effective_date,
                ):
                    raise ValueError("Invalid date format")
                start, *stops = effective_date.split(".")
                start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
                end_date = (
                    datetime.datetime.strptime(stops[0], "%Y-%m-%d") if stops else None
                )
            except ValueError as exc:
                raise ValueError(
                    f"Invalid reform date key {effective_date!r}. Accepted formats are "
                    "'YYYY-MM-DD' (effective date) and "
                    "'YYYY-MM-DD.YYYY-MM-DD' (inclusive interval). Bare years are "
                    "ambiguous: policyengine-uk's reform dict reads '2027' as fiscal "
                    "year 2027 only, while policyengine-core's Reform.from_dict "
                    "reads it as from 2027 on. Use '2027-04-06.2028-04-05' for one "
                    "UK fiscal year, or '2027-01-01' for an effective date."
                ) from exc
            if end_date is not None and end_date < start_date:
                raise ValueError(
                    f"Reform interval {effective_date!r} has an end date before "
                    "its start date."
                )
            data_type = type(value) if isinstance(value, (int, float, bool)) else float
            parameter_values.append(
                ParameterValue(
                    parameter=Parameter(
                        name=path,
                        tax_benefit_model_version=model_version,
                        data_type=data_type,
                    ),
                    start_date=start_date,
                    end_date=end_date,
                    value=value,
                )
            )
    return parameter_values


def _compile_reform_to(
    cls,
    default_name: str,
    reform: Optional[Mapping[str, Any]],
    *,
    year: Optional[int],
    model_version: TaxBenefitModelVersion,
    name: Optional[str] = None,
):
    parameter_values = _reform_dict_to_parameter_values(
        reform or {}, year=year, model_version=model_version
    )
    if not parameter_values:
        return None
    return cls(name=name or default_name, parameter_values=parameter_values)


def compile_reform_to_policy(
    reform: Optional[Mapping[str, Any]],
    *,
    year: Optional[int],
    model_version: TaxBenefitModelVersion,
    name: Optional[str] = None,
) -> Optional[Policy]:
    """Compile a flat reform dict into a fully-assembled ``Policy``.

    Accepts the same ``{param.path: value}`` /
    ``{param.path: {date_or_interval: value}}`` shape as :func:`compile_reform`,
    but returns a ready-to-use ``Policy`` with ``ParameterValue``
    objects so ``Simulation(policy={...})`` works without hand-building
    ``Parameter`` / ``ParameterValue``.
    """
    from policyengine.core.policy import Policy

    return _compile_reform_to(
        Policy,
        "Reform",
        reform,
        year=year,
        model_version=model_version,
        name=name,
    )


def compile_reform_to_dynamic(
    reform: Optional[Mapping[str, Any]],
    *,
    year: Optional[int],
    model_version: TaxBenefitModelVersion,
    name: Optional[str] = None,
) -> Optional[Dynamic]:
    """``Dynamic`` counterpart of :func:`compile_reform_to_policy`."""
    from policyengine.core.dynamic import Dynamic

    return _compile_reform_to(
        Dynamic,
        "Dynamic response",
        reform,
        year=year,
        model_version=model_version,
        name=name,
    )
