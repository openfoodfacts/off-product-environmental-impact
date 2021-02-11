""" Script to link CIQUAL nutritional data to OFF ingredients """

import json
from statistics import mean
import copy

import pandas as pd

from ingredients_characterization.vars import CIQUAL_DATA_FILEPATH, CIQUAL_OFF_LINKING_TABLE_FILEPATH
from data import INGREDIENTS_DATA_FILEPATH

links = pd.read_csv(CIQUAL_OFF_LINKING_TABLE_FILEPATH)

with open(CIQUAL_DATA_FILEPATH, 'r') as file:
    ciqual_data = json.load(file)

try:
    with open(INGREDIENTS_DATA_FILEPATH, 'r') as file:
        ingredients_data = json.load(file)
except FileNotFoundError:
    ingredients_data = dict()

# Looping on all links to append ciqual data to off ingredients
for off_id in links.OFF_ID.unique():

    if off_id in ingredients_data:
        ingredient = ingredients_data[off_id]
    else:
        ingredient = {'id': off_id}

    ingredient['nutritional_data_sources'] = []
    nutriments = dict()

    # Looping on ciqual products related to this off ingredient
    ciqual_ids = list(links[links.OFF_ID == off_id].CIQUAL_ID)
    if len(ciqual_ids) == 0:
        continue
    elif len(ciqual_ids) == 1:
        ciqual_product = ciqual_data[str(ciqual_ids[0])]
        ciqual_nutriments = ciqual_product['nutriments']

        ingredient['nutritional_data_sources'].append({'database': 'ciqual',
                                                       'entry': ciqual_product['alim_nom_eng']})

        # Getting minimum and maximum value for each nutriment
        # If they are not present, uses the confidence code to deduce it from the reference value
        # If there is no confidence code, use default error margin of 10%
        for nutriment_name in ciqual_nutriments:
            if (ciqual_nutriments[nutriment_name].get('value') is None) and \
                    (ciqual_nutriments[nutriment_name].get('min') is None):
                continue

            value = ciqual_nutriments[nutriment_name].get('value')

            if 'min' in ciqual_nutriments[nutriment_name]:
                min_value = ciqual_nutriments[nutriment_name]['min']
            else:
                min_value = value

            if 'max' in ciqual_nutriments[nutriment_name]:
                max_value = ciqual_nutriments[nutriment_name]['max']
            else:
                max_value = value

            max_value = min(max_value, 100) if nutriment_name != 'energy-kcal' else max_value

            # If value is undefined, take the middle value
            if (value is None) and ((min_value is not None) and (max_value is not None)):
                value = (min_value + max_value) / 2

            nutriments[nutriment_name] = {'value': value, 'min': min_value, 'max': max_value}
    else:
        # If there are more than one ciqual product linked to this off ingredient,
        # compile the data of every ciqual product
        values = dict()
        min_values = dict()
        max_values = dict()
        for ciqual_id in ciqual_ids:
            ciqual_product = ciqual_data[str(ciqual_id)]

            ingredient['nutritional_data_sources'].append({'database': 'ciqual',
                                                           'entry': ciqual_product['alim_nom_eng']})

            for nutriment_name, nutriment_data in ciqual_product['nutriments'].items():
                if (nutriment_data.get('value') is None) and (nutriment_data.get('min') is None):
                    continue

                if nutriment_name not in values:
                    values[nutriment_name] = []
                    min_values[nutriment_name] = []
                    max_values[nutriment_name] = []

                value = nutriment_data.get('value')

                if 'min' in nutriment_data:
                    min_value = nutriment_data['min']
                else:
                    min_value = value

                if 'max' in nutriment_data:
                    max_value = nutriment_data['max']
                else:
                    max_value = value

                # If value is undefined, take the middle value
                if (value is None) and ((min_value is not None) and (max_value is not None)):
                    value = (min_value + max_value) / 2

                values[nutriment_name].append(value)
                min_values[nutriment_name].append(min_value)
                max_values[nutriment_name].append(min(max_value, 100) if nutriment_name != 'energy-kcal' else max_value)

        for nutriment_name in values.keys():
            if values[nutriment_name]:
                nutriments[nutriment_name] = {'value': mean(values[nutriment_name]),
                                              'min': min(min_values[nutriment_name]),
                                              'max': max(max_values[nutriment_name])}

    if len(nutriments) > 0:
        # Add the nutriments dict to the ingredient
        ingredient['nutriments'] = nutriments

        # Adding the ingredient to the main result
        ingredients_data[off_id] = ingredient

with open(INGREDIENTS_DATA_FILEPATH, 'w') as file:
    json.dump(ingredients_data, file, indent=2, ensure_ascii=False)
