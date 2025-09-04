from __future__ import annotations

import argparse
import os
from typing import Any, Iterable

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
except Exception:  # rich not installed – gracefully degrade
    Console = None  # type: ignore
    Progress = None  # type: ignore

from policyengine.database import Database


def _console() -> Any:
    return Console() if Console is not None else None


def _log(msg: str) -> None:
    c = _console()
    if c is not None:
        c.print(msg)
    else:
        print(msg)


def seed_model(db: Database, country: str) -> dict[str, int]:
    """Seed variables, parameters, and parameter values for a country.

    Uses the installed policyengine_{country} package to derive the metadata.
    Returns counts for a quick summary.
    """
    country = country.lower()
    # Announce early to avoid long silence during heavy imports/metadata build
    _log(f"[migrate] Loading {country.upper()} model metadata...")

    # Wrap metadata build with a spinner if rich is available
    if Progress is not None:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        )
        progress.start()
        task_md = progress.add_task(
            "Building metadata from installed package...", total=None
        )
        try:
            if country == "uk":
                from policyengine.countries.uk.metadata import (
                    get_uk_metadata as get_md,
                )
            elif country == "us":
                from policyengine.countries.us.metadata import (
                    get_us_metadata as get_md,
                )
            else:
                raise SystemExit(f"Unknown country: {country}")
            md = get_md()
        finally:
            progress.update(task_md, completed=1)
            progress.stop()
    else:
        if country == "uk":
            from policyengine.countries.uk.metadata import (
                get_uk_metadata as get_md,
            )
        elif country == "us":
            from policyengine.countries.us.metadata import (
                get_us_metadata as get_md,
            )
        else:
            raise SystemExit(f"Unknown country: {country}")
        md = get_md()

    # Compute counts up-front
    var_count = len(md.get("variables", []) or [])
    pvals = list(md.get("parameter_values", []) or [])
    pval_count = len(pvals)
    unique_params: dict[tuple[str, str | None], Any] = {}
    for pv in pvals:
        if pv.parameter is not None:
            keyp = (pv.parameter.name, country)
            if keyp not in unique_params:
                unique_params[keyp] = pv.parameter
    par_count = len(unique_params)

    # Attach country and persist
    # Anchor policy/dynamics
    anchors = []
    if md.get("current_law") is not None:
        md["current_law"].country = country
        anchors.append(md["current_law"])
    if md.get("static") is not None:
        md["static"].country = country
        anchors.append(md["static"])

    # Progress UI
    if Progress is not None:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        )
        progress.start()
        if anchors:
            task_anchors = progress.add_task("Saving anchors...", total=None)
            db.add_all(anchors, refresh=False)
            progress.update(task_anchors, completed=1)
        if var_count:
            task_vars = progress.add_task(
                f"Saving variables ({var_count})...", total=None
            )
            variables = []
            for v in md.get("variables", []) or []:
                v.country = country
                variables.append(v)
            if variables:
                db.add_all(variables, refresh=False)
            progress.update(task_vars, completed=1)
        if par_count:
            task_params = progress.add_task(
                f"Saving parameters ({par_count})...", total=None
            )
            for p in unique_params.values():
                p.country = country
            if unique_params:
                db.add_all(
                    unique_params.values(), refresh=False, chunk_size=1000
                )
            progress.update(task_params, completed=1)
        if pval_count:
            task_pvals = progress.add_task(
                f"Saving parameter values (~{pval_count})...", total=None
            )
            # Ensure country set on values and referenced params
            prepared = []
            for pv in pvals:
                pv.country = country
                if pv.parameter is not None:
                    pv.parameter.country = country
                prepared.append(pv)
            if prepared:
                db.add_parameter_values_bulk(
                    prepared,
                    cascade=False,
                    chunk_size=2000,
                    progress=True,  # internal tqdm, complements rich step status
                    verbose=True,
                    replace=False,
                )
            progress.update(task_pvals, completed=1)
        progress.stop()
    else:
        # Plain output fallback
        if anchors:
            _log("Saving anchors...")
            db.add_all(anchors, refresh=False)
        if var_count:
            _log(f"Saving variables ({var_count})...")
            variables = []
            for v in md.get("variables", []) or []:
                v.country = country
                variables.append(v)
            if variables:
                db.add_all(variables, refresh=False)
        if par_count:
            _log(f"Saving parameters ({par_count})...")
            for p in unique_params.values():
                p.country = country
            if unique_params:
                db.add_all(
                    unique_params.values(), refresh=False, chunk_size=1000
                )
        if pval_count:
            _log(f"Saving parameter values (~{pval_count})...")
            prepared = []
            for pv in pvals:
                pv.country = country
                if pv.parameter is not None:
                    pv.parameter.country = country
                prepared.append(pv)
            if prepared:
                db.add_parameter_values_bulk(
                    prepared,
                    cascade=False,
                    chunk_size=2000,
                    progress=True,
                    verbose=True,
                    replace=False,
                )

    return {
        "variables": var_count,
        "parameters": par_count,
        "parameter_values": pval_count,
    }


