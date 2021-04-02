""" Script to copy nutritional and/or impact data from off ingredients to their proxies """

import json
import copy

import pandas as pd

from ingredients_characterization.vars import OFF_DUPLICATES_FILEPATH
from data import INGREDIENTS_DATA_FILEPATH


def main():
    duplicates = pd.read_csv(OFF_DUPLICATES_FILEPATH)
    duplicates.columns = ['ingredient', 'reference', 'proxy_type']

    with open(INGREDIENTS_DATA_FILEPATH, 'r', encoding='utf8') as file:
        ingredients_data = json.load(file)

    for duplicate in duplicates.itertuples():
        try:
            proxy = copy.deepcopy(ingredients_data[duplicate.reference])
        except KeyError:
            continue

        if duplicate.ingredient in ingredients_data:
            ingredient = ingredients_data[duplicate.ingredient]
        else:
            ingredient = {'id': duplicate.ingredient}

        # Nutritional proxy
        if (duplicate.proxy_type != 2) and ('nutriments' in proxy) and ('nutriments' not in ingredient):
            ingredient['nutriments'] = proxy['nutriments']
            ingredient['nutritional_data_sources'] = proxy['nutritional_data_sources']
            ingredient['nutritional_proxy'] = duplicate.reference

        # Impact proxy
        if (duplicate.proxy_type != 1) and ('LCI' in proxy) and ('LCI' not in ingredient):
            ingredient['environmental_impact_data_sources'] = proxy['environmental_impact_data_sources']
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
            ingredient_data['environmental_impact_proxy'] = get_root_proxy(ingredient_data,
                                                                           'environmental_impact_proxy')

    with open(INGREDIENTS_DATA_FILEPATH, 'w', encoding='utf8') as file:
        json.dump(ingredients_data, file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
