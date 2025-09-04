from __future__ import annotations

import argparse
import os
import json
from pathlib import Path
from urllib import request, error
from typing import Any, Iterable

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
except Exception:  # rich not installed – gracefully degrade
    Console = None  # type: ignore
    Progress = None  # type: ignore

from policyengine.database import Database


def _prompt_select(prompt: str, choices: list[str]) -> str:
    """Prompt user to select from choices. Falls back to text input.

    Returns the selected value from `choices`.
    """
    try:
        from rich.prompt import Prompt

        return str(Prompt.ask(prompt, choices=choices))
    except Exception:
        # Fallback: numeric menu
        while True:
            _log(f"{prompt}:")
            for i, ch in enumerate(choices, start=1):
                _log(f"  {i}. {ch}")
            try:
                sel = input("Enter number: ").strip()
            except EOFError:
                sel = ""
            if sel.isdigit():
                idx = int(sel) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
            _log("Invalid selection, try again.")


def _hf_list_tags(repo: str, *, repo_type: str = "datasets") -> list[str]:
    """Return tag names for a Hugging Face repo using the public API.

    Uses HUGGING_FACE_TOKEN if present for private repos.
    """
    base = f"https://huggingface.co/api/{repo_type}/{repo}/refs?type=tag"
    req = request.Request(base)
    token = os.getenv("HUGGING_FACE_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        _log(f"[error] Failed to fetch tags: HTTP {e.code}")
        return []
    except Exception as e:  # network/parse
        _log(f"[error] Failed to fetch tags: {e}")
        return []

    tags: list[str] = []
    # API sometimes returns { tags: [{name:..}] } or { refs: { tags: [...] } }
    if isinstance(data, dict):
        if isinstance(data.get("tags"), list):
            tags = [t.get("name") for t in data.get("tags", []) if t.get("name")]
        elif isinstance(data.get("refs"), dict) and isinstance(
            data["refs"].get("tags"), list
        ):
            tags = [
                t.get("name") for t in data["refs"].get("tags", []) if t.get("name")
            ]
        elif isinstance(data.get("refs"), list):
            tags = [
                r.get("name")
                for r in data.get("refs", [])
                if r and r.get("name") and r.get("type") == "tag"
            ]
    # Sort newest-like first if semantic versions, otherwise lexicographic desc
    tags = [t for t in tags if isinstance(t, str)]
    try:
        # Attempt to sort by version (vX.Y.Z) fallback to lexicographic
        from packaging.version import Version  # type: ignore

        tags.sort(key=lambda t: Version(t.lstrip("v")), reverse=True)
    except Exception:
        tags.sort(reverse=True)
    return tags


def _console() -> Any:
    return Console() if Console is not None else None


def _log(msg: str) -> None:
    c = _console()
    if c is not None:
        c.print(msg)
    else:
        print(msg)


def _load_env_file() -> None:
    """Load environment variables from a local .env file if present.

    Simple parser: lines of KEY=VALUE, ignores comments and blanks.
    Does not overwrite existing environment variables.
    """
    try:
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        # Non-fatal if .env cannot be read
        pass


def _policyengine_db_url() -> str:
    """Construct the PolicyEngine live DB URL using password from env.

    Requires `POLICYENGINE_DB_PASSWORD` to be set in the environment or .env.
    """
    pwd = os.getenv("POLICYENGINE_DB_PASSWORD")
    if not pwd:
        raise SystemExit(
            "POLICYENGINE_DB_PASSWORD is not set. Add it to your .env."
        )
    # Fixed connection parameters (no password embedded here)
    user = os.getenv("POLICYENGINE_DB_USER", "postgres")
    host = os.getenv(
        "POLICYENGINE_DB_HOST", "db.usugnrssspkdutcjeevk.supabase.co"
    )
    port = int(os.getenv("POLICYENGINE_DB_PORT", "5432"))
    dbname = os.getenv("POLICYENGINE_DB_NAME", "postgres")
    sslmode = os.getenv("POLICYENGINE_DB_SSLMODE", "")
    # Match the expected DSN shape exactly; add sslmode only if provided
    dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"
    if sslmode:
        dsn = f"{dsn}?sslmode={sslmode}"
    return dsn


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
        default=None,
        help="Explicit database URL (overrides --db-location)",
    )
    parser.add_argument(
        "--db-location",
        dest="db_location",
        choices=["local", "policyengine"],
        default=None,
        help="Shortcut for selecting the DB: local sqlite or PolicyEngine live DB",
    )

    sub = parser.add_subparsers(dest="cmd", required=False)

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

    # seed-datasets-hf (interactive)
    p_hf = sub.add_parser(
        "seed-datasets-hf",
        help="Interactively seed datasets from a Hugging Face repo",
    )
    p_hf.add_argument("--country", choices=["uk", "us"], default=None)
    p_hf.add_argument(
        "--family",
        choices=["efrs", "ecps"],
        default=None,
        help="Dataset family (efrs/ecps)",
    )
    p_hf.add_argument("--start", dest="start_year", type=int, default=None)
    p_hf.add_argument("--end", dest="end_year", type=int, default=None)

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

    # No explicit wizard subcommand; running without subcommand triggers wizard

    args = parser.parse_args(argv)

    # Load .env early so DB/password and tokens are available
    _load_env_file()

    # Resolve database URL (prompt if running interactively without a subcommand)
    db_url: str | None = args.db_url
    if db_url is None:
        if args.db_location == "policyengine":
            db_url = _policyengine_db_url()
        elif args.db_location == "local":
            db_url = os.getenv("DATABASE_URL", "sqlite:///policyengine.db")
        elif args.cmd is None:
            # Interactive selection for DB location
            choice = _prompt_select("Select database", ["local", "policyengine"])
            if choice == "policyengine":
                db_url = _policyengine_db_url()
            else:
                db_url = os.getenv("DATABASE_URL", "sqlite:///policyengine.db")
        else:
            # Default to env DATABASE_URL or local sqlite
            db_url = os.getenv("DATABASE_URL", "sqlite:///policyengine.db")
    db = Database(url=db_url)

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

    if args.cmd == "seed-datasets-hf":
        # Interactive selection flow
        country = getattr(args, "country", None) or _prompt_select(
            "Select country", ["uk", "us"]
        )
        if country == "uk":
            families = ["efrs"]
        elif country == "us":
            families = ["ecps"]
        else:
            raise SystemExit(f"Unknown country: {country}")

        family = getattr(args, "family", None) or _prompt_select(
            "Select dataset family", families
        )

        if country == "uk" and family == "efrs":
            from policyengine.countries.uk.datasets import (
                UK_HUGGING_FACE_REPO as REPO,
                UK_HUGGING_FACE_FILENAMES as FILES,
                create_efrs_years_from_hf as build_years,
            )
        elif country == "us" and family == "ecps":
            from policyengine.countries.us.datasets import (
                US_HUGGING_FACE_REPO as REPO,
                US_HUGGING_FACE_DATASETS as FILES,
                create_ecps_years_from_hf as build_years,
            )
        else:
            raise SystemExit(f"Unknown dataset family for {country}: {family}")

        # Choose base file
        filename = FILES[0] if len(FILES) == 1 else _prompt_select(
            "Select base dataset file", list(FILES)
        )

        # Fetch and choose tag
        _log(f"[migrate] Fetching tags from {REPO}...")
        tags = _hf_list_tags(REPO, repo_type="datasets")
        if not tags:
            raise SystemExit("No tags found or access denied to the repo.")
        version = _prompt_select("Select dataset version (git tag)", tags)

        # Year range (defaults consistent with non-HF path)
        if country == "uk":
            default_start, default_end = 2023, 2030
        else:
            default_start, default_end = 2024, 2035

        start_year = getattr(args, "start_year", None)
        end_year = getattr(args, "end_year", None)

        try:
            from rich.prompt import IntPrompt  # type: ignore

            if start_year is None:
                start_year = int(
                    IntPrompt.ask("Start year", default=str(default_start))
                )
            if end_year is None:
                end_year = int(
                    IntPrompt.ask("End year", default=str(default_end))
                )
        except Exception:
            # Fallback via input()
            if start_year is None:
                try:
                    start_year = int(
                        input(f"Start year [{default_start}]: ").strip()
                        or default_start
                    )
                except Exception:
                    start_year = default_start
            if end_year is None:
                try:
                    end_year = int(
                        input(f"End year [{default_end}]: ").strip()
                        or default_end
                    )
                except Exception:
                    end_year = default_end

        _log(
            f"[migrate] Seeding {country}:{family} from HF tag '{version}' years {start_year}-{end_year}..."
        )

        # Build
        datasets = build_years(
            start_year,
            end_year,
            repo=REPO,
            filename=filename,
            version=version,
        )
        ds_list = list(datasets)
        for ds in ds_list:
            try:
                ds.version = version  # type: ignore[attr-defined]
            except Exception:
                pass

        # Save with progress UI when available
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

        _log(f"[done] datasets={len(ds_list)}")
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

    # Automatic interactive wizard when no subcommand provided
    if args.cmd is None:
        action = _prompt_select(
            "Choose action",
            ["seed-model", "seed-datasets", "seed-datasets-hf", "reset"],
        )

        if action == "seed-model":
            country = _prompt_select("Select country", ["uk", "us"])
            _log(f"[migrate] Seeding model for {country}...")
            counts = seed_model(db, country)
            _log(
                f"[done] variables={counts['variables']} parameters={counts['parameters']} values≈{counts['parameter_values']}"
            )
            return

        if action == "seed-datasets":
            country = _prompt_select("Select country", ["uk", "us"])
            families = ["efrs"] if country == "uk" else ["ecps"]
            family = _prompt_select("Select dataset family", families)

            # Optional version label
            try:
                from rich.prompt import Prompt  # type: ignore

                version = Prompt.ask(
                    "Version label (optional)", default="", show_default=False
                ).strip()
            except Exception:
                try:
                    version = input("Version label (optional): ").strip()
                except EOFError:
                    version = ""
            version = version or None

            # Year range defaults
            if country == "uk":
                default_start, default_end = 2023, 2030
            else:
                default_start, default_end = 2024, 2035
            try:
                from rich.prompt import IntPrompt  # type: ignore

                start_year = int(
                    IntPrompt.ask("Start year", default=str(default_start))
                )
                end_year = int(
                    IntPrompt.ask("End year", default=str(default_end))
                )
            except Exception:
                try:
                    start_year = int(
                        input(f"Start year [{default_start}]: ").strip()
                        or default_start
                    )
                except Exception:
                    start_year = default_start
                try:
                    end_year = int(
                        input(f"End year [{default_end}]: ").strip()
                        or default_end
                    )
                except Exception:
                    end_year = default_end

            _log(
                f"[migrate] Seeding datasets for {country}:{family} (version={version or '-'}) {start_year}-{end_year}..."
            )
            n = seed_datasets(
                db,
                country,
                family=family,
                version=version,
                start_year=start_year,
                end_year=end_year,
            )
            _log(f"[done] datasets={n}")
            return

        if action == "seed-datasets-hf":
            country = _prompt_select("Select country", ["uk", "us"])
            families = ["efrs"] if country == "uk" else ["ecps"]
            family = _prompt_select("Select dataset family", families)

            if country == "uk" and family == "efrs":
                from policyengine.countries.uk.datasets import (
                    UK_HUGGING_FACE_REPO as REPO,
                    UK_HUGGING_FACE_FILENAMES as FILES,
                    create_efrs_years_from_hf as build_years,
                )
            elif country == "us" and family == "ecps":
                from policyengine.countries.us.datasets import (
                    US_HUGGING_FACE_REPO as REPO,
                    US_HUGGING_FACE_DATASETS as FILES,
                    create_ecps_years_from_hf as build_years,
                )
            else:
                raise SystemExit(
                    f"Unknown dataset family for {country}: {family}"
                )

            filename = FILES[0] if len(FILES) == 1 else _prompt_select(
                "Select base dataset file", list(FILES)
            )

            _log(f"[migrate] Fetching tags from {REPO}...")
            tags = _hf_list_tags(REPO, repo_type="datasets")
            if not tags:
                raise SystemExit(
                    "No tags found or access denied to the repo."
                )
            version = _prompt_select(
                "Select dataset version (git tag)", tags
            )

            if country == "uk":
                default_start, default_end = 2023, 2030
            else:
                default_start, default_end = 2024, 2035
            try:
                from rich.prompt import IntPrompt  # type: ignore

                start_year = int(
                    IntPrompt.ask("Start year", default=str(default_start))
                )
                end_year = int(
                    IntPrompt.ask("End year", default=str(default_end))
                )
            except Exception:
                try:
                    start_year = int(
                        input(f"Start year [{default_start}]: ").strip()
                        or default_start
                    )
                except Exception:
                    start_year = default_start
                try:
                    end_year = int(
                        input(f"End year [{default_end}]: ").strip()
                        or default_end
                    )
                except Exception:
                    end_year = default_end

            _log(
                f"[migrate] Seeding {country}:{family} from HF tag '{version}' years {start_year}-{end_year}..."
            )
            datasets = build_years(
                start_year,
                end_year,
                repo=REPO,
                filename=filename,
                version=version,
            )
            ds_list = list(datasets)
            for ds in ds_list:
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
            _log(f"[done] datasets={len(ds_list)}")
            return

        if action == "reset":
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
