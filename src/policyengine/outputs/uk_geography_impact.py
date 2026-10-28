"""Longwise UK geography impact helpers."""

import logging
import warnings
from pathlib import Path
from typing import Optional

import pandas as pd

from policyengine.data.uk_geography_assets import (
    UK_AREA_LIST_FILES,
    UKGeographyAssetSpec,
    default_download_dir,
    default_local_search_dirs,
    packaged_uk_area_list_path,
)
from policyengine.provenance.manifest import uk_area_dataset_hint

logger = logging.getLogger(__name__)
#: The region type whose dataset carries each longwise area column.
AREA_REGION_TYPES = {
    "constituency_code_oa": "constituency",
    "la_code_oa": "local_authority",
}


def warn_unprotected_uk_geography_output(name: str, level: str) -> None:
    """Warn that an output without disclosure control is deprecated.

    policyengine-core silences Python warnings in every process that loads a
    country model, so the message also goes to the log, which it leaves alone.
    """
    message = (
        f"{name} is deprecated. Its output is not disclosure-controlled, so it "
        "must not be published when the data is licensed survey microdata. Use "
        f"compute_uk_geography_disclosure(levels=({level!r},)) instead."
    )
    logger.warning(message)
    warnings.warn(message, DeprecationWarning, stacklevel=3)


def _normalise_code(value) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, bytes):
        value = value.decode()
    return str(value).strip()


def resolve_uk_geography_lookup_csv_path(
    spec: UKGeographyAssetSpec,
    *,
    lookup_csv_path: Optional[str] = None,
    download_missing_assets: bool = True,
) -> Optional[str]:
    """Resolve a UK geography lookup CSV without requiring a weight matrix.

    An explicit ``lookup_csv_path`` wins. Constituencies and local
    authorities otherwise use the area list shipped with the package, so
    labels never depend on a local file or on the unversioned GCS bucket
    (``download_missing_assets`` then has no effect). Other geography types
    keep the local search and GCS fallback.
    """
    if lookup_csv_path:
        path = Path(lookup_csv_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(
                f"Provided UK geography lookup CSV path does not exist "
                f"or is not a file: {path}"
            )
        return str(path)

    if spec.geography_type in UK_AREA_LIST_FILES:
        return packaged_uk_area_list_path(spec.geography_type)

    for search_dir in default_local_search_dirs():
        path = search_dir / spec.lookup_csv_filename
        if path.is_file():
            return str(path)

    if not download_missing_assets:
        return None

    try:
        from policyengine_core.tools.google_cloud import download_gcs_file
    except ImportError:
        return None

    try:
        target_path = default_download_dir() / spec.lookup_csv_filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return download_gcs_file(
            bucket=spec.resolved_lookup_csv_bucket,
            file_path=spec.lookup_csv_filename,
            local_path=str(target_path),
        )
    except Exception:
        return None


def _load_lookup_metadata(
    lookup_csv_path: Optional[str],
) -> tuple[dict[str, dict], list[str]]:
    """Read each area's name, and the area order, from a lookup CSV.

    Only the ``code`` and ``name`` columns are read; others, such as ``x``
    and ``y``, are ignored.
    """
    if lookup_csv_path is None:
        return {}, []

    lookup_df = pd.read_csv(lookup_csv_path)
    if "code" not in lookup_df.columns:
        raise ValueError(
            f"UK geography lookup CSV must contain a 'code' column: {lookup_csv_path}"
        )

    metadata: dict[str, dict] = {}
    order: list[str] = []
    for _, row in lookup_df.iterrows():
        code = _normalise_code(row["code"])
        if not code:
            continue
        order.append(code)
        metadata[code] = {
            "name": _normalise_code(row["name"])
            if "name" in lookup_df.columns
            else code,
        }
    return metadata, order


def compute_longwise_uk_geography_impacts(
    *,
    baseline_household: pd.DataFrame,
    reform_household: pd.DataFrame,
    geography_column: str,
    result_key_prefix: str,
    lookup_csv_path: Optional[str] = None,
) -> list[dict]:
    """Compute UK geography impacts by grouping household rows."""
    for column in [
        geography_column,
        "household_net_income",
        "household_weight",
    ]:
        if column not in baseline_household.columns:
            hint = uk_area_dataset_hint(AREA_REGION_TYPES.get(column, ""))
            raise ValueError(
                f"UK geography impacts require baseline household column "
                f"'{column}'. Re-run the simulation with an output dataset "
                f"that preserves UK geography passthrough columns."
                + (f" {hint}" if hint else "")
            )
    if "household_net_income" not in reform_household.columns:
        raise ValueError(
            "UK geography impacts require reform household column "
            "'household_net_income'."
        )
    if len(baseline_household) != len(reform_household):
        raise ValueError(
            "Baseline and reform household outputs must have the same row "
            "count for longwise UK geography impacts."
        )

    metadata, lookup_order = _load_lookup_metadata(lookup_csv_path)
    codes = (
        pd.Series(baseline_household[geography_column]).map(_normalise_code).to_numpy()
    )
    present_codes = {code for code in pd.unique(codes) if code}
    ordered_codes = [code for code in lookup_order if code in present_codes] + sorted(
        present_codes - set(lookup_order)
    )

    baseline_income = baseline_household["household_net_income"].to_numpy(dtype=float)
    reform_income = reform_household["household_net_income"].to_numpy(dtype=float)
    weights = baseline_household["household_weight"].to_numpy(dtype=float)

    results: list[dict] = []
    for code in ordered_codes:
        mask = codes == code
        w = weights[mask]
        total_weight = float(w.sum())
        if total_weight == 0:
            continue

        baseline_weighted = float((baseline_income[mask] * w).sum())
        reform_weighted = float((reform_income[mask] * w).sum())

        avg_change = (reform_weighted - baseline_weighted) / total_weight
        rel_change = (
            (reform_weighted / baseline_weighted - 1.0)
            if baseline_weighted != 0
            else 0.0
        )
        row_metadata = metadata.get(code, {})

        results.append(
            {
                f"{result_key_prefix}_code": code,
                f"{result_key_prefix}_name": row_metadata.get("name", code),
                "average_household_income_change": float(avg_change),
                "relative_household_income_change": float(rel_change),
                "population": total_weight,
            }
        )

    return results
