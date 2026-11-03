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

Certification records the certified dataset's supported years in the bundle
manifest (:func:`recorded_supported_years`), computed with exactly the pinned
packages (:func:`supported_years_in_environment`). Requests for that dataset
are checked against the record without reading any file
(:func:`refuse_years_outside_record`); other datasets are checked by computing
their years from the source (:func:`refuse_unsupported_years`).
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Optional, Union

COUNTRY_IDS = ("uk", "us")


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
      figures have no thresholds there. Years before the data year are not
      supported either, although the SPM forecast covers 2022 and 2023: the
      certified ``populace_us_2024`` holds almost no data for them (its
      household weights sum to 57,240 in each of 2022 and 2023, against
      122,537,088 in 2024, and employment income is zero).

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


def recorded_supported_years(
    country_id: str, dataset: Optional[str] = None
) -> Optional[list[int]]:
    """Return the supported years the bundle manifest records for a dataset.

    Certification records them for the certified dataset only, on
    ``data_releases.<country>.certified_data_artifact.supported_years``.
    ``dataset`` covers it when it is ``None`` (the certified default), the
    default dataset's name, or its certified URI, and the bundle serves that
    name with the certified bytes (the same ``sha256``).

    Args:
        country_id: ``"uk"`` or ``"us"``.
        dataset: The dataset as requested from ``create_datasets`` or
            ``ensure_datasets``.

    Returns:
        The recorded years, sorted ascending, or ``None`` when the manifest
        records none for ``dataset``: another dataset, a local file, or a
        certificate from before the record existed.
    """

    # Imported here: the certification environment loads this module by path,
    # without the rest of policyengine (see supported_years_in_environment).
    from policyengine.provenance import manifest as bundle_manifest

    country_manifest = bundle_manifest.get_release_manifest(country_id)
    certified = country_manifest.certified_data_artifact
    if certified is None or certified.supported_years is None:
        return None
    if certified.dataset != country_manifest.default_dataset:
        return None
    if dataset is not None and dataset not in (
        country_manifest.default_dataset,
        country_manifest.default_dataset_uri,
    ):
        return None
    served = country_manifest.datasets.get(certified.dataset)
    if served is None or certified.sha256 is None or served.sha256 != certified.sha256:
        return None
    return list(certified.supported_years)


def refuse_years_outside_record(
    country_id: str, dataset: Optional[str], years: Iterable[int]
) -> bool:
    """Check requested years against the years the bundle manifest records.

    Reads only the bundle manifest, never a dataset file, so it runs before
    any download and before year files that already exist are reused.

    Args:
        country_id: ``"uk"`` or ``"us"``.
        dataset: The dataset as requested; ``None`` is the certified default.
        years: The requested years.

    Returns:
        ``True`` when the manifest records supported years for ``dataset``
        and every requested year is among them. ``False`` when it records
        none for ``dataset``: the caller then computes them from the source
        with :func:`refuse_unsupported_years`.

    Raises:
        UnsupportedDatasetYearError: The manifest records supported years for
            ``dataset`` and a requested year is not among them.
    """

    recorded = recorded_supported_years(country_id, dataset)
    if recorded is None:
        return False
    requested = sorted({int(year) for year in years})
    unsupported = [year for year in requested if year not in recorded]
    if unsupported:
        from policyengine.provenance import manifest as bundle_manifest

        requested_dataset = (
            dataset or bundle_manifest.get_release_manifest(country_id).default_dataset
        )
        raise UnsupportedDatasetYearError(
            country_id, requested_dataset, unsupported, recorded
        )
    return True


class SupportedYearsEnvironmentError(ValueError):
    """The supported years could not be computed with the exact packages."""


#: Runs in the environment of :func:`supported_years_in_environment`: loads
#: this file by path, so nothing of policyengine but the rule is imported, and
#: prints the versions it imported with the years.
SUPPORTED_YEARS_PROBE = """
import importlib.util
import json
import sys
from importlib.metadata import version

module_path, country_id, dataset_path, *package_names = sys.argv[1:]
specification = importlib.util.spec_from_file_location(
    "_policyengine_dataset_years", module_path
)
dataset_years = importlib.util.module_from_spec(specification)
specification.loader.exec_module(dataset_years)
print(json.dumps({
    "package_versions": {name: version(name) for name in package_names},
    "supported_years": dataset_years.supported_years(country_id, dataset_path),
}))
"""


