import json
from pathlib import Path

import requests


def ensure_extension(filename, extension):
    """
        Ensures of the extension of a file

        >>> ensure_extension('foo.pdf', 'pdf')
        'foo.pdf'
        >>> ensure_extension('bar.csv', 'pdf')
        'bar.pdf'
    """
    return str(Path(filename).with_suffix(f".{extension}"))


def smart_round_format(number, precision):
    """
    Args:
        number (float):
        precision (int):

    Returns:
        str:

    Examples:
        >>> smart_round_format(258.658, 2)
        '258.66'
        >>> smart_round_format(0.258658, 2)
        '0.26'
        >>> smart_round_format(0.0000258658, 2)
        '2.59e-05'
    """

    if number >= 0.1:
        return str(round(number, 2))

    else:
        return ('{:0.' + str(precision) + 'e}').format(number)


def get_product_from_barcode(barcode):
    response = requests.get(f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json")

    if response.status_code == 404:
        raise ValueError('The product corresponding to this barcode cannot be found.')

    return json.loads(response.content)['product']
