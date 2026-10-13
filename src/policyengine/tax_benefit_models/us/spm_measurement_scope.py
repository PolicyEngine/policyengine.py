"""Keep ACS group quarters out of the SPM measurement for one certified source.

#############################################################################
# TEMPORARY ACS GROUP-QUARTERS SPM COMPATIBILITY — THIS MUST BE REPLACED.   #
#                                                                           #
# policyengine.py is standing in for a data contract the source should      #
# carry. DELETE THIS MODULE and its call sites as soon as a certified       #
# ACS-local release declares SPM measurement scope itself (for example      #
# PolicyEngine/microcosm#977 activated in the release build) and a          #
# policyengine-us release that reads that declaration                       #
# (PolicyEngine/policyengine-us#9462 or its successor) is in the bundle.    #
# Tracking issue: https://github.com/PolicyEngine/policyengine.py/issues/597 #
#############################################################################

The certified ACS-local source (:data:`ACS_LOCAL_SOURCE_SHA256`) retains ACS
group-quarters residents for ordinary tax and benefit calculations, but it
does not declare which SPM units belong to the SPM measurement population.
policyengine-us 2.2.1 therefore requests canonical SPM thresholds for every
unit, and a single-person group-quarters unit with no classified adult stops
the whole calculation with ``SPM_COMPOSITION_REQUIRED``.

Census's ACS SPM methodology measures the household population only, so this
module applies that rule to this one source until a compatible release
declares SPM scope itself:

- :func:`classify_spm_units` reads the source's record-type evidence (ACS
  ``TYPEHUGQ``/``RELSHIPP`` and ``person_support_channel``) and marks every ACS
  group-quarters SPM unit as outside the measurement. It never uses age or
  adult counts, and it raises on any evidence it does not recognise.
- ``create_datasets`` stores the result in each year file as the SPM-unit input
  :data:`OUTSIDE_SPM_MEASUREMENT`, with a :class:`SPMMeasurementScope` record.
- :func:`apply_spm_measurement_scope` changes the SPM variables of one
  simulation (and its branches) so that outside units never reach the
  canonical SPM provider and every SPM outcome for them is NaN ("not
  measured"). Measured units keep the canonical values. Poverty indicators
  become floats (1.0, 0.0 or NaN), since a boolean cannot hold "not measured".

Nobody is dropped: memberships, weights and every ordinary tax, benefit and
income calculation are unchanged.

The same record also binds the temporary SPM independence role supplied for
this source's ASEC/PUF records (see ``spm_independence_role``, #598).

Removal steps are in ``docs/engineering/runbooks/acs-local-spm-compatibility.md``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Literal, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

#: SHA-256 of the certified ACS-local source
#: ``populace_us_2024_acs_local.h5`` at revision
#: ``populace-us-2024-buildo-acs-local-767312d60-20260923T074941Z``. The rule
#: applies to year files cut from exactly this file and to nothing else.
ACS_LOCAL_SOURCE_SHA256 = (
    "769756c31f3ca646d12c272511744dec04c0e68870c6946dd945fbba65b6a7ec"
)

#: Identifier of the measurement-scope rule, recorded with every year file and
#: output it produced.
SCOPE_RULE: Final = "acs_2024_household_population_v1"

#: SPM-unit input that marks a unit outside the SPM measurement population.
#: The name is .py's own, so it cannot collide with a scope variable a future
#: policyengine-us release defines.
OUTSIDE_SPM_MEASUREMENT = "policyengine_outside_spm_measurement"

#: Key of the :class:`SPMMeasurementScope` record in a dataset's ``metadata``
#: (a ``create_datasets`` year file or a run's output).
SCOPE_RECORD_KEY = "spm_measurement_scope"

#: H5 dataset holding that record, as UTF-8 JSON, in a US file written by
#: ``PolicyEngineUSDataset.save()``.
SCOPE_H5_DATASET = "policyengine_spm_measurement_scope"

ACS_CHANNEL = "acs_2024_1yr"
NON_ACS_CHANNELS = frozenset({"asec", "puf_tax_detail"})

#: ACS household record type (``TYPEHUGQ``) of a housing unit.
ACS_HOUSING_UNIT = 1
#: ACS group-quarters record types (``TYPEHUGQ``) and the relationship code
#: (``RELSHIPP``) each requires: 2 institutional (37), 3 noninstitutional (38).
ACS_GROUP_QUARTERS = {2: 37, 3: 38}

#: Canonical amount variables built by spm-calculator, and the
#: ``masked_policyengine_amount`` field each one returns.
THRESHOLD_FIELDS = {
    "spm_unit_reference_spm_threshold": "reference_threshold",
    "spm_unit_unadjusted_spm_threshold": "unadjusted_threshold",
    "spm_unit_geographic_adjustment": "geographic_factor",
    "spm_unit_spm_threshold": "threshold",
    "spm_unit_spm_threshold_housing_portion": "housing_portion",
}

#: Formula variables downstream of the SPM thresholds whose results are set to
#: NaN for outside units. Indicators listed in :data:`FLOAT_INDICATORS` also
#: become floats.
MASKED_FORMULA_VARIABLES = (
    "spm_unit_benefits",
    "poverty_gap",
    "deep_poverty_line",
    "deep_poverty_gap",
    "spm_unit_is_in_spm_poverty",
    "spm_unit_is_in_deep_spm_poverty",
    "in_poverty",
    "in_deep_poverty",
    "person_in_poverty",
    "spm_unit_oecd_equiv_net_income",
)

FLOAT_INDICATORS = frozenset(
    {
        "spm_unit_is_in_spm_poverty",
        "spm_unit_is_in_deep_spm_poverty",
        "in_poverty",
        "in_deep_poverty",
        "person_in_poverty",
    }
)

#: ``adds``/``subtracts`` variables that carry NaN from a masked component.
NAN_PROPAGATING_VARIABLES = ("spm_unit_net_income", "poverty_line")

#: Every SPM measurement variable that is NaN for an outside unit.
SPM_MEASUREMENT_VARIABLES = (
    *THRESHOLD_FIELDS,
    "spm_unit_capped_housing_subsidy",
    *MASKED_FORMULA_VARIABLES,
    *NAN_PROPAGATING_VARIABLES,
    "spm_unit_income_decile",
)


class SPMMeasurementScope(BaseModel):
    """Record of the SPM measurement scope applied to a year file or output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: Literal["acs_2024_household_population_v1"]
    source_sha256: str
    outside_spm_units: int = Field(ge=0)
    measured_spm_units: int = Field(ge=0)
    #: SHA-256 of the national independence list the year file's
    #: ``is_spm_independent_minor_role`` came from (#598).
    independence_list_sha256: str
    #: People whose role came from that list (the source's ASEC/PUF people).
    independence_list_people: int = Field(ge=0)


