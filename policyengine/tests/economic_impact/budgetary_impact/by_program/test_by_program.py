import pytest
import yaml
import os
from policyengine import EconomicImpact

def assert_dict_approx_equal(actual, expected, tolerance=1e3):
    for key in expected:
        assert abs(actual[key] - expected[key]) < tolerance, f"Key {key}: expected {expected[key]}, got {actual[key]}"


yaml_file_path = "policyengine/tests/economic_impact/budgetary_impact/by_program/by_program.yaml"

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
    
    if 'income_tax' in test_name:
        result = economic_impact.calculate("budgetary/by_program/income_tax")
    elif 'national_insurance' in test_name:
        result = economic_impact.calculate("budgetary/by_program/national_insurance")
    elif 'vat' in test_name:
        result = economic_impact.calculate("budgetary/by_program/vat")
    elif 'council_tax' in test_name:
        result = economic_impact.calculate("budgetary/by_program/council_tax")
    elif 'fuel_duty' in test_name:
        result = economic_impact.calculate("budgetary/by_program/fuel_duty")
    elif 'tax_credits' in test_name:
        result = economic_impact.calculate("budgetary/by_program/tax_credits")
    elif 'universal_credits' in test_name:
        result = economic_impact.calculate("budgetary/by_program/universal_credits")
    elif 'child_benefits' in test_name:
        result = economic_impact.calculate("budgetary/by_program/child_benefits")
    elif 'state_pension' in test_name:
        result = economic_impact.calculate("budgetary/by_program/state_pension")
    elif 'pension_credit' in test_name:
        result = economic_impact.calculate("budgetary/by_program/pension_credit")
    else:
        pytest.fail(f"Unknown test case: {test_name}")
    
    assert_dict_approx_equal(result, test_data['expected'])

if __name__ == "__main__":
    pytest.main([__file__])
