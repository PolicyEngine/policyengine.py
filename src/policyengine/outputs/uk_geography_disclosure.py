"""Disclosure-controlled UK geography outputs.

A thin adapter from two completed simulations to
:mod:`policyengine.disclosure`. It reads the household output, builds one
checked release for the requested levels, and exposes the rows that may be
published.
"""

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import numpy as np
import pandas as pd
from pydantic import ConfigDict, PrivateAttr

from policyengine.core import Output
from policyengine.disclosure import (
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


class UKGeographyDisclosure(Output):
    """Income changes by UK area that are safe to publish.

    Every number passes the disclosure rules of
    :class:`~policyengine.disclosure.DisclosureSettings` and carries a 90%
    interval. ``public`` stays empty while a blocking finding remains.
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
                if column in baseline_hh.columns:
                    return AreaWeights.from_labels(baseline_hh[column], weights)
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
                        f"The household output has none of {list(columns)} for "
                        f"level {level!r}"
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
        parent_of: For a level given as a weight matrix, the region code of
            each of its areas. Required for such a level when the household
            output carries regions.
        acknowledge: Findings the caller accepts after review.
        prior_public: Earlier publications that count as already public.
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
