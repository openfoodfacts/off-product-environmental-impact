""" Variables used by the ingredient characterization scripts """

import os

# External data used
EXTERNAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'external_data')
FCEN_DATA_DIR = os.path.join(EXTERNAL_DATA_DIR, 'fcen')
FCEN_DATA_FILEPATH = os.path.join(FCEN_DATA_DIR, 'fcen_data.json')
CIQUAL_DATA_DIR = os.path.join(EXTERNAL_DATA_DIR, 'ciqual')
CIQUAL_DATA_FILEPATH = os.path.join(CIQUAL_DATA_DIR, 'ciqual_data.json')
AGRIBALYSE_DATA_DIR = os.path.join(EXTERNAL_DATA_DIR, 'agribalyse')
AGRIBALYSE_DATA_FILEPATH = os.path.join(AGRIBALYSE_DATA_DIR, 'Agribalyse.json')
MANUAL_SOURCES_NUTRITION_DATA_FILEPATH = os.path.join(EXTERNAL_DATA_DIR, 'manual_nutrition_data.csv')
TAP_WATER_IMPACTS_DATA_FILEPATH = os.path.join(EXTERNAL_DATA_DIR, 'tap_water_impacts.json')

# Tables for linking between external data and OFF ingredients
LINKING_TABLES_DIR = os.path.join(os.path.dirname(__file__), 'linking_tables')
FCEN_OFF_LINKING_TABLE_FILEPATH = os.path.join(LINKING_TABLES_DIR, 'fcen_off_links.csv')
CIQUAL_OFF_LINKING_TABLE_FILEPATH = os.path.join(LINKING_TABLES_DIR, 'ciqual_off_links.csv')
AGRIBALYSE_OFF_LINKING_TABLE_FILEPATH = os.path.join(LINKING_TABLES_DIR, 'agribalyse_off_links.csv')
OFF_DUPLICATES_FILEPATH = os.path.join(LINKING_TABLES_DIR, 'off-duplicates.csv')

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

# Conversion from ciqual nutritional data identifiers to off
CIQUAL_TO_OFF = {'400': 'water',
                 '328': 'energy-kcal',
                 '25000': 'proteins',
                 '31000': 'carbohydrates',
                 '40000': 'fat',
                 '32000': 'sugars',
                 '34100': 'fiber',
                 '40302': 'saturated-fat',
                 '10004': 'salt'}
