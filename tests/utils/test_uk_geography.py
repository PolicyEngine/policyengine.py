"""Tests for UK geographic region filtering utilities."""

import pytest

from policyengine.utils.uk_geography import (
    UK_REGION_TYPES,
    UKRegionType,
    determine_uk_region_type,
    get_country_from_code,
    should_zero_constituency,
    should_zero_local_authority,
)


class TestUKRegionTypes:
    """Tests for UK_REGION_TYPES constant."""

    def test_contains_expected_types(self):
        """Test that UK_REGION_TYPES contains all expected region types."""
        assert "uk" in UK_REGION_TYPES
        assert "country" in UK_REGION_TYPES
        assert "constituency" in UK_REGION_TYPES
        assert "local_authority" in UK_REGION_TYPES

    def test_has_four_types(self):
        """Test that UK_REGION_TYPES has exactly four types."""
        assert len(UK_REGION_TYPES) == 4


class TestDetermineUKRegionType:
    """Tests for determine_uk_region_type function."""

    def test_none_returns_uk(self):
        """Test that None region returns 'uk' type."""
        result = determine_uk_region_type(None)
        assert result == "uk"

    def test_country_region(self):
        """Test parsing country region strings."""
        assert determine_uk_region_type("country/scotland") == "country"
        assert determine_uk_region_type("country/england") == "country"
        assert determine_uk_region_type("country/wales") == "country"
        assert determine_uk_region_type("country/northern_ireland") == "country"

    def test_constituency_region(self):
        """Test parsing constituency region strings."""
        assert determine_uk_region_type("constituency/Aberdeen North") == "constituency"
        assert determine_uk_region_type("constituency/S14000001") == "constituency"

    def test_local_authority_region(self):
        """Test parsing local authority region strings."""
        assert determine_uk_region_type("local_authority/leicester") == "local_authority"
        assert determine_uk_region_type("local_authority/E06000016") == "local_authority"

    def test_invalid_region_raises_error(self):
        """Test that invalid region prefixes raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            determine_uk_region_type("invalid/test")
        assert "Invalid UK region type: 'invalid'" in str(exc_info.value)
        assert "Expected one of:" in str(exc_info.value)

    def test_empty_prefix_raises_error(self):
        """Test that empty prefix raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            determine_uk_region_type("/test")
        assert "Invalid UK region type: ''" in str(exc_info.value)

    def test_unknown_prefix_raises_error(self):
        """Test that unknown prefixes raise ValueError."""
        with pytest.raises(ValueError):
            determine_uk_region_type("state/california")
        with pytest.raises(ValueError):
            determine_uk_region_type("region/north_west")


class TestGetCountryFromCode:
    """Tests for get_country_from_code function."""

    def test_english_code(self):
        """Test that E prefix returns england."""
        assert get_country_from_code("E14000001") == "england"
        assert get_country_from_code("E06000016") == "england"

    def test_scottish_code(self):
        """Test that S prefix returns scotland."""
        assert get_country_from_code("S14000001") == "scotland"
        assert get_country_from_code("S12000033") == "scotland"

    def test_welsh_code(self):
        """Test that W prefix returns wales."""
        assert get_country_from_code("W07000041") == "wales"

    def test_northern_ireland_code(self):
        """Test that N prefix returns northern_ireland."""
        assert get_country_from_code("N06000001") == "northern_ireland"

    def test_unknown_code_returns_none(self):
        """Test that unknown code prefixes return None."""
        assert get_country_from_code("X12345678") is None
        assert get_country_from_code("123456789") is None


