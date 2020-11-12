""" Retrieving Agribalyse impacts from linked LCIs to give impact to OFF ingredients """

import json
from statistics import mean, stdev

from scipy.stats import gmean, gstd

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.vars import AGRIBALYSE_DATA_FILEPATH
from ingredients_characterization.impact.utils import gsd_from_dqr
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
        lcis_impacts = dict()
        lcis_dqrs = dict()

        # Retrieving the impacts of the corresponding LCIs
        for process_name in ingredient['LCI']:
            process_impacts = agribalyse_impacts[process_name]['impact_environnemental']

            for impact_category, impact_data in process_impacts.items():
                if impact_category not in lcis_impacts:
                    lcis_impacts[impact_category] = dict()

                lcis_impacts[impact_category][process_name] = sum([v
                                                                   for k, v
                                                                   in impact_data['etapes'].items()
                                                                   if k in STEPS_TO_INCLUDE])

                if impact_category not in ingredient['impacts']:
                    ingredient['impacts'][impact_category] = dict()

                # Agribalyse impacts are given per 1kg of product.
                #  If using a different source, ensure of consistency
                assert (IMPACT_MASS_UNIT == 1000) and ('/kg de produit' in impact_data['unite'])
                ingredient['impacts'][impact_category]['unit'] = impact_data['unite'].replace('/kg de produit', '')

        # Adding the impact values to the ingredient
        for impact_category, impacts in lcis_impacts.items():

            # If there is only one value or if all impact values are identical, don't add compute mean
            if len(set(impacts.values())) == 1:
                ingredient['impacts'][impact_category]['amount'] = list(impacts.values())[0]

            # If there are more than one value, compute a mean of the values
            # If there are only positive/negative values, use a geometric mean
            # If there are both positive and negative values, use an arithmetic mean
            elif min(impacts.values()) > 0:
                ingredient['impacts'][impact_category]['amount'] = gmean(list(impacts.values()))

            elif max(impacts.values()) < 0:
                pos_values = [-x for x in impacts.values()]

                ingredient['impacts'][impact_category]['amount'] = -gmean(pos_values)

            else:
                ingredient['impacts'][impact_category]['amount'] = mean(impacts.values())

        # Adding the impact uncertainty distributions to the ingredient
        for process_name in ingredient['LCI']:

            # Computing the geometric standard deviation from the DQR
            dqr_data = agribalyse_impacts[process_name]['DQR']
            gsd = gsd_from_dqr(precision=dqr_data['P'],
                               temp_repr=dqr_data['TiR'],
                               geo_repr=dqr_data['GR'],
                               tech_repr=dqr_data['TeR'])

            # For each impact, adding one log-normal uncertainty distribution per LCI
            for impact_category, impacts in lcis_impacts.items():
                # Skip if the impact value is null
                if impacts[process_name] == 0:
                    continue

                distribution_data = {'distribution': 'lognormal',
                                     'geometric mean': impacts[process_name],
                                     'geometric standard deviation': gsd}

                if 'uncertainty_distributions' not in ingredient['impacts'][impact_category]:
                    ingredient['impacts'][impact_category]['uncertainty_distributions'] = []

                ingredient['impacts'][impact_category]['uncertainty_distributions'].append(distribution_data)

            # If all linked LCIs have the same DQR and the same impact, only add one
            all_same = True
            for other_process_name in [x for x in ingredient['LCI'] if x != process_name]:
                if agribalyse_impacts[other_process_name]['DQR'] != agribalyse_impacts[process_name]['DQR']:
                    all_same = False
                    break

                for impact_category, impacts in lcis_impacts.items():
                    if impacts[other_process_name] != impacts[process_name]:
                        all_same = False
                        break

            if all_same:
                break

with open(INGREDIENTS_DATA_FILEPATH, 'w') as file:
    json.dump(ingredients_data, file, indent=2, ensure_ascii=False)
