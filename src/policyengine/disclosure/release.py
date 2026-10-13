"""A release: the only object that turns private estimates into public rows.

A release collects the estimates that will be published together, checks what
a reader could recover by subtraction, and refuses to publish while a blocking
finding remains. The check reports; it does not withhold cells by itself. A
person resolves a finding with :meth:`Release.withhold` and checks again.
"""

import os
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

from .estimate import AreaEstimates
from .schema import (
    ACKNOWLEDGEABLE_FINDINGS,
    ALREADY_PUBLIC,
    APPROXIMATE,
    CHANGE_OUTCOMES,
    FAMILIES,
    FAMILY_CHANGE,
    FAMILY_GAINING,
    FAMILY_LOSING,
    NOISE_REFERENCE_PUBLIC,
    OUTCOME_FAMILY,
    PRIVATE_SECONDARY,
    REASON_DISCLOSURE_CONTROL,
    REASON_THIN_SUPPORT,
    RECOVERABLE_PARENT,
    RECOVERABLE_REMAINDER,
    SHARE_NO_CHANGE,
    UNCHECKED_OVERLAP,
    WITHHELD,
    DisclosureSettings,
    Finding,
    PriorPublic,
    PublicRow,
    PublicTable,
)
from .support import cell_tier, family_supports

_Key = tuple[str, str, int]
_FAMILY_OUTCOMES = {
    FAMILY_CHANGE: CHANGE_OUTCOMES,
    FAMILY_GAINING: (FAMILY_GAINING,),
    FAMILY_LOSING: (FAMILY_LOSING,),
}


class DisclosureError(RuntimeError):
    """The release cannot be checked or published as it stands."""


