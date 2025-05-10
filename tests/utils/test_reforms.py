from pydantic import ValidationError
import pytest
import numpy as np

from policyengine.utils.reforms import (
    ParameterChangeDict,
    ParametricReform,
    ParameterChangeValue,
)


class TestParameterChangeDict:
    def test_schema__given_float_inputs__returns_valid_dict(self):
        input_data = {
            "2023-01-01.2023-12-31": 0.1,
            "2024-01-01.2024-12-31": 0.2,
        }

        expected_output_data = {
            "2023-01-01.2023-12-31": ParameterChangeValue(root=0.1),
            "2024-01-01.2024-12-31": ParameterChangeValue(root=0.2),
        }

        result = ParameterChangeDict(root=input_data)

        assert isinstance(result, ParameterChangeDict)
        assert result.root == expected_output_data

    def test_schema__given_string_inputs__returns_valid_dict(self):
        input_data = {
            "2023-01-01.2023-12-31": "0.1",
            "2024-01-01.2024-12-31": "0.2",
        }

        expected_output_data = {
            "2023-01-01.2023-12-31": ParameterChangeValue(root="0.1"),
            "2024-01-01.2024-12-31": ParameterChangeValue(root="0.2"),
        }

        result = ParameterChangeDict(root=input_data)

        assert isinstance(result, ParameterChangeDict)
        assert result.root == expected_output_data

    def test_schema__given_infinity_string__returns_valid_dict(self):
        input_data = {
            "2023-01-01.2023-12-31": "Infinity",
            "2024-01-01.2024-12-31": "-Infinity",
        }

        expected_output_data = {
            "2023-01-01.2023-12-31": ParameterChangeValue(root=np.inf),
            "2024-01-01.2024-12-31": ParameterChangeValue(root=-np.inf),
        }

        result = ParameterChangeDict(root=input_data)

        assert isinstance(result, ParameterChangeDict)
        assert result.root == expected_output_data

    def test_schema__given_yearly_input__returns_valid_dict(self):
        input_data = {
            "2023": 0.1,
            "2024": 0.2,
        }

        expected_output_data = {
            "2023": ParameterChangeValue(root=0.1),
            "2024": ParameterChangeValue(root=0.2),
        }

        result = ParameterChangeDict(root=input_data)

        assert isinstance(result, ParameterChangeDict)
        assert result.root == expected_output_data

    def test_schema__given_invalid_date_format__raises_validation_error(self):
        input_data = {"2023-01-01.2023-12-31": 0.1, "invalid_date_format": 0.2}

        with pytest.raises(
            ValidationError,
            match=r"validation errors? for ParameterChangeDict",
        ):
            ParameterChangeDict(root=input_data)

    def test_schema__given_non_date_key_type__raises_validation_error(self):
        input_data = {123: 0.1, "2024-01-01.2024-12-31": 0.2}

        with pytest.raises(
            ValidationError, match="validation error for ParameterChangeDict"
        ):
            ParameterChangeDict(root=input_data)

    def test_schema__given_incorrect_date_key_type__raises_validation_error(
        self,
    ):
        input_data = {
            "2023-01-01.2023-12-31": 0.1,
            "2024-01-01.2024-12-31": 0.2,
            "2024.01.01-2025.12.31": 0.3,
        }

        with pytest.raises(
            ValidationError, match="validation error for ParameterChangeDict"
        ):
            ParameterChangeDict(root=input_data)


class TestParameterChangeValue:
    def test_schema__given_float_input__returns_valid_value(self):
        input_data = 0.1

        result = ParameterChangeValue(root=input_data)

        assert isinstance(result, ParameterChangeValue)
        assert result.root == input_data

    def test_schema__given_string_input__returns_valid_value(self):
        input_data = "0.1"

        result = ParameterChangeValue(root=input_data)

        assert isinstance(result, ParameterChangeValue)
        assert result.root == input_data

    def test_schema__given_bool_input__returns_valid_value(self):
        input_data = True

        result = ParameterChangeValue(root=input_data)

        assert isinstance(result, ParameterChangeValue)
        assert result.root == input_data

    def test_schema__given_infinity_string__returns_valid_value(self):
        input_data = "Infinity"

        result = ParameterChangeValue(root=input_data)

        assert isinstance(result, ParameterChangeValue)
        assert result.root == float("inf")

    def test_schema__given_negative_infinity_string__returns_valid_value(self):
        input_data = "-Infinity"

        result = ParameterChangeValue(root=input_data)

        assert isinstance(result, ParameterChangeValue)
        assert result.root == float("-inf")

    def test_schema__given_invalid_type__raises_validation_error(self):
        input_data = [0.1, 0.2]

        with pytest.raises(
            ValidationError, match="validation error for ParameterChangeValue"
        ):
            ParameterChangeValue(root=input_data)

    def test_schema__given_dict_input__raises_validation_error(self):
        input_data = {"key": "value"}

        with pytest.raises(
            ValidationError, match="validation error for ParameterChangeValue"
        ):
            ParameterChangeValue(root=input_data)


class TestParametricReform:
    def test_schema__given_full_date_dict__returns_valid_reform(self):
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

    def test_schema__given_yearly_dict__returns_valid_reform(self):
        input_data = {
            "parameter1": {"2023": 0.1, "2024": 0.2},
            "parameter2": {"2023": 0.3, "2024": 0.4},
        }

        expected_output_data = {
            "parameter1": ParameterChangeDict(root={"2023": 0.1, "2024": 0.2}),
            "parameter2": ParameterChangeDict(root={"2023": 0.3, "2024": 0.4}),
        }

        result = ParametricReform(root=input_data)

        assert isinstance(result, ParametricReform)
        assert result.root == expected_output_data

    def test_schema__given_single_value_dict__returns_valid_reform(self):
        input_data = {
            "parameter1": 0.1,
            "parameter2": 0.2,
        }

        expected_output_data = {
            "parameter1": ParameterChangeValue(root=0.1),
            "parameter2": ParameterChangeValue(root=0.2),
        }

        result = ParametricReform(root=input_data)

        assert isinstance(result, ParametricReform)
        assert result.root == expected_output_data

    def test_schema__given_mixed_dict__returns_valid_reform(self):
        input_data = {
            "parameter1": {
                "2023-01-01.2023-12-31": 0.1,
                "2024-01-01.2024-12-31": 0.2,
            },
            "parameter2": 0.3,
        }

        expected_output_data = {
            "parameter1": ParameterChangeDict(
                root={
                    "2023-01-01.2023-12-31": 0.1,
                    "2024-01-01.2024-12-31": 0.2,
                }
            ),
            "parameter2": ParameterChangeValue(root=0.3),
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
