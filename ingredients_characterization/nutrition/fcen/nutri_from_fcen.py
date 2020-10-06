""" Script to link FCEN nutritional data to OFF ingredients """

import json
from statistics import mean
import math

import pandas as pd

from ingredients_characterization.vars import FCEN_DATA_FILEPATH, FCEN_OFF_LINKING_TABLE_FILEPATH
from data import INGREDIENTS_DATA_FILEPATH

links = pd.read_csv(FCEN_OFF_LINKING_TABLE_FILEPATH)

with open(FCEN_DATA_FILEPATH, 'r') as file:
    fcen_data = json.load(file)

with open(INGREDIENTS_DATA_FILEPATH, 'r') as file:
    ingredients_data = json.load(file)

ingredients_data_dict = {x['id']: x for x in ingredients_data.values()}

# Looping on all links to append fcen data to off ingredients
for off_id in links.OFF_ID.unique():

    if off_id in ingredients_data_dict:
        ingredient = ingredients_data_dict[off_id]
    else:
        ingredient = {'source_nutri': 'fcen'}

    nutriments = dict()

    # Looping on fcen products related to this off ingredient
    fcen_ids = list(links[links.OFF_ID == off_id].FCEN_ID)
    if len(fcen_ids) == 0:
        continue
    elif len(fcen_ids) == 1:
        fcen_nutriments = fcen_data[str(fcen_ids[0])]['nutriments']

        # Getting minimum and maximum value for each nutriment using the standard deviation
        # The distribution of the nutriment amount is supposed to be normal and the minimum and maximum values are
        # defined as:
        # min/max = reference_value -/+ 2 * std_error
        # If no standard error is given, a default 10% margin is used

        # Getting minimum and maximum value for each nutriment
        # If they are not present, uses the reference value
        for nutriment_name in fcen_nutriments:
            value = fcen_nutriments[nutriment_name]['value']
            stdev = fcen_nutriments[nutriment_name]['stdev']

            if not math.isnan(stdev):
                min_value = value - (2 * stdev)
                max_value = value + (2 * stdev)
            else:
                min_value = value
                max_value = value

            max_value = min(max_value, 100)

            nutriments[nutriment_name] = {'value': value,
                                          'min': min_value,
                                          'max': max_value}

    else:
        # If there are more than one fcen product linked to this off ingredient,
        # compile the data of every fcen product
        values = dict()
        min_values = dict()
        max_values = dict()
        for fcen_id in fcen_ids:
            fcen_product = fcen_data[str(fcen_id)]

            for nutriment_name, nutriment_data in fcen_product['nutriments'].items():
                if nutriment_name not in values:
                    values[nutriment_name] = []
                    min_values[nutriment_name] = []
                    max_values[nutriment_name] = []

                value = nutriment_data['value']
                stdev = nutriment_data['stdev']

                if not math.isnan(stdev):
                    min_value = value - (2 * stdev)
                    max_value = value + (2 * stdev)
                else:
                    min_value = value
                    max_value = value

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
