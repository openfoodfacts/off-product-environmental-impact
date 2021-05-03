# Environmental impact estimation of Open Food Facts products

This repository contains a Python program to estimate the environmental impact of a product of the Open Food Facts
database.

## Installation

This program uses the [PySCIPOpt](https://github.com/SCIP-Interfaces/PySCIPOpt) package and
the [SCIP Optimization Suite](http://scip.zib.de/). Installation instructions can be
found [here (PySCIPOpt)](https://github.com/SCIP-Interfaces/PySCIPOpt/blob/master/INSTALL.md)
and [here (SCIP)](https://www.scipopt.org/doc/html/INSTALL.php).

See [requirements.txt](requirements.txt) for the other required Python packages.

## Usage

Impact estimation of a product can be done using `impacts_estimation.estimate_impacts()`.

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

If `safe_mode` is set to `True`, it will change the parameters in case of error to ensure getting a result.

```python
from impacts_estimation import estimate_impacts, RecipeCreationError
from openfoodfacts import get_product

product = get_product(barcode='3564707104920')['product']

try:
    impact_estimation_result = estimate_impacts(product=product,
                                                impact_names='Score unique EF',
                                                safe_mode=False)
except RecipeCreationError:
    print("No possible recipe with the given input data.")
# No possible recipe with the given input data.

impact_estimation_result = estimate_impacts(product=product,
                                            impact_names='Score unique EF',
                                            safe_mode=True)

print(impact_estimation_result['impact_geom_means']['Score unique EF'])
# 0.16486248336651319

print(impact_estimation_result['warnings'])
# ['Parameter use_defined_prct has been set to False in order to get a result.']
``` 

### Parameters

The function `impacts_estimation.estimate_impacts()` accepts the following parameters:

| Parameter                            | Type                   | Default                                  | Description                                                                                                                                                                                                                               |
|--------------------------------------|------------------------|------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `product`                            | `dict`                 |                                          | Open Food Facts product to analyze                                                                                                                                                                                                        |
| `impact_names`                       | `string` or `iterable` |                                          | Names of the impacts to compute. They must correspond to the impact categories used by Agribalyse. See [list of available impact categories](#available-environmental-impact-categories).                                                                    |
| `quantity`                           | `float`                | `100`                                    | Quantity of product in grams for which the impact must be calculated. If None, will use the 'product_quantity' attribute of the product. If 'product_quantity' is undefined, will use 100g by default.                                    |
| `ignore_unknown_ingredients`         | `bool`                 | `True`                                   | Should ingredients absent of OFF taxonomy and without defined percentage be considered as parsing errors and ignored?                                                                                                                     |
| `min_run_nb`                         | `int`                  | `30`                                     | Minimum number of run for the Monte-Carlo loop                                                                                                                                                                                            |
| `max_run_nb`                         | `int`                  | `1000`                                   | Maximum number of run for the Monte-Carlo loop                                                                                                                                                                                            |
| `forced_run_nb`                      | `int`                  | `None`                                   | Used to bypass natural Monte-Carlo stopping criteria and force the number of runs                                                                                                                                                         |
| `confidence_interval_width`          | `float`                | `0.05`                                   | Width of the confidence interval that will determine the convergence detection.                                                                                                                                                           |
| `confidence_level`                   | `float`                | `0.95`                                   | Confidence level of the confidence interval.                                                                                                                                                                                              |
| `use_nutritional_info`               | `bool`                 | `True`                                   | Should nutritional information be used to estimate recipe?                                                                                                                                                                                |
| `maximum_evaporation`                | `float`                | `0.8`                                    | Upper bound of the evaporation coefficient [0-1[. I.e. maximum proportion of ingredients water that can evaporate.                                                                                                                        |
| `total_mass_used`                    | `float`                | `None`                                   | Total mass of ingredient used in grams, if known.                                                                                                                                                                                         |
| `min_prct_dist_size`                 | `int`                  | `30`                                     | Minimum size of the ingredients percentage distribution that will be used to pick a proportion for an ingredient. If the distribution (adjusted to the possible value interval) has less data, uniform distribution will be used instead. |
| `dual_gap_type`                      | `str`                  | `'absolute'`                             | 'absolute' or 'relative'. Determines the precision type of the variable optimization by the solver.                                                                                                                                       |
| `dual_gap_limit`                     | `float`                | `0.001`                                  | Determines the precision of the variable optimization by the solver. Relative or absolute according to dual_gap_type.                                                                                                                     |
| `solver_time_limit`                  | `float`                | `60`                                     | Maximum time for the solver optimization (in seconds). Set to None or 0 to set no limit.                                                                                                                                                  |
| `time_limit_dual_gap_limit`          | `float`                | `0.01`                                   | Accepted precision of the solver in case of time limit hit. Relative or absolute according to dual_gap_type                                                                                                                               |
| `use_ingredients_impact_uncertainty` | `bool`                 | `True`                                   | Should ingredients impacts uncertainty data be used?                                                                                                                                                                                      |
| `confidence_weighting`               | `bool`                 | `True`                                   | Should the recipes be weighted by their confidence score (deviation of the recipes nutritional composition to the reference product).                                                                                                     |
| `quantiles_points`                   | `iterable`             | `(0.05, 0.25, 0.5, 0.75, 0.95)` | List of impacts quantiles cutting points to return in the result.                                                                                                                                                                         |                                                          |

### Result

The result of `impacts_estimation.estimate_impacts()` is a dictionary containing the calculated impacts as well as
several additional data.

| Key                                           | Description                                                                                                                                  |
|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `impact_geom_means`                           | __Geometric means of the impacts of all sampled recipes in each impact
category.__ The main result.                                          |
| `impact_geom_stdevs`                          | Geometric standard deviations of the impacts of all sampled recipes in each impact category.                                                 |
| `impacts_quantiles`                           | Quantiles of the impacts of all sampled recipes in each impact category. Cutting points are defined by `quantiles_points`.                   |
| `impacts_relative_interquartile`                       | Relative interquartile of the impacts of all sampled recipes in each impact category. Useful to estimate the spread of the possible impact. |
| `ingredients_impact_share`                    | Average share of the impact carried by each ingredient for each impact category.                                                             |
| `impacts_units`                               | Units in which the impacts are expressed.                                                                                                    |
| `product_quantity`                            | Quantity of product in grams for which the impact have been calculated.                                                                      |
| `warnings`                                    | List of possible text warnings.                                                                                                              |
| `ignored_unknown_ingredients`                 | List of ingredients that have been ignored if `ignore_unknown_ingredients` have been set to `True`.                                          |
| `uncharacterized_ingredients`                 | List of ingredients with no data about nutrition and/or environmental impact.                                                                |
| `uncharacterized_ingredients_ratio`           | Ratio ingredients with no data about nutrition and/or environmental impact.                                                                  |
| `uncharacterized_ingredients_mass_proportion` | Average mass proportion of ingredients with no data about nutrition and/or environmental impact.                                             |
| `number_of_runs`                              | Number of runs before impact convergence.                                                                                                    |
| `number_of_ingredients`                       | Number of ingredients of the product.                                                                                                        |
| `calculation_time`                            | Impact calculation time.                                                                                                                     |
| `impact_distributions`                        | Distributions of the impacts of all sampled recipes in each impact category.                                                                 |
| `mean_confidence_interval_distribution`       | Distributions of the confidence interval of the mean of the impacts of all sampled recipes in each impact category.                          |
| `confidence_score_distribution`               | Distributions of the confidence score of all sampled recipes.                                                                                |

### Available environmental impact categories

The ingredients environmental impact data come from [_Agribalyse_](https://ecolab.ademe.fr/agribalyse). The impact
categories are:

| Agribalyse name                                     |                                           |
|-----------------------------------------------------|-------------------------------------------|
| Score unique EF                                     | Single score EF (Environmental Footprint) |
| Changement climatique                               | Climate change                            |
| Appauvrissement de la couche d'ozone                | Ozone depletion                           |
| Rayonnements ionisants                              | Ionizing radiations                       |
| Formation photochimique d'ozone                     | Photochemical ozone formation             |
| Particules                                          | Particulate matter                        |
| Acidification terrestre et eaux douces              | Terrestrial and freshwater acidification  |
| Eutrophisation terreste                             | Terrestrial eutrophication                |
| Eutrophisation eaux douces                          | Freshwater eutrophication                 |
| Eutrophisation marine                               | Marine eutrophication                     |
| Utilisation du sol                                  | Land use                                  |
| Écotoxicité pour écosystèmes aquatiques d'eau douce | Freshwater ecotoxicity                    |
| Épuisement des ressources eau                       | Water depletion                           |
| Épuisement des ressources énergétiques              | Resource use, energy carriers             |
| Épuisement des ressources minéraux                  | Resource use, minerals and metals         |

### Algorithm

The algorithm used by this program is based on a Monte-Carlo approach to estimate the impact of a product. Its principle
is to pick random possible recipes of the product and compute their impact until the geometric mean of the impacts of
all sampled recipes stabilizes within a given confidence interval. The sampling of possible recipes is made as accurate
as possible by the use of a non linear programming solver ([SCIP](http://scip.zib.de/)), and nutritional information of
the product.

## Disclaimer

The results given by this tool are **estimates** of the environmental impact of a food product. These estimates are
subject to potential bias and uncertainties due to the stochastic nature of the algorithm and the uncertainty inherent
to the background data. Thus, the accuracy of the result cannot be guaranteed.

## References

[_ADEME - Agribalyse_](https://ecolab.ademe.fr/agribalyse), 2020

[_Anses - Table de composition nutritionnelle des aliments Ciqual_](https://ciqual.anses.fr/), 2020

[_Santé Canada - Fichier canadien sur les éléments
nutritifs_](https://www.canada.ca/fr/sante-canada/services/aliments-nutrition/saine-alimentation/donnees-nutritionnelles/fichier-canadien-elements-nutritifs-propos-nous.html)
, 2015

[_The SCIP Optimization Suite_](https://scipopt.org/)