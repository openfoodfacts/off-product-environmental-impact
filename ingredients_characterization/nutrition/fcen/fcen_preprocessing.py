"""
Preprocessing of the Fichier Canadien des Éléments Nutritifs (FCEN) data before using it to characterize OFF ingredients
"""

import os
import pandas as pd
import json

from ingredients_characterization.vars import FCEN_DATA_DIR, FCEN_NUTRIMENTS_TO_OFF, FCEN_DATA_FILEPATH

# Reading data from FCEN
food_names = pd.read_csv(os.path.join(FCEN_DATA_DIR, 'FOOD NAME.csv'), encoding='ISO-8859-1')
nutrient_amounts = pd.read_csv(os.path.join(FCEN_DATA_DIR, 'NUTRIENT AMOUNT.csv'), encoding='ISO-8859-1')

top_level_nutriments = ['proteins', 'carbohydrates', 'fat', 'fiber', 'water']

# Looping on FCEN ingredients
result = dict()
for i, food in food_names.iterrows():

    # Looping on nutriments
    nutriments = dict()
    foo_nutrient_amounts = nutrient_amounts[(nutrient_amounts.FoodID == food.FoodID) &
                                            (nutrient_amounts.NutrientID.isin(FCEN_NUTRIMENTS_TO_OFF.keys()))]
    for j, nutri_amount in foo_nutrient_amounts.iterrows():
        nutriments[FCEN_NUTRIMENTS_TO_OFF[nutri_amount.NutrientID]] = {"value": nutri_amount.NutrientValue,
                                                                       "stdev": nutri_amount.StandardError}

    nutriments_sum = sum([v['value'] for k, v in nutriments.items() if k in top_level_nutriments])
    nutriments['other'] = {'value': 0, 'stdev': 0}

    # If the total sum is superior to 100, rectify the values
    if nutriments_sum > 100:
        for nutri in nutriments.values():
            if nutri['value']:
                nutri['value'] = nutri['value'] * 100 / nutriments_sum

    # If the total sum is inferior to 100, add a "other" nutriment category that will ensure mass balance
    elif (nutriments_sum < 100) and (all([x in nutriments for x in top_level_nutriments])):
        nutriments['other']['value'] = 100 - nutriments_sum

    # Adding the data to the result
    food['nutriments'] = nutriments
    result[food.FoodID] = food.to_dict()

# Saving the result
with open(FCEN_DATA_FILEPATH, 'w', encoding='utf8') as file:
    json.dump(result, file, indent=2, ensure_ascii=False)
