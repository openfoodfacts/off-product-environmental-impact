""" Script to link Agribalyse LCI names to OFF ingredients """

import json

import pandas as pd

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.vars import AGRIBALYSE_OFF_LINKING_TABLE_FILEPATH


def main():
    links = pd.read_csv(AGRIBALYSE_OFF_LINKING_TABLE_FILEPATH)

    try:
        with open(INGREDIENTS_DATA_FILEPATH, 'r') as file:
            ingredients_data = json.load(file)
    except FileNotFoundError:
        ingredients_data = dict()

    for link in links.itertuples():
        if link.off_id not in ingredients_data:
            ingredients_data[link.off_id] = {'id': link.off_id}

        if 'environmental_impact_data_sources' not in ingredients_data[link.off_id]:
            ingredients_data[link.off_id]['environmental_impact_data_sources'] = []

        if link.agribalyse_en not in [x['entry'] for x in
                                      ingredients_data[link.off_id]['environmental_impact_data_sources']]:
            ingredients_data[link.off_id]['environmental_impact_data_sources'].append({'database': 'agribalyse',
                                                                                       'entry': link.agribalyse_en})

    with open(INGREDIENTS_DATA_FILEPATH, 'w') as file:
        json.dump(ingredients_data, file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
