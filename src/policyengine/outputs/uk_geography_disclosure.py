"""Disclosure-controlled UK geography outputs.

A thin adapter from two completed simulations to
:mod:`policyengine.disclosure`. It reads the household output, builds one
checked release for the requested levels, and exposes the rows that may be
published.
"""

from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import numpy as np
import pandas as pd
from pydantic import ConfigDict, PrivateAttr

from policyengine.core import Output
from policyengine.disclosure import (
    UNASSIGNED,
    AreaWeights,
    DisclosureSettings,
    Finding,
    PriorPublic,
    PublicTable,
    Release,
    estimate_change,
)

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

UK_NATIONAL_LEVEL = "national"
UK_NATIONAL_AREA_CODE = "UK"
UK_REGION_LEVEL = "region"
# Household output columns that hold each level's area code, in order of
# preference.
UK_DISCLOSURE_LEVEL_COLUMNS = {
    UK_REGION_LEVEL: ("region_code_oa", "region"),
    "constituency": ("constituency_code_oa",),
    "local_authority": ("la_code_oa",),
}
UK_SOURCE_HOUSEHOLD_ID_COLUMN = "source_household_id"
# The ONS GSS code of each region, by every spelling a household output may
# carry. Regions are always keyed on these codes, so a release from a national
# dataset and one from a local file publish the same codes, and publishers use
# them in parent_of and prior_public. England has nine regions; Wales, Scotland
# and Northern Ireland are one region each, under their country code.
UK_REGION_GSS_CODES: dict[str, str] = {
    # GSS codes, as Microcosm writes them in region_code_oa.
    "E12000001": "E12000001",
    "E12000002": "E12000002",
    "E12000003": "E12000003",
    "E12000004": "E12000004",
    "E12000005": "E12000005",
    "E12000006": "E12000006",
    "E12000007": "E12000007",
    "E12000008": "E12000008",
    "E12000009": "E12000009",
    "W92000004": "W92000004",
    "S92000003": "S92000003",
    "N92000002": "N92000002",
    # The pseudo codes Microcosm writes in region_code_oa for the nations.
    "W99999999": "W92000004",
    "S99999999": "S92000003",
    "N99999999": "N92000002",
    # The names of the engine's region enum, as the stored region holds them.
    "NORTH_EAST": "E12000001",
    "NORTH_WEST": "E12000002",
    "YORKSHIRE": "E12000003",
    "EAST_MIDLANDS": "E12000004",
    "WEST_MIDLANDS": "E12000005",
    "EAST_OF_ENGLAND": "E12000006",
    "LONDON": "E12000007",
    "SOUTH_EAST": "E12000008",
    "SOUTH_WEST": "E12000009",
    "WALES": "W92000004",
    "SCOTLAND": "S92000003",
    "NORTHERN_IRELAND": "N92000002",
    "UNKNOWN": UNASSIGNED,
}


def _uk_region_gss_codes(values: object, column: str) -> np.ndarray:
    """The GSS code of each region value, blank where it is unassigned.

    Values may be strings, bytes or members of the engine's region enum. A
    missing value is unassigned. Any value outside the table raises: a region
    under another spelling would match no code that a publisher passes.
    """
    index, spellings = pd.factorize(pd.Series(values, dtype=object))
    codes: list[Optional[str]] = []
    unknown = 0
    for spelling in spellings:
        if isinstance(spelling, Enum):
            spelling = spelling.name
        if isinstance(spelling, bytes):
            spelling = spelling.decode("utf-8")
        spelling = str(spelling).strip()
        code = UK_REGION_GSS_CODES.get(spelling) if spelling else UNASSIGNED
        if code is None:
            unknown += 1
        codes.append(code)
    if unknown:
        raise ValueError(
            f"Values in {column} that name no UK region: {unknown}. A region is "
            "a GSS code, a name of the engine's region enum, or a Microcosm "
            "pseudo code for a nation; see UK_REGION_GSS_CODES."
        )
    # Factorize marks a missing value with -1, which picks the last entry.
    return np.asarray(np.array([*codes, UNASSIGNED], dtype=object)[index])


def _assigns_an_area(codes: np.ndarray) -> bool:
    """Whether any household has an area code, rather than a blank."""
    values = pd.Series(codes, dtype=object)
    for code in values[values.notna()].unique():
        text = code.decode("utf-8") if isinstance(code, bytes) else str(code)
        if text.strip() != UNASSIGNED:
            return True
    return False


