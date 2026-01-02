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

    if param_node.parent and param_node.parent.metadata.get("breakdown"):
        return _generate_breakdown_label(param_node, system)

    return None


def _generate_breakdown_label(param_node, system):
    """Generate label for a breakdown parameter using enum values."""
    parent = param_node.parent
    parent_label = parent.metadata.get("label")
    breakdown_vars = parent.metadata.get("breakdown", [])

    if not parent_label:
        return None

    child_key = param_node.name.split(".")[-1]

    for var_name in breakdown_vars:
        var = system.variables.get(var_name)
        if var and hasattr(var, "possible_values") and var.possible_values:
            enum_class = var.possible_values
            try:
                enum_value = enum_class[child_key].value
                return f"{parent_label} ({enum_value})"
            except (KeyError, AttributeError):
                continue

    return f"{parent_label} ({child_key})"


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
