""" Script to copy nutritional and/or impact data from off ingredients to their proxies """

import json
import copy

import pandas as pd

from ingredients_characterization.vars import OFF_DUPLICATES_FILEPATH
from data import INGREDIENTS_DATA_FILEPATH

duplicates = pd.read_csv(OFF_DUPLICATES_FILEPATH)
duplicates.columns = ['ingredient', 'reference', 'proxy_type']

with open(INGREDIENTS_DATA_FILEPATH, 'r') as file:
    ingredients_data = json.load(file)

for duplicate in duplicates.itertuples():
    try:
        proxy = copy.deepcopy(ingredients_data[duplicate.reference])
    except KeyError:
        continue

    ingredient = {'id': duplicate.ingredient}

    # Nutritional proxy
    if (duplicate.proxy_type != 2) and ('nutriments' in proxy):
        ingredient['nutriments'] = proxy['nutriments']
        ingredient['nutritional_proxy'] = duplicate.reference

    # Impact proxy
    if (duplicate.proxy_type != 1) and ('LCI' in proxy):
        ingredient['LCI'] = proxy['LCI']
        ingredient['impacts'] = proxy['impacts']
        ingredient['environmental_impact_proxy'] = duplicate.reference

    ingredients_data[duplicate.ingredient] = ingredient


# Rolling up proxies to "root" for all ingredients
def get_root_proxy(ingredient_param, proxy_type_param):
    if proxy_type_param in ingredient_param:
        if ingredient_param[proxy_type_param] == ingredient_param['id']:
            del ingredient_param[proxy_type_param]
            return ingredient_param['id']

        return get_root_proxy(ingredients_data[ingredient_param[proxy_type_param]], proxy_type_param)
    else:
        return ingredient_param['id']


for ingredient_name, ingredient_data in ingredients_data.items():
    if 'nutritional_proxy' in ingredient_data:
        ingredient_data['nutritional_proxy'] = get_root_proxy(ingredient_data, 'nutritional_proxy')
    if 'environmental_impact_proxy' in ingredient_data:
        ingredient_data['environmental_impact_proxy'] = get_root_proxy(ingredient_data, 'environmental_impact_proxy')

with open(INGREDIENTS_DATA_FILEPATH, 'w') as file:
    json.dump(ingredients_data, file, indent=2, ensure_ascii=False)