def applies_to_source(source_sha256: Optional[str]) -> bool:
    """Return whether the measurement-scope rule applies to a verified source."""
    return source_sha256 == ACS_LOCAL_SOURCE_SHA256


def classify_spm_units(person: pd.DataFrame, household: pd.DataFrame) -> pd.Series:
    """Return whether each SPM unit is outside the SPM measurement population.

    ``person`` and ``household`` are the source's stored entity tables. The
    result is a boolean Series indexed by SPM unit ID: ``True`` for an ACS
    group-quarters unit, ``False`` for an ACS housing-unit or non-ACS unit.

    Raises:
        ValueError: if any evidence is missing, unrecognised or inconsistent,
            or if an SPM unit mixes measured and outside people.
    """
    unit_link = _person_link(person, "spm_unit")
    household_link = _person_link(person, "household")
    for column in ("person_support_channel", "RELSHIPP"):
        if column not in person.columns:
            raise ValueError(f"SPM measurement scope needs person {column!r}.")
    for column in ("household_id", "TYPEHUGQ"):
        if column not in household.columns:
            raise ValueError(f"SPM measurement scope needs household {column!r}.")
    if household["household_id"].duplicated().any():
        raise ValueError("SPM measurement scope needs unique household_id values.")

    channel = person["person_support_channel"].map(_decode)
    relationship = pd.to_numeric(person["RELSHIPP"], errors="raise")
    record_type = pd.to_numeric(
        person[household_link].map(household.set_index("household_id")["TYPEHUGQ"]),
        errors="raise",
    )
    if not person[household_link].isin(household["household_id"]).all():
        raise ValueError("SPM measurement scope found people with unknown households.")

    acs = channel.eq(ACS_CHANNEL)
    non_acs = channel.isin(NON_ACS_CHANNELS)
    unknown = ~(acs | non_acs)
    if unknown.any():
        channels = sorted(map(str, channel[unknown].unique()))
        raise ValueError(
            f"SPM measurement scope has no rule for source channels {channels}."
        )

    housing_unit = (
        acs
        & record_type.eq(ACS_HOUSING_UNIT)
        & relationship.notna()
        & ~relationship.isin(list(ACS_GROUP_QUARTERS.values()))
    )
    group_quarters = acs & pd.Series(False, index=person.index)
    for quarters_type, quarters_relationship in ACS_GROUP_QUARTERS.items():
        group_quarters |= (
            acs & record_type.eq(quarters_type) & relationship.eq(quarters_relationship)
        )
    recognised_non_acs = non_acs & record_type.isna() & relationship.isna()
    unrecognised = ~(housing_unit | group_quarters | recognised_non_acs)
    if unrecognised.any():
        raise ValueError(
            f"SPM measurement scope cannot classify {int(unrecognised.sum())} "
            "people: their TYPEHUGQ/RELSHIPP evidence is missing or "
            "inconsistent with their source channel."
        )

    by_unit = group_quarters.groupby(person[unit_link])
    mixed = by_unit.nunique() > 1
    if mixed.any():
        raise ValueError(
            f"SPM measurement scope found {int(mixed.sum())} SPM units mixing "
            "group-quarters and household people."
        )
    outside = by_unit.first().astype(bool)
    outside.index.name = "spm_unit_id"
    return outside


