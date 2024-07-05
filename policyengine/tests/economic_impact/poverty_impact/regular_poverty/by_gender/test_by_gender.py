import pytest
import yaml
import os
from policyengine import EconomicImpact

def assert_dict_approx_equal(actual, expected, tolerance=1e-4):
    for key in expected:
        assert abs(actual[key] - expected[key]) < tolerance, f"Key {key}: expected {expected[key]}, got {actual[key]}"


yaml_file_path = "policyengine/tests/economic_impact/poverty_impact/regular_poverty/by_gender/by_gender.yaml"

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
    
    if test_name.startswith('female'):
     result = economic_impact.calculate("poverty/regular/female")
    elif test_name.startswith('male'):
        result = economic_impact.calculate("poverty/regular/male")
    elif 'all' in test_name:
        result = economic_impact.calculate("poverty/regular/gender/all")
    else:
     pytest.fail(f"Unknown test case: {test_name}")

    assert_dict_approx_equal(result, test_data['expected'])

if __name__ == "__main__":
    pytest.main([__file__])