class Release:
    """Estimates that are published together, and the checks across them."""

    def __init__(
        self,
        settings: Optional[DisclosureSettings] = None,
        *,
        prior_public: Sequence[PriorPublic] = (),
        acknowledge: Iterable[str] = (),
    ) -> None:
        self.settings = settings or DisclosureSettings()
        self._acknowledged = frozenset(acknowledge)
        unknown = sorted(self._acknowledged - set(ACKNOWLEDGEABLE_FINDINGS))
        if unknown:
            raise ValueError(f"These findings cannot be acknowledged: {unknown}")
        self._prior = tuple(prior_public)
        self._estimates: dict[_Key, AreaEstimates] = {}
        self._published: dict[_Key, bool] = {}
        self._nestings: list[tuple[str, str, Optional[dict[str, str]]]] = []
        self._packages: list[tuple[str, tuple[str, ...]]] = []
        self._manual: set[tuple[str, str, int, str, str]] = set()
        self._findings: Optional[list[Finding]] = None

    def add(self, estimates: AreaEstimates, *, publish: bool = True) -> None:
        """Add the estimates of one level, reform and year.

        With ``publish=False`` the estimates are a reference only: the release
        does not emit their rows, and treats the rows that pass the rules as
        public elsewhere.
        """
        if estimates.settings != self.settings:
            raise DisclosureError(
                "The estimates were made under other settings than the release's."
            )
        key = (estimates.level, estimates.reform, estimates.year)
        if key in self._estimates:
            raise DisclosureError(f"The release already holds estimates for {key}.")
        self._estimates[key] = estimates
        self._published[key] = publish
        self._findings = None

    def add_nesting(
        self,
        child_level: str,
        parent_level: str,
        parent_of: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Declare that the areas of one level tile the areas of another.

        ``parent_of`` (child area code to parent area code) is needed only when
        the child level is a weight matrix and the parent has several areas.
        """
        mapping = dict(parent_of) if parent_of is not None else None
        self._nestings.append((child_level, parent_level, mapping))
        self._findings = None

    def add_package(self, package: str, components: Sequence[str]) -> None:
        """Declare that one reform is the sum of other reforms in the release."""
        self._packages.append((package, tuple(components)))
        self._findings = None

    def withhold(
        self, *, level: str, area_code: str, reform: str, year: int, outcome: str
    ) -> None:
        """Withhold a cell by hand, for example to resolve a finding.

        Outcomes that share a numerator are withheld together.
        """
        family = OUTCOME_FAMILY.get(outcome)
        if family is None:
            raise ValueError(
                f"Withhold {FAMILY_GAINING!r} or {FAMILY_LOSING!r} instead of "
                f"{outcome!r}."
            )
        key = (level, reform, int(year))
        estimates = self._estimates.get(key)
        if estimates is None or area_code not in estimates.areas.area_codes:
            raise DisclosureError(f"The release has no cell for {key}, {area_code!r}.")
        self._manual.add((*key, family, area_code))
        self._findings = None

    @property
    def findings(self) -> Optional[list[Finding]]:
        """The findings of the last check, or None if the release changed since."""
        return self._findings

    def check(self) -> list[Finding]:
        """Report what a reader could recover from the rows as they stand."""
        tiers = {
            (key, family): self._family_tiers(key, family)
            for key in self._estimates
            for family in FAMILIES
        }
        known = self._known_cells()
        findings: list[Finding] = []
        self._check_nesting(tiers, known, findings)
        self._check_packages(tiers, known, findings)
        self._check_overlap(findings)
        self._check_prior(tiers, findings)
        self._findings = findings
        return findings

    def to_public(self) -> PublicTable:
        """The rows that may be published. Raises while anything blocks."""
        if self._findings is None:
            raise DisclosureError("Run check() before to_public().")
        blocking = sorted(
            {finding.code for finding in self._findings if finding.blocking}
        )
        if blocking:
            raise DisclosureError(
                f"Blocking findings remain: {blocking}. Resolve them, then run "
                "check() again."
            )
        rows: list[PublicRow] = []
        for key in sorted(self._estimates):
            if not self._published[key]:
                continue
            estimates = self._estimates[key]
            for record, tier, _ in self._effective_rows(key):
                common = {
                    "level": record["level"],
                    "area_code": record["area_code"],
                    "reform": record["reform"],
                    "year": int(record["year"]),
                    "outcome": record["outcome"],
                    "noise": estimates.noise,
                }
                if tier == WITHHELD:
                    rows.append(
                        PublicRow(
                            **common, tier=WITHHELD, reason=REASON_DISCLOSURE_CONTROL
                        )
                    )
                    continue
                direction = record["direction"]
                rows.append(
                    PublicRow(
                        **common,
                        value=float(record["value"]),
                        lo=float(record["lo"]),
                        hi=float(record["hi"]),
                        direction=None if pd.isna(direction) else str(direction),
                        tier=tier,
                        reason=REASON_THIN_SUPPORT if tier == APPROXIMATE else None,
                        support_band=record["support_band"],
                    )
                )
        return PublicTable(rows=rows)

    def write_audit(self, private_dir: Union[str, Path]) -> Path:
        """Write exact values, counts and shares to a private directory.

        The directory must be outside any git repository, so the audit cannot
        be committed or published with a bundle.
        """
        directory = Path(private_dir).expanduser().resolve()
        for folder in (directory, *directory.parents):
            if (folder / ".git").exists():
                raise DisclosureError(
                    "The audit path is inside a git repository. Choose a private "
                    "path outside any repository."
                )
        directory.mkdir(parents=True, exist_ok=True)
        frames = []
        for key in sorted(self._estimates):
            frame = self._estimates[key].table.drop(columns=["family_tier"]).copy()
            effective = list(self._effective_rows(key))
            frame["tier"] = [tier for _, tier, _ in effective]
            frame["private_reason"] = [reason for _, _, reason in effective]
            frame["published"] = self._published[key]
            frames.append(frame)
        audit = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        path = directory / "disclosure_audit.csv"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", newline="") as handle:
            audit.to_csv(handle, index=False)
        os.chmod(path, 0o600)
        return path

    # -- tiers ---------------------------------------------------------------

    def _family_tiers(self, key: _Key, family: str) -> dict[str, str]:
        tiers = self._estimates[key].family_tiers(family)
        for level, reform, year, manual_family, area in self._manual:
            if (level, reform, year) == key and manual_family == family:
                tiers[area] = WITHHELD
        return tiers

    def _effective_rows(self, key: _Key) -> Iterable[tuple[dict, str, Optional[str]]]:
        """Each private row with its tier and reason after manual withholding."""
        manual = {
            (family, area)
            for level, reform, year, family, area in self._manual
            if (level, reform, year) == key
        }
        for record in self._estimates[key].table.to_dict("records"):
            outcome, area = record["outcome"], record["area_code"]
            families = (
                (FAMILY_GAINING, FAMILY_LOSING)
                if outcome == SHARE_NO_CHANGE
                else (OUTCOME_FAMILY[outcome],)
            )
            reason = record["private_reason"]
            reason = None if pd.isna(reason) else reason
            if any((family, area) in manual for family in families):
                yield record, WITHHELD, PRIVATE_SECONDARY
            else:
                yield record, record["tier"], reason

    def _known_cells(self) -> set[tuple[str, str, str, int, str]]:
        """Family cells an earlier publication already made public."""
        known = set()
        for prior in self._prior:
            for level, area, reform, year, outcome in prior.cells:
                family = OUTCOME_FAMILY.get(outcome)
                if family is not None:
                    known.add((level, area, reform, int(year), family))
        return known

    # -- relations -----------------------------------------------------------

    def _passes(
        self, estimates: AreaEstimates, weights: np.ndarray, family: str
    ) -> tuple[bool, bool]:
        """Whether a remainder may be recovered, and whether it is empty."""
        records = np.flatnonzero(weights)
        supports = family_supports(
            weights[records],
            estimates.contributions[family][records],
            estimates.source_index[records],
            family,
        )
        tier, _ = cell_tier(
            supports,
            self.settings,
            one_area_per_record=estimates.areas.one_area_per_record,
            noise=estimates.noise,
        )
        empty = supports[0].n_sources == 0
        return tier != WITHHELD, empty

    @staticmethod
    def _require_same_records(first: AreaEstimates, second: AreaEstimates) -> None:
        same = first.areas.n_records == second.areas.n_records and np.array_equal(
            first.source_index, second.source_index
        )
        if not same:
            raise DisclosureError(
                "A relation needs both sets of estimates on the same records "
                "and source households."
            )

    def _groups(
        self,
        child: AreaEstimates,
        parent: AreaEstimates,
        parent_of: Optional[dict[str, str]],
    ) -> dict[str, tuple[list[str], Optional[np.ndarray]]]:
        """For each parent area: its child areas and its records with no child."""
        parents = parent.areas.area_codes
        if not child.areas.one_area_per_record:
            if len(parents) == 1:
                return {parents[0]: (list(child.areas.area_codes), None)}
            if parent_of is None:
                raise DisclosureError(
                    f"Nesting a weight matrix ({child.level}) in {parent.level} "
                    "needs parent_of."
                )
            missing = sorted(set(child.areas.area_codes) - set(parent_of))
            if missing:
                raise DisclosureError(
                    f"parent_of lacks {len(missing)} {child.level} areas."
                )
            return {
                code: (
                    [c for c in child.areas.area_codes if parent_of[c] == code],
                    None,
                )
                for code in parents
            }
        try:
            parent_labels = parent.areas.labels
        except ValueError as error:
            raise DisclosureError(
                f"The parent level {parent.level} must have one area per record."
            ) from error
        child_labels = child.areas.labels
        pairs = pd.DataFrame({"parent": parent_labels, "child": child_labels})
        pairs = pairs[pairs["child"] != ""].drop_duplicates()
        if pairs["child"].duplicated().any():
            raise DisclosureError(
                f"A {child.level} area lies in more than one {parent.level} area."
            )
        if (pairs["parent"] == "").any():
            raise DisclosureError(
                f"A {child.level} area has records outside every {parent.level} area."
            )
        children = pairs.groupby("parent")["child"].apply(list).to_dict()
        loose_weights = child.areas.record_weights([], include_unassigned=True)
        return {
            code: (
                sorted(children.get(code, [])),
                np.where(parent_labels == code, loose_weights, 0.0),
            )
            for code in parents
        }

    def _check_nesting(
        self,
        tiers: dict[tuple[_Key, str], dict[str, str]],
        known: set[tuple[str, str, str, int, str]],
        findings: list[Finding],
    ) -> None:
        for child_level, parent_level, parent_of in self._nestings:
            for key in sorted(self._estimates):
                level, reform, year = key
                if level != child_level or not self._published[key]:
                    continue
                child = self._estimates[key]
                parent_key = (parent_level, reform, year)
                parent = self._estimates.get(parent_key)
                if parent is None:
                    raise DisclosureError(
                        f"Nesting {child_level} in {parent_level} needs "
                        f"{parent_level} estimates for reform {reform!r}, {year}."
                    )
                self._require_same_records(child, parent)
                groups = self._groups(child, parent, parent_of)
                for family in FAMILIES:
                    child_tiers = tiers[(key, family)]
                    sources = child.family_sources(family)
                    for code, (children, loose) in groups.items():
                        hidden = [
                            c
                            for c in children
                            if child_tiers[c] == WITHHELD
                            and (level, c, reform, year, family) not in known
                        ]
                        weights = child.areas.record_weights(hidden)
                        if loose is not None:
                            weights = weights + loose
                        passes, empty = self._passes(child, weights, family)
                        location: dict[str, Any] = {
                            "level": child_level,
                            "reform": reform,
                            "year": year,
                            "family": family,
                            "group": code,
                            "group_level": parent_level,
                        }
                        parent_withheld = (
                            tiers[(parent_key, family)].get(code) == WITHHELD
                            and (parent_level, code, reform, year, family) not in known
                        )
                        if parent_withheld:
                            # There is no public parent to subtract from. The
                            # risk is the reverse: published children that add
                            # up to a parent this release withholds.
                            if empty and self._published[parent_key]:
                                findings.append(
                                    Finding(
                                        code=RECOVERABLE_PARENT,
                                        blocking=True,
                                        relation="nesting",
                                        message=(
                                            f"{parent_level} {code!r} is withheld "
                                            f"but all its {child_level} cells are "
                                            "published, so addition recovers it."
                                        ),
                                        **location,
                                    )
                                )
                            continue
                        if not passes:
                            # Withholding a cell with no contributor adds
                            # nothing to the remainder.
                            shown = [
                                c
                                for c in children
                                if child_tiers[c] != WITHHELD and sources[c] > 0
                            ]
                            findings.append(
                                Finding(
                                    code=RECOVERABLE_REMAINDER,
                                    blocking=True,
                                    relation="nesting",
                                    message=(
                                        f"The withheld {child_level} cells in "
                                        f"{parent_level} {code!r} fail the rules "
                                        "together, so subtraction recovers them. "
                                        "Withhold another cell of the group, or "
                                        "the parent."
                                    ),
                                    members=sorted(hidden),
                                    suggested=min(
                                        shown,
                                        key=lambda c: (sources[c], c),
                                        default=None,
                                    ),
                                    **location,
                                )
                            )

    def _check_packages(
        self,
        tiers: dict[tuple[_Key, str], dict[str, str]],
        known: set[tuple[str, str, str, int, str]],
        findings: list[Finding],
    ) -> None:
        family = FAMILY_CHANGE
        for package, components in self._packages:
            for key in sorted(self._estimates):
                level, reform, year = key
                if reform != package or not self._published[key]:
                    continue
                whole = self._estimates[key]
                parts = []
                for component in components:
                    part_key = (level, component, year)
                    part = self._estimates.get(part_key)
                    if part is None:
                        raise DisclosureError(
                            f"Package {package!r} needs estimates for component "
                            f"{component!r} at {level}, {year}."
                        )
                    self._require_same_records(whole, part)
                    if part.areas.area_codes != whole.areas.area_codes:
                        raise DisclosureError(
                            "A package and its components need the same areas."
                        )
                    parts.append((part_key, part))
                for area in whole.areas.area_codes:
                    hidden = [
                        (part_key, part)
                        for part_key, part in parts
                        if self._published[part_key]
                        and tiers[(part_key, family)][area] == WITHHELD
                        and (level, area, part.reform, year, family) not in known
                    ]
                    whole_hidden = (
                        tiers[(key, family)][area] == WITHHELD
                        and (level, area, package, year, family) not in known
                    )
                    location: dict[str, Any] = {
                        "level": level,
                        "reform": package,
                        "year": year,
                        "family": family,
                        "group": area,
                        "group_level": level,
                    }
                    if whole_hidden and not hidden:
                        findings.append(
                            Finding(
                                code=RECOVERABLE_PARENT,
                                blocking=True,
                                relation="package",
                                message=(
                                    f"Package {package!r} is withheld in {area!r} "
                                    "but all its components are published, so "
                                    "addition recovers it."
                                ),
                                **location,
                            )
                        )
                    elif hidden and not whole_hidden:
                        records, weights = whole.areas.area_records(area)
                        combined = sum(
                            part.contributions[family][records] for _, part in hidden
                        )
                        supports = family_supports(
                            weights, combined, whole.source_index[records], family
                        )
                        tier, _ = cell_tier(
                            supports,
                            self.settings,
                            one_area_per_record=whole.areas.one_area_per_record,
                            noise=whole.noise,
                        )
                        if tier != WITHHELD or supports[0].n_sources == 0:
                            continue
                        shown = [
                            part
                            for part_key, part in parts
                            if tiers[(part_key, family)][area] != WITHHELD
                            and part.family_sources(family)[area] > 0
                        ]
                        findings.append(
                            Finding(
                                code=RECOVERABLE_REMAINDER,
                                blocking=True,
                                relation="package",
                                message=(
                                    f"The withheld components of {package!r} in "
                                    f"{area!r} fail the rules together, so "
                                    "subtraction recovers them. Withhold another "
                                    "component, or the package."
                                ),
                                members=sorted(part.reform for _, part in hidden),
                                suggested=min(
                                    (part.reform for part in shown),
                                    key=lambda name: (
                                        self._estimates[
                                            (level, name, year)
                                        ].family_sources(family)[area],
                                        name,
                                    ),
                                    default=None,
                                ),
                                **location,
                            )
                        )

    def _check_overlap(self, findings: list[Finding]) -> None:
        """Levels published together need a declared relation between them."""
        related: dict[str, set[str]] = {}
        for child_level, parent_level, _ in self._nestings:
            related.setdefault(child_level, set()).add(parent_level)

        def nests(child: str, parent: str) -> bool:
            seen, queue = set(), [child]
            while queue:
                current = queue.pop()
                for above in related.get(current, ()):
                    if above == parent:
                        return True
                    if above not in seen:
                        seen.add(above)
                        queue.append(above)
            return False

        by_run: dict[tuple[str, int], set[str]] = {}
        for (level, reform, year), publish in self._published.items():
            if publish:
                by_run.setdefault((reform, year), set()).add(level)
        pairs = {
            pair
            for levels in by_run.values()
            for pair in combinations(sorted(levels), 2)
            if not nests(*pair) and not nests(*reversed(pair))
        }
        for first, second in sorted(pairs):
            findings.append(
                Finding(
                    code=UNCHECKED_OVERLAP,
                    blocking=UNCHECKED_OVERLAP not in self._acknowledged,
                    relation="release",
                    message=(
                        f"{first} and {second} are published together with no "
                        "declared nesting. Differences between overlapping areas "
                        "are not checked."
                    ),
                    level=f"{first}|{second}",
                )
            )

    def _check_prior(
        self,
        tiers: dict[tuple[_Key, str], dict[str, str]],
        findings: list[Finding],
    ) -> None:
        for prior in self._prior:
            cells: dict[tuple[_Key, str], set[str]] = {}
            for level, area, reform, year, outcome in prior.cells:
                family = OUTCOME_FAMILY.get(outcome)
                key = (level, reform, int(year))
                if family is not None and self._published.get(key):
                    cells.setdefault((key, family), set()).add(area)
            for (key, family), areas in sorted(cells.items()):
                level, reform, year = key
                family_tiers = tiers[(key, family)]
                present = sorted(areas & set(family_tiers))
                withheld = [a for a in present if family_tiers[a] == WITHHELD]
                shown = [a for a in present if family_tiers[a] != WITHHELD]
                location: dict[str, Any] = {
                    "level": level,
                    "reform": reform,
                    "year": year,
                    "family": family,
                    "group": prior.name,
                }
                if withheld:
                    findings.append(
                        Finding(
                            code=ALREADY_PUBLIC,
                            blocking=False,
                            relation="prior_public",
                            message=(
                                f"{prior.name!r} already published cells that "
                                "this release withholds."
                            ),
                            members=withheld,
                            **location,
                        )
                    )
                if shown and prior.noise != self._estimates[key].noise:
                    findings.append(
                        Finding(
                            code=NOISE_REFERENCE_PUBLIC,
                            blocking=NOISE_REFERENCE_PUBLIC not in self._acknowledged,
                            relation="prior_public",
                            message=(
                                f"{prior.name!r} published the same cells with a "
                                "different noise setting. A reader can compare "
                                "the two and learn the noise factors."
                            ),
                            members=shown,
                            **location,
                        )
                    )
