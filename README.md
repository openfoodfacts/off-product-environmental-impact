# Environmental impact estimation of Open Food Facts products

This repository contains a Python program to estimate the environmental impact of a product of the Open Food Facts database.


## Installation
This program uses the [PySCIPOpt](https://github.com/SCIP-Interfaces/PySCIPOpt) package and the [SCIP Optimization Suite](http://scip.zib.de/).
Installation instructions can be found [here (PySCIPOpt)](https://github.com/SCIP-Interfaces/PySCIPOpt/blob/master/INSTALL.md) and [here (SCIP)](https://www.scipopt.org/doc/html/INSTALL.php).

See [requirements.txt](requirements.txt) for the other required Python packages.

## Usage
Impact estimation of a product can be done using `impact_estimation.estimate_impacts()`.

```python
from impacts_estimation import estimate_impacts
from openfoodfacts import get_product

product = get_product(barcode='3175681790285')['product']

impact_categories = ['Score unique EF',
                     'Changement climatique']

impact_estimation_result = estimate_impacts(product=product,
                                            impact_names=impact_categories)

for impact_category in impact_categories:
    print(f"{impact_category}: "
          f"{impact_estimation_result['impact_geom_means'][impact_category]:.4} "
          f"{impact_estimation_result['impacts_units'][impact_category]}")
# Score unique EF: 0.07872 mPt
# Changement climatique: 0.7816 kg CO2 eq
```

`impact_estimation.estimate_impacts_safe()` will change the parameters in case of error to ensure getting a result. 
```python
from impacts_estimation import estimate_impacts, estimate_impacts_safe, RecipeCreationError
from openfoodfacts import get_product

product = get_product(barcode='3564707104920')['product']

try:
    impact_estimation_result = estimate_impacts(product=product,
                                                impact_names='Score unique EF')
except RecipeCreationError:
    print("No possible recipe with the given input data.")
# No possible recipe with the given input data.

impact_estimation_result = estimate_impacts_safe(product=product,
                                                 impact_names='Score unique EF')

print(impact_estimation_result['impact_geom_means']['Score unique EF'])
# 0.16486248336651319

print(impact_estimation_result['warnings'])
# ['Parameter use_defined_prct has been set to False in order to get a result.']
``` 

### Parameters
TODO: ajouter tableau paramètres