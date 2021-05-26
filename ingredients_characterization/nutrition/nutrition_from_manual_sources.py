""" Nutritional characterization of OFF ingredients by manually collected data """

import json

import pandas as pd

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.vars import MANUAL_SOURCES_NUTRITION_DATA_FILEPATH
from impacts_estimation.vars import NUTRIMENTS_CATEGORIES, TOP_LEVEL_NUTRIMENTS_CATEGORIES


def main():
    with open(INGREDIENTS_DATA_FILEPATH, 'r', encoding='utf8') as file:
        ingredients_data = json.load(file)

    manual_data = pd.read_csv(MANUAL_SOURCES_NUTRITION_DATA_FILEPATH)

    # Adding data with nutritional values
    for nutrition_data in manual_data.itertuples():
        ingredient_name = nutrition_data.OFF_ID

        if ingredient_name in ingredients_data:
            ingredient = ingredients_data[ingredient_name]
        else:
            ingredient = {'id': ingredient_name}

        for nutriment_name in NUTRIMENTS_CATEGORIES:
            if nutriment_name == 'other':
                continue

            value = getattr(nutrition_data, nutriment_name.replace('-', '_'))  # "-" replacement for "saturated-fat"

            if pd.notnull(value):
                value = float(value)

                # Creating the nutriments dict if it does not exist
                if 'nutriments' not in ingredient:
                    ingredient['nutriments'] = dict()

                ingredient['nutriments'][nutriment_name] = {'value': value,
                                                            'min': value,
                                                            'max': value}

        if ('nutriments' in ingredient) and len(ingredient['nutriments']) > 0:
            nutriments_sum = sum([v['value'] for k, v in ingredient['nutriments'].items()
                                  if k in TOP_LEVEL_NUTRIMENTS_CATEGORIES])
            ingredient['nutriments']['other'] = {'value': 0}

            # If the total sum is superior to 100, rectify the values
            if nutriments_sum > 100:
                for nutri in ingredient['nutriments'].values():
                    if nutri['value']:
                        nutri['value'] = nutri['value'] * 100 / nutriments_sum

            # If the total sum is inferior to 100, add a "other" nutriment category that will ensure mass balance
            elif (nutriments_sum < 100) and (
            all([x in ingredient['nutriments'] for x in TOP_LEVEL_NUTRIMENTS_CATEGORIES])):
                ingredient['nutriments']['other']['value'] = 100 - nutriments_sum

            # Adjust the min and max values for the "other" category
            ingredient['nutriments']['other']['min'] = max(0, 100 - sum([v.get('max', v['value']) or 0
                                                                         for k, v in ingredient['nutriments'].items()
                                                                         if k in TOP_LEVEL_NUTRIMENTS_CATEGORIES]))

            ingredient['nutriments']['other']['max'] = min(100, 100 - sum([v.get('min', v['value']) or 0
                                                                           for k, v in ingredient['nutriments'].items()
                                                                           if k in TOP_LEVEL_NUTRIMENTS_CATEGORIES]))

        ingredient['nutritional_data_sources'] = [{'database': 'manual sources',
                                                  'entry': nutrition_data.SOURCE if pd.notnull(
                                                      nutrition_data.SOURCE) else 'Manual entry'}]

        ingredients_data[ingredient_name] = ingredient

    with open(INGREDIENTS_DATA_FILEPATH, 'w', encoding='utf8') as file:
        json.dump(ingredients_data, file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