class UKGeographyDisclosure(Output):
    """Income changes by UK area that are safe to publish.

    Every number passes the disclosure rules of
    :class:`~policyengine.disclosure.DisclosureSettings` and carries a 90%
    interval. ``public`` stays empty while a blocking finding remains.
    Regions are keyed on their ONS GSS codes; see ``UK_REGION_GSS_CODES``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    year: int
    levels: tuple[str, ...] = (UK_REGION_LEVEL,)
    reform: str = "reform"
    settings: Optional[DisclosureSettings] = None
    income_variable: str = "household_net_income"

    # Results populated by run()
    public: Optional[PublicTable] = None
    findings: Optional[list[Finding]] = None

    _release: Optional[Release] = PrivateAttr(default=None)

    @property
    def release(self) -> Release:
        """The checked release, for example to withhold a cell by hand."""
        if self._release is None:
            raise ValueError("Call run() first.")
        return self._release

    def run(
        self,
        *,
        noise_key: Optional[Union[str, bytes]] = None,
        source_ids: Optional[Sequence] = None,
        area_weights: Optional[Mapping[str, AreaWeights]] = None,
        parent_of: Optional[Mapping[str, Mapping[str, str]]] = None,
        acknowledge: Iterable[str] = (),
        prior_public: Sequence[PriorPublic] = (),
        audit_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        """Estimate each level, check the release and fill the results."""
        baseline_hh = pd.DataFrame(
            self.baseline_simulation.output_dataset.data.household
        )
        reform_hh = pd.DataFrame(self.reform_simulation.output_dataset.data.household)
        for name, frame in (("Baseline", baseline_hh), ("Reform", reform_hh)):
            if self.income_variable not in frame.columns:
                raise ValueError(
                    f"{name} household output must include {self.income_variable}"
                )
        if "household_weight" not in baseline_hh.columns:
            raise ValueError("Baseline household output must include household_weight")
        if len(baseline_hh) != len(reform_hh):
            raise ValueError(
                "Baseline and reform household outputs must have the same row count"
            )
        if (
            "household_id" in baseline_hh.columns
            and "household_id" in reform_hh.columns
        ):
            same = np.array_equal(
                baseline_hh["household_id"].to_numpy(),
                reform_hh["household_id"].to_numpy(),
            )
            if not same:
                raise ValueError(
                    "Baseline and reform household outputs must hold the same "
                    "households in the same order"
                )
        if source_ids is None:
            if UK_SOURCE_HOUSEHOLD_ID_COLUMN not in baseline_hh.columns:
                raise ValueError(
                    f"The household output has no {UK_SOURCE_HOUSEHOLD_ID_COLUMN} "
                    "column, so support cannot be counted by survey household. "
                    "Pass source_ids= with one id per household row."
                )
            source_ids = baseline_hh[UK_SOURCE_HOUSEHOLD_ID_COLUMN].to_numpy()

        weights = baseline_hh["household_weight"].to_numpy(dtype=float)
        custom = dict(area_weights or {})
        parents = dict(parent_of or {})
        # A release ignores prior cells at levels it does not hold, since they
        # may belong to other publications. Every UK level is known here, so a
        # cell at any other level is a misspelling that would match nothing.
        known = {UK_NATIONAL_LEVEL, *UK_DISCLOSURE_LEVEL_COLUMNS, *custom}
        stray = [
            cell[0]
            for prior in prior_public
            for cell in prior.cells
            if cell[0] not in known
        ]
        if stray:
            raise ValueError(
                f"Prior cells at levels that are not UK levels: {len(stray)}, "
                f"at {sorted(set(stray))}. The levels are {sorted(known)}."
            )

        def areas_for(level: str) -> Optional[AreaWeights]:
            if level in custom:
                return custom[level]
            if level == UK_NATIONAL_LEVEL:
                codes = np.full(len(baseline_hh), UK_NATIONAL_AREA_CODE, dtype=object)
                return AreaWeights.from_labels(codes, weights)
            columns = UK_DISCLOSURE_LEVEL_COLUMNS.get(level)
            if columns is None:
                raise ValueError(f"Unknown level {level!r}")
            for column in columns:
                if column not in baseline_hh.columns:
                    continue
                codes = baseline_hh[column].to_numpy(dtype=object)
                if level == UK_REGION_LEVEL:
                    codes = _uk_region_gss_codes(codes, column)
                # A column that gives no household an area, such as an empty
                # region_code_oa, says nothing: read the next one.
                if _assigns_an_area(codes):
                    return AreaWeights.from_labels(codes, weights)
            return None

        settings = self.settings or DisclosureSettings()
        release = Release(settings, prior_public=prior_public, acknowledge=acknowledge)
        # The nation and the regions are always estimated: a level that is not
        # requested still serves as the parent in the remainder check.
        estimated: dict[str, AreaWeights] = {}
        for level in dict.fromkeys((UK_NATIONAL_LEVEL, UK_REGION_LEVEL, *self.levels)):
            areas = areas_for(level)
            if areas is None:
                if level in self.levels:
                    columns = UK_DISCLOSURE_LEVEL_COLUMNS[level]
                    raise ValueError(
                        f"The household output gives no household an area in "
                        f"any of {list(columns)} for level {level!r}"
                    )
                continue
            estimated[level] = areas
            release.add(
                estimate_change(
                    level=level,
                    reform=self.reform,
                    year=self.year,
                    areas=areas,
                    source_ids=source_ids,
                    baseline=baseline_hh[self.income_variable].to_numpy(dtype=float),
                    reformed=reform_hh[self.income_variable].to_numpy(dtype=float),
                    settings=settings,
                    noise_key=noise_key,
                ),
                publish=level in self.levels,
            )

        regions = estimated.get(UK_REGION_LEVEL)
        for level, areas in estimated.items():
            if level == UK_NATIONAL_LEVEL:
                continue
            if (
                level == UK_REGION_LEVEL
                or regions is None
                or not regions.one_area_per_record
            ):
                release.add_nesting(level, UK_NATIONAL_LEVEL)
                continue
            if not areas.one_area_per_record and level not in parents:
                # Against the nation alone, every withheld area goes into one
                # remainder, and that nearly always passes.
                raise ValueError(
                    f"Level {level!r} is a weight matrix. Pass "
                    f"parent_of={{{level!r}: ...}} with the region code of each "
                    "area, so its areas are checked against their region."
                )
            release.add_nesting(level, UK_REGION_LEVEL, parents.get(level))

        self._release = release
        self.refresh()
        if audit_dir is not None:
            release.write_audit(audit_dir)

    def refresh(self) -> Optional[PublicTable]:
        """Check the release again, for example after withholding a cell."""
        release = self.release
        self.findings = release.check()
        blocked = any(finding.blocking for finding in self.findings)
        self.public = None if blocked else release.to_public()
        return self.public


def compute_uk_geography_disclosure(
    baseline_simulation: "Simulation",
    reform_simulation: "Simulation",
    *,
    year: int,
    levels: Sequence[str] = (UK_REGION_LEVEL,),
    reform: str = "reform",
    settings: Optional[DisclosureSettings] = None,
    income_variable: str = "household_net_income",
    noise_key: Optional[Union[str, bytes]] = None,
    source_ids: Optional[Sequence] = None,
    area_weights: Optional[Mapping[str, AreaWeights]] = None,
    parent_of: Optional[Mapping[str, Mapping[str, str]]] = None,
    acknowledge: Iterable[str] = (),
    prior_public: Sequence[PriorPublic] = (),
    audit_dir: Optional[Union[str, Path]] = None,
) -> UKGeographyDisclosure:
    """Compute income changes by UK area under disclosure control.

    Args:
        baseline_simulation: Completed baseline simulation.
        reform_simulation: Completed reform simulation.
        year: Year of the results, used as a label.
        levels: Levels to publish: ``national``, ``region``, ``constituency``
            or ``local_authority``.
        reform: Label of the reform. A package and its components need
            distinct labels.
        settings: Publication rules. The defaults follow the UK Data Service
            licence: at least 10 distinct survey households behind a number.
        income_variable: Household output column whose change is measured.
        noise_key: Secret key for the noise, needed only when
            ``settings.noise`` is on. Else read from
            ``POLICYENGINE_DISCLOSURE_NOISE_KEY``.
        source_ids: The survey household of each household row. Needed when
            the dataset has no ``source_household_id`` column.
        area_weights: Weights for a level, in place of the level's area code
            column, for example an area x household weight matrix.
        parent_of: For a level given as a weight matrix, the GSS code of the
            region of each of its areas (see ``UK_REGION_GSS_CODES``).
            Required for such a level when the household output carries
            regions.
        acknowledge: Findings the caller accepts after review.
        prior_public: Earlier publications that count as already public.
            Their region cells use GSS codes too.
        audit_dir: Private directory, outside any repository, for the exact
            values and counts.

    Returns:
        UKGeographyDisclosure with ``public`` and ``findings`` populated.
        ``public`` is None while a blocking finding remains.
    """
    impact = UKGeographyDisclosure.model_construct(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        year=int(year),
        levels=tuple(levels),
        reform=reform,
        settings=settings,
        income_variable=income_variable,
    )
    impact.run(
        noise_key=noise_key,
        source_ids=source_ids,
        area_weights=area_weights,
        parent_of=parent_of,
        acknowledge=acknowledge,
        prior_public=prior_public,
        audit_dir=audit_dir,
    )
    return impact
