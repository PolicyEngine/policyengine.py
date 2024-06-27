# EconomicImpact Class

## Overview

The `EconomicImpact` class is designed to evaluate the economic impact of a given reform on a specified country. It provides methods to calculate various economic metrics, such as inequality and income distribution, before and after the reform.

## Class Initialization

### `EconomicImpact(reform, country)`

Initializes the `EconomicImpact` class with a specified reform and country.

**Parameters:**
- `reform` (dict): A dictionary defining the economic reform. The structure of the dictionary should match the expected format for the `Reform` class.
- `country` (str): The country for which the reform's impact is to be evaluated. Supported values are `"uk"` and `"us"`.

**Example:**
```python
from policyengine import EconomicImpact

impact = EconomicImpact(
    reform={"gov.hmrc.income_tax.rates.uk[0].rate": {"2024-01-01": 0.25}},
    country="uk"
)
```


## Example Usage

```python
from policyengine import EconomicImpact

# Initialize the EconomicImpact class
impact = EconomicImpact(
    reform={"gov.hmrc.income_tax.rates.uk[0].rate": {"2024-01-01": 0.25}},
    country="uk"
)

# Calculate the Gini coefficient
result_gini = impact.calculate("inequality/gini")
print(result_gini)
# Output: {'baseline': 0.4288962129322326, 'reform': 0.42720356179075414, 'change': -0.001692651141478485}

# Calculate the top 1% income share
result_top_1 = impact.calculate("inequality/top_1_pct_share")
print(result_top_1)
# Output: {'baseline': 0.09121853588608866, 'reform': 0.09301056461517446, 'change': 0.0017920287290857928}

# Calculate the top 10% income share
result_top_10 = impact.calculate("inequality/top_10_pct_share")
print(result_top_10)
# Output: {'baseline': 0.3101681771998754, 'reform': 0.31214840219992496, 'change': 0.0019802250000495736}
```