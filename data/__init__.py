""" Data used for environmental impact estimation of Open Food Facts products """

import os
import json

import pandas as pd

data_folder = os.path.dirname(__file__)

# OFF ingredients taxonomy
with open(os.path.join(data_folder, 'off_ingredients_taxonomy.json'), 'r') as file:
    off_taxonomy = json.load(file)

# Data about OFF ingredients (impacts and nutriments)
with open(os.path.join(data_folder, 'ingredients_data.json'), 'r') as file:
    ingredients_data = json.load(file)

# Distribution of ingredients percentage by category in OFF
ref_ing_dist = pd.read_csv(os.path.join(data_folder, 'off_ingredients_percentage_distribution.csv'), na_filter=None)
