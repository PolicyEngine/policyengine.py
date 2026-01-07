"""Utilities for generating human-readable labels for tax-benefit parameters."""

import re


def generate_label_for_parameter(param_node, system, scale_lookup):
    """
    Generate a label for a parameter that doesn't have one.

    For breakdown parameters: Uses parent label + enum value
    For bracket parameters: Uses scale label + bracket info

    Args:
        param_node: The CoreParameter object
        system: The tax-benefit system (has variables and parameters)
        scale_lookup: Dict mapping scale names to ParameterScale objects

    Returns:
        str or None: Generated label, or None if cannot generate
    """
    if param_node.metadata.get("label"):
        return param_node.metadata.get("label")

    param_name = param_node.name

    if "[" in param_name:
        return _generate_bracket_label(param_name, scale_lookup)

    # Check for breakdown - either direct child or nested
    breakdown_parent = _find_breakdown_parent(param_node)
    if breakdown_parent:
        return _generate_breakdown_label(param_node, system, breakdown_parent)

    return None


def _find_breakdown_parent(param_node):
    """
    Walk up the tree to find the nearest ancestor with breakdown metadata.

    Args:
        param_node: The CoreParameter object

    Returns:
        The breakdown parent node, or None if not found
    """
    current = param_node.parent
    while current:
        if current.metadata.get("breakdown"):
            return current
        current = getattr(current, "parent", None)
    return None


def _generate_breakdown_label(param_node, system, breakdown_parent=None):
    """
    Generate label for a breakdown parameter using enum values.

    Handles both single-level and nested breakdowns by walking up to the
    breakdown parent and collecting all dimension values.

    Args:
        param_node: The CoreParameter object
        system: The tax-benefit system
        breakdown_parent: The ancestor node with breakdown metadata (optional)

    Returns:
        str or None: Generated label, or None if cannot generate
    """
    # Find breakdown parent if not provided
    if breakdown_parent is None:
        breakdown_parent = _find_breakdown_parent(param_node)
        if not breakdown_parent:
            return None

    parent_label = breakdown_parent.metadata.get("label")
    if not parent_label:
        return None

    breakdown_vars = breakdown_parent.metadata.get("breakdown", [])
    breakdown_labels = breakdown_parent.metadata.get("breakdown_labels", [])

    # Collect dimension values from breakdown parent to param_node
    dimension_values = _collect_dimension_values(
        param_node, breakdown_parent
    )

    if not dimension_values:
        return None

    # Generate labels for each dimension
    formatted_parts = []
    for i, (dim_key, dim_value) in enumerate(dimension_values):
        var_name = breakdown_vars[i] if i < len(breakdown_vars) else None
        dim_label = breakdown_labels[i] if i < len(breakdown_labels) else None

        formatted_value = _format_dimension_value(
            dim_value, var_name, dim_label, system
        )
        formatted_parts.append(formatted_value)

    return f"{parent_label} ({', '.join(formatted_parts)})"


def _collect_dimension_values(param_node, breakdown_parent):
    """
    Collect dimension keys and values from breakdown parent to param_node.

    Args:
        param_node: The CoreParameter object
        breakdown_parent: The ancestor node with breakdown metadata

    Returns:
        list of (dimension_key, value) tuples, ordered from parent to child
    """
    # Build path from param_node up to breakdown_parent
    path = []
    current = param_node
    while current and current != breakdown_parent:
        path.append(current)
        current = getattr(current, "parent", None)

    # Reverse to get parent-to-child order
    path.reverse()

    # Extract dimension values
    dimension_values = []
    for i, node in enumerate(path):
        key = node.name.split(".")[-1]
        dimension_values.append((i, key))

    return dimension_values


def _format_dimension_value(value, var_name, dim_label, system):
    """
    Format a single dimension value with semantic label if available.

    Args:
        value: The raw dimension value (e.g., "SINGLE", "1", "CA")
        var_name: The breakdown variable name (e.g., "filing_status", "range(1, 9)")
        dim_label: The human-readable label for this dimension (e.g., "Household size")
        system: The tax-benefit system

    Returns:
        str: Formatted dimension value
    """
    # First, try to get enum display value
    if var_name and not var_name.startswith("range(") and not var_name.startswith("list("):
        var = system.variables.get(var_name)
        if var and hasattr(var, "possible_values") and var.possible_values:
            try:
                enum_value = var.possible_values[value].value
                return str(enum_value)
            except (KeyError, AttributeError):
                pass

    # For range() dimensions or when no enum found, use breakdown_label if available
    if dim_label:
        return f"{dim_label} {value}"

    return value


def _generate_bracket_label(param_name, scale_lookup):
    """Generate label for a bracket parameter."""
    match = re.match(r"^(.+)\[(\d+)\]\.(\w+)$", param_name)
    if not match:
        return None

    scale_name = match.group(1)
    bracket_index = int(match.group(2))
    field_name = match.group(3)

    scale = scale_lookup.get(scale_name)
    if not scale:
        return None

    scale_label = scale.metadata.get("label")
    scale_type = scale.metadata.get("type", "")

    if not scale_label:
        return None

    bracket_num = bracket_index + 1

    if scale_type in ("marginal_rate", "marginal_amount"):
        bracket_desc = f"bracket {bracket_num}"
    elif scale_type == "single_amount":
        bracket_desc = f"tier {bracket_num}"
    else:
        bracket_desc = f"bracket {bracket_num}"

    return f"{scale_label} ({bracket_desc} {field_name})"


def build_scale_lookup(system):
    """
    Build a lookup dict mapping scale names to ParameterScale objects.

    Args:
        system: The tax-benefit system

    Returns:
        dict: Mapping of scale name -> ParameterScale object
    """
    from policyengine_core.parameters import ParameterScale

    return {
        p.name: p
        for p in system.parameters.get_descendants()
        if isinstance(p, ParameterScale)
    }
