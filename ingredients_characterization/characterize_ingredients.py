""" Script to run all the OFF ingredients characterization script at one and in the right order """
import os

from data import INGREDIENTS_DATA_FILEPATH

from ingredients_characterization.nutrition.ciqual import nutri_from_ciqual
from ingredients_characterization.nutrition.fcen import nutri_from_fcen
from ingredients_characterization.nutrition import nutrition_from_manual_sources
from ingredients_characterization.impact import lci_from_agribalyse
from ingredients_characterization.impact import impacts_from_agribalyse
from ingredients_characterization.impact import tap_water_impacts
from ingredients_characterization.duplicates import off_duplicates_processing


def main():
    if os.path.isfile(INGREDIENTS_DATA_FILEPATH):
        os.remove(INGREDIENTS_DATA_FILEPATH)

    nutri_from_ciqual.main()
    nutri_from_fcen.main()
    nutrition_from_manual_sources.main()
    lci_from_agribalyse.main()
    impacts_from_agribalyse.main()
    tap_water_impacts.main()
    off_duplicates_processing.main()


if __name__ == '__main__':
    main()
