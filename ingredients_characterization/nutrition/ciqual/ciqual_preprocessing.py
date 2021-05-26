"""
Script to extract nutrition data from the ciqual XML files and convert it to a more usable JSON format
"""

import os
import json

import xmltodict

from ingredients_characterization.vars import CIQUAL_DATA_DIR, CIQUAL_DATA_FILEPATH, CIQUAL_TO_OFF

with open(os.path.join(CIQUAL_DATA_DIR, 'alim_2020_07_07.xml'), 'r', encoding='windows-1252') as file:
    products = xmltodict.parse(file.read())['TABLE']['ALIM']

with open(os.path.join(CIQUAL_DATA_DIR, 'compo_2020_07_07.xml'), 'r', encoding='windows-1252') as file:
    compositions = xmltodict.parse(file.read())['TABLE']['COMPO']

top_level_nutriments = ['proteins', 'carbohydrates', 'fat', 'fiber', 'salt', 'water']

# Changing products structures to dicts
products_dict = dict()
for product in products:
    products_dict[product['alim_code']] = product
products = products_dict


def parse_number(text):
    if text == '-':
        return None

    return float(text
                 .replace(',', '.')
                 .replace('traces', '0')
                 .replace('<', ''))


# Looping over compositions to join the nutritional data
for composition in compositions:
    product = products[composition['alim_code']]
    if 'nutriments' not in product:
        product['nutriments'] = dict()
    nutri = product['nutriments']

    if composition['const_code'] in CIQUAL_TO_OFF:
        nutri_dict = dict()

        if (type(composition['teneur']) is str) and (type(composition['teneur']) != '-'):
            nutri_dict['value'] = parse_number(composition['teneur'])
        if (type(composition['min']) is str) and (type(composition['min']) != '-'):
            nutri_dict['min'] = parse_number(composition['min'])
        if (type(composition['max']) is str) and (type(composition['max']) != '-'):
            nutri_dict['max'] = parse_number(composition['max'])

        # CIQUAL confidence code: A = Very likely, D = Less likely
        if type(composition['code_confiance']) is str:
            nutri_dict['confidence_code'] = composition['code_confiance']

        nutri_type = CIQUAL_TO_OFF[composition['const_code']]
        nutri[nutri_type] = nutri_dict

# Looping over products to rectify the data and add a "other" nutriment category
for product in products.values():
    total_sum = sum([v['value'] or 0 for k, v in product['nutriments'].items() if k in top_level_nutriments])
    product['nutriments']['other'] = {'value': 0, 'min': 0, 'max': 0}

    # If the total sum is superior to 100, rectify the values
    if total_sum > 100:
        for nutri in product['nutriments'].values():
            if nutri['value']:
                nutri['value'] = nutri['value'] * 100 / total_sum

                if 'min' in nutri:
                    nutri['min'] = min(nutri['value'], nutri['min'])

    # If the total sum is inferior to 100, add a "other" nutriment category that will ensure mass balance
    elif (total_sum < 100) and (all([product['nutriments'].get(x) is not None for x in top_level_nutriments])):
        product['nutriments']['other']['value'] = 100 - total_sum

    # Adjust the min and max values for the "other" category
    product['nutriments']['other']['min'] = max(0, 100 - sum([v.get('max', v['value']) or 0
                                                              for k, v in product['nutriments'].items()
                                                              if k in top_level_nutriments]))

    product['nutriments']['other']['max'] = min(100, 100 - sum([v.get('min', v['value']) or 0
                                                                for k, v in product['nutriments'].items()
                                                                if k in top_level_nutriments]))

# Exporting the result
with open(CIQUAL_DATA_FILEPATH, 'w', encoding='utf8') as file:
    json.dump(products, file, indent=2, ensure_ascii=False)