def seed_datasets(
    db: Database,
    country: str,
    *,
    family: str,
    version: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> int:
    """Seed dataset rows for a country and family, tagging with an optional version string.

    Defaults mirror your current helpers' ranges if years are not provided.
    Returns the number of inserted/updated dataset rows.
    """
    country = country.lower()
    family = family.lower()

    # Announce early to avoid silence during imports/build
    _log(
        f"[migrate] Preparing datasets for {country.upper()} family '{family}'..."
    )

    datasets: Iterable[Any]
    # Build with spinner when available
    if Progress is not None:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        )
        progress.start()
        task_build = progress.add_task("Building dataset rows...", total=None)
        try:
            if country == "uk" and family == "efrs":
                from policyengine.countries.uk.metadata import get_uk_datasets

                s = start_year if start_year is not None else 2023
                e = end_year if end_year is not None else 2030
                datasets = get_uk_datasets(s, e)
            elif country == "us" and family == "ecps":
                from policyengine.countries.us.metadata import get_us_datasets

                s = start_year if start_year is not None else 2024
                e = end_year if end_year is not None else 2035
                datasets = get_us_datasets(s, e)
            else:
                raise SystemExit(
                    f"Unknown dataset family for {country}: {family}"
                )
        finally:
            progress.update(task_build, completed=1)
            progress.stop()
    else:
        if country == "uk" and family == "efrs":
            from policyengine.countries.uk.metadata import get_uk_datasets

            s = start_year if start_year is not None else 2023
            e = end_year if end_year is not None else 2030
            datasets = get_uk_datasets(s, e)
        elif country == "us" and family == "ecps":
            from policyengine.countries.us.metadata import get_us_datasets

            s = start_year if start_year is not None else 2024
            e = end_year if end_year is not None else 2035
            datasets = get_us_datasets(s, e)
        else:
            raise SystemExit(f"Unknown dataset family for {country}: {family}")

    ds_list = list(datasets)
    for ds in ds_list:
        if version is not None:
            try:
                ds.version = version  # type: ignore[attr-defined]
            except Exception:
                pass

    if Progress is not None:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        )
        progress.start()
        task = progress.add_task(
            f"Saving datasets ({len(ds_list)})...", total=None
        )
        if ds_list:
            db.add_all(ds_list, refresh=False)
        progress.update(task, completed=1)
        progress.stop()
    else:
        _log(f"Saving datasets ({len(ds_list)})...")
        if ds_list:
            db.add_all(ds_list, refresh=False)

    return len(ds_list)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="PolicyEngine migrations runner"
    )
    parser.add_argument(
        "--db",
        dest="db_url",
        default=os.getenv("DATABASE_URL", "sqlite:///policyengine.db"),
        help="Database URL (default: env DATABASE_URL or local sqlite)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # seed-model
    p_model = sub.add_parser(
        "seed-model",
        help="Seed a country model (variables, parameters, values)",
    )
    p_model.add_argument("country", choices=["uk", "us"], help="Country code")

    # seed-datasets
    p_ds = sub.add_parser(
        "seed-datasets", help="Seed datasets for a country/family"
    )
    p_ds.add_argument("country", choices=["uk", "us"], help="Country code")
    p_ds.add_argument("family", help="Dataset family (e.g., efrs, ecps)")
    p_ds.add_argument(
        "--version",
        dest="version",
        default=None,
        help="Dataset version label to store on rows",
    )
    p_ds.add_argument(
        "--start",
        dest="start_year",
        type=int,
        default=None,
        help="Start year (optional)",
    )
    p_ds.add_argument(
        "--end",
        dest="end_year",
        type=int,
        default=None,
        help="End year (optional)",
    )

    # reset
    p_reset = sub.add_parser(
        "reset", help="Drop and recreate all tables (DESTROYS DATA)"
    )
    p_reset.add_argument(
        "-y",
        "--yes",
        dest="yes",
        action="store_true",
        help="Do not prompt for confirmation",
    )

    args = parser.parse_args(argv)

    db = Database(url=args.db_url)

    if args.cmd == "seed-model":
        _log(f"[migrate] Seeding model for {args.country}...")
        counts = seed_model(db, args.country)
        _log(
            f"[done] variables={counts['variables']} parameters={counts['parameters']} values≈{counts['parameter_values']}"
        )
        return

    if args.cmd == "seed-datasets":
        _log(
            f"[migrate] Seeding datasets for {args.country}:{args.family} (version={args.version or '-'})."
        )
        n = seed_datasets(
            db,
            args.country,
            family=args.family,
            version=args.version,
            start_year=args.start_year,
            end_year=args.end_year,
        )
        _log(f"[done] datasets={n}")
        return

    if args.cmd == "reset":
        if not getattr(args, "yes", False):
            try:
                confirm = input(
                    "This will DELETE ALL data and recreate tables. Type 'yes' to proceed: "
                ).strip()
            except EOFError:
                confirm = ""
            if confirm.lower() != "yes":
                _log("Aborted.")
                return
        _log("[migrate] Resetting database (drop + create all tables)...")
        db.reset()
        _log("[done] Database reset complete.")
        return


if __name__ == "__main__":
    main()