def build_scope(
    source_sha256: str,
    outside: pd.Series,
    independence_list_sha256: str,
    independence_list_people: int,
) -> SPMMeasurementScope:
    return SPMMeasurementScope(
        rule=SCOPE_RULE,
        source_sha256=source_sha256,
        outside_spm_units=int(outside.sum()),
        measured_spm_units=int((~outside).sum()),
        independence_list_sha256=independence_list_sha256,
        independence_list_people=independence_list_people,
    )


def outside_by_spm_unit(spm_unit_ids: Any, outside: pd.Series) -> np.ndarray:
    """Align a classification to SPM unit IDs, refusing unclassified units."""
    aligned = pd.Series(np.asarray(spm_unit_ids)).map(outside)
    if aligned.isna().any():
        raise ValueError(
            f"SPM measurement scope has no classification for "
            f"{int(aligned.isna().sum())} SPM units."
        )
    return np.asarray(aligned.to_numpy(dtype=bool))


def scope_from_metadata(metadata: Mapping[str, Any]) -> Optional[SPMMeasurementScope]:
    """Return the scope record in a dataset's ``metadata``, if it has one."""
    record = metadata.get(SCOPE_RECORD_KEY)
    if record is None:
        return None
    return SPMMeasurementScope.model_validate(record)


