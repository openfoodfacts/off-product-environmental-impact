""" Data used for environmental impact estimation of Open Food Facts products """

import os
import json

import pandas as pd

data_folder = os.path.dirname(__file__)

# OFF ingredients taxonomy
OFF_TAXONOMY_FILEPATH = os.path.join(data_folder, 'off_ingredients_taxonomy.json')
with open(OFF_TAXONOMY_FILEPATH, 'r', encoding='utf-8') as file:
    off_taxonomy = json.load(file)

# Data about OFF ingredients (impacts and nutriments)
INGREDIENTS_DATA_FILEPATH = os.path.join(data_folder, 'ingredients_data.json')
try:
    with open(INGREDIENTS_DATA_FILEPATH, 'r', encoding='utf-8') as file:
        ingredients_data = json.load(file)
except FileNotFoundError:
    ingredients_data = dict()

# Distribution of ingredients percentage by category in OFF
INGREDIENTS_DISTRIBUTION_FILEPATH = os.path.join(data_folder, 'off_ingredients_percentage_distribution.csv')
ref_ing_dist = pd.read_csv(INGREDIENTS_DISTRIBUTION_FILEPATH, na_filter=None, encoding='utf-8')

OFF_CATEGORIES_FILEPATH = os.path.join(data_folder, 'off_categories.json')
with open(OFF_CATEGORIES_FILEPATH, 'r', encoding='utf-8') as file:
    off_categories = json.load(file)
