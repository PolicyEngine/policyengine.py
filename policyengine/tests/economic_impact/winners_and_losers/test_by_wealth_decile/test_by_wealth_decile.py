import pytest
import yaml
import os
from policyengine import EconomicImpact

def assert_dict_approx_equal(actual, expected, tolerance=5e-2):
    if isinstance(expected, dict):
        for key in expected:
            assert_dict_approx_equal(actual[key], expected[key], tolerance)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), f"List length mismatch: expected {len(expected)}, got {len(actual)}"
        for a, e in zip(actual, expected):
            assert abs(a - e) < tolerance, f"Expected {e}, got {a}"
    else:
        assert abs(actual - expected) < tolerance, f"Expected {expected}, got {actual}"

yaml_file_path = "policyengine/tests/economic_impact/winners_and_losers/test_by_wealth_decile/by_wealth_decile.yaml"

# Check if the file exists
if not os.path.exists(yaml_file_path):
    raise FileNotFoundError(f"The YAML file does not exist at: {yaml_file_path}")

with open(yaml_file_path, 'r') as file:
    test_cases = yaml.safe_load(file)

@pytest.mark.parametrize("test_case", test_cases)
def test_economic_impact(test_case):
    test_name = list(test_case.keys())[0]
    test_data = test_case[test_name]
    
    if test_name != 'wealth_impact_test':
        pytest.skip(f"Skipping non-wealth test: {test_name}")
    
    economic_impact = EconomicImpact(test_data['reform'], test_data['country'])
    result = economic_impact.calculate("winners_and_losers/by_wealth_decile")

    assert_dict_approx_equal(result['result'], test_data['expected'])

if __name__ == "__main__":
    pytest.main([__file__])