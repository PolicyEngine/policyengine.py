import pytest
import yaml
import os
from policyengine import EconomicImpact

def assert_dict_approx_equal(actual, expected, tolerance=1e-4):
    assert set(actual.keys()) == set(expected.keys()), f"Keys don't match. Actual: {actual.keys()}, Expected: {expected.keys()}"
    for key in expected:
        if isinstance(expected[key], dict):
            assert_dict_approx_equal(actual[key], expected[key], tolerance)
        else:
            assert abs(actual[key] - expected[key]) < tolerance, f"Key {key}: expected {expected[key]}, got {actual[key]}"

yaml_file_path = "policyengine/tests/economic_impact/distributional_impact/by_wealth/average/average.yaml"

# Check if the file exists
if not os.path.exists(yaml_file_path):
    raise FileNotFoundError(f"The YAML file does not exist at: {yaml_file_path}")

with open(yaml_file_path, 'r') as file:
    test_cases = yaml.safe_load(file)

@pytest.mark.parametrize("test_case", test_cases)
def test_economic_impact(test_case):
    test_name = list(test_case.keys())[0]
    test_data = test_case[test_name]
    
    economic_impact = EconomicImpact(test_data['reform'], test_data['country'])
    
    if 'average' in test_name:
        result = economic_impact.calculate("distributional/by_wealth/average")
    else:
        pytest.fail(f"Unknown test case: {test_name}")
    
    assert_dict_approx_equal(result, test_data['expected'])

if __name__ == "__main__":
    pytest.main([__file__])