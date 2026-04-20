"""Generate reference documentation pages from PolicyEngine country models.

Introspects a country model's `TaxBenefitSystem` for every variable, reads
attributes directly from each `Variable` class (`label`, `documentation`,
`entity`, `unit`, `reference`, `defined_for`, `definition_period`,
`adds`/`subtracts`, source file path), and writes one ``.qmd`` page per
variable grouped by its parameter-tree path (``gov/hhs/chip/chip_premium``).

Also loads the country model's ``programs.yaml`` and writes a program-level
landing page for each entry, cross-linking the variables that belong to it.

Usage
-----

Run for a single country model, writing into an output directory:

.. code-block:: bash

    python docs/_generator/build_reference.py \\
        --country us \\
        --out docs/_generated/reference/us

Run for a subset of variables to preview output:

.. code-block:: bash

    python docs/_generator/build_reference.py \\
        --country us --filter chip --out /tmp/ref-preview

Design notes
------------

This is a prototype meant to demonstrate how much reference material can be
regenerated from code + parameter YAML + ``programs.yaml`` alone, with no
hand-authored prose. Intentional non-goals:

* Do not execute formulas; read metadata only.
* Do not render parameters (a follow-up can walk the parameter tree similarly).
* Do not write an index page tree; Quarto's directory listings handle that.

The generator emits standard Quarto Markdown (``.qmd``). Quarto reads regular
Markdown too, so the outputs drop into either a Quarto or MyST site.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

logger = logging.getLogger(__name__)


COUNTRY_MODULES = {
    "us": "policyengine_us",
    "uk": "policyengine_uk",
    "canada": "policyengine_canada",
    "il": "policyengine_il",
    "ng": "policyengine_ng",
}


@dataclass(frozen=True)
class VariableRecord:
    name: str
    label: str | None
    documentation: str | None
    entity: str | None
    unit: str | None
    value_type: str | None
    definition_period: str | None
    references: tuple[str, ...]
    defined_for: str | None
    source_file: Path | None
    source_line: int | None
    adds: tuple[str, ...]
    subtracts: tuple[str, ...]
    tree_path: tuple[str, ...]


def _tree_path_from_source(
    source_file: Path | None, package_root: Path
) -> tuple[str, ...]:
    if source_file is None:
        return ("_ungrouped",)
    try:
        rel = source_file.relative_to(package_root / "variables")
    except ValueError:
        return ("_ungrouped",)
    parts = rel.with_suffix("").parts
    return parts[:-1] if parts else ("_ungrouped",)


def _normalize_references(raw) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, (list, tuple)):
        return tuple(str(r) for r in raw if r)
    return (str(raw),)


def _variable_records(country: str) -> Iterable[VariableRecord]:
    module_name = COUNTRY_MODULES[country]
    country_module = importlib.import_module(module_name)

    system_module = importlib.import_module(f"{module_name}.system")
    tbs = system_module.CountryTaxBenefitSystem()

    package_root = Path(country_module.__file__).parent

    import inspect

    for name in sorted(tbs.variables):
        variable = tbs.variables[name]
        try:
            source_file = Path(inspect.getsourcefile(type(variable)))
            source_line = inspect.getsourcelines(type(variable))[1]
        except (TypeError, OSError):
            source_file = None
            source_line = None

        entity_key = getattr(variable.entity, "key", None) if variable.entity else None
        value_type = getattr(variable, "value_type", None)
        value_type_name = (
            value_type.__name__
            if isinstance(value_type, type)
            else str(value_type)
            if value_type is not None
            else None
        )
        defined_for = getattr(variable, "defined_for", None)
        defined_for_name = (
            defined_for.name if hasattr(defined_for, "name") else defined_for
        )

        yield VariableRecord(
            name=name,
            label=variable.label,
            documentation=variable.documentation,
            entity=entity_key,
            unit=getattr(variable, "unit", None),
            value_type=value_type_name,
            definition_period=getattr(variable, "definition_period", None),
            references=_normalize_references(getattr(variable, "reference", None)),
            defined_for=defined_for_name,
            source_file=source_file,
            source_line=source_line,
            adds=tuple(getattr(variable, "adds", ()) or ()),
            subtracts=tuple(getattr(variable, "subtracts", ()) or ()),
            tree_path=_tree_path_from_source(source_file, package_root),
        )


def _escape_yaml_scalar(value: str) -> str:
    return value.replace('"', '\\"')


def _render_variable_page(record: VariableRecord, country: str) -> str:
    title = record.label or record.name
    lines: list[str] = [
        "---",
        f'title: "{_escape_yaml_scalar(title)}"',
        f'subtitle: "`{record.name}`"',
    ]
    if record.documentation:
        summary = record.documentation.strip().splitlines()[0][:220]
        lines.append(f'description: "{_escape_yaml_scalar(summary)}"')
    lines.extend(
        [
            "format:",
            "  html:",
            "    code-copy: true",
            "---",
            "",
        ]
    )

    metadata = [
        ("Name", f"`{record.name}`"),
        ("Entity", f"`{record.entity}`" if record.entity else "—"),
        ("Value type", f"`{record.value_type}`" if record.value_type else "—"),
        ("Unit", f"`{record.unit}`" if record.unit else "—"),
        (
            "Period",
            f"`{record.definition_period}`" if record.definition_period else "—",
        ),
        (
            "Defined for",
            f"`{record.defined_for}`" if record.defined_for else "—",
        ),
    ]
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for key, value in metadata:
        lines.append(f"| {key} | {value} |")
    lines.append("")

    if record.documentation:
        lines.append("## Documentation")
        lines.append("")
        lines.append(record.documentation.strip())
        lines.append("")

    if record.adds:
        lines.append("## Components")
        lines.append("")
        lines.append("This variable sums the following variables:")
        lines.append("")
        for component in record.adds:
            lines.append(f"- `{component}`")
        lines.append("")

    if record.subtracts:
        lines.append("## Subtractions")
        lines.append("")
        lines.append("This variable subtracts the following variables:")
        lines.append("")
        for component in record.subtracts:
            lines.append(f"- `{component}`")
        lines.append("")

    if record.references:
        lines.append("## References")
        lines.append("")
        for ref in record.references:
            lines.append(f"- <{ref}>")
        lines.append("")

    if record.source_file:
        try:
            repo_rel = record.source_file.relative_to(record.source_file.parents[5])
        except (ValueError, IndexError):
            repo_rel = record.source_file.name
        lines.append("## Source")
        lines.append("")
        if record.source_line:
            lines.append(f"`{repo_rel}`, line {record.source_line}")
        else:
            lines.append(f"`{repo_rel}`")
        lines.append("")

    return "\n".join(lines)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")


def _write_variables(
    records: list[VariableRecord],
    out_root: Path,
    country: str,
) -> int:
    written = 0
    for record in records:
        tree_dir = out_root.joinpath(*record.tree_path)
        tree_dir.mkdir(parents=True, exist_ok=True)
        page_path = tree_dir / f"{_slug(record.name)}.qmd"
        page_path.write_text(_render_variable_page(record, country))
        written += 1
    return written


def _write_tree_indices(out_root: Path) -> int:
    written = 0
    for directory in [out_root, *(p for p in out_root.rglob("*") if p.is_dir())]:
        index_path = directory / "index.qmd"
        if index_path.exists():
            continue
        title = directory.name if directory != out_root else "Reference"
        index_path.write_text(
            textwrap.dedent(
                f"""\
                ---
                title: "{title}"
                listing:
                  contents: "*.qmd"
                  type: table
                  sort: "title"
                  fields: [title, subtitle, description]
                ---
                """
            )
        )
        written += 1
    return written


def _write_programs_index(country: str, out_root: Path) -> int:
    module_name = COUNTRY_MODULES[country]
    country_module = importlib.import_module(module_name)
    package_root = Path(country_module.__file__).parent
    programs_path = package_root / "programs.yaml"
    if not programs_path.exists():
        return 0
    with programs_path.open() as f:
        registry = yaml.safe_load(f)
    programs = registry.get("programs", [])
    lines: list[str] = [
        "---",
        'title: "Program coverage"',
        'description: "Programs modeled in the country model, generated from programs.yaml."',
        "---",
        "",
        "| ID | Name | Category | Agency | Status | Coverage |",
        "|---|---|---|---|---|---|",
    ]
    for program in programs:
        lines.append(
            "| "
            + " | ".join(
                str(program.get(field, "")).replace("\n", " ")
                for field in ("id", "name", "category", "agency", "status", "coverage")
            )
            + " |"
        )
    target = out_root / "programs.qmd"
    target.write_text("\n".join(lines) + "\n")
    return 1


def build_reference(
    country: str,
    out_root: Path,
    filter_substring: str | None = None,
) -> dict[str, int]:
    out_root.mkdir(parents=True, exist_ok=True)
    records = list(_variable_records(country))
    if filter_substring:
        needle = filter_substring.lower()
        records = [
            r
            for r in records
            if needle in r.name.lower()
            or needle in " ".join(str(p).lower() for p in r.tree_path)
        ]
    variables_written = _write_variables(records, out_root, country)
    programs_written = _write_programs_index(country, out_root)
    indices_written = _write_tree_indices(out_root)
    return {
        "variables": variables_written,
        "programs": programs_written,
        "indices": indices_written,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--country",
        choices=sorted(COUNTRY_MODULES),
        default="us",
        help="Country model to introspect.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for generated .qmd pages.",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="Substring filter on variable name or tree path (case-insensitive).",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    stats = build_reference(args.country, args.out, args.filter)
    logger.info(
        "Wrote %d variable pages, %d programs page, %d directory indices to %s",
        stats["variables"],
        stats["programs"],
        stats["indices"],
        args.out,
    )


if __name__ == "__main__":
    main()
