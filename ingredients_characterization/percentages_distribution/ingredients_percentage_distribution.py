"""
Script to get the distribution of defined percentage of most important ingredients according to their categories.
Needs a working MongoDB server containing the Open Food Facts database.
"""

import pandas as pd
import pymongo
import tqdm

from data import INGREDIENTS_DISTRIBUTION_FILEPATH

# Minimum number of defined percentage per ingredient
MIN_VALUE_NB = 30

df = pd.DataFrame(columns=['id', 'percent', 'categories_tags'])

client = pymongo.MongoClient()
db = client['off']
products = db['products']
query = {"ingredients": {"$elemMatch": {"percent": {"$exists": True}}}}

cursor = products.find(query,
                       {'ingredients.percent': 1,
                        'ingredients.id': 1,
                        'categories_tags': 1},
                       no_cursor_timeout=True).batch_size(1000)

# Looping on all products and all ingredients, adding the ingredient and its percentage to the dataframe if it is
#  defined
for product in tqdm.tqdm(cursor):
    for ingredient in product['ingredients']:
        if 'percent' not in ingredient:
            continue
        # Removing erroneous data
        if not (0 < float(ingredient["percent"]) <= 100):
            continue

        df = df.append({"id": ingredient['id'],
                        "percent": float(ingredient["percent"]),
                        "categories_tags": product.get('categories_tags')},
                       ignore_index=True)

# Removing elements with less than the minimum number of values
counts = df.id.value_counts()
df = df[df.id.isin(counts[counts >= MIN_VALUE_NB].index)]

# Sorting the dataframe by id
df.id = pd.Categorical(df.id, counts.index)
df.sort_values('id', inplace=True)

# Saving the dataframe
df.to_csv(INGREDIENTS_DISTRIBUTION_FILEPATH)
