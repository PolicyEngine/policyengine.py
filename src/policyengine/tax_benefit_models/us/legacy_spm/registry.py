"""Certified US sources that cannot carry their SPM declarations.

BACKWARD COMPATIBILITY (#597, #598). Register a certified source here only
when it cannot carry a declaration itself:

- it was certified before SPM measurement-scope and independence-role
  declarations existed (Build O); or
- the pinned policyengine-us does not define that declaration's variable, so
  the source cannot store it. Today that is ``spm_unit_spm_universe_status``,
  which policyengine-us defines only from PolicyEngine/policyengine-us#9462;
  Microcosm's stored-inputs gate refuses a variable the model does not define.

Register only the declarations the source lacks: a source that stores
``is_spm_independent_minor_role`` takes no independence list. Delete an entry
once nothing reads that source, or once a release of it carries the
declaration natively. Every other certified source must carry the
declarations itself.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

#: How a legacy source's SPM measurement scope is derived.
#:
#: ``acs_household_population``: Census's ACS SPM methodology measures the
#: household population only, so ACS group-quarters units are outside the
#: measurement (see :mod:`.universe`).
SPMUniverseRule = Literal["acs_household_population"]


class IndependenceListPin(BaseModel):
    """A certified list of SPM independence roles, pinned by bundle entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Name of the list's entry in the bundle manifest's datasets.
    bundle_dataset: str
    #: Its certified SHA-256. The bundle manifest must pin the same value.
    sha256: str


class LegacySPMSource(BaseModel):
    """A certified source and the SPM declarations it needs derived."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Human-readable identity: logical dataset name and certified revision.
    name: str
    #: Certified SHA-256 of the source file; the registry key.
    source_sha256: str
    #: How to derive its SPM measurement scope, if it needs one.
    spm_universe_rule: Optional[SPMUniverseRule] = None
    #: Where its ASEC/PUF records' SPM independence role comes from, if it
    #: needs one.
    independence_list: Optional[IndependenceListPin] = None


#: ``populace_us_2024_acs_local`` Build O. It keeps ACS group-quarters
#: residents without declaring SPM scope, and it was built a few hours before
#: PolicyEngine/microcosm#959, so its ASEC/PUF records lack the independence
#: role that the national release carries for the same records.
POPULACE_US_2024_ACS_LOCAL_BUILD_O = LegacySPMSource(
    name=(
        "populace_us_2024_acs_local@"
        "populace-us-2024-buildo-acs-local-767312d60-20260923T074941Z"
    ),
    source_sha256="769756c31f3ca646d12c272511744dec04c0e68870c6946dd945fbba65b6a7ec",
    spm_universe_rule="acs_household_population",
    independence_list=IndependenceListPin(
        bundle_dataset="source_spm_person_independence",
        sha256="22b5968d90fecfeef7614583e493fe10cc16bda8b5be82e6f49a5bc2102d3ce5",
    ),
)

#: ``populace_us_2024_acs_local`` rebuilt for PolicyEngine/microcosm#1263. It
#: stores the SPM independence role for every person, so it takes no list. It
#: cannot store the measurement scope: policyengine-us 2.2.1 does not define
#: ``spm_unit_spm_universe_status``. Its ACS group-quarters units are outside
#: the measurement under Census's ACS household-population rule, as Build O's
#: are. Remove the entry once a release carries the scope natively
#: (PolicyEngine/policyengine-us#9462).
POPULACE_US_2024_ACS_LOCAL_MICROCOSM_1263 = LegacySPMSource(
    name=(
        "populace_us_2024_acs_local@"
        "populace-us-2024-buildo-acs-local-766b7c7-20261017T030317Z"
    ),
    source_sha256="3ce781c440a7f933b1d952ff4e9d9f65f4698c64b94d2fad165af0c662838d6c",
    spm_universe_rule="acs_household_population",
)

LEGACY_SPM_SOURCES: tuple[LegacySPMSource, ...] = (
    POPULACE_US_2024_ACS_LOCAL_BUILD_O,
    POPULACE_US_2024_ACS_LOCAL_MICROCOSM_1263,
)


def legacy_spm_source(source_sha256: Optional[str]) -> Optional[LegacySPMSource]:
    """Return the registered legacy source with this certified SHA-256."""
    if source_sha256 is None:
        return None
    for source in LEGACY_SPM_SOURCES:
        if source.source_sha256 == source_sha256:
            return source
    return None
