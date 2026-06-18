"""PolicyEngine stack manifest inspection and verification.

The stack manifest is the pip-native replacement for release bundles: it names
the exact first-party package set certified for a ``policyengine`` release.
Installation remains standard pip extras; this module only reports and verifies
what is installed.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import metadata
from importlib.resources import files
from importlib.util import find_spec
from typing import Any, Mapping, Optional

import requests

STACK_MANIFEST_RESOURCE = ("data", "stack", "manifest.json")
URI_CHECK_TIMEOUT_SECONDS = 5


class StackError(ValueError):
    """Raised when stack metadata is missing or inconsistent."""


def _stack_resource_path():
    path = files("policyengine")
    for part in STACK_MANIFEST_RESOURCE:
        path = path.joinpath(part)
    return path


@lru_cache
def get_current_stack() -> dict[str, Any]:
    """Return the stack manifest packaged with this ``policyengine`` wheel."""
    resource = _stack_resource_path()
    try:
        return json.loads(resource.read_text())
    except FileNotFoundError as exc:
        raise StackError("No packaged PolicyEngine stack manifest found.") from exc


def get_component(name: str) -> dict[str, Any]:
    """Return one component from the current stack manifest."""
    components = get_current_stack().get("packages", {})
    key = _component_key(name)
    try:
        return components[key]
    except KeyError as exc:
        raise StackError(f"No stack component named {name!r}.") from exc


def get_extra(name: str) -> list[str]:
    """Return the component names included by a pip extra."""
    extras = get_current_stack().get("extras", {})
    try:
        return list(extras[name])
    except KeyError as exc:
        raise StackError(f"No stack extra named {name!r}.") from exc


def stack_install_requirements(extra: str = "full") -> list[str]:
    """Return exact pip requirements for a stack extra."""
    stack = get_current_stack()
    requirements = [f"policyengine=={stack['policyengine_version']}"]
    for component_name in get_extra(extra):
        component = get_component(component_name)
        requirements.append(component["install_requirement"])
    return requirements


def verify_installed_stack(
    *,
    extra: Optional[str] = None,
    check_imports: bool = True,
    check_uris: bool = False,
    uri_timeout_seconds: int = URI_CHECK_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Verify installed packages against the packaged stack manifest.

    Without ``extra``, this verifies ``policyengine`` plus every stack component
    that is already installed and marks missing optional components as skipped.
    With ``extra``, all components in that extra are required.
    """
    stack = get_current_stack()
    required = _required_components(stack, extra)
    component_checks = [
        _verify_component(
            key,
            component,
            required=key in required,
            check_imports=check_imports,
        )
        for key, component in stack.get("packages", {}).items()
        if key in required or extra is None
    ]
    uri_checks = (
        _verify_uris(stack.get("countries", {}), timeout=uri_timeout_seconds)
        if check_uris
        else []
    )
    checks: list[Mapping[str, Any]] = [*component_checks, *uri_checks]
    passed = all(check["status"] in {"ok", "skipped"} for check in checks)
    return {
        "schema_version": 1,
        "stack_version": stack.get("stack_version"),
        "policyengine_version": stack.get("policyengine_version"),
        "extra": extra,
        "passed": passed,
        "checks": checks,
    }


def format_stack_citation() -> str:
    """Return a concise human-readable citation for the current stack."""
    stack = get_current_stack()
    package_lines = [
        f"- {component['name']} {component['version']}"
        for _, component in sorted(stack.get("packages", {}).items())
    ]
    return "\n".join(
        [
            f"PolicyEngine stack {stack['stack_version']}",
            f"PolicyEngine package version: {stack['policyengine_version']}",
            "Components:",
            *package_lines,
        ]
    )


def _component_key(name: str) -> str:
    return name.replace("_", "-").lower()


def _required_components(stack: Mapping[str, Any], extra: Optional[str]) -> set[str]:
    if extra is None:
        return {"policyengine"}
    extras = stack.get("extras", {})
    if extra not in extras:
        raise StackError(f"No stack extra named {extra!r}.")
    return {"policyengine", *(_component_key(name) for name in extras[extra])}


def _verify_component(
    key: str,
    component: Mapping[str, Any],
    *,
    required: bool,
    check_imports: bool,
) -> dict[str, Any]:
    package_name = str(component["name"])
    expected_version = str(component["version"])
    check: dict[str, Any] = {
        "kind": "component",
        "component": key,
        "package": package_name,
        "expected_version": expected_version,
    }
    try:
        installed_version = metadata.version(package_name)
    except metadata.PackageNotFoundError:
        check["status"] = "missing" if required else "skipped"
        check["message"] = "Package is not installed."
        return check

    check["installed_version"] = installed_version
    if installed_version != expected_version:
        check["status"] = "mismatch"
        check["message"] = "Installed version does not match stack pin."
        return check

    import_name = component.get("import_name")
    if check_imports and import_name:
        if find_spec(str(import_name)) is None:
            check["status"] = "import_error"
            check["message"] = f"Import module {import_name!r} is not discoverable."
            return check

    check["status"] = "ok"
    return check


def _verify_uris(
    countries: Mapping[str, Mapping[str, Any]],
    *,
    timeout: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for country_id, country in sorted(countries.items()):
        for field in ("release_manifest_uri",):
            uri = country.get(field)
            if not uri:
                continue
            checks.append(_verify_uri(country_id, field, str(uri), timeout=timeout))
    return checks


def _verify_uri(
    country_id: str, field: str, uri: str, *, timeout: int
) -> dict[str, Any]:
    check: dict[str, Any] = {
        "kind": "uri",
        "country": country_id,
        "field": field,
        "uri": uri,
    }
    try:
        response = requests.head(uri, allow_redirects=True, timeout=timeout)
        if response.status_code == 405:
            response = requests.get(uri, stream=True, timeout=timeout)
    except requests.RequestException as exc:
        check["status"] = "unreachable"
        check["message"] = str(exc)
        return check

    check["status_code"] = response.status_code
    if response.status_code in {200, 401, 403}:
        check["status"] = "ok"
    else:
        check["status"] = "bad_status"
        check["message"] = f"HTTP {response.status_code}"
    return check