def read_scope_record(path: str | Path) -> Optional[SPMMeasurementScope]:
    """Return the scope record stored in an H5 file, or ``None``."""
    import h5py

    try:
        with h5py.File(path, "r") as file:
            if SCOPE_H5_DATASET not in file:
                return None
            raw = file[SCOPE_H5_DATASET].asstr()[()]
    except OSError:
        return None
    return SPMMeasurementScope.model_validate(json.loads(raw))


def write_scope_record(path: str | Path, scope: SPMMeasurementScope) -> None:
    """Store a scope record in an H5 file, replacing any it has."""
    import h5py

    with h5py.File(path, "a") as file:
        if SCOPE_H5_DATASET in file:
            del file[SCOPE_H5_DATASET]
        file.create_dataset(
            SCOPE_H5_DATASET,
            data=scope.model_dump_json(),
            dtype=h5py.string_dtype("utf-8"),
        )


def check_scoped_spm_units(spm_unit: pd.DataFrame, scope: SPMMeasurementScope) -> None:
    """Refuse a scoped dataset whose SPM-unit table lacks a complete input."""
    if OUTSIDE_SPM_MEASUREMENT not in spm_unit.columns:
        raise ValueError(
            f"This dataset records SPM measurement scope {scope.rule!r} but "
            f"stores no {OUTSIDE_SPM_MEASUREMENT!r} SPM-unit column. "
            "Regenerate it with ensure_datasets() or create_datasets()."
        )
    values = spm_unit[OUTSIDE_SPM_MEASUREMENT]
    if values.isna().any() or not pd.api.types.is_bool_dtype(values.dtype):
        raise ValueError(
            f"The stored {OUTSIDE_SPM_MEASUREMENT!r} column must be complete "
            "and boolean."
        )


def apply_spm_measurement_scope(microsimulation) -> None:
    """Apply the measurement scope to a simulation and every branch it has.

    Call it after the simulation is constructed (so every policy and
    structural reform is already applied) and before its populations are
    built, so that the stored :data:`OUTSIDE_SPM_MEASUREMENT` column loads as an
    input. Applying it again changes nothing.
    """
    from policyengine.tax_benefit_models.us.legacy_inputs import (
        _simulation_and_branches,
    )

    reform = _measurement_scope_reform()
    for simulation in _simulation_and_branches(microsimulation):
        if OUTSIDE_SPM_MEASUREMENT not in simulation.tax_benefit_system.variables:
            simulation.apply_reform(reform)


def _measurement_scope_reform():
    from policyengine_core.periods import ETERNITY
    from policyengine_core.reforms import Reform
    from policyengine_core.variables import Variable
    from policyengine_us.entities import SPMUnit

    class policyengine_outside_spm_measurement(Variable):
        value_type = bool
        entity = SPMUnit
        definition_period = ETERNITY
        default_value = False
        label = "Outside the SPM measurement population"
        documentation = (
            "Temporary policyengine.py input: an ACS group-quarters unit "
            "outside Census's household-population SPM measurement."
        )

    class spm_measurement_scope(Reform):
        def apply(self):
            self.add_variable(policyengine_outside_spm_measurement)
            for name, field in THRESHOLD_FIELDS.items():
                self.update_variable(_threshold_variable(name, field))
            self.update_variable(_capped_housing_subsidy_variable())
            for name in MASKED_FORMULA_VARIABLES:
                self.update_variable(_masked_variable(self.variables[name]))
            self.update_variable(_income_decile_variable())
            for name in NAN_PROPAGATING_VARIABLES:
                variable = self.variables[name]
                if variable.formulas or not variable.adds:
                    raise ValueError(
                        f"SPM measurement scope expects {name!r} to add up "
                        "its components; this policyengine-us release "
                        "computes it differently."
                    )

    return spm_measurement_scope


def _outside(population, period) -> np.ndarray:
    if population.entity.key == "spm_unit":
        values = population(OUTSIDE_SPM_MEASUREMENT, period)
    else:
        values = population.spm_unit(OUTSIDE_SPM_MEASUREMENT, period)
    return np.asarray(values, dtype=bool)


