""" Retrieving Agribalyse impacts from linked LCIs to give impact to OFF ingredients """

import json
from statistics import mean, stdev

from scipy.stats import gmean, gstd

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.vars import AGRIBALYSE_DATA_FILEPATH
from impacts_estimation.vars import IMPACT_MASS_UNIT

with open(INGREDIENTS_DATA_FILEPATH, 'r') as file:
    ingredients_data = json.load(file)

with open(AGRIBALYSE_DATA_FILEPATH, 'r') as file:
    agribalyse_impacts = json.load(file)
agribalyse_impacts = {x['LCI_name']: x for x in agribalyse_impacts}

# Choosing only steps corresponding to raw material production and transformation, not packaging or transport
STEPS_TO_INCLUDE = [
    'Agriculture',
    'Transformation',
    # 'Emballage',
    # 'Transport',
    # 'Supermarché et distribution',
    # 'Consommation'
]

for ingredient in ingredients_data.values():
    if 'LCI' in ingredient:
        ingredient['impacts'] = dict()
        impacts = dict()

        # Retrieving the impacts of the corresponding LCIs
        for process_name in ingredient['LCI']:

            process_impacts = agribalyse_impacts[process_name]['impact_environnemental']

            for impact_category, impact_data in process_impacts.items():
                if impact_category not in impacts:
                    impacts[impact_category] = []

                impacts[impact_category].append(sum([v
                                                     for k, v
                                                     in impact_data['etapes'].items()
                                                     if k in STEPS_TO_INCLUDE]))

                if impact_category not in ingredient['impacts']:
                    ingredient['impacts'][impact_category] = dict()

                # Agribalyse impacts are given per 1kg of product.
                #  If using a different source, ensure of consistency
                assert (IMPACT_MASS_UNIT == 1000) and ('/kg de produit' in impact_data['unite'])
                ingredient['impacts'][impact_category]['unit'] = impact_data['unite'].replace('/kg de produit', '')

        # Adding the impact values to the ingredient
        for impact_category, values in impacts.items():

            # If there is only one value or if all impact values are identical, don't add uncertainty data
            if len(set(values)) == 1:
                ingredient['impacts'][impact_category]['amount'] = values[0]

            # If there are more than one value, add uncertainty data
            # If there are only positive/negative values, use a log-normal distribution
            # If there are both positive and negative values, use a normal distribution
            elif min(values) > 0:
                ingredient['impacts'][impact_category]['amount'] = gmean(values)
                ingredient['impacts'][impact_category]['uncertainty'] = 'lognormal'
                ingredient['impacts'][impact_category]['geometric mean'] = gmean(values)
                ingredient['impacts'][impact_category]['geometric standard deviation'] = gstd(values)

            elif max(values) < 0:
                pos_values = [-x for x in values]

                ingredient['impacts'][impact_category]['amount'] = -gmean(pos_values)
                ingredient['impacts'][impact_category]['uncertainty'] = 'lognormal'
                ingredient['impacts'][impact_category]['geometric mean'] = -gmean(pos_values)
                ingredient['impacts'][impact_category]['geometric standard deviation'] = gstd(pos_values)

            else:
                ingredient['impacts'][impact_category]['amount'] = mean(values)
                ingredient['impacts'][impact_category]['uncertainty'] = 'normal'
                ingredient['impacts'][impact_category]['mean'] = mean(values)
                ingredient['impacts'][impact_category]['standard deviation'] = stdev(values)

with open(INGREDIENTS_DATA_FILEPATH, 'w') as file:
    json.dump(ingredients_data, file, indent=2, ensure_ascii=False)
