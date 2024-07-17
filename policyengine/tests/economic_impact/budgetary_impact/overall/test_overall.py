import pytest
import yaml
import os
from policyengine import EconomicImpact

def assert_dict_approx_equal(actual, expected, tolerance=1e3):
    for key in expected:
        assert abs(actual[key] - expected[key]) < tolerance, f"Key {key}: expected {expected[key]}, got {actual[key]}"


yaml_file_path = "policyengine/tests/economic_impact/budgetary_impact/overall/overall.yaml"

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
    
    if 'budgetary' in test_name:
        result = economic_impact.calculate("budgetary/overall/budgetary_impact")
    elif 'benefit' in test_name:
        result = economic_impact.calculate("budgetary/overall/benefit_spending_impact")
    elif 'tax' in test_name:
        result = economic_impact.calculate("budgetary/overall/tax_revenue_impact")
    else:
        pytest.fail(f"Unknown test case: {test_name}")
    
    assert_dict_approx_equal(result, test_data['expected'])

if __name__ == "__main__":
    pytest.main([__file__])