class TestShouldZeroConstituency:
    """Tests for should_zero_constituency function."""

    def test_uk_wide_never_zeros(self):
        """Test that UK-wide (None) region never zeros any constituency."""
        assert should_zero_constituency(None, "S14000001", "Aberdeen North") is False
        assert should_zero_constituency(None, "E14000001", "Some English") is False
        assert should_zero_constituency(None, "W07000001", "Some Welsh") is False

    def test_country_filter_keeps_matching_country(self):
        """Test that country filter keeps constituencies in that country."""
        # Scottish constituency in scotland filter -> keep
        assert should_zero_constituency("country/scotland", "S14000001", "Aberdeen North") is False
        # English constituency in england filter -> keep
        assert should_zero_constituency("country/england", "E14000001", "Some English") is False

    def test_country_filter_zeros_other_countries(self):
        """Test that country filter zeros constituencies in other countries."""
        # English constituency in scotland filter -> zero
        assert should_zero_constituency("country/scotland", "E14000001", "Some English") is True
        # Scottish constituency in england filter -> zero
        assert should_zero_constituency("country/england", "S14000001", "Aberdeen North") is True
        # Welsh constituency in scotland filter -> zero
        assert should_zero_constituency("country/scotland", "W07000001", "Some Welsh") is True

    def test_constituency_filter_keeps_matching_by_code(self):
        """Test that constituency filter keeps matching constituency by code."""
        assert should_zero_constituency("constituency/S14000001", "S14000001", "Aberdeen North") is False

    def test_constituency_filter_keeps_matching_by_name(self):
        """Test that constituency filter keeps matching constituency by name."""
        assert should_zero_constituency("constituency/Aberdeen North", "S14000001", "Aberdeen North") is False

    def test_constituency_filter_zeros_non_matching(self):
        """Test that constituency filter zeros non-matching constituencies."""
        assert should_zero_constituency("constituency/Aberdeen North", "S14000002", "Aberdeen South") is True
        assert should_zero_constituency("constituency/S14000001", "E14000001", "Some English") is True

    def test_local_authority_filter_zeros_all_constituencies(self):
        """Test that local authority filter zeros all constituencies."""
        assert should_zero_constituency("local_authority/leicester", "S14000001", "Aberdeen North") is True
        assert should_zero_constituency("local_authority/leicester", "E14000001", "Some English") is True
        assert should_zero_constituency("local_authority/E06000016", "W07000001", "Some Welsh") is True


class TestShouldZeroLocalAuthority:
    """Tests for should_zero_local_authority function."""

    def test_uk_wide_never_zeros(self):
        """Test that UK-wide (None) region never zeros any local authority."""
        assert should_zero_local_authority(None, "E06000016", "Leicester") is False
        assert should_zero_local_authority(None, "S12000033", "Aberdeen") is False
        assert should_zero_local_authority(None, "W06000001", "Some Welsh LA") is False

    def test_country_filter_keeps_matching_country(self):
        """Test that country filter keeps local authorities in that country."""
        # English LA in england filter -> keep
        assert should_zero_local_authority("country/england", "E06000016", "Leicester") is False
        # Scottish LA in scotland filter -> keep
        assert should_zero_local_authority("country/scotland", "S12000033", "Aberdeen") is False

    def test_country_filter_zeros_other_countries(self):
        """Test that country filter zeros local authorities in other countries."""
        # Scottish LA in england filter -> zero
        assert should_zero_local_authority("country/england", "S12000033", "Aberdeen") is True
        # English LA in scotland filter -> zero
        assert should_zero_local_authority("country/scotland", "E06000016", "Leicester") is True

    def test_local_authority_filter_keeps_matching_by_code(self):
        """Test that local authority filter keeps matching LA by code."""
        assert should_zero_local_authority("local_authority/E06000016", "E06000016", "Leicester") is False

    def test_local_authority_filter_keeps_matching_by_name(self):
        """Test that local authority filter keeps matching LA by name."""
        assert should_zero_local_authority("local_authority/Leicester", "E06000016", "Leicester") is False

    def test_local_authority_filter_zeros_non_matching(self):
        """Test that local authority filter zeros non-matching local authorities."""
        assert should_zero_local_authority("local_authority/Leicester", "E06000017", "Rutland") is True
        assert should_zero_local_authority("local_authority/E06000016", "S12000033", "Aberdeen") is True

    def test_constituency_filter_zeros_all_local_authorities(self):
        """Test that constituency filter zeros all local authorities."""
        assert should_zero_local_authority("constituency/Aberdeen North", "E06000016", "Leicester") is True
        assert should_zero_local_authority("constituency/Aberdeen North", "S12000033", "Aberdeen") is True
        assert should_zero_local_authority("constituency/S14000001", "W06000001", "Some Welsh LA") is True
