from pydantic import ValidationError
import pytest
import numpy as np

from policyengine.utils.reforms import ParameterChangeDict, ParametricReform


class TestParameterChangeDict:
    def test_schema__given_float_inputs__returns_valid_dict(self):
        input_data = {
            "2023-01-01.2023-12-31": 0.1,
            "2024-01-01.2024-12-31": 0.2,
        }

        result = ParameterChangeDict(root=input_data)

        assert isinstance(result, ParameterChangeDict)
        assert result.root == input_data

    def test_schema__given_string_inputs__returns_valid_dict(self):
        input_data = {
            "2023-01-01.2023-12-31": "0.1",
            "2024-01-01.2024-12-31": "0.2",
        }

        result = ParameterChangeDict(root=input_data)

        assert isinstance(result, ParameterChangeDict)
        assert result.root == input_data

    def test_schema__given_infinity_string__returns_valid_dict(self):
        input_data = {
            "2023-01-01.2023-12-31": "Infinity",
            "2024-01-01.2024-12-31": "-Infinity",
        }

        result = ParameterChangeDict(root=input_data)

        assert isinstance(result, ParameterChangeDict)
        assert result.root == {
            "2023-01-01.2023-12-31": np.inf,
            "2024-01-01.2024-12-31": -np.inf,
        }

    def test_schema__given_invalid_date_format__raises_validation_error(self):
        input_data = {"2023-01-01.2023-12-31": 0.1, "invalid_date_format": 0.2}

        with pytest.raises(
            ValidationError, match="Invalid date format in key"
        ):
            ParameterChangeDict(root=input_data)

    def test_schema__given_invalid_key_type__raises_validation_error(self):
        input_data = {123: 0.1, "2024-01-01.2024-12-31": 0.2}

        with pytest.raises(
            ValidationError, match="validation error for ParameterChangeDict"
        ):
            ParameterChangeDict(root=input_data)


class TestParametricReform:
    def test_schema__given_valid_dict__returns_valid_reform(self):
        input_data = {
            "parameter1": {
                "2023-01-01.2023-12-31": 0.1,
                "2024-01-01.2024-12-31": 0.2,
            },
            "parameter2": {
                "2023-01-01.2023-12-31": 0.3,
                "2024-01-01.2024-12-31": 0.4,
            },
        }

        expected_output_data = {
            "parameter1": ParameterChangeDict(
                root={
                    "2023-01-01.2023-12-31": 0.1,
                    "2024-01-01.2024-12-31": 0.2,
                }
            ),
            "parameter2": ParameterChangeDict(
                root={
                    "2023-01-01.2023-12-31": 0.3,
                    "2024-01-01.2024-12-31": 0.4,
                }
            ),
        }

        result = ParametricReform(root=input_data)

        assert isinstance(result, ParametricReform)
        assert result.root == expected_output_data

    def test_schema__given_invalid_key_type__raises_validation_error(self):
        input_data = {
            123: {"2023-01-01.2023-12-31": 0.1, "2024-01-01.2024-12-31": 0.2},
            "valid_parameter": {
                "2023-01-01.2023-12-31": 0.3,
                "2024-01-01.2024-12-31": 0.4,
            },
        }

        with pytest.raises(
            ValidationError, match=r"validation errors? for ParametricReform"
        ):
            ParametricReform(root=input_data)

    def test_schema__given_dateless_structure__raises_validation_error(self):
        input_data = {"parameter1": 0.1, "parameter2": 0.2}

        with pytest.raises(
            ValidationError, match=r"validation errors? for ParametricReform"
        ):
            ParametricReform(root=input_data)
