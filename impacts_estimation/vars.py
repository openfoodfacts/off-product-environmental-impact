""" Variables used by the impact estimation program """

# Nutriment categories taken into account for the recipe resolution
TOP_LEVEL_NUTRIMENTS_CATEGORIES = ['proteins',
                                   'carbohydrates',
                                   'fat',
                                   'fiber',
                                   'salt',
                                   'other']

NUTRIMENTS_CATEGORIES = TOP_LEVEL_NUTRIMENTS_CATEGORIES + ['sugars',
                                                           'saturated-fat']

# Max ash content of ingredients in %
MAX_ASH_CONTENT = 10

# Elements of the data_quality_tags attribute of products that should prevent from using nutritional information
# to guess the product's recipe
QUALITY_DATA_WARNINGS = {
    'global': ['en:missing-nutrition-data-prepared-with-category-dried-products-to-be-rehydrated',
               'en:no-nutrition-data',
               'en:nutrition-all-values-zero',
               'en:nutrition-data-prepared-without-category-dried-products-to-be-rehydrated',
               'en:nutrition-value-total-over-1000',
               'en:nutrition-value-total-over-105'],
    'energy-kcal': ['en:energy-value-in-kcal-greater-than-in-kj',
                    'en:nutrition-value-over-3800-energy',
                    'en:nutrition-value-very-high-for-category-energy',
                    'en:nutrition-value-very-low-for-category-carbohydrates'],
    'proteins': ['en:nutrition-value-over-1000-proteins',
                 'en:nutrition-value-over-105-proteins',
                 'en:nutrition-value-very-high-for-category-proteins',
                 'en:nutrition-value-very-low-for-category-proteins'],
    'carbohydrates': ['en:nutrition-sugars-plus-starch-greater-than-carbohydrates',
                      'en:nutrition-value-over-1000-carbohydrates',
                      'en:nutrition-value-over-105-carbohydrates',
                      'en:nutrition-value-very-high-for-category-carbohydrates',
                      'en:nutrition-value-very-low-for-category-carbohydrates'],
    'fat': ['en:nutrition-saturated-fat-greater-than-fat',
            'en:nutrition-value-over-1000-fat',
            'en:nutrition-value-over-105-fat',
            'en:nutrition-value-very-high-for-category-fat',
            'en:nutrition-value-very-low-for-category-fat'],
    'sugars': ['en:nutrition-sugars-plus-starch-greater-than-carbohydrates',
               'en:nutrition-value-over-1000-sugars',
               'en:nutrition-value-over-105-sugars',
               'en:nutrition-value-very-high-for-category-sugars',
               'en:nutrition-value-very-low-for-category-saturated-fat'],
    'fiber': ['en:nutrition-value-over-1000-fiber',
              'en:nutrition-value-over-105-fiber',
              'en:nutrition-value-very-high-for-category-fiber',
              'en:nutrition-value-very-low-for-category-fiber'],
    'saturated-fat': ['en:nutrition-saturated-fat-greater-than-fat',
                      'en:nutrition-value-over-1000-saturated-fat',
                      'en:nutrition-value-over-105-saturated-fat',
                      'en:nutrition-value-very-high-for-category-saturated-fat',
                      'en:nutrition-value-very-low-for-category-saturated-fat'],
    'salt': ['en:nutrition-value-over-1000-salt',
             'en:nutrition-value-over-105-salt',
             'en:nutrition-value-very-high-for-category-salt',
             'en:nutrition-value-very-low-for-category-salt']
}
QUALITY_DATA_WARNINGS_FLAT = [x for y in QUALITY_DATA_WARNINGS.values() for x in y]

# What is the mass (in g) for which ingredients impacts are given
IMPACT_MASS_UNIT = 1000  # Ingredients impacts are given per kg

AGRIBALYSE_IMPACT_CATEGORIES_EN_TO_FR = {
    'EF single score': 'Score unique EF',
    'Climate change': 'Changement climatique',
    'Ozone depletion': "Appauvrissement de la couche d'ozone",
    'Ionising radiation, HH': 'Rayonnements ionisants',
    'Photochemical ozone formation, HH': "Formation photochimique d'ozone",
    'Respiratory inorganics': 'Particules',
    'Acidification terrestrial and freshwater': 'Acidification terrestre et eaux douces',
    'Eutrophication terrestrial': 'Eutrophisation terrestre',
    'Eutrophication freshwater': 'Eutrophisation eaux douces',
    'Eutrophication marine': 'Eutrophisation marine',
    'Land use': 'Utilisation du sol',
    'Ecotoxicity freshwater': "Écotoxicité pour écosystèmes aquatiques d'eau douce",
    'Water scarcity': 'Épuisement des ressources eau',
    'Resource use, energy carriers': 'Épuisement des ressources énergétiques',
    'Resource use, mineral and metals': 'Épuisement des ressources minéraux'
}

