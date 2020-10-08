""" Script to link Agribalyse LCI names to OFF ingredients """

import json

import pandas as pd

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.vars import AGRIBALYSE_OFF_LINKING_TABLE_FILEPATH

links = pd.read_csv(AGRIBALYSE_OFF_LINKING_TABLE_FILEPATH)

try:
    with open(INGREDIENTS_DATA_FILEPATH, 'r') as file:
        ingredients_data = json.load(file)
except FileNotFoundError:
    ingredients_data = dict()

for link in links.itertuples():
    if link.off_id not in ingredients_data:
        ingredients_data[link.off_id] = {'id': link.off_id}

    if 'LCI' not in ingredients_data[link.off_id]:
        ingredients_data[link.off_id]['LCI'] = []

    ingredients_data[link.off_id]['source_impact'] = 'Agribalyse'

    ingredients_data[link.off_id]['LCI'].append(link.agribalyse_en)

with open(INGREDIENTS_DATA_FILEPATH, 'w') as file:
    json.dump(ingredients_data, file, indent=2, ensure_ascii=False)
