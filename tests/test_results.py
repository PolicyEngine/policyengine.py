"""Tests for the results.json schema validation and source tracking."""

import json
import tempfile
from pathlib import Path

import pytest

from policyengine.results import (
    ChartEntry,
    ResultsJson,
    ResultsMetadata,
    TableEntry,
    ValueEntry,
    tracked_value,
)


def test_valid_results_json():
    """A fully valid results.json passes validation."""
    results = ResultsJson(
        metadata=ResultsMetadata(
            title="Test Analysis",
            repo="PolicyEngine/test",
            year=2026,
            country_id="us",
        ),
        values={
            "budget_impact": ValueEntry(
                value=-15200000000,
                display="$15.2 billion",
                source_line=47,
                source_url="https://github.com/PolicyEngine/test/blob/main/analysis.py#L47",
            ),
        },
        tables={
            "household": TableEntry(
                title="Household impacts",
                headers=["Household", "Income", "Change"],
                rows=[
                    ["Single", "$50,000", "+$1,200"],
                    ["Married", "$100,000", "+$2,400"],
                ],
                source_line=80,
                source_url="https://github.com/PolicyEngine/test/blob/main/analysis.py#L80",
            ),
        },
        charts={
            "decile": ChartEntry(
                url="https://PolicyEngine.github.io/test/charts/decile.png",
                alt="Bar chart showing impact by decile. Top decile gains $8,200.",
                source_line=105,
                source_url="https://github.com/PolicyEngine/test/blob/main/analysis.py#L105",
            ),
        },
    )

    assert results.metadata.title == "Test Analysis"
    assert results.values["budget_impact"].value == -15200000000
    assert len(results.tables["household"].rows) == 2
    assert results.charts["decile"].width == 1200


def test_value_entry_requires_source_line():
    """ValueEntry without source_line raises ValidationError."""
    with pytest.raises(Exception):
        ValueEntry(
            value=100,
            display="$100",
            source_url="https://github.com/x/y#L1",
        )


def test_value_entry_requires_source_url():
    """ValueEntry without source_url raises ValidationError."""
    with pytest.raises(Exception):
        ValueEntry(
            value=100,
            display="$100",
            source_line=10,
        )


def test_table_row_width_mismatch():
    """Table with wrong number of columns per row raises error."""
    with pytest.raises(Exception):
        TableEntry(
            title="Bad table",
            headers=["A", "B", "C"],
            rows=[["x", "y"]],  # 2 cols, need 3
            source_line=1,
            source_url="https://github.com/x/y#L1",
        )


def test_chart_alt_text_too_short():
    """Chart with vague alt text raises error."""
    with pytest.raises(Exception):
        ChartEntry(
            url="https://example.com/chart.png",
            alt="A chart.",  # Too short
            source_line=1,
            source_url="https://github.com/x/y#L1",
        )


def test_chart_alt_text_descriptive():
    """Chart with descriptive alt text passes."""
    chart = ChartEntry(
        url="https://example.com/chart.png",
        alt="Bar chart showing reform impact by income decile. Top decile gains $8,200 average.",
        source_line=1,
        source_url="https://github.com/x/y#L1",
    )
    assert chart.width == 1200
    assert chart.height == 600


def test_write_results_json():
    """ResultsJson.write() produces valid JSON file."""
    results = ResultsJson(
        metadata=ResultsMetadata(
            title="Write Test",
            repo="PolicyEngine/test",
        ),
        values={
            "x": ValueEntry(
                value=42,
                display="42",
                source_line=1,
                source_url="https://github.com/x/y#L1",
            ),
        },
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "results.json"
        results.write(path)

        raw = path.read_text()
        assert raw.endswith("\n"), "File should end with a newline"
        data = json.loads(raw)
        assert data["metadata"]["title"] == "Write Test"
        assert data["values"]["x"]["value"] == 42
        assert data["values"]["x"]["source_line"] == 1


def test_write_creates_parent_directories():
    """ResultsJson.write() creates parent directories if needed."""
    results = ResultsJson(
        metadata=ResultsMetadata(
            title="Nested",
            repo="PolicyEngine/test",
        ),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sub" / "dir" / "results.json"
        results.write(path)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["metadata"]["title"] == "Nested"


def test_empty_results_json():
    """ResultsJson with only metadata is valid."""
    results = ResultsJson(
        metadata=ResultsMetadata(
            title="Empty",
            repo="PolicyEngine/test",
        ),
    )
    assert results.values == {}
    assert results.tables == {}
    assert results.charts == {}


def test_tracked_value():
    """tracked_value() captures line number and builds source URL."""
    result = tracked_value(
        value=-15200000000,
        display="$15.2 billion",
        repo="PolicyEngine/analyses",
        filename="analysis.py",
    )

    assert result["value"] == -15200000000
    assert result["display"] == "$15.2 billion"
    assert isinstance(result["source_line"], int)
    assert result["source_line"] > 0
    assert "PolicyEngine/analyses" in result["source_url"]
    assert "analysis.py#L" in result["source_url"]


def test_tracked_value_custom_filename():
    """tracked_value() respects custom filename and branch."""
    result = tracked_value(
        value=100,
        display="$100",
        repo="PolicyEngine/analyses",
        filename="salt-cap/analysis.py",
        branch="dev",
    )

    assert "salt-cap/analysis.py" in result["source_url"]
    assert "/blob/dev/" in result["source_url"]


def test_tracked_value_validates_as_value_entry():
    """tracked_value() output can be used to construct a ValueEntry."""
    result = tracked_value(
        value=42,
        display="42",
        repo="PolicyEngine/test",
    )
    entry = ValueEntry(**result)
    assert entry.value == 42
    assert entry.source_line > 0