AGRIBALYSE_IMPACT_CATEGORIES_FR = list(AGRIBALYSE_IMPACT_CATEGORIES_EN_TO_FR.values())
AGRIBALYSE_IMPACT_CATEGORIES_EN = list(AGRIBALYSE_IMPACT_CATEGORIES_EN_TO_FR.keys())
AGRIBALYSE_IMPACT_CATEGORIES_FR_TO_EN = {v: k for k, v in AGRIBALYSE_IMPACT_CATEGORIES_EN_TO_FR.items()}

AGRIBALYSE_IMPACT_UNITS = {
    "Score unique EF": "mPt",
    "Changement climatique": "kg CO2 eq",
    "Appauvrissement de la couche d'ozone": "E-06 kg CVC11 eq",
    "Rayonnements ionisants": "kBq U-235 eq",
    "Formation photochimique d'ozone": "E-03 kg NMVOC eq",
    "Particules": "E-06 disease inc.",
    "Acidification terrestre et eaux douces": "mol H+ eq",
    "Eutrophisation terrestre": "mol N eq",
    "Eutrophisation eaux douces": "E-03 kg P eq",
    "Eutrophisation marine": "E-03 kg N eq",
    "Utilisation du sol": "Pt",
    "Écotoxicité pour écosystèmes aquatiques d'eau douce": "CTUe",
    "Épuisement des ressources eau": "m3 depriv.",
    "Épuisement des ressources énergétiques": "MJ",
    "Épuisement des ressources minéraux": "E-06 kg Sb eq"
}

AGRIBALYSE_IMPACT_UNITS_MAGNITUDE_ORDER = {
    "Score unique EF": 1e-3,
    "Changement climatique": 1,
    "Appauvrissement de la couche d'ozone": 1e-6,
    "Rayonnements ionisants": 1,
    "Formation photochimique d'ozone": 1e-3,
    "Particules": 1e-6,
    "Acidification terrestre et eaux douces": 1,
    "Eutrophisation terrestre": 1,
    "Eutrophisation eaux douces": 1e-3,
    "Eutrophisation marine": 1e-3,
    "Utilisation du sol": 1,
    "Écotoxicité pour écosystèmes aquatiques d'eau douce": 1,
    "Épuisement des ressources eau": 1,
    "Épuisement des ressources énergétiques": 1,
    "Épuisement des ressources minéraux": 1e-6
}

FERMENTATION_AGENTS = ['en:selected-ferments',
                       'en:selected-lactic-ferments',
                       'en:lactic-ferments',
                       'en:ferment',
                       'fr:ferments-de-maturation',
                       'en:lactobacillus-casei',
                       'en:bifidus',
                       'en:fermented-milk-products',
                       'en:lactic-and-aging-ferments',
                       'en:bacillus-coagulans',
                       'en:lactobacillus',
                       'en:skyr-cultures',
                       'en:sourdough-starter',
                       'en:streptococcus-thermophilus',
                       'es:bifidobacterias-y-otros-fermentos-lacticos',
                       'fr:ferments-lactiques-dont-lactobacillus-casei',
                       'en:vegan-lactic-ferments',
                       'en:natural-yeast',
                       'en:selenium-enriched-yeast',
                       'en:baker-s-yeast',
                       'en:fresh-yeast',
                       'en:yeast-extract-powder',
                       'en:yeast-extract',
                       'en:brewer-s-yeast',
                       'en:torula-yeast',
                       'en:yeast-extract',
                       'en:autolyzed-yeast-extract',
                       'en:yeast-powder',
                       'en:nutritional-yeast',
                       'en:yeast',
                       'de:trockenhefe']

FERMENTED_FOOD_CATEGORIES = ['en:fermented-foods']

# Dictionary containing the names of the categories with a high water loss potential as keys and the maximum evaporation
# coefficient of the category as values
HIGH_WATER_LOSS_CATEGORIES = {'en:cheeses': 0.9}

RESULTS_WARNINGS_NOT_RELIABLE = ["The product has no recognized nutriment information."]
