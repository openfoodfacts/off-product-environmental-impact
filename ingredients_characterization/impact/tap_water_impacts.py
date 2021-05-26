""" As tap water impacts are not available in the agribalyse dataset, this simple script adds it manually. """

import json

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.vars import TAP_WATER_IMPACTS_DATA_FILEPATH


def main():
    with open(INGREDIENTS_DATA_FILEPATH, 'r', encoding='utf8') as file:
        ingredients_data = json.load(file)

    with open(TAP_WATER_IMPACTS_DATA_FILEPATH, 'r', encoding='utf8') as file:
        tap_water_impacts = json.load(file)

    ingredient = ingredients_data.get('en:water', {'id': 'en:water'})
    ingredient['LCI'] = 'Water, municipal'
    ingredient['impacts'] = tap_water_impacts
    ingredient['environmental_impact_data_sources'] = [{"database": "agribalyse",
                                                        "entry": "Water, municipal"}]

    ingredients_data['en:water'] = ingredient

    with open(INGREDIENTS_DATA_FILEPATH, 'w', encoding='utf8') as file:
        json.dump(ingredients_data, file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
