""" Retrieving Agribalyse impacts from linked LCIs to give impact to OFF ingredients """

import json
from statistics import mean

from scipy.stats import gmean

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.vars import AGRIBALYSE_DATA_FILEPATH
from impacts_estimation.vars import IMPACT_MASS_UNIT, AGRIBALYSE_IMPACT_UNITS


def main():
    with open(INGREDIENTS_DATA_FILEPATH, 'r', encoding='utf8') as file:
        ingredients_data = json.load(file)

    with open(AGRIBALYSE_DATA_FILEPATH, 'r', encoding='utf8') as file:
        agribalyse_impacts = json.load(file)
    agribalyse_impacts = {x['LCI_name']: x for x in agribalyse_impacts}

    # Choosing only steps corresponding to raw material production and transformation, not packaging or transport
    STEPS_TO_INCLUDE = [
        'Agriculture',
        # 'Transformation',
        # 'Emballage',
        # 'Transport',
        # 'Supermarché et distribution',
        # 'Consommation'
    ]

    for ingredient in ingredients_data.values():
        if 'environmental_impact_data_sources' in ingredient:
            ingredient['impacts'] = dict()
            lcis_impacts = dict()

            # Retrieving the impacts of the corresponding LCIs
            process_names = [x['entry']
                             for x in ingredient['environmental_impact_data_sources']
                             if x['database'] == 'agribalyse']
            for process_name in process_names:
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
                    ingredient['impacts'][impact_category]['unit'] = AGRIBALYSE_IMPACT_UNITS[impact_category]

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
            if len(ingredient['environmental_impact_data_sources']) > 1:
                for process_name in process_names:

                    # For each impact, adding one uniform uncertainty distribution per LCI
                    # Given that uncertainty data is not known fo Agribalyse processes, a uniform distribution with same
                    # minimum and maximum is used to still allow the algorithm to pick a random value in cases of
                    # multiple LCIs corresponding to one ingredient.
                    for impact_category, impacts in lcis_impacts.items():
                        # If all linked LCIs have the same impact, don't add uncertainty to this ingredient
                        if all(impacts[x] == impacts[process_name] for x in process_names):
                            continue

                        distribution_data = {'distribution': 'uniform',
                                             'minimum': impacts[process_name],
                                             'maximum': impacts[process_name]}

                        if 'uncertainty_distributions' not in ingredient['impacts'][impact_category]:
                            ingredient['impacts'][impact_category]['uncertainty_distributions'] = []

                        ingredient['impacts'][impact_category]['uncertainty_distributions'].append(distribution_data)

    with open(INGREDIENTS_DATA_FILEPATH, 'w', encoding='utf8') as file:
        json.dump(ingredients_data, file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
