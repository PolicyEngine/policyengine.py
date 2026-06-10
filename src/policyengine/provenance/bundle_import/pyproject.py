from __future__ import annotations

import re
from pathlib import Path

from .io import required_dict, required_string
from .types import BundleImportError

COUNTRY_OPTIONAL_DEPENDENCIES = {
    "uk": "policyengine-uk",
    "us": "policyengine-us",
}


def update_optional_dependency_pins(
    *,
    pyproject_path: Path,
    country_bundles: dict[str, dict],
) -> None:
    text = pyproject_path.read_text()
    core_versions = set()
    for country_id, country_bundle in sorted(country_bundles.items()):
        if country_id not in COUNTRY_OPTIONAL_DEPENDENCIES:
            raise BundleImportError(
                f"Cannot update pyproject pins for unknown country {country_id!r}."
            )
        model_package = required_dict(country_bundle, "model_package")
        core_package = required_dict(country_bundle, "core_package")
        expected_package = COUNTRY_OPTIONAL_DEPENDENCIES[country_id]
        package_name = required_string(model_package, "name")
        if package_name != expected_package:
            raise BundleImportError(
                f"Country {country_id} expected model package {expected_package}, "
                f"got {package_name}."
            )
        package_version = required_string(model_package, "version")
        core_version = required_string(core_package, "version")
        core_versions.add(core_version)

        text = replace_dependency_in_section(
            text,
            section_name=country_id,
            package_name="policyengine_core",
            requirement=f"policyengine_core>={core_version}",
        )
        text = replace_dependency_in_section(
            text,
            section_name=country_id,
            package_name=package_name,
            requirement=f"{package_name}=={package_version}",
        )
        text = replace_dependency_in_section(
            text,
            section_name="dev",
            package_name=package_name,
            requirement=f"{package_name}=={package_version}",
        )

    if len(core_versions) != 1:
        raise BundleImportError(
            "Imported countries must use one policyengine-core version so the "
            "dev extra can be updated unambiguously."
        )
    core_version = next(iter(core_versions))
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
        raise BundleImportError(
            f"pyproject optional dependency missing: {section_name}"
        )
    content_start = text.find("\n", section_start)
    content_end = text.find("\n]", content_start)
    if content_start == -1 or content_end == -1:
        raise BundleImportError(f"Malformed pyproject section: {section_name}")

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
        raise BundleImportError(
            f"pyproject optional dependency {section_name} is missing {package_name}."
        )
    replacement = "\n".join(updated_lines)
    return f"{text[: content_start + 1]}{replacement}{text[content_end:]}"


def dependency_line_matches(line: str, package_name: str) -> bool:
    return (
        re.match(rf'"{re.escape(package_name)}\s*(==|>=|<=|~=|!=|>|<)', line)
        is not None
    )
