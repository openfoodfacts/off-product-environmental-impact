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

AGRIBALYSE_IMPACT_CATEGORIES = [
    "Score unique EF",
    "Changement climatique",
    "Appauvrissement de la couche d'ozone",
    "Rayonnements ionisants",
    "Formation photochimique d'ozone",
    "Particules",
    "Acidification terrestre et eaux douces",
    "Eutrophisation terrestre",
    "Eutrophisation eaux douces",
    "Eutrophisation marine",
    "Utilisation du sol",
    "Écotoxicité pour écosystèmes aquatiques d'eau douce",
    "Épuisement des ressources eau",
    "Épuisement des ressources énergétiques",
    "Épuisement des ressources minéraux"]

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
