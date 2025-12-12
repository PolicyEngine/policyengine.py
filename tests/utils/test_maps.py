import pytest


def test_get_location_options_table_parliamentary_constituencies():
    """Test loading parliamentary constituencies location table."""
    from policyengine.utils.maps import get_location_options_table

    df = get_location_options_table("parliamentary_constituencies")

    assert len(df) > 0
    assert "name" in df.columns
    assert "code" in df.columns
    assert "x" in df.columns
    assert "y" in df.columns


def test_get_location_options_table_local_authorities():
    """Test loading local authorities location table."""
    from policyengine.utils.maps import get_location_options_table

    df = get_location_options_table("local_authorities")

    assert len(df) > 0
    assert "name" in df.columns
    assert "code" in df.columns
    assert "x" in df.columns
    assert "y" in df.columns


def test_plot_hex_map_local_authorities():
    """Test plotting hex map for local authorities."""
    from policyengine.utils.maps import (
        get_location_options_table,
        plot_hex_map,
    )

    # Get local authority names
    df = get_location_options_table("local_authorities")

    # Create dummy values for each local authority
    value_by_area_name = {name: i * 0.01 for i, name in enumerate(df["name"])}

    fig = plot_hex_map(value_by_area_name, "local_authorities")

    # Check that a figure was returned
    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0


def test_plot_hex_map_parliamentary_constituencies():
    """Test plotting hex map for parliamentary constituencies."""
    from policyengine.utils.maps import (
        get_location_options_table,
        plot_hex_map,
    )

    # Get constituency names
    df = get_location_options_table("parliamentary_constituencies")

    # Create dummy values for each constituency
    value_by_area_name = {name: i * 0.01 for i, name in enumerate(df["name"])}

    fig = plot_hex_map(value_by_area_name, "parliamentary_constituencies")

    # Check that a figure was returned
    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0


def test_plot_hex_map_invalid_location_type():
    """Test that invalid location type raises ValueError."""
    from policyengine.utils.maps import plot_hex_map

    with pytest.raises(ValueError, match="Invalid location_type"):
        plot_hex_map({"area": 1.0}, "invalid_type")
