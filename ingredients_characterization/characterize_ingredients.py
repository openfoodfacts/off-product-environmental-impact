""" Script to run all the OFF ingredients characterization script at one and in the right order """

from ingredients_characterization.nutrition.ciqual import nutri_from_ciqual
from ingredients_characterization.nutrition.fcen import nutri_from_fcen
from ingredients_characterization.nutrition import nutrition_from_manual_sources
from ingredients_characterization.impact import lci_from_agribalyse
from ingredients_characterization.impact import impacts_from_agribalyse
from ingredients_characterization.duplicates import off_duplicates_processing
