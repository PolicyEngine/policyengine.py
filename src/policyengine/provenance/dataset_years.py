"""The years a country model supports a single-year dataset for.

A supported year is one the installed country model projects its single-year
dataset to. The model's own ``Simulation`` builds that projection from a
single-year file with ``extend_single_year_dataset``; :func:`supported_years`
builds it the same way, without running any formula, and keeps the years from
the dataset's data year onwards.

A calculation for another year still succeeds: policyengine-core fills a year
outside the projection by carrying the latest projected inputs forward or
uprating them. A result there is therefore not evidence that its year is
supported, and ``create_datasets`` and ``ensure_datasets`` refuse such a year
with :class:`UnsupportedDatasetYearError` unless asked not to.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Union

COUNTRY_IDS = ("uk", "us")

#: Years the US rule supports although they come before the data year of the
#: certified ``populace_us_2024``. The certified dataset holds almost no data
#: for them: its household weights sum to 57,240 in each of 2022 and 2023,
#: against 122,537,088 in 2024, and employment income is zero. They stay
#: supported (not provisional) by a decision of 2026-10-28 and 2026-10-30
#: (PolicyEngine/policyengine.py#729). Removing them is a change to this
#: constant alone.
US_EARLY_YEAR_ALLOWANCE: frozenset[int] = frozenset({2022, 2023})


class UnsupportedDatasetYearError(ValueError):
    """Requested years are outside the years a dataset is supported for.

    Attributes:
        country_id: The country, ``"uk"`` or ``"us"``.
        dataset: The dataset the years were requested for, as requested.
        years: The requested years that are not supported, sorted.
        supported_years: Every year the dataset is supported for, sorted.
    """

    def __init__(
        self,
        country_id: str,
        dataset: str,
        years: Iterable[int],
        supported_years: Iterable[int],
    ):
        self.country_id = country_id
        self.dataset = dataset
        self.years = sorted({int(year) for year in years})
        self.supported_years = sorted({int(year) for year in supported_years})
        super().__init__(self._message())

    def __reduce__(self) -> tuple[Any, ...]:
        # The default reduction passes only the message back to __init__.
        return (
            type(self),
            (self.country_id, self.dataset, self.years, self.supported_years),
        )

    def _message(self) -> str:
        noun = "year" if len(self.years) == 1 else "years"
        requested = ", ".join(str(year) for year in self.years)
        return (
            f"{self.country_id.upper()} dataset {self.dataset!r} is not supported "
            f"for {noun} {requested}. Supported years: "
            f"{_describe_years(self.supported_years)}. The installed model "
            "projects the dataset only to its supported years; policyengine-core "
            "would fill any other year by carrying the latest projected inputs "
            "forward or uprating them. Pass allow_unsupported_years=True to "
            "create year files for it anyway."
        )


def supported_years(country_id: str, dataset_path: Union[str, Path]) -> list[int]:
    """Return the years the installed country model supports a dataset for.

    ``dataset_path`` is a local single-year dataset file, such as the
    certified source that ``create_datasets`` creates year files from. The
    multi-year dataset is built as the country model's own ``Simulation``
    builds it for a single-year file, with the model's
    ``extend_single_year_dataset`` and its default projection end, and
    without running any formula. The years it holds from the dataset's data
    year onwards are supported, with these country rules:

    - **UK:** policyengine-uk projects to ``PROJECTION_END_YEAR``, or to the
      last year of a capital gains projection that ends earlier.
    - **US:** policyengine-us projects to the last year in its
      ``gov.bls.cpi.cpi_u`` parameter file. Years after the last year of
      spm-calculator's SPM forecast are not supported, since the poverty
      figures have no thresholds there. :data:`US_EARLY_YEAR_ALLOWANCE` adds
      2022 and 2023.

    Args:
        country_id: ``"uk"`` or ``"us"``.
        dataset_path: Path of the single-year dataset file.

    Returns:
        The supported years, sorted ascending without duplicates.
    """

    if country_id == "uk":
        return _uk_supported_years(Path(dataset_path))
    if country_id == "us":
        return _us_supported_years(Path(dataset_path))
    raise ValueError(
        f"Unknown country {country_id!r}; expected one of {list(COUNTRY_IDS)}."
    )


def refuse_unsupported_years(
    country_id: str,
    dataset: str,
    dataset_path: Union[str, Path],
    years: Iterable[int],
) -> None:
    """Raise :class:`UnsupportedDatasetYearError` if a year is not supported.

    The supported years are computed from ``dataset_path`` only when ``years``
    holds at least one year.

    Args:
        country_id: ``"uk"`` or ``"us"``.
        dataset: The dataset as requested, named in the error.
        dataset_path: Path of the single-year dataset file.
        years: The requested years.
    """

    requested = sorted({int(year) for year in years})
    if not requested:
        return
    supported = supported_years(country_id, dataset_path)
    unsupported = [year for year in requested if year not in supported]
    if unsupported:
        raise UnsupportedDatasetYearError(country_id, dataset, unsupported, supported)


def _uk_supported_years(dataset_path: Path) -> list[int]:
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset
    from policyengine_uk.data.economic_assumptions import extend_single_year_dataset
    from policyengine_uk.system import system

    dataset = UKSingleYearDataset(str(dataset_path))
    data_year = _data_year(dataset)
    multi_year_dataset = extend_single_year_dataset(dataset, system.parameters)
    return sorted(
        year for year in _projected_years(multi_year_dataset) if year >= data_year
    )


def _us_supported_years(dataset_path: Path) -> list[int]:
    from policyengine_us.data.dataset_schema import USSingleYearDataset
    from policyengine_us.data.economic_assumptions import extend_single_year_dataset
    from spm_calculator.rolling_forecast import load_forecast

    dataset = USSingleYearDataset(file_path=str(dataset_path))
    data_year = _data_year(dataset)
    multi_year_dataset = extend_single_year_dataset(dataset)
    last_spm_forecast_year = max(int(year) for year in load_forecast().years)
    projected = {
        year
        for year in _projected_years(multi_year_dataset)
        if data_year <= year <= last_spm_forecast_year
    }
    return sorted(projected | US_EARLY_YEAR_ALLOWANCE)


def _data_year(dataset: Any) -> int:
    """The year of a single-year dataset's observed data."""

    return int(str(dataset.time_period)[:4])


def _projected_years(multi_year_dataset: Any) -> set[int]:
    """The years a country model's multi-year dataset holds."""

    years = getattr(multi_year_dataset, "years", None)
    if years is None:
        years = list(multi_year_dataset.datasets)
    return {int(year) for year in years}


def _describe_years(years: list[int]) -> str:
    """Sorted years as runs of consecutive years, such as ``2022–2035``."""

    if not years:
        return "none"
    runs: list[list[int]] = [[years[0], years[0]]]
    for year in years[1:]:
        if year == runs[-1][1] + 1:
            runs[-1][1] = year
        else:
            runs.append([year, year])
    return ", ".join(
        str(first) if first == last else f"{first}–{last}" for first, last in runs
    )