def _threshold_variable(name: str, field: str):
    from policyengine_core.variables import Variable
    from policyengine_us.spm import masked_policyengine_amount

    def formula(spm_unit, period, parameters):
        outside = _outside(spm_unit, period)
        amounts = masked_policyengine_amount(spm_unit, period, field, ~outside)
        return np.where(outside, np.nan, amounts)

    return type(name, (Variable,), {"formula": formula, "__module__": __name__})


def _capped_housing_subsidy_variable():
    """``spm_unit_capped_housing_subsidy`` for measured units only.

    The same cap as policyengine-us 2.2.1, evaluated for assisted units inside
    the measurement; outside units are NaN.
    """
    from policyengine_core.variables import Variable
    from policyengine_us.spm import masked_policyengine_amount

    def formula(spm_unit, period, parameters):
        outside = _outside(spm_unit, period)
        housing_assistance = np.asarray(
            spm_unit("spm_unit_allocated_housing_subsidy", period), dtype=np.float64
        )
        assisted = (housing_assistance > 0) & ~outside
        capped = np.zeros_like(housing_assistance)
        if assisted.any():
            housing_portion = masked_policyengine_amount(
                spm_unit, period, "housing_portion", assisted
            )
            tenant_payment = np.asarray(
                spm_unit("spm_unit_allocated_tenant_payment", period),
                dtype=np.float64,
            )
            cap = np.maximum(housing_portion - tenant_payment, 0)
            capped = np.where(assisted, np.minimum(housing_assistance, cap), 0)
        return np.where(outside, np.nan, capped)

    return type(
        "spm_unit_capped_housing_subsidy",
        (Variable,),
        {"formula": formula, "__module__": __name__},
    )


def _masked_variable(original):
    """Wrap a formula variable so that outside units are NaN."""
    from policyengine_core.variables import Variable

    if not original.formulas:
        raise ValueError(
            f"SPM measurement scope expects {original.name!r} to have a formula; "
            "this policyengine-us release computes it differently."
        )

    def formula(population, period, parameters):
        original_formula = original.get_formula(period)
        if original_formula.__code__.co_argcount == 2:
            values = original_formula(population, period)
        else:
            values = original_formula(population, period, parameters)
        return np.where(
            _outside(population, period),
            np.nan,
            np.asarray(values, dtype=np.float64),
        )

    attributes: dict[str, Any] = {"formula": formula, "__module__": __name__}
    if original.name in FLOAT_INDICATORS:
        attributes["value_type"] = float
        attributes["default_value"] = 0.0
    return type(original.name, (Variable,), attributes)


def _income_decile_variable():
    """Rank measured SPM units only; outside units have no decile."""
    from microdf import MicroSeries
    from policyengine_core.variables import Variable

    def formula(spm_unit, period, parameters):
        outside = _outside(spm_unit, period)
        income = np.asarray(spm_unit("spm_unit_oecd_equiv_net_income", period))
        weights = np.asarray(spm_unit("spm_unit_weight", period)) * np.asarray(
            spm_unit.nb_persons()
        )
        deciles = np.full(len(income), np.nan)
        measured = ~outside
        if measured.any():
            deciles[measured] = np.asarray(
                MicroSeries(income[measured], weights=weights[measured]).decile_rank()
            )
        return deciles

    return type(
        "spm_unit_income_decile",
        (Variable,),
        {
            "value_type": float,
            "default_value": 0.0,
            "formula": formula,
            "__module__": __name__,
        },
    )


def _person_link(person: pd.DataFrame, entity: str) -> str:
    for column in (f"person_{entity}_id", f"{entity}_id"):
        if column in person.columns:
            return column
    raise ValueError(f"SPM measurement scope needs a person {entity} link.")


def _decode(value: Any) -> Any:
    return value.decode("utf-8") if isinstance(value, bytes) else value
