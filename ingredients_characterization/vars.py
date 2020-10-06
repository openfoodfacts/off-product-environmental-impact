""" Variables used by the ingredient characterization scripts """

import os

# External data used
EXTERNAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'external_data')
FCEN_DATA_DIR = os.path.join(EXTERNAL_DATA_DIR, 'fcen')
FCEN_DATA_FILEPATH = os.path.join(FCEN_DATA_DIR, 'fcen_data.json')

# Tables for linking between external data and OFF ingredients
LINKING_TABLES_DIR = os.path.join(os.path.dirname(__file__), 'linking_tables')
FCEN_OFF_LINKING_TABLE_FILEPATH = os.path.join(LINKING_TABLES_DIR, 'fcen_off_links.csv')

# Conversion from FCEN nutritional data identifiers to off
FCEN_NUTRIMENTS_TO_OFF = {255: 'water',
                          208: 'energy-kcal',
                          203: 'proteins',
                          205: 'carbohydrates',
                          204: 'fat',
                          269: 'sugars',
                          291: 'fiber',
                          606: 'saturated-fat',
                          207: 'ash'}
