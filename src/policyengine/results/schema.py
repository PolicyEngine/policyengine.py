"""Pydantic schema for results.json — the contract between analysis
repos and blog posts.

Every PolicyEngine blog post references a results.json file produced
by an analysis script.  This module validates that the file conforms
to the expected schema so errors are caught at generation time rather
than at build time when resolve-posts tries to render templates.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, model_validator


class ResultsMetadata(BaseModel):
    """Top-level metadata about the analysis."""

    title: str
    repo: str
    slug: str | None = None
    commit: str | None = None
    generated_at: str | None = None
    policyengine_version: str | None = None
    dataset: str | None = None
    country_id: str | None = None
    year: int | None = None


class ValueEntry(BaseModel):
    """A single traceable value in results.json."""

    value: Any
    display: str
    source_line: int
    source_url: str


class TableEntry(BaseModel):
    """A table in results.json."""

    title: str
    headers: list[str]
    rows: list[list[str]]
    source_line: int
    source_url: str

    @model_validator(mode="after")
    def check_row_widths(self) -> "TableEntry":
        n_cols = len(self.headers)
        for i, row in enumerate(self.rows):
            if len(row) != n_cols:
                raise ValueError(
                    f"Row {i} has {len(row)} columns but headers "
                    f"has {n_cols}"
                )
        return self


class ChartEntry(BaseModel):
    """A chart reference in results.json."""

    url: str
    alt: str
    width: int = 1200
    height: int = 600
    source_line: int
    source_url: str

    @model_validator(mode="after")
    def check_alt_text(self) -> "ChartEntry":
        if len(self.alt) < 20:
            raise ValueError(
                f"Alt text is too short ({len(self.alt)} chars). "
                "Include chart type and 2-3 key data points."
            )
        return self


class ResultsJson(BaseModel):
    """Full results.json schema.

    Usage::

        from policyengine.results import ResultsJson

        results = ResultsJson(
            metadata=ResultsMetadata(
                title="SALT Cap Repeal",
                repo="PolicyEngine/analyses",
            ),
            values={
                "budget_impact": ValueEntry(
                    value=-15.2e9,
                    display="$15.2 billion",
                    source_line=47,
                    source_url="https://github.com/.../analysis.py#L47",
                ),
            },
        )
        results.write("results.json")
    """

    metadata: ResultsMetadata
    values: dict[str, ValueEntry] = {}
    tables: dict[str, TableEntry] = {}
    charts: dict[str, ChartEntry] = {}

    def write(self, path: str | Path) -> None:
        """Write validated results.json to disk."""
        path = Path(path)
        data = json.loads(self.model_dump_json())
        path.write_text(json.dumps(data, indent=2))
