import json
from pathlib import Path
# from openfoodfacts.products import get_product  # Not used because it uses the API v0 and API v2 is needed
import requests


def ensure_extension(filename, extension):
    return Path(filename).with_suffix(f".{extension}")


def get_product_from_barcode(barcode):
    response = requests.get(f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json")

    if response.status_code == 404:
        raise ValueError('The product corresponding to this barcode cannot be found.')

    return json.loads(response.content)['product']
