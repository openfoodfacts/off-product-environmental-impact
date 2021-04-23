from pathlib import Path
from openfoodfacts.products import get_product


def ensure_extension(filename, extension):
    return Path(filename).with_suffix(f".{extension}")


def get_product_from_barcode(barcode):
    query_result = get_product(str(barcode))

    if query_result['status'] == 0:
        raise ValueError('The product corresponding to this barcode cannot be found.')

    return query_result['product']
