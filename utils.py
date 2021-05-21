import json

import requests


def get_product_from_barcode(barcode):
    response = requests.get(f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json")

    if response.status_code == 404:
        raise ValueError('The product corresponding to this barcode cannot be found.')

    return json.loads(response.content)['product']
