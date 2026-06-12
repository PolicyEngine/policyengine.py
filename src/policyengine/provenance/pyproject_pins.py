"""Update country model/core pins in ``pyproject.toml``.

Used by data-release certification: the certified model package is
exact-pinned in the country extra and the dev extra, and the core floor
is raised to the certified core version.
"""

from __future__ import annotations

import re
from pathlib import Path

COUNTRY_OPTIONAL_DEPENDENCIES = {
    "uk": "policyengine-uk",
    "us": "policyengine-us",
}


class PinUpdateError(ValueError):
    """Raised when a pyproject pin cannot be updated."""


def update_country_pins(
    *,
    pyproject_path: Path,
    country: str,
    model_package: str,
    model_version: str,
    core_version: str,
) -> None:
    if country not in COUNTRY_OPTIONAL_DEPENDENCIES:
        raise PinUpdateError(
            f"Cannot update pyproject pins for unknown country {country!r}."
        )
    expected_package = COUNTRY_OPTIONAL_DEPENDENCIES[country]
    if model_package != expected_package:
        raise PinUpdateError(
            f"Country {country} expected model package {expected_package}, "
            f"got {model_package}."
        )
    text = pyproject_path.read_text()
    core_version = _max_core_floor(text, core_version)
    text = replace_dependency_in_section(
        text,
        section_name=country,
        package_name="policyengine_core",
        requirement=f"policyengine_core>={core_version}",
    )
    text = replace_dependency_in_section(
        text,
        section_name=country,
        package_name=model_package,
        requirement=f"{model_package}=={model_version}",
    )
    text = replace_dependency_in_section(
        text,
        section_name="dev",
        package_name=model_package,
        requirement=f"{model_package}=={model_version}",
    )
    text = replace_dependency_in_section(
        text,
        section_name="dev",
        package_name="policyengine_core",
        requirement=f"policyengine_core>={core_version}",
    )
    pyproject_path.write_text(text)


def replace_dependency_in_section(
    text: str,
    *,
    section_name: str,
    package_name: str,
    requirement: str,
) -> str:
    section_start = text.find(f"{section_name} = [")
    if section_start == -1:
        raise PinUpdateError(f"pyproject optional dependency missing: {section_name}")
    content_start = text.find("\n", section_start)
    content_end = text.find("\n]", content_start)
    if content_start == -1 or content_end == -1:
        raise PinUpdateError(f"Malformed pyproject section: {section_name}")

    lines = text[content_start + 1 : content_end].splitlines()
    updated_lines = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if dependency_line_matches(stripped, package_name):
            updated_lines.append(f'    "{requirement}",')
            replaced = True
        else:
            updated_lines.append(line)
    if not replaced:
        raise PinUpdateError(
            f"pyproject optional dependency {section_name} is missing {package_name}."
        )
    replacement = "\n".join(updated_lines)
    return f"{text[: content_start + 1]}{replacement}{text[content_end:]}"


def dependency_line_matches(line: str, package_name: str) -> bool:
    return (
        re.match(rf'"{re.escape(package_name)}\s*(==|>=|<=|~=|!=|>|<)', line)
        is not None
    )


def _max_core_floor(pyproject_text: str, candidate: str) -> str:
    """Never lower a committed core floor because of a stale local env."""
    from packaging.version import Version

    floors = re.findall(r"policyengine_core>=([0-9][^\"',]*)", pyproject_text)
    best = candidate
    for floor in floors:
        try:
            if Version(floor) > Version(best):
                best = floor
        except Exception:
            continue
    return best