def supported_years_in_environment(
    country_id: str,
    dataset_path: Union[str, Path],
    packages: Mapping[str, str],
    *,
    run: Optional[Callable[..., Any]] = None,
) -> list[int]:
    """Compute :func:`supported_years` with exactly the given package versions.

    ``uv run --isolated --no-project --no-config`` installs exactly
    ``packages`` from PyPI into a fresh environment, without the caller's uv
    settings, project or environment, and runs this module's rule there. The
    result therefore does not depend on what the caller has installed.
    Certification uses it, since a candidate pair is certified from an
    environment that still holds the previous model.

    Args:
        country_id: ``"uk"`` or ``"us"``.
        dataset_path: Path of the single-year dataset file.
        packages: Distribution names and exact versions to install, such as
            ``{"policyengine-us": "2.2.1", "policyengine-core": "3.33.3",
            "spm-calculator": "1.0.0"}``.
        run: Stands in for :func:`subprocess.run` in tests.

    Returns:
        The supported years, sorted ascending without duplicates.

    Raises:
        SupportedYearsEnvironmentError: uv failed, the environment imported
            other versions, or the rule printed no well-formed years.
    """

    # Imported here so that loading this module by path stays import-free.
    from policyengine.provenance.bundle_validation import supported_years_problem
    from policyengine.provenance.regional_input_surface import (
        BUILD_MODEL_INDEX,
        BUILD_MODEL_KEPT_UV_SETTINGS,
        BUILD_MODEL_PYTHON,
    )

    run = run if run is not None else subprocess.run
    package_names = sorted(packages)
    label = ", ".join(f"{name} {packages[name]}" for name in package_names)
    command = [
        "uv",
        "run",
        "--isolated",
        "--no-project",
        "--no-config",
        "--default-index",
        BUILD_MODEL_INDEX,
        "--python",
        BUILD_MODEL_PYTHON,
    ]
    for name in package_names:
        command.extend(["--with", f"{name}=={packages[name]}"])
    command.extend(
        [
            "python",
            "-I",
            "-c",
            SUPPORTED_YEARS_PROBE,
            str(Path(__file__).resolve()),
            country_id,
            str(dataset_path),
            *package_names,
        ]
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if key != "VIRTUAL_ENV"
        and (not key.startswith("UV_") or key in BUILD_MODEL_KEPT_UV_SETTINGS)
    }
    try:
        result = run(
            command, capture_output=True, text=True, check=True, env=environment
        )
    except subprocess.CalledProcessError as exc:
        detail = " | ".join((exc.stderr or "").strip().splitlines()[-5:])
        raise SupportedYearsEnvironmentError(
            f"Cannot compute the supported years with {label}: {detail or exc}"
        ) from exc
    except OSError as exc:
        raise SupportedYearsEnvironmentError(
            f"Cannot run uv to compute the supported years with {label}."
        ) from exc
    try:
        printed = json.loads((result.stdout or "").strip().splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise SupportedYearsEnvironmentError(
            f"The environment with {label} printed no supported years."
        ) from exc
    if not isinstance(printed, dict):
        raise SupportedYearsEnvironmentError(
            f"The environment with {label} printed no supported years."
        )
    resolved = printed.get("package_versions")
    if resolved != dict(packages):
        raise SupportedYearsEnvironmentError(
            f"The environment imported {resolved}, not {label}."
        )
    years: Any = printed.get("supported_years")
    problem = supported_years_problem(years)
    if problem is not None:
        raise SupportedYearsEnvironmentError(
            f"The supported years computed with {label} {problem}: {years!r}."
        )
    return list(years)


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
    return sorted(
        year
        for year in _projected_years(multi_year_dataset)
        if data_year <= year <= last_spm_forecast_year
    )


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
    """Sorted years as runs of consecutive years, such as ``2024–2035``."""

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
