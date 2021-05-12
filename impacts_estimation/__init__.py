""" Environmental impact estimation for Open Food Facts products """

from impacts_estimation.impacts_estimation import estimate_impacts, estimate_impacts_safe
from impacts_estimation.exceptions import RecipeCreationError, NoKnownIngredientsError, \
    NoCharacterizedIngredientsError, SolverTimeoutError
from impacts_estimation.vars import AGRIBALYSE_IMPACT_CATEGORIES_FR
